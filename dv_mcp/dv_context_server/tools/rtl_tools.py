"""RTL MCP tools — pure Python, no MCP runtime dependency.

Tools:
  - rtl_find_signal: find a signal in the RTL index by name
  - rtl_get_instance_info: get module or instance details from the RTL index
  - rtl_get_source_snippet: read source snippet for a signal definition
  - rtl_trace_fanin: trace same-module signals that may affect a signal (mock stub)
"""

from __future__ import annotations

from typing import Any

from dv_mcp.dv_context_server.indexes.readers import IndexNotFoundError
from dv_mcp.dv_context_server.services.evidence import rtl_evidence
from dv_mcp.dv_context_server.services.project_loader import (
    get_index_reader,
    get_manifest,
)
from dv_mcp.dv_context_server.services.summarizer import envelope, error_envelope
from lib.source_resolver import SourceResolver

_RTL_INDEX = "rtl_index.json"


def rtl_find_signal(
    project: str,
    signal_name: str,
    module_filter: str | None = None,
) -> dict[str, Any]:
    """Find RTL signals matching a name pattern.

    Searches module ports and signals. Supports substring matching.

    Args:
        project: Project ID or manifest path.
        signal_name: Signal name or substring to search for.
        module_filter: Optional module name to restrict search.

    Returns:
        Envelope with matching signals and their module context.
    """
    tool = "rtl_find_signal"
    try:
        reader = get_index_reader(project)
        data = reader.read(_RTL_INDEX)
    except (FileNotFoundError, IndexNotFoundError) as e:
        return error_envelope(tool, project, str(e))

    modules = data.get("modules", [])
    search = signal_name.lower()
    matches: list[dict] = []
    evidence_list: list[dict] = []

    for mod in modules:
        mod_name = mod.get("name", "")
        if module_filter and module_filter.lower() not in mod_name.lower():
            continue

        # Search ports
        for port in mod.get("ports", []):
            if search in port.lower():
                match = {
                    "module": mod_name,
                    "file": mod.get("file"),
                    "signal_name": port,
                    "signal_type": "port",
                    "line": None,
                    "width": None,
                }
                matches.append(match)
                evidence_list.append(
                    rtl_evidence(
                        mod_name, port, f"{mod.get('file', '?')}",
                        f"Port {port} in {mod_name}",
                    )
                )

        # Search signals
        for sig in mod.get("signals", []):
            sig_name = sig.get("name", "")
            if search in sig_name.lower():
                match = {
                    "module": mod_name,
                    "file": mod.get("file"),
                    "signal_name": sig_name,
                    "signal_type": sig.get("type", "unknown"),
                    "width": sig.get("width"),
                    "line": sig.get("line"),
                }
                matches.append(match)
                evidence_list.append(
                    rtl_evidence(
                        mod_name, sig_name,
                        f"{mod.get('file', '?')}:{sig.get('line', '?')}",
                        f"Signal {sig_name} ({sig.get('type', '?')}, width={sig.get('width', '?')})"
                    )
                )

    return envelope(
        tool=tool,
        project=project,
        result={
            "signal_name": signal_name,
            "module_filter": module_filter,
            "matches": matches,
            "total_matches": len(matches),
            "elaborated": data.get("elaborated", False),
        },
        evidence=evidence_list,
        truncated=False,
        next_actions=["reg_find_fields_affecting_feature", "spec_search"],
    )


def rtl_get_instance_info(
    project: str,
    module_name: str | None = None,
    instance_path: str | None = None,
) -> dict[str, Any]:
    """Get module or instance details from the RTL index.

    Returns ports, signals, instances, parameters, and FSM states for a
    given module name or instance hierarchy path. At least one of
    module_name or instance_path must be provided.

    Args:
        project: Project ID or manifest path.
        module_name: Module name to look up (case-insensitive exact match).
        instance_path: Dot-separated instance path (e.g. 'u_dma.u_desc_parser').

    Returns:
        Envelope with module details: file, line_range, ports, signals,
        instances, fsm_states, and parameters.
    """
    tool = "rtl_get_instance_info"

    if module_name is None and instance_path is None:
        return error_envelope(
            tool, project,
            "At least one of module_name or instance_path must be provided",
        )

    try:
        reader = get_index_reader(project)
        data = reader.read(_RTL_INDEX)
    except (FileNotFoundError, IndexNotFoundError) as e:
        return error_envelope(tool, project, str(e))

    modules = data.get("modules", [])
    hierarchy = data.get("hierarchy", {})

    # --- Lookup by module_name ---
    if module_name is not None:
        mod_lower = module_name.lower()
        mod = next(
            (m for m in modules if m.get("name", "").lower() == mod_lower),
            None,
        )
        if mod is None:
            return error_envelope(
                tool, project, f"Module not found: {module_name}",
            )
        return _build_module_result(
            tool, project, mod, data.get("elaborated", False),
        )

    # --- Lookup by instance_path ---
    # Walk the hierarchy tree using dot-separated path
    parts = instance_path.split(".")  # type: ignore[union-attr]
    node: dict | None = hierarchy
    for part in parts:
        if not isinstance(node, dict):
            node = None
            break
        node = node.get(part)

    if node is None:
        return error_envelope(
            tool, project, f"Instance path not found: {instance_path}",
        )

    # If the node resolved to a dict that is a leaf (no children or is a
    # module name reference), try to find the corresponding module entry.
    # The hierarchy values may be nested dicts (sub-instances) or empty
    # dicts for leaves. We look up the module by the last path component
    # or by searching for a module that contains an instance with this name.
    last_part = parts[-1]
    target_module = None

    # First, check if any module has an instance named last_part
    for mod in modules:
        for inst in mod.get("instances", []):
            if inst.get("name", "").lower() == last_part.lower():
                inst_module = inst.get("module", "")
                target_module = next(
                    (m for m in modules if m.get("name") == inst_module),
                    None,
                )
                break
        if target_module:
            break

    # Fallback: try matching module name by last_part
    if target_module is None:
        target_module = next(
            (m for m in modules if m.get("name", "").lower() == last_part.lower()),
            None,
        )

    if target_module is None:
        return error_envelope(
            tool, project,
            f"Module for instance path not found: {instance_path}",
        )

    return _build_module_result(
        tool, project, target_module, data.get("elaborated", False),
    )


def rtl_get_source_snippet(
    project: str,
    signal_name: str,
    module_filter: str | None = None,
    context_lines: int = 5,
) -> dict[str, Any]:
    """Read source snippet for a signal definition.

    Finds the signal in the RTL index, then reads a bounded snippet from
    the source file using SourceResolver security boundaries.

    Args:
        project: Project ID or manifest path.
        signal_name: Signal name to locate.
        module_filter: Optional module name to restrict search.
        context_lines: Lines of context around the signal definition.

    Returns:
        Envelope with snippet content, file, and line range.
    """
    tool = "rtl_get_source_snippet"
    try:
        reader = get_index_reader(project)
        data = reader.read(_RTL_INDEX)
        manifest = get_manifest(project)
    except (FileNotFoundError, IndexNotFoundError) as e:
        return error_envelope(tool, project, str(e))

    modules = data.get("modules", [])
    search = signal_name.lower()

    # Find the signal definition
    target_file: str | None = None
    target_line: int | None = None
    target_module: str = ""

    for mod in modules:
        mod_name = mod.get("name", "")
        if module_filter and module_filter.lower() not in mod_name.lower():
            continue

        # Check signals (internal declarations)
        for sig in mod.get("signals", []):
            if sig.get("name", "").lower() == search:
                target_file = mod.get("file")
                target_line = sig.get("line")
                target_module = mod_name
                break

        if target_file:
            break

        # Check ports (line info from module line_range start)
        for port in mod.get("ports", []):
            if port.lower() == search:
                target_file = mod.get("file")
                target_line = mod.get("line_range", [1])[0]
                target_module = mod_name
                break

        if target_file:
            break

    if target_file is None or target_line is None:
        return error_envelope(
            tool, project,
            f"Signal not found in RTL index: {signal_name}",
        )

    # Use SourceResolver to read the snippet
    project_root = manifest.project_root
    resolver = SourceResolver(
        allowed_roots=[project_root],
        max_lines=40,
        max_bytes=4096,
    )
    snippet = resolver.resolve(
        source_file=target_file,
        source_line=target_line,
        context_lines=context_lines,
    )

    if snippet.status != "ok":
        return error_envelope(
            tool, project,
            f"Source read failed: {snippet.message}",
        )

    evidence_list = [
        rtl_evidence(
            target_module, signal_name,
            f"{snippet.file}:{snippet.start_line}-{snippet.end_line}",
            f"Source snippet for {signal_name}",
        ),
    ]

    return envelope(
        tool=tool,
        project=project,
        result={
            "signal_name": signal_name,
            "module": target_module,
            "file": snippet.file,
            "start_line": snippet.start_line,
            "end_line": snippet.end_line,
            "content": snippet.content,
            "source_mode": "real",
        },
        evidence=evidence_list,
        truncated=snippet.truncated,
        next_actions=["rtl_find_signal", "rtl_trace_fanin"],
    )


def rtl_trace_fanin(
    project: str,
    signal_name: str,
    module_filter: str | None = None,
) -> dict[str, Any]:
    """Trace same-module signals that may affect a target signal (mock stub).

    Returns other signals and ports in the same module as potential fan-in
    sources. Full cross-module fan-in tracing requires elaboration data
    and is not available in text-analysis mode.

    Args:
        project: Project ID or manifest path.
        signal_name: Signal name to trace fan-in for.
        module_filter: Optional module name to restrict search.

    Returns:
        Envelope with list of same-module signals and a stub note.
    """
    tool = "rtl_trace_fanin"
    try:
        reader = get_index_reader(project)
        data = reader.read(_RTL_INDEX)
    except (FileNotFoundError, IndexNotFoundError) as e:
        return error_envelope(tool, project, str(e))

    modules = data.get("modules", [])
    search = signal_name.lower()
    elaborated = data.get("elaborated", False)

    # Find the module containing the target signal
    target_module: dict | None = None
    for mod in modules:
        mod_name = mod.get("name", "")
        if module_filter and module_filter.lower() not in mod_name.lower():
            continue
        # Check signals
        for sig in mod.get("signals", []):
            if sig.get("name", "").lower() == search:
                target_module = mod
                break
        if target_module:
            break
        # Check ports
        for port in mod.get("ports", []):
            if port.lower() == search:
                target_module = mod
                break
        if target_module:
            break

    if target_module is None:
        return error_envelope(
            tool, project,
            f"Signal not found in RTL index: {signal_name}",
        )

    mod_name = target_module.get("name", "")

    # Collect same-module signals (excluding the target itself)
    fanin_signals: list[dict] = []
    for port in target_module.get("ports", []):
        if port.lower() != search:
            fanin_signals.append(
                {"signal_name": port, "signal_type": "port", "direction": "input"}
            )
    for sig in target_module.get("signals", []):
        if sig.get("name", "").lower() != search:
            fanin_signals.append(
                {
                    "signal_name": sig.get("name", ""),
                    "signal_type": sig.get("type", "unknown"),
                    "width": sig.get("width"),
                }
            )

    evidence_list = [
        rtl_evidence(
            mod_name, signal_name,
            target_module.get("file", ""),
            f"Fan-in trace for {signal_name} in {mod_name} "
            f"({len(fanin_signals)} same-module signals)",
        ),
    ]

    return envelope(
        tool=tool,
        project=project,
        result={
            "signal_name": signal_name,
            "module": mod_name,
            "file": target_module.get("file", ""),
            "fanin_signals": fanin_signals,
            "total_fanin": len(fanin_signals),
            "elaborated": elaborated,
            "note": (
                "Same-module fan-in only. "
                "Cross-module tracing requires elaborated netlist data."
                if not elaborated
                else "Full fan-in trace from elaborated netlist."
            ),
        },
        evidence=evidence_list,
        truncated=False,
        next_actions=["rtl_find_signal", "rtl_get_source_snippet"],
    )


def _build_module_result(
    tool: str,
    project: str,
    mod: dict,
    elaborated: bool,
) -> dict[str, Any]:
    """Build an envelope result for a module entry."""
    mod_name = mod.get("name", "")
    mod_file = mod.get("file", "")

    evidence_list = [
        rtl_evidence(
            mod_name, "", mod_file,
            f"Module {mod_name} ({len(mod.get('ports', []))} ports, "
            f"{len(mod.get('signals', []))} signals)",
        ),
    ]

    return envelope(
        tool=tool,
        project=project,
        result={
            "module": mod_name,
            "file": mod_file,
            "line_range": mod.get("line_range"),
            "ports": mod.get("ports", []),
            "signals": mod.get("signals", []),
            "instances": mod.get("instances", []),
            "fsm_states": mod.get("fsm_states", []),
            "parameters": mod.get("parameters", []),
            "elaborated": elaborated,
        },
        evidence=evidence_list,
        truncated=False,
        next_actions=["rtl_find_signal", "reg_find_field"],
    )

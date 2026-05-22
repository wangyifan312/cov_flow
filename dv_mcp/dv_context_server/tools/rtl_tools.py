"""RTL MCP tools — pure Python, no MCP runtime dependency.

Tools:
  - rtl_find_signal: find a signal in the RTL index by name
"""

from __future__ import annotations

from typing import Any

from dv_mcp.dv_context_server.indexes.readers import IndexNotFoundError
from dv_mcp.dv_context_server.services.evidence import rtl_evidence
from dv_mcp.dv_context_server.services.project_loader import get_index_reader
from dv_mcp.dv_context_server.services.summarizer import envelope, error_envelope

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
                    rtl_evidence(mod_name, port, f"{mod.get('file', '?')}", f"Port {port} in {mod_name}")
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

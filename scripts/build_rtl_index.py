#!/usr/bin/env python3
"""Build RTL index from SystemVerilog source files.

Reads the RTL filelist, parses modules using lib/sv_parser.py, extracts
additional signals and instances, and produces rtl_index.json compatible
with the MCP rtl_find_signal and rtl_get_instance_info tools.

Usage:
    python scripts/build_rtl_index.py --manifest mock_data/dma_subsystem/project_manifest.yaml
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from lib.manifest import Manifest, ManifestError
from lib.sv_parser import RE_MEMBER_VAR, extract_modules

# ---------------------------------------------------------------------------
# Instance extraction
# ---------------------------------------------------------------------------

# Matches: module_name [#(params)] instance_name ( ... )
# Avoids: module declarations, always blocks, if/for/case
RE_INSTANCE = re.compile(
    r"^\s*"
    r"(\w+)"  # module type name
    r"(?:\s*#\s*\([^)]*\))?"  # optional parameter override
    r"\s+"
    r"(\w+)"  # instance name
    r"\s*\(",
    re.MULTILINE,
)

# Keywords that look like module types but aren't
_SV_KEYWORDS: set[str] = {
    "module", "endmodule", "input", "output", "inout", "wire", "reg",
    "logic", "bit", "int", "integer", "byte", "shortint", "longint",
    "real", "string", "parameter", "localparam", "assign", "always",
    "always_ff", "always_comb", "always_latch", "initial", "final",
    "if", "else", "for", "foreach", "while", "do", "case", "casex",
    "casez", "begin", "end", "function", "task", "class", "interface",
    "typedef", "enum", "struct", "union", "generate", "genvar",
    "import", "package", "property", "assert", "cover", "restrict",
    "return", "break", "continue", "fork", "join", "join_any",
    "join_none", "wait", "disable", "force", "release",
}


def _extract_instances(
    mod_body: str,
    mod_start_line: int,
) -> list[dict]:
    """Extract module instances from a module body."""
    instances: list[dict] = []
    seen: set[str] = set()

    for m in RE_INSTANCE.finditer(mod_body):
        mod_type = m.group(1)
        inst_name = m.group(2)

        # Skip SV keywords and common non-module patterns
        if mod_type in _SV_KEYWORDS:
            continue
        # Skip if instance name is an SV keyword
        if inst_name in _SV_KEYWORDS:
            continue
        # Skip if it looks like a port declaration (input/output/inout before)
        prefix = mod_body[max(0, m.start() - 20): m.start()].strip()
        if any(kw in prefix for kw in ("input", "output", "inout", "parameter")):
            continue
        # Skip duplicates
        key = f"{mod_type}.{inst_name}"
        if key in seen:
            continue
        seen.add(key)

        line = mod_start_line + mod_body[: m.start()].count("\n")
        instances.append(
            {
                "module": mod_type,
                "name": inst_name,
                "line": line,
            }
        )

    return instances


def _extract_signals(
    mod_body: str,
    mod_start_line: int,
) -> list[dict]:
    """Extract internal signal declarations from a module body."""
    signals: list[dict] = []
    seen: set[str] = set()

    # Types that indicate non-declaration matches from RE_MEMBER_VAR
    skip_types: set[str] = {
        "assign", "else", "return", "break", "continue",
        "disable", "force", "release", "wait",
    }

    for m in RE_MEMBER_VAR.finditer(mod_body):
        type_name = m.group(1).strip()
        width_str = m.group(2)  # may be None
        var_name = m.group(3)

        # Skip non-declaration patterns
        if type_name in skip_types:
            continue
        # Skip parameters and non-signal types
        if type_name.startswith("parameter") or type_name.startswith("localparam"):
            continue
        if type_name.startswith("virtual"):
            continue
        # Skip if it looks like a port (would have been caught by port extraction)
        # Check preceding text for port direction
        prefix = mod_body[max(0, m.start() - 30): m.start()].strip()
        if any(kw in prefix for kw in ("input", "output", "inout")):
            continue

        if var_name in seen:
            continue
        seen.add(var_name)

        # Compute width from range string
        width = 1
        if width_str:
            # Parse "[15:0]" -> 16, "[3:0]" -> 4
            range_m = re.match(r"(\d+)\s*:\s*(\d+)", width_str)
            if range_m:
                high = int(range_m.group(1))
                low = int(range_m.group(2))
                width = abs(high - low) + 1

        line = mod_start_line + mod_body[: m.start()].count("\n")

        signals.append(
            {
                "name": var_name,
                "type": type_name,
                "width": width,
                "line": line,
            }
        )

    return signals


def _strip_port_direction(port_str: str) -> str:
    """Strip direction prefix from a port string.

    'input clk' -> 'clk'
    'output logic [31:0] data' -> 'data'
    """
    # The sv_parser returns "direction name" for ports
    parts = port_str.split()
    if len(parts) >= 2 and parts[0] in ("input", "output", "inout"):
        return parts[-1]
    return port_str


def _build_hierarchy(
    modules: list[dict],
    top_module_name: str | None = None,
) -> dict:
    """Build a hierarchy tree from module instance relationships.

    Returns a nested dict: {top_inst: {child_inst: {grandchild_inst: {}}}}
    """
    # Build a map: module_name -> list of instance dicts
    mod_instances: dict[str, list[dict]] = {}
    for mod in modules:
        mod_instances[mod["name"]] = mod.get("instances", [])

    # Find root modules (not instantiated by any other module)
    all_instance_types: set[str] = set()
    all_instance_names: set[str] = set()
    for mod in modules:
        for inst in mod.get("instances", []):
            all_instance_types.add(inst["module"])
            all_instance_names.add(inst["name"])

    mod_names = {mod["name"] for mod in modules}
    root_modules = mod_names - all_instance_types

    if not root_modules:
        # Fallback: use top_module_name or first module
        if top_module_name and top_module_name in mod_names:
            root_modules = {top_module_name}
        else:
            root_modules = {modules[0]["name"]} if modules else set()

    def _walk(mod_name: str) -> dict:
        children: dict = {}
        for inst in mod_instances.get(mod_name, []):
            child_mod = inst["module"]
            child_name = inst["name"]
            children[child_name] = _walk(child_mod)
        return children

    hierarchy: dict = {}
    for root in sorted(root_modules):
        # Use the module name as top-level instance name
        hierarchy[root] = _walk(root)

    return hierarchy


# ---------------------------------------------------------------------------
# Filelist parsing
# ---------------------------------------------------------------------------


def parse_filelist(filelist_path: Path) -> list[str]:
    """Parse a Verilog filelist (.f) file.

    Returns a list of file paths (relative to the filelist directory).
    Skips comments (lines starting with //) and blank lines.
    """
    entries: list[str] = []
    text = filelist_path.read_text(encoding="utf-8")
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("//") or stripped.startswith("/*"):
            continue
        # Strip inline comments
        if "//" in stripped:
            stripped = stripped[: stripped.index("//")].strip()
        entries.append(stripped)
    return entries


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build RTL index from SystemVerilog source files"
    )
    parser.add_argument(
        "--manifest", required=True, help="Path to project manifest YAML"
    )
    parser.add_argument(
        "--out", default=None, help="Output directory (default: manifest index_path)"
    )
    args = parser.parse_args()

    # Load manifest
    manifest_path = Path(args.manifest)
    try:
        manifest = Manifest.load(manifest_path)
    except ManifestError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    project_root = manifest.project_root

    # Read RTL filelist path from manifest
    filelist_str: str | None = manifest.get("rtl", "filelist")
    if not filelist_str:
        print("ERROR: manifest has no rtl.filelist", file=sys.stderr)
        return 1

    filelist_path = manifest.resolve_path(filelist_str)
    if filelist_path is None or not filelist_path.exists():
        print(f"ERROR: filelist not found: {filelist_path}", file=sys.stderr)
        return 1

    # Determine output directory
    index_path_str: str | None = manifest.get("rtl", "index_path")
    if args.out:
        out_dir = Path(args.out)
    elif index_path_str:
        out_dir = manifest.resolve_path(index_path_str) or (project_root / index_path_str)
    else:
        out_dir = project_root / ".dv_ai_index"
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"Building RTL index for project: {manifest.project}")
    print(f"  Filelist: {filelist_path}")
    print(f"  Output:   {out_dir}")

    # Parse filelist
    file_entries = parse_filelist(filelist_path)
    if not file_entries:
        print("WARNING: filelist is empty or has no valid entries", file=sys.stderr)

    filelist_dir = filelist_path.parent

    # Parse each SV file
    all_modules: list[dict] = []
    parsed_count = 0

    for entry in file_entries:
        sv_path = filelist_dir / entry
        if not sv_path.exists():
            # Try relative to project root
            sv_path = project_root / entry
        if not sv_path.exists():
            print(f"  WARNING: SV file not found: {entry}")
            continue

        sv_text = sv_path.read_text(encoding="utf-8", errors="replace")
        parsed_count += 1

        # Use sv_parser for basic module extraction
        parsed_modules = extract_modules(sv_text, file=entry)

        for mod in parsed_modules:
            # Strip port directions to get just port names
            port_names = [_strip_port_direction(p) for p in mod.ports]

            # Compute module body for signal/instance extraction
            mod_start = mod.line_range[0]
            mod_end = mod.line_range[1]
            lines = sv_text.split("\n")
            mod_body = "\n".join(lines[mod_start - 1: mod_end])

            # Extract signals and instances
            signals = _extract_signals(mod_body, mod_start)
            instances = _extract_instances(mod_body, mod_start)

            # Format parameters: sv_parser returns {type, name, default}
            # rtl_index uses {name, default}
            parameters = [
                {"name": p["name"], "default": p["default"]}
                for p in mod.parameters
            ]

            all_modules.append(
                {
                    "name": mod.name,
                    "file": entry,
                    "line_range": list(mod.line_range),
                    "ports": port_names,
                    "instances": instances,
                    "parameters": parameters,
                    "signals": signals,
                    "fsm_states": mod.fsm_states,
                }
            )

    # Build hierarchy tree
    hierarchy = _build_hierarchy(all_modules)

    # Build index
    index = {
        "schema_version": "rtl_index.v1",
        "source": "text_analysis",
        "elaborated": False,
        "modules": all_modules,
        "hierarchy": hierarchy,
    }

    out_file = out_dir / "rtl_index.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(index, f, indent=2, ensure_ascii=False)

    print(f"\nWrote: {out_file}")
    print(f"  SV files parsed: {parsed_count}")
    print(f"  modules:         {len(all_modules)}")
    total_signals = sum(len(m["signals"]) for m in all_modules)
    total_instances = sum(len(m["instances"]) for m in all_modules)
    total_fsm = sum(len(m["fsm_states"]) for m in all_modules)
    print(f"  signals:         {total_signals}")
    print(f"  instances:       {total_instances}")
    print(f"  FSM states:      {total_fsm}")
    for mod_entry in all_modules:
        print(
            f"    {mod_entry['name']}: {len(mod_entry['ports'])} ports, "
            f"{len(mod_entry['signals'])} signals, "
            f"{len(mod_entry['instances'])} instances, "
            f"{len(mod_entry['fsm_states'])} FSM states"
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())

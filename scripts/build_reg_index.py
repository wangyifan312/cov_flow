#!/usr/bin/env python3
"""Build register index from a YAML register definition file.

Reads YAML register definitions and produces reg_db.json compatible
with the MCP register tools (reg_find_field, reg_search_by_description, etc.).

Usage:
    python scripts/build_reg_index.py --manifest mock_data/dma_subsystem/project_manifest.yaml
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

from lib.manifest import Manifest, ManifestError


def _build_ral_path(block: str, register: str, field: str) -> str:
    """Build a RAL access path: ral.{block}.{register}.{field}."""
    return f"ral.{block}.{register}.{field}"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build register index from YAML register definitions"
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

    # Read register source path from manifest
    reg_source: dict = manifest.get("registers", "source") or {}
    source_type = reg_source.get("type", "yaml")
    reg_path_str: str | None = reg_source.get("path")
    if not reg_path_str:
        print("ERROR: manifest has no registers.source.path", file=sys.stderr)
        return 1

    if source_type != "yaml":
        print(
            f"WARNING: only 'yaml' source type supported, got '{source_type}'. "
            "Attempting YAML parse anyway.",
            file=sys.stderr,
        )

    reg_file = manifest.resolve_path(reg_path_str)
    if reg_file is None or not reg_file.exists():
        print(f"ERROR: register file not found: {reg_file}", file=sys.stderr)
        return 1

    # Determine output directory
    index_path_str: str | None = manifest.get("registers", "index_path")
    if args.out:
        out_dir = Path(args.out)
    elif index_path_str:
        out_dir = manifest.resolve_path(index_path_str) or (project_root / index_path_str)
    else:
        out_dir = project_root / ".dv_ai_index"
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"Building register index for project: {manifest.project}")
    print(f"  Register file: {reg_file}")
    print(f"  Output:        {out_dir}")

    # Parse YAML
    with open(reg_file, encoding="utf-8") as f:
        reg_data = yaml.safe_load(f)

    if not isinstance(reg_data, dict):
        print("ERROR: register YAML must be a mapping", file=sys.stderr)
        return 1

    block = str(reg_data.get("block", "UNKNOWN"))
    registers_in = reg_data.get("registers", [])

    # Build output registers
    registers_out: list[dict] = []
    total_fields = 0

    for reg in registers_in:
        reg_name = str(reg.get("register", ""))
        offset = str(reg.get("offset", "0x000"))
        fields_in = reg.get("fields", [])

        fields_out: list[dict] = []
        for fld in fields_in:
            field_name = str(fld.get("field", ""))
            ral_path = _build_ral_path(block, reg_name, field_name)

            fields_out.append(
                {
                    "field": field_name,
                    "bit_range": str(fld.get("bit_range", "[0]")),
                    "access": str(fld.get("access", "RW")),
                    "reset": str(fld.get("reset", "0")),
                    "description": str(fld.get("description", "")),
                    "ral_path": ral_path,
                    "feature_tags": list(fld.get("feature_tags", [])),
                }
            )

        total_fields += len(fields_out)
        registers_out.append(
            {
                "block": block,
                "register": reg_name,
                "offset": offset,
                "fields": fields_out,
            }
        )

    # Build index
    index = {
        "schema_version": "reg_db.v1",
        "registers": registers_out,
    }

    out_file = out_dir / "reg_db.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(index, f, indent=2, ensure_ascii=False)

    print(f"\nWrote: {out_file}")
    print(f"  registers: {len(registers_out)}")
    print(f"  fields:    {total_fields}")
    for reg in registers_out:
        print(f"    {reg['register']} @ {reg['offset']}: {len(reg['fields'])} fields")

    return 0


if __name__ == "__main__":
    sys.exit(main())

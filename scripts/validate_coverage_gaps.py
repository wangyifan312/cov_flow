#!/usr/bin/env python3
"""Validate coverage_gaps.json against its JSON Schema.

Usage:
    python scripts/validate_coverage_gaps.py \
        --manifest mock_data/dma_subsystem/project_manifest.yaml
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_SCRIPT_DIR = Path(__file__).parent
_PROJECT_ROOT = _SCRIPT_DIR.parent
sys.path.insert(0, str(_PROJECT_ROOT))

from lib.manifest import Manifest  # noqa: E402
from lib.schema_validator import load_schema, validate  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate coverage_gaps.json.")
    parser.add_argument("--manifest", required=True, help="Path to project_manifest.yaml")
    parser.add_argument("--out", default=None, help="Output path for validation report JSON")
    args = parser.parse_args()

    manifest = Manifest.load(args.manifest)
    gaps_path = manifest.base_dir / "coverage_gaps.json"

    if not gaps_path.exists():
        report = {
            "ok": False,
            "file": str(gaps_path),
            "errors": [{"path": "(file)", "message": f"File not found: {gaps_path}"}],
            "warnings": [],
            "summary": {"valid": False, "gaps_count": 0},
        }
        _output(report, args.out)
        return 1

    with open(gaps_path, encoding="utf-8") as f:
        data = json.load(f)

    schema = load_schema("coverage_gap.schema.json")
    errors = []
    warnings = []

    # Validate top-level structure
    if not isinstance(data, dict):
        errors.append({"path": "(root)", "message": "coverage_gaps.json must be a JSON object"})
    else:
        # Validate each gap against the schema
        gaps = data.get("gaps", [])
        if not isinstance(gaps, list):
            errors.append({"path": "gaps", "message": "'gaps' must be an array"})
        else:
            for i, gap in enumerate(gaps):
                gap_errors = validate(gap, schema, raise_on_error=False)
                for e in gap_errors:
                    e["path"] = f"gaps[{i}].{e['path']}"
                    errors.append(e)

    # Check for duplicate gap_ids
    if isinstance(data, dict):
        gap_ids = [g.get("gap_id") for g in data.get("gaps", []) if isinstance(g, dict)]
        seen = set()
        for gid in gap_ids:
            if gid in seen:
                warnings.append({"type": "duplicate_gap_id", "gap_id": gid})
            seen.add(gid)

    ok = len(errors) == 0
    report = {
        "ok": ok,
        "file": str(gaps_path),
        "errors": errors,
        "warnings": warnings,
        "summary": {
            "valid": ok,
            "gaps_count": len(data.get("gaps", [])) if isinstance(data, dict) else 0,
            "unique_gap_ids": len(set(
                g.get("gap_id") for g in data.get("gaps", [])
                if isinstance(g, dict) and isinstance(data, dict)
            )) if isinstance(data, dict) else 0,
        },
    }
    _output(report, args.out)
    return 0 if ok else 1


def _output(report: dict, out_path: str | None) -> None:
    text = json.dumps(report, indent=2, ensure_ascii=False)
    if out_path:
        Path(out_path).parent.mkdir(parents=True, exist_ok=True)
        Path(out_path).write_text(text, encoding="utf-8")
        print(f"Report written to {out_path}")
    else:
        print(text)


if __name__ == "__main__":
    sys.exit(main())

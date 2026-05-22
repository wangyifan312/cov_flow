#!/usr/bin/env python3
"""Validate a scenario card file against its JSON Schema.

Usage:
    python scripts/validate_scenario_card.py --file path/to/scenario_card.json
    python scripts/validate_scenario_card.py --file path/to/scenario_card.yaml --out report.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_SCRIPT_DIR = Path(__file__).parent
_PROJECT_ROOT = _SCRIPT_DIR.parent
sys.path.insert(0, str(_PROJECT_ROOT))

from lib.schema_validator import load_schema, validate


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a scenario card file.")
    parser.add_argument("--file", required=True, help="Path to scenario card JSON/YAML file")
    parser.add_argument("--out", default=None, help="Output path for validation report JSON")
    parser.add_argument("--schemas-dir", default=None, help="Override schemas directory")
    args = parser.parse_args()

    file_path = Path(args.file)
    schemas_dir = Path(args.schemas_dir) if args.schemas_dir else None

    if not file_path.exists():
        report = {
            "ok": False,
            "file": str(file_path),
            "errors": [{"path": "(file)", "message": f"File not found: {file_path}"}],
            "warnings": [],
            "summary": {"valid": False},
        }
        _output(report, args.out)
        return 1

    # Load the data file
    with open(file_path, "r", encoding="utf-8") as f:
        if file_path.suffix in (".yaml", ".yml"):
            import yaml
            data = yaml.safe_load(f)
        else:
            data = json.load(f)

    # Load schema and validate
    schema = load_schema("scenario_card.schema.json", schemas_dir)
    errors = validate(data, schema, raise_on_error=False)

    ok = len(errors) == 0
    report = {
        "ok": ok,
        "file": str(file_path),
        "errors": errors,
        "warnings": [],
        "summary": {"valid": ok},
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

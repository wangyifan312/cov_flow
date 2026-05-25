#!/usr/bin/env python3
"""Coverage diff: compare before/after coverage databases and report gap deltas.

Usage:
    python scripts/coverage_diff.py --before db_before.json --after db_after.json
    python scripts/coverage_diff.py --before db_before.json --after db_after.json --gap-id GAP_0001
    python scripts/coverage_diff.py --before db_before.json --after db_after.json --out diff.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_SCRIPT_DIR = Path(__file__).parent
_PROJECT_ROOT = _SCRIPT_DIR.parent
sys.path.insert(0, str(_PROJECT_ROOT))

from lib.coverage_diff import compute_diff


def main() -> int:
    parser = argparse.ArgumentParser(description="Coverage diff: compare before/after databases.")
    parser.add_argument("--before", required=True, help="Path to coverage DB before JSON")
    parser.add_argument("--after", required=True, help="Path to coverage DB after JSON")
    parser.add_argument("--gap-id", default=None, help="Filter to a specific gap ID")
    parser.add_argument("--out", default=None, help="Output path for diff report JSON")
    args = parser.parse_args()

    before_path = Path(args.before)
    after_path = Path(args.after)

    if not before_path.exists():
        report = {"ok": False, "error": f"Before file not found: {before_path}"}
        _output(report, args.out)
        return 1

    if not after_path.exists():
        report = {"ok": False, "error": f"After file not found: {after_path}"}
        _output(report, args.out)
        return 1

    with open(before_path, "r", encoding="utf-8") as f:
        before = json.load(f)
    with open(after_path, "r", encoding="utf-8") as f:
        after = json.load(f)

    result = compute_diff(before, after, gap_id_filter=args.gap_id)
    _output(result, args.out)
    return 0


def _output(data: dict, out_path: str | None) -> None:
    text = json.dumps(data, indent=2, ensure_ascii=False)
    if out_path:
        Path(out_path).parent.mkdir(parents=True, exist_ok=True)
        Path(out_path).write_text(text, encoding="utf-8")
        print(f"Report written to {out_path}")
    else:
        print(text)


if __name__ == "__main__":
    sys.exit(main())

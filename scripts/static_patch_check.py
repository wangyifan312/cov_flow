#!/usr/bin/env python3
"""Static patch check: validate patch metadata references against project indexes.

Performs deterministic checks on a patch metadata file without requiring
MCP runtime or simulation execution.

Usage:
    python scripts/static_patch_check.py --file patch.json --manifest manifest.yaml
    python scripts/static_patch_check.py --file patch.json --manifest manifest.yaml \
        --out report.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_SCRIPT_DIR = Path(__file__).parent
_PROJECT_ROOT = _SCRIPT_DIR.parent
sys.path.insert(0, str(_PROJECT_ROOT))

from lib.index_paths import INDEX_DIR_NAME  # noqa: E402
from lib.manifest import Manifest, ManifestError  # noqa: E402


def _check_new_files(patch: dict, base_dir: Path) -> list[dict]:
    """Check that new_files paths are plausible new file locations."""
    checks = []
    for file_path_str in patch.get("new_files", []):
        file_path = Path(file_path_str)
        resolved = base_dir / file_path
        parent_exists = resolved.parent.exists() or file_path.suffix == ".sv"
        checks.append({
            "check": "new_file_path",
            "target": file_path_str,
            "passed": True,
            "warning": None if parent_exists else f"Parent dir does not exist: {resolved.parent}",
            "message": f"New file: {file_path_str}",
        })
    return checks


def _check_modified_files(patch: dict, base_dir: Path) -> list[dict]:
    """Check that modified_files paths exist in the project."""
    checks = []
    for file_path_str in patch.get("modified_files", []):
        resolved = base_dir / file_path_str
        exists = resolved.exists()
        checks.append({
            "check": "modified_file_exists",
            "target": file_path_str,
            "passed": exists,
            "message": f"File exists: {exists}" if exists else f"File not found: {resolved}",
        })
    return checks


def _check_base_test(patch: dict, tb_index: dict) -> list[dict]:
    """Check that base_reuse.base_test exists in tb_index."""
    checks: list[dict] = []
    base_test = patch.get("base_reuse", {}).get("base_test")
    if not base_test:
        return checks

    test_names = [t["name"] for t in tb_index.get("base_tests", [])]
    found = base_test in test_names
    if found:
        msg = f"Found in tb_index: {found}"
    else:
        msg = (
            f"base_test '{base_test}' not in tb_index base_tests: "
            f"{test_names}"
        )
    checks.append({
        "check": "base_test_in_index",
        "target": base_test,
        "passed": found,
        "message": msg,
    })
    return checks


def _check_base_sequence(patch: dict, tb_index: dict) -> list[dict]:
    """Check that base_reuse.base_sequence exists in tb_index."""
    checks: list[dict] = []
    base_seq = patch.get("base_reuse", {}).get("base_sequence")
    if not base_seq:
        return checks

    seq_names = [s["name"] for s in tb_index.get("sequences", [])]
    found = base_seq in seq_names
    if found:
        msg = f"Found in tb_index: {found}"
    else:
        msg = (
            f"base_sequence '{base_seq}' not in tb_index sequences: "
            f"{seq_names}"
        )
    checks.append({
        "check": "base_sequence_in_index",
        "target": base_seq,
        "passed": found,
        "message": msg,
    })
    return checks


def _check_coverage_targets(patch: dict) -> list[dict]:
    """Check that coverage_target entries have valid dot-separated format (≥3 segments)."""
    checks: list[dict] = []
    for target in patch.get("coverage_target", []):
        parts = target.split(".")
        valid = len(parts) >= 3 and all(p for p in parts)
        if valid:
            msg = f"Format valid (≥3 segments): {valid}"
        else:
            msg = (
                f"Invalid format '{target}': expected "
                f"covergroup.coverpoint.bin (≥3 dot-separated segments)"
            )
        checks.append({
            "check": "coverage_target_format",
            "target": target,
            "passed": valid,
            "message": msg,
        })
    return checks


def _check_review_checklist(patch: dict) -> list[dict]:
    """Check that review_checklist is non-empty."""
    checklist = patch.get("review_checklist", [])
    passed = len(checklist) > 0
    if passed:
        msg = f"Checklist has {len(checklist)} item(s)"
    else:
        msg = "review_checklist is empty"
    return [{
        "check": "review_checklist_non_empty",
        "target": "review_checklist",
        "passed": passed,
        "message": msg,
    }]


def run_checks(
    patch: dict,
    base_dir: Path,
    tb_index: dict,
) -> list[dict]:
    """Run all static checks and return a list of check results."""
    checks: list[dict] = []
    checks.extend(_check_new_files(patch, base_dir))
    checks.extend(_check_modified_files(patch, base_dir))
    checks.extend(_check_base_test(patch, tb_index))
    checks.extend(_check_base_sequence(patch, tb_index))
    checks.extend(_check_coverage_targets(patch))
    checks.extend(_check_review_checklist(patch))
    return checks


def main() -> int:
    parser = argparse.ArgumentParser(description="Static patch check: validate patch references.")
    parser.add_argument("--file", required=True, help="Path to patch metadata JSON file")
    parser.add_argument("--manifest", required=True, help="Path to project_manifest.yaml")
    parser.add_argument("--out", default=None, help="Output path for check report JSON")
    args = parser.parse_args()

    # Load manifest
    try:
        manifest = Manifest.load(args.manifest)
    except ManifestError as e:
        report = {
            "ok": False,
            "tool": "static_patch_check",
            "checks": [],
            "summary": {"total": 0, "passed": 0, "failed": 0},
            "error": f"Manifest error: {e}",
        }
        _output(report, args.out)
        return 1

    # Load patch file
    patch_path = Path(args.file)
    if not patch_path.exists():
        report = {
            "ok": False,
            "tool": "static_patch_check",
            "checks": [],
            "summary": {"total": 0, "passed": 0, "failed": 0},
            "error": f"Patch file not found: {patch_path}",
        }
        _output(report, args.out)
        return 1

    with open(patch_path, encoding="utf-8") as f:
        patch = json.load(f)

    # Load tb_index
    tb_index_path = manifest.base_dir / INDEX_DIR_NAME / "tb_index.json"
    if not tb_index_path.exists():
        report = {
            "ok": False,
            "tool": "static_patch_check",
            "checks": [],
            "summary": {"total": 0, "passed": 0, "failed": 0},
            "error": f"tb_index.json not found: {tb_index_path}. Run 'make build-indexes'.",
        }
        _output(report, args.out)
        return 1

    with open(tb_index_path, encoding="utf-8") as f:
        tb_index = json.load(f)

    # Run checks
    checks = run_checks(patch, manifest.base_dir, tb_index)

    passed_count = sum(1 for c in checks if c["passed"])
    failed_count = len(checks) - passed_count
    all_passed = failed_count == 0

    report = {
        "ok": all_passed,
        "tool": "static_patch_check",
        "checks": checks,
        "summary": {
            "total": len(checks),
            "passed": passed_count,
            "failed": failed_count,
        },
    }
    _output(report, args.out)
    return 0 if all_passed else 1


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

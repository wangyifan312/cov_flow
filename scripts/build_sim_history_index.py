#!/usr/bin/env python3
"""Build simulation history index from sim_results/ directory.

Scans simulation result directories, aggregates test pass/fail status and
coverage gap hit history with trend analysis.

Usage:
    python scripts/build_sim_history_index.py \
        --manifest mock_data/dma_subsystem/project_manifest.yaml
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path

from lib.manifest import Manifest, ManifestError

# ---------------------------------------------------------------------------
# Sim result parsing
# ---------------------------------------------------------------------------

# Directory name pattern: {test_name}_{seed}
RE_TEST_DIR = re.compile(r"^(.+?)_(\d+)$")


def _parse_test_dir_name(dirname: str) -> tuple[str, int] | None:
    """Parse a sim result directory name into (test_name, seed).

    Examples:
        'dma_test_1_42' -> ('dma_test_1', 42)
        'basic_test_1'  -> ('basic_test', 1)
    """
    m = RE_TEST_DIR.match(dirname)
    if m:
        return m.group(1), int(m.group(2))
    return None


def _load_sim_result(result_path: Path) -> dict | None:
    """Load a sim_result.json file. Returns None if not found or invalid."""
    if not result_path.exists():
        return None
    try:
        with open(result_path, encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return data
    except (json.JSONDecodeError, OSError):
        return None
    return None


def _load_coverage_gaps(gaps_path: Path) -> list[dict]:
    """Load a coverage_gaps.json file. Returns empty list on failure."""
    if not gaps_path.exists():
        return []
    try:
        with open(gaps_path, encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return list(data.get("gaps", []))
        if isinstance(data, list):
            return data
    except (json.JSONDecodeError, OSError):
        return []
    return []


# ---------------------------------------------------------------------------
# Trend calculation
# ---------------------------------------------------------------------------


def _compute_trend(hit_counts: list[int]) -> str:
    """Compute coverage trend from a sequence of hit counts.

    Rules:
        - "never_covered": all hit_counts are 0
        - "regressing": last value is 0 but earlier values were >0
        - "improving": hit_count goes from 0 to >0, or monotonically increases
        - "stable": hit_count stays the same (and >0)
    """
    if not hit_counts:
        return "never_covered"

    all_zero = all(h == 0 for h in hit_counts)
    if all_zero:
        return "never_covered"

    last = hit_counts[-1]
    first_nonzero = next((h for h in hit_counts if h > 0), None)

    # Check regression: was covered, now 0
    if last == 0 and first_nonzero is not None:
        return "regressing"

    # Check improving: started at 0 and went to >0, or monotonically increasing
    if hit_counts[0] == 0 and last > 0:
        return "improving"

    # Check monotonic increase
    increasing = all(
        hit_counts[i] <= hit_counts[i + 1] for i in range(len(hit_counts) - 1)
    )
    if increasing and hit_counts[-1] > hit_counts[0]:
        return "improving"

    # Stable: values don't change (and >0)
    all_same = all(h == hit_counts[0] for h in hit_counts)
    if all_same:
        return "stable"

    # Default: if last value > 0 and not strictly monotonic, call it stable
    return "stable"


def _find_first_covered(
    hit_records: list[dict],
) -> str | None:
    """Find the first test+seed where hit_count > 0.

    Returns a string like 'test_name seed=42', or None.
    """
    for rec in hit_records:
        if rec.get("hit_count", 0) > 0:
            return f"{rec['test']} seed={rec['seed']}"
    return None


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build simulation history index from sim_results/ directory"
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

    # Resolve sim_results_root
    results_root_str = manifest.get("simulation", "results_root") or "sim_results"
    results_root = manifest.resolve_path(str(results_root_str))
    if results_root is None or not results_root.exists():
        print(f"ERROR: sim results root not found: {results_root}", file=sys.stderr)
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

    print(f"Building sim history index for project: {manifest.project}")
    print(f"  Results root: {results_root}")
    print(f"  Output:       {out_dir}")

    # -----------------------------------------------------------------------
    # Scan sim result directories
    # -----------------------------------------------------------------------
    tests: list[dict] = []
    # gap_id -> ordered list of {test, seed, hit_count}
    gap_hits: dict[str, list[dict]] = {}

    result_dirs = sorted(
        d for d in results_root.iterdir() if d.is_dir()
    )

    for sim_dir in result_dirs:
        parsed = _parse_test_dir_name(sim_dir.name)
        if parsed is None:
            continue
        test_name, seed = parsed

        # Load sim_result.json
        sim_result = _load_sim_result(sim_dir / "sim_result.json")
        if sim_result is None:
            continue

        test_entry = {
            "test": sim_result.get("test", test_name),
            "seed": sim_result.get("seed", seed),
            "compile_status": sim_result.get("compile_status", "unknown"),
            "sim_status": sim_result.get("sim_status", "unknown"),
            "duration_seconds": sim_result.get("duration_seconds", 0.0),
            "log_path": sim_result.get(
                "log_path",
                f"sim_results/{sim_dir.name}/run.log",
            ),
        }
        tests.append(test_entry)

        # Load coverage_gaps.json from urg_report/ subdirectory
        gaps_file = sim_dir / "urg_report" / "coverage_gaps.json"
        gaps = _load_coverage_gaps(gaps_file)
        for gap in gaps:
            gap_id = gap.get("gap_id")
            if not gap_id:
                continue
            hit_count = gap.get("hit_count", 0)
            if gap_id not in gap_hits:
                gap_hits[gap_id] = []
            gap_hits[gap_id].append({
                "test": test_name,
                "seed": seed,
                "hit_count": hit_count,
            })

    # -----------------------------------------------------------------------
    # Build gap_history
    # -----------------------------------------------------------------------
    gap_history: list[dict] = []
    for gap_id in sorted(gap_hits.keys()):
        records = gap_hits[gap_id]
        hit_counts = [r["hit_count"] for r in records]
        trend = _compute_trend(hit_counts)
        first_covered = _find_first_covered(records)

        gap_history.append({
            "gap_id": gap_id,
            "hit_history": records,
            "trend": trend,
            "first_covered": first_covered,
        })

    # -----------------------------------------------------------------------
    # Build and write index
    # -----------------------------------------------------------------------
    index: dict = {
        "schema_version": "sim_history.v1",
        "generated_at": datetime.now(UTC).isoformat(),
        "project": manifest.project,
        "total_simulations": len(tests),
        "tests": tests,
        "gap_history": gap_history,
    }

    out_file = out_dir / "sim_history.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(index, f, indent=2, ensure_ascii=False)

    print(f"\nWrote: {out_file}")
    print(f"  tests:          {len(tests)}")
    print(f"  gap_history:    {len(gap_history)}")
    trends: dict[str, int] = {}
    for g in gap_history:
        trends[g["trend"]] = trends.get(g["trend"], 0) + 1
    for trend, count in sorted(trends.items()):
        print(f"    {trend}: {count}")

    return 0


if __name__ == "__main__":
    sys.exit(main())

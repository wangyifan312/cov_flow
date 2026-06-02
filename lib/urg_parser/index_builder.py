"""Build coverage index and gaps JSON files from parsed URG data."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from lib.urg_parser.structure import GroupInfo, ModuleInfo


def build_coverage_index(
    project: str,
    report_id: str,
    report_dir: Path,
    modules: list[ModuleInfo],
    groups: list[GroupInfo],
    gaps: list[dict],
    metrics: dict | None = None,
) -> dict:
    """Build the coverage_index.json structure.

    Output is compatible with both:
    - MCP tools (coverage_tools.py reads data["gaps"])
    - Mock project format (generate_mock_index.py:generate_coverage_index)
    """
    # Count gaps by type
    gap_counts: dict[str, int] = {}
    for gap in gaps:
        cov_type = gap.get("coverage_type", "unknown")
        gap_counts[cov_type] = gap_counts.get(cov_type, 0) + 1

    # Collect unique cluster IDs
    clusters: list[str] = sorted({
        g.get("cluster_id", "unknown")
        for g in gaps
        if g.get("cluster_id")
    })

    # Build module summaries
    module_summaries: list[dict] = []
    for mod in modules:
        coverage_types_list: list[dict] = []
        summary: dict = {
            "name": mod.name,
            "mod_file": mod.mod_file,
            "score": mod.score,
            "coverage_types": coverage_types_list,
        }
        if mod.line_score is not None:
            summary["coverage_types"].append(
                {"type": "line", "score": mod.line_score}
            )
        if mod.cond_score is not None:
            summary["coverage_types"].append(
                {"type": "condition", "score": mod.cond_score}
            )
        if mod.toggle_score is not None:
            summary["coverage_types"].append(
                {"type": "toggle", "score": mod.toggle_score}
            )
        if mod.fsm_score is not None:
            summary["coverage_types"].append(
                {"type": "fsm", "score": mod.fsm_score}
            )
        if mod.branch_score is not None:
            summary["coverage_types"].append(
                {"type": "branch", "score": mod.branch_score}
            )
        if mod.assert_score is not None:
            summary["coverage_types"].append(
                {"type": "assert", "score": mod.assert_score}
            )
        module_summaries.append(summary)

    # Build group summaries
    group_summaries = []
    for grp in groups:
        group_summaries.append({
            "name": grp.name,
            "grp_file": grp.grp_file,
            "score": grp.score,
            "instances": grp.instances,
        })

    return {
        "project": project,
        "report_id": report_id,
        "schema_version": "coverage_index.v1",
        "report_dir": str(report_dir),
        "generated_at": datetime.now().isoformat(),
        "metrics": metrics or {},
        "summary": {
            "total_modules": len(modules),
            "total_groups": len(groups),
            "total_gaps": len(gaps),
            "gap_counts_by_type": gap_counts,
        },
        "gaps": gaps,
        "total_gaps": len(gaps),
        "clusters": clusters,
        "modules": module_summaries,
        "groups": group_summaries,
    }


def build_coverage_gaps(gaps: list[dict], project: str, report_id: str) -> dict:
    """Build the coverage_gaps.json structure.

    Gaps are already schema-compliant from gap_assembler, so just wrap them.
    """
    return {
        "project": project,
        "report_id": report_id,
        "generated_at": datetime.now().isoformat(),
        "gaps": gaps,
    }


def write_index_files(
    output_dir: Path,
    index: dict,
    gaps: dict,
) -> tuple[Path, Path]:
    """Write coverage_index.json and coverage_gaps.json to output directory."""
    output_dir.mkdir(parents=True, exist_ok=True)

    index_path = output_dir / "coverage_index.json"
    gaps_path = output_dir / "coverage_gaps.json"

    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(index, f, indent=2, ensure_ascii=False)

    with open(gaps_path, "w", encoding="utf-8") as f:
        json.dump(gaps, f, indent=2, ensure_ascii=False)

    return index_path, gaps_path

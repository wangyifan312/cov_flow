"""Coverage diff computation: compare before/after databases and report gap deltas.

Shared between scripts/coverage_diff.py (CLI) and dv_mcp tools (cov_get_coverage_diff).
"""

from __future__ import annotations


def _gap_identifier(gap: dict) -> dict:
    """Extract type-specific identifier fields from a gap entry."""
    cov_type = gap.get("coverage_type", "functional")
    if cov_type == "functional":
        return {
            "covergroup": gap.get("covergroup", ""),
            "coverpoint": gap.get("coverpoint", ""),
            "bin": gap.get("bin", ""),
        }
    elif cov_type == "line":
        return {
            "source_file": gap.get("source_file", ""),
            "source_line": gap.get("source_line", 0),
        }
    elif cov_type == "branch":
        return {
            "source_file": gap.get("source_file", ""),
            "source_line": gap.get("source_line", 0),
            "branch_type": gap.get("branch_type", ""),
            "direction": gap.get("direction", ""),
        }
    elif cov_type == "condition":
        return {
            "source_file": gap.get("source_file", ""),
            "source_line": gap.get("source_line", 0),
            "condition_expr": gap.get("condition_expr", ""),
        }
    elif cov_type == "toggle":
        return {
            "signal": gap.get("signal", ""),
            "module": gap.get("module", ""),
            "toggle_dir": gap.get("toggle_dir", ""),
        }
    elif cov_type == "fsm":
        return {
            "module": gap.get("module", ""),
            "fsm_name": gap.get("fsm_name", ""),
            "state": gap.get("state", ""),
        }
    elif cov_type == "assert":
        return {
            "assert_name": gap.get("assert_name", ""),
            "source_file": gap.get("source_file", ""),
        }
    return {}


def compute_diff(
    before: dict,
    after: dict,
    gap_id_filter: str | None = None,
) -> dict:
    """Compute coverage diff between before and after databases.

    Returns a structured diff report with gap deltas and summary.
    """
    before_gaps = {g["gap_id"]: g for g in before.get("gaps", [])}
    after_gaps = {g["gap_id"]: g for g in after.get("gaps", [])}

    all_gap_ids = sorted(set(before_gaps.keys()) | set(after_gaps.keys()))

    if gap_id_filter:
        all_gap_ids = [gid for gid in all_gap_ids if gid == gap_id_filter]

    gap_deltas = []
    newly_covered = 0
    regressed = 0
    unchanged = 0

    for gid in all_gap_ids:
        before_hit = before_gaps.get(gid, {}).get("hit_count", 0)
        after_hit = after_gaps.get(gid, {}).get("hit_count", 0)

        before_entry = before_gaps.get(gid, {})
        after_entry = after_gaps.get(gid, after_entry if (after_entry := before_entry) else {})

        closed = after_hit > 0 and before_hit == 0
        is_regressed = after_hit < before_hit
        is_unchanged = after_hit == before_hit

        if closed:
            newly_covered += 1
        elif is_regressed:
            regressed += 1
        elif is_unchanged:
            unchanged += 1

        ref_entry = after_entry if after_entry.get("coverage_type") else before_entry
        identifier = _gap_identifier(ref_entry)
        delta = {
            "gap_id": gid,
            "coverage_type": after_entry.get(
                "coverage_type", before_entry.get("coverage_type", "functional"),
            ),
            "before_hit_count": before_hit,
            "after_hit_count": after_hit,
            "closed": closed,
            **identifier,
        }
        if is_regressed:
            delta["regressed"] = True

        gap_deltas.append(delta)

    all_types = set(d.get("coverage_type", "functional") for d in gap_deltas)
    by_type: dict[str, dict[str, int]] = {}
    for cov_type in sorted(all_types):
        type_deltas = [
            d for d in gap_deltas if d.get("coverage_type", "functional") == cov_type
        ]
        by_type[cov_type] = {
            "total": len(type_deltas),
            "newly_covered": sum(1 for d in type_deltas if d.get("closed")),
            "regressed": sum(1 for d in type_deltas if d.get("regressed")),
            "unchanged": sum(
                1 for d in type_deltas if not d.get("closed") and not d.get("regressed")
            ),
        }

    return {
        "ok": True,
        "tool": "coverage_diff",
        "before_report_id": before.get("report_id", ""),
        "after_report_id": after.get("report_id", ""),
        "gap_deltas": gap_deltas,
        "summary": {
            "total_gaps": len(gap_deltas),
            "newly_covered": newly_covered,
            "regressed": regressed,
            "unchanged": unchanged,
            "by_type": by_type,
        },
    }

"""Coverage diff computation: compare before/after databases and report gap deltas.

Shared between scripts/coverage_diff.py (CLI) and dv_mcp tools (cov_get_coverage_diff).
"""

from __future__ import annotations


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

        delta = {
            "gap_id": gid,
            "before_hit_count": before_hit,
            "after_hit_count": after_hit,
            "closed": closed,
            "covergroup": after_entry.get("covergroup", before_entry.get("covergroup", "")),
            "coverpoint": after_entry.get("coverpoint", before_entry.get("coverpoint", "")),
            "bin": after_entry.get("bin", before_entry.get("bin", "")),
        }
        if is_regressed:
            delta["regressed"] = True

        gap_deltas.append(delta)

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
        },
    }

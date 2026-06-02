"""Assemble coverage gaps from parsed URG data into structured output.

All output gaps conform to schemas/coverage_gap.schema.json.
"""

from __future__ import annotations

import os

# All fields allowed by coverage_gap.schema.json
ALLOWED_FIELDS: set[str] = {
    # Common required
    "gap_id", "coverage_type", "hit_count", "goal",
    # Functional required
    "covergroup", "coverpoint", "bin",
    # Line/Branch/Condition/Assert required
    "source_file", "source_line",
    # Branch required
    "branch_type", "direction",
    # Condition required
    "condition_expr", "combination",
    # Toggle required
    "signal", "toggle_dir", "module",
    # FSM required
    "fsm_name", "state", "transition",
    # Assert required
    "assert_name", "fail_count", "vacuous",
    # Optional
    "cluster_id", "classification", "priority",
    "related_register", "related_spec_section", "related_rtl_signal",
}


def assemble_gaps(
    functional_gaps: list[dict],
    code_coverage_gaps: list[dict],
    project_root: str | None = None,
) -> list[dict]:
    """Assemble and normalize coverage gaps from multiple sources.

    Assigns gap_ids:
        - Functional: GAP_0001, GAP_0002, ...
        - Line: GAP_L001, GAP_L002, ...
        - Branch: GAP_B001, GAP_B002, ...
        - Condition: GAP_C001, GAP_C002, ...
        - Toggle: GAP_T001, GAP_T002, ...
        - FSM: GAP_M001, GAP_M002, ...
        - Assert: GAP_A001, GAP_A002, ...
    """
    all_gaps: list[dict] = []

    # Process functional gaps
    for i, gap in enumerate(functional_gaps, start=1):
        gap_id = f"GAP_{i:04d}"
        normalized = _normalize_gap(gap, gap_id, project_root)
        all_gaps.append(normalized)

    # Process code coverage gaps by type
    type_prefixes = {
        "line": "L",
        "branch": "B",
        "condition": "C",
        "toggle": "T",
        "fsm": "M",
        "assert": "A",
    }
    counters: dict[str, int] = {t: 1 for t in type_prefixes}

    for gap in code_coverage_gaps:
        cov_type = gap.get("coverage_type", "")
        prefix = type_prefixes.get(cov_type, "X")
        counter = counters.get(cov_type, 1)
        gap_id = f"GAP_{prefix}{counter:03d}"
        counters[cov_type] = counter + 1

        normalized = _normalize_gap(gap, gap_id, project_root)
        all_gaps.append(normalized)

    return all_gaps


def _normalize_gap(gap: dict, gap_id: str, project_root: str | None) -> dict:
    """Normalize a gap dict with gap_id and standardized fields."""
    result = dict(gap)
    result["gap_id"] = gap_id

    # Normalize source file path
    source_file = result.get("source_file")
    if source_file and project_root:
        result["source_file"] = _normalize_path(source_file, project_root)

    # Remove empty source_file (toggle type doesn't have it)
    if not result.get("source_file"):
        result.pop("source_file", None)

    cov_type = result.get("coverage_type", "functional")

    # Fill classification (optional field)
    if "classification" not in result:
        result["classification"] = _default_classification(cov_type)

    # Fill priority (optional field)
    if "priority" not in result:
        result["priority"] = _compute_priority(cov_type)

    # Fill cluster_id (optional field)
    if "cluster_id" not in result:
        if cov_type == "functional":
            result["cluster_id"] = result.get("covergroup", "unknown")
        else:
            result["cluster_id"] = result.get("module", "unknown")

    # Remove all non-schema fields
    result = {k: v for k, v in result.items() if k in ALLOWED_FIELDS}

    return result


def _normalize_path(path: str, project_root: str) -> str:
    """Normalize a path relative to project root.

    Handles paths like:
    - /root/project_x2h/.../sim/../dut/.../file.sv → dut/.../file.sv
    - /root/project_x2h/.../env/file.sv → env/file.sv
    - /root/project_x2h/.../tb/file.sv → tb/file.sv

    Strategy:
    1. Resolve ".." segments with normpath
    2. If absolute and starts with project_root, make relative
    3. Otherwise, look for common project subdirs (sim, dut, tb, env) and extract from there
    4. Fallback to basename
    """
    if not path:
        return path

    # Step 1: Resolve ".." segments
    normalized = os.path.normpath(path)

    # Step 2: If absolute, make relative to project_root
    if os.path.isabs(normalized) and project_root:
        project_root_norm = os.path.normpath(project_root)
        if normalized.startswith(project_root_norm):
            return os.path.relpath(normalized, project_root_norm)

        # Step 3: Look for common project subdirectories in the path
        # Match patterns like /sim/../dut/ or /tb/ or /env/
        # Extract everything from the first occurrence of these subdirs
        project_subdirs = ["/sim/", "/dut/", "/tb/", "/env/", "/rtl/", "/cov/"]
        for subdir in project_subdirs:
            idx = normalized.find(subdir)
            if idx >= 0:
                # Extract from this subdir onwards (skip the leading /)
                relative = normalized[idx + 1:]  # +1 to skip the /
                return relative

    # Step 4: Fallback to basename
    return os.path.basename(normalized)


def _default_classification(cov_type: str) -> str:
    """Return default classification for a coverage type."""
    defaults = {
        "functional": "Missing Stimulus",
        "line": "Dead Code",
        "branch": "Dead Code",
        "condition": "Defensive Code",
        "toggle": "Insufficient Toggle",
        "fsm": "Unreachable State",
        "assert": "Missing Stimulus",
    }
    return defaults.get(cov_type, "Missing Stimulus")


def _compute_priority(cov_type: str) -> str:
    """Compute priority based on coverage type."""
    if cov_type in ("fsm", "assert"):
        return "P1"
    if cov_type == "functional":
        return "P1"
    return "P2"

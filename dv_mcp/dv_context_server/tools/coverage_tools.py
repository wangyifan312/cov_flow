"""Coverage MCP tools — pure Python, no MCP runtime dependency.

Tools:
  - cov_list_uncovered: list top uncovered gaps
  - cov_get_gap_detail: get detail for a single gap
  - cov_get_coverpoint_source: get coverage model source snippet
"""

from __future__ import annotations

from typing import Any

from dv_mcp.dv_context_server.indexes.readers import IndexNotFoundError
from dv_mcp.dv_context_server.services.evidence import coverage_evidence
from dv_mcp.dv_context_server.services.project_loader import get_index_reader, get_manifest
from dv_mcp.dv_context_server.services.summarizer import envelope, error_envelope, truncate_list
from lib.source_resolver import SourceResolver, SourceSnippet

_COVERAGE_INDEX = "coverage_index.json"


def _gap_summary(g: dict) -> dict:
    """Build a summary dict for a gap, including type-specific fields."""
    summary: dict[str, Any] = {
        "gap_id": g.get("gap_id"),
        "coverage_type": g.get("coverage_type", "functional"),
        "hit_count": g.get("hit_count"),
        "goal": g.get("goal"),
        "priority": g.get("priority"),
        "classification": g.get("classification"),
    }
    cov_type = g.get("coverage_type", "functional")
    if cov_type == "functional":
        summary["covergroup"] = g.get("covergroup")
        summary["coverpoint"] = g.get("coverpoint")
        summary["bin"] = g.get("bin")
    elif cov_type in ("line", "branch", "condition", "assert"):
        summary["source_file"] = g.get("source_file")
        summary["source_line"] = g.get("source_line")
    elif cov_type == "toggle":
        summary["signal"] = g.get("signal")
        summary["module"] = g.get("module")
        summary["toggle_dir"] = g.get("toggle_dir")
    elif cov_type == "fsm":
        summary["module"] = g.get("module")
        summary["fsm_name"] = g.get("fsm_name")
        summary["state"] = g.get("state")
    return summary


def cov_list_uncovered(
    project: str,
    scope: str | None = None,
    coverage_type: str = "functional",
    top_n: int = 20,
) -> dict[str, Any]:
    """List top uncovered coverage gaps.

    Args:
        project: Project ID or manifest path.
        scope: Optional instance path filter (e.g. 'tb_top.u_dut.u_dma').
        coverage_type: Coverage type filter (default: 'functional').
        top_n: Maximum number of gaps to return (default: 20, max: 50).

    Returns:
        Envelope with list of gap summaries sorted by priority.
    """
    tool = "cov_list_uncovered"
    try:
        reader = get_index_reader(project)
        data = reader.read(_COVERAGE_INDEX)
    except (FileNotFoundError, IndexNotFoundError) as e:
        return error_envelope(tool, project, str(e))

    gaps = data.get("gaps", [])

    # Filter by coverage type (skip filter when "all")
    if coverage_type != "all":
        gaps = [g for g in gaps if g.get("coverage_type") == coverage_type]

    # Filter by scope if provided (match in source_file or related signals)
    if scope:
        gaps = [g for g in gaps if scope in g.get("source_file", "") or
                scope in g.get("related_rtl_signal", "")]

    # Sort by priority (P0 first) then by gap_id
    priority_order = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
    gaps.sort(key=lambda g: (priority_order.get(g.get("priority", "P3"), 9), g.get("gap_id", "")))

    # Truncate
    top_n = min(top_n, 50)
    result_gaps, was_truncated = truncate_list(gaps, top_n)

    # Summary view for each gap
    summaries = [_gap_summary(g) for g in result_gaps]

    evidence = [
        coverage_evidence(
            "list", "list",
            data.get("report_id", "unknown"),
            f"Top {len(summaries)} uncovered {coverage_type} gaps "
            f"from report {data.get('report_id')}"
        )
    ]

    return envelope(
        tool=tool,
        project=project,
        result={
            "gaps": summaries,
            "total_uncovered": len(gaps),
            "report_id": data.get("report_id"),
        },
        evidence=evidence,
        truncated=was_truncated,
        next_actions=["cov_get_gap_detail", "cov_get_coverpoint_source"],
    )


def cov_get_gap_detail(project: str, gap_id: str) -> dict[str, Any]:
    """Get full detail for a single coverage gap.

    Args:
        project: Project ID or manifest path.
        gap_id: The gap identifier (e.g. 'GAP_0001').

    Returns:
        Envelope with the complete gap record.
    """
    tool = "cov_get_gap_detail"
    try:
        reader = get_index_reader(project)
        data = reader.read(_COVERAGE_INDEX)
    except (FileNotFoundError, IndexNotFoundError) as e:
        return error_envelope(tool, project, str(e))

    gaps = data.get("gaps", [])
    gap = next((g for g in gaps if g.get("gap_id") == gap_id), None)

    if gap is None:
        return error_envelope(tool, project, f"Gap not found: {gap_id}")

    cov_type = gap.get("coverage_type", "functional")
    if cov_type == "functional":
        desc = (
            f"Gap detail for {gap.get('covergroup')}."
            f"{gap.get('coverpoint')}.{gap.get('bin')}"
        )
    elif cov_type == "line":
        desc = f"Gap detail for line {gap.get('source_file')}:{gap.get('source_line')}"
    elif cov_type == "branch":
        desc = (
            f"Gap detail for branch at {gap.get('source_file')}:"
            f"{gap.get('source_line')} ({gap.get('branch_type')}/{gap.get('direction')})"
        )
    elif cov_type == "condition":
        desc = (
            f"Gap detail for condition '{gap.get('condition_expr')}' at "
            f"{gap.get('source_file')}:{gap.get('source_line')}"
        )
    elif cov_type == "toggle":
        desc = (
            f"Gap detail for toggle {gap.get('module')}."
            f"{gap.get('signal')} ({gap.get('toggle_dir')})"
        )
    elif cov_type == "fsm":
        desc = (
            f"Gap detail for FSM {gap.get('fsm_name')} state "
            f"'{gap.get('state')}' in {gap.get('module')}"
        )
    elif cov_type == "assert":
        desc = (
            f"Gap detail for assertion '{gap.get('assert_name')}' at "
            f"{gap.get('source_file')}:{gap.get('source_line')}"
        )
    else:
        desc = f"Gap detail for {gap.get('gap_id')}"

    evidence = [
        coverage_evidence(
            gap_id, "detail",
            f"{gap.get('source_file', '?')}:{gap.get('source_line', '?')}",
            desc,
        )
    ]

    next_actions: list[str] = ["cov_get_coverpoint_source", "spec_search"]
    if cov_type == "functional":
        next_actions.append("reg_find_fields_affecting_feature")
    elif cov_type in ("toggle", "fsm"):
        next_actions.append("rtl_find_signal")
    elif cov_type in ("line", "branch", "condition", "assert"):
        next_actions.extend(["reg_find_fields_affecting_feature", "rtl_find_signal"])

    return envelope(
        tool=tool,
        project=project,
        result=gap,
        evidence=evidence,
        truncated=False,
        next_actions=next_actions,
    )


def cov_get_coverpoint_source(
    project: str,
    gap_id: str,
    max_lines: int = 40,
) -> dict[str, Any]:
    """Get the coverage model source snippet for a coverpoint.

    Tries to read a real source file snippet via SourceResolver if
    coverage_model_root is configured in the manifest. Falls back to
    generated mock snippets when real files are unavailable.

    Args:
        project: Project ID or manifest path.
        gap_id: The gap identifier.
        max_lines: Maximum lines to return (default: 40).

    Returns:
        Envelope with source snippet and source_mode indicator.
    """
    tool = "cov_get_coverpoint_source"
    try:
        reader = get_index_reader(project)
        data = reader.read(_COVERAGE_INDEX)
    except (FileNotFoundError, IndexNotFoundError) as e:
        return error_envelope(tool, project, str(e))

    gaps = data.get("gaps", [])
    gap = next((g for g in gaps if g.get("gap_id") == gap_id), None)

    if gap is None:
        return error_envelope(tool, project, f"Gap not found: {gap_id}")

    source_file = gap.get("source_file", "unknown")
    source_line = gap.get("source_line", 0)
    cov_type = gap.get("coverage_type", "functional")

    # Try to resolve real source via SourceResolver
    snippet: SourceSnippet | None = None
    source_mode = "mock_fallback"

    try:
        manifest = get_manifest(project)
        cov_model_root = manifest.get_path("coverage", "coverage_model_root")
        if cov_model_root is not None and cov_model_root.is_dir():
            resolver = SourceResolver(
                allowed_roots=[cov_model_root],
                max_lines=max_lines,
            )
            snippet = resolver.resolve(source_file, source_line, context_lines=5)
            if snippet.status == "ok":
                source_mode = "real"
    except (FileNotFoundError, Exception):
        # Manifest load failure — proceed with mock fallback
        snippet = None
        source_mode = "mock_fallback"

    # Build the source snippet content
    if source_mode == "real" and snippet is not None:
        source_content = snippet.content
        note = (
            f"Real source snippet from {snippet.file} "
            f"(lines {snippet.start_line}-{snippet.end_line})"
        )
        was_truncated = snippet.truncated
    else:
        # Mock fallback — original MVP behavior
        source_content = _generate_mock_source(gap, cov_type, source_file, source_line)
        note = "Mock MVP: source snippet is generated, not read from actual file."
        was_truncated = False

    evidence = [
        coverage_evidence(
            gap_id, "source",
            f"{source_file}:{source_line}",
            f"Coverpoint source for {gap.get('covergroup')}.{gap.get('coverpoint')}"
        )
    ]

    return envelope(
        tool=tool,
        project=project,
        result={
            "gap_id": gap_id,
            "source_file": source_file,
            "source_line": source_line,
            "source_snippet": source_content,
            "source_mode": source_mode,
            "max_lines": max_lines,
            "note": note,
        },
        evidence=evidence,
        truncated=was_truncated,
        next_actions=["spec_search", "reg_find_fields_affecting_feature", "rtl_find_signal"],
    )


def _generate_mock_source(
    gap: dict[str, Any],
    cov_type: str,
    source_file: str,
    source_line: int,
) -> str:
    """Generate a mock source snippet for MVP fallback."""
    if cov_type == "functional":
        return (
            f"covergroup {gap.get('covergroup')} @(posedge clk);\n"
            f"  {gap.get('coverpoint')}: coverpoint <signal> {{\n"
            f"    bins {gap.get('bin')} = {{<value>}};\n"
            f"  }}\n"
            f"endgroup"
        )
    if cov_type == "line":
        return (
            f"// Mock line coverage source\n"
            f"// Source: {source_file}:{source_line}\n"
            f"// Unexecuted line in RTL module\n"
            f"// Line {source_line}: <statement not executed>"
        )
    if cov_type == "branch":
        return (
            f"// Mock branch coverage source\n"
            f"// Source: {source_file}:{source_line}\n"
            f"// Branch type: {gap.get('branch_type')}, "
            f"direction: {gap.get('direction')}\n"
            f"if (<condition>) begin\n"
            f"  // true branch\n"
            f"end else begin\n"
            f"  // false branch NOT taken\n"
            f"end"
        )
    if cov_type == "condition":
        return (
            f"// Mock condition coverage source\n"
            f"// Source: {source_file}:{source_line}\n"
            f"// Condition: {gap.get('condition_expr')}\n"
            f"// Missed combination: {gap.get('combination')}"
        )
    if cov_type == "toggle":
        return (
            f"// Mock toggle coverage source\n"
            f"// Module: {gap.get('module')}\n"
            f"// Signal: {gap.get('signal')}\n"
            f"// Toggle direction: {gap.get('toggle_dir')}"
        )
    if cov_type == "fsm":
        transition = gap.get("transition")
        return (
            f"// Mock FSM coverage source\n"
            f"// Module: {gap.get('module')}\n"
            f"// FSM: {gap.get('fsm_name')}\n"
            f"// Uncovered state: {gap.get('state')}\n"
            + (f"// Transition: {transition}\n" if transition else "")
        )
    if cov_type == "assert":
        return (
            f"// Mock assertion coverage source\n"
            f"// Source: {source_file}:{source_line}\n"
            f"// Assertion: {gap.get('assert_name')}\n"
            f"// Vacuous: {gap.get('vacuous', 'N/A')}"
        )
    return (
        f"// Mock coverage source for {gap.get('gap_id', 'unknown')}\n"
        f"// Source: {source_file}:{source_line}"
    )

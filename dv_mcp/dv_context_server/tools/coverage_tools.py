"""Coverage MCP tools — pure Python, no MCP runtime dependency.

Tools:
  - cov_list_uncovered: list top uncovered gaps
  - cov_get_gap_detail: get detail for a single gap
  - cov_get_coverpoint_source: get coverage model source snippet
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from dv_mcp.dv_context_server.indexes.readers import IndexNotFoundError
from dv_mcp.dv_context_server.services.evidence import coverage_evidence
from dv_mcp.dv_context_server.services.project_loader import get_index_reader
from dv_mcp.dv_context_server.services.summarizer import envelope, error_envelope, truncate_list

_COVERAGE_INDEX = "coverage_index.json"


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

    # Filter by coverage type
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
    summaries = []
    for g in result_gaps:
        summaries.append({
            "gap_id": g.get("gap_id"),
            "covergroup": g.get("covergroup"),
            "coverpoint": g.get("coverpoint"),
            "bin": g.get("bin"),
            "hit_count": g.get("hit_count"),
            "goal": g.get("goal"),
            "priority": g.get("priority"),
            "classification": g.get("classification"),
        })

    evidence = [
        coverage_evidence(
            "list", "list",
            data.get("report_id", "unknown"),
            f"Top {len(summaries)} uncovered {coverage_type} gaps from report {data.get('report_id')}"
        )
    ]

    return envelope(
        tool=tool,
        project=project,
        result={"gaps": summaries, "total_uncovered": len(gaps), "report_id": data.get("report_id")},
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

    evidence = [
        coverage_evidence(
            gap_id, "detail",
            f"{gap.get('source_file', '?')}:{gap.get('source_line', '?')}",
            f"Gap detail for {gap.get('covergroup')}.{gap.get('coverpoint')}.{gap.get('bin')}"
        )
    ]

    return envelope(
        tool=tool,
        project=project,
        result=gap,
        evidence=evidence,
        truncated=False,
        next_actions=["cov_get_coverpoint_source", "spec_search", "reg_find_fields_affecting_feature"],
    )


def cov_get_coverpoint_source(
    project: str,
    gap_id: str,
    max_lines: int = 40,
) -> dict[str, Any]:
    """Get the coverage model source snippet for a coverpoint.

    In MVP mode, returns the source file/line reference from the index
    without reading actual files (mock data does not include real SV sources).

    Args:
        project: Project ID or manifest path.
        gap_id: The gap identifier.
        max_lines: Maximum lines to return (default: 40).

    Returns:
        Envelope with source reference information.
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

    # In mock MVP, we return a reference rather than actual source content.
    # Real implementation would read the coverage model file.
    mock_source = (
        f"// Mock coverage model source for {gap.get('covergroup')}.{gap.get('coverpoint')}\n"
        f"// Source: {source_file}:{source_line}\n"
        f"// In production, this would contain the actual coverpoint/bin definition\n"
        f"// from the coverage model SystemVerilog file.\n"
        f"\n"
        f"covergroup {gap.get('covergroup')} @(posedge clk);\n"
        f"  {gap.get('coverpoint')}: coverpoint <signal> {{\n"
        f"    bins {gap.get('bin')} = {{<value>}};\n"
        f"  }}\n"
        f"endgroup"
    )

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
            "source_snippet": mock_source,
            "max_lines": max_lines,
            "note": "Mock MVP: source snippet is generated, not read from actual file.",
        },
        evidence=evidence,
        truncated=False,
        next_actions=["spec_search", "reg_find_fields_affecting_feature", "rtl_find_signal"],
    )

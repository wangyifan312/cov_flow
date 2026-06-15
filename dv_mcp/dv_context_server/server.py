"""DV Context MCP Server — thin FastMCP wrapper.

This module registers pure Python tool functions as MCP tools.
All logic lives in tools/*.py; this file only wires them to FastMCP.

Usage:
    python -m dv_mcp.dv_context_server.server
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from dv_mcp.dv_context_server.tools.coverage_tools import (
    cov_get_coverpoint_source,
    cov_get_gap_detail,
    cov_get_hit_history,
    cov_list_uncovered,
)
from dv_mcp.dv_context_server.tools.register_tools import (
    reg_find_field,
    reg_find_fields_affecting_feature,
    reg_get_ral_path,
    reg_search_by_description,
)
from dv_mcp.dv_context_server.tools.rtl_tools import (
    rtl_find_signal,
    rtl_get_instance_info,
    rtl_get_source_snippet,
    rtl_trace_fanin,
)
from dv_mcp.dv_context_server.tools.sim_tools import (
    cov_get_coverage_diff,
    sim_get_test_result,
    sim_run_targeted_test,
    sim_search_log,
    wave_check_condition,
)
from dv_mcp.dv_context_server.tools.spec_tools import spec_get_section, spec_search
from dv_mcp.dv_context_server.tools.tb_tools import (
    tb_find_config_knob,
    tb_find_sequence,
    tb_find_tests_for_gap,
    tb_get_base_test_template,
    tb_get_existing_tests_for_feature,
    tb_get_sequence_source_snippet,
    tb_read_source,
)

mcp = FastMCP(
    "dv-context",
    instructions=(
        "DV Context MCP Server provides structured query tools for "
        "digital IC verification coverage closure. Use these tools to "
        "query coverage gaps, spec sections, register fields, RTL signals, "
        "and testbench components. All tools return bounded, structured results."
    ),
)


# ---------------------------------------------------------------------------
# Coverage tools
# ---------------------------------------------------------------------------

@mcp.tool()
def tool_cov_list_uncovered(
    project: str,
    scope: str | None = None,
    coverage_type: str = "functional",
    top_n: int = 20,
) -> dict:
    """List top uncovered coverage gaps for a project.

    Returns gap summaries sorted by priority.
    Use coverage_type='all' to include all coverage types.
    """
    return cov_list_uncovered(project, scope=scope, coverage_type=coverage_type, top_n=top_n)


@mcp.tool()
def tool_cov_get_gap_detail(project: str, gap_id: str) -> dict:
    """Get full detail for a single coverage gap."""
    return cov_get_gap_detail(project, gap_id)


@mcp.tool()
def tool_cov_get_coverpoint_source(
    project: str,
    gap_id: str,
    max_lines: int = 40,
) -> dict:
    """Get the coverage model source snippet for a coverpoint."""
    return cov_get_coverpoint_source(project, gap_id, max_lines=max_lines)


@mcp.tool()
def tool_cov_get_hit_history(
    project: str,
    gap_id: str,
) -> dict:
    """Get simulation hit history for a coverage gap.

    Returns hit history across multiple regression runs, including trend
    analysis (improving/stable/regressing/never_covered) and first_covered info.
    """
    return cov_get_hit_history(project, gap_id)


# ---------------------------------------------------------------------------
# Spec tools
# ---------------------------------------------------------------------------

@mcp.tool()
def tool_spec_search(
    project: str,
    query: str,
    max_results: int = 10,
) -> dict:
    """Search spec sections by keyword or feature tag."""
    return spec_search(project, query, max_results=max_results)


@mcp.tool()
def tool_spec_get_section(
    project: str,
    section_id: str,
) -> dict:
    """Get a full spec section by section_id."""
    return spec_get_section(project, section_id)


# ---------------------------------------------------------------------------
# Register tools
# ---------------------------------------------------------------------------

@mcp.tool()
def tool_reg_find_fields_affecting_feature(
    project: str,
    feature: str,
) -> dict:
    """Find register fields likely controlling a given feature."""
    return reg_find_fields_affecting_feature(project, feature)


@mcp.tool()
def tool_reg_find_field(
    project: str,
    field_name: str,
) -> dict:
    """Find a register field by exact name (case-insensitive)."""
    return reg_find_field(project, field_name)


@mcp.tool()
def tool_reg_search_by_description(
    project: str,
    query: str,
) -> dict:
    """Search register fields by description keyword."""
    return reg_search_by_description(project, query)


@mcp.tool()
def tool_reg_get_ral_path(
    project: str,
    field_name: str,
) -> dict:
    """Get the RAL access path for a register field."""
    return reg_get_ral_path(project, field_name)


# ---------------------------------------------------------------------------
# Testbench tools
# ---------------------------------------------------------------------------

@mcp.tool()
def tool_tb_get_existing_tests_for_feature(
    project: str,
    feature: str,
) -> dict:
    """Find existing UVM tests and sequences related to a feature."""
    return tb_get_existing_tests_for_feature(project, feature)


@mcp.tool()
def tool_tb_find_tests_for_gap(
    project: str,
    gap_id: str,
) -> dict:
    """Find existing tests/sequences that may cover a coverage gap.

    Extracts semantic keywords from the gap's coverpoint/bin names,
    searches the TB index, and assesses whether existing tests likely
    cover the gap. Only supports functional coverage gaps.
    """
    return tb_find_tests_for_gap(project, gap_id)


@mcp.tool()
def tool_tb_read_source(
    project: str,
    component_type: str,
    name: str,
    max_lines: int = 500,
) -> dict:
    """Read the source code of a testbench component (sequence, test, base_test, or env file).

    Reads from the TB index with security boundaries (path traversal protection,
    max_lines/max_bytes caps). Use this to inspect sequence API signatures,
    constraint patterns, and coding style for testcase generation.
    """
    return tb_read_source(project, component_type, name, max_lines=max_lines)


@mcp.tool()
def tool_tb_find_sequence(
    project: str,
    sequence_name: str,
) -> dict:
    """Find a sequence by name (supports fuzzy/substring matching)."""
    return tb_find_sequence(project, sequence_name)


@mcp.tool()
def tool_tb_get_base_test_template(
    project: str,
    base_test_name: str | None = None,
) -> dict:
    """Get base test info with config_knobs."""
    return tb_get_base_test_template(project, base_test_name=base_test_name)


@mcp.tool()
def tool_tb_find_config_knob(
    project: str,
    knob_name: str,
) -> dict:
    """Find a config knob by name (supports fuzzy/substring matching)."""
    return tb_find_config_knob(project, knob_name)


@mcp.tool()
def tool_tb_get_sequence_source_snippet(
    project: str,
    sequence_name: str,
    max_lines: int = 40,
) -> dict:
    """Get source snippet for a sequence by name.

    Convenience wrapper around tb_read_source that only requires sequence_name.
    Looks up the sequence in tb_index.json (exact match first, then fuzzy
    fallback), then reads the source file with security boundaries.
    """
    return tb_get_sequence_source_snippet(project, sequence_name, max_lines=max_lines)


# ---------------------------------------------------------------------------
# RTL tools
# ---------------------------------------------------------------------------

@mcp.tool()
def tool_rtl_find_signal(
    project: str,
    signal_name: str,
    module_filter: str | None = None,
) -> dict:
    """Find RTL signals matching a name pattern."""
    return rtl_find_signal(project, signal_name, module_filter=module_filter)


@mcp.tool()
def tool_rtl_get_instance_info(
    project: str,
    module_name: str | None = None,
    instance_path: str | None = None,
) -> dict:
    """Get module or instance details from the RTL index."""
    return rtl_get_instance_info(project, module_name=module_name, instance_path=instance_path)


@mcp.tool()
def tool_rtl_get_source_snippet(
    project: str,
    signal_name: str,
    module_filter: str | None = None,
    context_lines: int = 5,
) -> dict:
    """Read source snippet for a signal definition.

    Finds the signal in the RTL index, then reads a bounded snippet from
    the source file using SourceResolver security boundaries.
    """
    return rtl_get_source_snippet(
        project, signal_name, module_filter=module_filter, context_lines=context_lines,
    )


@mcp.tool()
def tool_rtl_trace_fanin(
    project: str,
    signal_name: str,
    module_filter: str | None = None,
) -> dict:
    """Trace same-module signals that may affect a target signal (mock stub).

    Returns other signals and ports in the same module as potential fan-in
    sources. Full cross-module fan-in tracing requires elaboration data.
    """
    return rtl_trace_fanin(project, signal_name, module_filter=module_filter)


# ---------------------------------------------------------------------------
# Simulation tools
# ---------------------------------------------------------------------------

@mcp.tool()
def tool_sim_run_targeted_test(
    project: str,
    test: str,
    seed: int,
    confirm: bool = False,
) -> dict:
    """Run a targeted simulation test (mock: dry-run only).

    Requires confirm=true. Checks manifest policy before rendering commands.
    """
    return sim_run_targeted_test(project, test, seed, confirm=confirm)


@mcp.tool()
def tool_sim_get_test_result(
    project: str,
    test: str,
    seed: int | None = None,
) -> dict:
    """Get simulation result for a test."""
    return sim_get_test_result(project, test, seed=seed)


@mcp.tool()
def tool_sim_search_log(
    project: str,
    test: str,
    seed: int,
    keyword: str,
) -> dict:
    """Search simulation log for a keyword."""
    return sim_search_log(project, test, seed, keyword)


@mcp.tool()
def tool_cov_get_coverage_diff(
    project: str,
    gap_id: str | None = None,
) -> dict:
    """Compute coverage diff between before/after databases."""
    return cov_get_coverage_diff(project, gap_id=gap_id)


@mcp.tool()
def tool_wave_check_condition(
    project: str,
    signal_path: str,
    condition: str,
    time_range: str | None = None,
) -> dict:
    """Check signal condition in waveform (mock stub).

    Permanent mock stub — real waveform analysis requires Verdi/NPI integration
    which is not available per project rules. Uses StubVerdiAdapter internally.
    """
    return wave_check_condition(project, signal_path, condition, time_range)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    """Run the MCP server with stdio transport."""
    mcp.run()


if __name__ == "__main__":
    main()

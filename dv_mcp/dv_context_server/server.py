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
    cov_list_uncovered,
)
from dv_mcp.dv_context_server.tools.register_tools import reg_find_fields_affecting_feature
from dv_mcp.dv_context_server.tools.rtl_tools import rtl_find_signal
from dv_mcp.dv_context_server.tools.sim_tools import (
    cov_get_coverage_diff,
    sim_get_test_result,
    sim_run_targeted_test,
    sim_search_log,
)
from dv_mcp.dv_context_server.tools.spec_tools import spec_search
from dv_mcp.dv_context_server.tools.tb_tools import tb_get_existing_tests_for_feature

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


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    """Run the MCP server with stdio transport."""
    mcp.run()


if __name__ == "__main__":
    main()

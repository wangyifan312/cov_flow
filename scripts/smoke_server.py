#!/usr/bin/env python3
"""Smoke-test the DV Context MCP server: verify import and tool registration.

This script checks that the FastMCP server can be imported and that all
expected tools are registered. It uses try/except to guard against MCP SDK
internal API changes (_tool_manager._tools is a private attribute).
"""
from __future__ import annotations

import sys

EXPECTED_TOOLS = [
    "tool_cov_list_uncovered",
    "tool_cov_get_gap_detail",
    "tool_cov_get_coverpoint_source",
    "tool_spec_search",
    "tool_reg_find_fields_affecting_feature",
    "tool_tb_get_existing_tests_for_feature",
    "tool_rtl_find_signal",
]


def _get_registered_tools(mcp_instance) -> dict:
    """Attempt to retrieve the registered tools dict via public or private API.

    Returns the tools dict, or raises RuntimeError if no known access path works.
    """
    # Try public API first (if MCP SDK ever exposes a sync one)
    try:
        result = mcp_instance.list_tools()
        # If it's a coroutine, the public API is async-only — skip it
        if hasattr(result, "__await__"):
            result.close()  # prevent RuntimeWarning
            raise AttributeError("list_tools is async")
        return dict(result)
    except (AttributeError, TypeError):
        pass

    # Fallback: known private API (FastMCP internals)
    try:
        return mcp_instance._tool_manager._tools  # noqa: SLF001
    except AttributeError:
        pass

    raise RuntimeError(
        "MCP SDK internal API changed. Update smoke-server check.\n"
        "Neither mcp.list_tools() nor mcp._tool_manager._tools is available."
    )


def main() -> int:
    try:
        from dv_mcp.dv_context_server.server import mcp
    except Exception as e:
        print(f"FAIL: could not import dv_mcp.dv_context_server.server: {e}", file=sys.stderr)
        return 1

    try:
        tools = _get_registered_tools(mcp)
    except RuntimeError as e:
        print(f"FAIL: {e}", file=sys.stderr)
        return 1

    missing = [t for t in EXPECTED_TOOLS if t not in tools]
    if missing:
        print(f"FAIL: missing tools: {missing}", file=sys.stderr)
        return 1

    print(f"MCP server smoke OK: {len(tools)} tools registered")
    return 0


if __name__ == "__main__":
    sys.exit(main())

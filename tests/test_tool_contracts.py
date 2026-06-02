"""MCP tool envelope contract tests.

Verifies that all MCP tools return the standard envelope format:
- Success: ok, tool, project, result, evidence, truncated, next_actions
- Error: ok=false, tool, project, error, evidence=[], truncated=false, next_actions=[]
"""

import pytest

from dv_mcp.dv_context_server.services.project_loader import clear_cache
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

PROJECT = "mock_data/dma_subsystem/project_manifest.yaml"

REQUIRED_SUCCESS_KEYS = {"ok", "tool", "project", "result", "evidence", "truncated", "next_actions"}
REQUIRED_ERROR_KEYS = {"ok", "tool", "project", "error", "evidence", "truncated", "next_actions"}


@pytest.fixture(autouse=True)
def _clear():
    clear_cache()
    yield
    clear_cache()


def _check_success(resp: dict, expected_tool: str) -> None:
    """Verify a success response has all required envelope fields."""
    assert resp["ok"] is True
    assert resp["tool"] == expected_tool
    assert "project" in resp
    assert "result" in resp
    assert isinstance(resp["evidence"], list)
    assert isinstance(resp["truncated"], bool)
    assert isinstance(resp["next_actions"], list)
    for key in REQUIRED_SUCCESS_KEYS:
        assert key in resp, f"Missing key: {key}"


def _check_error(resp: dict, expected_tool: str) -> None:
    """Verify an error response has all required envelope fields."""
    assert resp["ok"] is False
    assert resp["tool"] == expected_tool
    assert "project" in resp
    assert "error" in resp
    assert isinstance(resp["error"], str)
    assert resp["evidence"] == []
    assert resp["truncated"] is False
    assert resp["next_actions"] == []
    for key in REQUIRED_ERROR_KEYS:
        assert key in resp, f"Missing key: {key}"


class TestCoverageToolsContract:
    def test_cov_list_uncovered_success(self) -> None:
        resp = cov_list_uncovered(PROJECT)
        _check_success(resp, "cov_list_uncovered")

    def test_cov_list_uncovered_error(self) -> None:
        resp = cov_list_uncovered("nonexistent_project_xyz")
        _check_error(resp, "cov_list_uncovered")

    def test_cov_get_gap_detail_success(self) -> None:
        resp = cov_get_gap_detail(PROJECT, "GAP_0001")
        _check_success(resp, "cov_get_gap_detail")

    def test_cov_get_gap_detail_error(self) -> None:
        resp = cov_get_gap_detail(PROJECT, "GAP_NONEXISTENT")
        _check_error(resp, "cov_get_gap_detail")

    def test_cov_get_coverpoint_source_success(self) -> None:
        resp = cov_get_coverpoint_source(PROJECT, "GAP_0001")
        _check_success(resp, "cov_get_coverpoint_source")

    def test_cov_get_coverpoint_source_error(self) -> None:
        resp = cov_get_coverpoint_source(PROJECT, "GAP_NONEXISTENT")
        _check_error(resp, "cov_get_coverpoint_source")


class TestSpecToolsContract:
    def test_spec_search_success(self) -> None:
        resp = spec_search(PROJECT, "dma")
        _check_success(resp, "spec_search")

    def test_spec_search_error_bad_project(self) -> None:
        resp = spec_search("nonexistent_project_xyz", "dma")
        _check_error(resp, "spec_search")


class TestRegisterToolsContract:
    def test_reg_find_fields_success(self) -> None:
        resp = reg_find_fields_affecting_feature(PROJECT, "linked_list")
        _check_success(resp, "reg_find_fields_affecting_feature")

    def test_reg_find_fields_error_bad_project(self) -> None:
        resp = reg_find_fields_affecting_feature("nonexistent_project_xyz", "linked_list")
        _check_error(resp, "reg_find_fields_affecting_feature")


class TestTBToolsContract:
    def test_tb_get_tests_success(self) -> None:
        resp = tb_get_existing_tests_for_feature(PROJECT, "linked_list")
        _check_success(resp, "tb_get_existing_tests_for_feature")

    def test_tb_get_tests_error_bad_project(self) -> None:
        resp = tb_get_existing_tests_for_feature("nonexistent_project_xyz", "linked_list")
        _check_error(resp, "tb_get_existing_tests_for_feature")


class TestRTLToolsContract:
    def test_rtl_find_signal_success(self) -> None:
        resp = rtl_find_signal(PROJECT, "clk")
        _check_success(resp, "rtl_find_signal")

    def test_rtl_find_signal_error_bad_project(self) -> None:
        resp = rtl_find_signal("nonexistent_project_xyz", "clk")
        _check_error(resp, "rtl_find_signal")


class TestSimToolsContract:
    def test_sim_run_targeted_test_no_confirm(self) -> None:
        resp = sim_run_targeted_test(PROJECT, "dma_basic_test", 42, confirm=False)
        _check_success(resp, "sim_run_targeted_test")

    def test_sim_run_targeted_test_error_bad_project(self) -> None:
        resp = sim_run_targeted_test("nonexistent_project_xyz", "test", 42, confirm=False)
        _check_error(resp, "sim_run_targeted_test")

    def test_sim_get_test_result_success(self) -> None:
        resp = sim_get_test_result(PROJECT, "dma_basic_test")
        _check_success(resp, "sim_get_test_result")

    def test_sim_get_test_result_error_bad_project(self) -> None:
        resp = sim_get_test_result("nonexistent_project_xyz", "test")
        _check_error(resp, "sim_get_test_result")

    def test_sim_search_log_success(self) -> None:
        resp = sim_search_log(PROJECT, "dma_linked_list_desc_test", 1, "error")
        _check_success(resp, "sim_search_log")

    def test_sim_search_log_error_bad_project(self) -> None:
        resp = sim_search_log("nonexistent_project_xyz", "test", 42, "error")
        _check_error(resp, "sim_search_log")

    def test_cov_get_coverage_diff_success(self) -> None:
        resp = cov_get_coverage_diff(PROJECT)
        _check_success(resp, "cov_get_coverage_diff")

    def test_cov_get_coverage_diff_error_bad_project(self) -> None:
        resp = cov_get_coverage_diff("nonexistent_project_xyz")
        _check_error(resp, "cov_get_coverage_diff")

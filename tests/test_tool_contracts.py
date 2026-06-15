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

PROJECT = "mock_data/dma_subsystem/project_manifest.yaml"
AXI2AHB_PROJECT = "mock_data/axi2ahb/project_manifest.yaml"

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


class TestTbToolContractsAxi2ahb:
    """Envelope contract tests using axi2ahb real TB data."""

    def test_tb_get_tests_success_axi2ahb(self) -> None:
        resp = tb_get_existing_tests_for_feature(AXI2AHB_PROJECT, "burst")
        _check_success(resp, "tb_get_existing_tests_for_feature")

    def test_tb_get_tests_scope_tests_axi2ahb(self) -> None:
        resp = tb_get_existing_tests_for_feature(AXI2AHB_PROJECT, "burst", scope="tests")
        _check_success(resp, "tb_get_existing_tests_for_feature")

    def test_tb_get_tests_scope_sequences_axi2ahb(self) -> None:
        resp = tb_get_existing_tests_for_feature(AXI2AHB_PROJECT, "burst", scope="sequences")
        _check_success(resp, "tb_get_existing_tests_for_feature")


class TestTbFindTestsForGapContract:
    """Envelope contract tests for tb_find_tests_for_gap."""

    def test_success(self) -> None:
        resp = tb_find_tests_for_gap(AXI2AHB_PROJECT, "GAP_0003")
        _check_success(resp, "tb_find_tests_for_gap")

    def test_error_bad_gap(self) -> None:
        resp = tb_find_tests_for_gap(PROJECT, "GAP_9999")
        _check_error(resp, "tb_find_tests_for_gap")

    def test_error_bad_project(self) -> None:
        resp = tb_find_tests_for_gap("nonexistent_project_xyz", "GAP_0001")
        _check_error(resp, "tb_find_tests_for_gap")


class TestTbReadSourceContract:
    """Envelope contract tests for tb_read_source."""

    def test_error_invalid_component_type(self) -> None:
        resp = tb_read_source(AXI2AHB_PROJECT, "invalid", "any")
        _check_error(resp, "tb_read_source")

    def test_error_bad_project(self) -> None:
        resp = tb_read_source("nonexistent_project_xyz", "sequence", "any")
        _check_error(resp, "tb_read_source")

    def test_error_component_not_found(self) -> None:
        resp = tb_read_source(AXI2AHB_PROJECT, "sequence", "nonexistent_seq_xyz")
        _check_error(resp, "tb_read_source")


# ---------------------------------------------------------------------------
# Phase 6A new tools contract tests
# ---------------------------------------------------------------------------


class TestSpecGetSectionContract:
    """Envelope contract tests for spec_get_section."""

    def test_success(self) -> None:
        resp = spec_get_section(PROJECT, "spec_linked_list_descriptor_mode")
        _check_success(resp, "spec_get_section")

    def test_error_section_not_found(self) -> None:
        resp = spec_get_section(PROJECT, "nonexistent_section_xyz")
        _check_error(resp, "spec_get_section")

    def test_error_bad_project(self) -> None:
        resp = spec_get_section("nonexistent_project_xyz", "spec_linked_list_descriptor_mode")
        _check_error(resp, "spec_get_section")


class TestRegFindFieldContract:
    """Envelope contract tests for reg_find_field."""

    def test_success(self) -> None:
        resp = reg_find_field(PROJECT, "LL_MODE_EN")
        _check_success(resp, "reg_find_field")

    def test_error_field_not_found(self) -> None:
        resp = reg_find_field(PROJECT, "NONEXISTENT_FIELD_XYZ")
        _check_error(resp, "reg_find_field")

    def test_error_bad_project(self) -> None:
        resp = reg_find_field("nonexistent_project_xyz", "LL_MODE_EN")
        _check_error(resp, "reg_find_field")


class TestRegSearchByDescriptionContract:
    """Envelope contract tests for reg_search_by_description."""

    def test_success(self) -> None:
        resp = reg_search_by_description(PROJECT, "linked list")
        _check_success(resp, "reg_search_by_description")

    def test_success_no_match(self) -> None:
        resp = reg_search_by_description(PROJECT, "zzzznonexistent")
        _check_success(resp, "reg_search_by_description")

    def test_error_bad_project(self) -> None:
        resp = reg_search_by_description("nonexistent_project_xyz", "dma")
        _check_error(resp, "reg_search_by_description")


class TestRegGetRalPathContract:
    """Envelope contract tests for reg_get_ral_path."""

    def test_success(self) -> None:
        resp = reg_get_ral_path(PROJECT, "LL_MODE_EN")
        _check_success(resp, "reg_get_ral_path")

    def test_error_field_not_found(self) -> None:
        resp = reg_get_ral_path(PROJECT, "NONEXISTENT_FIELD_XYZ")
        _check_error(resp, "reg_get_ral_path")

    def test_error_bad_project(self) -> None:
        resp = reg_get_ral_path("nonexistent_project_xyz", "LL_MODE_EN")
        _check_error(resp, "reg_get_ral_path")


class TestRtlGetInstanceInfoContract:
    """Envelope contract tests for rtl_get_instance_info."""

    def test_success_module_name(self) -> None:
        resp = rtl_get_instance_info(PROJECT, module_name="dma_desc_parser")
        _check_success(resp, "rtl_get_instance_info")

    def test_success_instance_path(self) -> None:
        resp = rtl_get_instance_info(PROJECT, instance_path="dma_subsystem.u_dma")
        _check_success(resp, "rtl_get_instance_info")

    def test_error_module_not_found(self) -> None:
        resp = rtl_get_instance_info(PROJECT, module_name="nonexistent_module_xyz")
        _check_error(resp, "rtl_get_instance_info")

    def test_error_both_none(self) -> None:
        resp = rtl_get_instance_info(PROJECT)
        _check_error(resp, "rtl_get_instance_info")

    def test_error_bad_project(self) -> None:
        resp = rtl_get_instance_info("nonexistent_project_xyz", module_name="dma_core")
        _check_error(resp, "rtl_get_instance_info")


class TestTbFindSequenceContract:
    """Envelope contract tests for tb_find_sequence."""

    def test_success(self) -> None:
        resp = tb_find_sequence(PROJECT, "dma_normal_desc_seq")
        _check_success(resp, "tb_find_sequence")

    def test_error_sequence_not_found(self) -> None:
        resp = tb_find_sequence(PROJECT, "nonexistent_seq_xyz")
        _check_error(resp, "tb_find_sequence")

    def test_error_bad_project(self) -> None:
        resp = tb_find_sequence("nonexistent_project_xyz", "dma_normal_desc_seq")
        _check_error(resp, "tb_find_sequence")


class TestTbGetBaseTestTemplateContract:
    """Envelope contract tests for tb_get_base_test_template."""

    def test_success_all(self) -> None:
        resp = tb_get_base_test_template(PROJECT)
        _check_success(resp, "tb_get_base_test_template")

    def test_success_specific(self) -> None:
        resp = tb_get_base_test_template(PROJECT, base_test_name="dma_base_test")
        _check_success(resp, "tb_get_base_test_template")

    def test_error_not_found(self) -> None:
        resp = tb_get_base_test_template(PROJECT, base_test_name="nonexistent_base_test")
        _check_error(resp, "tb_get_base_test_template")

    def test_error_bad_project(self) -> None:
        resp = tb_get_base_test_template("nonexistent_project_xyz")
        _check_error(resp, "tb_get_base_test_template")


class TestTbFindConfigKnobContract:
    """Envelope contract tests for tb_find_config_knob."""

    def test_success(self) -> None:
        resp = tb_find_config_knob(PROJECT, "num_channels")
        _check_success(resp, "tb_find_config_knob")

    def test_error_not_found(self) -> None:
        resp = tb_find_config_knob(PROJECT, "nonexistent_knob_xyz")
        _check_error(resp, "tb_find_config_knob")

    def test_error_bad_project(self) -> None:
        resp = tb_find_config_knob("nonexistent_project_xyz", "num_channels")
        _check_error(resp, "tb_find_config_knob")


# ---------------------------------------------------------------------------
# Phase 6B new RTL tools contract tests
# ---------------------------------------------------------------------------


class TestRtlGetSourceSnippetContract:
    """Envelope contract tests for rtl_get_source_snippet."""

    def test_success(self) -> None:
        resp = rtl_get_source_snippet(PROJECT, "ll_mode_en")
        _check_success(resp, "rtl_get_source_snippet")

    def test_error_signal_not_found(self) -> None:
        resp = rtl_get_source_snippet(PROJECT, "zzzznonexistent_signal")
        _check_error(resp, "rtl_get_source_snippet")

    def test_error_bad_project(self) -> None:
        resp = rtl_get_source_snippet("nonexistent_project_xyz", "ll_mode_en")
        _check_error(resp, "rtl_get_source_snippet")


class TestRtlTraceFaninContract:
    """Envelope contract tests for rtl_trace_fanin."""

    def test_success(self) -> None:
        resp = rtl_trace_fanin(PROJECT, "ll_mode_en")
        _check_success(resp, "rtl_trace_fanin")

    def test_error_signal_not_found(self) -> None:
        resp = rtl_trace_fanin(PROJECT, "zzzznonexistent_signal")
        _check_error(resp, "rtl_trace_fanin")

    def test_error_bad_project(self) -> None:
        resp = rtl_trace_fanin("nonexistent_project_xyz", "ll_mode_en")
        _check_error(resp, "rtl_trace_fanin")


# ---------------------------------------------------------------------------
# Phase 6C new coverage tool contract tests
# ---------------------------------------------------------------------------


class TestCovGetHitHistoryContract:
    """Envelope contract tests for cov_get_hit_history."""

    def test_success(self) -> None:
        resp = cov_get_hit_history(PROJECT, "GAP_0001")
        _check_success(resp, "cov_get_hit_history")

    def test_error_gap_not_found(self) -> None:
        resp = cov_get_hit_history(PROJECT, "GAP_9999")
        _check_error(resp, "cov_get_hit_history")

    def test_error_bad_project(self) -> None:
        resp = cov_get_hit_history("nonexistent_project_xyz", "GAP_0001")
        _check_error(resp, "cov_get_hit_history")


# ---------------------------------------------------------------------------
# Phase 6D new tool contract tests
# ---------------------------------------------------------------------------


class TestTbGetSequenceSourceSnippetContract:
    """Envelope contract tests for tb_get_sequence_source_snippet."""

    def test_success(self) -> None:
        resp = tb_get_sequence_source_snippet(PROJECT, "dma_normal_desc_seq")
        _check_success(resp, "tb_get_sequence_source_snippet")

    def test_error_sequence_not_found(self) -> None:
        resp = tb_get_sequence_source_snippet(PROJECT, "nonexistent_seq_xyz")
        _check_error(resp, "tb_get_sequence_source_snippet")

    def test_error_bad_project(self) -> None:
        resp = tb_get_sequence_source_snippet(
            "nonexistent_project_xyz", "dma_normal_desc_seq",
        )
        _check_error(resp, "tb_get_sequence_source_snippet")


class TestWaveCheckConditionContract:
    """Envelope contract tests for wave_check_condition."""

    def test_success(self) -> None:
        resp = wave_check_condition(PROJECT, "top.dut.axi_valid", "axi_valid")
        _check_success(resp, "wave_check_condition")

    def test_error_bad_project(self) -> None:
        resp = wave_check_condition(
            "nonexistent_project_xyz", "top.dut.axi_valid", "axi_valid",
        )
        _check_error(resp, "wave_check_condition")

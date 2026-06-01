"""Tests for coverage MCP tools (pure Python, no MCP runtime)."""

import pytest

from dv_mcp.dv_context_server.services.project_loader import clear_cache
from dv_mcp.dv_context_server.tools.coverage_tools import (
    cov_get_coverpoint_source,
    cov_get_gap_detail,
    cov_list_uncovered,
)

PROJECT = "mock_data/dma_subsystem/project_manifest.yaml"


@pytest.fixture(autouse=True)
def _clear():
    clear_cache()
    yield
    clear_cache()


class TestCovListUncovered:
    def test_returns_ok(self) -> None:
        result = cov_list_uncovered(PROJECT)
        assert result["ok"] is True
        assert result["tool"] == "cov_list_uncovered"

    def test_default_top_n(self) -> None:
        result = cov_list_uncovered(PROJECT)
        assert len(result["result"]["gaps"]) == 15  # All 15 gaps, under default 20

    def test_custom_top_n(self) -> None:
        result = cov_list_uncovered(PROJECT, top_n=3)
        assert len(result["result"]["gaps"]) == 3

    def test_sorted_by_priority(self) -> None:
        result = cov_list_uncovered(PROJECT, top_n=10)
        priorities = [g["priority"] for g in result["result"]["gaps"]]
        priority_order = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
        assert priorities == sorted(priorities, key=lambda p: priority_order[p])

    def test_has_evidence(self) -> None:
        result = cov_list_uncovered(PROJECT)
        assert len(result["evidence"]) > 0
        assert result["evidence"][0]["source_type"] == "coverage_report"

    def test_invalid_project(self) -> None:
        result = cov_list_uncovered("nonexistent_manifest.yaml")
        assert result["ok"] is False

    def test_filter_by_line_type(self) -> None:
        result = cov_list_uncovered(PROJECT, coverage_type="line")
        assert result["ok"] is True
        assert all(g["coverage_type"] == "line" for g in result["result"]["gaps"])
        assert len(result["result"]["gaps"]) == 2  # GAP_L001, GAP_L002

    def test_filter_by_toggle_type(self) -> None:
        result = cov_list_uncovered(PROJECT, coverage_type="toggle")
        assert result["ok"] is True
        assert all(g["coverage_type"] == "toggle" for g in result["result"]["gaps"])
        assert len(result["result"]["gaps"]) == 2

    def test_filter_all_types(self) -> None:
        result = cov_list_uncovered(PROJECT, coverage_type="all", top_n=50)
        assert result["ok"] is True
        # Should return all 27 gaps
        assert result["result"]["total_uncovered"] == 27
        types_present = set(g["coverage_type"] for g in result["result"]["gaps"])
        assert "functional" in types_present
        assert "line" in types_present

    def test_line_gap_summary_has_source_fields(self) -> None:
        result = cov_list_uncovered(PROJECT, coverage_type="line")
        gap = result["result"]["gaps"][0]
        assert "source_file" in gap
        assert "source_line" in gap

    def test_toggle_gap_summary_has_signal_fields(self) -> None:
        result = cov_list_uncovered(PROJECT, coverage_type="toggle")
        gap = result["result"]["gaps"][0]
        assert "signal" in gap
        assert "module" in gap
        assert "toggle_dir" in gap

    def test_fsm_gap_summary_has_fsm_fields(self) -> None:
        result = cov_list_uncovered(PROJECT, coverage_type="fsm")
        gap = result["result"]["gaps"][0]
        assert "module" in gap
        assert "fsm_name" in gap
        assert "state" in gap


class TestCovGetGapDetail:
    def test_existing_gap(self) -> None:
        result = cov_get_gap_detail(PROJECT, "GAP_0001")
        assert result["ok"] is True
        assert result["result"]["gap_id"] == "GAP_0001"
        assert result["result"]["bin"] == "linked_list"

    def test_nonexistent_gap(self) -> None:
        result = cov_get_gap_detail(PROJECT, "GAP_9999")
        assert result["ok"] is False
        assert "not found" in result["error"].lower()

    def test_has_evidence(self) -> None:
        result = cov_get_gap_detail(PROJECT, "GAP_0001")
        assert len(result["evidence"]) > 0

    def test_suggests_next_actions(self) -> None:
        result = cov_get_gap_detail(PROJECT, "GAP_0001")
        assert len(result["next_actions"]) > 0

    def test_line_gap_detail(self) -> None:
        result = cov_get_gap_detail(PROJECT, "GAP_L001")
        assert result["ok"] is True
        assert result["result"]["coverage_type"] == "line"
        assert result["result"]["source_file"] == "rtl/dma_desc_parser.sv"
        assert len(result["evidence"]) > 0

    def test_toggle_gap_detail(self) -> None:
        result = cov_get_gap_detail(PROJECT, "GAP_T001")
        assert result["ok"] is True
        assert result["result"]["coverage_type"] == "toggle"
        assert result["result"]["signal"] == "burst_wrap"
        assert "rtl_find_signal" in result["next_actions"]

    def test_fsm_gap_detail(self) -> None:
        result = cov_get_gap_detail(PROJECT, "GAP_M001")
        assert result["ok"] is True
        assert result["result"]["coverage_type"] == "fsm"
        assert result["result"]["state"] == "PARSE_SG"


class TestCovGetCoverpointSource:
    def test_existing_gap(self) -> None:
        result = cov_get_coverpoint_source(PROJECT, "GAP_0001")
        assert result["ok"] is True
        assert "source_snippet" in result["result"]
        assert result["result"]["source_file"] == "tb/cov/dma_cov.sv"

    def test_nonexistent_gap(self) -> None:
        result = cov_get_coverpoint_source(PROJECT, "GAP_9999")
        assert result["ok"] is False

    def test_mock_note_present(self) -> None:
        result = cov_get_coverpoint_source(PROJECT, "GAP_0001")
        assert "Mock MVP" in result["result"]["note"]

    def test_line_gap_source(self) -> None:
        result = cov_get_coverpoint_source(PROJECT, "GAP_L001")
        assert result["ok"] is True
        assert "Mock line coverage source" in result["result"]["source_snippet"]

    def test_toggle_gap_source(self) -> None:
        result = cov_get_coverpoint_source(PROJECT, "GAP_T001")
        assert result["ok"] is True
        assert "Mock toggle coverage source" in result["result"]["source_snippet"]
        assert "burst_wrap" in result["result"]["source_snippet"]

    def test_fsm_gap_source(self) -> None:
        result = cov_get_coverpoint_source(PROJECT, "GAP_M001")
        assert result["ok"] is True
        assert "Mock FSM coverage source" in result["result"]["source_snippet"]
        assert "PARSE_SG" in result["result"]["source_snippet"]

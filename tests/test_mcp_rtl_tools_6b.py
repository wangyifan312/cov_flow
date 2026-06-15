"""Tests for Phase 6B RTL MCP tools: rtl_get_source_snippet, rtl_trace_fanin."""

import pytest

from dv_mcp.dv_context_server.services.project_loader import clear_cache
from dv_mcp.dv_context_server.tools.rtl_tools import (
    rtl_get_source_snippet,
    rtl_trace_fanin,
)

PROJECT = "mock_data/dma_subsystem/project_manifest.yaml"


@pytest.fixture(autouse=True)
def _clear():
    clear_cache()
    yield
    clear_cache()


class TestRtlGetSourceSnippet:
    def test_find_ll_mode_en(self) -> None:
        result = rtl_get_source_snippet(PROJECT, "ll_mode_en")
        assert result["ok"] is True
        assert result["result"]["signal_name"] == "ll_mode_en"
        assert result["result"]["source_mode"] == "real"
        assert "content" in result["result"]
        assert len(result["result"]["content"]) > 0

    def test_find_burst_wrap(self) -> None:
        result = rtl_get_source_snippet(PROJECT, "burst_wrap")
        assert result["ok"] is True
        assert result["result"]["module"] == "dma_axi_master"

    def test_find_signal_with_module_filter(self) -> None:
        result = rtl_get_source_snippet(
            PROJECT, "ll_mode_en", module_filter="dma_desc_parser"
        )
        assert result["ok"] is True
        assert result["result"]["module"] == "dma_desc_parser"

    def test_signal_not_found(self) -> None:
        result = rtl_get_source_snippet(PROJECT, "zzzznonexistent_signal")
        assert result["ok"] is False
        assert "not found" in result["error"].lower()

    def test_bad_project(self) -> None:
        result = rtl_get_source_snippet("nonexistent_project_xyz", "ll_mode_en")
        assert result["ok"] is False

    def test_has_evidence(self) -> None:
        result = rtl_get_source_snippet(PROJECT, "ll_mode_en")
        assert len(result["evidence"]) > 0
        assert result["evidence"][0]["source_type"] == "rtl"

    def test_line_range_in_result(self) -> None:
        result = rtl_get_source_snippet(PROJECT, "ll_mode_en")
        assert result["ok"] is True
        assert result["result"]["start_line"] >= 1
        assert result["result"]["end_line"] >= result["result"]["start_line"]

    def test_next_actions(self) -> None:
        result = rtl_get_source_snippet(PROJECT, "ll_mode_en")
        assert "rtl_find_signal" in result["next_actions"]
        assert "rtl_trace_fanin" in result["next_actions"]


class TestRtlTraceFanin:
    def test_trace_ll_mode_en(self) -> None:
        result = rtl_trace_fanin(PROJECT, "ll_mode_en")
        assert result["ok"] is True
        assert result["result"]["signal_name"] == "ll_mode_en"
        assert "fanin_signals" in result["result"]
        assert result["result"]["total_fanin"] >= 1

    def test_trace_excludes_target(self) -> None:
        result = rtl_trace_fanin(PROJECT, "ll_mode_en")
        fanin_names = [s["signal_name"] for s in result["result"]["fanin_signals"]]
        assert "ll_mode_en" not in fanin_names

    def test_trace_port(self) -> None:
        result = rtl_trace_fanin(PROJECT, "clk")
        assert result["ok"] is True
        assert result["result"]["total_fanin"] >= 1

    def test_trace_with_module_filter(self) -> None:
        result = rtl_trace_fanin(
            PROJECT, "ll_mode_en", module_filter="dma_desc_parser"
        )
        assert result["ok"] is True
        assert result["result"]["module"] == "dma_desc_parser"

    def test_signal_not_found(self) -> None:
        result = rtl_trace_fanin(PROJECT, "zzzznonexistent_signal")
        assert result["ok"] is False
        assert "not found" in result["error"].lower()

    def test_bad_project(self) -> None:
        result = rtl_trace_fanin("nonexistent_project_xyz", "ll_mode_en")
        assert result["ok"] is False

    def test_has_evidence(self) -> None:
        result = rtl_trace_fanin(PROJECT, "ll_mode_en")
        assert len(result["evidence"]) > 0

    def test_elaborated_flag(self) -> None:
        result = rtl_trace_fanin(PROJECT, "ll_mode_en")
        assert result["result"]["elaborated"] is False

    def test_stub_note_present(self) -> None:
        result = rtl_trace_fanin(PROJECT, "ll_mode_en")
        assert "note" in result["result"]
        assert "Same-module" in result["result"]["note"]

    def test_next_actions(self) -> None:
        result = rtl_trace_fanin(PROJECT, "ll_mode_en")
        assert "rtl_find_signal" in result["next_actions"]
        assert "rtl_get_source_snippet" in result["next_actions"]

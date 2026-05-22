"""Tests for RTL MCP tools."""

import pytest

from dv_mcp.dv_context_server.services.project_loader import clear_cache
from dv_mcp.dv_context_server.tools.rtl_tools import rtl_find_signal

PROJECT = "mock_data/dma_subsystem/project_manifest.yaml"


@pytest.fixture(autouse=True)
def _clear():
    clear_cache()
    yield
    clear_cache()


class TestRtlFindSignal:
    def test_find_ll_mode_en(self) -> None:
        result = rtl_find_signal(PROJECT, "ll_mode_en")
        assert result["ok"] is True
        matches = result["result"]["matches"]
        assert len(matches) >= 2  # port + signal
        names = [m["signal_name"] for m in matches]
        assert all(n == "ll_mode_en" for n in names)

    def test_find_burst_wrap(self) -> None:
        result = rtl_find_signal(PROJECT, "burst_wrap")
        assert result["ok"] is True
        assert len(result["result"]["matches"]) >= 1

    def test_find_error_irq(self) -> None:
        result = rtl_find_signal(PROJECT, "error_irq")
        assert result["ok"] is True
        matches = result["result"]["matches"]
        assert any(m["module"] == "dma_int_ctrl" for m in matches)

    def test_module_filter(self) -> None:
        result = rtl_find_signal(PROJECT, "ll_mode_en", module_filter="dma_desc_parser")
        assert result["ok"] is True
        for m in result["result"]["matches"]:
            assert "desc_parser" in m["module"]

    def test_no_match(self) -> None:
        result = rtl_find_signal(PROJECT, "zzzznonexistent_signal")
        assert result["ok"] is True
        assert len(result["result"]["matches"]) == 0

    def test_has_evidence(self) -> None:
        result = rtl_find_signal(PROJECT, "ll_mode_en")
        assert len(result["evidence"]) > 0

    def test_elaborated_flag(self) -> None:
        result = rtl_find_signal(PROJECT, "ll_mode_en")
        assert result["result"]["elaborated"] is False  # MVP is not elaborated

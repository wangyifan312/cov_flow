"""Tests for RTL MCP tools."""

import pytest

from dv_mcp.dv_context_server.services.project_loader import clear_cache
from dv_mcp.dv_context_server.tools.rtl_tools import rtl_find_signal, rtl_get_instance_info

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


class TestRtlGetInstanceInfo:
    def test_get_module_by_name(self) -> None:
        result = rtl_get_instance_info(PROJECT, module_name="dma_desc_parser")
        assert result["ok"] is True
        assert result["result"]["module"] == "dma_desc_parser"
        assert "ports" in result["result"]
        assert "signals" in result["result"]
        assert "fsm_states" in result["result"]

    def test_get_dma_core(self) -> None:
        result = rtl_get_instance_info(PROJECT, module_name="dma_core")
        assert result["ok"] is True
        assert result["result"]["module"] == "dma_core"
        instances = result["result"]["instances"]
        assert len(instances) >= 1
        inst_names = [i["name"] for i in instances]
        assert "u_desc_parser" in inst_names

    def test_module_not_found(self) -> None:
        result = rtl_get_instance_info(PROJECT, module_name="nonexistent_module_xyz")
        assert result["ok"] is False
        assert "not found" in result["error"].lower()

    def test_both_none_error(self) -> None:
        result = rtl_get_instance_info(PROJECT)
        assert result["ok"] is False
        assert "at least one" in result["error"].lower()

    def test_instance_path(self) -> None:
        result = rtl_get_instance_info(PROJECT, instance_path="dma_subsystem.u_dma")
        assert result["ok"] is True
        # Should resolve u_dma instance to dma_core module
        assert result["result"]["module"] in ("dma_core", "dma_subsystem")

    def test_has_evidence(self) -> None:
        result = rtl_get_instance_info(PROJECT, module_name="dma_desc_parser")
        assert len(result["evidence"]) > 0

    def test_has_ports_and_signals(self) -> None:
        result = rtl_get_instance_info(PROJECT, module_name="dma_desc_parser")
        assert result["ok"] is True
        ports = result["result"]["ports"]
        assert isinstance(ports, list)
        assert len(ports) >= 1
        assert "ll_mode_en" in ports

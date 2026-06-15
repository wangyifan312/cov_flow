"""Tests for simulation MCP tools (real-mode only, mock branches removed)."""

import pytest

from dv_mcp.dv_context_server.services.project_loader import clear_cache
from dv_mcp.dv_context_server.tools.sim_tools import (
    sim_get_test_result,
    sim_run_targeted_test,
    wave_check_condition,
)

PROJECT = "mock_data/dma_subsystem/project_manifest.yaml"


@pytest.fixture(autouse=True)
def _clear():
    clear_cache()
    yield
    clear_cache()


class TestSimRunTargetedTest:
    def test_requires_confirm(self) -> None:
        result = sim_run_targeted_test(PROJECT, "dma_linked_list_desc_test", 1, confirm=False)
        assert result["ok"] is True
        assert "requires confirm" in result["result"]["message"]
        assert result["safety"]["confirmed"] is False
        assert result["safety"]["policy_checked"] is True

    def test_has_audit_field(self) -> None:
        result = sim_run_targeted_test(PROJECT, "dma_linked_list_desc_test", 1, confirm=False)
        assert "audit" in result
        audit = result["audit"]
        assert "user" in audit
        assert "tool" in audit
        assert "arg_hash" in audit
        assert "timestamp" in audit
        assert "result_size" in audit

    def test_has_safety_field(self) -> None:
        result = sim_run_targeted_test(PROJECT, "dma_linked_list_desc_test", 1, confirm=False)
        assert "safety" in result
        safety = result["safety"]
        assert safety["policy_checked"] is True
        assert safety["confirmed"] is False


class TestSimGetTestResult:
    def test_load_persisted_result(self) -> None:
        """Load pre-stored sim_result.json."""
        result = sim_get_test_result(PROJECT, "dma_linked_list_desc_test", seed=1)
        assert result["ok"] is True
        assert result["result"]["test"] == "dma_linked_list_desc_test"
        assert result["result"]["seed"] == 1
        assert result["result"]["compile"] is not None
        assert result["result"]["compile"]["status"] == "pass"
        assert result["result"]["run"] is not None
        assert result["result"]["run"]["status"] == "pass"

    def test_missing_result(self) -> None:
        result = sim_get_test_result(PROJECT, "nonexistent_test", seed=999)
        assert result["ok"] is False
        assert "no simulation results" in result["error"].lower()


class TestWaveCheckCondition:
    def test_returns_ok(self) -> None:
        result = wave_check_condition(PROJECT, "top.dut.axi_valid", "axi_valid && axi_ready")
        assert result["ok"] is True
        assert result["result"]["signal_path"] == "top.dut.axi_valid"
        assert result["result"]["condition"] == "axi_valid && axi_ready"

    def test_stub_mode(self) -> None:
        result = wave_check_condition(PROJECT, "top.dut.axi_valid", "axi_valid")
        assert result["ok"] is True
        assert result["result"]["mode"] == "stub"
        assert result["result"]["condition_met"] is None

    def test_note_present(self) -> None:
        result = wave_check_condition(PROJECT, "top.dut.axi_valid", "axi_valid")
        assert result["ok"] is True
        assert "Verdi/NPI" in result["result"]["note"]

    def test_has_evidence(self) -> None:
        result = wave_check_condition(PROJECT, "top.dut.axi_valid", "axi_valid")
        assert len(result["evidence"]) > 0

    def test_with_time_range(self) -> None:
        result = wave_check_condition(
            PROJECT, "top.dut.axi_valid", "axi_valid", time_range="0,1000",
        )
        assert result["ok"] is True
        assert result["result"]["time_range"] == [0, 1000]

    def test_invalid_time_range(self) -> None:
        result = wave_check_condition(
            PROJECT, "top.dut.axi_valid", "axi_valid", time_range="invalid",
        )
        assert result["ok"] is False
        assert "time_range" in result["error"].lower()

    def test_has_audit(self) -> None:
        result = wave_check_condition(PROJECT, "top.dut.axi_valid", "axi_valid")
        assert "audit" in result

    def test_signal_values_from_adapter(self) -> None:
        result = wave_check_condition(PROJECT, "top.dut.axi_valid", "axi_valid")
        assert result["ok"] is True
        assert isinstance(result["result"]["signal_values"], list)

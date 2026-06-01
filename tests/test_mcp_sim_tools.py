"""Tests for simulation MCP tools."""

import pytest

from dv_mcp.dv_context_server.services.project_loader import clear_cache
from dv_mcp.dv_context_server.tools.sim_tools import (
    cov_get_coverage_diff,
    sim_get_test_result,
    sim_run_targeted_test,
    sim_search_log,
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

    def test_confirmed_returns_mock_result(self) -> None:
        result = sim_run_targeted_test(PROJECT, "dma_linked_list_desc_test", 1, confirm=True)
        assert result["ok"] is True
        assert result["result"]["test"] == "dma_linked_list_desc_test"
        assert result["result"]["seed"] == 1
        assert result["result"]["compile_status"] == "pass"
        assert result["result"]["sim_status"] == "pass"
        assert result["result"]["dry_run"] is True
        assert result["safety"]["confirmed"] is True

    def test_has_audit_field(self) -> None:
        result = sim_run_targeted_test(PROJECT, "dma_linked_list_desc_test", 1, confirm=True)
        assert "audit" in result
        audit = result["audit"]
        assert "user" in audit
        assert "tool" in audit
        assert "arg_hash" in audit
        assert "timestamp" in audit
        assert "result_size" in audit

    def test_has_safety_field(self) -> None:
        result = sim_run_targeted_test(PROJECT, "dma_linked_list_desc_test", 1, confirm=True)
        assert "safety" in result
        safety = result["safety"]
        assert safety["policy_checked"] is True
        assert safety["confirmed"] is True
        assert "command_template_used" in safety

    def test_command_from_manifest_template(self) -> None:
        result = sim_run_targeted_test(PROJECT, "my_test", 42, confirm=True)
        assert "my_test" in result["result"]["run_command"]
        assert "42" in result["result"]["run_command"]


class TestSimGetTestResult:
    def test_existing_log(self) -> None:
        result = sim_get_test_result(PROJECT, "dma_linked_list_desc_test", seed=1)
        assert result["ok"] is True
        assert result["result"]["sim_status"] == "pass"

    def test_missing_log(self) -> None:
        result = sim_get_test_result(PROJECT, "nonexistent_test", seed=999)
        assert result["ok"] is True
        assert result["result"]["sim_status"] == "not_found"


class TestSimSearchLog:
    def test_search_keyword(self) -> None:
        result = sim_search_log(PROJECT, "dma_linked_list_desc_test", 1, "PASSED")
        assert result["ok"] is True
        assert result["result"]["total_matches"] >= 1
        assert len(result["result"]["matches"]) >= 1

    def test_search_no_match(self) -> None:
        result = sim_search_log(PROJECT, "dma_linked_list_desc_test", 1, "ZZZZNONEXISTENT")
        assert result["ok"] is True
        assert result["result"]["total_matches"] == 0

    def test_log_not_found(self) -> None:
        result = sim_search_log(PROJECT, "nonexistent_test", 999, "keyword")
        assert result["ok"] is False


class TestCovGetCoverageDiff:
    def test_full_diff(self) -> None:
        result = cov_get_coverage_diff(PROJECT)
        assert result["ok"] is True
        assert result["result"]["summary"]["total_gaps"] == 27
        assert result["result"]["summary"]["newly_covered"] == 5

    def test_filter_by_gap_id(self) -> None:
        result = cov_get_coverage_diff(PROJECT, gap_id="GAP_0001")
        assert result["ok"] is True
        assert len(result["result"]["gap_deltas"]) == 1
        assert result["result"]["gap_deltas"][0]["closed"] is True

    def test_has_audit(self) -> None:
        result = cov_get_coverage_diff(PROJECT)
        assert "audit" in result

    def test_diff_includes_code_coverage_types(self) -> None:
        result = cov_get_coverage_diff(PROJECT)
        assert result["ok"] is True
        by_type = result["result"]["summary"]["by_type"]
        assert "line" in by_type
        assert "branch" in by_type
        assert "toggle" in by_type
        assert "fsm" in by_type
        assert "assert" in by_type

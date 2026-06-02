"""Large dataset behavior tests using axi2ahb (982 gaps).

Verifies truncation, pagination, and context budget behavior
when working with a realistic coverage index.
"""

import json

import pytest

from dv_mcp.dv_context_server.services.project_loader import clear_cache
from dv_mcp.dv_context_server.tools.coverage_tools import cov_list_uncovered

AXI2AHB = "mock_data/axi2ahb/project_manifest.yaml"


@pytest.fixture(autouse=True)
def _clear():
    clear_cache()
    yield
    clear_cache()


class TestLargeDatasetTruncation:
    def test_default_top_n_truncates(self) -> None:
        """Default top_n=20 should truncate 982 gaps."""
        resp = cov_list_uncovered(AXI2AHB, coverage_type="all")
        assert resp["ok"] is True
        assert resp["truncated"] is True
        assert len(resp["result"]["gaps"]) == 20
        assert resp["result"]["total_uncovered"] == 982

    def test_top_n_10_returns_exactly_10(self) -> None:
        """Explicit top_n=10 should return exactly 10 gaps."""
        resp = cov_list_uncovered(AXI2AHB, coverage_type="all", top_n=10)
        assert resp["ok"] is True
        assert len(resp["result"]["gaps"]) == 10
        assert resp["truncated"] is True
        assert resp["result"]["total_uncovered"] == 982

    def test_top_n_50_returns_exactly_50(self) -> None:
        """top_n=50 should return exactly 50 gaps (capped by tool max)."""
        resp = cov_list_uncovered(AXI2AHB, coverage_type="all", top_n=50)
        assert resp["ok"] is True
        assert len(resp["result"]["gaps"]) == 50
        assert resp["truncated"] is True

    def test_toggle_type_has_many_gaps(self) -> None:
        """toggle type has 763 gaps, should truncate with default top_n."""
        resp = cov_list_uncovered(AXI2AHB, coverage_type="toggle")
        assert resp["ok"] is True
        assert resp["result"]["total_uncovered"] == 763
        assert resp["truncated"] is True
        assert len(resp["result"]["gaps"]) == 20

    def test_toggle_top_n_10(self) -> None:
        """toggle type with top_n=10."""
        resp = cov_list_uncovered(AXI2AHB, coverage_type="toggle", top_n=10)
        assert resp["ok"] is True
        assert len(resp["result"]["gaps"]) == 10
        assert resp["truncated"] is True
        assert all(g["coverage_type"] == "toggle" for g in resp["result"]["gaps"])

    def test_line_type_returns_126(self) -> None:
        """line type has 126 gaps."""
        resp = cov_list_uncovered(AXI2AHB, coverage_type="line", top_n=50)
        assert resp["ok"] is True
        assert resp["result"]["total_uncovered"] == 126
        assert len(resp["result"]["gaps"]) == 50
        assert resp["truncated"] is True


class TestLargeDatasetContextBudget:
    def test_result_size_within_budget(self) -> None:
        """A top_n=20 result should stay well within 100KB context budget."""
        resp = cov_list_uncovered(AXI2AHB, coverage_type="all", top_n=20)
        assert resp["ok"] is True
        serialized = json.dumps(resp)
        # 100KB budget for normal gaps
        assert len(serialized.encode("utf-8")) < 100_000

    def test_top_n_50_within_budget(self) -> None:
        """Even top_n=50 should stay within 100KB."""
        resp = cov_list_uncovered(AXI2AHB, coverage_type="all", top_n=50)
        assert resp["ok"] is True
        serialized = json.dumps(resp)
        assert len(serialized.encode("utf-8")) < 100_000


class TestLargeDatasetFiltering:
    def test_filter_functional(self) -> None:
        """functional type should return 16 gaps."""
        resp = cov_list_uncovered(AXI2AHB, coverage_type="functional", top_n=50)
        assert resp["ok"] is True
        assert resp["result"]["total_uncovered"] == 16
        assert resp["truncated"] is False  # 16 < 50

    def test_filter_branch(self) -> None:
        resp = cov_list_uncovered(AXI2AHB, coverage_type="branch", top_n=50)
        assert resp["ok"] is True
        assert resp["result"]["total_uncovered"] == 40

    def test_filter_condition(self) -> None:
        resp = cov_list_uncovered(AXI2AHB, coverage_type="condition", top_n=50)
        assert resp["ok"] is True
        assert resp["result"]["total_uncovered"] == 32

    def test_filter_fsm(self) -> None:
        resp = cov_list_uncovered(AXI2AHB, coverage_type="fsm", top_n=50)
        assert resp["ok"] is True
        assert resp["result"]["total_uncovered"] == 1
        assert resp["truncated"] is False

    def test_filter_assert(self) -> None:
        resp = cov_list_uncovered(AXI2AHB, coverage_type="assert", top_n=50)
        assert resp["ok"] is True
        assert resp["result"]["total_uncovered"] == 4
        assert resp["truncated"] is False


class TestLargeDatasetProjectNameResolution:
    def test_axi2ahb_by_name(self) -> None:
        """axi2ahb should be resolvable by project name."""
        resp = cov_list_uncovered("axi2ahb", coverage_type="functional", top_n=5)
        assert resp["ok"] is True
        assert resp["result"]["total_uncovered"] == 16

    def test_dma_subsystem_by_name(self) -> None:
        resp = cov_list_uncovered("dma_subsystem", coverage_type="all", top_n=50)
        assert resp["ok"] is True
        assert resp["result"]["total_uncovered"] == 27

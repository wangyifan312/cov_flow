"""Integration tests for tb_find_tests_for_gap MCP tool."""

import pytest

from dv_mcp.dv_context_server.services.project_loader import clear_cache
from dv_mcp.dv_context_server.tools.tb_tools import tb_find_tests_for_gap

AXI2AHB = "mock_data/axi2ahb/project_manifest.yaml"
DMA = "mock_data/dma_subsystem/project_manifest.yaml"


@pytest.fixture(autouse=True)
def _clear():
    clear_cache()
    yield
    clear_cache()


class TestAxi2ahbBurstGaps:
    """Burst-related gap lookups."""

    def test_incr16_gap(self) -> None:
        result = tb_find_tests_for_gap(AXI2AHB, "GAP_0003")
        assert result["ok"] is True
        r = result["result"]
        assert "incr" in r["semantic_keywords"]
        assert "16" in r["semantic_keywords"]
        seq_names = [s["name"] for s in r["matching_sequences"]]
        assert "incr_random_len_size_wr_virt_seq" in seq_names

    def test_wrap8_gap(self) -> None:
        result = tb_find_tests_for_gap(AXI2AHB, "GAP_0006")
        assert result["ok"] is True
        r = result["result"]
        assert "wrap" in r["semantic_keywords"]
        assert "8" in r["semantic_keywords"]
        seq_names = [s["name"] for s in r["matching_sequences"]]
        assert "wrap_random_len_size_wr_virt_seq" in seq_names

    def test_burst_gap_assessment(self) -> None:
        result = tb_find_tests_for_gap(AXI2AHB, "GAP_0003")
        r = result["result"]
        assert r["gap_assessment"] == "existing_test_likely_covers"

    def test_incr_only_gap(self) -> None:
        result = tb_find_tests_for_gap(AXI2AHB, "GAP_0009")
        assert result["ok"] is True
        assert "incr" in result["result"]["semantic_keywords"]


class TestAxi2ahbWaitGaps:
    """Wait-related gap lookups."""

    def test_wait_gap(self) -> None:
        result = tb_find_tests_for_gap(AXI2AHB, "GAP_0010")
        assert result["ok"] is True
        kw = result["result"]["semantic_keywords"]
        assert any("wait" in k for k in kw)

    def test_wait_delay_gap(self) -> None:
        result = tb_find_tests_for_gap(AXI2AHB, "GAP_0011")
        assert result["ok"] is True
        kw = result["result"]["semantic_keywords"]
        assert "wait" in kw or "6" in kw


class TestAxi2ahbCrossGaps:
    """Cross-bin gap lookups."""

    def test_cross_rw_burst_gap(self) -> None:
        result = tb_find_tests_for_gap(AXI2AHB, "GAP_0014")
        assert result["ok"] is True
        kw = result["result"]["semantic_keywords"]
        assert "incr" in kw
        assert "wrap" in kw
        seq_names = [
            s["name"] for s in result["result"]["matching_sequences"]
        ]
        assert len(seq_names) > 0

    def test_cross_wait_rw_gap(self) -> None:
        result = tb_find_tests_for_gap(AXI2AHB, "GAP_0015")
        assert result["ok"] is True

    def test_cross_trans_rw_gap(self) -> None:
        result = tb_find_tests_for_gap(AXI2AHB, "GAP_0016")
        assert result["ok"] is True
        kw = result["result"]["semantic_keywords"]
        assert "seq" in kw or "nonseq" in kw


class TestDmaSubsystemGaps:
    """dma_subsystem gap lookups."""

    def test_dma_linked_list_gap(self) -> None:
        result = tb_find_tests_for_gap(DMA, "GAP_0001")
        assert result["ok"] is True
        kw = result["result"]["semantic_keywords"]
        assert "linked" in kw
        assert "list" in kw

    def test_dma_chain_gap(self) -> None:
        result = tb_find_tests_for_gap(DMA, "GAP_0003")
        assert result["ok"] is True
        assert "chain" in result["result"]["semantic_keywords"]


class TestErrorCases:
    """Error handling tests."""

    def test_nonexistent_gap(self) -> None:
        result = tb_find_tests_for_gap(AXI2AHB, "GAP_9999")
        assert result["ok"] is False
        assert "not found" in result["error"].lower()

    def test_code_coverage_gap_rejected(self) -> None:
        result = tb_find_tests_for_gap(AXI2AHB, "GAP_L001")
        assert result["ok"] is False
        assert "functional" in result["error"].lower()

    def test_bad_project(self) -> None:
        result = tb_find_tests_for_gap("nonexistent_manifest.yaml", "GAP_0001")
        assert result["ok"] is False


class TestEnvelopeStructure:
    """Verify envelope fields are correct."""

    def test_result_has_required_fields(self) -> None:
        result = tb_find_tests_for_gap(AXI2AHB, "GAP_0006")
        assert result["ok"] is True
        r = result["result"]
        required = [
            "gap_id", "covergroup", "coverpoint", "bin",
            "coverage_type", "semantic_keywords",
            "matching_sequences", "matching_tests",
            "gap_assessment", "assessment_confidence",
        ]
        for field in required:
            assert field in r, f"Missing field: {field}"

    def test_evidence_present(self) -> None:
        result = tb_find_tests_for_gap(AXI2AHB, "GAP_0006")
        assert isinstance(result["evidence"], list)
        assert len(result["evidence"]) > 0

    def test_next_actions(self) -> None:
        result = tb_find_tests_for_gap(AXI2AHB, "GAP_0006")
        assert "cov_get_coverpoint_source" in result["next_actions"]

    def test_assessment_confidence_is_float(self) -> None:
        result = tb_find_tests_for_gap(AXI2AHB, "GAP_0006")
        conf = result["result"]["assessment_confidence"]
        assert isinstance(conf, float)
        assert 0.0 <= conf <= 1.0

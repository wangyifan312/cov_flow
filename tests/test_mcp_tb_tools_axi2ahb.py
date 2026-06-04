"""Integration tests for tb_get_existing_tests_for_feature with axi2ahb real TB data."""

import pytest

from dv_mcp.dv_context_server.services.project_loader import clear_cache
from dv_mcp.dv_context_server.tools.tb_tools import tb_get_existing_tests_for_feature

AXI2AHB = "mock_data/axi2ahb/project_manifest.yaml"


@pytest.fixture(autouse=True)
def _clear():
    clear_cache()
    yield
    clear_cache()


class TestAxi2ahbBurstFeature:
    """feature='burst' should match wrap/incr/fixed sequences."""

    def test_returns_ok(self) -> None:
        result = tb_get_existing_tests_for_feature(AXI2AHB, "burst")
        assert result["ok"] is True

    def test_matches_sequences(self) -> None:
        result = tb_get_existing_tests_for_feature(AXI2AHB, "burst")
        seq_names = [s["name"] for s in result["result"]["sequences"]]
        assert "base_virtual_sequence" in seq_names

    def test_matches_tests(self) -> None:
        result = tb_get_existing_tests_for_feature(AXI2AHB, "burst")
        test_names = [t["name"] for t in result["result"]["existing_tests"]]
        assert len(test_names) >= 1

    def test_api_methods_included(self) -> None:
        result = tb_get_existing_tests_for_feature(AXI2AHB, "burst")
        seqs = result["result"]["sequences"]
        base_seq = next(s for s in seqs if s["name"] == "base_virtual_sequence")
        assert len(base_seq["api_methods"]) == 10
        assert base_seq["api_methods_truncated"] is True

    def test_non_base_seq_full_methods(self) -> None:
        result = tb_get_existing_tests_for_feature(AXI2AHB, "burst")
        seqs = result["result"]["sequences"]
        mixed = next(
            (s for s in seqs if s["name"] == "mixed_random_traffic_virt_seq"),
            None,
        )
        assert mixed is not None, "mixed_random_traffic_virt_seq not found"
        assert mixed["api_methods_truncated"] is False
        assert len(mixed["api_methods"]) > 10


class TestAxi2ahbWrapFeature:
    """feature='wrap' should match wrap sequences."""

    def test_matches_wrap_seq(self) -> None:
        result = tb_get_existing_tests_for_feature(AXI2AHB, "wrap")
        seq_names = [s["name"] for s in result["result"]["sequences"]]
        assert "wrap_random_len_size_wr_virt_seq" in seq_names

    def test_matches_wrap_test(self) -> None:
        result = tb_get_existing_tests_for_feature(AXI2AHB, "wrap")
        test_names = [t["name"] for t in result["result"]["existing_tests"]]
        assert "wrap_random_len_size_wr_test" in test_names


class TestAxi2ahbScopeFilter:
    """scope parameter filtering."""

    def test_scope_all(self) -> None:
        result = tb_get_existing_tests_for_feature(AXI2AHB, "write", scope="all")
        assert "sequences" in result["result"]
        assert "existing_tests" in result["result"]
        assert "base_tests" in result["result"]
        assert "config_knobs" in result["result"]

    def test_scope_tests_only(self) -> None:
        result = tb_get_existing_tests_for_feature(AXI2AHB, "write", scope="tests")
        assert "existing_tests" in result["result"]
        assert "sequences" not in result["result"]
        assert "base_tests" in result["result"]
        assert "config_knobs" in result["result"]

    def test_scope_sequences_only(self) -> None:
        result = tb_get_existing_tests_for_feature(AXI2AHB, "write", scope="sequences")
        assert "sequences" in result["result"]
        assert "existing_tests" not in result["result"]
        assert "base_tests" not in result["result"]
        assert "config_knobs" not in result["result"]

    def test_scope_invalid(self) -> None:
        result = tb_get_existing_tests_for_feature(AXI2AHB, "write", scope="invalid")
        assert result["ok"] is False
        assert "Invalid scope" in result["error"]


class TestAxi2ahbBaseTestsAndKnobs:
    """base_tests and config_knobs are returned."""

    def test_base_tests_present(self) -> None:
        result = tb_get_existing_tests_for_feature(AXI2AHB, "burst")
        base_tests = result["result"]["base_tests"]
        assert len(base_tests) == 1
        assert base_tests[0]["name"] == "base_test"

    def test_config_knobs_present(self) -> None:
        result = tb_get_existing_tests_for_feature(AXI2AHB, "burst")
        knobs = result["result"]["config_knobs"]
        assert len(knobs) >= 10


class TestAxi2ahbNoMatch:
    """No match returns empty lists."""

    def test_no_match(self) -> None:
        result = tb_get_existing_tests_for_feature(AXI2AHB, "zzzznonexistent")
        assert result["ok"] is True
        assert len(result["result"]["sequences"]) == 0
        assert len(result["result"]["existing_tests"]) == 0

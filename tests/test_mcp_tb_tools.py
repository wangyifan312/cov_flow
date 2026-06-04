"""Tests for testbench MCP tools."""

import pytest

from dv_mcp.dv_context_server.services.project_loader import clear_cache
from dv_mcp.dv_context_server.tools.tb_tools import tb_get_existing_tests_for_feature

PROJECT = "mock_data/dma_subsystem/project_manifest.yaml"


@pytest.fixture(autouse=True)
def _clear():
    clear_cache()
    yield
    clear_cache()


class TestTbGetExistingTestsForFeature:
    def test_descriptor_feature(self) -> None:
        result = tb_get_existing_tests_for_feature(PROJECT, "descriptor")
        assert result["ok"] is True
        seqs = result["result"]["sequences"]
        tests = result["result"]["existing_tests"]
        assert len(seqs) >= 1
        assert len(tests) >= 1
        # Verify api_methods field is present (list type) on all matched sequences
        for seq in seqs:
            assert "api_methods" in seq
            assert isinstance(seq["api_methods"], list)
            assert "api_methods_truncated" in seq
            assert isinstance(seq["api_methods_truncated"], bool)

    def test_linked_list_feature(self) -> None:
        result = tb_get_existing_tests_for_feature(PROJECT, "linked_list")
        assert result["ok"] is True
        seq_names = [s["name"] for s in result["result"]["sequences"]]
        assert "dma_desc_base_seq" in seq_names

    def test_interrupt_feature(self) -> None:
        result = tb_get_existing_tests_for_feature(PROJECT, "interrupt")
        assert result["ok"] is True
        seq_names = [s["name"] for s in result["result"]["sequences"]]
        assert "dma_interrupt_seq" in seq_names

    def test_includes_base_tests(self) -> None:
        result = tb_get_existing_tests_for_feature(PROJECT, "descriptor")
        base_tests = result["result"]["base_tests"]
        assert len(base_tests) >= 1
        assert base_tests[0]["name"] == "dma_base_test"

    def test_includes_config_knobs(self) -> None:
        result = tb_get_existing_tests_for_feature(PROJECT, "descriptor")
        knobs = result["result"]["config_knobs"]
        assert len(knobs) >= 1

    def test_no_match(self) -> None:
        result = tb_get_existing_tests_for_feature(PROJECT, "zzzznonexistent")
        assert result["ok"] is True
        assert len(result["result"]["sequences"]) == 0
        assert len(result["result"]["existing_tests"]) == 0

    def test_has_evidence(self) -> None:
        result = tb_get_existing_tests_for_feature(PROJECT, "descriptor")
        assert len(result["evidence"]) > 0

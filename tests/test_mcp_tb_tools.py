"""Tests for testbench MCP tools."""

import pytest

from dv_mcp.dv_context_server.services.project_loader import clear_cache
from dv_mcp.dv_context_server.tools.tb_tools import (
    tb_find_config_knob,
    tb_find_sequence,
    tb_get_base_test_template,
    tb_get_existing_tests_for_feature,
    tb_get_sequence_source_snippet,
)

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


class TestTbFindSequence:
    def test_find_normal_desc_seq(self) -> None:
        result = tb_find_sequence(PROJECT, "dma_normal_desc_seq")
        assert result["ok"] is True
        matches = result["result"]["matches"]
        assert len(matches) >= 1
        assert matches[0]["name"] == "dma_normal_desc_seq"

    def test_fuzzy_match(self) -> None:
        result = tb_find_sequence(PROJECT, "desc")
        assert result["ok"] is True
        assert len(result["result"]["matches"]) >= 1

    def test_sequence_not_found(self) -> None:
        result = tb_find_sequence(PROJECT, "nonexistent_seq_xyz")
        assert result["ok"] is False
        assert "not found" in result["error"].lower()

    def test_has_evidence(self) -> None:
        result = tb_find_sequence(PROJECT, "dma_normal_desc_seq")
        assert len(result["evidence"]) > 0

    def test_has_api_methods(self) -> None:
        result = tb_find_sequence(PROJECT, "dma_normal_desc_seq")
        matches = result["result"]["matches"]
        assert "api_methods" in matches[0]
        assert isinstance(matches[0]["api_methods"], list)

    def test_has_feature_tags(self) -> None:
        result = tb_find_sequence(PROJECT, "dma_normal_desc_seq")
        matches = result["result"]["matches"]
        assert "feature_tags" in matches[0]


class TestTbGetBaseTestTemplate:
    def test_get_all_base_tests(self) -> None:
        result = tb_get_base_test_template(PROJECT)
        assert result["ok"] is True
        base_tests = result["result"]["base_tests"]
        assert len(base_tests) >= 1
        assert base_tests[0]["name"] == "dma_base_test"

    def test_get_specific_base_test(self) -> None:
        result = tb_get_base_test_template(PROJECT, base_test_name="dma_base_test")
        assert result["ok"] is True
        assert len(result["result"]["base_tests"]) == 1
        bt = result["result"]["base_tests"][0]
        assert bt["name"] == "dma_base_test"
        assert "config_knobs" in bt

    def test_case_insensitive(self) -> None:
        result = tb_get_base_test_template(PROJECT, base_test_name="DMA_BASE_TEST")
        assert result["ok"] is True
        assert result["result"]["base_tests"][0]["name"] == "dma_base_test"

    def test_base_test_not_found(self) -> None:
        result = tb_get_base_test_template(PROJECT, base_test_name="nonexistent_base_test")
        assert result["ok"] is False
        assert "not found" in result["error"].lower()

    def test_has_evidence(self) -> None:
        result = tb_get_base_test_template(PROJECT)
        assert len(result["evidence"]) > 0

    def test_has_config_knobs(self) -> None:
        result = tb_get_base_test_template(PROJECT, base_test_name="dma_base_test")
        bt = result["result"]["base_tests"][0]
        assert "config_knobs" in bt
        assert isinstance(bt["config_knobs"], list)


class TestTbFindConfigKnob:
    def test_find_num_channels(self) -> None:
        result = tb_find_config_knob(PROJECT, "num_channels")
        assert result["ok"] is True
        matches = result["result"]["matches"]
        assert len(matches) >= 1
        assert matches[0]["name"] == "num_channels"

    def test_fuzzy_match(self) -> None:
        result = tb_find_config_knob(PROJECT, "channel")
        assert result["ok"] is True
        assert len(result["result"]["matches"]) >= 1

    def test_knob_not_found(self) -> None:
        result = tb_find_config_knob(PROJECT, "nonexistent_knob_xyz")
        assert result["ok"] is False
        assert "not found" in result["error"].lower()

    def test_has_evidence(self) -> None:
        result = tb_find_config_knob(PROJECT, "num_channels")
        assert len(result["evidence"]) > 0

    def test_has_all_fields(self) -> None:
        result = tb_find_config_knob(PROJECT, "num_channels")
        knob = result["result"]["matches"][0]
        for key in ("name", "type", "default", "plusarg"):
            assert key in knob, f"Missing key: {key}"


class TestTbGetSequenceSourceSnippet:
    def test_exact_match(self) -> None:
        result = tb_get_sequence_source_snippet(PROJECT, "dma_normal_desc_seq")
        assert result["ok"] is True
        assert result["result"]["name"] == "dma_normal_desc_seq"
        assert "source_snippet" in result["result"]
        assert len(result["result"]["source_snippet"]) > 0
        assert result["result"]["total_lines"] > 0

    def test_fuzzy_match(self) -> None:
        result = tb_get_sequence_source_snippet(PROJECT, "normal_desc")
        assert result["ok"] is True
        assert result["result"]["name"] == "dma_normal_desc_seq"
        assert "source_snippet" in result["result"]

    def test_not_found(self) -> None:
        result = tb_get_sequence_source_snippet(PROJECT, "nonexistent_seq_xyz")
        assert result["ok"] is False
        assert "not found" in result["error"].lower()

    def test_evidence_present(self) -> None:
        result = tb_get_sequence_source_snippet(PROJECT, "dma_normal_desc_seq")
        assert len(result["evidence"]) > 0
        assert result["evidence"][0]["source_type"] == "testbench"

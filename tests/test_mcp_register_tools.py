"""Tests for register MCP tools."""

import pytest

from dv_mcp.dv_context_server.services.project_loader import clear_cache
from dv_mcp.dv_context_server.tools.register_tools import (
    reg_find_field,
    reg_find_fields_affecting_feature,
    reg_get_ral_path,
    reg_search_by_description,
)

PROJECT = "mock_data/dma_subsystem/project_manifest.yaml"


@pytest.fixture(autouse=True)
def _clear():
    clear_cache()
    yield
    clear_cache()


class TestRegFindFieldsAffectingFeature:
    def test_linked_list_feature(self) -> None:
        result = reg_find_fields_affecting_feature(PROJECT, "linked_list")
        assert result["ok"] is True
        fields = result["result"]["fields"]
        assert len(fields) >= 1
        # LL_MODE_EN should be the top match
        assert fields[0]["field"] == "LL_MODE_EN"
        assert fields[0]["register"] == "DMA_CFG"

    def test_interrupt_feature(self) -> None:
        result = reg_find_fields_affecting_feature(PROJECT, "interrupt")
        assert result["ok"] is True
        fields = result["result"]["fields"]
        assert len(fields) >= 1
        field_names = [f["field"] for f in fields]
        assert "ERROR_MASK" in field_names or "COMP_MASK" in field_names

    def test_power_feature(self) -> None:
        result = reg_find_fields_affecting_feature(PROJECT, "power")
        assert result["ok"] is True
        fields = result["result"]["fields"]
        field_names = [f["field"] for f in fields]
        assert "CLOCK_GATE_EN" in field_names or "RET_EN" in field_names

    def test_no_match(self) -> None:
        result = reg_find_fields_affecting_feature(PROJECT, "zzzznonexistent")
        assert result["ok"] is True
        assert len(result["result"]["fields"]) == 0

    def test_has_ral_path(self) -> None:
        result = reg_find_fields_affecting_feature(PROJECT, "linked_list")
        fields = result["result"]["fields"]
        assert fields[0]["ral_path"] == "ral.dma.DMA_CFG.LL_MODE_EN"

    def test_has_evidence(self) -> None:
        result = reg_find_fields_affecting_feature(PROJECT, "linked_list")
        assert len(result["evidence"]) > 0

    def test_relevance_sorted(self) -> None:
        result = reg_find_fields_affecting_feature(PROJECT, "descriptor")
        fields = result["result"]["fields"]
        if len(fields) > 1:
            assert fields[0]["relevance"] >= fields[1]["relevance"]


class TestRegFindField:
    def test_find_ll_mode_en(self) -> None:
        result = reg_find_field(PROJECT, "LL_MODE_EN")
        assert result["ok"] is True
        assert result["result"]["field"] == "LL_MODE_EN"
        assert result["result"]["register"] == "DMA_CFG"
        assert result["result"]["ral_path"] == "ral.dma.DMA_CFG.LL_MODE_EN"

    def test_case_insensitive(self) -> None:
        result = reg_find_field(PROJECT, "ll_mode_en")
        assert result["ok"] is True
        assert result["result"]["field"] == "LL_MODE_EN"

    def test_field_not_found(self) -> None:
        result = reg_find_field(PROJECT, "NONEXISTENT_FIELD_XYZ")
        assert result["ok"] is False
        assert "not found" in result["error"].lower()

    def test_has_evidence(self) -> None:
        result = reg_find_field(PROJECT, "LL_MODE_EN")
        assert len(result["evidence"]) > 0

    def test_has_all_fields(self) -> None:
        result = reg_find_field(PROJECT, "LL_MODE_EN")
        r = result["result"]
        for key in ("register", "field", "offset", "bit_range", "access",
                     "reset", "description", "ral_path", "feature_tags"):
            assert key in r, f"Missing key: {key}"


class TestRegSearchByDescription:
    def test_search_linked_list(self) -> None:
        result = reg_search_by_description(PROJECT, "linked list")
        assert result["ok"] is True
        matches = result["result"]["matches"]
        assert len(matches) >= 1
        field_names = [m["field"] for m in matches]
        assert "LL_MODE_EN" in field_names

    def test_search_descriptor(self) -> None:
        result = reg_search_by_description(PROJECT, "descriptor")
        assert result["ok"] is True
        assert len(result["result"]["matches"]) >= 1

    def test_no_match(self) -> None:
        result = reg_search_by_description(PROJECT, "zzzznonexistent")
        assert result["ok"] is True
        assert len(result["result"]["matches"]) == 0

    def test_has_evidence(self) -> None:
        result = reg_search_by_description(PROJECT, "linked list")
        assert len(result["evidence"]) > 0

    def test_relevance_sorted(self) -> None:
        result = reg_search_by_description(PROJECT, "dma")
        matches = result["result"]["matches"]
        if len(matches) > 1:
            assert matches[0]["relevance"] >= matches[1]["relevance"]

    def test_truncated_to_10(self) -> None:
        result = reg_search_by_description(PROJECT, "dma")
        assert len(result["result"]["matches"]) <= 10


class TestRegGetRalPath:
    def test_get_ral_path(self) -> None:
        result = reg_get_ral_path(PROJECT, "LL_MODE_EN")
        assert result["ok"] is True
        assert result["result"]["ral_path"] == "ral.dma.DMA_CFG.LL_MODE_EN"
        assert result["result"]["field"] == "LL_MODE_EN"
        assert result["result"]["register"] == "DMA_CFG"

    def test_case_insensitive(self) -> None:
        result = reg_get_ral_path(PROJECT, "ll_mode_en")
        assert result["ok"] is True
        assert result["result"]["ral_path"] == "ral.dma.DMA_CFG.LL_MODE_EN"

    def test_field_not_found(self) -> None:
        result = reg_get_ral_path(PROJECT, "NONEXISTENT_FIELD_XYZ")
        assert result["ok"] is False
        assert "not found" in result["error"].lower()

    def test_has_evidence(self) -> None:
        result = reg_get_ral_path(PROJECT, "LL_MODE_EN")
        assert len(result["evidence"]) > 0

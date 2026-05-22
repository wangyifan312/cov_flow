"""Tests for register MCP tools."""

import pytest

from dv_mcp.dv_context_server.services.project_loader import clear_cache
from dv_mcp.dv_context_server.tools.register_tools import reg_find_fields_affecting_feature

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

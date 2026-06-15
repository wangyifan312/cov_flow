"""Tests for spec MCP tools."""

import pytest

from dv_mcp.dv_context_server.services.project_loader import clear_cache
from dv_mcp.dv_context_server.tools.spec_tools import spec_get_section, spec_search

PROJECT = "mock_data/dma_subsystem/project_manifest.yaml"


@pytest.fixture(autouse=True)
def _clear():
    clear_cache()
    yield
    clear_cache()


class TestSpecSearch:
    def test_search_linked_list(self) -> None:
        result = spec_search(PROJECT, "linked_list")
        assert result["ok"] is True
        assert len(result["result"]["matches"]) >= 1
        section = result["result"]["matches"][0]
        assert section["section_id"] == "spec_linked_list_descriptor_mode"

    def test_search_interrupt(self) -> None:
        result = spec_search(PROJECT, "interrupt")
        assert result["ok"] is True
        assert len(result["result"]["matches"]) >= 1

    def test_search_power(self) -> None:
        result = spec_search(PROJECT, "power")
        assert result["ok"] is True
        ids = [m["section_id"] for m in result["result"]["matches"]]
        assert "spec_power_management" in ids

    def test_no_match(self) -> None:
        result = spec_search(PROJECT, "zzzznonexistent")
        assert result["ok"] is True
        assert len(result["result"]["matches"]) == 0

    def test_has_evidence(self) -> None:
        result = spec_search(PROJECT, "descriptor")
        assert len(result["evidence"]) > 0

    def test_max_results_limit(self) -> None:
        result = spec_search(PROJECT, "dma", max_results=2)
        assert len(result["result"]["matches"]) <= 2


class TestSpecGetSection:
    def test_get_linked_list_section(self) -> None:
        result = spec_get_section(PROJECT, "spec_linked_list_descriptor_mode")
        assert result["ok"] is True
        assert result["result"]["section_id"] == "spec_linked_list_descriptor_mode"
        assert "title" in result["result"]
        assert "text" in result["result"]

    def test_get_descriptor_section(self) -> None:
        result = spec_get_section(PROJECT, "spec_descriptor_format")
        assert result["ok"] is True
        assert result["result"]["section_id"] == "spec_descriptor_format"

    def test_section_not_found(self) -> None:
        result = spec_get_section(PROJECT, "nonexistent_section_xyz")
        assert result["ok"] is False
        assert "not found" in result["error"].lower()

    def test_has_evidence(self) -> None:
        result = spec_get_section(PROJECT, "spec_linked_list_descriptor_mode")
        assert len(result["evidence"]) > 0
        assert result["evidence"][0]["evidence_id"] == "spec:spec_linked_list_descriptor_mode"

    def test_feature_tags_present(self) -> None:
        result = spec_get_section(PROJECT, "spec_linked_list_descriptor_mode")
        assert result["ok"] is True
        tags = result["result"]["feature_tags"]
        assert isinstance(tags, list)
        assert len(tags) >= 1

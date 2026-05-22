"""Tests for spec MCP tools."""

import pytest

from dv_mcp.dv_context_server.services.project_loader import clear_cache
from dv_mcp.dv_context_server.tools.spec_tools import spec_search

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
        assert section["section_id"] == "spec_dma_linked_list"

    def test_search_interrupt(self) -> None:
        result = spec_search(PROJECT, "interrupt")
        assert result["ok"] is True
        assert len(result["result"]["matches"]) >= 1

    def test_search_power(self) -> None:
        result = spec_search(PROJECT, "power")
        assert result["ok"] is True
        ids = [m["section_id"] for m in result["result"]["matches"]]
        assert "spec_dma_power" in ids

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

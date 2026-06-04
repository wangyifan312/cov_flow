"""Integration tests for tb_read_source MCP tool.

Uses mock_data/axi2ahb/project_manifest.yaml with pre-built tb_index.json.
When AXI2AHB_ROOT is set, tests read real source files; otherwise the
SourceResolver returns file_not_found and tests verify graceful handling.
"""

import os

import pytest

from dv_mcp.dv_context_server.services.project_loader import clear_cache
from dv_mcp.dv_context_server.tools.tb_tools import tb_read_source

AXI2AHB = "mock_data/axi2ahb/project_manifest.yaml"

# True when real project files are available
_HAS_REAL = bool(os.environ.get("AXI2AHB_ROOT"))


@pytest.fixture(autouse=True)
def _clear() -> None:
    clear_cache()
    yield
    clear_cache()


class TestReadSequence:
    """Read a sequence component."""

    @pytest.mark.skipif(not _HAS_REAL, reason="AXI2AHB_ROOT not set")
    def test_sequence_ok(self) -> None:
        resp = tb_read_source(AXI2AHB, "sequence", "wrap_random_len_size_wr_virt_seq")
        assert resp["ok"] is True

    @pytest.mark.skipif(not _HAS_REAL, reason="AXI2AHB_ROOT not set")
    def test_sequence_file_field(self) -> None:
        resp = tb_read_source(AXI2AHB, "sequence", "wrap_random_len_size_wr_virt_seq")
        r = resp["result"]
        assert r["file"] == "seq_lib/wrap_random_len_size_wr_virt_seq.sv"

    @pytest.mark.skipif(not _HAS_REAL, reason="AXI2AHB_ROOT not set")
    def test_sequence_component_type(self) -> None:
        resp = tb_read_source(AXI2AHB, "sequence", "wrap_random_len_size_wr_virt_seq")
        r = resp["result"]
        assert r["component_type"] == "sequence"
        assert r["name"] == "wrap_random_len_size_wr_virt_seq"

    @pytest.mark.skipif(not _HAS_REAL, reason="AXI2AHB_ROOT not set")
    def test_sequence_content_real(self) -> None:
        resp = tb_read_source(AXI2AHB, "sequence", "wrap_random_len_size_wr_virt_seq")
        content = resp["result"]["content"]
        assert "class wrap_random_len_size_wr_virt_seq" in content
        assert "fd_write_burst" in content

    @pytest.mark.skipif(not _HAS_REAL, reason="AXI2AHB_ROOT not set")
    def test_sequence_total_lines(self) -> None:
        resp = tb_read_source(AXI2AHB, "sequence", "wrap_random_len_size_wr_virt_seq")
        assert resp["result"]["total_lines"] > 0

    @pytest.mark.skipif(not _HAS_REAL, reason="AXI2AHB_ROOT not set")
    def test_sequence_source_mode_real(self) -> None:
        resp = tb_read_source(AXI2AHB, "sequence", "wrap_random_len_size_wr_virt_seq")
        assert resp["result"]["source_mode"] == "real"

    def test_sequence_not_found_when_no_real(self) -> None:
        if _HAS_REAL:
            pytest.skip("AXI2AHB_ROOT is set — real file exists")
        resp = tb_read_source(AXI2AHB, "sequence", "wrap_random_len_size_wr_virt_seq")
        assert resp["ok"] is False
        assert "not found" in resp["error"].lower() or "cannot read" in resp["error"].lower()


class TestReadTest:
    """Read a test component."""

    def test_test_ok(self) -> None:
        if not _HAS_REAL:
            pytest.skip("AXI2AHB_ROOT not set")
        resp = tb_read_source(AXI2AHB, "test", "wrap_random_len_size_wr_test")
        assert resp["ok"] is True

    @pytest.mark.skipif(not _HAS_REAL, reason="AXI2AHB_ROOT not set")
    def test_test_content(self) -> None:
        resp = tb_read_source(AXI2AHB, "test", "wrap_random_len_size_wr_test")
        content = resp["result"]["content"]
        assert "class wrap_random_len_size_wr_test" in content

    @pytest.mark.skipif(not _HAS_REAL, reason="AXI2AHB_ROOT not set")
    def test_test_file_field(self) -> None:
        resp = tb_read_source(AXI2AHB, "test", "wrap_random_len_size_wr_test")
        assert resp["result"]["file"] == "tests/wrap_random_len_size_wr_test.sv"


class TestReadBaseTest:
    """Read a base_test component."""

    def test_base_test_ok(self) -> None:
        if not _HAS_REAL:
            pytest.skip("AXI2AHB_ROOT not set")
        resp = tb_read_source(AXI2AHB, "base_test", "base_test")
        assert resp["ok"] is True

    @pytest.mark.skipif(not _HAS_REAL, reason="AXI2AHB_ROOT not set")
    def test_base_test_content(self) -> None:
        resp = tb_read_source(AXI2AHB, "base_test", "base_test")
        content = resp["result"]["content"]
        assert "class base_test" in content


class TestErrorCases:
    """Error handling tests."""

    def test_invalid_component_type(self) -> None:
        resp = tb_read_source(AXI2AHB, "invalid", "anything")
        assert resp["ok"] is False
        assert "Invalid component_type" in resp["error"]

    def test_component_not_found_lists_available(self) -> None:
        resp = tb_read_source(AXI2AHB, "sequence", "nonexistent_seq_xyz")
        assert resp["ok"] is False
        assert "not found" in resp["error"].lower()
        # Should list available sequences
        assert "Available sequences" in resp["error"]

    def test_test_not_found(self) -> None:
        resp = tb_read_source(AXI2AHB, "test", "nonexistent_test_xyz")
        assert resp["ok"] is False
        assert "not found" in resp["error"].lower()

    def test_base_test_not_found(self) -> None:
        resp = tb_read_source(AXI2AHB, "base_test", "nonexistent_base_xyz")
        assert resp["ok"] is False
        assert "not found" in resp["error"].lower()

    def test_bad_project(self) -> None:
        resp = tb_read_source("nonexistent_project_xyz", "sequence", "any")
        assert resp["ok"] is False

    def test_env_path_traversal_rejected(self) -> None:
        resp = tb_read_source(AXI2AHB, "env", "../../../etc/passwd")
        assert resp["ok"] is False


class TestMaxLines:
    """max_lines truncation tests."""

    @pytest.mark.skipif(not _HAS_REAL, reason="AXI2AHB_ROOT not set")
    def test_truncation_with_small_max_lines(self) -> None:
        resp = tb_read_source(
            AXI2AHB, "sequence", "wrap_random_len_size_wr_virt_seq", max_lines=10,
        )
        r = resp["result"]
        assert r["total_lines"] > 10
        assert resp["truncated"] is True
        # Content should have at most 10 lines
        content_lines = r["content"].rstrip("\n").split("\n")
        assert len(content_lines) <= 10

    @pytest.mark.skipif(not _HAS_REAL, reason="AXI2AHB_ROOT not set")
    def test_default_max_lines_no_truncation(self) -> None:
        resp = tb_read_source(
            AXI2AHB, "sequence", "wrap_random_len_size_wr_virt_seq",
        )
        # wrap_random is ~315 lines, default max_lines=500
        assert resp["truncated"] is False
        assert resp["result"]["max_lines"] == 500

    @pytest.mark.skipif(not _HAS_REAL, reason="AXI2AHB_ROOT not set")
    def test_max_lines_capped_at_1000(self) -> None:
        resp = tb_read_source(
            AXI2AHB, "sequence", "wrap_random_len_size_wr_virt_seq", max_lines=9999,
        )
        assert resp["result"]["max_lines"] == 1000


class TestEnvelope:
    """Envelope structure validation."""

    def test_success_envelope_keys(self) -> None:
        if not _HAS_REAL:
            pytest.skip("AXI2AHB_ROOT not set")
        resp = tb_read_source(AXI2AHB, "sequence", "wrap_random_len_size_wr_virt_seq")
        required = {"ok", "tool", "project", "result", "evidence", "truncated", "next_actions"}
        for key in required:
            assert key in resp, f"Missing key: {key}"

    def test_evidence_present(self) -> None:
        if not _HAS_REAL:
            pytest.skip("AXI2AHB_ROOT not set")
        resp = tb_read_source(AXI2AHB, "sequence", "wrap_random_len_size_wr_virt_seq")
        assert isinstance(resp["evidence"], list)
        assert len(resp["evidence"]) > 0
        ev = resp["evidence"][0]
        assert "evidence_id" in ev
        assert "source_type" in ev
        assert ev["source_type"] == "testbench"

    def test_next_actions(self) -> None:
        if not _HAS_REAL:
            pytest.skip("AXI2AHB_ROOT not set")
        resp = tb_read_source(AXI2AHB, "sequence", "wrap_random_len_size_wr_virt_seq")
        assert "tb_get_existing_tests_for_feature" in resp["next_actions"]
        assert "tb_find_tests_for_gap" in resp["next_actions"]

    def test_result_fields(self) -> None:
        if not _HAS_REAL:
            pytest.skip("AXI2AHB_ROOT not set")
        resp = tb_read_source(AXI2AHB, "sequence", "wrap_random_len_size_wr_virt_seq")
        r = resp["result"]
        required = [
            "component_type", "name", "file",
            "total_lines", "content", "max_lines", "source_mode",
        ]
        for field in required:
            assert field in r, f"Missing field: {field}"

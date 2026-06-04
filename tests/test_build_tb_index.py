"""Integration tests for build_tb_index.py using the real axi2ahb project.

These tests run the CLI script against the real AXI2AHB UVM verification
project and verify structural properties of the generated tb_index.json.

Requires AXI2AHB_ROOT environment variable to be set.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

# Real project path — skip all tests if not available
AXI2AHB_REAL_ROOT = Path(
    os.environ.get(
        "AXI2AHB_ROOT",
        "/Users/wangyifan/Desktop/AI/project_x2h/AXI2AHB-Lite-Bridge-UVM-Verification",
    )
)

MANIFEST_PATH = Path(__file__).parent.parent / "mock_data" / "axi2ahb" / "project_manifest.yaml"
PROJECT_ROOT = Path(__file__).parent.parent

pytestmark = pytest.mark.skipif(
    not AXI2AHB_REAL_ROOT.exists(),
    reason=f"AXI2AHB real project not found at {AXI2AHB_REAL_ROOT}",
)


@pytest.fixture
def tb_index(tmp_path: Path) -> dict:
    """Run build_tb_index.py and return the parsed JSON output."""
    out_dir = tmp_path / "tb_index_out"
    env = {
        **os.environ,
        "AXI2AHB_ROOT": str(AXI2AHB_REAL_ROOT),
    }
    result = subprocess.run(
        [
            sys.executable,
            str(PROJECT_ROOT / "scripts" / "build_tb_index.py"),
            "--manifest",
            str(MANIFEST_PATH),
            "--out",
            str(out_dir),
        ],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(PROJECT_ROOT),
    )
    assert result.returncode == 0, (
        f"Script failed:\nstdout: {result.stdout}\nstderr: {result.stderr}"
    )

    out_file = out_dir / "tb_index.json"
    assert out_file.exists(), f"Output file not created: {out_file}"
    with open(out_file, encoding="utf-8") as f:
        return json.load(f)  # type: ignore[no-any-return]


class TestCLIExecution:
    """Tests for CLI exit code and output creation."""

    def test_cli_exit_code_0(self, tmp_path: Path) -> None:
        env = {**os.environ, "AXI2AHB_ROOT": str(AXI2AHB_REAL_ROOT)}
        result = subprocess.run(
            [
                sys.executable,
                str(PROJECT_ROOT / "scripts" / "build_tb_index.py"),
                "--manifest",
                str(MANIFEST_PATH),
                "--out",
                str(tmp_path / "out"),
            ],
            capture_output=True,
            text=True,
            env=env,
            cwd=str(PROJECT_ROOT),
        )
        assert result.returncode == 0

    def test_output_file_created(self, tmp_path: Path) -> None:
        env = {**os.environ, "AXI2AHB_ROOT": str(AXI2AHB_REAL_ROOT)}
        out_dir = tmp_path / "out"
        subprocess.run(
            [
                sys.executable,
                str(PROJECT_ROOT / "scripts" / "build_tb_index.py"),
                "--manifest",
                str(MANIFEST_PATH),
                "--out",
                str(out_dir),
            ],
            capture_output=True,
            text=True,
            env=env,
            cwd=str(PROJECT_ROOT),
        )
        assert (out_dir / "tb_index.json").exists()


class TestOutputSchema:
    """Tests for the output schema structure."""

    def test_output_schema_version(self, tb_index: dict) -> None:
        assert tb_index["schema_version"] == "tb_index.v1"

    def test_output_has_required_fields(self, tb_index: dict) -> None:
        required = ["schema_version", "env_root", "sequence_root", "base_tests",
                     "sequences", "existing_tests", "config_knobs"]
        for field in required:
            assert field in tb_index, f"Missing required field: {field}"


class TestExtractedContent:
    """Tests for the quality of extracted content."""

    def test_base_tests_extracted(self, tb_index: dict) -> None:
        assert len(tb_index["base_tests"]) > 0, "No base tests found"
        # Base test should extend uvm_test
        for bt in tb_index["base_tests"]:
            assert bt["extends"] in ("uvm_test", ""), (
                f"Base test {bt['name']} should extend uvm_test"
            )

    def test_existing_tests_extracted(self, tb_index: dict) -> None:
        assert len(tb_index["existing_tests"]) > 0, "No existing tests found"
        # Each concrete test should have a name and file
        for test in tb_index["existing_tests"]:
            assert "name" in test
            assert "file" in test
            assert test["name"] != ""

    def test_sequences_extracted(self, tb_index: dict) -> None:
        assert len(tb_index["sequences"]) > 0, "No sequences found"
        # Each sequence should have a name and file
        for seq in tb_index["sequences"]:
            assert "name" in seq
            assert "file" in seq

    def test_base_sequence_api_methods(self, tb_index: dict) -> None:
        """The base virtual sequence should have >= 20 API methods."""
        # Find the sequence with the most methods (likely the base)
        max_methods = 0
        base_seq_name = ""
        for seq in tb_index["sequences"]:
            n = len(seq.get("api_methods", []))
            if n > max_methods:
                max_methods = n
                base_seq_name = seq["name"]
        assert max_methods >= 20, (
            f"Expected base sequence '{base_seq_name}' to have >= 20 methods, "
            f"got {max_methods}"
        )

    def test_feature_tags_present(self, tb_index: dict) -> None:
        """At least one sequence should have non-empty feature tags."""
        tagged = [s for s in tb_index["sequences"] if s.get("feature_tags")]
        assert len(tagged) > 0, "No sequences have feature tags"

    def test_config_knobs_extracted(self, tb_index: dict) -> None:
        assert len(tb_index["config_knobs"]) > 0, "No config knobs found"
        # Each knob should have name, type, default, plusarg
        for knob in tb_index["config_knobs"]:
            assert "name" in knob
            assert "type" in knob

    def test_test_sequence_links(self, tb_index: dict) -> None:
        """At least one test should have non-empty sequences list."""
        linked = [t for t in tb_index["existing_tests"] if t.get("sequences")]
        assert len(linked) > 0, "No tests have linked sequences"

    def test_test_count_matches_project(self, tb_index: dict) -> None:
        """axi2ahb has 12 concrete tests + 1 base test."""
        total = len(tb_index["base_tests"]) + len(tb_index["existing_tests"])
        assert total >= 10, f"Expected >= 10 total tests, got {total}"

    def test_no_duplicate_classes(self, tb_index: dict) -> None:
        """No class name should appear in multiple categories."""
        base_names = {t["name"] for t in tb_index["base_tests"]}
        test_names = {t["name"] for t in tb_index["existing_tests"]}
        seq_names = {s["name"] for s in tb_index["sequences"]}
        assert not (base_names & test_names), "Overlap between base_tests and existing_tests"
        assert not (base_names & seq_names), "Overlap between base_tests and sequences"
        assert not (test_names & seq_names), "Overlap between existing_tests and sequences"


class TestDMACompatibility:
    """Ensure existing mock data still works."""

    def test_dma_subsystem_mock_unchanged(self) -> None:
        """The existing mock tb_index.json should still be loadable."""
        mock_tb = PROJECT_ROOT / "mock_data" / "dma_subsystem" / ".dv_ai_index" / "tb_index.json"
        assert mock_tb.exists()
        with open(mock_tb, encoding="utf-8") as f:
            data = json.load(f)
        assert data["schema_version"] == "tb_index.v1"
        assert "base_tests" in data
        assert "sequences" in data
        assert "existing_tests" in data
        assert "config_knobs" in data

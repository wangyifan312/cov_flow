"""Tests for build_sim_history_index.py (Phase 6C).

Runs the CLI indexer against the mock dma_subsystem sim_results/ directory
and verifies the structure and content of the generated sim_history.json.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

MANIFEST_PATH = (
    Path(__file__).parent.parent
    / "mock_data" / "dma_subsystem" / "project_manifest.yaml"
)
PROJECT_ROOT = Path(__file__).parent.parent


def _run_indexer(tmp_path: Path) -> tuple[dict, str]:
    """Run build_sim_history_index.py and return (parsed_json, stdout)."""
    out_dir = tmp_path / "sim_history_out"
    result = subprocess.run(
        [
            sys.executable,
            str(PROJECT_ROOT / "scripts" / "build_sim_history_index.py"),
            "--manifest",
            str(MANIFEST_PATH),
            "--out",
            str(out_dir),
        ],
        capture_output=True,
        text=True,
        env={**os.environ},
        cwd=str(PROJECT_ROOT),
    )
    assert result.returncode == 0, (
        f"Script failed:\nstdout: {result.stdout}\nstderr: {result.stderr}"
    )
    out_file = out_dir / "sim_history.json"
    assert out_file.exists(), f"Output file not found: {out_file}"
    with open(out_file, encoding="utf-8") as f:
        return json.load(f), result.stdout


class TestBuildSimHistoryIndex:
    def test_schema_version(self, tmp_path: Path) -> None:
        data, _ = _run_indexer(tmp_path)
        assert data["schema_version"] == "sim_history.v1"

    def test_project_name(self, tmp_path: Path) -> None:
        data, _ = _run_indexer(tmp_path)
        assert data["project"] == "dma_subsystem"

    def test_total_simulations(self, tmp_path: Path) -> None:
        data, _ = _run_indexer(tmp_path)
        assert data["total_simulations"] == 15
        assert len(data["tests"]) == 15

    def test_test_entry_format(self, tmp_path: Path) -> None:
        data, _ = _run_indexer(tmp_path)
        for test in data["tests"]:
            assert "test" in test
            assert "seed" in test
            assert "compile_status" in test
            assert "sim_status" in test
            assert "duration_seconds" in test
            assert "log_path" in test
            assert isinstance(test["seed"], int)

    def test_gap_history_count(self, tmp_path: Path) -> None:
        data, _ = _run_indexer(tmp_path)
        assert len(data["gap_history"]) == 10

    def test_gap_entry_format(self, tmp_path: Path) -> None:
        data, _ = _run_indexer(tmp_path)
        for gap in data["gap_history"]:
            assert "gap_id" in gap
            assert "hit_history" in gap
            assert "trend" in gap
            assert gap["trend"] in ("improving", "stable", "regressing", "never_covered")
            assert isinstance(gap["hit_history"], list)

    def test_improving_trend(self, tmp_path: Path) -> None:
        data, _ = _run_indexer(tmp_path)
        gap2 = next(g for g in data["gap_history"] if g["gap_id"] == "GAP_0002")
        assert gap2["trend"] == "improving"
        assert gap2["first_covered"] is not None

    def test_never_covered_trend(self, tmp_path: Path) -> None:
        data, _ = _run_indexer(tmp_path)
        gap4 = next(g for g in data["gap_history"] if g["gap_id"] == "GAP_0004")
        assert gap4["trend"] == "never_covered"
        assert gap4["first_covered"] is None

    def test_regressing_trend(self, tmp_path: Path) -> None:
        data, _ = _run_indexer(tmp_path)
        gap9 = next(g for g in data["gap_history"] if g["gap_id"] == "GAP_0009")
        assert gap9["trend"] == "regressing"

    def test_stable_trend(self, tmp_path: Path) -> None:
        data, _ = _run_indexer(tmp_path)
        gap3 = next(g for g in data["gap_history"] if g["gap_id"] == "GAP_0003")
        assert gap3["trend"] == "stable"

    def test_generated_at_present(self, tmp_path: Path) -> None:
        data, _ = _run_indexer(tmp_path)
        assert "generated_at" in data
        assert len(data["generated_at"]) > 10

    def test_bad_manifest(self, tmp_path: Path) -> None:
        result = subprocess.run(
            [
                sys.executable,
                str(PROJECT_ROOT / "scripts" / "build_sim_history_index.py"),
                "--manifest",
                str(tmp_path / "nonexistent.yaml"),
            ],
            capture_output=True,
            text=True,
            cwd=str(PROJECT_ROOT),
        )
        assert result.returncode != 0

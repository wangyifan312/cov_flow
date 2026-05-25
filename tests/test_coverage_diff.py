"""Tests for coverage_diff.py."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = "scripts/coverage_diff.py"
PYTHON = sys.executable
BEFORE = "mock_data/dma_subsystem/sim_data/coverage_db_before.json"
AFTER = "mock_data/dma_subsystem/sim_data/coverage_db_after.json"


def _run(before: str = BEFORE, after: str = AFTER, gap_id: str | None = None,
         out: str | None = None) -> subprocess.CompletedProcess:
    cmd = [PYTHON, SCRIPT, "--before", before, "--after", after]
    if gap_id:
        cmd.extend(["--gap-id", gap_id])
    if out:
        cmd.extend(["--out", out])
    return subprocess.run(cmd, capture_output=True, text=True)


class TestCoverageDiff:
    def test_gap_closed(self) -> None:
        result = _run()
        assert result.returncode == 0
        report = json.loads(result.stdout)
        assert report["ok"] is True
        gap_0001 = [d for d in report["gap_deltas"] if d["gap_id"] == "GAP_0001"][0]
        assert gap_0001["before_hit_count"] == 0
        assert gap_0001["after_hit_count"] == 5
        assert gap_0001["closed"] is True

    def test_gap_unchanged(self) -> None:
        result = _run()
        assert result.returncode == 0
        report = json.loads(result.stdout)
        gap_0002 = [d for d in report["gap_deltas"] if d["gap_id"] == "GAP_0002"][0]
        assert gap_0002["before_hit_count"] == 0
        assert gap_0002["after_hit_count"] == 0
        assert gap_0002["closed"] is False

    def test_gap_regressed(self, tmp_path: Path) -> None:
        # Create custom before/after where hit_count goes down
        before_data = {
            "report_id": "before",
            "gaps": [{"gap_id": "GAP_0099", "covergroup": "cg", "coverpoint": "cp", "bin": "b", "hit_count": 10}]
        }
        after_data = {
            "report_id": "after",
            "gaps": [{"gap_id": "GAP_0099", "covergroup": "cg", "coverpoint": "cp", "bin": "b", "hit_count": 5}]
        }
        before_path = tmp_path / "before.json"
        after_path = tmp_path / "after.json"
        before_path.write_text(json.dumps(before_data), encoding="utf-8")
        after_path.write_text(json.dumps(after_data), encoding="utf-8")

        result = _run(before=str(before_path), after=str(after_path))
        assert result.returncode == 0
        report = json.loads(result.stdout)
        delta = report["gap_deltas"][0]
        assert delta["regressed"] is True
        assert report["summary"]["regressed"] == 1

    def test_filter_by_gap_id(self) -> None:
        result = _run(gap_id="GAP_0001")
        assert result.returncode == 0
        report = json.loads(result.stdout)
        assert len(report["gap_deltas"]) == 1
        assert report["gap_deltas"][0]["gap_id"] == "GAP_0001"

    def test_file_not_found(self, tmp_path: Path) -> None:
        result = _run(before=str(tmp_path / "nonexistent.json"))
        assert result.returncode == 1
        report = json.loads(result.stdout)
        assert report["ok"] is False
        assert "not found" in report["error"].lower()

    def test_output_to_file(self, tmp_path: Path) -> None:
        out_path = tmp_path / "diff.json"
        result = _run(out=str(out_path))
        assert result.returncode == 0
        assert out_path.exists()
        report = json.loads(out_path.read_text(encoding="utf-8"))
        assert report["ok"] is True
        assert report["summary"]["total_gaps"] == 15

    def test_summary_counts(self) -> None:
        result = _run()
        assert result.returncode == 0
        report = json.loads(result.stdout)
        summary = report["summary"]
        assert summary["total_gaps"] == 15
        assert summary["newly_covered"] == 3  # GAP_0001, GAP_0003, GAP_0007
        assert summary["unchanged"] == 12
        assert summary["regressed"] == 0

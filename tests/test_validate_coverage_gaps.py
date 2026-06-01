"""Tests for validate_coverage_gaps.py script."""

import json
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
MOCK_MANIFEST = PROJECT_ROOT / "mock_data" / "dma_subsystem" / "project_manifest.yaml"


class TestValidateCoverageGaps:
    """Tests for the coverage gaps validation script."""

    def test_valid_coverage_gaps(self) -> None:
        result = subprocess.run(
            [sys.executable, str(PROJECT_ROOT / "scripts" / "validate_coverage_gaps.py"),
             "--manifest", str(MOCK_MANIFEST)],
            capture_output=True, text=True, cwd=str(PROJECT_ROOT),
        )
        assert result.returncode == 0
        report = json.loads(result.stdout)
        assert report["ok"] is True
        assert report["summary"]["gaps_count"] == 27
        assert report["summary"]["unique_gap_ids"] == 27

    def test_output_to_file(self, tmp_path: Path) -> None:
        out_file = tmp_path / "report.json"
        result = subprocess.run(
            [sys.executable, str(PROJECT_ROOT / "scripts" / "validate_coverage_gaps.py"),
             "--manifest", str(MOCK_MANIFEST), "--out", str(out_file)],
            capture_output=True, text=True, cwd=str(PROJECT_ROOT),
        )
        assert result.returncode == 0
        assert out_file.exists()
        report = json.loads(out_file.read_text())
        assert report["ok"] is True

    def test_missing_coverage_gaps(self, tmp_path: Path) -> None:
        # Create a minimal manifest pointing to a dir without coverage_gaps.json
        manifest = tmp_path / "project_manifest.yaml"
        manifest.write_text(
            "project: test\n"
            "top_instance: tb_top\n"
            "coverage:\n"
            f"  reports_root: {tmp_path}\n"
            f"  coverage_model_root: {tmp_path}\n"
            "rtl:\n"
            f"  filelist: {tmp_path / 'rtl.f'}\n"
            "registers:\n"
            "  source:\n"
            "    type: yaml\n"
            f"    path: {tmp_path / 'regs.yaml'}\n"
            "testbench:\n"
            "  type: uvm\n"
            f"  env_root: {tmp_path}\n"
            "policy:\n"
            "  allow_direct_file_modification: false\n"
            "  allow_running_simulation: false\n"
            "  require_human_review_before_commit: true\n",
            encoding="utf-8",
        )
        result = subprocess.run(
            [sys.executable, str(PROJECT_ROOT / "scripts" / "validate_coverage_gaps.py"),
             "--manifest", str(manifest)],
            capture_output=True, text=True, cwd=str(PROJECT_ROOT),
        )
        assert result.returncode == 1
        report = json.loads(result.stdout)
        assert report["ok"] is False

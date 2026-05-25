"""Tests for validate_patch_metadata.py."""

import json
import subprocess
import sys
from pathlib import Path

SCRIPT = "scripts/validate_patch_metadata.py"
PYTHON = sys.executable


def _valid_patch() -> dict:
    return {
        "patch_id": "PATCH_GAP_0001_001",
        "gap_id": "GAP_0001",
        "new_files": [
            "tb/sequences/dma_linked_list_desc_seq.sv",
            "tb/tests/dma_linked_list_desc_test.sv",
        ],
        "modified_files": [],
        "base_reuse": {
            "base_test": "dma_base_test",
            "base_sequence": "dma_desc_base_seq",
        },
        "compile_command": "make compile TEST=dma_linked_list_desc_test",
        "run_command": "make run TEST=dma_linked_list_desc_test SEED=1",
        "coverage_target": [
            "dma_desc_cg.desc_mode_cp.linked_list",
        ],
        "review_checklist": [
            "confirm RAL path for DMA_CFG.LL_MODE_EN",
            "confirm descriptor memory allocation helper",
            "confirm sequence starts on correct virtual sequencer",
        ],
    }


def _write_json(data: dict, tmpdir: Path) -> Path:
    path = tmpdir / "patch_metadata.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def _run(file_path: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [PYTHON, SCRIPT, "--file", str(file_path)],
        capture_output=True,
        text=True,
    )


class TestValidatePatchMetadata:
    def test_valid_patch_passes(self, tmp_path: Path) -> None:
        path = _write_json(_valid_patch(), tmp_path)
        result = _run(path)
        assert result.returncode == 0
        report = json.loads(result.stdout)
        assert report["ok"] is True
        assert report["summary"]["valid"] is True
        assert report["errors"] == []

    def test_missing_required_field(self, tmp_path: Path) -> None:
        patch = _valid_patch()
        del patch["patch_id"]
        path = _write_json(patch, tmp_path)
        result = _run(path)
        assert result.returncode == 1
        report = json.loads(result.stdout)
        assert report["ok"] is False
        assert len(report["errors"]) > 0

    def test_invalid_patch_id_format(self, tmp_path: Path) -> None:
        patch = _valid_patch()
        patch["patch_id"] = "BAD_ID"
        path = _write_json(patch, tmp_path)
        result = _run(path)
        assert result.returncode == 1
        report = json.loads(result.stdout)
        assert report["ok"] is False
        paths = [e["path"] for e in report["errors"]]
        assert "patch_id" in paths

    def test_empty_review_checklist(self, tmp_path: Path) -> None:
        patch = _valid_patch()
        patch["review_checklist"] = []
        path = _write_json(patch, tmp_path)
        result = _run(path)
        assert result.returncode == 1
        report = json.loads(result.stdout)
        assert report["ok"] is False
        paths = [e["path"] for e in report["errors"]]
        assert "review_checklist" in paths

    def test_empty_coverage_target(self, tmp_path: Path) -> None:
        patch = _valid_patch()
        patch["coverage_target"] = []
        path = _write_json(patch, tmp_path)
        result = _run(path)
        assert result.returncode == 1
        report = json.loads(result.stdout)
        assert report["ok"] is False
        paths = [e["path"] for e in report["errors"]]
        assert "coverage_target" in paths

    def test_output_to_file(self, tmp_path: Path) -> None:
        patch_path = _write_json(_valid_patch(), tmp_path)
        out_path = tmp_path / "report.json"
        result = subprocess.run(
            [PYTHON, SCRIPT, "--file", str(patch_path), "--out", str(out_path)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert out_path.exists()
        report = json.loads(out_path.read_text(encoding="utf-8"))
        assert report["ok"] is True

    def test_file_not_found(self, tmp_path: Path) -> None:
        fake_path = tmp_path / "nonexistent.json"
        result = _run(fake_path)
        assert result.returncode == 1
        report = json.loads(result.stdout)
        assert report["ok"] is False
        assert "File not found" in report["errors"][0]["message"]

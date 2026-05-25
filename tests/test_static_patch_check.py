"""Tests for static_patch_check.py."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = "scripts/static_patch_check.py"
PYTHON = sys.executable
MANIFEST = "mock_data/dma_subsystem/project_manifest.yaml"


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
        ],
    }


def _write_json(data: dict, tmpdir: Path, name: str = "patch.json") -> Path:
    path = tmpdir / name
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def _run(patch_path: Path, manifest: str = MANIFEST, out_path: Path | None = None) -> subprocess.CompletedProcess:
    cmd = [PYTHON, SCRIPT, "--file", str(patch_path), "--manifest", manifest]
    if out_path:
        cmd.extend(["--out", str(out_path)])
    return subprocess.run(cmd, capture_output=True, text=True)


class TestStaticPatchCheck:
    def test_all_checks_pass(self, tmp_path: Path) -> None:
        patch = _valid_patch()
        path = _write_json(patch, tmp_path)
        result = _run(path)
        assert result.returncode == 0
        report = json.loads(result.stdout)
        assert report["ok"] is True
        assert report["summary"]["failed"] == 0
        assert report["summary"]["total"] > 0
        assert report["tool"] == "static_patch_check"

    def test_modified_file_not_found(self, tmp_path: Path) -> None:
        patch = _valid_patch()
        patch["modified_files"] = ["tb/nonexistent/file.sv"]
        path = _write_json(patch, tmp_path)
        result = _run(path)
        assert result.returncode == 1
        report = json.loads(result.stdout)
        assert report["ok"] is False
        failed = [c for c in report["checks"] if not c["passed"]]
        assert len(failed) >= 1
        assert failed[0]["check"] == "modified_file_exists"

    def test_base_test_not_in_index(self, tmp_path: Path) -> None:
        patch = _valid_patch()
        patch["base_reuse"]["base_test"] = "nonexistent_base_test"
        path = _write_json(patch, tmp_path)
        result = _run(path)
        assert result.returncode == 1
        report = json.loads(result.stdout)
        assert report["ok"] is False
        failed = [c for c in report["checks"] if not c["passed"]]
        assert any(c["check"] == "base_test_in_index" for c in failed)

    def test_base_sequence_not_in_index(self, tmp_path: Path) -> None:
        patch = _valid_patch()
        patch["base_reuse"]["base_sequence"] = "nonexistent_seq"
        path = _write_json(patch, tmp_path)
        result = _run(path)
        assert result.returncode == 1
        report = json.loads(result.stdout)
        failed = [c for c in report["checks"] if not c["passed"]]
        assert any(c["check"] == "base_sequence_in_index" for c in failed)

    def test_invalid_coverage_target_format(self, tmp_path: Path) -> None:
        patch = _valid_patch()
        patch["coverage_target"] = ["invalid_format"]
        path = _write_json(patch, tmp_path)
        result = _run(path)
        assert result.returncode == 1
        report = json.loads(result.stdout)
        failed = [c for c in report["checks"] if not c["passed"]]
        assert any(c["check"] == "coverage_target_format" for c in failed)

    def test_empty_review_checklist(self, tmp_path: Path) -> None:
        patch = _valid_patch()
        patch["review_checklist"] = []
        path = _write_json(patch, tmp_path)
        result = _run(path)
        assert result.returncode == 1
        report = json.loads(result.stdout)
        failed = [c for c in report["checks"] if not c["passed"]]
        assert any(c["check"] == "review_checklist_non_empty" for c in failed)

    def test_manifest_not_found(self, tmp_path: Path) -> None:
        patch = _valid_patch()
        path = _write_json(patch, tmp_path)
        result = _run(path, manifest="nonexistent/manifest.yaml")
        assert result.returncode == 1
        report = json.loads(result.stdout)
        assert report["ok"] is False
        assert "Manifest error" in report["error"]

    def test_output_to_file(self, tmp_path: Path) -> None:
        patch = _valid_patch()
        path = _write_json(patch, tmp_path)
        out_path = tmp_path / "report.json"
        result = _run(path, out_path=out_path)
        assert result.returncode == 0
        assert out_path.exists()
        report = json.loads(out_path.read_text(encoding="utf-8"))
        assert report["ok"] is True

    def test_coverage_target_two_segments(self, tmp_path: Path) -> None:
        patch = _valid_patch()
        patch["coverage_target"] = ["only.two"]
        path = _write_json(patch, tmp_path)
        result = _run(path)
        assert result.returncode == 1
        report = json.loads(result.stdout)
        failed = [c for c in report["checks"] if not c["passed"]]
        assert any(c["check"] == "coverage_target_format" for c in failed)

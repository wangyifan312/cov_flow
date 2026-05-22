"""Tests for validate_scenario_card.py."""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

SCRIPT = "scripts/validate_scenario_card.py"
PYTHON = sys.executable


def _valid_card() -> dict:
    return {
        "gap_id": "GAP_0001",
        "target_coverage": {
            "covergroup": "dma_desc_cg",
            "coverpoint": "desc_mode_cp",
            "bin": "linked_list",
        },
        "classification": "Config Missing",
        "semantic_interpretation": (
            "Linked-list descriptor mode has not been exercised. "
            "The scenario requires enabling linked-list mode and "
            "providing a descriptor with a non-zero next pointer."
        ),
        "required_config": [
            {"register": "DMA_CFG.LL_MODE_EN", "value": 1},
        ],
        "stimulus": [
            "program descriptor base address",
            "build two linked descriptors",
            "start DMA channel",
        ],
        "expected_behavior": [
            "descriptor parser enters LINK_DESC state",
            "next descriptor is fetched",
            "completion interrupt is generated",
        ],
        "tb_reuse": {
            "base_test": "dma_base_test",
            "candidate_sequence": "dma_desc_base_seq",
        },
        "confidence": "medium",
        "risk": [
            "confirm linked-list mode is enabled in current build configuration",
        ],
    }


def _write_json(data: dict, tmpdir: Path) -> Path:
    path = tmpdir / "scenario_card.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def _run(file_path: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [PYTHON, SCRIPT, "--file", str(file_path)],
        capture_output=True,
        text=True,
    )


class TestValidateScenarioCard:
    def test_valid_card_passes(self, tmp_path: Path) -> None:
        path = _write_json(_valid_card(), tmp_path)
        result = _run(path)
        assert result.returncode == 0
        report = json.loads(result.stdout)
        assert report["ok"] is True
        assert report["summary"]["valid"] is True
        assert report["errors"] == []

    def test_missing_required_field(self, tmp_path: Path) -> None:
        card = _valid_card()
        del card["gap_id"]
        path = _write_json(card, tmp_path)
        result = _run(path)
        assert result.returncode == 1
        report = json.loads(result.stdout)
        assert report["ok"] is False
        assert len(report["errors"]) > 0

    def test_invalid_gap_id_format(self, tmp_path: Path) -> None:
        card = _valid_card()
        card["gap_id"] = "INVALID_ID"
        path = _write_json(card, tmp_path)
        result = _run(path)
        assert result.returncode == 1
        report = json.loads(result.stdout)
        assert report["ok"] is False
        # Should have pattern error on gap_id
        paths = [e["path"] for e in report["errors"]]
        assert "gap_id" in paths

    def test_invalid_confidence_enum(self, tmp_path: Path) -> None:
        card = _valid_card()
        card["confidence"] = "super_high"
        path = _write_json(card, tmp_path)
        result = _run(path)
        assert result.returncode == 1
        report = json.loads(result.stdout)
        assert report["ok"] is False
        paths = [e["path"] for e in report["errors"]]
        assert "confidence" in paths

    def test_empty_stimulus_array(self, tmp_path: Path) -> None:
        card = _valid_card()
        card["stimulus"] = []
        path = _write_json(card, tmp_path)
        result = _run(path)
        assert result.returncode == 1
        report = json.loads(result.stdout)
        assert report["ok"] is False
        paths = [e["path"] for e in report["errors"]]
        assert "stimulus" in paths

    def test_output_to_file(self, tmp_path: Path) -> None:
        card_path = _write_json(_valid_card(), tmp_path)
        out_path = tmp_path / "report.json"
        result = subprocess.run(
            [PYTHON, SCRIPT, "--file", str(card_path), "--out", str(out_path)],
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

"""Tests for validate_feedback_report.py (Phase 6C).

Validates the feedback report schema and the CLI validator script.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent


def _valid_report() -> dict:
    """Return a valid feedback report."""
    return {
        "gap_id": "GAP_0001",
        "test": "dma_linked_list_desc_test",
        "seed": 42,
        "compile_status": "pass",
        "sim_status": "pass",
        "coverage_delta": {
            "GAP_0001": {"before": 0, "after": 5, "delta": 5},
        },
        "root_cause": "Linked-list mode requires next-pointer setup",
        "next_actions": ["Add descriptor memory init sequence"],
        "confidence": "high",
    }


def _validate_file(tmp_path: Path, data: dict) -> tuple[int, dict]:
    """Write data to a temp file and run the validator. Returns (exit_code, report)."""
    feedback_file = tmp_path / "feedback.json"
    with open(feedback_file, "w", encoding="utf-8") as f:
        json.dump(data, f)

    result = subprocess.run(
        [
            sys.executable,
            str(PROJECT_ROOT / "scripts" / "validate_feedback_report.py"),
            "--feedback",
            str(feedback_file),
        ],
        capture_output=True,
        text=True,
        env={**os.environ},
        cwd=str(PROJECT_ROOT),
    )
    try:
        report = json.loads(result.stdout)
    except json.JSONDecodeError:
        report = {"ok": False, "errors": [], "stdout": result.stdout}
    return result.returncode, report


class TestValidateFeedbackReport:
    def test_valid_report_passes(self, tmp_path: Path) -> None:
        exit_code, report = _validate_file(tmp_path, _valid_report())
        assert exit_code == 0
        assert report["ok"] is True

    def test_missing_required_field(self, tmp_path: Path) -> None:
        data = _valid_report()
        del data["root_cause"]
        exit_code, report = _validate_file(tmp_path, data)
        assert exit_code != 0
        assert report["ok"] is False
        assert any("root_cause" in str(e) for e in report["errors"])

    def test_gap_id_pattern(self, tmp_path: Path) -> None:
        data = _valid_report()
        data["gap_id"] = "INVALID_ID"
        exit_code, report = _validate_file(tmp_path, data)
        assert exit_code != 0
        assert report["ok"] is False
        assert any("gap_id" in str(e.get("path", "")) for e in report["errors"])

    def test_gap_id_code_coverage_format(self, tmp_path: Path) -> None:
        data = _valid_report()
        data["gap_id"] = "GAP_L001"
        exit_code, report = _validate_file(tmp_path, data)
        assert exit_code == 0
        assert report["ok"] is True

    def test_coverage_delta_format(self, tmp_path: Path) -> None:
        data = _valid_report()
        data["coverage_delta"]["GAP_0001"]["delta"] = "not_an_int"
        exit_code, report = _validate_file(tmp_path, data)
        assert exit_code != 0
        assert report["ok"] is False

    def test_confidence_enum(self, tmp_path: Path) -> None:
        data = _valid_report()
        data["confidence"] = "maybe"
        exit_code, report = _validate_file(tmp_path, data)
        assert exit_code != 0
        assert report["ok"] is False

    def test_optional_fields_accepted(self, tmp_path: Path) -> None:
        data = _valid_report()
        data["log_summary"] = "Test ran OK"
        data["uvm_counts"] = {"info": 10, "warning": 1, "error": 0, "fatal": 0}
        data["evidence"] = [
            {"evidence_id": "test", "source_type": "sim", "source_ref": "log", "summary": "ok"}
        ]
        exit_code, report = _validate_file(tmp_path, data)
        assert exit_code == 0
        assert report["ok"] is True

    def test_nonexistent_file(self, tmp_path: Path) -> None:
        result = subprocess.run(
            [
                sys.executable,
                str(PROJECT_ROOT / "scripts" / "validate_feedback_report.py"),
                "--feedback",
                str(tmp_path / "nonexistent.json"),
            ],
            capture_output=True,
            text=True,
            cwd=str(PROJECT_ROOT),
        )
        assert result.returncode != 0

    def test_seed_minimum(self, tmp_path: Path) -> None:
        data = _valid_report()
        data["seed"] = -1
        exit_code, report = _validate_file(tmp_path, data)
        assert exit_code != 0
        assert report["ok"] is False

    def test_next_actions_min_items(self, tmp_path: Path) -> None:
        data = _valid_report()
        data["next_actions"] = []
        exit_code, report = _validate_file(tmp_path, data)
        assert exit_code != 0
        assert report["ok"] is False

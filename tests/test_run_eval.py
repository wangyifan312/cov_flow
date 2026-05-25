"""Tests for eval runner."""

import json
import tempfile
from pathlib import Path

from scripts.run_eval import run_eval_batch, run_eval_single, validate_eval


class TestRunEval:
    def test_dry_run_single_eval(self) -> None:
        result = run_eval_single(Path("evals/triage_gap_0001.yaml"), dry_run=True)
        assert result["ok"] is True
        assert result["tool"] == "run_eval"
        assert result["eval_id"] == "triage_gap_0001"
        assert result["task_mode"] == "triage"
        assert "prompt" in result
        assert len(result["expected_tools"]) > 0
        assert result["validation"]["yaml_valid"] is True
        assert result["status"] == "dry_run_complete"

    def test_dry_run_batch_mode(self) -> None:
        result = run_eval_batch(Path("evals/"), dry_run=True)
        assert result["ok"] is True
        assert result["tool"] == "run_eval"
        assert len(result["evals"]) >= 3
        assert result["summary"]["total"] >= 3
        assert result["summary"]["valid"] >= 3
        assert result["summary"]["invalid"] == 0

    def test_invalid_yaml(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            bad_yaml = Path(tmpdir) / "bad.yaml"
            bad_yaml.write_text(": : : invalid yaml", encoding="utf-8")
            result = run_eval_single(bad_yaml, dry_run=True)
            assert result["ok"] is False
            assert "Failed to parse YAML" in result["error"]

    def test_missing_required_field(self) -> None:
        eval_data = {
            "eval_id": "test_001",
            "task_mode": "triage",
            # missing: prompt, expected_tools
        }
        validation = validate_eval(eval_data)
        assert validation["yaml_valid"] is False
        assert any("Missing required field" in err for err in validation["errors"])

    def test_invalid_task_mode(self) -> None:
        eval_data = {
            "eval_id": "test_001",
            "task_mode": "invalid_mode",
            "prompt": "test prompt",
            "expected_tools": ["cov_get_gap_detail"],
        }
        validation = validate_eval(eval_data)
        assert validation["yaml_valid"] is False
        assert any("Invalid task_mode" in err for err in validation["errors"])

    def test_unknown_tool_in_expected_tools(self) -> None:
        eval_data = {
            "eval_id": "test_001",
            "task_mode": "triage",
            "prompt": "test prompt",
            "expected_tools": ["nonexistent_tool", "cov_get_gap_detail"],
        }
        validation = validate_eval(eval_data)
        assert validation["yaml_valid"] is False
        assert any("Unknown tools" in err for err in validation["errors"])

    def test_invalid_classification_enum(self) -> None:
        eval_data = {
            "eval_id": "test_001",
            "task_mode": "triage",
            "prompt": "test prompt",
            "expected_tools": ["cov_get_gap_detail"],
            "expected_classification": "Invalid Classification",
        }
        validation = validate_eval(eval_data)
        assert validation["yaml_valid"] is False
        assert any("Invalid expected_classification" in err for err in validation["errors"])

    def test_output_to_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = Path(tmpdir) / "report.json"
            result = run_eval_single(Path("evals/triage_gap_0001.yaml"), dry_run=True)
            out_path.write_text(json.dumps(result), encoding="utf-8")
            assert out_path.exists()
            loaded = json.loads(out_path.read_text(encoding="utf-8"))
            assert loaded["ok"] is True
            assert loaded["eval_id"] == "triage_gap_0001"

    def test_file_not_found(self) -> None:
        result = run_eval_single(Path("evals/nonexistent.yaml"), dry_run=True)
        assert result["ok"] is False
        assert "Eval file not found" in result["error"]

    def test_batch_empty_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            result = run_eval_batch(Path(tmpdir), dry_run=True)
            assert result["ok"] is False
            assert "No YAML files found" in result["error"]
            assert result["summary"]["total"] == 0

"""Tests for sim_runner.py (dry-run and real execution via SimExecutor)."""

import json
import subprocess
import sys
from pathlib import Path

import yaml

SCRIPT = "scripts/sim_runner.py"
PYTHON = sys.executable
MANIFEST = "mock_data/dma_subsystem/project_manifest.yaml"


def _run_dry(manifest: str = MANIFEST, test: str = "dma_linked_list_desc_test",
             seed: int = 1) -> subprocess.CompletedProcess:
    """Run sim_runner.py with --dry-run flag."""
    return subprocess.run(
        [PYTHON, SCRIPT, "--manifest", manifest, "--test", test,
         "--seed", str(seed), "--dry-run"],
        capture_output=True,
        text=True,
    )


def _run_real(manifest: str = MANIFEST, test: str = "dma_linked_list_desc_test",
              seed: int = 1) -> subprocess.CompletedProcess:
    """Run sim_runner.py in real execution mode (no --dry-run)."""
    return subprocess.run(
        [PYTHON, SCRIPT, "--manifest", manifest, "--test", test,
         "--seed", str(seed)],
        capture_output=True,
        text=True,
    )


class TestSimRunnerDryRun:
    def test_dry_run_produces_valid_output(self) -> None:
        result = _run_dry()
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data["ok"] is True
        assert data["dry_run"] is True
        assert data["test"] == "dma_linked_list_desc_test"
        assert data["seed"] == 1
        assert "compile_command" in data
        assert "run_command" in data

    def test_policy_blocks_when_false(self, tmp_path: Path) -> None:
        with open(MANIFEST, encoding="utf-8") as f:
            manifest_data = yaml.safe_load(f)
        manifest_data["policy"]["allow_running_simulation"] = False

        restricted_manifest = tmp_path / "manifest.yaml"
        restricted_manifest.write_text(yaml.dump(manifest_data), encoding="utf-8")

        result = _run_dry(manifest=str(restricted_manifest))
        assert result.returncode == 1
        data = json.loads(result.stdout)
        assert data["ok"] is False
        assert "not allowed" in data["error"].lower() or "policy" in data["error"].lower()

    def test_command_template_rendering(self) -> None:
        result = _run_dry(test="my_custom_test", seed=42)
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert "my_custom_test" in data["compile_command"]
        assert "42" in data["run_command"]

    def test_manifest_missing_simulation_block(self, tmp_path: Path) -> None:
        with open(MANIFEST, encoding="utf-8") as f:
            manifest_data = yaml.safe_load(f)
        del manifest_data["simulation"]

        no_sim_manifest = tmp_path / "manifest.yaml"
        no_sim_manifest.write_text(yaml.dump(manifest_data), encoding="utf-8")

        result = _run_dry(manifest=str(no_sim_manifest))
        assert result.returncode == 1
        data = json.loads(result.stdout)
        assert data["ok"] is False
        assert "simulation" in data["error"].lower()

    def test_seed_validation_negative(self) -> None:
        result = _run_dry(seed=-1)
        assert result.returncode == 1
        data = json.loads(result.stdout)
        assert data["ok"] is False
        assert "seed" in data["error"].lower()


class TestSimRunnerRealExecution:
    """Real execution tests using echo-based commands (no VCS dependency)."""

    def test_successful_run(self) -> None:
        """dma_subsystem manifest uses echo commands, so real execution succeeds."""
        result = _run_real()
        assert result.returncode == 0
        assert "Running simulation" in result.stdout
        assert "compile" in result.stdout

    def test_compile_failure_exit_code(self, tmp_path: Path) -> None:
        """Compile failure returns exit code 2."""
        manifest_path = tmp_path / "manifest.yaml"
        manifest_path.write_text(
            f"""
project: test_fail
project_root: {tmp_path}
simulation:
  compile_cmd_template: "false"
  run_cmd_template: "echo run"
  results_root: sim_results
policy:
  allow_running_simulation: true
""",
            encoding="utf-8",
        )
        (tmp_path / "sim_results").mkdir()

        result = _run_real(manifest=str(manifest_path))
        assert result.returncode == 2

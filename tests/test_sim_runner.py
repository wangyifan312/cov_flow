"""Tests for sim_runner.py."""

import json
import subprocess
import sys
from pathlib import Path

import yaml

SCRIPT = "scripts/sim_runner.py"
PYTHON = sys.executable
MANIFEST = "mock_data/dma_subsystem/project_manifest.yaml"


def _run(manifest: str = MANIFEST, test: str = "dma_linked_list_desc_test",
         seed: int = 1, out: str = "result.json") -> subprocess.CompletedProcess:
    return subprocess.run(
        [PYTHON, SCRIPT, "--manifest", manifest, "--test", test, "--seed", str(seed), "--out", out],
        capture_output=True,
        text=True,
    )


class TestSimRunner:
    def test_dry_run_produces_valid_output(self, tmp_path: Path) -> None:
        out_path = tmp_path / "result.json"
        result = _run(out=str(out_path))
        assert result.returncode == 0
        data = json.loads(out_path.read_text(encoding="utf-8"))
        assert data["ok"] is True
        assert data["dry_run"] is True
        assert data["test"] == "dma_linked_list_desc_test"
        assert data["seed"] == 1
        assert data["compile_status"] == "pass"
        assert data["sim_status"] == "pass"
        assert data["policy_checked"] is True

    def test_policy_blocks_when_false(self, tmp_path: Path) -> None:
        # Create a manifest with allow_running_simulation: false
        with open(MANIFEST, encoding="utf-8") as f:
            manifest_data = yaml.safe_load(f)
        manifest_data["policy"]["allow_running_simulation"] = False

        restricted_manifest = tmp_path / "manifest.yaml"
        restricted_manifest.write_text(yaml.dump(manifest_data), encoding="utf-8")

        out_path = tmp_path / "result.json"
        result = _run(manifest=str(restricted_manifest), out=str(out_path))
        assert result.returncode == 1
        data = json.loads(out_path.read_text(encoding="utf-8"))
        assert data["ok"] is False
        assert "not allowed" in data["error"].lower() or "policy" in data["error"].lower()

    def test_command_template_rendering(self, tmp_path: Path) -> None:
        out_path = tmp_path / "result.json"
        result = _run(test="my_custom_test", seed=42, out=str(out_path))
        assert result.returncode == 0
        data = json.loads(out_path.read_text(encoding="utf-8"))
        assert "my_custom_test" in data["compile_command"]
        assert "42" in data["run_command"]

    def test_manifest_missing_simulation_block(self, tmp_path: Path) -> None:
        with open(MANIFEST, encoding="utf-8") as f:
            manifest_data = yaml.safe_load(f)
        del manifest_data["simulation"]

        no_sim_manifest = tmp_path / "manifest.yaml"
        no_sim_manifest.write_text(yaml.dump(manifest_data), encoding="utf-8")

        out_path = tmp_path / "result.json"
        result = _run(manifest=str(no_sim_manifest), out=str(out_path))
        assert result.returncode == 1
        data = json.loads(out_path.read_text(encoding="utf-8"))
        assert data["ok"] is False
        assert "simulation" in data["error"].lower()

    def test_seed_validation_negative(self, tmp_path: Path) -> None:
        out_path = tmp_path / "result.json"
        result = _run(seed=-1, out=str(out_path))
        assert result.returncode == 1
        data = json.loads(out_path.read_text(encoding="utf-8"))
        assert data["ok"] is False
        assert "seed" in data["error"].lower()

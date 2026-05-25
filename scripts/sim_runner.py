#!/usr/bin/env python3
"""Simulation runner: renders command templates from manifest and produces mock results.

In mock MVP mode, sim_runner.py does NOT execute shell commands. It validates
the manifest policy, renders command templates, and produces a mock sim_result.json.

Usage:
    python scripts/sim_runner.py --manifest manifest.yaml --test my_test \
        --seed 1 --out result.json
    python scripts/sim_runner.py --manifest manifest.yaml --test my_test \
        --seed 1 --out result.json --dry-run
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_SCRIPT_DIR = Path(__file__).parent
_PROJECT_ROOT = _SCRIPT_DIR.parent
sys.path.insert(0, str(_PROJECT_ROOT))

from lib.manifest import Manifest, ManifestError  # noqa: E402


def render_commands(manifest: Manifest, test: str, seed: int) -> dict[str, str]:
    """Render command templates from the manifest."""
    sim_config = manifest.data.get("simulation", {})
    compile_template = sim_config.get("compile_cmd_template", "make compile TEST={test}")
    run_template = sim_config.get("run_cmd_template", "make run TEST={test} SEED={seed}")
    coverage_template = sim_config.get("coverage_cmd_template", "make cov TEST={test}")

    return {
        "compile_command": compile_template.format(test=test, seed=seed),
        "run_command": run_template.format(test=test, seed=seed),
        "coverage_command": coverage_template.format(test=test, seed=seed),
    }


def build_sim_result(
    test: str,
    seed: int,
    commands: dict[str, str],
    policy_checked: bool,
    dry_run: bool = True,
) -> dict:
    """Build a mock simulation result."""
    return {
        "ok": True,
        "test": test,
        "seed": seed,
        "compile_command": commands["compile_command"],
        "run_command": commands["run_command"],
        "coverage_command": commands["coverage_command"],
        "compile_status": "pass",
        "sim_status": "pass",
        "return_code": 0,
        "log_path": f"sim_logs/{test}_{seed}.log",
        "coverage_report_id": "mock_cov_report_001",
        "policy_checked": policy_checked,
        "dry_run": dry_run,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Simulation runner (mock MVP).")
    parser.add_argument("--manifest", required=True, help="Path to project_manifest.yaml")
    parser.add_argument("--test", required=True, help="Test name")
    parser.add_argument(
        "--seed", required=True, type=int, help="Random seed (non-negative integer)",
    )
    parser.add_argument("--out", required=True, help="Output path for sim result JSON")
    parser.add_argument("--dry-run", action="store_true", default=True,
                        help="Dry-run mode (default: true in mock MVP)")
    args = parser.parse_args()

    if args.seed < 0:
        report = {
            "ok": False,
            "error": f"Seed must be non-negative, got {args.seed}",
            "test": args.test,
            "seed": args.seed,
        }
        _output(report, args.out)
        return 1

    # Load manifest
    try:
        manifest = Manifest.load(args.manifest)
    except ManifestError as e:
        report = {
            "ok": False,
            "error": f"Manifest error: {e}",
            "test": args.test,
            "seed": args.seed,
        }
        _output(report, args.out)
        return 1

    # Check policy
    policy = manifest.data.get("policy", {})
    allow_sim = policy.get("allow_running_simulation", False)
    if not allow_sim:
        report = {
            "ok": False,
            "error": "Simulation not allowed: manifest policy.allow_running_simulation is false",
            "test": args.test,
            "seed": args.seed,
            "policy_checked": True,
        }
        _output(report, args.out)
        return 1

    # Check simulation block exists
    sim_config = manifest.data.get("simulation")
    if not sim_config:
        report = {
            "ok": False,
            "error": "Manifest missing 'simulation' block",
            "test": args.test,
            "seed": args.seed,
        }
        _output(report, args.out)
        return 1

    # Render commands and build mock result
    commands = render_commands(manifest, args.test, args.seed)
    result = build_sim_result(
        args.test, args.seed, commands, policy_checked=True, dry_run=args.dry_run,
    )
    _output(result, args.out)
    return 0


def _output(data: dict, out_path: str) -> None:
    text = json.dumps(data, indent=2, ensure_ascii=False)
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    Path(out_path).write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    sys.exit(main())

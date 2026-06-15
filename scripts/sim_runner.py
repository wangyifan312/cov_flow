#!/usr/bin/env python3
"""Simulation runner: renders command templates from manifest and executes via SimExecutor.

Usage:
    python scripts/sim_runner.py --manifest manifest.yaml --test my_test --seed 42
    python scripts/sim_runner.py --manifest manifest.yaml --test my_test --seed 42 --dry-run
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


def main() -> int:
    parser = argparse.ArgumentParser(description="Simulation runner.")
    parser.add_argument("--manifest", required=True, help="Path to project_manifest.yaml")
    parser.add_argument("--test", required=True, help="Test name")
    parser.add_argument(
        "--seed", required=True, type=int, help="Random seed (non-negative integer)",
    )
    parser.add_argument("--dry-run", action="store_true", default=False,
                        help="Render command templates and print without executing")
    args = parser.parse_args()

    if args.seed < 0:
        report = {
            "ok": False,
            "error": f"Seed must be non-negative, got {args.seed}",
            "test": args.test,
            "seed": args.seed,
        }
        print(json.dumps(report, indent=2))
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
        print(json.dumps(report, indent=2))
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
        print(json.dumps(report, indent=2))
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
        print(json.dumps(report, indent=2))
        return 1

    # === Dry-run: render and print commands without executing ===
    if args.dry_run:
        commands = render_commands(manifest, args.test, args.seed)
        report = {
            "ok": True,
            "test": args.test,
            "seed": args.seed,
            "dry_run": True,
            "compile_command": commands["compile_command"],
            "run_command": commands["run_command"],
            "coverage_command": commands["coverage_command"],
        }
        print(json.dumps(report, indent=2))
        return 0

    # === Real execution via SimExecutor ===
    from lib.sim_executor import SimExecutor

    executor = SimExecutor(
        project_root=manifest.project_root,
        results_root=manifest.sim_results_root,
        timeout_seconds=manifest.sim_timeout,
        urg_timeout_seconds=manifest.sim_urg_timeout,
    )

    # Validate test name and seed
    try:
        executor.validate_test_name(args.test)
        executor.validate_seed(args.seed)
    except ValueError as e:
        print(f"ERROR: {e}")
        return 1

    # Render commands from manifest
    compile_cmd = sim_config.get(
        "compile_cmd_template", "make compile TEST={test}",
    ).format(test=args.test, seed=args.seed)
    run_cmd = sim_config.get(
        "run_cmd_template", "make run TEST={test} SEED={seed}",
    ).format(test=args.test, seed=args.seed)

    # URG command (optional)
    urg_cmd = None
    urg_template = sim_config.get("urg_cmd_template")
    if urg_template:
        vdb_dir = sim_config.get(
            "vdb_dir_template", "sim_results/coverage/{test}_{seed}.vdb",
        ).format(test=args.test, seed=args.seed)
        report_dir = f"{executor.get_results_dir(args.test, args.seed)}/urg_report"
        urg_cmd = urg_template.format(vdb_dir=vdb_dir, report_dir=report_dir)

    # Run pipeline
    print(f"Running simulation: test={args.test} seed={args.seed}")
    print(f"  compile: {compile_cmd}")
    print(f"  run:     {run_cmd}")
    if urg_cmd:
        print(f"  urg:     {urg_cmd}")

    result = executor.run_pipeline(
        test=args.test, seed=args.seed,
        compile_cmd=compile_cmd, run_cmd=run_cmd, urg_cmd=urg_cmd,
    )

    # Persist
    result_path = executor.save_result(args.test, args.seed, result)
    print(f"\nResults saved to: {result_path}")

    # Print summary
    print("\n--- Results ---")
    if result.compile:
        print(f"Compile: {result.compile.status} ({result.compile.duration_seconds:.1f}s)")
        if result.compile.status != "pass":
            print(f"  Log: {result.compile.log_path}")
    if result.run:
        print(f"Run:     {result.run.status} ({result.run.duration_seconds:.1f}s)")
        print(f"  Log: {result.run.log_path}")
    if result.urg:
        print(f"URG:     {result.urg.status} ({result.urg.duration_seconds:.1f}s)")
        print(f"  Log: {result.urg.log_path}")

    # Exit code based on run status
    if result.run and result.run.status == "pass":
        return 0
    elif result.compile and result.compile.status != "pass":
        return 2  # compile failure
    else:
        return 1  # run failure or timeout


if __name__ == "__main__":
    sys.exit(main())

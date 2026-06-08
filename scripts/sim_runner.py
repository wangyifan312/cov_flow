#!/usr/bin/env python3
"""Simulation runner: renders command templates from manifest and produces results.

In mock mode (default), sim_runner.py does NOT execute shell commands. It validates
the manifest policy, renders command templates, and produces a mock sim_result.json.

In real mode (--real), sim_runner.py executes the compile + run pipeline via
SimExecutor, persists results to sim_results/{test}_{seed}/sim_result.json.

Usage:
    python scripts/sim_runner.py --manifest manifest.yaml --test my_test \
        --seed 1 --out result.json
    python scripts/sim_runner.py --manifest manifest.yaml --test my_test \
        --seed 1 --out result.json --dry-run
    python scripts/sim_runner.py --manifest manifest_real.yaml --test my_test \
        --seed 42 --real
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
    parser = argparse.ArgumentParser(description="Simulation runner.")
    parser.add_argument("--manifest", required=True, help="Path to project_manifest.yaml")
    parser.add_argument("--test", required=True, help="Test name")
    parser.add_argument(
        "--seed", required=True, type=int, help="Random seed (non-negative integer)",
    )
    parser.add_argument("--out", default=None, help="Output path for sim result JSON (mock mode)")
    parser.add_argument("--dry-run", action="store_true", default=True,
                        help="Dry-run mode (default: true in mock mode)")
    parser.add_argument("--real", action="store_true",
                        help="Run real VCS simulation (requires simulation.mode: real in manifest)")
    args = parser.parse_args()

    if args.seed < 0:
        report = {
            "ok": False,
            "error": f"Seed must be non-negative, got {args.seed}",
            "test": args.test,
            "seed": args.seed,
        }
        if args.out:
            _output(report, args.out)
        else:
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
        if args.out:
            _output(report, args.out)
        else:
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
        if args.out:
            _output(report, args.out)
        else:
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
        if args.out:
            _output(report, args.out)
        else:
            print(json.dumps(report, indent=2))
        return 1

    # === Mode branching ===
    if args.real:
        return _run_real(manifest, sim_config, args.test, args.seed)

    # === Mock mode (default) ===
    # --out is required in mock mode
    if not args.out:
        print("ERROR: --out is required in mock mode", file=sys.stderr)
        return 1

    commands = render_commands(manifest, args.test, args.seed)
    result = build_sim_result(
        args.test, args.seed, commands, policy_checked=True, dry_run=args.dry_run,
    )
    _output(result, args.out)
    return 0


def _run_real(
    manifest: Manifest,
    sim_config: dict,
    test: str,
    seed: int,
) -> int:
    """Run real simulation via SimExecutor."""
    from lib.sim_executor import SimExecutor

    # Check manifest mode
    if manifest.sim_mode != "real":
        print(f"ERROR: manifest simulation.mode is '{manifest.sim_mode}', not 'real'.")
        print("To run real simulation, set mode: real in the manifest.")
        return 1

    # Create executor
    executor = SimExecutor(
        project_root=manifest.project_root,
        results_root=manifest.sim_results_root,
        timeout_seconds=manifest.sim_timeout,
        urg_timeout_seconds=manifest.sim_urg_timeout,
    )

    # Validate test name and seed
    try:
        executor.validate_test_name(test)
        executor.validate_seed(seed)
    except ValueError as e:
        print(f"ERROR: {e}")
        return 1

    # Render commands from manifest
    compile_cmd = sim_config.get(
        "compile_cmd_template", "make compile TEST={test}",
    ).format(test=test, seed=seed)
    run_cmd = sim_config.get(
        "run_cmd_template", "make run TEST={test} SEED={seed}",
    ).format(test=test, seed=seed)

    # URG command (optional)
    urg_cmd = None
    urg_template = sim_config.get("urg_cmd_template")
    if urg_template:
        vdb_dir = sim_config.get(
            "vdb_dir_template", "sim_results/coverage/{test}_{seed}.vdb",
        ).format(test=test, seed=seed)
        report_dir = f"{executor.get_results_dir(test, seed)}/urg_report"
        urg_cmd = urg_template.format(vdb_dir=vdb_dir, report_dir=report_dir)

    # Run pipeline
    print(f"Running real simulation: test={test} seed={seed}")
    print(f"  compile: {compile_cmd}")
    print(f"  run:     {run_cmd}")
    if urg_cmd:
        print(f"  urg:     {urg_cmd}")

    result = executor.run_pipeline(
        test=test, seed=seed,
        compile_cmd=compile_cmd, run_cmd=run_cmd, urg_cmd=urg_cmd,
    )

    # Persist
    result_path = executor.save_result(test, seed, result)
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


def _output(data: dict, out_path: str) -> None:
    text = json.dumps(data, indent=2, ensure_ascii=False)
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    Path(out_path).write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    sys.exit(main())

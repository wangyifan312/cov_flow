#!/usr/bin/env python3
"""Eval runner: validate eval YAML structure and prepare for LLM execution.

Usage:
    python scripts/run_eval.py --eval evals/triage_gap_0001.yaml --dry-run
    python scripts/run_eval.py --eval-dir evals/ --dry-run
    python scripts/run_eval.py --eval evals/triage_gap_0001.yaml --out report.json

Note: This is a dry-run validator. LLM execution is deferred to Phase 3+.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import yaml

VALID_TASK_MODES = {"triage", "scenario", "generate-case", "feedback"}

VALID_CLASSIFICATIONS = {
    "Missing Stimulus",
    "Config Missing",
    "Constraint Too Tight",
    "Coverage Model Issue",
    "Monitor Sampling Issue",
    "Unreachable Candidate",
}

REGISTERED_TOOLS = {
    "cov_list_uncovered",
    "cov_get_gap_detail",
    "cov_get_coverpoint_source",
    "spec_search",
    "reg_find_fields_affecting_feature",
    "tb_get_existing_tests_for_feature",
    "rtl_find_signal",
    "sim_run_targeted_test",
    "sim_get_test_result",
    "sim_search_log",
    "cov_get_coverage_diff",
}


def validate_eval(eval_data: dict[str, Any]) -> dict[str, Any]:
    """Validate eval YAML structure.

    Returns validation report with yaml_valid, has_prompt, has_expected_tools,
    tool_count, and any errors.
    """
    errors: list[str] = []

    # Check required fields
    required_fields = ["eval_id", "task_mode", "prompt", "expected_tools"]
    for field in required_fields:
        if field not in eval_data:
            errors.append(f"Missing required field: {field}")

    # Check task_mode enum
    task_mode = eval_data.get("task_mode")
    if task_mode and task_mode not in VALID_TASK_MODES:
        errors.append(
            f"Invalid task_mode: {task_mode}. Must be one of: {sorted(VALID_TASK_MODES)}"
        )

    # Check expected_tools non-empty
    expected_tools = eval_data.get("expected_tools", [])
    if not expected_tools:
        errors.append("expected_tools must be non-empty")

    # Check each tool exists in registered tools
    unknown_tools = []
    for tool in expected_tools:
        if tool not in REGISTERED_TOOLS:
            unknown_tools.append(tool)
    if unknown_tools:
        errors.append(f"Unknown tools in expected_tools: {unknown_tools}")

    # Check expected_classification enum (if present)
    classification = eval_data.get("expected_classification")
    if classification is not None and classification not in VALID_CLASSIFICATIONS:
        errors.append(
            f"Invalid expected_classification: {classification}. "
            f"Must be one of: {sorted(VALID_CLASSIFICATIONS)}"
        )

    yaml_valid = len(errors) == 0

    return {
        "yaml_valid": yaml_valid,
        "has_prompt": "prompt" in eval_data and bool(eval_data["prompt"]),
        "has_expected_tools": bool(expected_tools),
        "tool_count": len(expected_tools),
        "errors": errors,
    }


def run_eval_single(eval_path: Path, dry_run: bool = True) -> dict[str, Any]:
    """Run a single eval case (dry-run mode).

    Returns structured report with eval metadata and validation results.
    """
    # Load YAML
    try:
        with open(eval_path, encoding="utf-8") as f:
            eval_data = yaml.safe_load(f)
    except FileNotFoundError:
        return {
            "ok": False,
            "tool": "run_eval",
            "eval_id": "unknown",
            "error": f"Eval file not found: {eval_path}",
        }
    except yaml.YAMLError as e:
        return {
            "ok": False,
            "tool": "run_eval",
            "eval_id": "unknown",
            "error": f"Failed to parse YAML: {e}",
        }

    if not isinstance(eval_data, dict):
        return {
            "ok": False,
            "tool": "run_eval",
            "eval_id": "unknown",
            "error": f"Eval must be a YAML mapping, got {type(eval_data).__name__}",
        }

    eval_id = eval_data.get("eval_id", "unknown")
    task_mode = eval_data.get("task_mode", "")
    prompt = eval_data.get("prompt", "")
    expected_tools = eval_data.get("expected_tools", [])
    expected_classification = eval_data.get("expected_classification")
    expected_output_keys = eval_data.get("expected_output_keys", [])

    # Validate structure
    validation = validate_eval(eval_data)

    ok = validation["yaml_valid"]

    report = {
        "ok": ok,
        "tool": "run_eval",
        "eval_id": eval_id,
        "task_mode": task_mode,
        "prompt": prompt,
        "expected_tools": expected_tools,
        "expected_classification": expected_classification,
        "expected_output_keys": expected_output_keys,
        "validation": validation,
    }

    if dry_run:
        report["status"] = "dry_run_complete"
        report["message"] = "Eval case validated. LLM execution deferred to Phase 3+."

    return report


def run_eval_batch(eval_dir: Path, dry_run: bool = True) -> dict[str, Any]:
    """Run all eval cases in a directory (dry-run mode).

    Returns batch report with per-eval results and summary.
    """
    yaml_files = sorted(eval_dir.glob("*.yaml")) + sorted(eval_dir.glob("*.yml"))

    if not yaml_files:
        return {
            "ok": False,
            "tool": "run_eval",
            "error": f"No YAML files found in {eval_dir}",
            "evals": [],
            "summary": {"total": 0, "valid": 0, "invalid": 0},
        }

    evals: list[dict[str, Any]] = []
    valid_count = 0
    invalid_count = 0

    for yaml_file in yaml_files:
        result = run_eval_single(yaml_file, dry_run=dry_run)
        evals.append(result)
        if result.get("ok"):
            valid_count += 1
        else:
            invalid_count += 1

    total = len(evals)
    all_ok = invalid_count == 0

    return {
        "ok": all_ok,
        "tool": "run_eval",
        "evals": evals,
        "summary": {
            "total": total,
            "valid": valid_count,
            "invalid": invalid_count,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Eval runner: validate eval YAML structure (dry-run mode)."
    )
    parser.add_argument(
        "--eval",
        dest="eval_file",
        help="Path to a single eval YAML file.",
    )
    parser.add_argument(
        "--eval-dir",
        dest="eval_dir",
        help="Path to directory containing eval YAML files (batch mode).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Dry-run mode (default). Validates structure without LLM execution.",
    )
    parser.add_argument(
        "--out",
        default=None,
        help="Output path for the report JSON. Prints to stdout if omitted.",
    )
    args = parser.parse_args()

    if not args.eval_file and not args.eval_dir:
        parser.error("Either --eval or --eval-dir is required")

    if args.eval_file and args.eval_dir:
        parser.error("Cannot specify both --eval and --eval-dir")

    if args.eval_file:
        report = run_eval_single(Path(args.eval_file), dry_run=args.dry_run)
    else:
        report = run_eval_batch(Path(args.eval_dir), dry_run=args.dry_run)

    text = json.dumps(report, indent=2, ensure_ascii=False)
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(text, encoding="utf-8")
        print(f"Report written to {args.out}")
    else:
        print(text)

    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())

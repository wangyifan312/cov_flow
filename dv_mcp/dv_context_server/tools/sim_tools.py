"""Simulation MCP tools (pure Python, no MCP runtime dependency).

Provides tools for running simulations, querying results, and computing
coverage diffs. All functions return the standard envelope format.
"""

from __future__ import annotations

import json
from typing import Any

from dv_mcp.dv_context_server.services.audit import audit_record
from dv_mcp.dv_context_server.services.evidence import simulation_evidence
from dv_mcp.dv_context_server.services.project_loader import get_manifest
from dv_mcp.dv_context_server.services.summarizer import envelope, error_envelope, truncate_list
from lib.coverage_diff import compute_diff


def sim_run_targeted_test(
    project: str,
    test: str,
    seed: int,
    confirm: bool = False,
) -> dict[str, Any]:
    """Run a targeted simulation test (mock MVP: dry-run only).

    Requires confirm=true to proceed. Checks manifest policy before rendering
    command templates.
    """
    tool_name = "sim_run_targeted_test"
    args = {"project": project, "test": test, "seed": seed, "confirm": confirm}

    try:
        manifest = get_manifest(project)
    except (FileNotFoundError, Exception) as e:
        return error_envelope(tool_name, project, f"Cannot load project: {e}")

    # Check policy
    policy = manifest.data.get("policy", {})
    allow_sim = policy.get("allow_running_simulation", False)
    if not allow_sim:
        return error_envelope(
            tool_name, project,
            "Simulation not allowed: manifest policy.allow_running_simulation is false",
        )

    # Require explicit confirmation
    if not confirm:
        audit = audit_record(tool_name, project, args)
        return envelope(
            tool_name, project,
            result={"message": "Simulation execution requires confirm=true"},
            evidence=[],
            audit=audit,
            safety={
                "policy_checked": True,
                "confirmed": False,
                "command_template_used": None,
            },
        )

    # Render commands from manifest templates
    sim_config = manifest.data.get("simulation", {})
    compile_template = sim_config.get("compile_cmd_template", "make compile TEST={test}")
    run_template = sim_config.get("run_cmd_template", "make run TEST={test} SEED={seed}")
    coverage_template = sim_config.get("coverage_cmd_template", "make cov TEST={test}")

    commands = {
        "compile_command": compile_template.format(test=test, seed=seed),
        "run_command": run_template.format(test=test, seed=seed),
        "coverage_command": coverage_template.format(test=test, seed=seed),
    }

    result = {
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
        "dry_run": True,
    }

    evidence = [
        simulation_evidence(test, seed, commands["run_command"],
                            f"Mock simulation result for {test} seed={seed}"),
    ]

    audit = audit_record(tool_name, project, args)
    safety = {
        "policy_checked": True,
        "confirmed": True,
        "command_template_used": run_template,
    }

    return envelope(tool_name, project, result, evidence, audit=audit, safety=safety)


def sim_get_test_result(
    project: str,
    test: str,
    seed: int | None = None,
) -> dict[str, Any]:
    """Get simulation result for a test.

    Reads mock sim_data if available, otherwise returns a default mock result.
    """
    tool_name = "sim_get_test_result"
    args = {"project": project, "test": test, "seed": seed}

    try:
        manifest = get_manifest(project)
    except (FileNotFoundError, Exception) as e:
        return error_envelope(tool_name, project, f"Cannot load project: {e}")

    # Look for sim result in sim_data directory
    sim_data_dir = manifest.base_dir / "sim_data"
    log_path = None

    if seed is not None:
        candidate = sim_data_dir / "sim_logs" / f"{test}_{seed}.log"
        if candidate.exists():
            log_path = candidate

    # Read log summary if available
    log_summary = ""
    if log_path and log_path.exists():
        lines = log_path.read_text(encoding="utf-8").strip().splitlines()
        # Extract key lines
        pass_lines = [
            line for line in lines if "PASSED" in line or "FAILED" in line
        ]
        log_summary = pass_lines[-1] if pass_lines else f"Log has {len(lines)} lines"
        sim_status = "pass" if any("PASSED" in line for line in lines) else "unknown"
    else:
        sim_status = "not_found"
        log_summary = f"No log found for test={test} seed={seed}"

    result = {
        "test": test,
        "seed": seed,
        "compile_status": "pass" if sim_status != "not_found" else "unknown",
        "sim_status": sim_status,
        "log_summary": log_summary,
        "log_path": str(log_path) if log_path else None,
    }

    evidence = []
    if log_path:
        evidence.append(
            simulation_evidence(test, seed or 0, str(log_path),
                                f"Simulation log for {test}")
        )

    audit = audit_record(tool_name, project, args)
    return envelope(tool_name, project, result, evidence, audit=audit)


def sim_search_log(
    project: str,
    test: str,
    seed: int,
    keyword: str,
) -> dict[str, Any]:
    """Search simulation log for a keyword.

    Returns matching lines (bounded to 20 lines max).
    """
    tool_name = "sim_search_log"
    args = {"project": project, "test": test, "seed": seed, "keyword": keyword}

    try:
        manifest = get_manifest(project)
    except (FileNotFoundError, Exception) as e:
        return error_envelope(tool_name, project, f"Cannot load project: {e}")

    log_path = manifest.base_dir / "sim_data" / "sim_logs" / f"{test}_{seed}.log"

    if not log_path.exists():
        return error_envelope(tool_name, project, f"Log file not found: {log_path}")

    lines = log_path.read_text(encoding="utf-8").strip().splitlines()
    matches = [line for line in lines if keyword.lower() in line.lower()]
    matches, was_truncated = truncate_list(matches, max_items=20)

    result = {
        "test": test,
        "seed": seed,
        "keyword": keyword,
        "matches": matches,
        "total_matches": len([line for line in lines if keyword.lower() in line.lower()]),
        "log_path": str(log_path),
    }

    evidence = [
        simulation_evidence(test, seed, str(log_path),
                            f"Log search for '{keyword}': {len(matches)} matches"),
    ]

    audit = audit_record(tool_name, project, args)
    return envelope(tool_name, project, result, evidence,
                    truncated=was_truncated, audit=audit)


def cov_get_coverage_diff(
    project: str,
    gap_id: str | None = None,
) -> dict[str, Any]:
    """Compute coverage diff between before/after databases.

    Reads mock sim_data/coverage_db_before.json and coverage_db_after.json.
    If gap_id is specified, only returns that gap's delta.
    """
    tool_name = "cov_get_coverage_diff"
    args = {"project": project, "gap_id": gap_id}

    try:
        manifest = get_manifest(project)
    except (FileNotFoundError, Exception) as e:
        return error_envelope(tool_name, project, f"Cannot load project: {e}")

    before_path = manifest.base_dir / "sim_data" / "coverage_db_before.json"
    after_path = manifest.base_dir / "sim_data" / "coverage_db_after.json"

    if not before_path.exists():
        return error_envelope(tool_name, project, f"Before DB not found: {before_path}")
    if not after_path.exists():
        return error_envelope(tool_name, project, f"After DB not found: {after_path}")

    with open(before_path, encoding="utf-8") as f:
        before = json.load(f)
    with open(after_path, encoding="utf-8") as f:
        after = json.load(f)

    diff_result = compute_diff(before, after, gap_id_filter=gap_id)

    summary_msg = (
        f"Coverage diff: {diff_result['summary']['newly_covered']} newly covered, "
        f"{diff_result['summary']['regressed']} regressed"
    )
    evidence = [
        simulation_evidence("coverage_diff", 0, str(after_path), summary_msg),
    ]

    audit = audit_record(tool_name, project, args)
    return envelope(tool_name, project, diff_result, evidence, audit=audit)

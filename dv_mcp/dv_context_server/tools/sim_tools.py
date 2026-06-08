"""Simulation MCP tools (pure Python, no MCP runtime dependency).

Provides tools for running simulations, querying results, and computing
coverage diffs. All functions return the standard envelope format.

Supports two modes:
- mock (default): Returns fake data, no subprocess execution
- real: Calls SimExecutor/SimLogParser/UrgRunner for actual VCS execution
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

from dv_mcp.dv_context_server.services.audit import audit_record
from dv_mcp.dv_context_server.services.evidence import simulation_evidence
from dv_mcp.dv_context_server.services.project_loader import get_manifest
from dv_mcp.dv_context_server.services.summarizer import envelope, error_envelope, truncate_list
from lib.coverage_diff import compute_diff

if TYPE_CHECKING:
    from lib.sim_executor import SimResult


def _sim_result_to_dict(sr: SimResult, test: str, seed: int) -> dict:
    """Convert SimResult dataclass to MCP result dict."""
    def _step_dict(step: Any) -> dict | None:
        if step is None:
            return None
        return {
            "step": step.step,
            "status": step.status,
            "return_code": step.return_code,
            "log_path": step.log_path,
            "duration_seconds": round(step.duration_seconds, 2),
            "message": step.message,
        }
    return {
        "test": test,
        "seed": seed,
        "compile": _step_dict(sr.compile),
        "run": _step_dict(sr.run),
        "urg": _step_dict(sr.urg),
        "started_at": sr.started_at,
        "finished_at": sr.finished_at,
        "dry_run": False,
    }


def sim_run_targeted_test(
    project: str,
    test: str,
    seed: int,
    confirm: bool = False,
) -> dict[str, Any]:
    """Run a targeted simulation test.

    Requires confirm=true to proceed. Checks manifest policy before rendering
    command templates. In real mode, executes VCS subprocess via SimExecutor.
    In mock mode (default), returns fake data.
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

    # === Mode branching ===
    sim_mode = manifest.sim_mode

    if sim_mode == "real":
        from lib.sim_executor import SimExecutor

        executor = SimExecutor(
            project_root=manifest.project_root,
            results_root=manifest.sim_results_root,
            timeout_seconds=manifest.sim_timeout,
            urg_timeout_seconds=manifest.sim_urg_timeout,
        )

        # Validate inputs
        try:
            executor.validate_test_name(test)
            executor.validate_seed(seed)
        except ValueError as e:
            return error_envelope(tool_name, project, str(e))

        # Render commands
        compile_cmd = compile_template.format(test=test, seed=seed)
        run_cmd = run_template.format(test=test, seed=seed)

        # URG command (optional)
        urg_cmd = None
        urg_template = sim_config.get("urg_cmd_template")
        if urg_template:
            vdb_dir = sim_config.get(
                "vdb_dir_template", "sim_results/coverage/{test}_{seed}.vdb"
            ).format(test=test, seed=seed)
            report_dir = f"{executor.get_results_dir(test, seed)}/urg_report"
            urg_cmd = urg_template.format(vdb_dir=vdb_dir, report_dir=report_dir)

        # Run pipeline
        sim_result = executor.run_pipeline(
            test=test, seed=seed,
            compile_cmd=compile_cmd,
            run_cmd=run_cmd,
            urg_cmd=urg_cmd,
        )

        # Persist
        executor.save_result(test, seed, sim_result)

        # Build result dict from SimResult
        result = _sim_result_to_dict(sim_result, test, seed)

        evidence = [
            simulation_evidence(test, seed, str(executor.get_results_dir(test, seed)),
                                f"Real simulation result for {test} seed={seed}"),
        ]

        audit = audit_record(tool_name, project, args)
        safety = {
            "policy_checked": True,
            "confirmed": True,
            "command_template_used": run_template,
            "mode": "real",
        }

        return envelope(tool_name, project, result, evidence, audit=audit, safety=safety)

    else:
        # === Mock mode (default) ===
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
            "mode": "mock",
        }

        return envelope(tool_name, project, result, evidence, audit=audit, safety=safety)


def sim_get_test_result(
    project: str,
    test: str,
    seed: int | None = None,
) -> dict[str, Any]:
    """Get simulation result for a test.

    In real mode, loads persisted SimResult or parses run.log.
    In mock mode, reads sim_data if available, otherwise returns default mock.
    """
    tool_name = "sim_get_test_result"
    args = {"project": project, "test": test, "seed": seed}

    try:
        manifest = get_manifest(project)
    except (FileNotFoundError, Exception) as e:
        return error_envelope(tool_name, project, f"Cannot load project: {e}")

    # === Mode branching ===
    sim_mode = manifest.sim_mode

    if sim_mode == "real" and seed is not None:
        from lib.sim_executor import SimExecutor

        executor = SimExecutor(
            project_root=manifest.project_root,
            results_root=manifest.sim_results_root,
        )

        # 1. Try loading persisted SimResult
        sim_result = executor.load_result(test, seed)
        if sim_result is not None:
            result = _sim_result_to_dict(sim_result, test, seed)
            evidence = [simulation_evidence(test, seed, str(executor.get_results_dir(test, seed)),
                                            f"Real simulation result for {test} seed={seed}")]
            audit = audit_record(tool_name, project, args)
            return envelope(tool_name, project, result, evidence, audit=audit)

        # 2. Try parsing run.log directly
        log_content = executor.read_log(test, seed, "run")
        if log_content is not None:
            from lib.sim_log_parser import parse_vcs_log
            summary = parse_vcs_log(log_content)
            result = {
                "test": test,
                "seed": seed,
                "sim_status": summary.status,
                "log_summary": (
                    summary.test_pass_line
                    or f"UVM: {summary.uvm_fatal} fatal, {summary.uvm_error} error"
                ),
                "log_path": str(executor.get_log_path(test, seed, "run")),
                "uvm_counts": {
                    "info": summary.uvm_info,
                    "warning": summary.uvm_warning,
                    "error": summary.uvm_error,
                    "fatal": summary.uvm_fatal,
                },
            }
            evidence = [simulation_evidence(test, seed, result["log_path"],
                                            f"Parsed simulation log for {test}")]
            audit = audit_record(tool_name, project, args)
            return envelope(tool_name, project, result, evidence, audit=audit)

        # 3. Fall through to mock behavior (no real results found)

    # === Mock mode (default) or fallthrough ===
    # Look for sim result in sim_data directory
    sim_data_dir = manifest.base_dir / "sim_data"
    mock_log_path: Path | None = None

    if seed is not None:
        candidate = sim_data_dir / "sim_logs" / f"{test}_{seed}.log"
        if candidate.exists():
            mock_log_path = candidate

    # Read log summary if available
    log_summary = ""
    if mock_log_path and mock_log_path.exists():
        lines = mock_log_path.read_text(encoding="utf-8").strip().splitlines()
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
        "log_path": str(mock_log_path) if mock_log_path else None,
    }

    mock_evidence: list[dict[str, Any]] = []
    if mock_log_path:
        mock_evidence.append(
            simulation_evidence(test, seed or 0, str(mock_log_path),
                                f"Simulation log for {test}")
        )

    audit = audit_record(tool_name, project, args)
    return envelope(tool_name, project, result, mock_evidence, audit=audit)


def sim_search_log(
    project: str,
    test: str,
    seed: int,
    keyword: str,
) -> dict[str, Any]:
    """Search simulation log for a keyword.

    In real mode, searches real log files via SimExecutor.
    In mock mode, searches sim_data/sim_logs.
    Returns matching lines (bounded to 20 lines max).
    """
    tool_name = "sim_search_log"
    args = {"project": project, "test": test, "seed": seed, "keyword": keyword}

    try:
        manifest = get_manifest(project)
    except (FileNotFoundError, Exception) as e:
        return error_envelope(tool_name, project, f"Cannot load project: {e}")

    # === Mode branching ===
    sim_mode = manifest.sim_mode

    if sim_mode == "real":
        from lib.sim_executor import SimExecutor

        executor = SimExecutor(
            project_root=manifest.project_root,
            results_root=manifest.sim_results_root,
        )

        search_result = executor.search_log(test, seed, keyword, step="run")
        if search_result["total_matches"] > 0 or executor.read_log(test, seed, "run") is not None:
            log_path = str(executor.get_log_path(test, seed, "run"))
            result = {
                "test": test,
                "seed": seed,
                "keyword": keyword,
                "matches": search_result["matches"],
                "total_matches": search_result["total_matches"],
                "log_path": log_path,
            }
            match_count = search_result["total_matches"]
            evidence = [simulation_evidence(
                test, seed, log_path,
                f"Log search for '{keyword}': {match_count} matches",
            )]
            was_truncated = search_result["total_matches"] > len(search_result["matches"])
            audit = audit_record(tool_name, project, args)
            return envelope(tool_name, project, result, evidence,
                            truncated=was_truncated, audit=audit)

        # Fall through to mock behavior

    # === Mock mode (default) or fallthrough ===
    mock_log_path = manifest.base_dir / "sim_data" / "sim_logs" / f"{test}_{seed}.log"

    if not mock_log_path.exists():
        return error_envelope(tool_name, project, f"Log file not found: {mock_log_path}")

    lines = mock_log_path.read_text(encoding="utf-8").strip().splitlines()
    matches = [line for line in lines if keyword.lower() in line.lower()]
    matches, was_truncated = truncate_list(matches, max_items=20)

    result = {
        "test": test,
        "seed": seed,
        "keyword": keyword,
        "matches": matches,
        "total_matches": len([line for line in lines if keyword.lower() in line.lower()]),
        "log_path": str(mock_log_path),
    }

    evidence = [
        simulation_evidence(test, seed, str(mock_log_path),
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

    In real mode, auto-discovers latest URG reports from sim_results.
    In mock mode, reads sim_data/coverage_db_before.json and coverage_db_after.json.
    If gap_id is specified, only returns that gap's delta.
    """
    tool_name = "cov_get_coverage_diff"
    args = {"project": project, "gap_id": gap_id}

    try:
        manifest = get_manifest(project)
    except (FileNotFoundError, Exception) as e:
        return error_envelope(tool_name, project, f"Cannot load project: {e}")

    # === Mode branching ===
    sim_mode = manifest.sim_mode

    if sim_mode == "real":
        # Auto-discover latest coverage_db files from sim_results
        results_root = manifest.sim_results_root
        if not results_root.is_dir():
            return error_envelope(tool_name, project,
                                  f"sim_results directory not found: {results_root}")

        # Find most recent urg_report/coverage_gaps.json
        urg_reports = sorted(
            results_root.glob("*/urg_report/coverage_gaps.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )

        if len(urg_reports) >= 2:
            after_path = urg_reports[0]
            before_path = urg_reports[1]
        elif len(urg_reports) == 1:
            after_path = urg_reports[0]
            before_path = None
        else:
            return error_envelope(tool_name, project,
                                  "No URG reports found in sim_results/")

        if before_path is None:
            # Single report — return as-is without diff
            with open(after_path, encoding="utf-8") as f:
                after = json.load(f)
            audit = audit_record(tool_name, project, args)
            return envelope(tool_name, project,
                            {"report_id": "latest", "gaps": after.get("gaps", []),
                             "summary": {"note": "Only one report found, no diff computed"}},
                            [simulation_evidence("coverage_diff", 0, str(after_path),
                                                 "Single URG report (no diff)")],
                            audit=audit)

        # Both paths found — fall through to diff computation below
    else:
        # === Mock mode (default) ===
        before_path = manifest.base_dir / "sim_data" / "coverage_db_before.json"
        after_path = manifest.base_dir / "sim_data" / "coverage_db_after.json"

        if not before_path.exists():
            return error_envelope(tool_name, project, f"Before DB not found: {before_path}")
        if not after_path.exists():
            return error_envelope(tool_name, project, f"After DB not found: {after_path}")

    # === Common diff computation ===
    with open(before_path, encoding="utf-8") as f:  # type: ignore[arg-type]
        before = json.load(f)
    with open(after_path, encoding="utf-8") as f:  # type: ignore[arg-type]
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

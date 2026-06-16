"""Simulation MCP tools (pure Python, no MCP runtime dependency).

Provides tools for running simulations, querying results, and computing
coverage diffs. All functions return the standard envelope format.

All simulation tools execute real VCS subprocess via SimExecutor.

Also provides a permanent stub for waveform analysis (wave_check_condition)
which requires Verdi/NPI integration (not available per project rules).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

from dv_mcp.dv_context_server.services.audit import audit_record
from dv_mcp.dv_context_server.services.evidence import simulation_evidence
from dv_mcp.dv_context_server.services.project_loader import get_manifest
from dv_mcp.dv_context_server.services.summarizer import envelope, error_envelope
from lib.coverage_diff import compute_diff
from lib.remote_executor import RemoteSimExecutor

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



def _create_executor(manifest: Any) -> Any:
    """Create a SimExecutor or RemoteSimExecutor based on manifest config."""
    from lib.sim_executor import SimExecutor

    if manifest.is_remote and manifest.remote_host:
        return RemoteSimExecutor(
            host=manifest.remote_host,
            project_root=Path(manifest.remote_project_root or str(manifest.project_root)),
            results_root=manifest.sim_results_root,
            timeout_seconds=manifest.sim_timeout,
            urg_timeout_seconds=manifest.sim_urg_timeout,
            env_setup=manifest.remote_env_setup,
        )
    return SimExecutor(
        project_root=manifest.project_root,
        results_root=manifest.sim_results_root,
        timeout_seconds=manifest.sim_timeout,
        urg_timeout_seconds=manifest.sim_urg_timeout,
    )


def sim_run_targeted_test(
    project: str,
    test: str,
    seed: int,
    confirm: bool = False,
) -> dict[str, Any]:
    """Run a targeted simulation test.

    Requires confirm=true to proceed. Checks manifest policy before rendering
    command templates. Executes VCS subprocess via SimExecutor.
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

    # === Real simulation execution (local or remote) ===
    executor = _create_executor(manifest)

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


def sim_get_test_result(
    project: str,
    test: str,
    seed: int | None = None,
) -> dict[str, Any]:
    """Get simulation result for a test.

    Loads persisted SimResult or parses run.log from sim_results.
    """
    tool_name = "sim_get_test_result"
    args = {"project": project, "test": test, "seed": seed}

    try:
        manifest = get_manifest(project)
    except (FileNotFoundError, Exception) as e:
        return error_envelope(tool_name, project, f"Cannot load project: {e}")

    if seed is not None:
        executor = _create_executor(manifest)

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

        # 3. No results found
        return error_envelope(
            tool_name, project,
            f"No simulation results found for test={test} seed={seed}",
        )

    # seed is None — cannot locate results without a seed
    audit = audit_record(tool_name, project, args)
    return envelope(
        tool_name, project,
        {
            "test": test,
            "seed": seed,
            "sim_status": "not_found",
            "log_summary": "seed is required to locate simulation results",
        },
        [],
        audit=audit,
    )


def sim_search_log(
    project: str,
    test: str,
    seed: int,
    keyword: str,
) -> dict[str, Any]:
    """Search simulation log for a keyword.

    Searches real log files via SimExecutor.
    Returns matching lines (bounded to 20 lines max).
    """
    tool_name = "sim_search_log"
    args = {"project": project, "test": test, "seed": seed, "keyword": keyword}

    try:
        manifest = get_manifest(project)
    except (FileNotFoundError, Exception) as e:
        return error_envelope(tool_name, project, f"Cannot load project: {e}")

    executor = _create_executor(manifest)

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

    return error_envelope(
        tool_name, project,
        f"Log file not found for test={test} seed={seed}",
    )


def cov_get_coverage_diff(
    project: str,
    gap_id: str | None = None,
) -> dict[str, Any]:
    """Compute coverage diff between before/after databases.

    Auto-discovers latest URG reports from sim_results.
    If gap_id is specified, only returns that gap's delta.
    """
    tool_name = "cov_get_coverage_diff"
    args = {"project": project, "gap_id": gap_id}

    try:
        manifest = get_manifest(project)
    except (FileNotFoundError, Exception) as e:
        return error_envelope(tool_name, project, f"Cannot load project: {e}")

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

    before_path: Path | None = None
    after_path: Path | None = None

    if len(urg_reports) >= 2:
        after_path = urg_reports[0]
        before_path = urg_reports[1]
    elif len(urg_reports) == 1:
        after_path = urg_reports[0]
    else:
        return error_envelope(tool_name, project,
                              "No URG reports found in sim_results/")

    if before_path is None:
        # Single report — return as-is without diff
        with open(after_path, encoding="utf-8") as f:  # type: ignore[arg-type]
            after = json.load(f)
        audit = audit_record(tool_name, project, args)
        return envelope(tool_name, project,
                        {"report_id": "latest", "gaps": after.get("gaps", []),
                         "summary": {"note": "Only one report found, no diff computed"}},
                        [simulation_evidence("coverage_diff", 0, str(after_path),
                                             "Single URG report (no diff)")],
                        audit=audit)

    # === Diff computation ===
    with open(before_path, encoding="utf-8") as f:
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


def wave_check_condition(
    project: str,
    signal_path: str,
    condition: str,
    time_range: str | None = None,
) -> dict[str, Any]:
    """Check signal condition in waveform (stub).

    This is a permanent stub. Real waveform analysis requires
    Verdi/NPI integration which is not available per project rules.

    Args:
        project: Project ID or manifest path.
        signal_path: Hierarchical signal path (e.g. 'top.dut.axi_valid').
        condition: Condition expression to check (e.g. 'axi_valid && axi_ready').
        time_range: Optional time range as 'start,end' string (e.g. '0,1000').

    Returns:
        Envelope with waveform query results. mode is always 'stub'.
    """
    tool_name = "wave_check_condition"
    args = {
        "project": project,
        "signal_path": signal_path,
        "condition": condition,
        "time_range": time_range,
    }

    try:
        _manifest = get_manifest(project)
    except (FileNotFoundError, Exception) as e:
        return error_envelope(tool_name, project, f"Cannot load project: {e}")

    # Parse time_range string into tuple
    parsed_time_range: tuple[int, int] | None = None
    if time_range is not None:
        try:
            parts = time_range.split(",")
            if len(parts) == 2:
                parsed_time_range = (int(parts[0].strip()), int(parts[1].strip()))
            else:
                return error_envelope(
                    tool_name, project,
                    f"Invalid time_range format: '{time_range}'. "
                    f"Expected 'start,end' (e.g. '0,1000')",
                )
        except (ValueError, IndexError):
            return error_envelope(
                tool_name, project,
                f"Invalid time_range format: '{time_range}'. Expected 'start,end' (e.g. '0,1000')",
            )

    # Use StubVerdiAdapter for waveform query
    from lib.eda_adapters import get_adapter

    adapter = get_adapter("verdi_stub")
    adapter_result = adapter.query_signal(signal_path, time_range=parsed_time_range)

    # Build time_range output (use parsed tuple if available, else original string)
    time_range_out: list[int] | None = None
    if parsed_time_range is not None:
        time_range_out = [parsed_time_range[0], parsed_time_range[1]]

    result = {
        "signal_path": signal_path,
        "condition": condition,
        "time_range": time_range_out,
        "mode": "stub",
        "signal_values": adapter_result.get("values", []),
        "condition_met": None,
        "note": (
            "Real waveform analysis requires Verdi/NPI integration "
            "(not available in current build)"
        ),
    }

    evidence = [
        simulation_evidence(
            "", 0, signal_path,
            f"Waveform query for '{signal_path}' condition='{condition}'",
        ),
    ]

    audit = audit_record(tool_name, project, args)
    return envelope(
        tool_name, project, result, evidence, audit=audit,
        next_actions=["sim_search_log"],
    )

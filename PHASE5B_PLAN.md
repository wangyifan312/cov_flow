# Phase 5b — Real VCS Simulation & URG Coverage Integration

## Context

Currently the 4 simulation MCP tools (`sim_run_targeted_test`, `sim_get_test_result`, `sim_search_log`, `cov_get_coverage_diff`) are mock/dry-run only — they return hardcoded fake data without executing anything. The user's axi2ahb project on the remote server has real VCS simulation infrastructure (`make compile` + `make run`) and URG HTML coverage reports. This plan upgrades these tools to support real execution while keeping mock mode as the safe default.

## Architecture

```
MCP Tool Layer (sim_tools.py)          ← policy check + mode branching + envelope
         │
         ├── mode: "mock" → existing dry-run behavior (unchanged)
         │
         └── mode: "real" →
              ├── SimExecutor          ← subprocess management, log I/O
              │    ├── compile()       ← subprocess.run(compile_cmd, cwd=project_root)
              │    └── run_simulation()← subprocess.run(run_cmd, cwd=project_root)
              │
              ├── SimLogParser         ← VCS/UVM log parsing, pass/fail detection
              │
              └── UrgRunner            ← urg invocation → urg_parser → coverage_db
```

Core principle: simulation execution logic lives in `lib/` (shared library), MCP tool layer stays thin.

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Sync vs Async | Sync + configurable timeout (default 600s) | MCP tools are request/response; most targeted tests < 2min; timeout overflow returns `status: "timeout"` |
| Output dir | `{project_root}/sim_results/{test}_{seed}/` | Standard DV convention; configurable via manifest |
| URG invocation | Manifest template `urg_cmd_template` | Same pattern as compile/run commands |
| URG timeout | Separate `urg_timeout_seconds` (default 300s) | URG report generation is typically faster than simulation; decoupled from `timeout_seconds` |
| Coverage format | URG HTML → existing `urg_parser` → coverage_gaps.json → `compute_diff()` | Reuses entire Phase 3 parser pipeline |
| Mock fallback | `simulation.mode: "mock"` (default) | Zero breaking changes; real mode needs 3 gates |
| Concurrency | Not supported — no file locking | Each `SimExecutor` instance is single-threaded; MCP tools are synchronous request/response; documenting this avoids false expectations |
| Result cleanup | Out of scope for Phase 5b | `sim_results/` grows without bound; cleanup utility deferred to a future phase or handled by project-level CI |
| Compile failure | Skip run AND URG | If compile fails, there is no vdb to feed URG; return compile log only |

## Security Gates (Triple Lock)

1. `simulation.mode: "real"` in manifest (new gate)
2. `policy.allow_running_simulation: true` (existing)
3. `confirm: true` in tool call argument (existing)
4. Test name regex: `^[a-zA-Z0-9_][a-zA-Z0-9_.\-]*$` (prevent shell injection)
5. Explicit path traversal rejection: `".." in test` and `"/" in test` → `ValueError` (the regex allows `..` so an additional string check is required)
6. `shlex.split()` + `shell=False` (no shell interpretation)
7. `cwd` locked to `project_root`

---

## Implementation Plan

### WP-1: Foundation Library (3 new files)

#### 1.1 `lib/sim_executor.py` (~250 lines)

`SimExecutor` class with:
- `validate_test_name(test)` — regex check + explicit `".." in test` / `"/" in test` rejection, prevents shell injection and path traversal
- `validate_seed(seed)` — non-negative check
- `compile(command, test, seed)` → `SimStepResult` — subprocess.run with log capture
- `run_simulation(command, test, seed)` → `SimStepResult` — same pattern
- `_execute_step(step, command, log_path)` — core subprocess logic with timeout
- `get_results_dir(test, seed)` — creates `{results_root}/{test}_{seed}/` with `mkdir(parents=True, exist_ok=True)`
- `get_log_path(test, seed, step)` — `{results_dir}/{step}.log`
- `save_result(test, seed, result)` — writes `sim_result.json`
- `load_result(test, seed)` — reads `sim_result.json`
- `read_log(test, seed, step)` — reads full log content
- `search_log(test, seed, keyword, step)` — bounded keyword search (max 20 matches), returns `{"matches": [...], "total_matches": N}` so callers know if results were truncated

Key: `subprocess.run(cmd_args, capture_output=True, text=True, timeout=self._timeout, cwd=str(self._project_root))`

#### 1.2 `lib/sim_log_parser.py` (~120 lines)

VCS/UVM log parsing:
- `parse_vcs_log(log_content)` → `SimLogSummary`
- `detect_pass_fail(log_content)` → `"pass" | "fail" | "unknown"`
- Pass/fail priority: explicit "Test PASSED/FAILED" > UVM_FATAL > UVM_ERROR > $finish
- Count UVM_INFO / UVM_WARNING / UVM_ERROR / UVM_FATAL messages

#### 1.3 `lib/urg_runner.py` (~150 lines)

URG invocation:
- `UrgRunner(urg_binary, timeout_seconds=300)` 
- `generate_report(vdb_dir, report_dir, cmd_template)` → `UrgResult` — runs urg subprocess; if `cmd_template` is empty/None, returns error result with message "URG not configured" instead of raising KeyError
- `parse_report(report_dir)` → coverage_gaps.json dict — calls existing `lib/urg_parser/` pipeline
- `build_coverage_db(gaps_json, report_id)` → coverage_db format compatible with `compute_diff()`

### WP-2: Manifest Schema Extension

#### 2.1 `schemas/project_manifest.schema.json` — add to `simulation` block:

```json
{
  "mode": { "type": "string", "enum": ["mock", "real"], "default": "mock" },
  "urg_cmd_template": { "type": "string" },
  "urg_binary": { "type": "string", "default": "urg" },
  "urg_timeout_seconds": { "type": "integer", "default": 300, "minimum": 30, "maximum": 1800 },
  "timeout_seconds": { "type": "integer", "default": 600, "minimum": 60, "maximum": 3600 },
  "results_root": { "type": "string", "default": "sim_results" },
  "vdb_dir_template": { "type": "string", "default": "sim_results/coverage/{test}_{seed}.vdb" }
}
```

#### 2.2 `lib/manifest.py` — add convenience properties:
- `sim_mode` → returns `simulation.mode` or `"mock"`
- `sim_results_root` → resolves `simulation.results_root` against `project_root`
- `sim_timeout` → returns `simulation.timeout_seconds` or `600`
- `sim_urg_timeout` → returns `simulation.urg_timeout_seconds` or `300`

#### 2.3 Both mock manifests — add explicit `mode: mock`

#### 2.4 Schema backward compatibility verification:
- Run `make validate` on both existing mock manifests — must pass without modification
- The `mode` field defaults to `"mock"`, so manifests without it remain valid

### WP-3: MCP Tool Upgrades (modify `sim_tools.py`)

#### 3.1 `sim_run_targeted_test` — mode branching:
- Read `simulation.mode` from manifest
- `mode == "mock"`: existing dry-run behavior (unchanged)
- `mode == "real"`: create `SimExecutor`, run compile + run, persist result, return real status
- On compile fail: skip run AND URG, return error envelope with compile log path for diagnosis
- On timeout: return `status: "timeout"` with log path for manual inspection
- Optional: after successful run, auto-invoke URG if `urg_cmd_template` is configured

**Note: `server.py` does NOT need modification.** The `mode` branching is handled entirely inside `sim_tools.py` by reading `manifest.sim_mode`. The `server.py` wrapper functions pass through to the tool functions unchanged.

#### 3.2 `sim_get_test_result` — resolution order:
1. Real mode: `sim_results/{test}_{seed}/sim_result.json` (persisted by run tool)
2. Real mode: parse `sim_results/{test}_{seed}/run.log` via `sim_log_parser`
3. Mock fallback: existing `sim_data/sim_logs/` behavior

#### 3.3 `sim_search_log` — resolution order:
1. Real mode: search `sim_results/{test}_{seed}/run.log`
2. Mock fallback: existing behavior

#### 3.4 `cov_get_coverage_diff` — extend:
- Add optional `before_path` / `after_path` parameters for explicit paths
- Real mode: auto-discover latest `coverage_db_after.json` from sim results
- Mock fallback: existing `sim_data/coverage_db_*.json` behavior

### WP-4: CLI Script Upgrade

`scripts/sim_runner.py` — add `--real` flag:
- Without `--real`: existing mock behavior
- With `--real`: use `SimExecutor` to run compile + run, output `sim_result.json`

### WP-5: Tests (~75 new tests)

| Test file | Count | Coverage |
|-----------|-------|----------|
| `tests/test_sim_executor.py` | ~30 | validation, dry-run, subprocess flow, timeout, log search |
| `tests/test_sim_log_parser.py` | ~15 | UVM pass/fail, message counting |
| `tests/test_urg_runner.py` | ~10 | command rendering, parse pipeline |
| `tests/test_sim_tools_real_mode.py` | ~20 | MCP tool tests with real mode |

Tests use `echo`/`false`/`sleep` as fake commands to test subprocess flow without VCS.

### WP-6: Server-side Verification (on remote server with VCS)

1. Provide real-mode manifest template: `mock_data/axi2ahb/project_manifest_real.yaml.example` (copy and set `mode: real` + `AXI2AHB_ROOT`)
2. Run compile + run via CLI: `python scripts/sim_runner.py --manifest ... --real`
3. Run URG and verify report generation
4. Run `cov_get_coverage_diff` with real coverage data
5. End-to-end MCP test via Claude Code

---

## Output Directory Structure

```
{project_root}/
└── sim_results/
    ├── {test}_{seed}/
    │   ├── compile.log
    │   ├── run.log
    │   ├── sim_result.json
    │   └── urg_report/          (if URG auto-run enabled)
    │       ├── session.xml, *.html
    │       ├── coverage_gaps.json
    │       └── coverage_index.json
    └── coverage/
        └── {test}_{seed}.vdb/
```

## Backward Compatibility

- All existing manifests without `mode` field → default `"mock"` → unchanged behavior
- All 414 existing tests pass without modification
- Mock `sim_data/` directory still works as before
- Real mode is strictly opt-in via manifest

## Files Summary

**New files (3):** `lib/sim_executor.py`, `lib/sim_log_parser.py`, `lib/urg_runner.py`

**Modified files (6):** `schemas/project_manifest.schema.json`, `lib/manifest.py`, `dv_mcp/dv_context_server/tools/sim_tools.py`, `scripts/sim_runner.py`, `mock_data/axi2ahb/project_manifest.yaml`, `mock_data/dma_subsystem/project_manifest.yaml`

Note: `server.py` does NOT need modification — mode branching is internal to `sim_tools.py`.

**New template (1):** `mock_data/axi2ahb/project_manifest_real.yaml.example` — real-mode manifest template for remote server use

**New test files (4):** `tests/test_sim_executor.py`, `tests/test_sim_log_parser.py`, `tests/test_urg_runner.py`, `tests/test_sim_tools_real_mode.py`

## Verification

1. `make lint && make typecheck` — ruff 0, mypy 0
2. `make validate` — schema validation passes (both mock manifests, with and without `mode` field)
3. `make test` — all existing + new tests pass
4. `make smoke-server` — MCP server starts with all tools
5. On server with VCS: real compile + run + URG + diff end-to-end

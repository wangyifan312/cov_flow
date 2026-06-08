# Phase 5b Coding Agent Prompt: WP-3 MCP Tool Upgrades

> **执行顺序**: WP-1 → WP-2 → **WP-3** → WP-4 → WP-5  
> **本文档**: WP-3（MCP Tool Upgrades）  
> **前置依赖**: WP-1 + WP-2 完成  
> **后续**: WP-3 完成后回来 review，再执行 WP-4

---

## Objective

升级 4 个 simulation MCP tools，支持 `mode: "real"` 分支调用 WP-1 创建的 `SimExecutor` / `SimLogParser` / `UrgRunner`。Mock 模式（默认）保持不变。

**注意**: `server.py` 不需要修改。模式切换逻辑完全在 `sim_tools.py` 内部处理。

## File to Modify (1 file)

| File | Action | Purpose |
|------|--------|---------|
| `dv_mcp/dv_context_server/tools/sim_tools.py` | Modify | 4 个工具新增 real mode 分支 |

---

## Task 1: `sim_run_targeted_test` — 新增 real mode 分支

### 修改逻辑

在现有 `confirm: true` 检查之后、mock result 构建之前，插入模式分支：

```python
# === 现有代码：policy check + confirm check ===
# ... (保持不变)

# === 新增：mode branching ===
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
    # ... build evidence + envelope ...

else:
    # === 现有 mock 逻辑（完全不变） ===
    result = { ... }  # 现有代码
```

### `_sim_result_to_dict` 辅助函数

```python
def _sim_result_to_dict(sr: SimResult, test: str, seed: int) -> dict:
    """Convert SimResult dataclass to MCP result dict."""
    def _step_dict(step):
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
```

---

## Task 2: `sim_get_test_result` — real mode 优先查 sim_results

### 修改逻辑

在现有 `sim_data_dir` 查找逻辑**之前**，插入 real mode 分支：

```python
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
            "log_summary": summary.test_pass_line or f"UVM: {summary.uvm_fatal} fatal, {summary.uvm_error} error",
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

# === 现有 mock 逻辑（完全不变）===
```

---

## Task 3: `sim_search_log` — real mode 优先查 sim_results

### 修改逻辑

在现有 `log_path` 计算**之前**，插入 real mode 分支：

```python
sim_mode = manifest.sim_mode

if sim_mode == "real":
    from lib.sim_executor import SimExecutor

    executor = SimExecutor(
        project_root=manifest.project_root,
        results_root=manifest.sim_results_root,
    )

    search_result = executor.search_log(test, seed, keyword, step="run")
    if search_result is not None:
        log_path = str(executor.get_log_path(test, seed, "run"))
        result = {
            "test": test,
            "seed": seed,
            "keyword": keyword,
            "matches": search_result["matches"],
            "total_matches": search_result["total_matches"],
            "log_path": log_path,
        }
        evidence = [simulation_evidence(test, seed, log_path,
                                        f"Log search for '{keyword}': {search_result['total_matches']} matches")]
        was_truncated = search_result["total_matches"] > len(search_result["matches"])
        audit = audit_record(tool_name, project, args)
        return envelope(tool_name, project, result, evidence,
                        truncated=was_truncated, audit=audit)

    # Fall through to mock behavior

# === 现有 mock 逻辑（完全不变）===
```

---

## Task 4: `cov_get_coverage_diff` — 支持 real mode 自动发现

### 修改逻辑

在现有 `before_path` / `after_path` 计算**之前**，插入 real mode 分支：

```python
sim_mode = manifest.sim_mode

if sim_mode == "real":
    # Auto-discover latest coverage_db files from sim_results
    results_root = manifest.sim_results_root
    if results_root.is_dir():
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
            before_path = None  # No before data
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

        # Both paths found — fall through to diff computation
    else:
        return error_envelope(tool_name, project,
                              f"sim_results directory not found: {results_root}")

# === 现有 mock 逻辑（完全不变，或继续用上面找到的 real paths）===
```

---

## Verification

```bash
# 1. Import check — 所有工具可导入
.venv/bin/python -c "
from dv_mcp.dv_context_server.tools.sim_tools import (
    sim_run_targeted_test, sim_get_test_result,
    sim_search_log, cov_get_coverage_diff,
)
print('All sim tools import OK')
"

# 2. Mock mode 不变 — 现有 contract tests 通过
.venv/bin/python -m pytest tests/test_tool_contracts.py -v -k "SimTools"

# 3. Mock mode 手动测试
.venv/bin/python -c "
from dv_mcp.dv_context_server.services.project_loader import clear_cache
from dv_mcp.dv_context_server.tools.sim_tools import sim_run_targeted_test
clear_cache()

# Mock mode: confirm=false → 要求确认
resp = sim_run_targeted_test('mock_data/axi2ahb/project_manifest.yaml', 'test1', 42, confirm=False)
print('confirm=false:', resp['ok'], resp['result'].get('message', ''))

# Mock mode: confirm=true → 返回 mock 结果
resp = sim_run_targeted_test('mock_data/axi2ahb/project_manifest.yaml', 'test1', 42, confirm=True)
print('confirm=true (mock):', resp['ok'], resp['result'].get('dry_run'))
"

# 4. Real mode validation（不需要 VCS — 只验证 test name 拒绝）
.venv/bin/python -c "
from dv_mcp.dv_context_server.services.project_loader import clear_cache
from dv_mcp.dv_context_server.tools.sim_tools import sim_run_targeted_test
clear_cache()

# 需要一个 mode:real 的 manifest 来测试
# 如果有 project_manifest_real.yaml.example:
resp = sim_run_targeted_test(
    'mock_data/axi2ahb/project_manifest_real.yaml.example',
    '../etc/passwd', 42, confirm=True,
)
print('Path traversal rejected:', not resp['ok'], resp.get('error', ''))
"

# 5. Lint + typecheck
.venv/bin/ruff check dv_mcp/dv_context_server/tools/sim_tools.py
.venv/bin/mypy dv_mcp/dv_context_server/tools/sim_tools.py

# 6. 现有测试不破坏
.venv/bin/python -m pytest --tb=short -q

# 7. Smoke server
make smoke-server
```

---

## Quality Checklist

- [ ] `sim_run_targeted_test` mock 模式行为完全不变（dry_run=True）
- [ ] `sim_run_targeted_test` real 模式调用 `SimExecutor.run_pipeline`
- [ ] `sim_get_test_result` real 模式优先查 `sim_result.json`，其次解析 `run.log`
- [ ] `sim_search_log` real 模式调用 `SimExecutor.search_log`
- [ ] `cov_get_coverage_diff` real 模式自动发现最新 URG 报告
- [ ] Real 模式下 `validate_test_name` 拒绝路径遍历
- [ ] `_sim_result_to_dict` 辅助函数正确序列化 `SimResult`
- [ ] `server.py` **未修改**
- [ ] `make smoke-server` 仍显示 13 tools
- [ ] 现有 contract tests 通过
- [ ] ruff 0 issues
- [ ] mypy 0 errors
- [ ] 现有 413+ 测试全部通过

# Phase 5b Coding Agent Prompt: WP-5 Tests

> **执行顺序**: WP-1 → WP-2 → WP-3 → WP-4 → **WP-5**  
> **本文档**: WP-5（Tests）  
> **前置依赖**: WP-1 + WP-2 + WP-3 + WP-4 完成  
> **后续**: WP-5 完成后执行完整 `make accept`

---

## Objective

为 Phase 5b 所有新增代码编写测试。使用 `echo` / `false` / `sleep` 等 fake command 测试 subprocess 流程，**不依赖 VCS**。

## Files to Create (4 new test files)

| File | Count | Coverage |
|------|-------|----------|
| `tests/test_sim_executor.py` | ~30 | SimExecutor 全部方法 |
| `tests/test_sim_log_parser.py` | ~15 | VCS/UVM 日志解析 |
| `tests/test_urg_runner.py` | ~10 | URG 调用和解析 |
| `tests/test_sim_tools_real_mode.py` | ~20 | MCP 工具 real mode 分支 |

**不要修改任何现有测试文件。** 纯新增。

---

## File 1: `tests/test_sim_executor.py` (~30 tests)

### Setup

```python
import tempfile
from pathlib import Path
import pytest
from lib.sim_executor import SimExecutor, SimStepResult, SimResult

@pytest.fixture
def tmp_project(tmp_path: Path) -> tuple[SimExecutor, Path]:
    """Create a temp project with results dir."""
    project_root = tmp_path / "project"
    project_root.mkdir()
    results_root = tmp_path / "project" / "sim_results"
    executor = SimExecutor(
        project_root=project_root,
        results_root=results_root,
        timeout_seconds=10,
        urg_timeout_seconds=5,
    )
    return executor, project_root
```

### Test Cases

```python
class TestValidateTestName:
    def test_valid_simple(self, tmp_project): ...         # "test1" → OK
    def test_valid_with_dots(self, tmp_project): ...       # "my.test.v2" → OK
    def test_valid_with_dash(self, tmp_project): ...       # "wrap8-targeted" → OK
    def test_rejects_path_traversal_dotdot(self, tmp_project): ...  # "../etc" → ValueError
    def test_rejects_path_traversal_slash(self, tmp_project): ...   # "test/name" → ValueError
    def test_rejects_empty(self, tmp_project): ...         # "" → ValueError
    def test_rejects_space(self, tmp_project): ...         # "test name" → ValueError
    def test_rejects_starts_with_dash(self, tmp_project): ...  # "-test" → ValueError
    def test_rejects_starts_with_dot(self, tmp_project): ...  # ".hidden" → ValueError

class TestValidateSeed:
    def test_valid_zero(self, tmp_project): ...            # 0 → OK
    def test_valid_positive(self, tmp_project): ...        # 42 → OK
    def test_rejects_negative(self, tmp_project): ...      # -1 → ValueError

class TestGetResultsDir:
    def test_creates_directory(self, tmp_project): ...     # 返回 Path 且 exists
    def test_idempotent(self, tmp_project): ...            # 调用两次不报错
    def test_path_format(self, tmp_project): ...           # "test1_42" 在路径中

class TestGetLogPath:
    def test_compile_log(self, tmp_project): ...           # compile.log
    def test_run_log(self, tmp_project): ...               # run.log

class TestExecuteStep:
    def test_echo_success(self, tmp_project): ...
        # command = "echo hello world"
        # 期望: status="pass", return_code=0, log 包含 "hello world"
    
    def test_false_failure(self, tmp_project): ...
        # command = "false" (Unix false 命令，exit 1)
        # 期望: status="fail", return_code=1
    
    def test_timeout(self, tmp_project): ...
        # command = "sleep 60" (executor timeout=10s)
        # 期望: status="timeout", return_code=-1
    
    def test_stdout_captured(self, tmp_project): ...
        # command = "echo line1 && echo line2"
        # 期望: log 包含 "line1" 和 "line2"
    
    def test_stderr_captured(self, tmp_project): ...
        # command = "echo error >&2"
        # 期望: log 包含 "error"
    
    def test_cwd_is_project_root(self, tmp_project): ...
        # command = "pwd"
        # 期望: log 内容等于 str(project_root)

class TestSearchLog:
    def test_keyword_found(self, tmp_project): ...
        # 先写一个 log 文件，然后 search
        # 期望: matches 非空，total_matches > 0
    
    def test_keyword_not_found(self, tmp_project): ...
        # 期望: matches 为空，total_matches == 0
    
    def test_case_insensitive(self, tmp_project): ...
        # log 包含 "ERROR"，search "error"
        # 期望: 找到
    
    def test_max_20_matches(self, tmp_project): ...
        # log 有 50 行匹配
        # 期望: len(matches) == 20, total_matches == 50
    
    def test_returns_total_matches(self, tmp_project): ...
        # 期望: result 包含 "total_matches" key

class TestRunPipeline:
    def test_compile_pass_run_pass(self, tmp_project): ...
        # compile_cmd = "echo compile OK"
        # run_cmd = "echo run OK"
        # 期望: compile.status="pass", run.status="pass"
    
    def test_compile_fail_skips_run(self, tmp_project): ...
        # compile_cmd = "false"
        # run_cmd = "echo should not run"
        # 期望: compile.status="fail", run is None
    
    def test_compile_fail_skips_urg(self, tmp_project): ...
        # compile_cmd = "false"
        # urg_cmd = "echo should not urg"
        # 期望: compile.status="fail", urg is None
    
    def test_run_fail_skips_urg(self, tmp_project): ...
        # compile_cmd = "echo ok"
        # run_cmd = "false"
        # urg_cmd = "echo should not urg"
        # 期望: run.status="fail", urg is None
    
    def test_with_urg(self, tmp_project): ...
        # compile_cmd = "echo ok"
        # run_cmd = "echo ok"
        # urg_cmd = "echo urg done"
        # 期望: 三个 step 都 pass

class TestSaveLoadResult:
    def test_roundtrip(self, tmp_project): ...
        # save 后 load，比较字段一致
    
    def test_load_nonexistent(self, tmp_project): ...
        # 期望: 返回 None

class TestReadLog:
    def test_existing_log(self, tmp_project): ...
    def test_nonexistent_log(self, tmp_project): ...
        # 期望: 返回 None
```

---

## File 2: `tests/test_sim_log_parser.py` (~15 tests)

```python
from lib.sim_log_parser import parse_vcs_log, detect_pass_fail, SimLogSummary

class TestDetectPassFail:
    def test_explicit_passed(self): ...
        # "Test PASSED" → "pass"
    
    def test_explicit_failed(self): ...
        # "Test FAILED" → "fail"
    
    def test_uvm_fatal_is_fail(self): ...
        # log 包含 "UVM_FATAL" 但没有 explicit PASSED/FAILED → "fail"
    
    def test_uvm_error_is_fail(self): ...
        # log 包含 "UVM_ERROR" 但没有 FATAL → "fail"
    
    def test_dollar_finish_is_pass(self): ...
        # log 包含 "$finish" 但没有 UVM messages → "pass"
    
    def test_empty_log_is_unknown(self): ...
        # 空字符串 → "unknown"
    
    def test_priority_explicit_over_fatal(self): ...
        # "Test PASSED" + "UVM_FATAL" → "pass"（explicit 优先级更高）

class TestParseVcsLog:
    def test_count_uvm_info(self): ...
        # 3 行 UVM_INFO → uvm_info == 3
    
    def test_count_uvm_warning(self): ...
    def test_count_uvm_error(self): ...
    def test_count_uvm_fatal(self): ...
    
    def test_bracket_format(self): ...
        # "[UVM_INFO]" 格式也能计数
    
    def test_mixed_format(self): ...
        # 同时有 "UVM_INFO" 和 "[UVM_INFO]" 格式
    
    def test_status_set_correctly(self): ...
        # parse_vcs_log 内部调用 detect_pass_fail 设置 status
    
    def test_test_pass_line_extracted(self): ...
        # 包含 "Test PASSED" 的行被提取到 test_pass_line
```

---

## File 3: `tests/test_urg_runner.py` (~10 tests)

```python
from pathlib import Path
import pytest
from lib.urg_runner import UrgRunner, UrgResult

class TestGenerateReport:
    def test_not_configured_when_no_template(self): ...
        # cmd_template=None → UrgResult(status="not_configured")
    
    def test_not_configured_when_empty_template(self): ...
        # cmd_template="" → UrgResult(status="not_configured")
    
    def test_echo_success(self, tmp_path): ...
        # cmd_template = "echo {vdb_dir} {report_dir}"
        # 期望: status="ok"（注意：echo 不产生真实 HTML，parse 可能失败）
    
    def test_false_returns_error(self, tmp_path): ...
        # cmd_template = "false"
        # 期望: status="error"
    
    def test_timeout(self, tmp_path): ...
        # UrgRunner(timeout_seconds=1)
        # cmd_template = "sleep 60"
        # 期望: status="timeout"

class TestBuildCoverageDb:
    def test_basic_conversion(self): ...
        # gaps = {"gaps": [{"gap_id": "GAP_0001", ...}]}
        # result = build_coverage_db(gaps, "test_report")
        # 期望: result["report_id"] == "test_report"
        # 期望: result["gaps"] 非空
    
    def test_empty_gaps(self): ...
        # gaps = {"gaps": []}
        # 期望: result["gaps"] == [], result["total_coverpoints"] == 0
    
    def test_report_id_included(self): ...
```

---

## File 4: `tests/test_sim_tools_real_mode.py` (~20 tests)

### Setup

```python
import os
import pytest
from pathlib import Path
from dv_mcp.dv_context_server.services.project_loader import clear_cache
from dv_mcp.dv_context_server.tools.sim_tools import (
    sim_run_targeted_test, sim_get_test_result,
    sim_search_log, cov_get_coverage_diff,
)

@pytest.fixture(autouse=True)
def _clear():
    clear_cache()
    yield
    clear_cache()

@pytest.fixture
def real_manifest(tmp_path: Path) -> Path:
    """Create a temp manifest with mode: real and echo-based commands."""
    manifest_path = tmp_path / "project_manifest.yaml"
    manifest_path.write_text(f"""
project: test_real
project_root: {tmp_path}

simulation:
  mode: real
  compile_cmd_template: "echo compile {{test}} {{seed}}"
  run_cmd_template: "echo run {{test}} {{seed}} && echo Test PASSED"
  urg_cmd_template: "echo urg {{vdb_dir}} {{report_dir}}"
  results_root: sim_results
  timeout_seconds: 10

policy:
  allow_running_simulation: true
""")
    # Create sim_results dir
    (tmp_path / "sim_results").mkdir()
    return manifest_path
```

### Test Cases

```python
class TestSimRunTargetedTestRealMode:
    def test_compile_and_run_pass(self, real_manifest): ...
        # confirm=True → run pipeline with echo commands
        # 期望: ok=True, result.run.status="pass", dry_run=False
    
    def test_compile_fail_skips_run(self, real_manifest_with_fail_compile): ...
        # compile_cmd = "false"
        # 期望: compile.status="fail", run is None
    
    def test_test_name_validation(self, real_manifest): ...
        # test="../../../etc/passwd"
        # 期望: ok=False, error 包含 "Invalid"
    
    def test_seed_validation(self, real_manifest): ...
        # seed=-1
        # 期望: ok=False
    
    def test_confirm_required(self, real_manifest): ...
        # confirm=False
        # 期望: ok=True, result.message 包含 "confirm"
    
    def test_policy_check(self, real_manifest_no_policy): ...
        # allow_running_simulation: false
        # 期望: ok=False
    
    def test_envelope_format(self, real_manifest): ...
        # 验证 ok, tool, project, result, evidence, truncated, next_actions 都存在

class TestSimGetTestResultRealMode:
    def test_load_persisted_result(self, real_manifest): ...
        # 先 run，再 get_result
        # 期望: 返回持久化的 SimResult
    
    def test_parse_log_fallback(self, real_manifest): ...
        # 手动创建 run.log（无 sim_result.json）
        # 期望: 解析 log 返回 status
    
    def test_no_results_found(self, real_manifest): ...
        # 没有 run 过
        # 期望: 适当的 not_found 响应

class TestSimSearchLogRealMode:
    def test_search_after_run(self, real_manifest): ...
        # 先 run（echo "Test PASSED"），再 search "PASSED"
        # 期望: matches 包含 "Test PASSED"
    
    def test_search_returns_total_matches(self, real_manifest): ...
        # 期望: result 包含 "total_matches" key
    
    def test_search_no_results(self, real_manifest): ...
        # search 不存在的 keyword
        # 期望: matches 为空

class TestCovGetCoverageDiffRealMode:
    def test_no_urg_reports(self, real_manifest): ...
        # sim_results 为空
        # 期望: ok=False, error 包含 "No URG reports"
```

---

## Verification

```bash
# 1. 所有新测试通过
.venv/bin/python -m pytest tests/test_sim_executor.py -v
.venv/bin/python -m pytest tests/test_sim_log_parser.py -v
.venv/bin/python -m pytest tests/test_urg_runner.py -v
.venv/bin/python -m pytest tests/test_sim_tools_real_mode.py -v

# 2. 完整测试套件
.venv/bin/python -m pytest --tb=short -q

# 3. Lint + typecheck
.venv/bin/ruff check tests/test_sim_executor.py tests/test_sim_log_parser.py \
    tests/test_urg_runner.py tests/test_sim_tools_real_mode.py
.venv/bin/mypy tests/test_sim_executor.py tests/test_sim_log_parser.py \
    tests/test_urg_runner.py tests/test_sim_tools_real_mode.py

# 4. 完整 acceptance
make accept

# 5. 无 VCS 依赖检查 — 所有测试使用 echo/false/sleep
grep -rn "vcs\|urg " tests/test_sim_executor.py tests/test_sim_log_parser.py \
    tests/test_urg_runner.py tests/test_sim_tools_real_mode.py
# 期望: 无匹配（除了注释和字符串模板中的 "urg"）
```

---

## Quality Checklist

- [ ] `test_sim_executor.py` ~30 tests，覆盖 validate / execute / search / pipeline / save-load
- [ ] `test_sim_log_parser.py` ~15 tests，覆盖 detect_pass_fail 优先级 + UVM 计数
- [ ] `test_urg_runner.py` ~10 tests，覆盖 not_configured / echo / error / timeout
- [ ] `test_sim_tools_real_mode.py` ~20 tests，覆盖 4 个 MCP 工具的 real mode 分支
- [ ] 所有测试使用 `echo`/`false`/`sleep`，不依赖 VCS
- [ ] `tmp_path` fixture 用于隔离文件系统
- [ ] 测试之间无依赖（每个测试独立）
- [ ] ruff 0 issues
- [ ] mypy 0 errors
- [ ] `make accept` 全部通过
- [ ] 新增测试总数 ~75
- [ ] 无现有测试被修改

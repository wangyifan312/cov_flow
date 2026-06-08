# Phase 5b Coding Agent Prompt: WP-1 Foundation Library

> **执行顺序**: WP-1 → WP-2 → WP-3 → WP-4 → WP-5  
> **本文档**: WP-1（Foundation Library）  
> **前置依赖**: 无  
> **后续**: WP-1 完成后回来 review，再执行 WP-2

---

## Objective

为 Phase 5b 创建 3 个基础库文件，实现真实的 VCS 仿真执行、日志解析和 URG 覆盖率报告生成。这些库文件是后续 WP-2/3/4 的基础。

**当前状态**: 4 个 simulation MCP tools 都是 mock/dry-run，返回硬编码假数据。  
**目标**: 创建 `lib/` 层的执行逻辑，MCP 工具层在 WP-3 接入。

## Files to Create (3 new files)

| File | Lines | Purpose |
|------|-------|---------|
| `lib/sim_executor.py` | ~250 | Subprocess 管理、日志 I/O、结果持久化 |
| `lib/sim_log_parser.py` | ~120 | VCS/UVM 日志解析、pass/fail 检测 |
| `lib/urg_runner.py` | ~150 | URG 调用、报告解析、coverage_db 构建 |

**不要修改任何现有文件。** 纯新增。

---

## Task 1: `lib/sim_executor.py`

### 数据结构

```python
@dataclass
class SimStepResult:
    step: str              # "compile" | "run" | "urg"
    status: str            # "pass" | "fail" | "timeout" | "error"
    return_code: int       # subprocess return code, -1 for timeout
    log_path: str          # absolute path to log file
    duration_seconds: float
    message: str           # human-readable summary
    stdout_tail: str       # last 50 lines of stdout (for error diagnosis)

@dataclass
class SimResult:
    test: str
    seed: int
    compile: SimStepResult | None
    run: SimStepResult | None
    urg: SimStepResult | None
    started_at: str        # ISO timestamp
    finished_at: str       # ISO timestamp
```

### SimExecutor 类

```python
class SimExecutor:
    """Real VCS simulation executor with security boundaries."""
    
    # Test name regex — alphanumeric + underscore/dot/dash only
    TEST_NAME_RE = re.compile(r"^[a-zA-Z0-9_][a-zA-Z0-9_.\-]*$")
    
    def __init__(
        self,
        project_root: Path,
        results_root: Path,
        timeout_seconds: int = 600,
        urg_timeout_seconds: int = 300,
    ) -> None: ...
    
    # --- Validation ---
    def validate_test_name(self, test: str) -> None:
        """Raise ValueError if test name is invalid.
        
        Checks:
        1. regex match
        2. ".." not in test (path traversal)
        3. "/" not in test (path traversal)
        """
    
    def validate_seed(self, seed: int) -> None:
        """Raise ValueError if seed is negative."""
    
    # --- Directory management ---
    def get_results_dir(self, test: str, seed: int) -> Path:
        """Return {results_root}/{test}_{seed}/ — creates with parents=True."""
    
    def get_log_path(self, test: str, seed: int, step: str) -> Path:
        """Return {results_dir}/{step}.log"""
    
    # --- Execution ---
    def compile(self, command: str, test: str, seed: int) -> SimStepResult:
        """Run compile command, capture log to compile.log."""
    
    def run_simulation(self, command: str, test: str, seed: int) -> SimStepResult:
        """Run simulation command, capture log to run.log."""
    
    def run_urg(self, command: str, test: str, seed: int) -> SimStepResult:
        """Run URG command with urg_timeout, capture log to urg.log."""
    
    def _execute_step(
        self, step: str, command: str, log_path: Path, timeout: int,
    ) -> SimStepResult:
        """Core subprocess logic.
        
        Uses shlex.split(command) + shell=False.
        subprocess.run(cmd_args, capture_output=True, text=True, 
                       timeout=timeout, cwd=str(self._project_root))
        
        On timeout: returns status="timeout", return_code=-1
        On non-zero exit: returns status="fail"
        On zero exit: returns status="pass"
        
        Always writes stdout to log_path.
        Always captures last 50 lines as stdout_tail.
        """
    
    # --- Result persistence ---
    def save_result(self, test: str, seed: int, result: SimResult) -> Path:
        """Write sim_result.json to results dir. Return path."""
    
    def load_result(self, test: str, seed: int) -> SimResult | None:
        """Read sim_result.json. Return None if not found."""
    
    # --- Log I/O ---
    def read_log(self, test: str, seed: int, step: str) -> str | None:
        """Read full log content. Return None if not found."""
    
    def search_log(
        self, test: str, seed: int, keyword: str, step: str = "run",
    ) -> dict:
        """Bounded keyword search in log.
        
        Returns: {"matches": [...], "total_matches": N, "returned": M}
        Max 20 matches returned.
        """
    
    # --- Full pipeline ---
    def run_pipeline(
        self,
        test: str,
        seed: int,
        compile_cmd: str,
        run_cmd: str,
        urg_cmd: str | None = None,
    ) -> SimResult:
        """Execute compile → run → (optional) urg pipeline.
        
        - On compile fail: skip run and urg
        - On run fail: skip urg
        - On run success + urg_cmd provided: run urg
        - Returns SimResult with all step results
        """
```

### 关键实现细节

1. `shlex.split(command)` 拆分命令，`shell=False` 执行
2. `subprocess.run` 的 `cwd` 固定为 `str(self._project_root)`
3. 超时处理：`except subprocess.TimeoutExpired` → `SimStepResult(status="timeout", return_code=-1)`
4. 日志写入：`log_path.write_text(result.stdout + result.stderr, encoding="utf-8")`
5. `stdout_tail`：取最后 50 行，用于错误诊断
6. `save_result` / `load_result`：用 `dataclasses.asdict` + `json` 序列化
7. `search_log`：大小写不敏感匹配，返回 `total_matches` 让调用方知道是否有更多结果

---

## Task 2: `lib/sim_log_parser.py`

### 数据结构

```python
@dataclass
class SimLogSummary:
    status: str           # "pass" | "fail" | "unknown"
    uvm_info: int         # count of UVM_INFO messages
    uvm_warning: int      # count of UVM_WARNING messages
    uvm_error: int        # count of UVM_ERROR messages
    uvm_fatal: int        # count of UVM_FATAL messages
    finish_detected: bool # whether $finish was detected
    test_pass_line: str   # the line containing PASSED/FAILED, or ""
    duration_hint: str    # "simulation time" line if found, or ""
```

### 函数

```python
def parse_vcs_log(log_content: str) -> SimLogSummary:
    """Parse a VCS/UVM simulation log.
    
    Counts UVM message types by regex:
    - UVM_INFO:    r'UVM_INFO'     or r'\[UVM_INFO\]'
    - UVM_WARNING: r'UVM_WARNING'  or r'\[UVM_WARNING\]'
    - UVM_ERROR:   r'UVM_ERROR'    or r'\[UVM_ERROR\]'
    - UVM_FATAL:   r'UVM_FATAL'    or r'\[UVM_FATAL\]'
    """

def detect_pass_fail(log_content: str) -> str:
    """Determine pass/fail from log content.
    
    Priority (highest first):
    1. Explicit "Test PASSED" or "Test FAILED" → "pass" / "fail"
    2. UVM_FATAL present → "fail"
    3. UVM_ERROR present → "fail"
    4. "$finish" present → "pass" (VCS normal exit)
    5. Otherwise → "unknown"
    """
```

### 关键实现细节

1. 用 `re.findall` 计数，不逐行遍历（日志可能很大）
2. `detect_pass_fail` 是独立函数，可被 `sim_tools.py` 直接调用
3. `parse_vcs_log` 内部调用 `detect_pass_fail` 设置 `status`
4. 正则匹配要兼容两种格式：`UVM_INFO` 和 `[UVM_INFO]`

---

## Task 3: `lib/urg_runner.py`

### 数据结构

```python
@dataclass
class UrgResult:
    status: str           # "ok" | "error" | "not_configured" | "timeout"
    report_dir: str       # path to generated report
    message: str          # human-readable description
    gaps_count: int       # number of gaps parsed (0 if error)
```

### UrgRunner 类

```python
class UrgRunner:
    """URG report generator and parser."""
    
    def __init__(
        self,
        urg_binary: str = "urg",
        timeout_seconds: int = 300,
    ) -> None: ...
    
    def generate_report(
        self,
        vdb_dir: str | Path,
        report_dir: str | Path,
        cmd_template: str | None = None,
    ) -> UrgResult:
        """Run urg to generate HTML coverage report.
        
        If cmd_template is None or empty:
            return UrgResult(status="not_configured", ...)
        
        Otherwise:
            cmd = cmd_template.format(vdb_dir=str(vdb_dir), report_dir=str(report_dir))
            subprocess.run(shlex.split(cmd), shell=False, timeout=self._timeout_seconds)
        
        On success: parse the report and return UrgResult(status="ok")
        On failure: return UrgResult(status="error")
        On timeout: return UrgResult(status="timeout")
        """
    
    def parse_report(self, report_dir: str | Path) -> dict:
        """Parse URG HTML report using existing lib/urg_parser pipeline.
        
        Calls:
            from lib.urg_parser.index_builder import build_indexes
            coverage_index, coverage_gaps = build_indexes(report_dir)
        
        Returns the coverage_gaps dict (compatible with compute_diff).
        
        If parsing fails, returns {"gaps": [], "error": str(e)}
        """
    
    def build_coverage_db(
        self, gaps: dict, report_id: str = "urg_report",
    ) -> dict:
        """Convert coverage_gaps dict to coverage_db format.
        
        The coverage_db format is what compute_diff() expects:
        {
            "report_id": report_id,
            "total_coverpoints": N,
            "covered": N,
            "gaps": [
                {"gap_id": "...", "hit_count": N, "goal": N, ...},
                ...
            ]
        }
        """
```

### 关键实现细节

1. `generate_report` 中 `cmd_template` 为 None/空时返回 `not_configured`，**不抛异常**
2. `parse_report` 调用已有的 `lib/urg_parser/` 管道（Phase 3 实现），不重复造轮子
3. `build_coverage_db` 输出格式与现有 `mock_data/dma_subsystem/sim_data/coverage_db_after.json` 兼容
4. 先读一下 `mock_data/dma_subsystem/sim_data/coverage_db_after.json` 了解目标格式

---

## Verification

完成所有 3 个文件后，依次执行：

```bash
# 1. 文件存在性
ls -la lib/sim_executor.py lib/sim_log_parser.py lib/urg_runner.py

# 2. 导入检查（不依赖 VCS，纯 import 即可）
.venv/bin/python -c "from lib.sim_executor import SimExecutor, SimStepResult, SimResult; print('sim_executor OK')"
.venv/bin/python -c "from lib.sim_log_parser import parse_vcs_log, detect_pass_fail, SimLogSummary; print('sim_log_parser OK')"
.venv/bin/python -c "from lib.urg_runner import UrgRunner, UrgResult; print('urg_runner OK')"

# 3. 安全验证（不需要 VCS）
.venv/bin/python -c "
from lib.sim_executor import SimExecutor
from pathlib import Path
e = SimExecutor(Path('/tmp'), Path('/tmp/sim_results'))

# Valid names
e.validate_test_name('wrap8_targeted_test')
e.validate_test_name('my.test-name_v2')
print('Valid names: OK')

# Invalid names
for bad in ['../etc/passwd', 'test/../../', '../../../', 'test name', '']:
    try:
        e.validate_test_name(bad)
        print(f'FAIL: should have rejected: {bad!r}')
    except ValueError as ex:
        print(f'Rejected {bad!r}: {ex}')

# Seed validation
e.validate_seed(0)
e.validate_seed(42)
try:
    e.validate_seed(-1)
    print('FAIL: should have rejected negative seed')
except ValueError:
    print('Negative seed rejected: OK')
"

# 4. Lint
.venv/bin/ruff check lib/sim_executor.py lib/sim_log_parser.py lib/urg_runner.py

# 5. Type check
.venv/bin/mypy lib/sim_executor.py lib/sim_log_parser.py lib/urg_runner.py

# 6. 现有测试不破坏
.venv/bin/python -m pytest --tb=short -q

# 7. 通用性检查 — lib 文件不应包含项目名
grep -n "axi\|ahb\|dma" lib/sim_executor.py lib/sim_log_parser.py lib/urg_runner.py
# 期望: 无匹配
```

---

## Quality Checklist

- [ ] `SimExecutor.validate_test_name` 拒绝 `..`、`/`、空格、空字符串
- [ ] `SimExecutor.validate_seed` 拒绝负数
- [ ] `SimExecutor._execute_step` 使用 `shlex.split` + `shell=False`
- [ ] `SimExecutor._execute_step` 设置 `cwd=str(self._project_root)`
- [ ] `SimExecutor.get_results_dir` 使用 `mkdir(parents=True, exist_ok=True)`
- [ ] `SimExecutor.search_log` 返回 `total_matches` 字段
- [ ] `SimExecutor.run_pipeline` compile 失败时跳过 run 和 urg
- [ ] `SimLogSummary` 包含所有 UVM 消息计数
- [ ] `detect_pass_fail` 优先级正确：explicit > FATAL > ERROR > $finish > unknown
- [ ] `UrgRunner.generate_report` cmd_template 为 None 时返回 `not_configured`
- [ ] `UrgRunner.parse_report` 调用已有的 `lib/urg_parser/` 管道
- [ ] `build_coverage_db` 输出格式与 `mock_data/dma_subsystem/sim_data/coverage_db_after.json` 兼容
- [ ] 3 个文件 ruff 0 issues
- [ ] 3 个文件 mypy 0 errors
- [ ] 现有 413+ 测试全部通过
- [ ] 无硬编码项目名（axi2ahb / dma / ahb）

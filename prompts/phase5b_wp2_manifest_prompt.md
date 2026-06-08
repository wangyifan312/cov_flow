# Phase 5b Coding Agent Prompt: WP-2 Manifest Schema Extension

> **执行顺序**: WP-1 → **WP-2** → WP-3 → WP-4 → WP-5  
> **本文档**: WP-2（Manifest Schema Extension）  
> **前置依赖**: WP-1 完成  
> **后续**: WP-2 完成后回来 review，再执行 WP-3

---

## Objective

扩展 project manifest schema，新增 `simulation.mode` 字段（`mock` / `real`）和相关配置项。为 WP-3 的 MCP 工具模式切换提供 manifest 层支持。

## Files to Modify (4 files) + New Template (1 file)

| File | Action | Purpose |
|------|--------|---------|
| `schemas/project_manifest.schema.json` | Modify | 新增 `simulation.mode` 及相关字段 |
| `lib/manifest.py` | Modify | 新增 4 个 convenience properties |
| `mock_data/axi2ahb/project_manifest.yaml` | Modify | 添加显式 `mode: mock` |
| `mock_data/dma_subsystem/project_manifest.yaml` | Modify | 添加显式 `mode: mock` |
| `mock_data/axi2ahb/project_manifest_real.yaml.example` | **New** | Real-mode 模板供远程服务器使用 |

---

## Task 1: `schemas/project_manifest.schema.json`

在 `simulation` 块的 properties 中新增以下字段：

```json
"mode": {
    "type": "string",
    "enum": ["mock", "real"],
    "default": "mock",
    "description": "Simulation execution mode. 'mock' returns fake data (safe default). 'real' executes VCS subprocess."
},
"urg_cmd_template": {
    "type": "string",
    "description": "URG report generation command template. Placeholders: {vdb_dir}, {report_dir}"
},
"urg_binary": {
    "type": "string",
    "default": "urg",
    "description": "Path to urg binary"
},
"urg_timeout_seconds": {
    "type": "integer",
    "default": 300,
    "minimum": 30,
    "maximum": 1800,
    "description": "Timeout for URG report generation in seconds"
},
"timeout_seconds": {
    "type": "integer",
    "default": 600,
    "minimum": 60,
    "maximum": 3600,
    "description": "Timeout for compile/run simulation in seconds"
},
"results_root": {
    "type": "string",
    "default": "sim_results",
    "description": "Directory for simulation results, relative to project_root"
},
"vdb_dir_template": {
    "type": "string",
    "default": "sim_results/coverage/{test}_{seed}.vdb",
    "description": "Template for VDB directory path. Placeholders: {test}, {seed}"
}
```

**注意**: 所有新字段都是 optional（不设 required），`default` 值确保旧 manifest 仍通过 `make validate`。

## Task 2: `lib/manifest.py`

在 `Manifest` 类中新增 4 个 property：

```python
@property
def sim_mode(self) -> str:
    """Return simulation mode: 'mock' or 'real'. Default: 'mock'."""
    return str(self.get("simulation", "mode") or "mock")

@property
def sim_results_root(self) -> Path:
    """Resolve simulation results root against project_root."""
    root = self.get("simulation", "results_root") or "sim_results"
    return self.resolve_path(str(root)) or (self.project_root / "sim_results")

@property
def sim_timeout(self) -> int:
    """Return simulation timeout in seconds. Default: 600."""
    val = self.get("simulation", "timeout_seconds")
    return int(val) if val is not None else 600

@property
def sim_urg_timeout(self) -> int:
    """Return URG timeout in seconds. Default: 300."""
    val = self.get("simulation", "urg_timeout_seconds")
    return int(val) if val is not None else 300
```

## Task 3: Mock Manifests — 添加 `mode: mock`

在 `mock_data/axi2ahb/project_manifest.yaml` 和 `mock_data/dma_subsystem/project_manifest.yaml` 的 `simulation:` 块中新增：

```yaml
simulation:
  mode: mock                  # ← 新增这一行
  compile_cmd_template: ...
```

## Task 4: `mock_data/axi2ahb/project_manifest_real.yaml.example`

复制 `mock_data/axi2ahb/project_manifest.yaml`，做以下修改：

1. `mode: mock` → `mode: real`
2. 在文件头部添加注释说明使用方式
3. 新增 URG 相关配置

```yaml
# Real-mode manifest for axi2ahb project
# Usage:
#   1. Copy this file to project_manifest.yaml (or use --manifest flag)
#   2. Set AXI2AHB_ROOT environment variable
#   3. Run: python scripts/sim_runner.py --manifest path/to/this.yaml --real
#
# WARNING: This manifest enables real VCS execution. Use only on servers with VCS installed.

simulation:
  mode: real
  compile_cmd_template: "make compile TEST={test}"
  run_cmd_template: "make run TEST={test} SEED={seed}"
  coverage_cmd_template: "make cov TEST={test}"
  urg_cmd_template: "urg -dir {vdb_dir} -report {report_dir} -format html"
  urg_binary: "urg"
  urg_timeout_seconds: 300
  timeout_seconds: 600
  results_root: "sim_results"
  vdb_dir_template: "sim_results/coverage/{test}_{seed}.vdb"
```

---

## Verification

```bash
# 1. Schema validation — 两个 mock manifest 必须通过（向后兼容）
make validate

# 2. 新增 properties 可访问
.venv/bin/python -c "
from lib.manifest import Manifest
m = Manifest.load('mock_data/axi2ahb/project_manifest.yaml')
print('sim_mode:', m.sim_mode)           # 期望: mock
print('sim_results_root:', m.sim_results_root)  # 期望: .../sim_results
print('sim_timeout:', m.sim_timeout)     # 期望: 600
print('sim_urg_timeout:', m.sim_urg_timeout)    # 期望: 300
"

# 3. 无 mode 字段时默认 mock
.venv/bin/python -c "
from lib.manifest import Manifest
# dma_subsystem manifest 如果还没有 mode 字段，也应默认 mock
m = Manifest.load('mock_data/dma_subsystem/project_manifest.yaml')
print('sim_mode (default):', m.sim_mode)  # 期望: mock
"

# 4. Real mode template 存在且可解析
.venv/bin/python -c "
from lib.manifest import Manifest
m = Manifest.load('mock_data/axi2ahb/project_manifest_real.yaml.example')
print('mode:', m.sim_mode)  # 期望: real
"

# 5. Lint + typecheck
.venv/bin/ruff check lib/manifest.py
.venv/bin/mypy lib/manifest.py

# 6. 现有测试不破坏
.venv/bin/python -m pytest --tb=short -q

# 7. 通用性检查
grep -n "axi\|ahb\|dma" lib/manifest.py
# 期望: 无新增匹配（仅已有内容）
```

---

## Quality Checklist

- [ ] `schemas/project_manifest.schema.json` 新增 7 个字段，全部 optional
- [ ] `lib/manifest.py` 新增 4 个 property: `sim_mode`, `sim_results_root`, `sim_timeout`, `sim_urg_timeout`
- [ ] 两个 mock manifest 添加 `mode: mock`
- [ ] `make validate` 通过（两个 manifest 都通过）
- [ ] `project_manifest_real.yaml.example` 创建，`mode: real`
- [ ] 无 mode 字段时 `sim_mode` 返回 `"mock"`（向后兼容）
- [ ] ruff 0 issues
- [ ] mypy 0 errors
- [ ] 现有 413+ 测试全部通过

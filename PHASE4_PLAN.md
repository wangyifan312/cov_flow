# Phase 4 计划文档

> 文档用途：定义 Phase 4 的工作范围、交付物、依赖关系和验收标准。
>
> 创建日期：2026-06-02
>
> 状态：**待审批 → 进行中**
>
> 前置条件：Phase 3 release-ready（已完成 Phase 3 hardening）

---

## 1. 背景

### 1.1 Phase 3 交付了什么

- URG HTML coverage report parser（`lib/urg_parser/`）
- 从真实 URG 报告生成 coverage_index.json + coverage_gaps.json
- axi2ahb demo 项目（982 gaps，7 种覆盖率类型）
- MCP tools 可以查询真实解析出的 coverage gaps

### 1.2 Phase 3 没有做什么

| 缺失能力 | 影响 |
|---|---|
| `cov_get_coverpoint_source` 仍返回 mock 片段 | scenario generation 的 evidence chain 不完整，AI 看不到真实 coverpoint 定义 |
| 无 project registry | 每次调用 MCP tool 都需要传完整 manifest path，团队使用不便 |
| 无 EDA adapter 接口定义 | Phase 5 要接入真实 Verdi/VCS 时没有架构基础 |
| 无 MCP tool contract tests | 新增 parser/adapter 后 envelope 字段可能漂移 |
| 无大数据量测试 | 982 gaps 下的 truncation/pagination 行为未被测试保护 |

### 1.3 为什么现在做 Phase 4

Phase 3 hardening 已完成，所有 P1 风险已关闭，CI 已建立。
当前仓库处于一个稳定的发布基线，适合在此基础上扩展新能力。

---

## 2. Phase 4 范围定义

Phase 4 包含 **三个核心工作包（WP）+ 一个加固工作包**：

| 工作包 | 名称 | 核心交付 | 优先级 |
|---|---|---|---|
| **WP-1** | Bounded Source Snippet Resolver | `cov_get_coverpoint_source` 读取真实 SV 文件 | P0（Phase 4 核心） |
| **WP-2** | Project Registry | `projects.yaml` + project name → manifest path 解析 | P1 |
| **WP-3** | EDA Adapter Skeleton | 抽象接口 + mock adapter + registry | P1 |
| **WP-4** | Phase 3 遗留加固 | contract tests + 大数据量测试 + 测试数量清理 | P2 |

---

## 3. WP-1: Bounded Source Snippet Resolver（核心）

### 3.1 目标

让 `cov_get_coverpoint_source` 从返回 mock/generated 片段变为**读取真实 SV 源文件**中的 bounded snippet，同时保持严格的安全边界。

### 3.2 当前状态

```python
# coverage_tools.py 第 238-303 行
# 当前实现：为 7 种 coverage type 分别生成 mock snippet
# 不读取任何真实文件
mock_source = (
    f"covergroup {gap.get('covergroup')} @(posedge clk);\n"
    f"  {gap.get('coverpoint')}: coverpoint <signal> {{\n"
    ...
)
```

manifest 中已有 `coverage_model_root` 字段：
- `dma_subsystem`: `coverage/coverage_model`（目录存在但为空）
- `axi2ahb`: `null`（未配置）

### 3.3 设计方案

#### 3.3.1 新增模块：`lib/source_resolver.py`

```
class SourceResolver:
    """Bounded source snippet resolver with security boundaries."""

    def __init__(self, allowed_roots: list[Path], max_lines: int = 40, max_bytes: int = 4096):
        ...

    def resolve(self, source_file: str, source_line: int, context_lines: int = 5) -> SourceSnippet:
        """Read a bounded snippet from a source file.

        Security:
        - source_file must be under one of allowed_roots
        - No path traversal (reject '../' and symlinks outside roots)
        - Snippet bounded by max_lines and max_bytes
        - Returns 'not_found' or 'access_denied' on failure
        """
        ...

@dataclass
class SourceSnippet:
    file: str           # relative path
    start_line: int
    end_line: int
    content: str        # the actual snippet text
    truncated: bool     # whether content was truncated
    status: str         # 'ok', 'file_not_found', 'access_denied', 'parse_error'
    message: str        # human-readable status description
```

#### 3.3.2 修改 `cov_get_coverpoint_source`

```python
def cov_get_coverpoint_source(project, gap_id, max_lines=40):
    # 1. 获取 gap 信息
    # 2. 确定 source_file 和 source_line
    # 3. 尝试 SourceResolver 读取真实文件
    #    - 如果 coverage_model_root 存在且文件在其中 → 读取真实 snippet
    #    - 如果文件不存在或不可读 → 回退到当前的 mock snippet
    # 4. 在 result 中标注 source_mode: "real" | "mock_fallback"
```

#### 3.3.3 安全边界

| 安全措施 | 说明 |
|---|---|
| **Allowlist** | 只读取 `coverage_model_root`、`rtl` 目录、`testbench.env_root`、`testbench.sequence_root` 下的文件 |
| **Path traversal 防护** | `Path.resolve()` 后检查是否在 allowed roots 下；拒绝 `..`、symlink 逃逸 |
| **Max lines** | 默认 40 行，最大 100 行 |
| **Max bytes** | 默认 4096 字节，最大 16384 字节 |
| **No full-file read** | 只读取 `[source_line - context, source_line + context]` 范围 |
| **Graceful fallback** | 文件不存在或不可读时，回退到 mock snippet，result 中标注 `source_mode: "mock_fallback"` |

#### 3.3.4 测试数据

为 `dma_subsystem` 创建 mock SV 文件：

```
mock_data/dma_subsystem/coverage/coverage_model/
  └── tb/cov/
      └── dma_cov.sv        # 包含 dma_desc_cg、dma_transfer_cg 等 covergroup 定义
```

文件内容示例（手工构造，非真实代码）：

```systemverilog
// Mock coverage model for dma_subsystem demo
// This is synthetic SV code for testing the source resolver

class dma_cov extends uvm_component;

  covergroup dma_desc_cg @(posedge clk);
    desc_mode_cp: coverpoint desc_mode {
      bins linked_list   = {DESC_LINKED_LIST};
      bins scatter_gather = {DESC_SCATTER_GATHER};
      bins single        = {DESC_SINGLE};
    }
    // ... more coverpoints
  endgroup

  covergroup dma_transfer_cg @(posedge clk);
    xfer_size_cp: coverpoint xfer_size {
      bins small  = {[1:64]};
      bins medium = {[65:512]};
      bins large  = {[513:4096]};
    }
  endgroup

endclass
```

### 3.4 交付物清单

| 文件 | 操作 | 说明 |
|---|---|---|
| `lib/source_resolver.py` | 新增 | SourceResolver 类 + SourceSnippet dataclass |
| `dv_mcp/dv_context_server/tools/coverage_tools.py` | 修改 | `cov_get_coverpoint_source` 集成 SourceResolver |
| `tests/test_source_resolver.py` | 新增 | 单元测试：正常读取、path traversal 拒绝、max_lines 截断、fallback |
| `tests/test_mcp_coverage_tools.py` | 修改 | 增加 source resolver 集成测试 |
| `mock_data/dma_subsystem/coverage/coverage_model/tb/cov/dma_cov.sv` | 新增 | mock SV 文件作为测试数据 |

### 3.5 验收标准

- [ ] `cov_get_coverpoint_source("dma_subsystem", "GAP_0001")` 返回真实 snippet（从 `dma_cov.sv` 读取）
- [ ] `cov_get_coverpoint_source("dma_subsystem", "GAP_L001")` 返回 code coverage 的真实 source line
- [ ] `cov_get_coverpoint_source("axi2ahb", "GAP_L001")` 回退到 mock（`coverage_model_root` 为 null）
- [ ] result 中包含 `source_mode: "real"` 或 `source_mode: "mock_fallback"`
- [ ] path traversal 测试：`source_file = "../../etc/passwd"` → 返回 `access_denied`
- [ ] max_lines 测试：请求 100 行但文件只有 20 行 → 返回 20 行，`truncated: false`
- [ ] max_bytes 测试：snippet 超过 max_bytes → 截断，`truncated: true`
- [ ] 所有现有测试仍然通过

---

## 4. WP-2: Project Registry

### 4.1 目标

让 MCP tools 支持 `project = "dma_subsystem"` 作为输入，而不必传完整 manifest path。

### 4.2 当前状态

```python
# project_loader.py resolve_project()
# 只支持直接 manifest path
manifest_path = Path(project_id_or_path)
if manifest_path.is_file():
    manifest = Manifest.load(manifest_path)
else:
    raise FileNotFoundError(...)
```

### 4.3 设计方案

#### 4.3.1 注册表文件：`projects.yaml`

```yaml
# projects.yaml — project name → manifest path registry
# Place this file at:
#   1. ./projects.yaml (repo root)
#   2. ~/.cov_flow/projects.yaml (user home)
#   3. Or set COV_FLOW_PROJECTS environment variable

projects:
  dma_subsystem:
    manifest: mock_data/dma_subsystem/project_manifest.yaml
    description: "Mock DMA project (Phase 0-2 demo)"
  axi2ahb:
    manifest: mock_data/axi2ahb/project_manifest.yaml
    description: "Sample AXI2AHB bridge URG report (Phase 3 demo)"
```

#### 4.3.2 新增模块：`lib/project_registry.py`

```python
class ProjectRegistry:
    """Resolves project names to manifest paths."""

    def __init__(self):
        self._projects = {}
        self._load()

    def _load(self):
        """Load from COV_FLOW_PROJECTS env var, ./projects.yaml, ~/.cov_flow/projects.yaml"""
        ...

    def resolve(self, project_name: str) -> Path:
        """Resolve project name to manifest path."""
        ...

    def list_projects(self) -> list[dict]:
        """List all registered projects."""
        ...
```

#### 4.3.3 修改 `project_loader.py`

```python
def resolve_project(project_id_or_path: str) -> _ProjectContext:
    # 1. 先尝试作为 project name 从 registry 查找
    # 2. 如果找不到，尝试作为直接 manifest path
    # 3. 如果都失败，返回清晰的错误信息（包含已注册的 project 列表）
```

### 4.4 交付物清单

| 文件 | 操作 | 说明 |
|---|---|---|
| `projects.yaml` | 新增 | repo 根目录的注册表 |
| `lib/project_registry.py` | 新增 | ProjectRegistry 类 |
| `dv_mcp/dv_context_server/services/project_loader.py` | 修改 | 集成 registry 查找 |
| `tests/test_project_registry.py` | 新增 | registry 解析测试 |
| `tests/test_mcp_coverage_tools.py` | 修改 | 增加 project name 输入测试 |

### 4.5 验收标准

- [ ] `cov_list_uncovered(project="dma_subsystem")` 可工作（不需要传 manifest path）
- [ ] `cov_list_uncovered(project="axi2ahb")` 可工作
- [ ] `cov_list_uncovered(project="nonexistent")` 返回清晰错误 + 已注册项目列表
- [ ] 直接传 manifest path 仍然可用（向后兼容）
- [ ] `COV_FLOW_PROJECTS` 环境变量优先于 `./projects.yaml`

---

## 5. WP-3: EDA Adapter Skeleton

### 5.1 目标

建立 EDA 工具 adapter 的抽象接口和 mock 实现，为 Phase 5 的真实接入做架构准备。
**不连接任何真实 EDA 工具。**

### 5.2 设计方案

#### 5.2.1 新增模块：`lib/eda_adapters/`

```
lib/eda_adapters/
  ├── __init__.py          # adapter 注册表
  ├── base.py              # abstract base class
  ├── mock_verdi.py        # mock Verdi adapter
  ├── mock_vcs.py          # mock VCS adapter
  └── README.md            # adapter 接口文档
```

#### 5.2.2 抽象接口

```python
class EDAAdapter(ABC):
    """Abstract base class for EDA tool adapters."""

    @property
    @abstractmethod
    def name(self) -> str: ...

    @property
    @abstractmethod
    def capabilities(self) -> list[str]: ...

    @abstractmethod
    def check_availability(self) -> dict[str, Any]:
        """Check if the EDA tool is available (license, path, etc.)."""
        ...

    @abstractmethod
    def open_waveform(self, path: str) -> dict[str, Any]:
        """Open a waveform file (FSDB/VCD). Returns stub in mock mode."""
        ...

    @abstractmethod
    def query_signal(self, signal_path: str, time_range: tuple) -> dict[str, Any]:
        """Query signal values from waveform. Returns stub in mock mode."""
        ...
```

#### 5.2.3 Mock 实现

```python
class MockVerdiAdapter(EDAAdapter):
    """Mock Verdi adapter — returns stub data, never calls real Verdi."""

    name = "verdi_mock"
    capabilities = ["waveform_view", "signal_query", "schematic_view"]

    def check_availability(self):
        return {"available": True, "mode": "mock", "note": "Mock adapter, no real Verdi"}

    def open_waveform(self, path):
        return {"status": "mock", "path": path, "signals": []}
```

### 5.3 交付物清单

| 文件 | 操作 | 说明 |
|---|---|---|
| `lib/eda_adapters/__init__.py` | 新增 | adapter 注册表和工厂方法 |
| `lib/eda_adapters/base.py` | 新增 | EDAAdapter 抽象基类 |
| `lib/eda_adapters/mock_verdi.py` | 新增 | Mock Verdi adapter |
| `lib/eda_adapters/mock_vcs.py` | 新增 | Mock VCS adapter |
| `lib/eda_adapters/README.md` | 新增 | 接口文档和使用说明 |
| `tests/test_eda_adapters.py` | 新增 | adapter 接口契约测试 |

### 5.4 验收标准

- [ ] `MockVerdiAdapter().check_availability()` 返回 `mode: "mock"`
- [ ] 所有 adapter 实现 `EDAAdapter` 抽象接口的全部方法
- [ ] adapter 注册表可根据 name 查找 adapter
- [ ] 没有任何代码调用真实 Verdi/VCS/KDB/NPI/VPI/FSDB
- [ ] 接口测试覆盖：availability check、waveform open、signal query

---

## 6. WP-4: Phase 3 遗留加固

### 6.1 MCP Tool Contract Tests（RISK_REVIEW #14）

新增 `tests/test_tool_contracts.py`：

```python
# 对每个 MCP tool 验证：
# 1. 成功返回包含标准 envelope: ok, tool, project, result, evidence, truncated, next_actions
# 2. 错误返回包含: ok=false, tool, project, error, evidence=[], truncated=false, next_actions=[]
# 3. evidence 是 list[dict]，每个 entry 有 type, id, source, summary
# 4. truncated 是 bool
# 5. next_actions 是 list[str]
```

### 6.2 大数据量测试（RISK_REVIEW #13, R-NEW-5）

新增测试，使用 axi2ahb 982-gap 数据集验证：

```python
# 1. cov_list_uncovered(project="axi2ahb", coverage_type="all") → truncated=True
# 2. cov_list_uncovered(project="axi2ahb", coverage_type="all", top_n=10) → 只返回 10 条
# 3. cov_list_uncovered(project="axi2ahb", coverage_type="toggle") → 763 gaps 中只返回 top_n
# 4. 返回的 result 大小在合理范围内（不超过 context budget）
```

### 6.3 测试数量清理（RISK_REVIEW #18）

- README.md：将 "181 tests" 改为不写具体数字，或加 "(as of Phase 2d)"
- CLAUDE.md：同上

### 6.4 交付物清单

| 文件 | 操作 | 说明 |
|---|---|---|
| `tests/test_tool_contracts.py` | 新增 | envelope contract 测试 |
| `tests/test_large_dataset.py` | 新增 | axi2ahb 982-gap 大数据量测试 |
| `README.md` | 修改 | 移除硬编码测试数量 |
| `CLAUDE.md` | 修改 | 移除硬编码测试数量 |

### 6.5 验收标准

- [ ] 每个 MCP tool 都通过 contract test（成功 + 失败两种路径）
- [ ] 大数据量测试验证 truncation 行为
- [ ] 文档中不再写死测试数量
- [ ] `make test` 全部通过

---

## 7. 依赖关系

```
WP-1 (Source Resolver)  ← 无依赖，可立即开始
WP-2 (Registry)         ← 无依赖，可与 WP-1 并行
WP-3 (EDA Skeleton)     ← 无依赖，可与 WP-1 并行
WP-4 (加固)             ← 建议在 WP-1/2/3 之后做（测试要覆盖新代码）
```

推荐执行顺序：

```
WP-1 → WP-2 → WP-3 → WP-4
 (核心)   (增强)   (骨架)   (加固)
```

WP-1 是核心，建议最先完成。WP-2 和 WP-3 可并行。WP-4 最后做，因为 contract tests 和大数据量测试需要覆盖 WP-1/2/3 的新代码。

---

## 8. 需要修改/新增的文件总览

### 新增文件

| 文件 | WP | 说明 |
|---|---|---|
| `lib/source_resolver.py` | WP-1 | Bounded source snippet resolver |
| `lib/project_registry.py` | WP-2 | Project name → manifest path 注册表 |
| `lib/eda_adapters/__init__.py` | WP-3 | Adapter 注册表 |
| `lib/eda_adapters/base.py` | WP-3 | EDAAdapter 抽象基类 |
| `lib/eda_adapters/mock_verdi.py` | WP-3 | Mock Verdi adapter |
| `lib/eda_adapters/mock_vcs.py` | WP-3 | Mock VCS adapter |
| `lib/eda_adapters/README.md` | WP-3 | Adapter 接口文档 |
| `projects.yaml` | WP-2 | 项目注册表 |
| `mock_data/dma_subsystem/coverage/coverage_model/tb/cov/dma_cov.sv` | WP-1 | Mock SV 测试数据 |
| `tests/test_source_resolver.py` | WP-1 | Source resolver 测试 |
| `tests/test_project_registry.py` | WP-2 | Registry 测试 |
| `tests/test_eda_adapters.py` | WP-3 | Adapter 测试 |
| `tests/test_tool_contracts.py` | WP-4 | Envelope contract 测试 |
| `tests/test_large_dataset.py` | WP-4 | 大数据量测试 |

### 修改文件

| 文件 | WP | 修改内容 |
|---|---|---|
| `dv_mcp/dv_context_server/tools/coverage_tools.py` | WP-1 | `cov_get_coverpoint_source` 集成 SourceResolver |
| `dv_mcp/dv_context_server/services/project_loader.py` | WP-2 | 集成 ProjectRegistry 查找 |
| `tests/test_mcp_coverage_tools.py` | WP-1/2 | 增加 source resolver + registry 测试 |
| `CLAUDE.md` | 全部 | 添加 Phase 4 scope 描述 + 移除硬编码测试数量 |
| `README.md` | 全部 | 添加 Phase 4 状态 + 移除硬编码测试数量 |
| `Makefile` | 全部 | 可能无需修改 |
| `schemas/project_manifest.schema.json` | WP-1 | 可能需要添加 `source_resolver` 配置字段 |

---

## 9. 安全边界（不可突破）

| 规则 | 说明 |
|---|---|
| **不接入真实 EDA 工具** | WP-3 只建 mock adapter，不调用 Verdi/VCS/KDB/NPI/VPI/FSDB |
| **不读取真实公司数据** | WP-1 的 mock SV 文件是手工构造的 demo 数据 |
| **不生成真实 UVM 代码** | testcase-generation skill 仍只输出结构化 JSON，不编译不运行 |
| **不运行真实仿真** | sim tools 仍为 mock/dry-run |
| **路径穿越防护** | SourceResolver 必须拒绝 `../` 和 symlink 逃逸 |
| **Context budget** | 单次 source snippet 不超过 max_bytes (默认 4096) |
| **Mock fallback** | 真实文件不可用时，回退到 mock snippet，不报错 |

---

## 10. 工作量预估

| 工作包 | 预估时间 | 说明 |
|---|---|---|
| WP-1 Source Resolver | 4-6 小时 | 核心模块 + mock SV 数据 + 测试 |
| WP-2 Registry | 2-3 小时 | 注册表 + 集成 + 测试 |
| WP-3 EDA Skeleton | 2-3 小时 | 接口定义 + 2 个 mock adapter + 测试 |
| WP-4 加固 | 2-3 小时 | contract tests + 大数据量测试 + 文档清理 |
| **总计** | **10-15 小时** | 约 1.5-2 个工作日 |

---

## 11. Phase 4 完成标准

Phase 4 标记为 **Done** 需要满足：

| 条件 | 要求 |
|---|---|
| WP-1 Source Resolver | `cov_get_coverpoint_source` 能读取真实 mock SV 文件 |
| WP-2 Registry | MCP tools 支持 project name 输入 |
| WP-3 EDA Skeleton | 抽象接口 + mock adapter 就位 |
| WP-4 加固 | contract tests + 大数据量测试通过 |
| make accept | 全部通过 |
| CI | GitHub Actions 绿色 |
| 安全边界 | 无 path traversal、无真实 EDA 调用 |
| 文档 | CLAUDE.md + README.md 更新 Phase 4 状态 |

---

## 12. Phase 5 展望（仅规划，不实现）

Phase 4 完成后，Phase 5 的可能方向：

| 方向 | 说明 |
|---|---|
| 真实 Verdi adapter | 基于 Phase 4 的 skeleton，填充真实 Verdi API 调用 |
| 真实 VCS 仿真集成 | 基于 Phase 4 的 skeleton，接入真实 VCS 编译/仿真 |
| FSDB waveform 分析 | 读取真实 waveform，提取信号值辅助 gap 分析 |
| Real eval LLM execution | 让 eval runner 真正执行 LLM，验证 skill workflow |

**所有这些都需要单独审批，不在 Phase 4 范围内。**

---

## 13. 进度跟踪

| 工作包 | 状态 | 开始日期 | 完成日期 | 备注 |
|---|---|---|---|---|
| WP-1 Source Resolver | ⬜ 待开始 | | | |
| WP-2 Registry | ⬜ 待开始 | | | |
| WP-3 EDA Skeleton | ⬜ 待开始 | | | |
| WP-4 加固 | ⬜ 待开始 | | | |

---

## 14. Coding Agent Prompt

（见下一节，可直接复制到新的 Claude Code 会话）

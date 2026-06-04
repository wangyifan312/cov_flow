# WP-2 Coding Agent Prompt: MCP TB 工具集成真实 tb_index.json

> **Phase**: 5a WP-2
> **前置**: WP-1 已完成（lib/sv_parser.py, scripts/build_tb_index.py 已通过验证）
> **目标**: 让 `tb_get_existing_tests_for_feature` MCP 工具能返回 axi2ahb 的真实 TB 数据（tests/sequences/api_methods/config_knobs），支持 triage 工作流中快速定位现有激励资源
> **验收**: `make accept` 全部通过（validate + build-indexes + build-real-index + lint + typecheck + test + smoke-server）

---

## 背景

WP-1 已完成 `scripts/build_tb_index.py`，可从真实 UVM 源码生成 `tb_index.json`（schema_version: `tb_index.v1`）。

当前 `dv_mcp/dv_context_server/tools/tb_tools.py` 的 `tb_get_existing_tests_for_feature` 已实现基础 feature tag 评分逻辑，但：
- axi2ahb 项目没有预构建的 `tb_index.json`（`.dv_ai_index/` 目录下只有 coverage 文件）
- Makefile 无 `build-real-tb-index` 目标
- tb_tools.py 不展示匹配 sequence 的 `api_methods`（这是 triage 最需要的信息）
- 无 axi2ahb tb 工具的集成测试

真实项目路径：`/Users/wangyifan/Desktop/AI/project_x2h/AXI2AHB-Lite-Bridge-UVM-Verification`
环境变量：`AXI2AHB_ROOT`

---

## 任务列表

### Task 1: 生成并提交 axi2ahb tb_index.json

运行以下命令生成真实的 tb_index.json：

```bash
export AXI2AHB_ROOT=/Users/wangyifan/Desktop/AI/project_x2h/AXI2AHB-Lite-Bridge-UVM-Verification
source .venv/bin/activate
python scripts/build_tb_index.py \
  --manifest mock_data/axi2ahb/project_manifest.yaml \
  --out mock_data/axi2ahb/.dv_ai_index
```

**注意**：`--out` 必须指向 `mock_data/axi2ahb/.dv_ai_index`（与 coverage_index.json 同目录，是 IndexReader 查找的目录）。

生成后验证输出包含：
- `base_tests`: 1 (base_test)
- `existing_tests`: 12 (concrete tests)
- `sequences`: 13 (含 base_virtual_sequence 44 个 api_methods)
- `config_knobs`: 24

**不要修改** `generated_at` 字段之后的内容；直接提交生成的文件。

### Task 2: Makefile 新增构建目标

在 `Makefile` 的 `# Index building` 部分添加：

```makefile
build-real-tb-index: ## Build TB index from real UVM sources (axi2ahb)
	$(PYTHON) scripts/build_tb_index.py --manifest mock_data/axi2ahb/project_manifest.yaml --out mock_data/axi2ahb/.dv_ai_index
```

**注意**：`build-real-tb-index` 需要 `AXI2AHB_ROOT` 环境变量，CI 上可能不可用，所以**不要**把它加入 `accept` 目标。`accept` 仍然只依赖 `build-real-index`（coverage）。

在 `.PHONY` 行添加 `build-real-tb-index`。

### Task 3: 增强 tb_tools.py

修改 `dv_mcp/dv_context_server/tools/tb_tools.py`，增强 `tb_get_existing_tests_for_feature`：

#### 3.1 新增参数 `scope`

```python
def tb_get_existing_tests_for_feature(
    project: str,
    feature: str,
    scope: str = "all",  # "all" | "tests" | "sequences"
) -> dict[str, Any]:
```

- `scope="all"`: 返回 sequences + existing_tests（默认，向后兼容）
- `scope="tests"`: 只返回 existing_tests
- `scope="sequences"`: 只返回 sequences

#### 3.2 匹配的 sequence 包含 api_methods

当前 seq_matches 不含 api_methods。增加：

```python
seq_matches.append({
    "name": seq.get("name"),
    "file": seq.get("file"),
    "extends": seq.get("extends"),
    "description": seq.get("description"),
    "feature_tags": seq.get("feature_tags"),
    "relevance": min(s / 10.0, 1.0),
    "api_methods": [  # 新增：展示 API 方法签名
        {
            "name": m.get("name"),
            "signature": m.get("signature", ""),
            "is_task": m.get("is_task", False),
        }
        for m in seq.get("api_methods", [])
    ],
})
```

**重要**：`base_virtual_sequence` 有 44 个 api_methods，全量返回会超 context budget。只对**非 base** sequence 展示完整 api_methods；对 base sequence 只展示前 10 个方法，并在 result 中注明 `api_methods_truncated: true`。

实现方式：

```python
MAX_BASE_METHODS = 10

# 在循环内判断是否是 base sequence
is_base = seq.get("extends") in ("uvm_sequence", "uvm_sequence_base") or \
          seq.get("name", "").startswith("base_")
all_methods = seq.get("api_methods", [])
if is_base and len(all_methods) > MAX_BASE_METHODS:
    methods_out = [
        {"name": m.get("name"), "signature": m.get("signature", ""), "is_task": m.get("is_task", False)}
        for m in all_methods[:MAX_BASE_METHODS]
    ]
    methods_truncated = True
else:
    methods_out = [
        {"name": m.get("name"), "signature": m.get("signature", ""), "is_task": m.get("is_task", False)}
        for m in all_methods
    ]
    methods_truncated = False
```

并在 seq_matches 的 dict 中加入 `"api_methods_truncated": methods_truncated`。

#### 3.3 base_tests 只在 scope="all" 或 scope="tests" 时返回

config_knobs 同理。

#### 3.4 更新函数 docstring

说明 scope 参数的含义和取值。

### Task 4: 编写集成测试

#### 4.1 新增文件 `tests/test_mcp_tb_tools_axi2ahb.py`

```python
"""Integration tests for tb_get_existing_tests_for_feature with axi2ahb real TB data."""

import pytest

from dv_mcp.dv_context_server.services.project_loader import clear_cache
from dv_mcp.dv_context_server.tools.tb_tools import tb_get_existing_tests_for_feature

AXI2AHB = "mock_data/axi2ahb/project_manifest.yaml"

@pytest.fixture(autouse=True)
def _clear():
    clear_cache()
    yield
    clear_cache()

class TestAxi2ahbBurstFeature:
    """feature='burst' should match wrap/incr/fixed sequences."""

    def test_returns_ok(self) -> None:
        result = tb_get_existing_tests_for_feature(AXI2AHB, "burst")
        assert result["ok"] is True

    def test_matches_sequences(self) -> None:
        result = tb_get_existing_tests_for_feature(AXI2AHB, "burst")
        seq_names = [s["name"] for s in result["result"]["sequences"]]
        # base_virtual_sequence has 'burst' tag
        assert "base_virtual_sequence" in seq_names

    def test_matches_tests(self) -> None:
        result = tb_get_existing_tests_for_feature(AXI2AHB, "burst")
        test_names = [t["name"] for t in result["result"]["existing_tests"]]
        # mixed_random_traffic_test has 'burst' tag
        assert len(test_names) >= 1

    def test_api_methods_included(self) -> None:
        result = tb_get_existing_tests_for_feature(AXI2AHB, "burst")
        seqs = result["result"]["sequences"]
        # base_virtual_sequence should have api_methods (truncated to 10)
        base_seq = next(s for s in seqs if s["name"] == "base_virtual_sequence")
        assert len(base_seq["api_methods"]) == 10
        assert base_seq["api_methods_truncated"] is True

    def test_non_base_seq_full_methods(self) -> None:
        result = tb_get_existing_tests_for_feature(AXI2AHB, "burst")
        seqs = result["result"]["sequences"]
        # mixed_random_traffic_virt_seq is non-base, should have full methods
        mixed = next((s for s in seqs if s["name"] == "mixed_random_traffic_virt_seq"), None)
        if mixed:
            assert mixed["api_methods_truncated"] is False
            assert len(mixed["api_methods"]) > 10

class TestAxi2ahbWrapFeature:
    """feature='wrap' should match wrap sequences."""

    def test_matches_wrap_seq(self) -> None:
        result = tb_get_existing_tests_for_feature(AXI2AHB, "wrap")
        seq_names = [s["name"] for s in result["result"]["sequences"]]
        assert "wrap_random_len_size_wr_virt_seq" in seq_names

    def test_matches_wrap_test(self) -> None:
        result = tb_get_existing_tests_for_feature(AXI2AHB, "wrap")
        test_names = [t["name"] for t in result["result"]["existing_tests"]]
        assert "wrap_random_len_size_wr_test" in test_names

class TestAxi2ahbScopeFilter:
    """scope parameter filtering."""

    def test_scope_all(self) -> None:
        result = tb_get_existing_tests_for_feature(AXI2AHB, "write", scope="all")
        assert "sequences" in result["result"]
        assert "existing_tests" in result["result"]
        assert "base_tests" in result["result"]
        assert "config_knobs" in result["result"]

    def test_scope_tests_only(self) -> None:
        result = tb_get_existing_tests_for_feature(AXI2AHB, "write", scope="tests")
        assert "existing_tests" in result["result"]
        assert "sequences" not in result["result"]

    def test_scope_sequences_only(self) -> None:
        result = tb_get_existing_tests_for_feature(AXI2AHB, "write", scope="sequences")
        assert "sequences" in result["result"]
        assert "existing_tests" not in result["result"]

class TestAxi2ahbBaseTestsAndKnobs:
    """base_tests and config_knobs are returned."""

    def test_base_tests_present(self) -> None:
        result = tb_get_existing_tests_for_feature(AXI2AHB, "burst")
        base_tests = result["result"]["base_tests"]
        assert len(base_tests) == 1
        assert base_tests[0]["name"] == "base_test"

    def test_config_knobs_present(self) -> None:
        result = tb_get_existing_tests_for_feature(AXI2AHB, "burst")
        knobs = result["result"]["config_knobs"]
        assert len(knobs) >= 10  # axi2ahb has 24 knobs

class TestAxi2ahbNoMatch:
    """No match returns empty lists."""

    def test_no_match(self) -> None:
        result = tb_get_existing_tests_for_feature(AXI2AHB, "zzzznonexistent")
        assert result["ok"] is True
        assert len(result["result"]["sequences"]) == 0
        assert len(result["result"]["existing_tests"]) == 0
```

#### 4.2 更新 `tests/test_mcp_tb_tools.py`

在现有 dma_subsystem 测试中添加 `api_methods` 相关断言：

- `test_descriptor_feature`: 验证匹配的 sequence 有 `api_methods` 字段
- `test_includes_base_tests`: 保持原样（dma 的 base_tests 不受 api_methods 截断影响）

#### 4.3 更新 `tests/test_tool_contracts.py`

axi2ahb 项目的 contract test：

```python
class TestTbToolContractsAxi2ahb:
    def test_tb_get_tests_success_axi2ahb(self) -> None:
        resp = tb_get_existing_tests_for_feature(AXI2AHB_PROJECT, "burst")
        _check_success(resp, "tb_get_existing_tests_for_feature")
```

### Task 5: 更新文档

#### 5.1 CLAUDE.md

在 `### Phase 4 — Source Resolver + Project Registry + EDA Adapters (Done)` 后面添加：

```markdown
### Phase 5a — TB Index Builder + MCP Integration (In Progress)
- **WP-1 SV Parser + TB Index Builder** (Done): `lib/sv_parser.py` (generic regex-based SV parser, 13 patterns), `scripts/build_tb_index.py` (manifest-driven CLI indexer), 47 tests
- **WP-2 MCP TB Tool Integration** (In Progress): `tb_get_existing_tests_for_feature` upgraded to return real axi2ahb test/sequence/api_method data; scope filter parameter; integration tests
```

#### 5.2 README.md

在 architecture 或 status 部分加入 WP-2 的状态更新（与 CLAUDE.md 保持一致）。

---

## 验证步骤

按顺序执行以下命令，全部通过后方可提交：

```bash
source .venv/bin/activate

# 1. 生成 tb_index.json
export AXI2AHB_ROOT=/Users/wangyifan/Desktop/AI/project_x2h/AXI2AHB-Lite-Bridge-UVM-Verification
python scripts/build_tb_index.py \
  --manifest mock_data/axi2ahb/project_manifest.yaml \
  --out mock_data/axi2ahb/.dv_ai_index

# 2. Lint + typecheck
ruff check .
ruff format --check .
mypy lib/ scripts/ dv_mcp/

# 3. 全部测试
python -m pytest tests/ -v

# 4. Mock server smoke test
PYTHONPATH=. python scripts/smoke_server.py

# 5. Full accept (不含 build-real-tb-index)
make accept
```

---

## 文件清单

| 文件 | 操作 | 说明 |
|---|---|---|
| `mock_data/axi2ahb/.dv_ai_index/tb_index.json` | **新增**（生成） | 运行 build_tb_index.py 生成 |
| `Makefile` | **修改** | 添加 `build-real-tb-index` 目标 |
| `dv_mcp/dv_context_server/tools/tb_tools.py` | **修改** | 添加 scope 参数 + api_methods 展示 + base 方法截断 |
| `tests/test_mcp_tb_tools_axi2ahb.py` | **新增** | axi2ahb 集成测试 |
| `tests/test_mcp_tb_tools.py` | **修改** | 添加 api_methods 字段断言 |
| `tests/test_tool_contracts.py` | **修改** | 添加 axi2ahb contract test |
| `CLAUDE.md` | **修改** | 添加 Phase 5a 状态 |
| `README.md` | **修改** | 更新状态 |

---

## 注意事项

1. **Context budget**: `base_virtual_sequence` 有 44 个 api_methods，全量返回会超 context budget。必须截断到 10 个并注明 `api_methods_truncated: true`。
2. **向后兼容**: `scope="all"` 是默认值，现有 dma_subsystem 测试不应受影响。
3. **不要修改** `lib/sv_parser.py` 或 `scripts/build_tb_index.py`（WP-1 的代码不在 WP-2 范围内）。
4. **不要修改** `lib/source_resolver.py` 或 `lib/project_registry.py`（Phase 4 代码）。
5. **ruff 0 + mypy 0** 是硬性要求，所有新代码必须通过。
6. **不要自动 commit**，完成所有验证后报告结果。

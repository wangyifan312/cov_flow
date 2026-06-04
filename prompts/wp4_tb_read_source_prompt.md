# WP-4 Coding Agent Prompt: Add `tb_read_source` MCP Tool

## Objective

Add a new MCP tool `tb_read_source` that reads the full source code of a testbench component (sequence, test, base_test, or env file) from the TB index, with security boundaries enforced by `SourceResolver`.

This is the **13th MCP tool** (currently 12).

## Background

The generic testcase generation workflow (see `prompts/testcase_gen_generic_prompt.md`) needs to read sequence/test source code to understand API signatures, constraints, and coding patterns. Currently the coding agent uses the local `Read` tool, but for remote/future Skill-based execution, an MCP tool with security boundaries is needed.

### Existing Patterns to Follow

- **`cov_get_coverpoint_source`** in `coverage_tools.py` — reads coverage model source via `SourceResolver`, returns envelope with `source_mode`, `truncated`, etc. Your tool should follow this exact pattern.
- **`SourceResolver`** in `lib/source_resolver.py` — handles path traversal protection, symlink checks, max_lines/max_bytes bounds. Reuse this class.
- **`tb_find_tests_for_gap`** in `tb_tools.py` — reads `tb_index.json`, looks up sequences/tests by name. Reuse this lookup pattern.

### TB Index Structure

```json
{
  "schema_version": "tb_index.v1",
  "env_root": "env",
  "sequence_root": "seq_lib",
  "sequences": [
    {
      "name": "wrap_random_len_size_wr_virt_seq",
      "file": "seq_lib/wrap_random_len_size_wr_virt_seq.sv",
      "extends": "base_virtual_sequence",
      "description": "",
      "feature_tags": ["random", "read", "wrap", "write"],
      "api_methods": [...]
    }
  ],
  "existing_tests": [
    {
      "name": "wrap_random_len_size_wr_test",
      "file": "tests/wrap_random_len_size_wr_test.sv",
      "extends": "base_test",
      "sequences": ["wrap_random_len_size_wr_virt_seq"],
      "feature_tags": ["random", "read", "wrap", "write"]
    }
  ],
  "base_tests": [
    {
      "name": "base_test",
      "file": "tests/base_test.sv",
      "extends": "uvm_test",
      "description": "",
      "feature_tags": [...],
      "api_methods": [...]
    }
  ],
  "config_knobs": [...]
}
```

### Manifest Paths (from `mock_data/axi2ahb/project_manifest.yaml`)

```yaml
testbench:
  type: uvm
  env_root: env
  base_test: tests/base_test.sv
  sequence_root: seq_lib
  agent_root: agent
  config_root: config
  test_root: tests
  index_path: .dv_ai_index
```

The `project_root` field (e.g., `$AXI2AHB_ROOT`) resolves to the actual project directory. Use `manifest.get_path()` or `manifest.base_dir` to resolve relative paths.

---

## Implementation

### File 1: `dv_mcp/dv_context_server/tools/tb_tools.py`

Add a new function `tb_read_source()` at the end of the file (after `tb_find_tests_for_gap`).

#### Function Signature

```python
def tb_read_source(
    project: str,
    component_type: str,
    name: str,
    max_lines: int = 500,
) -> dict[str, Any]:
```

#### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `project` | `str` | Project ID or manifest path |
| `component_type` | `str` | One of: `"sequence"`, `"test"`, `"base_test"`, `"env"` |
| `name` | `str` | Component name (e.g., `"wrap_random_len_size_wr_virt_seq"`) or file basename for env |
| `max_lines` | `int` | Maximum lines to return (default: 500, max: 1000) |

#### Logic

1. Validate `component_type` — return `error_envelope` if not in `{"sequence", "test", "base_test", "env"}`
2. Load `tb_index.json` via `get_index_reader(project)`
3. Look up the component by `name` in the appropriate index section:
   - `"sequence"` → search `data["sequences"]` where `seq["name"] == name`
   - `"test"` → search `data["existing_tests"]` where `t["name"] == name`
   - `"base_test"` → search `data["base_tests"]` where `t["name"] == name`
   - `"env"` → construct file path as `env_root / name` (name should be a filename like `axi2ahb_cov.sv`)
4. If not found, return `error_envelope` with a helpful message listing available components
5. Get the `file` field from the found entry (e.g., `"seq_lib/wrap_random_len_size_wr_virt_seq.sv"`)
6. Load manifest via `get_manifest(project)`
7. Determine the allowed root from manifest:
   - `"sequence"` → `manifest.get_path("testbench", "sequence_root")`
   - `"test"` / `"base_test"` → `manifest.get_path("testbench", "test_root")`
   - `"env"` → `manifest.get_path("testbench", "env_root")`
8. If the root is `None` or not a directory, fall back to `manifest.base_dir`
9. Use `SourceResolver` to read the file:
   ```python
   resolver = SourceResolver(
       allowed_roots=[allowed_root],
       max_lines=min(max_lines, 1000),
       max_bytes=65536,  # 64KB
   )
   # Read from line 1 with max_lines context to get the whole file
   snippet = resolver.resolve(file_path, source_line=1, context_lines=min(max_lines, 1000))
   ```
10. Count total lines in the file (read separately if needed, or use snippet metadata)
11. Return envelope with:
    ```python
    {
        "component_type": component_type,
        "name": name,
        "file": file_path,  # relative path from index
        "total_lines": <count>,
        "content": snippet.content,
        "truncated": snippet.truncated,
        "max_lines": max_lines,
        "source_mode": "real" if snippet.status == "ok" else snippet.status,
    }
    ```

#### Error Cases

| Case | Error Message |
|------|---------------|
| Invalid `component_type` | `"Invalid component_type '{x}': must be sequence\|test\|base_test\|env"` |
| Component not found | `"Component not found: {component_type} '{name}'. Available {type}s: [list of names]"` |
| TB index not found | Propagate from `IndexNotFoundError` |
| File not under allowed root | SourceResolver returns `access_denied` — pass through in envelope |
| File not found | SourceResolver returns `file_not_found` — pass through |
| Manifest load failure | Propagate as error_envelope |

#### Important Implementation Details

- **Do NOT modify** existing functions (`tb_get_existing_tests_for_feature`, `tb_find_tests_for_gap`, `_is_base_sequence`)
- Add `from lib.source_resolver import SourceResolver` at the top of the file (alongside existing imports)
- Add `from dv_mcp.dv_context_server.services.project_loader import get_manifest` (already imported in the file)
- Use `tb_evidence()` for evidence entries (already imported)
- The `max_lines` cap should be 1000 (sequence files can be 200-400 lines; env/coverage files can be larger)
- For the `"env"` component type, the `file` field in the index may not exist — construct the path as `f"{env_root}/{name}"` where `env_root` comes from the TB index's top-level `env_root` field or the manifest

### File 2: `dv_mcp/dv_context_server/server.py`

Register the new tool. Add to the imports:

```python
from dv_mcp.dv_context_server.tools.tb_tools import (
    tb_find_tests_for_gap,
    tb_get_existing_tests_for_feature,
    tb_read_source,  # NEW
)
```

Add a new `@mcp.tool()` function in the Testbench tools section:

```python
@mcp.tool()
def tool_tb_read_source(
    project: str,
    component_type: str,
    name: str,
    max_lines: int = 500,
) -> dict:
    """Read the source code of a testbench component (sequence, test, base_test, or env file).

    Reads from the TB index with security boundaries (path traversal protection,
    max_lines/max_bytes caps). Use this to inspect sequence API signatures,
    constraint patterns, and coding style for testcase generation.
    """
    return tb_read_source(project, component_type, name, max_lines=max_lines)
```

### File 3: `tests/test_tb_read_source.py` (NEW)

Integration tests using `mock_data/axi2ahb/project_manifest.yaml`.

Test cases:

1. **Read a sequence** — `component_type="sequence"`, `name="wrap_random_len_size_wr_virt_seq"`
   - `ok` is True
   - `content` contains `class wrap_random_len_size_wr_virt_seq`
   - `content` contains `fd_write_burst`
   - `file` is `"seq_lib/wrap_random_len_size_wr_virt_seq.sv"`
   - `total_lines` > 0
   - `source_mode` is `"real"` or `"mock_fallback"` (depends on whether project_root is set)

2. **Read a test** — `component_type="test"`, `name="wrap_random_len_size_wr_test"`
   - `ok` is True
   - `content` contains `class wrap_random_len_size_wr_test`

3. **Read a base_test** — `component_type="base_test"`, `name="base_test"`
   - `ok` is True
   - `content` contains `class base_test`

4. **Component not found** — `component_type="sequence"`, `name="nonexistent_seq"`
   - `ok` is False
   - Error message contains "not found"
   - Error message lists available sequences

5. **Invalid component_type** — `component_type="invalid"`
   - `ok` is False
   - Error message contains "Invalid component_type"

6. **max_lines truncation** — `max_lines=10`
   - Content is truncated (fewer than full file lines)
   - `truncated` is True

7. **env component type** — `component_type="env"`, `name="axi2ahb_cov.sv"`
   - If env file exists under env_root, returns content
   - If not, returns appropriate error

Use the same test pattern as `test_tb_find_tests_for_gap.py`:
```python
import pytest
from dv_mcp.dv_context_server.services.project_loader import clear_cache
from dv_mcp.dv_context_server.tools.tb_tools import tb_read_source

AXI2AHB = "mock_data/axi2ahb/project_manifest.yaml"

@pytest.fixture(autouse=True)
def _clear():
    clear_cache()
    yield
    clear_cache()
```

### File 4: `tests/test_tool_contracts.py` (MODIFY)

Add contract tests for `tb_read_source`. Follow the existing pattern in the file — read the file first to understand the contract test structure, then add:

1. **Envelope format** — returns dict with `ok`, `tool`, `project`, `result`, `evidence`, `truncated`, `next_actions` keys
2. **Evidence format** — evidence entries have `evidence_id`, `source_type`, `source_ref`, `summary`
3. **Error envelope** — invalid component_type returns `ok=False` with `error` key

---

## Quality Checklist

- [ ] `tb_read_source()` function added to `tb_tools.py` with correct signature and logic
- [ ] Tool registered in `server.py` as `tool_tb_read_source`
- [ ] All 4 component types work: `sequence`, `test`, `base_test`, `env`
- [ ] Invalid component_type returns error_envelope with available options
- [ ] Component not found returns error_envelope listing available names
- [ ] SourceResolver security boundaries enforced (path traversal, symlink, max_bytes)
- [ ] `max_lines` defaults to 500, capped at 1000
- [ ] `tests/test_tb_read_source.py` passes all test cases
- [ ] `tests/test_tool_contracts.py` contract tests pass
- [ ] `make test` — all tests pass
- [ ] `make lint` — ruff 0 issues
- [ ] `make typecheck` — mypy 0 errors
- [ ] Total MCP tool count is now 13

## Important Notes

- Follow the existing code style in `tb_tools.py` exactly (imports, docstrings, error handling pattern)
- The `SourceResolver` class is in `lib/source_resolver.py` — import as `from lib.source_resolver import SourceResolver`
- Use `get_manifest(project)` from `dv_mcp.dv_context_server.services.project_loader` to access manifest paths
- Use `get_index_reader(project)` to read `tb_index.json`
- Do NOT modify any existing functions in `tb_tools.py`
- The env component type is a stretch goal — if it's too complex to resolve env file paths, return an error_envelope saying "env reading not yet supported" and add a TODO comment

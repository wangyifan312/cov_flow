# MCP Tool Reference

Complete reference for the 26 tools exposed by the DV Context MCP Server
(`dv-context`). All tools return a standard JSON envelope with `tool`,
`project`, `result`, `evidence`, `truncated`, and `next_actions` fields.

---

## 1. Quick Lookup

| I want to... | Use this tool | Category |
|---|---|---|
| List top uncovered gaps | `cov_list_uncovered` | Coverage |
| Get full detail on one gap | `cov_get_gap_detail` | Coverage |
| Read coverpoint source code | `cov_get_coverpoint_source` | Coverage |
| Check gap hit history across regressions | `cov_get_hit_history` | Coverage |
| Compare before/after coverage databases | `cov_get_coverage_diff` | Coverage |
| Search spec by keyword | `spec_search` | Spec |
| Get a specific spec section | `spec_get_section` | Spec |
| Find registers controlling a feature | `reg_find_fields_affecting_feature` | Register |
| Look up a register field by name | `reg_find_field` | Register |
| Search register fields by description | `reg_search_by_description` | Register |
| Get the RAL path for a field | `reg_get_ral_path` | Register |
| Find an RTL signal by name | `rtl_find_signal` | RTL |
| Get module or instance info | `rtl_get_instance_info` | RTL |
| Read RTL source around a signal | `rtl_get_source_snippet` | RTL |
| Trace fan-in signals (stub) | `rtl_trace_fanin` | RTL |
| Find tests/sequences for a feature | `tb_get_existing_tests_for_feature` | TB |
| Find tests that may cover a specific gap | `tb_find_tests_for_gap` | TB |
| Read TB component source code | `tb_read_source` | TB |
| Find a sequence by name | `tb_find_sequence` | TB |
| Get base test template and config knobs | `tb_get_base_test_template` | TB |
| Find a config knob by name | `tb_find_config_knob` | TB |
| Read sequence source snippet by name | `tb_get_sequence_source_snippet` | TB |
| Run a targeted simulation | `sim_run_targeted_test` | Simulation |
| Get simulation result for a test | `sim_get_test_result` | Simulation |
| Search a simulation log for a keyword | `sim_search_log` | Simulation |
| Check waveform signal condition (stub) | `wave_check_condition` | Simulation |

---

## 2. Tool Details by Category

### 2.1 Coverage Tools

#### cov_get_coverage_diff

- **Category**: Coverage
- **Parameters**:
  - `project` (str, required) — project name or manifest path
  - `gap_id` (str | None, default `None`) — restrict diff to a single gap
- **Returns**: Diff summary with `newly_covered`, `regressed`, and per-gap deltas. Auto-discovers the latest URG reports from `sim_results/`.
- **Reads from**: `sim_results/*/urg_report/coverage_gaps.json`
- **Example call**: `cov_get_coverage_diff(project="axi2ahb", gap_id="GAP_0003")`

#### cov_get_coverpoint_source

- **Category**: Coverage
- **Parameters**:
  - `project` (str, required) — project name or manifest path
  - `gap_id` (str, required) — gap identifier (e.g. `"GAP_0001"`)
  - `max_lines` (int, default `40`) — maximum lines to return
- **Returns**: Source snippet for the coverpoint with `source_mode` indicator (`"real"` when read from `coverage_model_root`, `"synthetic"` otherwise).
- **Reads from**: `coverage_index.json`, source files via SourceResolver
- **Example call**: `cov_get_coverpoint_source(project="axi2ahb", gap_id="GAP_0006")`

#### cov_get_gap_detail

- **Category**: Coverage
- **Parameters**:
  - `project` (str, required) — project name or manifest path
  - `gap_id` (str, required) — gap identifier (e.g. `"GAP_0001"`)
- **Returns**: Complete gap record including all type-specific fields (covergroup/coverpoint/bin for functional; source_file/source_line for code coverage; signal/module for toggle; fsm_name/state for FSM).
- **Reads from**: `coverage_index.json`
- **Example call**: `cov_get_gap_detail(project="axi2ahb", gap_id="GAP_0003")`

#### cov_get_hit_history

- **Category**: Coverage
- **Parameters**:
  - `project` (str, required) — project name or manifest path
  - `gap_id` (str, required) — gap identifier (e.g. `"GAP_0001"`)
- **Returns**: Hit history across regression runs, trend analysis (`improving` / `stable` / `regressing` / `never_covered`), and `first_covered` info.
- **Reads from**: `sim_history.json` (built index)
- **Example call**: `cov_get_hit_history(project="axi2ahb", gap_id="GAP_0001")`

#### cov_list_uncovered

- **Category**: Coverage
- **Parameters**:
  - `project` (str, required) — project name or manifest path
  - `scope` (str | None, default `None`) — instance path filter (e.g. `"tb_top.u_dut.u_dma"`)
  - `coverage_type` (str, default `"functional"`) — type filter; use `"all"` to include all 7 types
  - `top_n` (int, default `20`) — maximum gaps to return (capped at 50)
- **Returns**: Gap summaries sorted by priority (P0 first). Each summary includes gap_id, coverage_type, hit_count, goal, priority, classification, and type-specific fields.
- **Reads from**: `coverage_index.json`
- **Example call**: `cov_list_uncovered(project="axi2ahb", coverage_type="all", top_n=10)`

---

### 2.2 Spec Tools

#### spec_get_section

- **Category**: Spec
- **Parameters**:
  - `project` (str, required) — project name or manifest path
  - `section_id` (str, required) — section identifier (e.g. `"spec_linked_list_descriptor_mode"`)
- **Returns**: Full section details: title, text, page_range, and feature_tags.
- **Reads from**: `spec_index.json`
- **Example call**: `spec_get_section(project="dma_subsystem", section_id="spec_linked_list_descriptor_mode")`

#### spec_search

- **Category**: Spec
- **Parameters**:
  - `project` (str, required) — project name or manifest path
  - `query` (str, required) — search keyword or feature tag
  - `max_results` (int, default `10`) — maximum results (capped at 20)
- **Returns**: Matching spec sections scored against titles, feature_tags, and summary text. Each result includes section_id, title, page_range, feature_tags, and summary.
- **Reads from**: `spec_index.json`
- **Example call**: `spec_search(project="dma_subsystem", query="linked_list")`

---

### 2.3 Register Tools

#### reg_find_field

- **Category**: Register
- **Parameters**:
  - `project` (str, required) — project name or manifest path
  - `field_name` (str, required) — field name (case-insensitive exact match, e.g. `"LL_MODE_EN"`)
- **Returns**: Field details including register, offset, bit_range, access, reset, description, ral_path, and feature_tags.
- **Reads from**: `reg_db.json`
- **Example call**: `reg_find_field(project="dma_subsystem", field_name="LL_MODE_EN")`

#### reg_find_fields_affecting_feature

- **Category**: Register
- **Parameters**:
  - `project` (str, required) — project name or manifest path
  - `feature` (str, required) — feature keyword (e.g. `"linked_list"`, `"interrupt"`, `"power"`)
- **Returns**: Matching register fields scored by relevance against feature_tags (weight 3+5), field name (weight 2), description (weight 1), and register name (weight 1). Sorted by relevance descending.
- **Reads from**: `reg_db.json`
- **Example call**: `reg_find_fields_affecting_feature(project="dma_subsystem", feature="linked_list")`

#### reg_get_ral_path

- **Category**: Register
- **Parameters**:
  - `project` (str, required) — project name or manifest path
  - `field_name` (str, required) — field name (case-insensitive)
- **Returns**: RAL access path, register name, offset, and bit_range for the field.
- **Reads from**: `reg_db.json`
- **Example call**: `reg_get_ral_path(project="dma_subsystem", field_name="LL_MODE_EN")`

#### reg_search_by_description

- **Category**: Register
- **Parameters**:
  - `project` (str, required) — project name or manifest path
  - `query` (str, required) — search keyword
- **Returns**: Top 10 matching register fields scored against feature_tags (weight 5), register name (weight 2), and description (weight 1). Sorted by relevance descending.
- **Reads from**: `reg_db.json`
- **Example call**: `reg_search_by_description(project="dma_subsystem", query="burst length")`

---

### 2.4 RTL Tools

#### rtl_find_signal

- **Category**: RTL
- **Parameters**:
  - `project` (str, required) — project name or manifest path
  - `signal_name` (str, required) — signal name or substring to search for
  - `module_filter` (str | None, default `None`) — restrict search to a specific module
- **Returns**: Matching signals with module context, file path, signal type (port/internal), width, and line number.
- **Reads from**: `rtl_index.json`
- **Example call**: `rtl_find_signal(project="axi2ahb", signal_name="axi_valid", module_filter="axi2ahb_core")`

#### rtl_get_instance_info

- **Category**: RTL
- **Parameters**:
  - `project` (str, required) — project name or manifest path
  - `module_name` (str | None, default `None`) — module name (case-insensitive exact match)
  - `instance_path` (str | None, default `None`) — dot-separated instance path (e.g. `"u_dma.u_desc_parser"`)
- **Returns**: Module details: file, line_range, ports, signals, instances, fsm_states, and parameters. At least one of `module_name` or `instance_path` must be provided.
- **Reads from**: `rtl_index.json`
- **Example call**: `rtl_get_instance_info(project="dma_subsystem", module_name="dma_desc_parser")`

#### rtl_get_source_snippet

- **Category**: RTL
- **Parameters**:
  - `project` (str, required) — project name or manifest path
  - `signal_name` (str, required) — signal name to locate
  - `module_filter` (str | None, default `None`) — restrict search to a specific module
  - `context_lines` (int, default `5`) — lines of context around the definition
- **Returns**: Bounded source snippet with file path, line range, and content. Uses SourceResolver security boundaries (path traversal protection, max 40 lines / 4 KB).
- **Reads from**: `rtl_index.json`, RTL source files via SourceResolver
- **Example call**: `rtl_get_source_snippet(project="axi2ahb", signal_name="wr_state", context_lines=10)`

#### rtl_trace_fanin

- **Category**: RTL — **stub**
- **Parameters**:
  - `project` (str, required) — project name or manifest path
  - `signal_name` (str, required) — signal name to trace fan-in for
  - `module_filter` (str | None, default `None`) — restrict search to a specific module
- **Returns**: Same-module signals (ports and internal) as potential fan-in sources. Full cross-module tracing requires elaboration data and is not available in text-analysis mode.
- **Reads from**: `rtl_index.json`
- **Note**: This is a **stub**. The `note` field in the result indicates whether the data comes from a same-module approximation or an elaborated netlist.
- **Example call**: `rtl_trace_fanin(project="axi2ahb", signal_name="wr_state")`

---

### 2.5 TB Tools

#### tb_find_config_knob

- **Category**: TB
- **Parameters**:
  - `project` (str, required) — project name or manifest path
  - `knob_name` (str, required) — config knob name or substring
- **Returns**: Matching config knobs including name, type, default value, and plusarg string. Supports fuzzy/substring matching.
- **Reads from**: `tb_index.json`
- **Example call**: `tb_find_config_knob(project="dma_subsystem", knob_name="burst_len")`

#### tb_find_sequence

- **Category**: TB
- **Parameters**:
  - `project` (str, required) — project name or manifest path
  - `sequence_name` (str, required) — sequence name or substring
- **Returns**: Matching sequences with file, extends, description, feature_tags, and api_methods. Supports fuzzy/substring matching.
- **Reads from**: `tb_index.json`
- **Example call**: `tb_find_sequence(project="axi2ahb", sequence_name="wrap")`

#### tb_find_tests_for_gap

- **Category**: TB
- **Parameters**:
  - `project` (str, required) — project name or manifest path
  - `gap_id` (str, required) — coverage gap identifier (e.g. `"GAP_0003"`)
- **Returns**: Semantic keywords extracted from the gap's coverpoint/bin names, matching sequences and tests with relevance scores, and a gap assessment (`covered` / `partially_covered` / `not_covered`) with confidence. **Only supports functional coverage gaps**; code coverage gaps return an error.
- **Reads from**: `coverage_index.json`, `tb_index.json`
- **Example call**: `tb_find_tests_for_gap(project="axi2ahb", gap_id="GAP_0006")`

#### tb_get_base_test_template

- **Category**: TB
- **Parameters**:
  - `project` (str, required) — project name or manifest path
  - `base_test_name` (str | None, default `None`) — specific base test name (case-insensitive); `None` returns all base tests
- **Returns**: Base test(s) with name, file, extends, description, and config_knobs.
- **Reads from**: `tb_index.json`
- **Example call**: `tb_get_base_test_template(project="dma_subsystem")`

#### tb_get_existing_tests_for_feature

- **Category**: TB
- **Parameters**:
  - `project` (str, required) — project name or manifest path
  - `feature` (str, required) — feature keyword (e.g. `"linked_list"`, `"interrupt"`, `"burst"`)
- **Returns**: Matching sequences (with api_methods) and tests sorted by relevance. The `scope` parameter controls which sections are returned:
  - `"all"` (default): sequences + existing_tests + base_tests + config_knobs
  - `"tests"`: existing_tests + base_tests + config_knobs
  - `"sequences"`: sequences only

  Base sequences (extending `uvm_sequence` or named `base_*`) have api_methods truncated to 10 entries.
- **Reads from**: `tb_index.json`
- **Example call**: `tb_get_existing_tests_for_feature(project="axi2ahb", feature="wrap_burst")`

#### tb_get_sequence_source_snippet

- **Category**: TB
- **Parameters**:
  - `project` (str, required) — project name or manifest path
  - `sequence_name` (str, required) — exact sequence name or substring for fuzzy fallback
  - `max_lines` (int, default `40`) — maximum lines to return (capped at 1000)
- **Returns**: Sequence name, file path, source snippet, total_lines, and max_lines. Convenience wrapper around `tb_read_source` — looks up the sequence in `tb_index.json` (exact match first, then fuzzy fallback), then reads the source file with SourceResolver security boundaries.
- **Reads from**: `tb_index.json`, sequence source files via SourceResolver
- **Example call**: `tb_get_sequence_source_snippet(project="dma_subsystem", sequence_name="dma_linked_list_seq")`

#### tb_read_source

- **Category**: TB
- **Parameters**:
  - `project` (str, required) — project name or manifest path
  - `component_type` (str, required) — one of `"sequence"`, `"test"`, `"base_test"`, `"env"`
  - `name` (str, required) — component name or file basename for env
  - `max_lines` (int, default `500`) — maximum lines to return (capped at 1000)
- **Returns**: Component source content, total_lines, truncated flag, and `source_mode` indicator. Uses SourceResolver for path traversal protection, symlink checks, and max_bytes (64 KB) cap.
- **Reads from**: `tb_index.json`, TB source files via SourceResolver
- **Example call**: `tb_read_source(project="axi2ahb", component_type="sequence", name="wrap8_seq")`

---

### 2.6 Simulation Tools

#### sim_get_test_result

- **Category**: Simulation
- **Parameters**:
  - `project` (str, required) — project name or manifest path
  - `test` (str, required) — test name
  - `seed` (int | None, default `None`) — random seed
- **Returns**: Simulation result with compile_status, sim_status, log_summary, and log_path. Loads persisted SimResult or parses `run.log`.
- **Reads from**: `sim_results/<test>_<seed>/`
- **Example call**: `sim_get_test_result(project="axi2ahb", test="wrap8_test", seed=42)`

#### sim_run_targeted_test

- **Category**: Simulation
- **Parameters**:
  - `project` (str, required) — project name or manifest path
  - `test` (str, required) — test name
  - `seed` (int, required) — random seed
  - `confirm` (bool, default `False`) — must be `True` to proceed with execution
- **Returns**: Simulation execution result with compile/run/urg step status, return codes, log paths, and durations. Requires `confirm=true` and `policy.allow_running_simulation=true` in the manifest. Executes VCS subprocess via SimExecutor.
- **Reads from**: project manifest (command templates and policy)
- **Example call**: `sim_run_targeted_test(project="axi2ahb", test="wrap8_test", seed=42, confirm=True)`

#### sim_search_log

- **Category**: Simulation
- **Parameters**:
  - `project` (str, required) — project name or manifest path
  - `test` (str, required) — test name
  - `seed` (int, required) — random seed
  - `keyword` (str, required) — search keyword (case-insensitive)
- **Returns**: Matching log lines (bounded to 20 lines max) with total match count and log path. Searches real log files via SimExecutor.
- **Reads from**: `sim_results/<test>_<seed>/run.log`
- **Example call**: `sim_search_log(project="axi2ahb", test="wrap8_test", seed=42, keyword="UVM_ERROR")`

#### wave_check_condition

- **Category**: Simulation — **stub**
- **Parameters**:
  - `project` (str, required) — project name or manifest path
  - `signal_path` (str, required) — hierarchical signal path (e.g. `"top.dut.axi_valid"`)
  - `condition` (str, required) — condition expression (e.g. `"axi_valid && axi_ready"`)
  - `time_range` (str | None, default `None`) — time range as `"start,end"` string (e.g. `"0,1000"`)
- **Returns**: Waveform query results with `mode: "stub"`, signal_values, and `condition_met: null`. Uses StubVerdiAdapter internally.
- **Reads from**: StubVerdiAdapter (no real waveform data)
- **Note**: This is a **permanent stub**. Real waveform analysis requires Verdi/NPI integration which is not available per project rules.
- **Example call**: `wave_check_condition(project="axi2ahb", signal_path="top.dut.axi_valid", condition="axi_valid && axi_ready", time_range="0,5000")`

---

## 3. Tool Chaining Guide

The four primary verification workflows use tools in the following sequences.
Each step feeds context into the next, building up the information needed
for the LLM to reason about coverage closure.

### Triage Workflow

Understand why a gap exists and whether it is worth pursuing.

```
cov_list_uncovered          # identify top-priority gaps
  → cov_get_gap_detail      # full gap record and classification
  → cov_get_coverpoint_source  # see the SV coverpoint code
  → spec_search             # find related spec sections
  → reg_find_fields_affecting_feature  # identify control registers
  → cov_get_hit_history     # check if the gap was ever hit before
```

### Scenario Workflow

Design a new test scenario to close a specific gap.

```
cov_get_gap_detail          # understand the gap
  → cov_get_coverpoint_source  # read the coverpoint definition
  → spec_search             # gather spec context
  → spec_get_section        # read full spec section text
  → reg_find_fields_affecting_feature  # find knobs to control
  → tb_get_existing_tests_for_feature  # see what tests already exist
  → tb_find_tests_for_gap   # assess whether existing tests cover it
```

### Testcase Generation Workflow

Build a new UVM test from existing infrastructure.

```
tb_get_base_test_template   # pick a base test to extend
  → tb_find_sequence        # find reusable sequences
  → tb_get_sequence_source_snippet  # read sequence API and constraints
  → tb_find_config_knob     # discover plusargs and config knobs
  → tb_read_source          # read full component source for reference
```

### Simulation Feedback Workflow

Run a test and evaluate whether it closed the target gap.

```
sim_run_targeted_test       # execute the test (confirm=true)
  → sim_get_test_result     # check pass/fail status
  → sim_search_log          # search for errors or key events
  → cov_get_coverage_diff   # compare before/after coverage
  → cov_get_hit_history     # verify trend (improving?)
```

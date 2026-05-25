# End-to-End Coverage Closure Walkthrough

Complete coverage closure flow for a single gap using the DV AI Coverage
Closure Skill Pack. Uses GAP_0001 from the `{project}` mock project.

```
 Triage ──▶ Scenario ──▶ Generate Case ──▶ Simulation ──▶ Feedback
```

## Stage 1 — Triage (`dv-coverage-gap-triage`)

**Prompt:** `Triage GAP_0001 in project {project}.`

**Tool calls:** `cov_list_uncovered` → `cov_get_gap_detail` →
`cov_get_coverpoint_source` → `spec_search` →
`reg_find_fields_affecting_feature`

**Output:**
```yaml
gap_id: GAP_0001
classification: Config Missing
priority: P0
recommended_action: scenario-generation
```
See [triage_walkthrough.md](triage_walkthrough.md) for details.

## Stage 2 — Scenario Card (`dv-coverage-scenario-generation`)

**Prompt:**
```
Generate a scenario card for GAP_0001 in project {project}.
Classification: Config Missing — LL_MODE_EN must be enabled.
```

**Tool calls:** `cov_get_gap_detail` → `reg_find_fields_affecting_feature` →
`tb_get_existing_tests_for_feature` → `spec_search`

**Output (scenario card):**
```json
{
  "scenario_id": "SCN_GAP0001_01",
  "gap_id": "GAP_0001",
  "title": "Linked-list descriptor mode enable and transfer",
  "steps": [
    { "order": 1, "action": "Write DMA_CFG.LL_MODE_EN = 1" },
    { "order": 2, "action": "Program descriptor base address" },
    { "order": 3, "action": "Build two-element linked-list in memory" },
    { "order": 4, "action": "Start DMA transfer via DMA_CTRL.START" },
    { "order": 5, "action": "Wait for completion interrupt" }
  ],
  "expected_result": "desc_mode_cp bin linked_list hits"
}
```

> **Decision point:** If `tb_get_existing_tests_for_feature` returns a test
> that should have covered this bin, investigate before generating a new one.

## Stage 3 — Test-Case Generation (`dv-testcase-generation`)

**Prompt:** `Generate a UVM testcase patch for SCN_GAP0001_01, scope {scope}.`

**Tool calls:** `cov_get_gap_detail` → `cov_get_coverpoint_source` →
`rtl_find_signal(signal="u_dma.u_desc_parser.ll_mode_en")`

**Output (patch metadata):**
```json
{
  "patch_id": "PATCH_GAP0001_01",
  "testcase_name": "dma_linked_list_mode_test",
  "files_modified": ["tb/tests/dma_linked_list_mode_test.sv"],
  "files_created": ["tb/sequences/dma_ll_mode_seq.sv"],
  "run_args": "+UVM_TESTNAME=dma_linked_list_mode_test"
}
```

**Validate before proceeding:**
```bash
make validate-patch FILE=path/to/patch.json
make static-check FILE=path/to/patch.json
```

## Stage 4 — Simulation

**Prompt:** `Run dma_linked_list_mode_test for project {project}.`

**Tool calls:**
1. `sim_run_targeted_test(test_name="dma_linked_list_mode_test")`
2. `sim_get_test_result(run_id=...)` — poll for pass/fail

**Output:**
```json
{ "run_id": "run_001", "status": "PASS", "duration_s": 42, "seed": 12345 }
```
> Phase 1 returns canned responses; later phases integrate real simulators.

## Stage 5 — Feedback (`dv-simulation-feedback`)

**Prompt:** `Analyse run_001 — did GAP_0001 close? Any regressions?`

**Tool calls:** `sim_get_test_result` → `sim_search_log(pattern=...)` →
`cov_get_coverage_diff(run_id="run_001")`

**Output:**
```yaml
gap_id: GAP_0001
status: CLOSED
bin_hit: true
new_gaps_introduced: 0
regressions: 0
```

## Summary — Full Tool Chain

| Stage | Tools | Output |
|---|---|---|
| Triage | `cov_list_uncovered`, `cov_get_gap_detail`, `cov_get_coverpoint_source`, `spec_search`, `reg_find_fields_affecting_feature` | Classification + action |
| Scenario | `cov_get_gap_detail`, `reg_find_fields_affecting_feature`, `tb_get_existing_tests_for_feature`, `spec_search` | Scenario card |
| Generate | `cov_get_gap_detail`, `cov_get_coverpoint_source`, `rtl_find_signal` | Testcase patch |
| Simulate | `sim_run_targeted_test`, `sim_get_test_result` | Pass/fail |
| Feedback | `sim_get_test_result`, `sim_search_log`, `cov_get_coverage_diff` | Closure confirm |

Iterate over remaining gaps using the same flow. For server setup, see
[MCP Server Setup Guide](mcp_server_setup.md).

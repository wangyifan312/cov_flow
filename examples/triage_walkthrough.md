# Coverage Triage Walkthrough

This walkthrough shows how to triage a single coverage gap using the
`dv-context` MCP server. All data is from the `{project}` mock project.

## Prerequisites

- MCP server connected (see [MCP Server Setup Guide](mcp_server_setup.md))
- `make validate && make validate-gaps` passes
- `make build-indexes` has been run

## User Prompt Template

```
Triage coverage gap GAP_0001 in project {project}.
Classify it, assign priority, and recommend a next action.
```

## Tool Call Chain

### 1. List uncovered gaps

```
mcp__dv-context__cov_list_uncovered(project="{project}")
```
Returns all open gaps sorted by priority. Select GAP_0001 (P0).

### 2. Get gap detail

```
mcp__dv-context__cov_get_gap_detail(gap_id="GAP_0001")
```
Returns covergroup, coverpoint, bin, hit count, source location,
classification, priority, related register, spec section, and RTL signal.

### 3. Inspect coverpoint source

```
mcp__dv-context__cov_get_coverpoint_source(
    source_file="tb/cov/dma_cov.sv", line=88, context_lines=10)
```
Returns a bounded ±10-line snippet showing how the bin is defined.

### 4. Search the spec

```
mcp__dv-context__spec_search(query="linked list descriptor mode")
```
Returns spec excerpts describing the linked-list mode enable mechanism.

### 5. Find related register fields

```
mcp__dv-context__reg_find_fields_affecting_feature(feature="linked_list_mode")
```
Returns fields like `DMA_CFG.LL_MODE_EN` with reset values and access types.

## Expected Triage Output

```yaml
gap_id: GAP_0001
classification: Config Missing
priority: P0
root_cause: No test enables LL_MODE_EN, so the linked_list bin is never hit.
recommended_action: Generate a scenario enabling DMA_CFG.LL_MODE_EN.
next_skill: dv-coverage-scenario-generation
```

## Key Decision Points

| Question | If yes | If no |
|---|---|---|
| Classification is **Config Missing**? | Proceed with register-enable scenario. | Check stimulus/constraint path. |
| Spec confirms feature is supported? | Continue to scenario generation. | Flag as Coverage Model Issue. |
| Register field is writable (RW)? | Direct write sequence. | Investigate indirect enable path. |

## Next Steps

Hand off to scenario generation. See
[End-to-End Coverage Closure Walkthrough](full_closure_walkthrough.md).

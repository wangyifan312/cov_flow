# Triage Policy

Coverage gap triage workflow and rules for the DV AI Coverage Closure Skill Pack.

## 6-Step Triage Workflow

| Step | Executor | Action | Output |
|------|----------|--------|--------|
| 1 | Skill/Claude | Read manifest, confirm scope and report_id | Task context established |
| 2 | MCP Tool | `cov_list_uncovered(scope, report_id, top_n)` | Top N uncovered gaps |
| 3 | MCP Tool | `cov_get_gap_detail` + `cov_get_coverpoint_source` per gap | Gap facts and evidence |
| 4 | Claude | Judge gap type, priority, whether more context is needed | Classification + priority + context plan |
| 5 | MCP Tool | Query spec/reg/tb/rtl as needed (context routing table) | Supporting evidence |
| 6 | Claude | Output triage report | Ranked table with classification, priority, recommended action |

## MCP Tool Call Order

```
cov_list_uncovered(project, scope, coverage_type, top_n)
    │
    ├── for each gap:
    │   ├── cov_get_gap_detail(project, gap_id)
    │   └── cov_get_coverpoint_source(project, gap_id)
    │
    └── per gap, as needed (based on classification):
        ├── spec_search(project, query)
        ├── reg_find_fields_affecting_feature(project, feature)
        ├── tb_get_existing_tests_for_feature(project, feature)
        └── rtl_find_signal(project, signal_name)
```

**Rules:**
- Always call `cov_list_uncovered` first — never query individual gaps without knowing the full uncovered list
- Always get gap detail + coverpoint source before attempting classification
- Only query spec/reg/tb/rtl after initial classification suggests they are needed (see context routing table in `gap_classification.md`)
- Each tool call must have a clear purpose; do not speculatively query all tools for every gap
- Use `coverage_type="all"` in `cov_list_uncovered` to include both functional and code coverage gaps in the triage scope; use specific type filters (e.g., `"line"`, `"fsm"`) when focusing on a single coverage category

## Triage Report Template

```markdown
# Coverage Gap Triage Report

Project: {project}
Regression: {regression_id}
Scope: {scope}
Coverage Type: {coverage_type}
Date: {date}

## Summary

- Total gaps analyzed: {N}
- P0: {count}, P1: {count}, P2: {count}, P3: {count}

## Ranked Gaps

| Rank | Gap ID | Type | Identifier | Classification | Priority | Recommended Action |
|------|--------|------|------------|----------------|----------|-------------------|
| 1    | GAP_XXXX | functional | {cg}.{cp}.{bin} | {class} | P0 | {action} |
| 2    | GAP_L001 | line | {file}:{line} | {class} | P1 | {action} |
| ...  | ... | ... | ... | ... | ... | ... |

## Evidence Detail

### GAP_XXXX
- **Coverage source**: {file}:{line_range}
- **Classification rationale**: {reasoning}
- **Related spec**: {spec_section} (if applicable)
- **Related register**: {register.field} (if applicable)
- **Existing tests**: {test_names} (if applicable)
- **Confidence**: {high/medium/low}
```

## Prohibited Operations

- Do not generate code during triage
- Do not mark gaps as waived
- Do not mark gaps as unreachable without formal evidence
- Do not read full RTL/FS/TB files — use bounded MCP tool queries only
- Do not skip gaps — every gap in the top N must be classified
- Do not assign priority without evidence supporting the classification

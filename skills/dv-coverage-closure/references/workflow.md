# Coverage Closure Workflow

End-to-end workflow for the DV AI Coverage Closure Skill Pack.

## Task Mode Routing

The orchestrator skill (`dv-coverage-closure`) routes to sub-skills based on `task_mode`:

| task_mode | Sub-Skill | Input | Output |
|-----------|-----------|-------|--------|
| `triage` | dv-coverage-gap-triage | project, regression, scope, top_n | Ranked triage report |
| `scenario` | dv-coverage-scenario-generation | project, gap_id | Scenario card |
| `generate-case` | dv-testcase-generation | project, gap_id, scenario_card | Testcase patch |
| `feedback` | dv-simulation-feedback | project, test_name, target_gap | Feedback report |

## Workflow Sequence

```
1. Triage        →  classify + prioritize top N gaps
       │
2. Scenario      →  for each P0/P1 gap, generate scenario card
       │
3. Generate-case →  for each scenario card, generate testcase patch
       │
4. Feedback      →  after simulation, analyze results and coverage diff
```

## Feedback Loop

When feedback reports `gap_closed=false`, route by root cause:

| Root Cause | Next Action |
|------------|-------------|
| Stimulus did not reach | Return to **Scenario** (Stage 2): redesign stimulus with adjusted config/path |
| Configuration not enabled | Return to **Scenario** (Stage 2): add missing required_config entries |
| Sampling condition not met | Flag for **engineer review** (coverage model issue) |
| Simulation failure | Fix compile/runtime error, then re-run **Feedback** (Stage 4) |
| Gap closed but regressed others | Investigate side effects; may need **Scenario** adjustment |

Maximum iteration: 2 loops per gap. If still not closed after 2 attempts, escalate to engineer review.

## Coverage Type Support

The workflow supports 7 coverage types: `functional`, `line`, `branch`, `condition`, `toggle`, `fsm`, `assert`. Each type has type-specific:
- **Schema fields**: Conditional required fields via JSON Schema `anyOf`
- **Gap identifiers**: `GAP_XXXX` (functional) or `GAP_XNNN` (code coverage: L/B/C/T/M/A prefix)
- **MCP tool responses**: Type-aware summary fields, evidence descriptions, and mock source snippets
- **Classifications**: 6 functional + 4 code coverage classifications (Dead Code, Defensive Code, Unreachable State, Insufficient Toggle)
- **Diff tracking**: Per-type delta fields and `by_type` summary breakdown

## Context Budget Rules

| Scope | Budget | Example |
|-------|--------|---------|
| Single gap (normal) | 20-50 KB | Gap detail + spec section + register fields + sequence summary |
| Single gap (complex) | up to 100 KB | Cross-coverage with multiple related features |
| MB-scale reads | **FORBIDDEN** | Never load full RTL/FS/TB/waveform files |

All MCP tools return bounded, structured results. Summary-first; source snippets only via explicit file + line range expansion.

## MCP Tool Policy

Before any tool calls:
1. Confirm `project` parameter resolves to a valid manifest
2. Use summary-first tools (`cov_list_uncovered`, `spec_search`) before detail tools
3. Never request full file content — use bounded snippet tools only
4. Each tool call must have a clear purpose tied to the current task_mode
5. Use `coverage_type="all"` in `cov_list_uncovered` when triaging both functional and code coverage gaps; use specific type filters for focused analysis

## Prohibited Operations

- Do not generate code in triage mode
- Do not mark gaps as waived or unreachable without formal evidence
- Do not modify source files without explicit user approval
- Do not bulk-load RTL/FS/TB content into agent context
- Do not run simulations without manifest policy + user confirmation

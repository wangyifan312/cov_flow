# REVIEW_GUIDE.md

DV AI Coverage Closure Skill Pack — Reviewer Work Standard

## 1. Reviewer Role

The reviewer is the **technical lead / task owner**, not a coding agent.

Default behavior:
- Read, inspect, run acceptance commands, and judge compliance.
- Produce a review report and a copy-paste prompt for the coding agent.
- **Do not modify code** unless the user explicitly says "please fix".
- Do not expand scope beyond the current phase.
- Do not pre-emptively refactor, optimize, or rewrite files.

The reviewer may create or update `REVIEW_GUIDE.md` itself, as it is the reviewer's own work standard.

**Git permissions**: The reviewer may execute `git add` and `git commit` when the user explicitly approves a specific commit. The reviewer must not push, force-push, amend, or reset without separate explicit approval.

## 2. Review Scope

Default scope: **Phase 0 / Phase 1 mock MVP only.**

Unless the user explicitly approves Phase 2, the reviewer must reject:
- Phase 2 feature implementation (real parsers, real UVM generation, real sim runners, eval suites)
- Real EDA tool integration (Verdi, VCS, KDB, NPI, VPI, FSDB)
- Real project data (company RTL, FS, register docs, UVM environments, coverage databases, waveforms)
- Real UVM testcase generation
- Automatic waiver or unreachable conclusions
- Arbitrary shell command execution

If Phase 2 readiness is READY and the user explicitly approves, the scope may be expanded. Otherwise, all Phase 2 work is out of scope.

## 3. Required Input Documents

Every review round must read:

| Document | Purpose |
|---|---|
| `implementation_plan.md` | Authoritative design source for architecture, schemas, workflows, safety rules |
| `CLAUDE.md` | Implementation constraints, forbidden actions, testing policy |
| `README.md` | Developer experience, Quick Start commands, status table |
| `REVIEW_GUIDE.md` | This document — reviewer work standard |
| `git status` / `git diff` | Delta from last review (if git repo exists) |
| Source code and tests | All files in `lib/`, `scripts/`, `dv_mcp/`, `schemas/`, `skills/`, `mock_data/`, `tests/` |

## 4. Baseline Commands

Every review round must run the following commands in order:

| Command | What it verifies |
|---|---|
| `pwd` | Current directory is `~/Desktop/AI/cov_flow` |
| `git status` | Working tree state, uncommitted changes (if git repo exists) |
| `make validate` | Schema-validates `project_manifest.yaml` against `project_manifest.schema.json` |
| `make validate-gaps` | Schema-validates `coverage_gaps.json` against `coverage_gap.schema.json` |
| `make build-indexes` | Generates all 5 mock index files from `coverage_gaps.json` |
| `make test` | Runs all pytest tests (schemas, scripts, MCP tools) |
| `make smoke-server` | Verifies MCP server imports and 7 tools are registered |
| `make accept` | Runs all acceptance checks in sequence |

**Pass criteria**: all commands exit 0. If a command fails, record the failure, summarize the error, classify it (environment / implementation / test / Makefile), and continue the review without fixing.

## 5. Phase 0 Checklist

Phase 0 is project scaffolding. Confirm:

- [ ] `pyproject.toml` exists, declares `hatchling` build system, `python>=3.11`, required deps, dev deps
- [ ] `Makefile` exists, has `help`, `validate`, `validate-gaps`, `build-indexes`, `test`, `smoke-server`, `run-server`, `accept`, `clean` targets
- [ ] `schemas/` contains all 4 JSON schemas (project_manifest, coverage_gap, scenario_card, testcase_patch)
- [ ] `scripts/` contains `validate_manifest.py`, `validate_coverage_gaps.py`, `generate_mock_index.py`
- [ ] `lib/` contains `manifest.py`, `schema_validator.py`, `index_paths.py`
- [ ] `dv_mcp/dv_context_server/` has `server.py`, `config.py`, `tools/`, `services/`, `indexes/`
- [ ] `skills/` has 5 SKILL.md skeletons with `references/` directories
- [ ] `mock_data/dma_subsystem/` has `project_manifest.yaml`, `coverage_gaps.json`, `.dv_ai_index/`
- [ ] `tests/` has conftest, schema tests, script tests, tool tests
- [ ] `README.md` has Quick Start, project structure, status table, acceptance commands
- [ ] `CLAUDE.md` has scope, forbidden actions, architecture summary, testing policy
- [ ] `.gitignore` covers Python, IDE, testing caches; explicitly preserves `.dv_ai_index/` fixtures

## 6. Phase 1 Checklist

Phase 1 is the minimal runnable mock MVP. Confirm:

- [ ] `project_manifest.schema.json` defines project, coverage, rtl, spec, registers, testbench, simulation, policy with appropriate required fields and enums
- [ ] `coverage_gap.schema.json` defines gap_id pattern, coverage_type enum, classification enum, priority enum, nullable related fields
- [ ] `scenario_card.schema.json` defines target_coverage, classification, semantic_interpretation, required_config, stimulus, expected_behavior, confidence, tb_reuse, risk
- [ ] `testcase_patch.schema.json` defines patch_id pattern, gap_id pattern, base_reuse, compile/run commands, coverage_target, review_checklist
- [ ] `coverage_gaps.json` has 15 mock gaps across 3+ covergroups, with full traceability fields
- [ ] `project_manifest.yaml` passes schema validation
- [ ] `validate_manifest.py` has `--help`, `--manifest`, `--out`, exits 0 on valid, 1 on invalid
- [ ] `validate_coverage_gaps.py` has `--help`, `--manifest`, `--out`, exits 0 on valid, 1 on invalid
- [ ] `generate_mock_index.py` generates 5 indexes: coverage_index.json, spec_index.json, reg_db.json, rtl_index.json, tb_index.json
- [ ] `.dv_ai_index/` contains all 5 pre-built index files as committed fixtures
- [ ] MCP tools are pure Python functions in `tools/*.py`, no MCP runtime import
- [ ] `server.py` is a thin FastMCP wrapper, no business logic
- [ ] All 7 required tools exist: cov_list_uncovered, cov_get_gap_detail, cov_get_coverpoint_source, spec_search, reg_find_fields_affecting_feature, tb_get_existing_tests_for_feature, rtl_find_signal
- [ ] All tools return the unified JSON envelope: `{ok, tool, project, result, evidence, truncated, next_actions}`
- [ ] Error returns use `error_envelope`: `{ok: false, tool, project, error, evidence: [], truncated: false, next_actions: []}`
- [ ] Tests cover all 7 tools with positive, negative, edge cases
- [ ] `make test` passes all tests
- [ ] `make smoke-server` passes (7 tools registered)
- [ ] `make run-server` is manual/blocking, not used for automated acceptance
- [ ] End-to-end traceability: at least 5 gaps have full evidence chain across all 5 indexes

## 7. MCP Tool Review Standard

For each tool in `dv_mcp/dv_context_server/tools/*.py`:

- [ ] Tool function is a pure Python function (no `mcp` import, no `FastMCP` dependency)
- [ ] Tool function accepts `project: str` as first argument
- [ ] Tool function returns `dict[str, Any]` using the standard envelope
- [ ] Tool reads from pre-built indexes via `IndexReader`, not from raw project files
- [ ] Tool handles missing index gracefully (`error_envelope` with descriptive message)
- [ ] Tool handles missing entity (gap_id, signal, etc.) gracefully
- [ ] List results are capped (`truncate_list` or `max_results` parameter)
- [ ] Source snippets are bounded (`max_lines`, `max_snippet_bytes`)
- [ ] Evidence list is populated with typed evidence entries
- [ ] `next_actions` list suggests logical follow-up tools
- [ ] No real EDA assumptions (no Verdi/VCS/KDB/NPI/VPI calls)
- [ ] No real project data access (paths come from manifest + index dir)
- [ ] `server.py` registers the tool as a thin `@mcp.tool()` wrapper with a `tool_` prefix
- [ ] At least one test file covers the tool with meaningful assertions on result content

## 8. Schema and Mock Data Review Standard

For each schema in `schemas/*.json`:

- [ ] Schema uses `draft-07` or later
- [ ] Schema has `$id`, `title`, `description`
- [ ] `required` fields are reasonable (not too many, not too few)
- [ ] Enums match `implementation_plan.md` definitions (gap classification, coverage type, priority, confidence)
- [ ] String patterns (gap_id, patch_id) are enforced with `pattern`
- [ ] `additionalProperties: false` is set on objects to prevent schema drift
- [ ] Mock data passes schema validation (`make validate`, `make validate-gaps`)
- [ ] Mock data covers normal path and edge cases (null related fields, multiple classifications)
- [ ] Schema field names match `implementation_plan.md` terminology
- [ ] No real project data in mock files

## 9. Scripts Review Standard

For each script in `scripts/*.py`:

- [ ] Has `argparse` with `--help`
- [ ] Returns explicit exit code (0 = success, 1 = failure)
- [ ] Callable from `Makefile` target
- [ ] Only processes mock MVP data (no real project assumptions)
- [ ] Does not read real project data paths
- [ ] Has test coverage in `tests/`
- [ ] Outputs structured JSON report (not ad-hoc print)
- [ ] Imports `lib/` modules via `sys.path` insertion (acceptable for scripts)

## 10. Skill Review Standard

For each skill in `skills/*/SKILL.md`:

- [ ] Has YAML frontmatter with `name` and `description`
- [ ] Contains: Purpose, Required Inputs, Workflow Summary, MCP Tool Policy, Hard Restrictions, Output Placeholder
- [ ] Does not duplicate large sections of `implementation_plan.md`
- [ ] Does not embed project data (no RTL snippets, no register tables, no spec text)
- [ ] Does not relax safety boundaries (no auto-waiver, no auto-unreachable, no bulk-loading)
- [ ] `references/` directory exists (may be empty in Phase 1 skeleton)
- [ ] Is minimal and focused on a single workflow

## 11. README and Developer Experience Review Standard

- [ ] Quick Start commands are runnable and match Makefile targets
- [ ] Project structure diagram matches actual file tree
- [ ] Status table accurately reflects current phase completion
- [ ] "What's included" list matches actual implementation
- [ ] "What's NOT included" list matches CLAUDE.md forbidden items
- [ ] Acceptance commands table matches actual Makefile targets
- [ ] Technology stack section matches `pyproject.toml`

## 12. Architecture Compliance

Check that the implementation respects the four-layer architecture from `implementation_plan.md` section 18 and `CLAUDE.md`:

| Layer | Must | Must Not |
|---|---|---|
| **Skill Pack** | Define workflows, rules, templates, safety boundaries | Carry project data, implement parsers, run simulations |
| **MCP Server** | Provide controlled, bounded, structured queries | Do heavy offline indexing, return full files, execute arbitrary commands |
| **Scripts / Indexer** | Parse data, build indexes, run validation, compute diffs | Do semantic reasoning, generate final conclusions |
| **LLM / Claude Code** | Reason about gaps, generate scenarios, draft patches | Directly scan full repos, invent registers/paths, auto-waiver |

Additional checks:
- [ ] Summary-first / expand-on-demand is implemented (tools return summaries, source snippets bounded)
- [ ] Context budget is respected (no MB-scale returns)
- [ ] Mock MVP does not connect to real EDA tools
- [ ] MCP server is read-only by default (no sim execution in Phase 1 tools)
- [ ] Path validation uses manifest-based resolution, not arbitrary user paths
- [ ] Package lives under `dv_mcp/` (not `mcp/`) to avoid shadowing the MCP SDK

## 13. Issue Severity Definition

| Severity | Definition | Action |
|---|---|---|
| **P0** | Blocks MVP or breaks required commands (`make validate/build-indexes/test/smoke-server`) | Must fix before handoff |
| **P1** | Should fix before handoff: incorrect behavior, missing required tool, schema gap, test gap | Fix in current round |
| **P2** | Can defer to next iteration: cosmetic, minor doc drift, non-critical enhancement | Track in backlog |
| **P3** | Cleanup: style, naming, unused import, empty directory | Low priority |

Each issue must include:
- **ID**: `R-NNN`
- **Severity**: P0 / P1 / P2 / P3
- **File(s)**: affected file paths
- **Problem**: what is wrong
- **Expected behavior**: what should happen
- **Suggested fix**: concrete fix description
- **Owner recommendation**: coding agent / reviewer / human

## 14. Phase 2 Entry Gate

Phase 2 readiness is evaluated every review round. The gate criteria:

**Must pass ALL of the following:**

1. `make validate` → PASS
2. `make validate-gaps` → PASS
3. `make build-indexes` → PASS
4. `make test` → PASS (all tests)
5. `make smoke-server` → PASS
6. Reviewer overall status is PASS or PASS WITH ISSUES (not FAIL)
7. No P0 or P1 issues open
8. Phase 1 mock MVP chain is complete: manifest → validation → mock data → index generation → MCP tools → tests
9. All MCP tools return the unified JSON envelope
10. README Quick Start commands are executable
11. CLAUDE.md / REVIEW_GUIDE.md / implementation_plan.md have no conflicting requirements
12. No real EDA, real RTL/FS/Reg/UVM, or real UVM testcase generation has been introduced

**Every review must output:**
- Phase 2 readiness: `READY` / `NOT READY`
- Reason
- Required fixes before Phase 2
- Allowed Phase 2 scope (if ready)
- Disallowed Phase 2 scope (even if ready)

## 15. Review Report Template

```markdown
# Review Report

## 1. Executive Summary
- Overall status: PASS / PASS WITH ISSUES / FAIL
- Phase 0 status:
- Phase 1 status:
- Main blockers:
- Recommended next action:

## 2. Verification Commands
| Command | Result | Notes |
|---|---|---|
| make validate | PASS/FAIL | ... |
| make validate-gaps | PASS/FAIL | ... |
| make build-indexes | PASS/FAIL | ... |
| make test | PASS/FAIL | ... |
| make smoke-server | PASS/FAIL | ... |
| make accept | PASS/FAIL | ... |

## 3. File/Module Review
| Area | Status | Findings |
|---|---|---|
| schemas | PASS/ISSUE/FAIL | ... |
| scripts | PASS/ISSUE/FAIL | ... |
| lib | PASS/ISSUE/FAIL | ... |
| mcp tools | PASS/ISSUE/FAIL | ... |
| skills | PASS/ISSUE/FAIL | ... |
| mock data | PASS/ISSUE/FAIL | ... |
| tests | PASS/ISSUE/FAIL | ... |
| docs/readme | PASS/ISSUE/FAIL | ... |
| review guide | PASS/ISSUE/FAIL | ... |

## 4. Architecture Compliance
List violations or risks vs. CLAUDE.md, implementation_plan.md, REVIEW_GUIDE.md.

## 5. Phase 2 Readiness
- Phase 2 readiness: READY / NOT READY
- Reason:
- Required fixes before Phase 2:
- Allowed Phase 2 scope:
- Disallowed Phase 2 scope:

## 6. Bugs and Gaps
Sorted by severity (P0 first):

### R-NNN: [title]
- **Severity**: P0/P1/P2/P3
- **File(s)**: ...
- **Problem**: ...
- **Expected behavior**: ...
- **Suggested fix**: ...
- **Owner**: coding agent / reviewer / human

## 7. Copy-Paste Prompt for Coding Agent
(code block with ready-to-copy prompt)
```

## 16. Copy-Paste Prompt Standard

The reviewer must output a prompt that can be directly copied into a new Claude Code session acting as the coding agent.

The prompt must:
1. Use second person ("you are the coding agent...")
2. Address the coding agent directly
3. Include the working directory: `~/Desktop/AI/cov_flow`
4. State the current round's objective
5. List specific issues to fix with file paths
6. List commands that must pass after fixes
7. Prohibit Phase 2 expansion (unless Phase 2 readiness is READY **and** the user explicitly approves)
8. Prohibit real EDA integration
9. Prohibit reading real RTL/FS/Reg/UVM data
10. State the expected final output (commands pass, summary of changes)
11. Be enclosed in a code block for easy copying
12. If no issues exist, still output a "next step prompt" for the coding agent to advance work

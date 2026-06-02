# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Purpose

This is an **implementation engineering repository** for the DV AI Coverage Closure Skill Pack — a company-internal solution that helps digital IC verification teams close coverage gaps using Claude Code Agent + Skills + MCP.

This is **not** a documentation-only repository. It contains Python code, JSON schemas, CLI scripts, an MCP server, mock data, skills, and tests.

## Authoritative Design Source

`implementation_plan.md` is the authoritative design document. All architecture decisions, module boundaries, workflow definitions, schema shapes, and safety rules must be traced back to it. When in doubt, read the relevant section of `implementation_plan.md` before writing code.

## Current Implementation Scope

**Phase 0 + Phase 1 + Phase 2 mock MVP + Phase 3 URG parser are complete.** Phase 4+ (real UVM generation, real sim integration) require explicit user approval before any work begins.

### Phase 0 — Project Scaffolding (Done)
- `pyproject.toml`, `Makefile`, `README.md`
- `schemas/` (all JSON schemas)
- `scripts/` (offline CLI tools)
- `lib/` (shared Python library)
- `dv_mcp/dv_context_server/` (MCP server skeleton and tools)
- `skills/` (skill definitions and references)
- `mock_data/` (mock project data and pre-built indexes)
- `tests/` (tests for schemas, scripts, and tools)

### Phase 1 — Minimal Runnable Mock MVP (Done)
- All JSON schemas (`project_manifest`, `coverage_gap`, `scenario_card`, `testcase_patch`)
- Mock project data (`mock_data/<project>/project_manifest.yaml`, `coverage_gaps.json`, mock index files)
- Validation scripts (`validate_manifest.py`, `validate_coverage_gaps.py`, `generate_mock_index.py`)
- MCP server (`server.py`) with 7 mock tools:
  - `cov_list_uncovered`, `cov_get_gap_detail`, `cov_get_coverpoint_source`
  - `spec_search`, `reg_find_fields_affecting_feature`
  - `tb_get_existing_tests_for_feature`, `rtl_find_signal`
- Tests for schemas, scripts, and mock tools
- `make validate`, `make build-indexes`, `make test`, `make smoke-server` all work under mock MVP
- `make run-server` is a manual blocking command; use `make smoke-server` for automated verification

### Phase 2 — Skills, Sim Tools, Eval Suite (Done)
- **Phase 2a**: 8 skill reference documents (triage/closure workflows), 2 validation scripts (scenario card, patch metadata), eval skeleton (YAML structure + 1 case)
- **Phase 2b**: 4 new MCP sim tools (`sim_run_targeted_test`, `sim_get_test_result`, `sim_search_log`, `cov_get_coverage_diff`), static patch check script, audit logging service, mock simulation data, 2 eval cases
- **Phase 2c**: Eval runner dry-run mode (`run_eval.py`), 7 additional skill reference documents completing all 5 sub-skill workflows
- **Phase 2 收尾**: `pip install -e ".[dev]"` fix (hatch build targets), `.mcp.json` Claude Code MCP config, ruff 95→0 issues, mypy 18→0 errors, 4th eval case (`generate_case_0001.yaml` completing all 4 task_modes), 3 example walkthroughs (triage, full closure, MCP setup)
- **Phase 2d**: Code coverage extension — 7 coverage types (functional, line, branch, condition, toggle, fsm, assert), unified schema with `anyOf` conditional required fields, type-aware MCP tools and diff computation, 12 new mock gaps (27 total), 4 new classifications (10 total), 35 new tests (181 total), 2 new eval cases (6 total)
- **Total**: 181 tests, 11 MCP tools, 15 skill reference documents, 6 eval cases, ruff 0, mypy 0, make accept clean
- All sim tools are **mock/dry-run only** — no real shell execution, no real coverage parsing

### Phase 3 — Real URG Coverage Report Parser (Done)
- **URG HTML parser library** (`lib/urg_parser/`): parses Synopsys VCS URG reports (O-2018.09-SP2)
  - `session.py` — session.xml metadata and per-type metrics
  - `structure.py` — modlist.html and groups.html structure mapping
  - `functional.py` — grp*.html functional coverage (covergroup/coverpoint/bin)
  - `code_coverage.py` — mod*.html code coverage (line/branch/condition/toggle/fsm/assert)
  - `gap_assembler.py` — gap ID assignment, path normalization, schema filtering
  - `index_builder.py` — coverage_index.json and coverage_gaps.json output
- **CLI script** (`scripts/build_coverage_index.py`): `--manifest PATH` orchestrates full parse pipeline
- **Demo project** (`mock_data/axi2ahb/`): real AXI2AHB bridge UVM verification project
  - 982 schema-compliant gaps across all 7 coverage types
  - Synopsys library file filtering (`/opt/synopsys/` paths excluded)
  - Source file path normalization (absolute → relative)
- **MCP integration**: coverage_index.json includes `gaps` field compatible with existing MCP tools
- **Makefile target**: `make build-real-index`
- All sim tools remain **mock/dry-run only** — no real shell execution

### Phase 4+ — Real Integration (Out of Scope, Requires Approval)
- Real UVM testcase generation
- Real simulation tool integration (VCS, Verdi, etc.)
- Real eval suite LLM execution
- Multi-project support

## What Is Allowed

- Create and modify Python code, JSON schemas, YAML manifests, CLI scripts, MCP server code, mock data, mock indexes, skill markdown, tests, `README.md`, `Makefile`, `pyproject.toml`.
- Use `.venv/` for Python dependency isolation.
- Run `pytest`, `ruff`, `make` targets to verify changes.
- Run `make build-real-index` after modifying URG parser code or adding new URG report data.

## What Is Forbidden

These rules are non-negotiable. Phase 2 mock implementations (dry-run, stub data, no real tool calls) are allowed; real tool integration beyond the URG parser is not.

1. **No real EDA tool integration.** Do not implement real Verdi, VCS, KDB, NPI, VPI, FSDB, or any other EDA tool interfaces. All EDA-related capabilities must be implemented as adapter/stub only.
2. **No real project data.** Do not read, assume, or generate real company RTL, FS, register documents, UVM environments, real coverage databases, or waveforms.
3. **No bulk-loading.** Do not bulk-load RTL/FS/TB content into the Agent context. MCP tools must return bounded, structured results.
4. **No automatic waivers or formal conclusions.** Do not implement automatic waiver generation or formal unreachable conclusions. Those require human sign-off.
5. **No auto-commits.** Neither the coding agent nor the review Claude may commit code without explicit user instruction. The review Claude may execute `git add` and `git commit` when the user explicitly approves a specific commit.
6. **No Phase 4+ implementation without approval.** Do not implement real UVM testcase generation, real simulation runners, or eval suites with LLM execution unless the user explicitly approves Phase 4+ work.
7. **No complex frameworks.** Use stdlib + the declared dependencies only (see `pyproject.toml`). Python 3.11+.

## Implementation Principles

When deciding where to put a capability, follow this split (from `implementation_plan.md` §18):

| Layer | Responsibility | Examples |
|---|---|---|
| **Scripts / Indexer** | Deterministic facts, offline index building | `build_*_index.py`, `validate_manifest.py`, `coverage_diff.py` |
| **MCP tools** | Controlled, bounded, structured query interface | `cov_get_gap_detail`, `spec_search`, `rtl_find_signal` |
| **Claude Code / LLM** | Semantic reasoning, scenario generation, report writing | Gap classification, scenario card authoring, feedback interpretation |
| **Skills** | Workflow rules, output templates, context budgets, safety boundaries | `SKILL.md`, `references/*.md` |

## Testing Policy

- Run `pytest` after modifying code in `lib/`, `scripts/`, `dv_mcp/`, or `tests/`.
- Run `make validate` after modifying schemas or mock manifests.
- Run `make smoke-server` after modifying MCP server code or tools.
- Run `make lint` and `make typecheck` after any Python code change — ruff 0 and mypy 0 are required.
- Run `scripts/run_eval.py --eval-dir evals/ --dry-run` after modifying eval YAML files or the eval runner.
- Run `make build-real-index` after modifying URG parser code to verify parsing pipeline.
- If a change cannot be tested immediately (e.g., missing dependency), state the reason explicitly rather than skipping silently.

## Architecture Summary

Four layers, strict separation:

1. **Skill Pack** — workflows, rules, output templates, safety boundaries. **Never** bundles project data.
2. **DV Context MCP Server** — controlled query tools over project indexes. Summary-first; source snippets only via explicit `file + line range` expansion. **Note**: the server package lives under `dv_mcp/` (not `mcp/`) to avoid shadowing the installed `mcp` SDK package.
3. **Project Context Indexer** (offline scripts) — converts raw project data into structured indexes before Agent execution.
4. **Project Manifest** — YAML declaring data locations, index paths, command templates, and policy switches.

### Coverage Types and Gap IDs

7 coverage types supported: `functional`, `line`, `branch`, `condition`, `toggle`, `fsm`, `assert`.
Gap ID format: `GAP_XXXX` (functional, 4-digit) or `GAP_XNNN` (code coverage, letter prefix: L=line, B=branch, C=condition, T=toggle, M=FSM, A=assert).
Schema uses JSON Schema `anyOf` for conditional required fields per type.

## Context Budget Rules

Single-gap context: normal 20–50 KB, complex gaps up to 100 KB. MB-scale reads of RTL/FS/UVM/waveform data are forbidden.

## Gap Classification

Gaps are classified into two groups:
- **Functional coverage**: Missing Stimulus, Config Missing, Constraint Too Tight, Coverage Model Issue, Monitor Sampling Issue, Unreachable Candidate
- **Code coverage**: Dead Code, Defensive Code, Unreachable State, Insufficient Toggle

Each classification drives a different context retrieval strategy. Code coverage types apply to line, branch, condition, toggle, FSM, and assertion coverage gaps.

## Security Boundaries

- MCP server is read-only by default; simulation execution and file writes require manifest policy + user confirmation.
- All paths validated against project root allowlist; no path traversal.
- Shell commands must come from manifest command templates; no arbitrary command injection.
- Source snippet returns capped by line range and max byte size.
- Tool calls should be audit-logged (user, project, tool, argument hash, timestamp, result size).

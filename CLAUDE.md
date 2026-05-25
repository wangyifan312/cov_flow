# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Purpose

This is an **implementation engineering repository** for the DV AI Coverage Closure Skill Pack — a company-internal solution that helps digital IC verification teams close coverage gaps using Claude Code Agent + Skills + MCP.

This is **not** a documentation-only repository. It contains Python code, JSON schemas, CLI scripts, an MCP server, mock data, skills, and tests.

## Authoritative Design Source

`implementation_plan.md` is the authoritative design document. All architecture decisions, module boundaries, workflow definitions, schema shapes, and safety rules must be traced back to it. When in doubt, read the relevant section of `implementation_plan.md` before writing code.

## Current Implementation Scope

**Phase 0 + Phase 1 + Phase 2 mock MVP are complete.** Phase 3 (real EDA integration) and beyond require explicit user approval before any work begins.

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
- **Total**: 146 tests, 11 MCP tools, 15 skill reference documents, 3 eval cases, make accept clean
- All sim tools are **mock/dry-run only** — no real shell execution, no real coverage parsing

### Phase 3+ — Real Integration (Out of Scope, Requires Approval)
- Real URG HTML/XML coverage report parsing
- Real UVM testcase generation
- Real simulation tool integration (VCS, Verdi, etc.)
- Real eval suite LLM execution
- Multi-project support

## What Is Allowed

- Create and modify Python code, JSON schemas, YAML manifests, CLI scripts, MCP server code, mock data, mock indexes, skill markdown, tests, `README.md`, `Makefile`, `pyproject.toml`.
- Use `.venv/` for Python dependency isolation.
- Run `pytest`, `ruff`, `make` targets to verify changes.

## What Is Forbidden

These rules are non-negotiable. Phase 2 mock implementations (dry-run, stub data, no real tool calls) are allowed; real tool integration is not.

1. **No real EDA tool integration.** Do not implement real Verdi, VCS, KDB, NPI, VPI, FSDB, or any other EDA tool interfaces. All EDA-related capabilities must be implemented as adapter/stub only.
2. **No real project data.** Do not read, assume, or generate real company RTL, FS, register documents, UVM environments, real coverage databases, or waveforms.
3. **No bulk-loading.** Do not bulk-load RTL/FS/TB content into the Agent context. MCP tools must return bounded, structured results.
4. **No automatic waivers or formal conclusions.** Do not implement automatic waiver generation or formal unreachable conclusions. Those require human sign-off.
5. **No auto-commits.** Neither the coding agent nor the review Claude may commit code without explicit user instruction. The review Claude may execute `git add` and `git commit` when the user explicitly approves a specific commit.
6. **No Phase 3+ implementation without approval.** Do not implement real coverage report parsers, real UVM testcase generation, real simulation runners, or eval suites with LLM execution unless the user explicitly approves Phase 3 work.
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
- Run `scripts/run_eval.py --eval-dir evals/ --dry-run` after modifying eval YAML files or the eval runner.
- If a change cannot be tested immediately (e.g., missing dependency), state the reason explicitly rather than skipping silently.

## Architecture Summary

Four layers, strict separation:

1. **Skill Pack** — workflows, rules, output templates, safety boundaries. **Never** bundles project data.
2. **DV Context MCP Server** — controlled query tools over project indexes. Summary-first; source snippets only via explicit `file + line range` expansion. **Note**: the server package lives under `dv_mcp/` (not `mcp/`) to avoid shadowing the installed `mcp` SDK package.
3. **Project Context Indexer** (offline scripts) — converts raw project data into structured indexes before Agent execution.
4. **Project Manifest** — YAML declaring data locations, index paths, command templates, and policy switches.

## Context Budget Rules

Single-gap context: normal 20–50 KB, complex gaps up to 100 KB. MB-scale reads of RTL/FS/UVM/waveform data are forbidden.

## Gap Classification

Gaps are classified into: Missing Stimulus, Config Missing, Constraint Too Tight, Coverage Model Issue, Monitor Sampling Issue, Unreachable Candidate. Each drives a different context retrieval strategy.

## Security Boundaries

- MCP server is read-only by default; simulation execution and file writes require manifest policy + user confirmation.
- All paths validated against project root allowlist; no path traversal.
- Shell commands must come from manifest command templates; no arbitrary command injection.
- Source snippet returns capped by line range and max byte size.
- Tool calls should be audit-logged (user, project, tool, argument hash, timestamp, result size).

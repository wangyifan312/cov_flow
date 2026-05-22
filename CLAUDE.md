# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Purpose

This is an **implementation engineering repository** for the DV AI Coverage Closure Skill Pack — a company-internal solution that helps digital IC verification teams close coverage gaps using Claude Code Agent + Skills + MCP.

This is **not** a documentation-only repository. It contains Python code, JSON schemas, CLI scripts, an MCP server, mock data, skills, and tests.

## Authoritative Design Source

`implementation_plan.md` is the authoritative design document. All architecture decisions, module boundaries, workflow definitions, schema shapes, and safety rules must be traced back to it. When in doubt, read the relevant section of `implementation_plan.md` before writing code.

## Current Implementation Scope

**Only Phase 0 and Phase 1 mock MVP are in scope.** Phase 2 and beyond are explicitly out of scope.

### Phase 0 — Project Scaffolding
- `pyproject.toml`, `Makefile`, `README.md`
- `schemas/` (all JSON schemas)
- `scripts/` (offline CLI tools)
- `lib/` (shared Python library)
- `mcp/dv_context_server/` (MCP server skeleton and tools)
- `skills/` (skill definitions and references)
- `mock_data/` (mock project data and pre-built indexes)
- `examples/` (usage examples)
- `tests/` (tests for schemas, scripts, and tools)

### Phase 1 — Minimal Runnable Mock MVP
- All JSON schemas (`project_manifest`, `coverage_gap`, `scenario_card`, `testcase_patch`)
- Mock project data (`mock_data/<project>/project_manifest.yaml`, `coverage_gaps.json`, mock index files)
- Validation scripts (`validate_manifest.py`, `validate_coverage_gaps.py`, `generate_mock_index.py`)
- MCP server (`server.py`) with mock tools:
  - `cov_list_uncovered`, `cov_get_gap_detail`, `cov_get_coverpoint_source`
  - `spec_search`, `reg_find_fields_affecting_feature`
  - `tb_get_existing_tests_for_feature`, `rtl_find_signal`
- Tests for schemas, scripts, and mock tools
- `make validate`, `make build-indexes`, `make test`, `make smoke-server` must all work under mock MVP
- `make run-server` is a manual blocking command; use `make smoke-server` for automated verification

## What Is Allowed

- Create and modify Python code, JSON schemas, YAML manifests, CLI scripts, MCP server code, mock data, mock indexes, skill markdown, tests, `README.md`, `Makefile`, `pyproject.toml`.
- Use `.venv/` for Python dependency isolation.
- Run `pytest`, `ruff`, `make` targets to verify changes.

## What Is Forbidden

These rules are non-negotiable during Phase 0/1:

1. **No real EDA tool integration.** Do not implement real Verdi, VCS, KDB, NPI, VPI, FSDB, or any other EDA tool interfaces. All EDA-related capabilities must be implemented as adapter/stub only.
2. **No real project data.** Do not read, assume, or generate real company RTL, FS, register documents, UVM environments, real coverage databases, or waveforms.
3. **No bulk-loading.** Do not bulk-load RTL/FS/TB content into the Agent context. MCP tools must return bounded, structured results.
4. **No automatic waivers or formal conclusions.** Do not implement automatic waiver generation or formal unreachable conclusions. Those require human sign-off.
5. **No auto-commits.** Do not commit code without explicit user instruction.
6. **No Phase 2 implementation.** Do not implement real coverage report parsers, real UVM testcase generation, real simulation runners, or eval suites.
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

- Run `pytest` after modifying code in `lib/`, `scripts/`, `mcp/`, or `tests/`.
- Run `make validate` after modifying schemas or mock manifests.
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

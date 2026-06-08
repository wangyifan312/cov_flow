# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Purpose

This is an **implementation engineering repository** for the DV AI Coverage Closure Skill Pack — a company-internal solution that helps digital IC verification teams close coverage gaps using Claude Code Agent + Skills + MCP.

This is **not** a documentation-only repository. It contains Python code, JSON schemas, CLI scripts, an MCP server, mock data, skills, and tests.

## Authoritative Design Source

`implementation_plan.md` is the authoritative design document. All architecture decisions, module boundaries, workflow definitions, schema shapes, and safety rules must be traced back to it. When in doubt, read the relevant section of `implementation_plan.md` before writing code.

**Phase numbering note**: The phase definitions in `implementation_plan.md` §13 are the original design plan. The project has redefined phases during actual implementation:
- Phase 0: Project scaffolding
- Phase 1: Mock MVP (schemas, mock data, MCP tools, tests)
- Phase 2: Skills, eval dry-run, validation scripts
- Phase 3: URG HTML coverage report parser
- Phase 4: Source resolver + Project registry + EDA adapter skeleton
- Phase 5a: TB Index Builder + MCP integration
- Phase 5b: Real simulation execution infrastructure

For current phase status, refer to the README.md status table. The `implementation_plan.md` remains authoritative for architecture, module boundaries, and schema definitions, but not for phase numbering.

## Current Implementation Scope

**Phase 0 through Phase 5b are complete.** Phase 6+ (eval LLM execution, multi-project) require explicit user approval before any work begins.

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
- **Phase 2d**: Code coverage extension — 7 coverage types (functional, line, branch, condition, toggle, fsm, assert), unified schema with `anyOf` conditional required fields, type-aware MCP tools and diff computation, 12 new mock gaps (27 total), 4 new classifications (10 total), 35 new tests, 2 new eval cases (6 total)
- **Phase 3**: URG HTML parser — 982 real gaps from axi2ahb URG report
- **Phase 4**: Source resolver + registry + EDA adapters — 90 new tests (271 total), 11 MCP tools
- **Phase 5a**: TB Index Builder + MCP integration — 13 MCP tools, 414 tests
- **Phase 5b**: Real simulation execution infrastructure — SimExecutor + SimLogParser + UrgRunner, mock/real dual-mode, 521 tests
- **Total**: 13 MCP tools, 15 skill reference documents, 6 eval cases, ruff 0, mypy 0, make accept clean
- Phase 5b adds real subprocess execution (VCS/URG) via manifest `mode: real` with security boundaries (test name validation, path traversal rejection, shlex + shell=False, cwd lock, timeout)

### Phase 3 — Real URG Coverage Report Parser (Done)
- **URG HTML parser library** (`lib/urg_parser/`): parses Synopsys VCS URG reports (O-2018.09-SP2)
  - `session.py` — session.xml metadata and per-type metrics
  - `structure.py` — modlist.html and groups.html structure mapping
  - `functional.py` — grp*.html functional coverage (covergroup/coverpoint/bin)
  - `code_coverage.py` — mod*.html code coverage (line/branch/condition/toggle/fsm/assert)
  - `gap_assembler.py` — gap ID assignment, path normalization, schema filtering
  - `index_builder.py` — coverage_index.json and coverage_gaps.json output
- **CLI script** (`scripts/build_coverage_index.py`): `--manifest PATH` orchestrates full parse pipeline
- **Demo project** (`mock_data/axi2ahb/`): sample AXI2AHB bridge URG report (public/sanitized demo data)
  - 982 schema-compliant gaps across all 7 coverage types
  - Synopsys library file filtering (`/opt/synopsys/` paths excluded)
  - Source file path normalization (absolute → relative)
- **MCP integration**: coverage_index.json includes `gaps` field compatible with existing MCP tools
- **Makefile target**: `make build-real-index`
- All sim tools support **mock/dry-run mode** (default) and **real mode** (manifest `mode: real`) — real mode executes VCS/URG subprocess via SimExecutor with security boundaries

### Phase 4 — Source Resolver + Project Registry + EDA Adapters (Done)
- **Bounded Source Snippet Resolver** (`lib/source_resolver.py`): reads real SV source snippets with security boundaries (path traversal protection, allowlist, max_lines/max_bytes)
- **Project Registry** (`lib/project_registry.py`): resolves project names to manifest paths via `projects.yaml` or `COV_FLOW_PROJECTS` env var
- **EDA Adapter Skeleton** (`lib/eda_adapters/`): abstract base class + MockVerdiAdapter + MockVCSAdapter (stub data, no real EDA integration)
- **Contract Tests** (`tests/test_tool_contracts.py`): envelope format validation for all 11 MCP tools
- **Large Dataset Tests** (`tests/test_large_dataset.py`): truncation and context budget validation with axi2ahb 982-gap dataset
- **`cov_get_coverpoint_source` upgraded**: now returns `source_mode: "real"` when reading from coverage_model_root, falls back to `source_mode: "mock_fallback"` when file unavailable
- **MCP tools support project name input**: `cov_list_uncovered(project="dma_subsystem")` works without manifest path

### Phase 5a — TB Index Builder + MCP Integration (Done)
- **WP-1 SV Parser + TB Index Builder** (Done): `lib/sv_parser.py` (generic regex-based SV parser, 13 patterns, 12 public functions), `scripts/build_tb_index.py` (manifest-driven CLI indexer), 47 tests
- **WP-2 MCP TB Tool Integration** (Done): `tb_get_existing_tests_for_feature` upgraded with scope filter and api_methods display
- **WP-3 Gap→TB Semantic Bridge** (Done): `tb_find_tests_for_gap` — auto-extracts semantic keywords from coverpoint/bin names, searches TB index, assesses coverage; `lib/semantic_matcher.py` module; 44 tests
- **WP-4 Targeted Testcase Generation** (Done): `tb_read_source` MCP tool (4 component types: sequence/test/base_test/env, SourceResolver security boundaries, max_lines=1000/max_bytes=64KB); generic testcase generation prompt (`prompts/testcase_gen_generic_prompt.md`); axi2ahb GAP_0006 validation (wrap8 targeted sequence generated)
- **Total**: 13 MCP tools, 414 tests, 5 prompts, ruff 0, mypy 0

### Phase 5b — Real Simulation Execution Infrastructure (Done)
- **WP-1 Foundation Libraries** (Done): `lib/sim_executor.py` (subprocess executor with security: test name validation, path traversal rejection, shlex.split + shell=False, cwd locked to project_root, timeout), `lib/sim_log_parser.py` (VCS/UVM log parsing with priority-based pass/fail detection), `lib/urg_runner.py` (URG report generation + parsing pipeline), 102 tests
- **WP-2 Manifest Schema Extension** (Done): 7 new optional fields in `simulation` block (`mode: mock|real`, `urg_cmd_template`, `urg_binary`, `urg_timeout_seconds`, `timeout_seconds`, `results_root`, `vdb_dir_template`), 4 convenience properties in `lib/manifest.py`, real-mode manifest template (`project_manifest_real.yaml.example`)
- **WP-3 MCP Tool Upgrades** (Done): 4 sim tools (`sim_run_targeted_test`, `sim_get_test_result`, `sim_search_log`, `cov_get_coverage_diff`) support real mode branching via `manifest.sim_mode`, mock mode unchanged, `_sim_result_to_dict` helper for SimResult serialization
- **WP-4 CLI Script Upgrade** (Done): `scripts/sim_runner.py --real` flag, mode check (rejects mock manifests), test name/seed validation, SimExecutor pipeline execution, human-readable summary, exit codes (0=pass, 1=run fail, 2=compile fail)
- **WP-5 Tests** (Done): `tests/test_sim_tools_real_mode.py` (21 tests covering all 4 MCP tools in real mode), added tests to existing files
- **Total**: 13 MCP tools, 521 tests, ruff 0, mypy 0
- Mock/real dual-mode: `mode: mock` (default) returns fake data, `mode: real` executes VCS subprocess via SimExecutor

### Phase 6+ — Out of Scope (Requires Approval)
- Real eval suite LLM execution
- Multi-project support (beyond registry lookup)

## What Is Allowed

- Create and modify Python code, JSON schemas, YAML manifests, CLI scripts, MCP server code, mock data, mock indexes, skill markdown, tests, `README.md`, `Makefile`, `pyproject.toml`.
- Use `.venv/` for Python dependency isolation.
- Run `pytest`, `ruff`, `make` targets to verify changes.
- Run `make build-real-index` after modifying URG parser code or adding new URG report data.

## What Is Forbidden

These rules are non-negotiable. Phase 2 mock implementations (dry-run, stub data, no real tool calls) are allowed; real tool integration beyond the URG parser, SourceResolver, TB Indexer, and SimExecutor is not.

1. **No real EDA tool integration.** Do not implement real Verdi, VCS, KDB, NPI, VPI, FSDB, or any other EDA tool interfaces. All EDA-related capabilities must be implemented as adapter/stub only.
2. **No real project data.** Do not read, assume, or generate real company RTL, FS, register documents, UVM environments, real coverage databases, or waveforms.
3. **No bulk-loading.** Do not bulk-load RTL/FS/TB content into the Agent context. MCP tools must return bounded, structured results.
4. **No automatic waivers or formal conclusions.** Do not implement automatic waiver generation or formal unreachable conclusions. Those require human sign-off.
5. **No auto-commits.** Neither the coding agent nor the review Claude may commit code without explicit user instruction. The review Claude may execute `git add` and `git commit` when the user explicitly approves a specific commit.
6. **No Phase 6+ implementation without approval.** Do not implement eval suites with LLM execution or multi-project support unless the user explicitly approves Phase 6+ work.
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

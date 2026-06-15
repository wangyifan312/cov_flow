# DV AI Coverage Closure Skill Pack

A reusable AI-assisted coverage closure toolkit for digital IC verification teams, built on Claude Code Agent + Skills + MCP Server.

## Overview

This project helps verification engineers close coverage gaps through:
- **Coverage Triage** - classify and prioritize uncovered items
- **Scenario Generation** - generate structured scenario cards from coverage gaps
- **Testcase Generation** - draft UVM sequence/test patches based on existing templates
- **Simulation Feedback** - analyze simulation results and coverage diffs

See `implementation_plan.md` for the full design document.

## Quick Start

```bash
# Install dependencies
pip install -e ".[dev]"

# Validate the sample project manifest
make validate

# Validate coverage gaps data
make validate-gaps

# Build all indexes from sample data
make build-indexes

# Lint and typecheck
make lint
make typecheck

# Run tests
make test

# Smoke-test the MCP server (non-blocking)
make smoke-server

# Run full acceptance suite
make accept

# Start the MCP server (manual, blocking)
make run-server
```

## Documentation

| Document | For Whom | What |
|----------|----------|------|
| [Getting Started](docs/getting_started.md) | New users | Clone → install → first use → real project |
| [MCP Tool Reference](docs/mcp_tool_reference.md) | All users | 26 tools: parameters, returns, chaining guide |
| [Prompt Templates](docs/user_prompt_templates.md) | All users | 25 copy-paste prompts for each workflow |
| [Server Setup Guide](docs/server_setup_guide.md) | Platform team | VCS integration, real-mode deployment |
| [Quick Start Checklist](docs/quick_start_checklist.md) | Platform team | Step-by-step server migration |
| [Project Structure](docs/project_structure.md) | All users | Directory layout and file purposes |
| [Project Onboarding](docs/project_onboarding.md) | DV engineers | What to prepare + step-by-step project integration |
| [Examples](examples/README.md) | All users | 3 walkthroughs: triage, full closure, MCP setup |

## Server Deployment

For production use with real VCS simulation and Claude Code integration:

```bash
# 1. Clone on server
git clone https://github.com/your-org/cov_flow.git
cd cov_flow

# 2. Install dependencies
pip install -e ".[dev]"

# 3. Set environment variables
export AXI2AHB_ROOT=/path/to/AXI2AHB-Lite-Bridge-UVM-Verification

# 4. Configure manifest for real simulation
# Edit mock_data/axi2ahb/project_manifest.yaml to set your VCS command templates

# 5. Build real indexes
make build-real-tb-index

# 6. Configure MCP for Claude Code
cp .mcp.json.example .mcp.json

# 7. Start Claude Code
claude
```

See [docs/server_setup_guide.md](docs/server_setup_guide.md) for detailed instructions and [docs/quick_start_checklist.md](docs/quick_start_checklist.md) for step-by-step verification.

## Project Structure

```
cov_flow/
├── .mcp.json.example      MCP client configuration template (copy to .mcp.json)
├── projects.yaml          Project name → manifest path registry
├── schemas/              JSON Schema definitions for all outputs
├── scripts/              Offline indexer CLIs and validators
├── lib/                  Shared Python library (manifest, URG parser, source resolver, registry, EDA adapters, sim executor, log parser)
├── dv_mcp/               DV Context MCP Server (FastMCP-based)
│   └── dv_context_server/
│       ├── server.py          FastMCP entry point (thin wrapper)
│       ├── tools/             Pure Python tool functions (no MCP dependency)
│       ├── services/          Project loading, evidence, summarization
│       └── indexes/           JSON index readers
├── skills/               Skill Pack (SKILL.md + references for each workflow)
├── docs/                 Server setup and usage documentation
├── mock_data/            Sample project data
│   ├── dma_subsystem/    Sample DMA project (Phase 0-2)
│   │   ├── project_manifest.yaml
│   │   ├── coverage_gaps.json
│   │   └── .dv_ai_index/      Pre-built indexes (committed as fixtures)
│   └── axi2ahb/          Sample AXI2AHB URG report (sanitized demo data, Phase 3)
│       ├── project_manifest.yaml
│       ├── urg_report/         URG HTML coverage report
│       ├── coverage_gaps.json  Parsed gaps (982 gaps, 7 types)
│       └── .dv_ai_index/       Generated coverage index
├── examples/             End-to-end usage walkthroughs
├── evals/                Eval YAML cases (6 cases: triage, scenario, generate-case, feedback, code coverage)
└── tests/                Tests for schemas, scripts, and tools
```

## Current Status

**Phase 6 complete** - Full MCP tool coverage with source-backed indexers and simulation history.

| Phase | Scope | Status |
|-------|-------|--------|
| Phase 0 | Project scaffolding + Manifest schema | **Done** |
| Phase 1 | Schemas + Sample data + MCP tools + Tests | **Done** |
| Phase 2a | Skill references + Validation scripts + Eval skeleton | **Done** |
| Phase 2b | Sim tools + Coverage diff + Static patch check + Evals | **Done** |
| Phase 2c | Eval runner + Remaining skill references | **Done** |
| Phase 2d | Code coverage extension (7 types, 27 gaps) | **Done** |
| Phase 3 | Real URG HTML coverage report parser + MCP integration | **Done** |
| Phase 4 | Source resolver + Project registry + EDA adapter skeleton | **Done** |
| Phase 5a | TB Index Builder + MCP TB tool integration | **Done** |
| Phase 5b | Real simulation execution infrastructure | **Done** |
| Phase 6A | 8 quick-win MCP tools (spec/reg/rtl/tb lookups) | **Done** |
| Phase 6B | 3 source-file indexers + 2 RTL tools | **Done** |
| Phase 6C | Simulation history indexer + feedback schema | **Done** |
| Phase 6D | 2 final stubs (sequence snippet + wave check) | **Done** |

### What's included in Phase 1 Sample MVP

- **4 JSON schemas**: project_manifest, coverage_gap, scenario_card, testcase_patch
- **15 coverage gaps** across 5 covergroups (5 fully traceable end-to-end)
- **5 pre-built indexes**: coverage, spec, register, RTL, TB
- **7 MCP tools** (pure Python, no MCP runtime needed for testing):
  - `cov_list_uncovered`, `cov_get_gap_detail`, `cov_get_coverpoint_source`
  - `spec_search`
  - `reg_find_fields_affecting_feature`
  - `tb_get_existing_tests_for_feature`
  - `rtl_find_signal`
- **82 tests** covering schemas, scripts, and all tools
- **5 SKILL.md definitions** for each workflow (orchestrator + 4 sub-skills)

### What's included in Phase 2a (initial stage)

- **8 skill reference documents**: workflow, gap classification, scenario card schema guide, testcase generation rules, review checklist, triage policy, gap priority rules, unreachable heuristics
- **2 validation scripts**: validate_scenario_card.py, validate_patch_metadata.py
- **1 eval skeleton**: README.md + triage_gap_0001.yaml
- **14 new tests** (total: 96)

### What's included in Phase 2b

- **1 static patch check script**: static_patch_check.py with 6 deterministic checks
- **2 simulation scripts**: sim_runner.py (real execution with --dry-run), coverage_diff.py (before/after DB comparison)
- **4 new MCP tools** (total: 11):
  - `sim_run_targeted_test`, `sim_get_test_result`, `sim_search_log`
  - `cov_get_coverage_diff`
- **Audit logging service**: 5-field audit records (user, project, tool, arg_hash, timestamp, result_size)
- **Safety field** for simulation execution: policy_checked, confirmed, command_template_used
- **Simulation data**: coverage_db_before.json, coverage_db_after.json, sim_logs/
- **2 eval cases**: scenario_gen_0001.yaml, simulation_feedback_0001.yaml
- **Manifest extensions**: simulation_config, policy, get_simulation_command
- **20+ new tests** (total: ≥116)

### What's included in Phase 2c

- **Eval runner** (scripts/run_eval.py): dry-run YAML structure validator with 6 checks
- **7 skill reference documents** completing all workflow references:
  - Scenario generation: scenario_patterns.md, protocol_scenario_templates.md
  - Testcase generation: uvm_generation_rules.md, patch_rules.md, compile_check_rules.md
  - Simulation feedback: coverage_diff_rules.md, log_analysis_rules.md
- **10 new tests** for eval runner (total: ≥146)
- **Shared coverage_diff module** in lib/ (eliminated sys.path hack from Phase 2b)

### What's included in Phase 2 收尾 (cleanup)

- **pip install fix**: hatch build targets for `lib`, `dv_mcp`, `scripts` packages
- **.mcp.json**: Claude Code MCP client configuration for auto-connecting the DV Context server
- **ruff 95→0**: E501 line wraps, E402 noqa for sys.path pattern, UP015/UP017/UP037/I001/F401/E741 fixes
- **mypy 18→0**: no-any-return, import-untyped stubs (types-PyYAML, types-jsonschema), var-annotated
- **4th eval case**: generate_case_0001.yaml (completing all 4 task_modes: triage, scenario, generate-case, feedback)
- **3 example walkthroughs**: triage, full end-to-end closure, MCP server setup guide

### What's included in Phase 2d (Code Coverage Extension)

- **7 coverage types**: functional, line, branch, condition, toggle, fsm, assert
- **Unified schema**: `anyOf` conditional required fields per coverage type, backward-compatible with existing functional gaps
- **Extended gap IDs**: `GAP_XXXX` (functional) + `GAP_XNNN` (code coverage: L/B/C/T/M/A prefix)
- **4 new classifications**: Dead Code, Defensive Code, Unreachable State, Insufficient Toggle (10 total)
- **27 gaps**: 15 functional + 12 code coverage (2 per type)
- **Type-aware MCP tools**: `cov_list_uncovered` with `coverage_type="all"` filter, type-specific summaries, evidence, and synthetic source snippets
- **Type-aware diff**: `coverage_diff.py` produces per-type delta fields and `by_type` summary breakdown
- **Type-aware validation**: `static_patch_check.py` validates coverage target format per type
- **35 new tests** (total: 181), **2 new eval cases** (total: 6)
- **12 updated skill documents** covering all workflow references
- Running total after Phase 2d: 181 tests, 27 gaps (15 functional + 12 code coverage)

### What's included in Phase 3 (URG Coverage Report Parser)

- **URG HTML parser library** (`lib/urg_parser/`): parses Synopsys VCS URG reports (O-2018.09-SP2)
  - `session.py` — session.xml metadata and per-type metrics
  - `structure.py` — modlist.html and groups.html structure mapping
  - `functional.py` — grp*.html functional coverage (covergroup/coverpoint/bin)
  - `code_coverage.py` — mod*.html code coverage (line/branch/condition/toggle/fsm/assert)
  - `gap_assembler.py` — gap ID assignment, path normalization, schema filtering
  - `index_builder.py` — coverage_index.json and coverage_gaps.json output (MCP-compatible)
- **CLI script** (`scripts/build_coverage_index.py`): orchestrates full parse pipeline from URG HTML to structured JSON
- **Demo project** (`mock_data/axi2ahb/`): sample AXI2AHB bridge URG report (public/sanitized demo data)
  - 982 schema-compliant gaps across all 7 coverage types (functional 16, line 126, branch 40, condition 32, toggle 763, fsm 1, assert 4)
  - Synopsys library file filtering (`/opt/synopsys/` paths excluded)
  - Source file path normalization (absolute → relative)
- **MCP integration**: coverage_index.json includes `gaps` field, all 3 coverage tools can query real project data
- **Makefile target**: `make build-real-index`

### What's included in Phase 4 (Source Resolver + Project Registry + EDA Adapters)

- **Bounded Source Snippet Resolver** (`lib/source_resolver.py`): reads real SV source snippets with security boundaries (path traversal protection, allowlist, max_lines/max_bytes)
- **Project Registry** (`lib/project_registry.py`): resolves project names to manifest paths via `projects.yaml` or `COV_FLOW_PROJECTS` env var
- **EDA Adapter Skeleton** (`lib/eda_adapters/`): abstract base class + StubVerdiAdapter + StubVCSAdapter (stub data, no real EDA integration)
- **Contract Tests** (`tests/test_tool_contracts.py`): envelope format validation for all 11 MCP tools
- **Large Dataset Tests** (`tests/test_large_dataset.py`): truncation and context budget validation with axi2ahb 982-gap dataset
- **`cov_get_coverpoint_source` upgraded**: now returns `source_mode: "real"` when reading from coverage_model_root, falls back to `source_mode: "synthetic"` when file unavailable
- **MCP tools support project name input**: `cov_list_uncovered(project="dma_subsystem")` works without manifest path

### What's included in Phase 5a (TB Index Builder + MCP Integration)

- **Generic SV Parser** (`lib/sv_parser.py`): regex-based SystemVerilog parser (13 patterns, 12 public functions) — class/module/method/config_db/plusarg extraction, feature tag inference, UVM role classification, test-to-sequence linking
- **TB Index Builder** (`scripts/build_tb_index.py`): manifest-driven CLI that parses UVM source directories and generates `tb_index.json` (schema_version: tb_index.v1)
- **axi2ahb real TB data**: pre-built `mock_data/axi2ahb/.dv_ai_index/tb_index.json` with 1 base test, 12 concrete tests, 13 sequences (base_virtual_sequence: 44 api_methods), 24 config knobs
- **`tb_get_existing_tests_for_feature` upgraded**: scope filter parameter (all/tests/sequences), api_methods included in matched sequences with base-sequence truncation (10 methods max, api_methods_truncated flag)
- **`tb_find_tests_for_gap`** (new): auto-extracts semantic keywords from coverpoint/bin names, searches TB index for matching tests/sequences, assesses whether existing TB likely covers the gap (existing_test_likely_covers / partial_coverage / new_stimulus_needed)
- **Semantic Matcher** (`lib/semantic_matcher.py`): keyword extraction (prefix stripping, letter↔digit splitting, cross-bin parsing), TB entry scoring, gap coverage assessment
- **Makefile target**: `make build-real-tb-index` (requires AXI2AHB_ROOT env var)
- **Integration tests**: `tests/test_mcp_tb_tools_axi2ahb.py` (14 tests), `tests/test_tb_find_tests_for_gap.py` (18 tests), `tests/test_semantic_matcher.py` (26 tests), contract tests for axi2ahb

### What's included in Phase 5b (Real Simulation Execution Infrastructure)

- **SimExecutor** (`lib/sim_executor.py`): subprocess executor with security boundaries — test name validation (regex + path traversal rejection), seed validation, `shlex.split()` + `shell=False`, cwd locked to project_root, timeout enforcement, log capture with stderr separation, 50-line stdout tail, result persistence to JSON
- **SimLogParser** (`lib/sim_log_parser.py`): VCS/UVM log parsing with priority-based pass/fail detection (explicit markers > UVM_FATAL > UVM_ERROR > $finish > unknown), UVM message counting (INFO/WARNING/ERROR/FATAL), bracket format support
- **UrgRunner** (`lib/urg_runner.py`): URG report generation via subprocess with timeout, report parsing via existing `lib/urg_parser` pipeline, coverage_db.v1 schema output compatible with `compute_diff()`
- **Manifest Schema Extension**: 6 new optional fields in `simulation` block (`urg_cmd_template`, `urg_binary`, `urg_timeout_seconds`, `timeout_seconds`, `results_root`, `vdb_dir_template`), 4 convenience properties in `lib/manifest.py`
- **4 MCP tools upgraded** with real execution: `sim_run_targeted_test` (compile→run→urg pipeline), `sim_get_test_result` (loads persisted SimResult or parses run.log), `sim_search_log` (bounded 20 matches with total_matches), `cov_get_coverage_diff` (auto-discovers latest URG reports)
- **CLI upgrade**: `scripts/sim_runner.py --dry-run` flag with test name/seed validation, pipeline execution, human-readable summary, exit codes (0=pass, 1=run fail, 2=compile fail)
- **Real-only mode**: all simulation tools execute VCS subprocess via SimExecutor with full security boundaries
- **521 tests total**: 102 new tests for foundation libraries, 21 new tests for MCP tool real mode branching

### What's included in Phase 6 (Full MCP Tool Coverage)

- **Phase 6A — 8 Quick-Win MCP Tools** (21 tools total):
  - `spec_get_section` — get full spec section by section_id
  - `reg_find_field` — exact field name lookup (case-insensitive)
  - `reg_search_by_description` — keyword search on register field descriptions
  - `reg_get_ral_path` — get RAL access path for a register field
  - `rtl_get_instance_info` — get module hierarchy, ports, signals, FSM states
  - `tb_find_sequence` — find sequence by name (fuzzy match)
  - `tb_get_base_test_template` — get base test template with config knobs
  - `tb_find_config_knob` — find config knob by name

- **Phase 6B — 3 Source-File Indexers + 2 RTL Tools** (23 tools total):
  - `build_spec_index.py` — Markdown heading splitter (spec.md → spec_index.json)
  - `build_reg_index.py` — YAML register parser (regs.yaml → reg_db.json)
  - `build_rtl_index.py` — RTL module/signal/FSM indexer (reuses lib/sv_parser.py)
  - `rtl_get_source_snippet` — signal lookup + SourceResolver bounded read
  - `rtl_trace_fanin` — stub returning same-module signals as fan-in sources
  - Expanded sample data: 7 RTL SV files, 125-line spec, 144-line register YAML

- **Phase 6C — Simulation History + Feedback Schema** (24 tools total):
  - `build_sim_history_index.py` — aggregates sim_results/ into sim_history.json with per-gap hit trends
  - `feedback_report.schema.json` — validates /dv-simulation-feedback skill output
  - `validate_feedback_report.py` — CLI schema validator
  - `cov_get_hit_history` — gap_id → hit trend, first_covered, associated tests

- **Phase 6D — 2 Final Stubs** (26 tools total):
  - `tb_get_sequence_source_snippet` — convenience wrapper (sequence name → source snippet)
  - `wave_check_condition` — permanent stub via StubVerdiAdapter (real = Verdi/NPI)

- **693 tests total**, ruff 0, mypy 0, make accept clean
- Makefile targets: `build-spec-index`, `build-reg-index`, `build-rtl-index`, `build-sim-history-index`, `validate-feedback`

### What's explicitly NOT included (see CLAUDE.md)

- No real EDA tool integration (Verdi/VCS/KDB/NPI/VPI/FSDB) — EDA adapters are stub only
- No real project data (RTL/FS/register docs/UVM/coverage DB) — the URG report is sanitized demo data only
- Real simulation execution requires VCS installed and proper command templates in manifest (Phase 5b provides infrastructure, not VCS itself)
- No eval runner LLM execution mode (Phase 6)

## Coverage Types

| Type | Gap ID Prefix | Schema Required Fields | Classification Examples |
|------|--------------|----------------------|------------------------|
| functional | `GAP_XXXX` | covergroup, coverpoint, bin | Missing Stimulus, Config Missing |
| line | `GAP_LNNN` | source_file, source_line | Dead Code, Defensive Code |
| branch | `GAP_BNNN` | source_file, source_line, branch_type, direction | Missing Stimulus, Defensive Code |
| condition | `GAP_CNNN` | source_file, source_line, condition_expr, combination | Missing Stimulus |
| toggle | `GAP_TNNN` | signal, toggle_dir, module | Insufficient Toggle |
| fsm | `GAP_MNNN` | module, fsm_name, state | Unreachable State, Config Missing |
| assert | `GAP_ANNN` | assert_name, source_file, source_line | Dead Code |

## Technology Stack

- **Python 3.11+** with hatchling build system
- **MCP SDK** (`mcp[cli]`) with FastMCP for stdio transport
- **jsonschema** for output validation
- **pytest** for testing

## Acceptance Commands

| Command | What it does |
|---------|-------------|
| `make validate` | Schema-validate `project_manifest.yaml` |
| `make validate-gaps` | Schema-validate `coverage_gaps.json` |
| `make validate-scenario FILE=path` | Schema-validate a scenario card file |
| `make validate-patch FILE=path` | Schema-validate a testcase patch file |
| `make static-check FILE=path` | Run 6 static patch checks |
| `make build-indexes` | Generate all 5 index files |
| `make build-real-index` | Parse real URG report and generate coverage index |
| `make build-spec-index` | Build spec index from Markdown |
| `make build-reg-index` | Build register index from YAML |
| `make build-rtl-index` | Build RTL index from SV source files |
| `make build-sim-history-index` | Aggregate simulation results into history index |
| `make validate-feedback FILE=path` | Schema-validate a feedback report |
| `make lint` | Run ruff linter (0 issues required) |
| `make typecheck` | Run mypy type checker (0 errors required) |
| `make test` | Run all pytest tests |
| `make smoke-server` | Verify server imports and 26 tools registered |
| `make run-server` | Start MCP server (manual, blocking) |
| `make accept` | Run all acceptance checks |

## Eval Suite

The `evals/` directory contains YAML evaluation cases for validating skill workflows.

**Validate a single eval case**:
```bash
python scripts/run_eval.py --eval evals/triage_gap_0001.yaml --dry-run
```

**Validate all eval cases in batch**:
```bash
python scripts/run_eval.py --eval-dir evals/ --dry-run
```

The runner performs 6 structure checks: YAML parseable, required fields, valid task_mode, non-empty expected_tools, tool existence, valid classification enum. LLM execution is deferred to Phase 6.
See `evals/README.md` for details.

## Next Steps

Phase 0–6D are complete. The design blueprint from `implementation_plan.md` is fully implemented.

The following are **out of scope** and require explicit approval before starting:

| Item | Scope | Status |
|------|-------|--------|
| Eval LLM execution | Run eval cases with actual Claude calls and scoring | Not started |
| Multi-project support | Beyond registry lookup | Not started |
| Real EDA integration | Verdi/VCS/NPI adapters | Not started (permanent stubs) |

## License

Proprietary - Internal use only.

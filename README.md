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
# Create virtual environment and install dependencies
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# Validate the mock project manifest
make validate

# Validate coverage gaps data
make validate-gaps

# Build all indexes from mock data
make build-indexes

# Run tests
make test

# Smoke-test the MCP server (non-blocking)
make smoke-server

# Run full acceptance suite
make accept

# Start the MCP server (manual, blocking)
make run-server
```

## Project Structure

```
cov_flow/
├── schemas/              JSON Schema definitions for all outputs
├── scripts/              Offline indexer CLIs and validators
├── lib/                  Shared Python library (manifest, schema validation)
├── dv_mcp/               DV Context MCP Server (FastMCP-based)
│   └── dv_context_server/
│       ├── server.py          FastMCP entry point (thin wrapper)
│       ├── tools/             Pure Python tool functions (no MCP dependency)
│       ├── services/          Project loading, evidence, summarization
│       └── indexes/           JSON index readers
├── skills/               Skill Pack (SKILL.md + references for each workflow)
├── mock_data/            Mock DMA subsystem project data
│   └── dma_subsystem/
│       ├── project_manifest.yaml
│       ├── coverage_gaps.json
│       └── .dv_ai_index/      Pre-built mock indexes (committed as fixtures)
├── examples/             Usage examples (planned)
└── tests/                Tests for schemas, scripts, and tools
```

## Current Status

**Phase 2 complete** - all acceptance checks passing.

| Phase | Scope | Status |
|-------|-------|--------|
| Phase 0 | Project scaffolding + Manifest schema | **Done** |
| Phase 1 | Schemas + Mock data + MCP tools + Tests | **Done** |
| Phase 2a | Skill references + Validation scripts + Eval skeleton | **Done** |
| Phase 2b | Sim tools + Coverage diff + Static patch check + Evals | **Done** |
| Phase 2c | Eval runner + Remaining skill references | **Done** |

### What's included in Phase 1 Mock MVP

- **4 JSON schemas**: project_manifest, coverage_gap, scenario_card, testcase_patch
- **15 mock coverage gaps** across 5 covergroups (5 fully traceable end-to-end)
- **5 pre-built mock indexes**: coverage, spec, register, RTL, TB
- **7 MCP tools** (pure Python, no MCP runtime needed for testing):
  - `cov_list_uncovered`, `cov_get_gap_detail`, `cov_get_coverpoint_source`
  - `spec_search`
  - `reg_find_fields_affecting_feature`
  - `tb_get_existing_tests_for_feature`
  - `rtl_find_signal`
- **82 tests** covering schemas, scripts, and all tools
- **5 SKILL.md skeletons** for each workflow

### What's included in Phase 2a (initial stage)

- **8 skill reference documents**: workflow, gap classification, scenario card schema guide, testcase generation rules, review checklist, triage policy, gap priority rules, unreachable heuristics
- **2 validation scripts**: validate_scenario_card.py, validate_patch_metadata.py
- **1 eval skeleton**: README.md + triage_gap_0001.yaml
- **14 new tests** (total: 96)

### What's included in Phase 2b

- **1 static patch check script**: static_patch_check.py with 6 deterministic checks
- **2 simulation scripts**: sim_runner.py (mock dry-run), coverage_diff.py (before/after DB comparison)
- **4 new MCP tools** (total: 11):
  - `sim_run_targeted_test`, `sim_get_test_result`, `sim_search_log`
  - `cov_get_coverage_diff`
- **Audit logging service**: 5-field audit records (user, project, tool, arg_hash, timestamp, result_size)
- **Safety field** for simulation execution: policy_checked, confirmed, command_template_used
- **Mock simulation data**: coverage_db_before.json, coverage_db_after.json, sim_logs/
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

### What's explicitly NOT included (see CLAUDE.md)

- No real EDA tool integration (Verdi/VCS/KDB/NPI/VPI/FSDB)
- No real project data (RTL/FS/register docs/UVM/coverage DB)
- No real coverage report parser (Phase 3)
- No real UVM testcase generation (Phase 4)
- No real simulation execution (Phase 5)
- No eval runner LLM execution mode (Phase 6)

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
| `make build-indexes` | Generate all 5 mock index files |
| `make test` | Run all pytest tests |
| `make smoke-server` | Verify server imports and 11 tools registered |
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

The runner performs 6 structure checks: YAML parseable, required fields, valid task_mode, non-empty expected_tools, tool existence, valid classification enum. LLM execution is deferred to Phase 3+.

See `evals/README.md` for details.

## Next Steps

Phase 0–2 are complete. The following are **out of scope** and require explicit approval before starting:

| Phase | Scope | Status |
|-------|-------|--------|
| Phase 3 | Real URG HTML/XML coverage report parser | Not started |
| Phase 4 | Real UVM testcase generation | Not started |
| Phase 5 | Real simulation tool integration (VCS, Verdi, etc.) | Not started |
| Phase 6 | Eval runner LLM execution mode | Not started |

See `implementation_plan.md` §13 and CLAUDE.md for constraints.

## License

Proprietary - Internal use only.

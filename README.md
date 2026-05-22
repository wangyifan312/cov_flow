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

**Phase 1 Mock MVP** - all acceptance checks passing.

| Phase | Scope | Status |
|-------|-------|--------|
| Phase 0 | Project scaffolding + Manifest schema | **Done** |
| Phase 1 | Schemas + Mock data + MCP tools + Tests | **Done** |
| Phase 2 | Full Skills + Sim tools + Eval suite | Not started (out of MVP scope) |

### What's included in Phase 1 Mock MVP

- **4 JSON schemas**: project_manifest, coverage_gap, scenario_card, testcase_patch
- **15 mock coverage gaps** across 3 covergroups (5 fully traceable end-to-end)
- **5 pre-built mock indexes**: coverage, spec, register, RTL, TB
- **7 MCP tools** (pure Python, no MCP runtime needed for testing):
  - `cov_list_uncovered`, `cov_get_gap_detail`, `cov_get_coverpoint_source`
  - `spec_search`
  - `reg_find_fields_affecting_feature`
  - `tb_get_existing_tests_for_feature`
  - `rtl_find_signal`
- **82 tests** covering schemas, scripts, and all tools
- **5 SKILL.md skeletons** for each workflow

### What's explicitly NOT included (see CLAUDE.md)

- No real EDA tool integration (Verdi/VCS/KDB/NPI/VPI/FSDB)
- No real project data (RTL/FS/register docs/UVM/coverage DB)
- No real coverage report parser
- No real UVM testcase generation
- No Phase 2 features

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
| `make build-indexes` | Generate all 5 mock index files |
| `make test` | Run all 82 pytest tests |
| `make smoke-server` | Verify server imports and 7 tools registered |
| `make run-server` | Start MCP server (manual, blocking) |
| `make accept` | Run all of the above |

## License

Proprietary - Internal use only.

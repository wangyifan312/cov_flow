# MCP Server Setup Guide

How to configure and verify the `dv-context` MCP server for the DV AI Coverage
Closure Skill Pack.

## Prerequisites

- Python 3.11+, dependencies installed (`pip install -e ".[dev]"`)
- Claude Code CLI available on `$PATH`

## Step 1 — Configure `.mcp.json`

Copy `.mcp.json.example` from the project root and adjust the Python path:

```bash
cp .mcp.json.example .mcp.json
# Ensure .mcp.json uses python3 as command
```

The resulting `.mcp.json` should look like:

```json
{
  "mcpServers": {
    "dv-context": {
      "command": "python3",
      "args": ["-m", "dv_mcp.dv_context_server.server"],
      "env": { "PYTHONPATH": "." }
    }
  }
}
```

| Field | Purpose |
|---|---|
| `command` | System Python 3.11+ interpreter |
| `args` | Module path to the MCP server entry point |
| `env.PYTHONPATH` | Adds project root to `sys.path` for `lib/`, `dv_mcp/` |

> The server package lives under `dv_mcp/` (not `mcp/`) to avoid shadowing
> the installed `mcp` SDK package.

## Step 2 — Build Indexes and Validate

```bash
make build-indexes
make validate && make validate-gaps
```

## Step 3 — Verify Connection

```bash
make smoke-server
```

A successful run lists all 11 registered tools and exits with code 0.

Then start Claude Code:

```bash
claude
```

Ask `What MCP tools are available?` — you should see all 11:

`cov_list_uncovered`, `cov_get_gap_detail`, `cov_get_coverpoint_source`,
`spec_search`, `reg_find_fields_affecting_feature`,
`tb_get_existing_tests_for_feature`, `rtl_find_signal`,
`sim_run_targeted_test`, `sim_get_test_result`, `sim_search_log`,
`cov_get_coverage_diff`.

## Example Conversation

```
User:  List all P0 uncovered gaps for project {project}.
Claude: [calls cov_list_uncovered]
        - GAP_0001: desc_mode_cp / linked_list (Config Missing)
        - GAP_0003: desc_chaining_cp / chain_of_3 (Missing Stimulus)
```

## Troubleshooting

**Server not found** — Verify `.mcp.json` is in the project root and `command`
points to a valid interpreter (`python3 --version`). Restart Claude
Code after editing `.mcp.json`.

**Tool returns an error** — Confirm mock indexes exist under
`mock_data/{project}/`. Rebuild with `make build-indexes`. Validate with
`make validate`.

**Import errors** (`ModuleNotFoundError: No module named 'dv_mcp'`) — Ensure
`PYTHONPATH=.` is set in `.mcp.json`. Reinstall: `pip install -e ".[dev]"`.

**Smoke test fails** — Run directly for verbose output:
`PYTHONPATH=. python3 scripts/smoke_server.py`

## Next Steps

- [Coverage Triage Walkthrough](triage_walkthrough.md)
- [End-to-End Coverage Closure Walkthrough](full_closure_walkthrough.md)

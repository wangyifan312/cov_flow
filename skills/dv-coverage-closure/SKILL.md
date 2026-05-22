---
name: dv-coverage-closure
description: >
  Use this skill for digital IC verification coverage closure workflows.
  It orchestrates gap triage, scenario generation, testcase generation,
  and simulation feedback through sub-skills and DV Context MCP tools.
---

# DV Coverage Closure — Orchestrator Skill

## Purpose

Top-level entry point and workflow orchestrator for coverage closure.
Routes tasks to the appropriate sub-skill based on the user's request.

## Required Inputs

- `project` — project id or manifest path
- `regression` — regression id or coverage report path
- `scope` — block, subsystem, feature, or covergroup
- `task_mode` — one of: `triage`, `scenario`, `generate-case`, `feedback`

## Workflow Summary

1. Load the project manifest.
2. Validate available context sources.
3. Route to sub-skill by `task_mode`:
   - `triage` → `dv-coverage-gap-triage`
   - `scenario` → `dv-coverage-scenario-generation`
   - `generate-case` → `dv-testcase-generation`
   - `feedback` → `dv-simulation-feedback`
4. Aggregate and present the sub-skill output.

## MCP Tool Policy

- Call `manifest_validate` before any other tool.
- Never read full RTL/FS/TB files.
- Use summary-first tools; expand source snippets only when evidence is required.

## Hard Restrictions

- Do not generate code in `triage` mode.
- Do not mark gaps as waived or unreachable.
- Do not modify source files without explicit user approval.
- Do not bulk-load project data.

## Output Placeholder

Output depends on `task_mode`. See sub-skill documentation for format.

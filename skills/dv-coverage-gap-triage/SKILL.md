---
name: dv-coverage-gap-triage
description: >
  Use this skill to classify, prioritize, and triage coverage gaps
  from a regression report. Produces a structured triage report with
  classification, priority, root cause hypothesis, and recommended action.
---

# DV Coverage Gap Triage

## Purpose

Analyze uncovered coverage items and produce a triage report:
classification, priority ranking, root cause hypothesis, and next action.

## Required Inputs

- `project` — project id or manifest path
- `regression` — regression id or coverage report path
- `scope` — instance path or feature scope
- `top_n` — number of top gaps to triage (default: 20)

## Workflow Summary

1. Load manifest and validate context sources.
2. Call `cov_list_uncovered` to get top gaps.
3. For each gap, call `cov_get_gap_detail` + `cov_get_coverpoint_source`.
4. Classify each gap into one of:
   - Functional: Missing Stimulus, Config Missing, Constraint Too Tight,
     Coverage Model Issue, Monitor Sampling Issue, Unreachable Candidate
   - Code coverage: Dead Code, Defensive Code, Unreachable State, Insufficient Toggle
5. Assign priority (P0–P3) based on coverage impact and fix complexity.
6. Output triage report.

## MCP Tool Policy

- `cov_list_uncovered` — required, first call.
- `cov_get_gap_detail` — required per gap.
- `cov_get_coverpoint_source` — required per gap.
- `cov_get_coverage_diff` — optional, for comparing before/after coverage databases.
- `spec_search`, `reg_find_fields_affecting_feature` — only when needed for classification.

## Hard Restrictions

- Do not generate code or testcases.
- Do not read full RTL files.
- Do not mark gaps as waived automatically.
- Do not claim unreachable without formal evidence.

## Output Placeholder

Triage report: ranked table with Gap ID, Coverpoint, Bin, Classification,
Priority, Recommended Action, and Evidence references.

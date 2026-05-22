---
name: dv-coverage-scenario-generation
description: >
  Use this skill to generate a structured scenario card for a single
  coverage gap. The card specifies required configuration, stimulus,
  expected behavior, and confidence level.
---

# DV Coverage Scenario Generation

## Purpose

Transform a single coverage gap into a verification scenario card
that describes what stimulus is needed to close the gap.

## Required Inputs

- `project` — project id or manifest path
- `gap_id` — specific coverage gap identifier
- (optional) `triage_entry` — classification and priority from triage

## Workflow Summary

1. Call `cov_get_gap_detail` + `cov_get_coverpoint_source` for the gap.
2. Infer semantic meaning from coverpoint/bin names and source.
3. Call `spec_search` for relevant feature documentation.
4. Call `reg_find_fields_affecting_feature` for configuration dependencies.
5. Call `tb_get_existing_tests_for_feature` to check for existing coverage.
6. If signal controllability is unclear, call `rtl_find_signal`.
7. Generate scenario card with all required fields.

## MCP Tool Policy

- `cov_get_gap_detail` — required.
- `spec_search` — required for semantic context.
- `reg_find_fields_affecting_feature` — required for config dependencies.
- `tb_get_existing_tests_for_feature` — required to avoid duplication.
- `rtl_find_signal` — optional, only when controllability is unclear.

## Hard Restrictions

- Lower confidence when evidence is insufficient.
- Do not invent register fields or RAL paths.
- Do not claim full confidence without complete evidence chain.
- Do not generate UVM code (that is the testcase-generation skill).

## Output Placeholder

Scenario card YAML: gap_id, target_coverage, semantic_interpretation,
required_config, stimulus, expected_behavior, tb_reuse, confidence, risk.

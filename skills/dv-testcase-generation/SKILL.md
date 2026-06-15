---
name: dv-testcase-generation
description: >
  Use this skill to generate a minimal UVM testcase or sequence patch
  based on a scenario card and existing testbench templates. Output is
  a patch/new-file set, not a direct source modification.
---

# DV Testcase Generation

## Purpose

Generate a minimal UVM sequence/test/config patch that implements
the stimulus described in a scenario card, reusing existing TB templates.

## Required Inputs

- `project` — project id or manifest path
- `gap_id` — target coverage gap
- `scenario_card` — output from scenario-generation skill

## Workflow Summary

1. Read the scenario card; confirm generation target (sequence/test/config).
2. Call `tb_get_existing_tests_for_feature` to identify the base test structure.
3. Call `tb_get_existing_tests_for_feature` to find reusable sequences.
4. Call `reg_find_fields_affecting_feature` for RAL access paths.
5. Generate minimal patch: new sequence or test file, or config override.
6. Output patch metadata: new files, modified files, compile/run commands,
   coverage target mapping, and review checklist.

## MCP Tool Policy

- `tb_get_existing_tests_for_feature` — required before generation (identifies base test and reusable sequences).
- `tb_get_existing_tests_for_feature` — required to avoid duplication.
- `reg_find_fields_affecting_feature` — required for RAL paths.
- `rtl_find_signal` — optional, only when signal controllability or data path is unclear.

## Coverage Type Support

Generates testcase patches targeting both functional and code coverage gaps.
Coverage target format varies by type: `covergroup.coverpoint.bin` (functional), `source_file:line` (line/branch/condition), `module.signal[direction]` (toggle), `module.fsm_name.state` (fsm).

## Hard Restrictions

- Must reuse existing base_test/sequence/config_knob.
- Do not invent UVM component names, RAL paths, or sequencer paths.
- Do not directly modify trunk files — output as patch or new files only.
- Do not skip the review checklist.

## Output Placeholder

Patch metadata: patch_id, gap_id, new_files, modified_files,
base_reuse, compile_command, run_command, coverage_target, review_checklist.

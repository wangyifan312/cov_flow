---
name: dv-simulation-feedback
description: >
  Use this skill to analyze simulation results and coverage diffs
  after running a generated testcase. Determines whether the target
  gap was closed and recommends next actions.
---

# DV Simulation Feedback

## Purpose

Analyze compile/simulation results and coverage diff to determine
whether a target gap was closed and what to do next.

## Required Inputs

- `project` — project id or manifest path
- `test_name` — the test that was run
- `target_gap` — the gap_id that was targeted

## Workflow Summary

1. Call `sim_get_test_result` for compile/run status.
2. If compile or sim failed, call `sim_search_log` for error root cause.
3. If sim passed, call `cov_get_coverage_diff` for hit count delta.
4. If target gap was not hit, classify the reason:
   - Stimulus did not reach the condition
   - Configuration was not enabled
   - Sampling condition was not met
   - Simulation failure prevented coverage collection
5. Output feedback report with delta, root cause, and next action.

## Seed Strategy

When a gap is not closed on the first run:

1. **Single seed** (seed=1): Initial run. If gap not hit, check root cause before re-running.
2. **Targeted seeds** (3-5 seeds): If root cause is constraint randomization, re-run with 3-5 different seeds to check stochastic coverage.
3. **Escalation**: If 5 seeds all miss the gap, the stimulus or config approach likely needs redesign — return to Scenario stage rather than sweeping more seeds.

Do not blindly sweep seeds without analyzing root cause first. Each re-run should be informed by the previous feedback.

## MCP Tool Policy

- `sim_get_test_result` — required first call.
- `sim_search_log` — required on failure.
- `cov_get_coverage_diff` — required when sim passes.
- `cov_get_gap_detail` — for re-checking gap context.

## Coverage Type Support

Analyzes coverage diffs for both functional and code coverage gaps.
The `cov_get_coverage_diff` tool returns type-specific delta fields and a `by_type` summary breakdown across all 7 coverage types.

## Hard Restrictions

- Must distinguish between stimulus/config/sampling/sim-failure causes.
- Do not guess hit status from log text — use coverage diff data.
- Do not mark gap as closed without positive coverage diff evidence.

## Output Placeholder

Feedback report: test_name, target_gap, compile_result, sim_result,
hit_count_delta, gap_closed (bool), root_cause, next_action.

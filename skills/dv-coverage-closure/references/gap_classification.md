# Gap Classification Guide

Definitions and criteria for classifying coverage gaps into one of ten categories (6 functional + 4 code coverage).

## Classification Categories

### Missing Stimulus
The testbench does not generate the required stimulus to exercise the feature.
- **Indicators**: coverpoint exists, config is correct, but the specific input pattern or data sequence is absent from existing tests.
- **Typical fix**: Add or extend a sequence that generates the missing stimulus.

### Config Missing
The required configuration (register write, mode enable, parameter override) is not applied in existing tests.
- **Indicators**: The feature path exists in RTL and testbench, but no test sets the necessary config registers or mode bits.
- **Typical fix**: Add register writes or config overrides to an existing or new sequence.

### Constraint Too Tight
The testbench constraints (e.g., `uvm_sequence` randomization constraints, `constraint` blocks) exclude the value range needed to hit the coverage point.
- **Indicators**: Stimulus exists but randomization constraints prevent certain values or combinations from being generated.
- **Typical fix**: Relax or add directed constraint overrides for targeted runs.

### Coverage Model Issue
The coverage model itself has a problem — incorrect bins, overly specific cross conditions, or sampling logic errors.
- **Indicators**: The feature works correctly in simulation but the coverage model fails to sample due to model bugs or overly narrow bin definitions.
- **Typical fix**: Correct the coverage model source code (requires engineer review).

### Monitor Sampling Issue
The coverage monitor or subscriber has a sampling condition that is too restrictive or incorrectly timed.
- **Indicators**: The feature is exercised but the monitor's `sample()` call is gated by conditions that are never simultaneously true.
- **Typical fix**: Correct the sampling condition in the monitor or coverage collector.

### Unreachable Candidate
The coverage point may be structurally unreachable given the current design configuration.
- **Indicators**: RTL analysis suggests the signal path is gated by a constant, a `generate` condition, or a parameter that prevents the state from being reached.
- **Typical fix**: Requires formal verification or engineer sign-off. **Never auto-waive.** Mark as candidate only.

## Code Coverage Classifications

The following 4 classifications apply to code coverage gaps (line, branch, condition, toggle, FSM, assert). They complement the 6 functional coverage classifications above.

### Dead Code
Code that is structurally unreachable or no longer used in the design.
- **Indicators**: Line or branch has never been executed across all regressions; RTL analysis shows the code path is gated by a constant or removed by synthesis.
- **Typical fix**: Confirm with formal analysis; if truly dead, request engineer waiver. Do not generate stimulus.

### Defensive Code
Error-handling or safety code that is difficult to trigger under normal operation.
- **Indicators**: Code path exists for error injection, bus fault, or overflow handling; stimulus required is highly specific or requires fault injection.
- **Typical fix**: Add directed error-injection stimulus or request waiver with documented safety rationale.

### Unreachable State
An FSM state that cannot be reached given the current design configuration or parameter settings.
- **Indicators**: FSM analysis shows the state transition is gated by a parameter, generate condition, or external signal not present in the testbench.
- **Typical fix**: Verify parameter settings; if structurally unreachable, request formal proof and engineer waiver.

### Insufficient Toggle
A signal toggle direction (0→1 or 1→0) that has not been observed in simulation.
- **Indicators**: Signal toggles in one direction but not the other; may indicate missing stimulus, disabled feature, or constant-driven signal.
- **Typical fix**: Add stimulus that exercises the missing toggle direction; check if the signal is controllable from the testbench.

## Context Routing Table

For each classification, query only the context needed. Avoid loading unnecessary data.

| Classification | Priority Context | Usually Not Needed |
|---------------|-----------------|-------------------|
| Missing Stimulus | Coverage model, existing sequences, config registers | Full RTL |
| Config Missing | Register fields, existing test config, coverage model | Full UVM env |
| Constraint Too Tight | Sequence constraints, coverage bins, config knobs | Full FS |
| Coverage Model Issue | Coverage model source, FS spec section | Full RTL, waveforms |
| Monitor Sampling Issue | Monitor code, sampling conditions, simulation log | Full register doc |
| Unreachable Candidate | RTL fanin, formal evidence, generate conditions | All testcases |
| Dead Code | RTL source, synthesis constraints, formal evidence | Testcases, sequences |
| Defensive Code | Error injection points, fault models, RTL source | Full UVM env |
| Unreachable State | FSM definition, parameter settings, RTL fanin | Testcases |
| Insufficient Toggle | RTL signal drivers, toggle coverage report | Full FS, register doc |

## Compound Classifications

A gap may have multiple contributing factors. Use compound labels when appropriate:
- **Config Missing + Missing Stimulus**: Both config and stimulus need to be added.
- **Constraint Too Tight + Config Missing**: Config is missing AND constraints are too restrictive.

List the primary classification first, followed by secondary factors.

## Cross-Coverage Bins

Cross-coverage bins (where two or more coverpoints are crossed) require special handling:

- **Overly specific cross**: If the cross condition combines values that are mutually exclusive or practically unreachable together, classify as **Coverage Model Issue** and flag for engineer review.
- **Missing stimulus for cross**: If both individual coverpoints are hit but the cross bin is not, classify as **Missing Stimulus** — the testbench needs a scenario that exercises both dimensions simultaneously.
- **Config-dependent cross**: If one dimension of the cross requires specific configuration, classify as **Config Missing + Missing Stimulus** (compound).

When triaging cross-coverage gaps, always check the individual coverpoint hit counts first. If individual bins are also uncovered, address those before the cross.

## Follow-Up Actions by Classification

| Classification | Next Step |
|---------------|-----------|
| Missing Stimulus | Proceed to scenario generation → testcase generation |
| Config Missing | Proceed to scenario generation with explicit config steps |
| Constraint Too Tight | Generate scenario with constraint override guidance |
| Coverage Model Issue | Flag for engineer review; do not generate testcase |
| Monitor Sampling Issue | Flag for engineer review; do not generate testcase |
| Unreachable Candidate | Flag for formal/human review; do not generate testcase |
| Dead Code | Flag for formal/human review; do not generate testcase |
| Defensive Code | Generate error-injection scenario if feasible; otherwise flag for review |
| Unreachable State | Flag for formal/human review; do not generate testcase |
| Insufficient Toggle | Proceed to scenario generation with directed toggle stimulus |

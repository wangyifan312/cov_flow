# Gap Classification Guide

Definitions and criteria for classifying coverage gaps into one of six categories.

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

## Compound Classifications

A gap may have multiple contributing factors. Use compound labels when appropriate:
- **Config Missing + Missing Stimulus**: Both config and stimulus need to be added.
- **Constraint Too Tight + Config Missing**: Config is missing AND constraints are too restrictive.

List the primary classification first, followed by secondary factors.

## Follow-Up Actions by Classification

| Classification | Next Step |
|---------------|-----------|
| Missing Stimulus | Proceed to scenario generation → testcase generation |
| Config Missing | Proceed to scenario generation with explicit config steps |
| Constraint Too Tight | Generate scenario with constraint override guidance |
| Coverage Model Issue | Flag for engineer review; do not generate testcase |
| Monitor Sampling Issue | Flag for engineer review; do not generate testcase |
| Unreachable Candidate | Flag for formal/human review; do not generate testcase |

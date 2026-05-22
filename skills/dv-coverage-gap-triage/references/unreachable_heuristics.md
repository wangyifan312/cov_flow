# Unreachable Candidate Heuristics

Rules and heuristics for identifying coverage gaps that may be structurally unreachable.

## Core Rule

**Unreachable can only be marked as a candidate — never as a confirmed waiver.**

Auto-waiver is explicitly prohibited. An unreachable candidate must be confirmed by:
1. Formal verification (e.g., VC Formal, JasperGold) proving the state is unreachable, OR
2. Engineer sign-off with documented reasoning

Until confirmed, the gap remains in the triage report as "Unreachable Candidate — pending formal/human review."

## Common Unreachable Patterns

### 1. RTL Constant Constraints
A signal is tied to a constant value, preventing certain states from being reached.
- **Example**: `assign ll_mode_en = 1'b0;` — linked-list mode is permanently disabled
- **Evidence**: Check RTL source for `assign` statements with constant values, or `parameter` overrides that lock out features

### 2. Generate Block Conditions
A `generate` block condition evaluates to false at elaboration time, removing entire code paths.
- **Example**: `generate if (ENABLE_CRC) begin ... end endgenerate` — if `ENABLE_CRC=0`, the CRC logic and its coverage points are structurally absent
- **Evidence**: Check parameter values in the elaboration configuration; verify `generate` conditions

### 3. Parameter Lockout
A parameter value prevents certain FSM states or code branches from being reachable.
- **Example**: `parameter MAX_BURST = 4;` — if coverage bins exist for burst length > 4, they are unreachable
- **Evidence**: Check parameter definitions and their override values in the testbench elaboration

### 4. Mutually Exclusive Conditions
Two or more conditions that cannot be simultaneously true, making cross-coverage bins unreachable.
- **Example**: Cross of `mode == IDLE` with `data_valid == 1` — if data_valid is only asserted in non-IDLE states
- **Evidence**: Analyze the FSM or control logic to verify mutual exclusion

### 5. External Dependency
A coverage point depends on an external signal or interface that is not active in the current testbench configuration.
- **Example**: Coverage of AXI response types that require a specific slave model not present in the testbench
- **Evidence**: Check testbench configuration and connected IP/models

## Evidence Checklist for Unreachable Candidates

Before marking a gap as Unreachable Candidate, collect:

- [ ] **RTL source snippet**: The specific code that suggests unreachability
- [ ] **Parameter/generate analysis**: Current parameter values and generate conditions
- [ ] **Signal controllability**: Whether the controlling signal can be driven by the testbench
- [ ] **Simulation evidence**: Whether the signal was observed to toggle in any regression run
- [ ] **Formal evidence** (if available): Formal proof that the state is unreachable

## False Positive Risks

**Do not mark a gap as unreachable based on any single indicator.** Common false positives:

| False Positive | Why It's Wrong |
|---------------|----------------|
| "The signal never toggled in regression" | May be missing stimulus, not unreachable |
| "The FSM state seems unused" | May require a specific configuration to reach |
| "No existing test exercises this path" | Does not mean the path is structurally unreachable |
| "The parameter defaults to 0" | The testbench may override it; check actual elaboration values |

## Output Format

When classifying a gap as Unreachable Candidate, include in the triage report:

```
Classification: Unreachable Candidate
Confidence: low | medium
Evidence:
  - RTL pattern: {description of the constant/generate/parameter constraint}
  - Signal: {signal_name} in {module_name}
  - Controllability: {can/cannot be driven by testbench}
  - Simulation: {observed/not observed in N regression runs}
  - Formal: {available/not available}
Recommended action: Request formal verification or engineer review
```

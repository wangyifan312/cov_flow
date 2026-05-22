# Gap Priority Rules

Priority assignment rules for coverage gap triage. Priority is based on coverage impact and fix complexity.

## Priority Definitions

| Priority | Definition | Criteria |
|----------|-----------|----------|
| **P0** | Critical — fix immediately | Critical feature path + 0% coverage + clear fix path available |
| **P1** | High — fix in current iteration | High-impact feature + low coverage + fix path is clear |
| **P2** | Medium — plan for next iteration | Moderate impact feature + requires cross-module analysis or complex fix |
| **P3** | Low — monitor or defer | Low impact feature, or likely unreachable candidate, or coverage model issue |

## P0 Criteria (all must be true)

- The feature is on a **critical path** (e.g., data path, interrupt handling, error recovery, power state transitions)
- Current coverage is **0%** for this specific point (not partially covered)
- A **clear fix path** exists: the classification is Missing Stimulus or Config Missing, and existing testbench infrastructure can be reused
- Related spec section and register fields are identified

## P1 Criteria (at least 2 must be true)

- The feature has **high impact** on verification goals (e.g., protocol compliance, corner cases in data handling)
- Coverage is **low** (0-25% of target) for this point
- Fix path is clear but may require **new sequence or test** (not just config change)
- Evidence chain is mostly complete (spec + register + TB identified)

## P2 Criteria

- Feature has **moderate impact** — not on critical path but still important
- Requires **cross-module analysis** (e.g., cross-coverage between blocks, inter-block protocol)
- Fix may require **testbench modifications** beyond adding sequences (e.g., new monitors, new config knobs)
- Evidence chain has gaps that need further investigation

## P3 Criteria (any one is sufficient)

- Feature has **low impact** on overall verification goals
- Classification is **Unreachable Candidate** (needs formal verification)
- Classification is **Coverage Model Issue** or **Monitor Sampling Issue** (needs model/monitor fix, not stimulus)
- Gap is in a **debug or test-only feature** that does not affect production verification

## Priority Escalation Rules

| Condition | Effect |
|-----------|--------|
| Gap has been P0/P1 for 2+ regression cycles without progress | Escalate: flag for engineering lead review |
| Multiple gaps share the same root cause | Escalate: fix the root cause to close multiple gaps at once |
| Gap blocks a downstream verification milestone | Escalate by one priority level |

## Priority Demotion Rules

| Condition | Effect |
|-----------|--------|
| Formal evidence shows gap is unreachable | Demote to P3 + mark as Unreachable Candidate |
| Coverage model is confirmed buggy | Demote to P3 + reclassify as Coverage Model Issue |
| Feature is confirmed out of scope for current verification plan | Demote to P3 + flag for waiver review |

## Classification-to-Priority Correlation

This is a default mapping. Override based on feature criticality.

| Classification | Default Priority | Notes |
|---------------|-----------------|-------|
| Missing Stimulus | P0 or P1 | P0 if critical feature; P1 otherwise |
| Config Missing | P0 or P1 | P0 if simple config add; P1 if complex |
| Constraint Too Tight | P1 or P2 | P1 if constraint relaxation is straightforward |
| Coverage Model Issue | P3 | Requires model fix, not stimulus |
| Monitor Sampling Issue | P3 | Requires monitor fix, not stimulus |
| Unreachable Candidate | P3 | Requires formal/human review |

# Review Checklist

Review checklist templates for all task modes. Each output from the coverage closure workflow must pass human review before being acted upon.

## Universal Review Points

These apply to all task modes:

- [ ] Evidence chain is complete and traceable (each claim references a specific source)
- [ ] No full RTL/FS/TB content was loaded into context (context budget respected)
- [ ] All referenced components (registers, sequences, tests) exist in the project index
- [ ] No project-specific assumptions were made beyond what the evidence supports
- [ ] Output format matches the schema definition

## Triage Report Review

| Check | Description |
|-------|-------------|
| Classification accuracy | Each gap's classification matches the evidence (coverage source, config state, constraint analysis) |
| Priority justification | P0/P1 assignments have supporting evidence; not based on guesswork |
| Unreachable claims | Any "Unreachable Candidate" has formal evidence or is flagged for engineer investigation |
| Completeness | All requested gaps (top N) are covered; no gaps silently dropped |
| Actionability | Recommended actions are specific enough to proceed to the next step |

## Scenario Card Review

| Check | Description |
|-------|-------------|
| Target coverage accuracy | covergroup/coverpoint/bin match the gap detail exactly |
| Semantic interpretation | Accurately synthesizes evidence from multiple sources |
| Config completeness | All required register writes are listed with correct RAL paths |
| Stimulus feasibility | Stimulus steps are achievable with existing testbench infrastructure |
| Expected behavior | Observable behaviors are verifiable (not vague) |
| Confidence calibration | Confidence level matches evidence completeness |
| Risk identification | Open questions and assumptions are explicitly listed |

## Testcase Patch Review

| Check | Description |
|-------|-------------|
| Base reuse | Patch extends an existing base test, not a standalone test |
| Sequence reuse | Patch reuses or extends an existing sequence |
| No trunk modification | Patch does not modify existing committed files without explicit approval |
| RAL path validity | All register references use valid paths from the register index |
| Compile command | Command follows manifest template and targets the correct test |
| Coverage target | Target format matches coverage model naming exactly |
| Review checklist | Patch includes specific, actionable review items (not generic) |
| Static checks pass | All class references, file paths, and component names exist in the index |

## Feedback Report Review

| Check | Description |
|-------|-------------|
| Root cause accuracy | Root cause classification matches simulation evidence |
| Coverage delta | Hit count change is correctly reported |
| Gap closure | `gap_closed` flag is accurate (true only if target bin was hit) |
| Next action | Recommended action is appropriate for the root cause |
| Distinguish failure modes | Compile failure vs. simulation failure vs. stimulus gap vs. sampling issue are correctly distinguished |

## Human Sign-Off Requirements

The following actions **require explicit human approval** before proceeding:

| Action | Why |
|--------|-----|
| Marking a gap as unreachable | Requires formal evidence; auto-waiver is prohibited |
| Running a simulation | Manifest policy + user confirmation required |
| Modifying source files | Even patch application requires human review |
| Changing coverage model | Model changes affect all downstream analysis |
| Committing code to repository | Must pass review checklist + human approval |
| Lowering confidence to "low" | Should trigger a discussion about evidence gaps |

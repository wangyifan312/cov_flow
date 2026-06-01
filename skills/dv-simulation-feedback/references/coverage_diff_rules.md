# Coverage Diff Interpretation Rules

Rules for analyzing coverage diff results and determining if a gap was closed.

## Gap State Definitions

### Closed

**Definition**: Gap transitioned from uncovered to covered.

**Condition**: `before_hit_count == 0 && after_hit_count > 0`

**Interpretation**: The test successfully exercised the previously uncovered bin.

**Action**: Mark gap as closed in tracking system. No further action needed for this gap.

### Regressed

**Definition**: Gap's hit count decreased.

**Condition**: `after_hit_count < before_hit_count`

**Interpretation**: The test reduced coverage, possibly due to:
- Constraint changes that exclude previously covered bins
- Timing changes that prevent sampling
- Monitor or coverage model changes

**Action**: Investigate root cause. May need to adjust test or revert changes.

### Unchanged

**Definition**: Gap's hit count did not change.

**Condition**: `after_hit_count == before_hit_count`

**Interpretation**: The test did not affect this gap. Possible reasons:
- Test does not target this gap
- Test targets gap but stimulus insufficient
- Coverage model issue prevents sampling

**Action**: If gap was target of this test, analyze failure modes (see below).

### Newly Covered

**Synonym**: Same as "Closed" - gap went from 0 to >0 hits.

## Diff Result Structure

The coverage_diff.py tool produces:

```json
{
  "ok": true,
  "tool": "coverage_diff",
  "before_report_id": "before_regression_001",
  "after_report_id": "after_regression_001",
  "gap_deltas": [
    {
      "gap_id": "GAP_0001",
      "coverage_type": "functional",
      "before_hit_count": 0,
      "after_hit_count": 5,
      "closed": true,
      "covergroup": "dma_desc_cg",
      "coverpoint": "desc_mode_cp",
      "bin": "linked_list"
    }
  ],
  "summary": {
    "total_gaps": 27,
    "newly_covered": 5,
    "regressed": 0,
    "unchanged": 22
  }
}
```

### Code Coverage Delta Example

Code coverage gaps produce type-specific identifier fields in the delta:

```json
{
  "gap_id": "GAP_B001",
  "coverage_type": "branch",
  "before_hit_count": 0,
  "after_hit_count": 3,
  "closed": true,
  "source_file": "rtl/dma_desc_parser.sv",
  "source_line": 78,
  "branch_type": "if",
  "direction": "false"
}
```

The summary section includes a by_type breakdown:

```json
{
  "summary": {
    "total_gaps": 27,
    "newly_covered": 5,
    "regressed": 0,
    "unchanged": 22,
    "by_type": {
      "functional": {"total": 15, "newly_covered": 3, "regressed": 0, "unchanged": 12},
      "branch": {"total": 2, "newly_covered": 1, "regressed": 0, "unchanged": 1},
      "toggle": {"total": 2, "newly_covered": 1, "regressed": 0, "unchanged": 1},
      "line": {"total": 2, "newly_covered": 0, "regressed": 0, "unchanged": 2}
    }
  }
}
```

## Analysis Workflow

### Single Gap Analysis

1. **Check gap state**: Look at the `closed`, `regressed`, or `unchanged` flag
2. **Review hit counts**: Compare before_hit_count vs after_hit_count
3. **Verify coverage target**: Confirm type-specific identifier matches the gap (covergroup/coverpoint/bin for functional; source_file/line for code coverage; signal/module for toggle)
4. **Determine next action**: Based on state (see below)

### Multi-Gap Analysis

When multiple gaps change simultaneously:

1. **Sort by state**: Group closed, regressed, unchanged
2. **Check for correlations**: Did closing one gap cause regression in another?
3. **Prioritize**: Focus on closed gaps first (success), then regressed (issues)
4. **Document**: Record which test closed which gaps

## Failure Mode Analysis

When a gap remains unchanged after a targeted test, analyze these 4 failure modes:

### Failure Mode 1: Stimulus Did Not Reach

**Symptoms**:
- Test passed but gap unchanged
- No errors in log
- Stimulus generation may have been skipped

**Diagnosis**:
1. Search log for stimulus generation messages
2. Check if sequence was actually started
3. Verify stimulus reached the DUT

**Fix**:
- Ensure sequence is called in test
- Add debug prints to verify stimulus generation
- Check sequencer arbitration

### Failure Mode 2: Stimulus Reached But Insufficient

**Symptoms**:
- Test passed
- Stimulus generated but gap unchanged
- Hit count may have increased but not enough to close

**Diagnosis**:
1. Check hit_count delta (before vs after)
2. Review stimulus parameters (length, count, values)
3. Verify stimulus matches bin requirements

**Fix**:
- Increase stimulus count or duration
- Adjust stimulus parameters to target bin
- Add directed stimulus if constrained random insufficient

### Failure Mode 3: Coverage Model Issue

**Symptoms**:
- Stimulus appears correct
- Gap unchanged
- Other similar gaps may also be unchanged

**Diagnosis**:
1. Review coverpoint sampling conditions
2. Check if stimulus timing aligns with sampling edge
3. Verify coverpoint is enabled

**Fix**:
- Adjust stimulus timing
- Add explicit sample calls if needed
- Review coverpoint definition

### Failure Mode 4: Configuration Missing

**Symptoms**:
- Stimulus generated
- Gap unchanged
- Feature may not be enabled

**Diagnosis**:
1. Check if required configuration was applied
2. Verify enable bits are set
3. Review mode settings

**Fix**:
- Add missing configuration in test build_phase
- Verify configuration took effect (read back registers)
- Check configuration order dependencies

## Regression Analysis

When a gap regresses (hit count decreases):

1. **Identify the change**: What changed between before and after?
   - New test added
   - Existing test modified
   - Constraint changes
   - Coverage model changes

2. **Check for side effects**:
   - Did the new test modify shared state?
   - Did constraint changes exclude previously covered bins?
   - Did timing changes prevent sampling?

3. **Determine severity**:
   - Small regression (1-2 hits): May be acceptable
   - Large regression (>10 hits): Requires investigation
   - Regression to 0: Critical - feature no longer tested

4. **Apply fix**:
   - Revert problematic changes
   - Adjust constraints to include both old and new bins
   - Add separate test for regressed bins

## Multi-Test Correlation

When running multiple tests:

1. **Track per-test coverage**: Which test closed which gap?
2. **Check for overlap**: Multiple tests closing same gap is OK
3. **Check for conflicts**: One test closes, another regresses same gap
4. **Optimize**: Remove redundant tests, keep most effective

## Coverage Diff Best Practices

1. **Run diff after each test**: Don't wait until end of regression
2. **Document results**: Record which test closed which gap
3. **Investigate unchanged**: If targeted test did not close gap, analyze why
4. **Monitor regressions**: Any regression requires root cause analysis
5. **Celebrate closures**: Track progress toward coverage goals

## Relationship to Other References

- log_analysis_rules.md: Diagnose test failures when gap unchanged
- scenario_patterns.md: Design effective stimulus to close gaps
- cov_get_coverage_diff tool: Compute diff from before/after databases

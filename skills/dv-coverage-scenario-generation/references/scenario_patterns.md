# Scenario Patterns by Gap Classification

This document provides guidance on designing stimulus scenarios based on gap classification.
It complements gap_classification.md which defines classification criteria.

## Pattern Selection by Classification

### Missing Stimulus

**Characteristics**: Gap has 0% coverage, no existing tests target this feature.

**Typical stimulus structure**:
1. Identify configuration prerequisites (registers, modes)
2. Generate stimulus that exercises the uncovered bin/coverpoint
3. Add assertions or monitors to verify expected behavior
4. Ensure stimulus duration is sufficient for sampling

**Confidence calibration**:
- **high**: Clear spec requirement + straightforward stimulus path
- **medium**: Spec exists but stimulus requires complex setup
- **low**: Spec ambiguous or stimulus path unclear

### Config Missing

**Characteristics**: Feature exists but required configuration is not applied.

**Typical stimulus structure**:
1. Identify missing configuration (register field, mode bit)
2. Apply configuration before stimulus
3. Generate minimal stimulus to trigger sampling
4. Verify configuration took effect

**Confidence calibration**:
- **high**: Configuration field clearly documented, single-bit enable
- **medium**: Multi-field configuration, ordering constraints
- **low**: Configuration side effects unclear

### Constraint Too Tight

**Characteristics**: Stimulus exists but constraints prevent reaching the bin.

**Typical stimulus structure**:
1. Analyze constraint bounds vs. bin requirements
2. Relax constraints or add constraint override
3. Verify relaxed constraints still produce valid transactions
4. May require directed seed or constraint partition

**Confidence calibration**:
- **high**: Constraint relaxation is straightforward, no side effects
- **medium**: Requires constraint partitioning or multiple scenarios
- **low**: Constraint relaxation may break other coverage or assertions

### Coverage Model Issue

**Characteristics**: Stimulus and config appear correct, but coverage not sampled.

**Typical stimulus structure**:
1. Verify coverpoint sampling conditions (clock, reset, enable)
2. Check if stimulus timing aligns with sampling edge
3. May require adding explicit sample calls or adjusting timing
4. Consider if coverpoint definition matches spec intent

**Confidence calibration**:
- **high**: Clear timing mismatch, fix is localized
- **medium**: Requires coverpoint definition review
- **low**: May need coverage model redesign

### Monitor Sampling Issue

**Characteristics**: Monitor not observing transactions, or sampling logic incorrect.

**Typical stimulus structure**:
1. Verify monitor is enabled and connected
2. Check if stimulus reaches monitor observation point
3. Verify sampling conditions in monitor
4. May require adding debug prints to monitor

**Confidence calibration**:
- **high**: Monitor enable bit missing
- **medium**: Monitor connection or protocol issue
- **low**: Monitor logic fundamentally flawed

### Unreachable Candidate

**Characteristics**: Gap appears structurally unreachable (RTL constant, generate condition).

**Typical stimulus structure**:
1. **Do not generate stimulus** until reachability confirmed
2. Document evidence for unreachable determination
3. Escalate for formal waiver or RTL change

**Confidence calibration**:
- Not applicable - requires human review

## Compound Classification Patterns

When a gap exhibits multiple classifications (e.g., Config Missing + Missing Stimulus):

1. Address Config Missing first (prerequisite)
2. Then apply Missing Stimulus pattern
3. Document both in scenario card

## Confidence Calibration Rules

| Evidence | Confidence |
|----------|-----------|
| Spec section exists + clear stimulus path | high |
| Spec exists + complex setup required | medium |
| Spec ambiguous or missing | low |
| Existing similar test in testbench | high |
| No similar tests, novel scenario | medium/low |
| Register field documented in RAL | high |
| Register field only in spec | medium |

## Relationship to Other References

- gap_classification.md: Defines classification criteria
- scenario_patterns.md (this file): Guides stimulus design after classification
- protocol_scenario_templates.md: Provides concrete protocol-specific templates

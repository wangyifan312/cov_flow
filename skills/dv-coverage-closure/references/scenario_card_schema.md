# Scenario Card Schema Guide

Human-readable guide for filling in scenario card fields. This complements (not duplicates) `schemas/scenario_card.schema.json`.

## Field Reference

### gap_id
The coverage gap identifier this scenario targets. Must match an existing gap in `coverage_gaps.json`.
- Format: `GAP_XXXX` (4-digit zero-padded number)

### target_coverage
The specific coverage point this scenario aims to hit.

| Sub-field | Description |
|-----------|-------------|
| `covergroup` | The covergroup name (e.g., `dma_desc_cg`) |
| `coverpoint` | The coverpoint within the covergroup (e.g., `desc_mode_cp`) |
| `bin` | The specific bin to hit (e.g., `linked_list`) |

Map these directly from the gap detail returned by `cov_get_gap_detail`.

### classification
The gap classification from triage. Must be one of:
`Missing Stimulus` | `Config Missing` | `Constraint Too Tight` | `Coverage Model Issue` | `Monitor Sampling Issue` | `Unreachable Candidate`

Compound labels allowed (e.g., `Config Missing + Missing Stimulus`).

### semantic_interpretation
A plain-language explanation of **what the coverage point represents** and **why it is not being hit**. Minimum 10 characters. This should synthesize evidence from coverage source, spec, and registers into a human-readable narrative.

### required_config
List of register writes or configuration steps needed before the stimulus can exercise the target feature.

Each entry has:
- `register` (required): Register path (e.g., `DMA_CFG.LL_MODE_EN`)
- `value` (required): The value to write
- `constraint` (optional): Additional constraint description (e.g., `non_zero`, `aligned_to_4K`)

### stimulus
Ordered list of stimulus actions the testbench must perform. Each item is a short descriptive string (not code).

Minimum 1 item. Examples:
- "program descriptor base address"
- "build two linked descriptors"
- "start DMA channel"

### expected_behavior
Ordered list of observable behaviors that confirm the feature was exercised correctly.

Minimum 1 item. Examples:
- "descriptor parser enters LINK_DESC state"
- "next descriptor is fetched"
- "completion interrupt is generated"

### tb_reuse (optional)
Identifies existing testbench components that can be reused.

| Sub-field | Description |
|-----------|-------------|
| `base_test` | The base test class to extend |
| `candidate_sequence` | An existing sequence that can be extended or composed |

### confidence
How confident the agent is in this scenario card, based on evidence completeness:

| Level | Criteria |
|-------|----------|
| `high` | Full evidence chain: coverage source + spec section + register fields + existing TB reuse path all confirmed |
| `medium` | Partial evidence: some fields confirmed but others inferred or missing |
| `low` | Weak evidence: classification is uncertain, multiple assumptions made |

**Rule**: Lower confidence when evidence is insufficient. Never claim `high` without a complete evidence chain.

### risk (optional)
List of risk factors or open questions that could prevent the scenario from working as expected. Each item is a short string.

Examples:
- "confirm linked-list mode is enabled in current build configuration"
- "memory allocation helper may not support chained descriptors"

## Abstract Template

```yaml
gap_id: GAP_XXXX
target_coverage:
  covergroup: <covergroup_name>
  coverpoint: <coverpoint_name>
  bin: <bin_name>
classification: <classification_label>
semantic_interpretation: |
  <What the coverage point represents and why it is not being hit.
   Synthesize from coverage source, spec, and register evidence.>
required_config:
  - register: <REG_PATH.FIELD>
    value: <value>
    constraint: <optional constraint>
stimulus:
  - <stimulus action 1>
  - <stimulus action 2>
expected_behavior:
  - <observable behavior 1>
  - <observable behavior 2>
tb_reuse:
  base_test: <base_test_class>
  candidate_sequence: <existing_sequence>
confidence: high | medium | low
risk:
  - <risk factor 1>
```

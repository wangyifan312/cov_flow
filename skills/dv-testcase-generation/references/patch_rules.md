# Patch Metadata Rules

Rules for generating valid patch metadata that conforms to testcase_patch.schema.json.

## Patch Output Structure

A testcase patch is a JSON document describing new and modified files for a coverage gap closure.

### Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `patch_id` | string | Unique patch identifier |
| `gap_id` | string | Coverage gap this patch addresses |
| `classification` | string | Gap classification category |
| `base_reuse` | object | References to reused base components |
| `new_files` | array | List of new file paths |
| `modified_files` | array | List of modified file paths |
| `compile_command` | string | Command to compile the patch |
| `run_command` | string | Command to run the patch |
| `coverage_targets` | array | List of coverage targets |
| `review_checklist` | array | Pre-review checks |

## Field-by-Field Rules

### patch_id

**Format**: `patch_{gap_id}_{timestamp}` or `patch_{gap_id}_{seq}`

```json
"patch_id": "patch_GAP_0001_001"
```

**Rules**:
- Must start with `patch_`
- Must reference the gap_id
- Must be unique across all patches

### gap_id

**Format**: `GAP_NNNN` (matches coverage_gaps.json)

```json
"gap_id": "GAP_0001"
```

**Rules**:
- Must exist in coverage_gaps.json
- Must match the gap being addressed

### classification

**Enum**: One of the 6 valid classifications

```json
"classification": "Missing Stimulus"
```

**Rules**:
- Must match the gap's classification from triage
- Must be one of: Missing Stimulus, Config Missing, Constraint Too Tight,
  Coverage Model Issue, Monitor Sampling Issue, Unreachable Candidate

### base_reuse

**Structure**: References to existing testbench components

```json
"base_reuse": {
  "base_test": "dma_base_test",
  "base_sequence": "dma_base_seq",
  "config_knobs": ["num_iterations", "timeout_ns"]
}
```

**Rules**:
- base_test must exist in tb_index
- base_sequence must exist in tb_index (or be null if not applicable)
- config_knobs must exist in tb_index (or be empty array)
- Use `tb_get_existing_tests_for_feature` to find valid references

### new_files

**Structure**: Array of file paths relative to project root

```json
"new_files": [
  "tests/dma/dma_linked_list_desc_test.sv",
  "sequences/dma/dma_descriptor_chain_seq.sv"
]
```

**Rules**:
- Paths are relative to project root
- New files do not need to exist at validation time
- Parent directory should exist (or be created by patch application)
- Use when creating entirely new test/sequence files

### modified_files

**Structure**: Array of file paths relative to project root

```json
"modified_files": [
  "tests/dma/dma_regression_test.sv"
]
```

**Rules**:
- Paths are relative to project root
- Modified files must exist at validation time
- Use when extending existing tests (e.g., adding to regression list)
- Prefer new_files over modified_files when possible

### compile_command / run_command

**Rules**:
- Must come from manifest command templates
- Use `{test}` and `{seed}` placeholders
- Example: `"make compile TEST={test}"`

```json
"compile_command": "make compile TEST=dma_linked_list_desc_test",
"run_command": "make run TEST=dma_linked_list_desc_test SEED=1"
```

**Validation**:
- static_patch_check verifies these are non-empty
- Commands must match manifest templates

### coverage_targets

**Structure**: Array of coverage target objects

```json
"coverage_targets": [
  {
    "covergroup": "dma_descriptor_cov",
    "coverpoint": "descriptor_type",
    "bin": "linked_list_desc"
  }
]
```

**Rules**:
- Each target must have at least 3 dot-separated segments
  (covergroup.coverpoint.bin or covergroup.cross.bin)
- Must reference the gap's coverage target
- Use `cov_get_gap_detail` to get the correct hierarchy

### review_checklist

**Structure**: Array of checklist items

```json
"review_checklist": [
  "Verify base_test inheritance is correct",
  "Check RAL paths match register index",
  "Confirm sequence compiles without errors",
  "Run targeted test with seed=1 to verify pass",
  "Check coverage report shows gap closed"
]
```

**Rules**:
- Must be non-empty
- Should include compile verification
- Should include run verification
- Should include coverage verification
- Should include any project-specific checks

## new_files vs modified_files

### When to Use new_files

- Creating a new test class
- Creating a new sequence
- Adding new utility components
- Test is self-contained and does not require changes to existing files

### When to Use modified_files

- Adding test to a regression list
- Extending an existing virtual sequence
- Updating include files
- Changes require coordination with existing code

**Best Practice**: Prefer new_files when possible. Modified files have higher risk
of breaking existing tests and require more careful review.

## Validation Workflow

1. **Generate patch JSON** following rules above
2. **Run schema validation**:
   ```bash
   python scripts/validate_patch_metadata.py --file patch.json
   ```
3. **Run static checks**:
   ```bash
   python scripts/static_patch_check.py --file patch.json --manifest manifest.yaml
   ```
4. **Fix any errors** reported by validators
5. **Apply patch** and compile/run

## Common Mistakes

### Mistake: Fabricated base_test

```json
"base_reuse": {
  "base_test": "fake_base_test"  // Does not exist in tb_index
}
```

**Fix**: Use `tb_get_existing_tests_for_feature` to find real base_test.

### Mistake: Empty modified_files when new_files suffice

```json
"new_files": ["tests/new_test.sv"],
"modified_files": ["tests/regression_list.sv"]  // Unnecessary modification
```

**Fix**: Remove modified_files entry if not strictly needed.

### Mistake: Coverage target with insufficient segments

```json
"coverage_targets": [
  {
    "covergroup": "dma_cov",
    "coverpoint": "type"
    // Missing: bin
  }
]
```

**Fix**: Include all 3 segments: covergroup, coverpoint, bin.

### Mistake: Hardcoded commands instead of templates

```json
"compile_command": "vcs -full64 -f filelist.f"  // Should use template
```

**Fix**: Use manifest template with `{test}` placeholder.

## Relationship to Other References

- uvm_generation_rules.md: UVM-specific code generation rules
- compile_check_rules.md: Pre-compile validation (static_patch_check.py checks)
- testcase_patch.schema.json: Formal schema definition

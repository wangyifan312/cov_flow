# Compile Check Rules

Pre-compile validation checklist and compile failure debugging guide.
Corresponds to the 6 checks in static_patch_check.py.

## Pre-Compile Checklist

Before attempting compilation, verify these 6 items:

### 1. new_files Paths

**Check**: All paths in new_files are valid file locations.

**What to verify**:
- File extension is correct (.sv, .svh, .v)
- Directory structure exists (or will be created)
- File name follows project conventions

**Common errors**:
- Typo in directory name
- Missing parent directory
- Wrong file extension

### 2. modified_files Existence

**Check**: All paths in modified_files exist in the project.

**What to verify**:
- File exists at the specified path
- File is not read-only or locked
- File is part of the current project (not a stale reference)

**Common errors**:
- File was renamed or moved
- Path is relative to wrong base directory
- File was deleted in a recent change

### 3. base_test in tb_index

**Check**: The base_test referenced in base_reuse exists in the testbench index.

**What to verify**:
- base_test class name matches tb_index entry
- base_test is in a package that will be compiled
- base_test is not abstract (can be instantiated)

**Common errors**:
- Typo in class name
- base_test was renamed
- base_test is in a package not included in filelist

### 4. base_sequence in tb_index

**Check**: The base_sequence referenced in base_reuse exists in the testbench index.

**What to verify**:
- base_sequence class name matches tb_index entry
- base_sequence is in a package that will be compiled
- base_sequence is compatible with the target sequencer

**Common errors**:
- Typo in class name
- base_sequence was renamed
- base_sequence requires parameters not provided

### 5. coverage_targets Format

**Check**: Each coverage target has at least 3 dot-separated segments.

**What to verify**:
- covergroup name is valid
- coverpoint name is valid
- bin name is valid (or cross name)
- Hierarchy matches coverage model

**Common errors**:
- Missing bin (only 2 segments)
- Typo in covergroup/coverpoint name
- Bin was renamed in coverage model

### 6. review_checklist Non-Empty

**Check**: The review_checklist array is not empty.

**What to verify**:
- At least one checklist item exists
- Checklist items are actionable (not vague)
- Checklist covers compile, run, and coverage verification

**Common errors**:
- Empty array
- Items are too generic ("check everything")
- Missing coverage verification step

## Running Static Checks

Use static_patch_check.py to automate these checks:

```bash
python scripts/static_patch_check.py \
  --file patch.json \
  --manifest mock_data/dma_subsystem/project_manifest.yaml
```

**Expected output**: JSON report with pass/fail for each check.

**If any check fails**:
1. Read the error message
2. Fix the corresponding field in patch.json
3. Re-run static_patch_check
4. Repeat until all checks pass

## Compile Failure Debugging

When compilation fails, follow this systematic approach:

### Step 1: Read the Error Message

Compile errors typically include:
- File name and line number
- Error type (syntax, type mismatch, undefined symbol)
- Context (surrounding code)

### Step 2: Categorize the Error

| Error Type | Common Causes | Fix |
|------------|---------------|-----|
| **Undefined class** | Missing import, typo in class name | Add import or fix name |
| **Undefined symbol** | Missing variable, wrong scope | Check variable declaration |
| **Type mismatch** | Wrong data type, missing cast | Add cast or fix type |
| **Syntax error** | Missing semicolon, bracket, keyword | Fix syntax |
| **Duplicate definition** | Multiple files define same class | Remove duplicate or rename |
| **Package not found** | Missing package in filelist | Add to filelist.f |

### Step 3: Locate the Source

- If error is in generated code: fix the generation logic
- If error is in base code: check if modification was unintended
- If error is in include file: check include path

### Step 4: Apply Fix and Re-compile

- Fix the root cause (not just the symptom)
- Re-run compile command
- If new errors appear, repeat from Step 1

## Common Compile Error Patterns

### Pattern 1: Undefined Base Test

```
Error: Undefined type 'dma_base_test'
```

**Cause**: base_test not imported or not in filelist.

**Fix**:
1. Check if dma_base_test is in tb_index
2. Verify the package containing it is in filelist.f
3. Add `import dma_env_pkg::*;` to generated test file

### Pattern 2: Undefined RAL Path

```
Error: 'ral.fake_reg' is not a member of 'ral_model'
```

**Cause**: RAL path does not exist in register model.

**Fix**:
1. Use `reg_find_fields_affecting_feature` to find valid paths
2. Update generated code with correct RAL path
3. Re-verify with static_patch_check

### Pattern 3: Sequencer Type Mismatch

```
Error: Type mismatch in 'seq.start(seqr)' - expected 'uvm_sequencer#(dma_seq_item)'
```

**Cause**: Sequence item type does not match sequencer.

**Fix**:
1. Check the sequencer's item type in tb_index
2. Ensure sequence generates correct item type
3. May need to parameterize the sequence

### Pattern 4: Missing Include

```
Error: Cannot open include file 'dma_macros.svh'
```

**Cause**: Include path not in compile options or file does not exist.

**Fix**:
1. Check if include file exists
2. Add include path to compile command: `+incdir+path/to/includes`
3. Or add to filelist.f

### Pattern 5: Duplicate Class Definition

```
Error: Class 'my_test' already defined in another file
```

**Cause**: Same class name in multiple files.

**Fix**:
1. Rename one of the classes
2. Or remove the duplicate file from filelist

## Compile Success Criteria

Compilation is successful when:
- Exit code is 0
- No ERROR messages in compile log
- Warnings are reviewed and accepted (not ignored)
- All generated files are compiled
- All dependencies are resolved

## Post-Compile Verification

After successful compilation:
1. Run the test with a smoke seed (seed=1)
2. Verify test completes without runtime errors
3. Check coverage report for the target gap
4. If gap not closed, analyze why (see coverage_diff_rules.md)

## Relationship to Other References

- patch_rules.md: Patch metadata format
- static_patch_check.py: Automated validation tool
- uvm_generation_rules.md: Code generation rules
- log_analysis_rules.md: Runtime failure debugging

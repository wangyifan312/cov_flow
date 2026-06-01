# Testcase Generation Rules

Rules and constraints for generating UVM testcase/sequence patches from scenario cards.

## Core Principle

All generated code must **reuse existing testbench infrastructure**. Never generate standalone tests that bypass the existing UVM hierarchy.

## Reuse Requirements

| Component | Rule |
|-----------|------|
| Base test | Must extend an existing base test class (from `tb_get_existing_tests_for_feature`) |
| Base sequence | Must extend or compose with an existing sequence (from `tb_get_existing_tests_for_feature`) |
| Config knobs | Must use existing config knobs and RAL paths (from `reg_find_fields_affecting_feature`) |
| Virtual sequencer | Must target an existing virtual sequencer path |

## Prohibited Actions

- **Do not directly modify trunk files.** All changes go through patch files (new files + modified file diffs).
- **Do not fabricate non-existent UVM components.** If a base test, sequence, or config knob does not exist in the testbench index, do not reference it.
- **Do not generate full test files from scratch.** Always extend an existing base class.
- **Do not include hardcoded addresses or magic numbers** without referencing register definitions.

## Patch Metadata Fields

### patch_id
Unique identifier for the patch.
- Format: `PATCH_GAP_(XXXX|XNNN)_NNN` where XXXX = 4-digit functional gap number, XNNN = letter-prefixed code coverage gap (L/B/C/T/M/A), NNN = patch variant (starting from 001)

### gap_id
The coverage gap this patch targets. Must match the scenario card's gap_id.

### new_files
List of new files to create (e.g., new sequence file, new test file).
- Paths relative to project testbench root

### modified_files
List of existing files that need modification (e.g., adding a factory override, updating a test list).
- Empty list if no existing files are modified

### base_reuse
Documents which existing components are being reused:
- `base_test` (required): The base test class being extended
- `base_sequence` (optional): The base sequence being extended or composed

### compile_command
The compile command for this patch. Must follow the manifest's `compile_cmd_template`.
- Example: `make compile TEST=<new_test_name>`

### run_command
The simulation run command. Must follow the manifest's `run_cmd_template`.
- Example: `make run TEST=<new_test_name> SEED=1`

### coverage_target
List of coverage targets this patch aims to hit. Format depends on coverage type:
- Functional: `<covergroup>.<coverpoint>.<bin>`
- Line/Branch/Condition: `<source_file>:<line>`
- Toggle: `<module>.<signal>[<direction>]`
- FSM: `<module>.<fsm_name>.<state>`
- Assert: `<source_file>:<assert_name>`
- Minimum 1 item

### review_checklist
List of items the engineer must verify before merging the patch.
- Minimum 1 item

## Static Check List

Before presenting a patch for review, verify:

1. **Class name references**: All `extends` targets exist in the TB index
2. **File paths**: All new file paths are under the testbench sequence/test directories
3. **RAL paths**: All register references use valid RAL paths from the register index
4. **Base test**: The referenced base test exists in the TB index
5. **Sequence hierarchy**: The sequence targets a valid virtual sequencer
6. **No duplicate definitions**: New class names do not conflict with existing classes

## Generation Output Structure

```yaml
patch_id: PATCH_GAP_(XXXX|XNNN)_NNN
gap_id: GAP_(XXXX|XNNN)
new_files:
  - tb/sequences/<new_sequence>.sv
  - tb/tests/<new_test>.sv
modified_files: []
base_reuse:
  base_test: <existing_base_test>
  base_sequence: <existing_base_sequence>
compile_command: make compile TEST=<new_test>
run_command: make run TEST=<new_test> SEED=1
coverage_target:
  - <covergroup>.<coverpoint>.<bin>  # functional
  # or <source_file>:<line>          # line/branch/condition
  # or <module>.<signal>[<dir>]      # toggle
  # or <module>.<fsm_name>.<state>   # fsm
review_checklist:
  - confirm RAL path for <register.field>
  - confirm <helper> supports <feature>
  - confirm sequence starts on correct virtual sequencer
```

# UVM Code Generation Rules

Detailed rules for generating UVM testcases, sequences, and components.
This extends the generic rules defined in `skills/dv-coverage-closure/references/testcase_generation_rules.md` with UVM-specific guidance.

## Inheritance and Reuse Requirements

### Base Test Inheritance

**Rule**: All generated tests must inherit from an existing base_test.

```systemverilog
class {test_name} extends {base_test};
  `uvm_component_utils({test_name})
  
  function new(string name, uvm_component parent);
    super.new(name, parent);
  endfunction
  
  // Override build_phase or run_phase as needed
endclass
```

**Validation**:
- base_test must exist in tb_index
- Use `tb_get_existing_tests_for_feature` to find suitable base_test
- Never create a test that inherits directly from uvm_test

### Base Sequence Reuse

**Rule**: Generated sequences must extend existing base_sequence or virtual_sequence.

```systemverilog
class {seq_name} extends {base_sequence};
  `uvm_object_utils({seq_name})
  
  function new(string name = "{seq_name}");
    super.new(name);
  endfunction
  
  task body();
    // Call super.body() if needed
    // Add scenario-specific stimulus
  endtask
endclass
```

**Validation**:
- base_sequence must exist in tb_index
- Prefer extending sequences related to the target feature
- Avoid duplicating stimulus logic from base_sequence

### Config Knob Usage

**Rule**: Use existing config_knob mechanisms for test configuration.

```systemverilog
// In test build_phase:
uvm_config_db#(int)::set(this, "*", "{knob_name}", {value});

// In sequence:
if (!uvm_config_db#(int)::get(null, "", "{knob_name}", cfg_val))
  `uvm_fatal("CFG", "Failed to get {knob_name}")
```

**Validation**:
- config_knob must exist in tb_index
- Use knobs for parameterizing scenarios (timeouts, iteration counts, modes)
- Do not hardcode values that should be configurable

## Prohibited Practices

### No Fabricated Class Names

**Forbidden**: Creating class names that do not exist in the testbench.

```systemverilog
// WRONG: fake_monitor does not exist
class my_test extends base_test;
  fake_monitor mon;  // Compile error
endclass

// CORRECT: use actual monitor from tb_index
class my_test extends base_test;
  dma_monitor mon;  // Verified to exist
endclass
```

### No Fabricated RAL Paths

**Forbidden**: Using register paths not defined in the RAL model.

```systemverilog
// WRONG: fabricated path
ral.fake_reg.field.write(status, 8'hFF);

// CORRECT: verified RAL path
ral.dma_ctrl.enable.write(status, 1'b1);
```

**Validation**:
- Use `reg_find_fields_affecting_feature` to find valid RAL paths
- Cross-check with register index

### No Fabricated Sequencer Paths

**Forbidden**: Referencing sequencers that do not exist.

```systemverilog
// WRONG: fabricated sequencer
seq.start(p_sequencer.fake_seqr);

// CORRECT: verified sequencer path
seq.start(p_sequencer.dma_seqr);
```

### No Direct Trunk Modification

**Forbidden**: Modifying base_test, base_sequence, or environment directly.

**Correct approach**:
- Extend base_test for test-specific configuration
- Extend base_sequence for scenario-specific stimulus
- Use config_db for runtime parameterization
- Create new sequences rather than patching existing ones

## Code Structure Requirements

### File Naming Conventions

| Type | Pattern | Example |
|------|---------|---------|
| Test | `{feature}_{scenario}_test.sv` | `dma_linked_list_desc_test.sv` |
| Sequence | `{feature}_{scenario}_seq.sv` | `dma_descriptor_chain_seq.sv` |
| Virtual Sequence | `{feature}_{scenario}_vseq.sv` | `dma_multi_channel_vseq.sv` |

### Class Naming Conventions

| Type | Pattern | Example |
|------|---------|---------|
| Test | `{feature}_{scenario}_test` | `dma_linked_list_desc_test` |
| Sequence | `{feature}_{scenario}_seq` | `dma_descriptor_chain_seq` |
| Config | `{feature}_config` | `dma_config` |

### Include Guards

All generated files must use include guards:

```systemverilog
`ifndef {FEATURE}_{SCENARIO}_TEST_SV
`define {FEATURE}_{SCENARIO}_TEST_SV

// ... class definition ...

`endif // {FEATURE}_{SCENARIO}_TEST_SV
```

### Package Imports

Required imports for generated code:

```systemverilog
import uvm_pkg::*;
`include "uvm_macros.svh"

// Project-specific packages (from tb_index)
import {project}_ral_pkg::*;
import {project}_env_pkg::*;
```

## Generation Workflow

1. **Query context**:
   - `cov_get_gap_detail` → understand coverage target
   - `tb_get_existing_tests_for_feature` → find base_test, base_sequence, config_knob
   - `reg_find_fields_affecting_feature` → find RAL paths

2. **Select inheritance**:
   - Choose base_test related to feature
   - Choose base_sequence related to stimulus type

3. **Generate skeleton**:
   - Test class with build_phase override
   - Sequence class with body task
   - Apply config_db for parameters

4. **Add stimulus logic**:
   - Use protocol templates from protocol_scenario_templates.md
   - Fill in RAL paths from register index
   - Add assertions or checks if needed

5. **Validate**:
   - Run static_patch_check to verify paths and references
   - Check compile before committing

## Common Patterns

### Directed Test Pattern

```systemverilog
class {test_name} extends {base_test};
  `uvm_component_utils({test_name})
  
  function new(string name, uvm_component parent);
    super.new(name, parent);
  endfunction
  
  virtual function void build_phase(uvm_phase phase);
    super.build_phase(phase);
    // Override config
    uvm_config_db#(int)::set(this, "*", "num_iterations", 10);
  endfunction
  
  task run_phase(uvm_phase phase);
    phase.raise_objection(this);
    // Create and start sequence
    {seq_name} seq = {seq_name}::type_id::create("seq");
    seq.start(env.seqr);
    phase.drop_objection(this);
  endtask
endclass
```

### Constrained Random Pattern

```systemverilog
class {seq_name} extends {base_sequence};
  `uvm_object_utils({seq_name})
  
  rand int unsigned num_transactions;
  
  constraint c_num_trans {
    num_transactions inside {[5:20]};
  }
  
  task body();
    repeat (num_transactions) begin
      // Generate constrained random stimulus
    end
  endtask
endclass
```

## Relationship to Other References

- testcase_generation_rules.md: Generic rules (this file extends with UVM details)
- patch_rules.md: Output format for generated patches
- compile_check_rules.md: Pre-compile validation checklist

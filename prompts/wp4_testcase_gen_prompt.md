# WP-4 Coding Agent Prompt: Targeted UVM Testcase Generation for GAP_0006

## Objective

Generate a **targeted UVM testcase** (virtual sequence + test) to close coverage gap **GAP_0006** (AHB burst type `wrap8`). This is an experiment to validate the Agent-based testcase generation workflow: coverage gap -> MCP tool context collection -> SV code generation.

## Background

### What is GAP_0006?

```json
{
  "gap_id": "GAP_0006",
  "coverage_type": "functional",
  "covergroup": "axi2ahb_pkg::axi2ahb_coverage::ahb_cg",
  "coverpoint": "cp_ahb_burst",
  "bin": "wrap8",
  "hit_count": 0,
  "goal": 1,
  "classification": "Missing Stimulus",
  "priority": "P1"
}
```

The `cp_ahb_burst` coverpoint in `ahb_cg` samples the AHB burst type. The `wrap8` bin corresponds to `ahb_pkg::WRAP8`. The AXI-to-AHB bridge translates AXI `WRAP` burst with `len=8` into AHB `WRAP8`.

### Why does the existing test not close this gap?

The existing `wrap_random_len_size_wr_test` uses `wrap_random_len_size_wr_virt_seq` which randomizes `len` inside `{2, 4, 8, 16}`. While it *can* produce `len=8`, the randomization space is very large (`sequence_length` = 50-100, alternating write/read, 4 sizes, many address options), so wrap8 may not be reliably hit in a short regression. A **targeted** sequence that forces `len=8` every iteration will deterministically close this gap.

## Project Root

The UVM project is at:
```
/Users/wangyifan/Desktop/AI/project_x2h/AXI2AHB-Lite-Bridge-UVM-Verification/
```

## Step 1: Collect Context via MCP Tools (Already Done)

For reference, here is what the MCP tools returned for GAP_0006. You do NOT need to run these tools — the results are provided inline.

### tb_find_tests_for_gap result (summary)

- **semantic_keywords**: `["8", "ahb", "burst", "wrap"]`
- **matching_sequences**: `base_virtual_sequence` (relevance=1.0), `wrap_random_len_size_wr_virt_seq` (relevance=0.6)
- **matching_tests**: `wrap_random_len_size_wr_test` (relevance=0.53)
- **gap_assessment**: `existing_test_likely_covers` (confidence=1.0) — existing test CAN cover this, but a targeted test would be more efficient

### Key API method from base_virtual_sequence

```systemverilog
virtual task fd_write_burst(
    bit [`ADDR_WIDTH-1:0] addr,
    int                   no_of_beats,
    bit [`DATA_WIDTH-1:0] data[],
    axi_burst_type_e      burst,
    axi_size_e            size,
    output axi_resp_e     resp
);

virtual task fd_read_burst(
    bit [`ADDR_WIDTH-1:0] addr,
    int                   no_of_beats,
    axi_burst_type_e      burst,
    axi_size_e            size,
    output bit [`DATA_WIDTH-1:0] data[],
    output axi_resp_e     resp[]
);
```

### Coverage model sampling (from axi2ahb_cov.sv write_slv())

```systemverilog
ahb_burst = tr.burst;   // AHB burst type from the AHB transaction
// ...
ahb_cg.sample();
```

The `cp_ahb_burst` coverpoint bins:
```systemverilog
cp_ahb_burst : coverpoint ahb_burst {
    bins single = {ahb_pkg::SINGLE};
    bins incr   = {ahb_pkg::INCR};
    bins wrap4  = {ahb_pkg::WRAP4};
    bins incr4  = {ahb_pkg::INCR4};
    bins wrap8  = {ahb_pkg::WRAP8};   // <-- THIS IS THE TARGET
    bins incr8  = {ahb_pkg::INCR8};
    bins wrap16 = {ahb_pkg::WRAP16};
    bins incr16 = {ahb_pkg::INCR16};
}
```

Also, `cr_ahb_rw_burst` is a cross of `cp_ahb_rw` x `cp_ahb_burst`, so doing both write AND read with WRAP8 will also hit the cross bins (`write,wrap8` and `read,wrap8`).

### AXI/ AHB burst type enums

```systemverilog
// axi_type.svh (AXI side)
typedef enum bit [1:0] {
    FIXED = 2'b00,
    INCR  = 2'b01,
    WRAP  = 2'b10
} axi_burst_type_e;

// ahb_type.svh (AHB side)
typedef enum {
    SINGLE, INCR, WRAP4, INCR4, WRAP8, INCR8, WRAP16, INCR16
} ahb_burst_e;
```

The bridge maps AXI `WRAP` with `len=N` to AHB `WRAPN` (WRAP4 for len=4, WRAP8 for len=8, etc.).

## Step 2: Reference Templates (Existing Code)

### Template 1: wrap_random_len_size_wr_virt_seq.sv (the existing sequence — your template)

This is the **primary template**. Your new sequence should be a simplified, targeted version of this.

Key patterns to follow:
- `extends base_virtual_sequence`
- `` `uvm_object_utils(wrap8_targeted_virt_seq) ``
- Constraints force `len=8` for every transaction (not randomized over {2,4,8,16})
- Uses `fd_write_burst(addr, len, beats, axi_pkg::WRAP, size, bresp)` for frontdoor write
- Uses `fd_read_burst(addr, len, axi_pkg::WRAP, size, read_beats, rresp)` for frontdoor read
- Calls `add_tag()` at start of `body()`
- Calls `set_check_state_by_check_error_num()` at end of `body()`
- `build_frontdoor_beats(idx, fd_beats)` to pack write data
- `calc_beat_addr(addr, beat, axi_pkg::WRAP, size, len)` for address calculation

WRAP alignment constraint from the existing sequence:
```systemverilog
// wrap_bytes = len * beat_bytes (for len=8, SIZE_4B: wrap_bytes = 8*4 = 32)
// wrap_base_addr must be aligned to wrap_bytes: (wrap_base_addr % wrap_bytes) == 0
// addr = wrap_base_addr + (wrap_offset * beat_bytes), where wrap_offset in [1:len-1]
```

### Template 2: wrap_random_len_size_wr_test.sv (the existing test — your template)

```systemverilog
`ifndef AXI2AHB_WRAP_RANDOM_LEN_SIZE_WR_TEST_SV
`define AXI2AHB_WRAP_RANDOM_LEN_SIZE_WR_TEST_SV

class wrap_random_len_size_wr_test extends base_test;

  `uvm_component_utils(wrap_random_len_size_wr_test)

  wrap_random_len_size_wr_virt_seq vseq;

  function new(string name = "wrap_random_len_size_wr_test", uvm_component parent);
    super.new(name, parent);
  endfunction

  function void build_phase(uvm_phase phase);
    super.build_phase(phase);
    vseq = wrap_random_len_size_wr_virt_seq::type_id::create("vseq");
  endfunction

  task run_phase(uvm_phase phase);
    phase.raise_objection(this);
    super.run_phase(phase);

    if (!vseq.randomize())
      `uvm_fatal("RND", "Randomization failed!")

    vseq.start(env.vseqr);
    `uvm_info("TEST", "Wrap random length/size write-read Virtual Test Finished!", UVM_LOW)
    phase.drop_objection(this);
  endtask

endclass

`endif
```

### Template 3: base_test.sv (the base class — for reference only, do NOT modify)

```systemverilog
class base_test extends uvm_test;
  // Has: virtual axi_intf avif, virtual ahb_intf hvif, virtual dut_dbg_if dvif
  // Creates: axi2ahb_env env, axi2ahb_config cfg
  // run_phase: set_drain_time, raise/drop objection
  // report_phase: checks test_error_count
endclass
```

### Include files to update

**virt_seqs.svh** (add `include "wrap8_targeted_virt_seq.sv"`):
```
`include "base_virt_seq.sv"
`include "single_write_read_virt_seq.sv"
... (other includes)
`include "reset_recovery_virt_seq.sv"
// ADD NEW LINE HERE:
`include "wrap8_targeted_virt_seq.sv"
```

**tests.svh** (add `include "wrap8_targeted_test.sv"`):
```
`include "base_test.sv"
`include "single_write_read_test.sv"
... (other includes)
`include "reset_recovery_test.sv"
// ADD NEW LINE HERE:
`include "wrap8_targeted_test.sv"
```

## Step 3: Generate the Files

### File 1: `seq_lib/wrap8_targeted_virt_seq.sv`

**Requirements:**
1. Class `wrap8_targeted_virt_seq extends base_virtual_sequence`
2. `` `uvm_object_utils(wrap8_targeted_virt_seq) ``
3. Keep it **simple and targeted** — this is NOT a random stress test. The goal is to deterministically hit `cp_ahb_burst.wrap8`
4. Use a small fixed number of iterations (e.g., 5-10 transactions), not 50-100
5. **Every** transaction must use `len=8` and `burst=axi_pkg::WRAP`
6. Size can be fixed to `SIZE_4B` (or randomized over a small set)
7. Address must be WRAP-aligned: `(addr % (len * beat_bytes)) == 0`
8. Alternate between write and read to also hit `cr_ahb_rw_burst` cross coverage
9. Include both `run_fd_write_bd_read()` and `run_bd_write_fd_read()` patterns (copy from template)
10. `add_tag()` should describe the targeted nature: "Targeted WRAP8 burst coverage closure for GAP_0006"
11. `set_check_state_by_check_error_num()` at end of body
12. Include helper functions: `build_frontdoor_beats`, `bd_write_payload`, `bd_read_payload`, `pack_frontdoor_payload`, `unpack_frontdoor_payload`, `mask_payload`, `compare_payload` — copy these from the template sequence as-is
13. Use the same `` `ifndef / `define / `endif `` include guard pattern: `AXI2AHB_WRAP8_TARGETED_VIRT_SEQ_SV`

**Key constraint simplification:**
Instead of the complex randomization in the template, use a much simpler approach:
```systemverilog
constraint wrap8_only {
    // Fixed len=8 for every transaction
    foreach (len[i]) len[i] == 8;
    
    // Fixed or small random size set
    foreach (size[i]) size[i] inside {axi_pkg::SIZE_4B};
    
    // WRAP alignment
    foreach (wrap_base_addr[i]) {
        wrap_bytes[i] == 8 * beat_bytes[i];  // 8 beats * 4 bytes = 32 bytes
        (wrap_base_addr[i] % wrap_bytes[i]) == 0;
        wrap_base_addr[i][31:16] == 16'h0000;  // stay in lower 64KB
        wrap_base_addr[i] + wrap_bytes[i] - 1 <= 32'h0000_ffff;
    }
    
    // wrap_offset in valid range
    foreach (wrap_offset[i]) wrap_offset[i] inside {[1:7]};  // [1:len-1] = [1:7]
    
    // Address calculation
    foreach (addr[i]) {
        addr[i] == wrap_base_addr[i] + (wrap_offset[i] * beat_bytes[i]);
    }
    
    // Alternating write/read
    foreach (do_write[i]) {
        if (i == 0) do_write[i] == first_is_write;
        else do_write[i] == ~do_write[i-1];
    }
}
```

### File 2: `tests/wrap8_targeted_test.sv`

**Requirements:**
1. Class `wrap8_targeted_test extends base_test`
2. `` `uvm_component_utils(wrap8_targeted_test) ``
3. Follow the exact pattern from `wrap_random_len_size_wr_test.sv`
4. Create `wrap8_targeted_virt_seq vseq` in `build_phase`
5. In `run_phase`: raise objection, randomize vseq, start on `env.vseqr`, drop objection
6. Include guard: `AXI2AHB_WRAP8_TARGETED_TEST_SV`

### File 3 & 4: Update include files

1. Append `` `include "wrap8_targeted_virt_seq.sv" `` to `seq_lib/virt_seqs.svh`
2. Append `` `include "wrap8_targeted_test.sv" `` to `tests/tests.svh`

## Step 4: Output

After generating the files, print:

1. **Full source code** of each generated/modified file
2. **Compile command** (assuming standard VCS flow):
   ```
   # Compile (adjust paths as needed)
   vcs -full64 -sverilog -ntb_opts uvm-1.2 \
       -f <project>/filelist.f \
       +incdir+<project>/seq_lib+<project>/tests+... \
       -l compile.log
   ```
3. **Run command**:
   ```
   ./simv +UVM_TESTNAME=wrap8_targeted_test -l wrap8_targeted.log
   ```
4. **Expected coverage impact**: List which bins should be hit
   - `cp_ahb_burst.wrap8` — primary target
   - `cr_ahb_rw_burst (write, wrap8)` — cross coverage from write transactions
   - `cr_ahb_rw_burst (read, wrap8)` — cross coverage from read transactions

## Quality Checklist

Before considering the task complete, verify:

- [ ] `wrap8_targeted_virt_seq.sv` compiles (correct include guard, extends base_virtual_sequence, `uvm_object_utils)
- [ ] `wrap8_targeted_test.sv` compiles (correct include guard, extends base_test, `uvm_component_utils)
- [ ] Both files follow the coding style of existing files (indentation, naming conventions)
- [ ] Every transaction uses `len=8` and `axi_pkg::WRAP`
- [ ] WRAP alignment constraint is correct: `(addr % wrap_bytes) == 0` where `wrap_bytes = 8 * beat_bytes`
- [ ] Both write and read paths are exercised (for cross coverage)
- [ ] `add_tag()` and `set_check_state_by_check_error_num()` are called
- [ ] `virt_seqs.svh` and `tests.svh` are updated
- [ ] Helper functions (build_frontdoor_beats, pack/unpack/mask/compare_payload, bd_write/read_payload) are complete and correct

## Important Notes

- **Do NOT modify** any existing files (base_virtual_sequence, base_test, axi2ahb_cov.sv, etc.)
- **Do NOT add** any new packages or imports — all types come from existing `axi_pkg`, `ahb_pkg`
- The generated sequence must be **self-contained** — it inherits everything it needs from `base_virtual_sequence`
- Keep the sequence **simple** — 5-10 iterations is enough, this is a targeted coverage closure test, not a stress test
- The file names must be exactly `wrap8_targeted_virt_seq.sv` and `wrap8_targeted_test.sv`

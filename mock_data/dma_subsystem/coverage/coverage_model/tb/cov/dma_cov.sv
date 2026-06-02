// Mock coverage model for dma_subsystem demo project
// This is synthetic SystemVerilog code for testing the source resolver.
// NOT real company RTL or UVM code.

class dma_cov extends uvm_component;
  `uvm_component_utils(dma_cov)

  // Virtual interface handles
  virtual dma_if vif;
  virtual dma_desc_if desc_vif;

  // Signal sampling
  logic [1:0] desc_mode;
  logic [2:0] desc_chaining;
  logic [3:0] desc_alignment;
  logic [11:0] desc_size;
  logic [1:0] desc_fetch_timing;

  logic [2:0] int_type;
  logic [1:0] int_coalesce;
  logic [7:0] int_masking;

  logic clock_gate;
  logic [1:0] power_state;

  logic [1:0] burst_type;
  logic [7:0] burst_length;

  logic [31:0] fetch_timestamp;
  logic fetch_valid;


















































  // ================================================================
  // Descriptor Mode Coverage
  // ================================================================

  covergroup dma_desc_cg @(posedge vif.clk);
    option.name = "dma_desc_cg";

    desc_mode_cp: coverpoint desc_mode {
      bins linked_list    = {2'h2};  // DESC_LINKED_LIST
      bins scatter_gather = {2'h3};  // DESC_SCATTER_GATHER
      bins single         = {2'h0};  // DESC_SINGLE
    }
    // chaining descriptor coverage
    // chaining descriptor coverage
    // chaining descriptor coverage
    // chaining descriptor coverage
    // chaining descriptor coverage
    // chaining descriptor coverage
    // chaining descriptor coverage
    // chaining descriptor coverage
    // chaining descriptor coverage
    // chaining descriptor coverage
    // chaining descriptor coverage

    desc_chaining_cp: coverpoint desc_chaining {
      bins chain_of_2 = {3'h1};
      bins chain_of_3 = {3'h2};  // 3-descriptor chain
      bins chain_of_4 = {3'h3};
    }
    // alignment error coverage
    // alignment error coverage
    // alignment error coverage
    // alignment error coverage
    // alignment error coverage
    // alignment error coverage
    // alignment error coverage
    // alignment error coverage
    // alignment error coverage

    desc_alignment_cp: coverpoint desc_alignment {
      bins aligned_4byte   = {4'h0};
      bins misaligned_4byte = {4'h1, 4'h2, 4'h3};
      bins misaligned_8byte = {4'h4, 4'h5, 4'h6, 4'h7};
    }
    // transfer size boundary coverage
    // transfer size boundary coverage
    // transfer size boundary coverage
    // transfer size boundary coverage
    // transfer size boundary coverage
    // transfer size boundary coverage
    // transfer size boundary coverage
    // transfer size boundary coverage
    // transfer size boundary coverage

    desc_size_cp: coverpoint desc_size {
      bins small_size  = {[1:64]};
      bins medium_size = {[65:1024]};
      bins large_size  = {[1025:4095]};
      bins max_size_4k = {4096};  // 4K boundary
    }
    // descriptor fetch timing cross coverage
    // descriptor fetch timing cross coverage
    // descriptor fetch timing cross coverage
    // descriptor fetch timing cross coverage
    // descriptor fetch timing cross coverage
    // descriptor fetch timing cross coverage
    // descriptor fetch timing cross coverage
    // descriptor fetch timing cross coverage

    desc_fetch_cross: cross desc_mode_cp, desc_fetch_timing {
      bins back_to_back_cross = binsof(desc_mode_cp.linked_list) &&
                                binsof(desc_fetch_timing) intersect {2'h3};
    }

  endgroup : dma_desc_cg
  // interrupt coverage placeholder
  // interrupt coverage placeholder
  // interrupt coverage placeholder
  // interrupt coverage placeholder
  // interrupt coverage placeholder
  // interrupt coverage placeholder
  // interrupt coverage placeholder
  // interrupt coverage placeholder
  // interrupt coverage placeholder
  // interrupt coverage placeholder
  // interrupt coverage placeholder
  // interrupt coverage placeholder
  // interrupt coverage placeholder
  // interrupt coverage placeholder
  // interrupt coverage placeholder
  // interrupt coverage placeholder
  // interrupt coverage placeholder
  // interrupt coverage placeholder
  // interrupt coverage placeholder
  // interrupt coverage placeholder
  // interrupt coverage placeholder
  // interrupt coverage placeholder
  // interrupt coverage placeholder
  // interrupt coverage placeholder
  // interrupt coverage placeholder
  // interrupt coverage placeholder
  // interrupt coverage placeholder
  // interrupt coverage placeholder
  // interrupt coverage placeholder
  // interrupt coverage placeholder
  // interrupt coverage placeholder
  // interrupt coverage placeholder
  // interrupt coverage placeholder
  // interrupt coverage placeholder
  // interrupt coverage placeholder
  // interrupt coverage placeholder
  // interrupt coverage placeholder
  // interrupt coverage placeholder
  // interrupt coverage placeholder

  covergroup dma_interrupt_cg @(posedge vif.clk);
    option.name = "dma_interrupt_cg";


    int_type_cp: coverpoint int_type {
      bins completion_interrupt = {3'h0};
      bins error_interrupt      = {3'h1};  // DMA error
      bins timeout_interrupt    = {3'h2};
    }

    // interrupt coalescing coverage
    // interrupt coalescing coverage
    // interrupt coalescing coverage
    // interrupt coalescing coverage
    // interrupt coalescing coverage
    // interrupt coalescing coverage
    // interrupt coalescing coverage
    // interrupt coalescing coverage

    int_coalesce_cp: coverpoint int_coalesce {
      bins no_coalesce       = {2'h0};
      bins coalesce_timeout  = {2'h1};  // timer-based
      bins coalesce_count    = {2'h2};  // count-based
      bins coalesce_both     = {2'h3};
    }
    // interrupt masking edge cases
    // interrupt masking edge cases
    // interrupt masking edge cases
    // interrupt masking edge cases
    // interrupt masking edge cases
    // interrupt masking edge cases
    // interrupt masking edge cases
    // interrupt masking edge cases
    // interrupt masking edge cases
    // interrupt masking edge cases
    // interrupt masking edge cases
    // interrupt masking edge cases
    // interrupt masking edge cases

    int_masking_cp: coverpoint int_masking {
      bins all_unmasked = {8'h00};
      bins masked_pending = {8'hFF};  // all masked with pending
      bins partial_mask   = default;
    }

  endgroup : dma_interrupt_cg
  // power management coverage placeholder
  // power management coverage placeholder
  // power management coverage placeholder
  // power management coverage placeholder
  // power management coverage placeholder
  // power management coverage placeholder
  // power management coverage placeholder
  // power management coverage placeholder
  // power management coverage placeholder
  // power management coverage placeholder
  // power management coverage placeholder
  // power management coverage placeholder
  // power management coverage placeholder
  // power management coverage placeholder
  // power management coverage placeholder
  // power management coverage placeholder
  // power management coverage placeholder
  // power management coverage placeholder
  // power management coverage placeholder
  // power management coverage placeholder
  // power management coverage placeholder
  // power management coverage placeholder
  // power management coverage placeholder
  // power management coverage placeholder
  // power management coverage placeholder
  // power management coverage placeholder
  // power management coverage placeholder
  // power management coverage placeholder
  // power management coverage placeholder
  // power management coverage placeholder
  // power management coverage placeholder
  // power management coverage placeholder
  // power management coverage placeholder
  // power management coverage placeholder
  // power management coverage placeholder
  // power management coverage placeholder
  // power management coverage placeholder
  // power management coverage placeholder
  // power management coverage placeholder
  // power management coverage placeholder
  // power management coverage placeholder
  // power management coverage placeholder
  // power management coverage placeholder
  // power management coverage placeholder
  // power management coverage placeholder
  // power management coverage placeholder
  // power management coverage placeholder
  // power management coverage placeholder
  // power management coverage placeholder
  // power management coverage placeholder
  // power management coverage placeholder
  // power management coverage placeholder
  // power management coverage placeholder

  covergroup dma_power_cg @(posedge vif.clk);
    option.name = "dma_power_cg";


    clock_gate_cp: coverpoint clock_gate {
      bins active_gate = {1'b1};
      bins idle_gate   = {1'b0};  // idle clock gating
    }

    // power state transitions
    // power state transitions
    // power state transitions
    // power state transitions
    // power state transitions
    // power state transitions
    // power state transitions
    // power state transitions
    // power state transitions

    power_state_cp: coverpoint power_state {
      bins active_mode    = {2'h0};
      bins sleep_mode     = {2'h1};
      bins retention_mode = {2'h2};  // retention state
      bins shutdown_mode  = {2'h3};
    }

  endgroup : dma_power_cg
  // burst transfer coverage placeholder
  // burst transfer coverage placeholder
  // burst transfer coverage placeholder
  // burst transfer coverage placeholder
  // burst transfer coverage placeholder
  // burst transfer coverage placeholder
  // burst transfer coverage placeholder
  // burst transfer coverage placeholder
  // burst transfer coverage placeholder
  // burst transfer coverage placeholder
  // burst transfer coverage placeholder
  // burst transfer coverage placeholder
  // burst transfer coverage placeholder
  // burst transfer coverage placeholder
  // burst transfer coverage placeholder
  // burst transfer coverage placeholder
  // burst transfer coverage placeholder
  // burst transfer coverage placeholder
  // burst transfer coverage placeholder
  // burst transfer coverage placeholder
  // burst transfer coverage placeholder
  // burst transfer coverage placeholder
  // burst transfer coverage placeholder
  // burst transfer coverage placeholder
  // burst transfer coverage placeholder
  // burst transfer coverage placeholder
  // burst transfer coverage placeholder
  // burst transfer coverage placeholder
  // burst transfer coverage placeholder
  // burst transfer coverage placeholder
  // burst transfer coverage placeholder
  // burst transfer coverage placeholder
  // burst transfer coverage placeholder
  // burst transfer coverage placeholder
  // burst transfer coverage placeholder
  // burst transfer coverage placeholder
  // burst transfer coverage placeholder
  // burst transfer coverage placeholder
  // burst transfer coverage placeholder
  // burst transfer coverage placeholder
  // burst transfer coverage placeholder
  // burst transfer coverage placeholder
  // burst transfer coverage placeholder
  // burst transfer coverage placeholder
  // burst transfer coverage placeholder
  // burst transfer coverage placeholder
  // burst transfer coverage placeholder
  // burst transfer coverage placeholder
  // burst transfer coverage placeholder
  // burst transfer coverage placeholder
  // burst transfer coverage placeholder
  // burst transfer coverage placeholder
  // burst transfer coverage placeholder
  // burst transfer coverage placeholder
  // burst transfer coverage placeholder
  // burst transfer coverage placeholder
  // burst transfer coverage placeholder
  // burst transfer coverage placeholder
  // burst transfer coverage placeholder
  // burst transfer coverage placeholder
  // burst transfer coverage placeholder
  // burst transfer coverage placeholder
  // burst transfer coverage placeholder
  // burst transfer coverage placeholder
  // burst transfer coverage placeholder
  // burst transfer coverage placeholder
  // burst transfer coverage placeholder
  // burst transfer coverage placeholder
  // burst transfer coverage placeholder
  // burst transfer coverage placeholder
  // burst transfer coverage placeholder
  // burst transfer coverage placeholder

  covergroup dma_burst_cg @(posedge vif.clk);
    option.name = "dma_burst_cg";


    burst_type_cp: coverpoint burst_type {
      bins fixed_burst = {2'h0};
      bins incr_burst  = {2'h1};
      bins wrap_burst  = {2'h2};  // AXI wrap burst
    }

    // burst length boundaries
    // burst length boundaries
    // burst length boundaries
    // burst length boundaries
    // burst length boundaries
    // burst length boundaries
    // burst length boundaries
    // burst length boundaries

    burst_length_cp: coverpoint burst_length {
      bins short_burst  = {[1:16]};
      bins medium_burst = {[17:128]};
      bins long_burst   = {[129:255]};
      bins max_len_256  = {256};  // AXI max burst length
    }

  endgroup : dma_burst_cg
  // monitor sampling coverage placeholder
  // monitor sampling coverage placeholder
  // monitor sampling coverage placeholder
  // monitor sampling coverage placeholder
  // monitor sampling coverage placeholder
  // monitor sampling coverage placeholder
  // monitor sampling coverage placeholder
  // monitor sampling coverage placeholder
  // monitor sampling coverage placeholder
  // monitor sampling coverage placeholder
  // monitor sampling coverage placeholder
  // monitor sampling coverage placeholder
  // monitor sampling coverage placeholder
  // monitor sampling coverage placeholder
  // monitor sampling coverage placeholder
  // monitor sampling coverage placeholder
  // monitor sampling coverage placeholder
  // monitor sampling coverage placeholder
  // monitor sampling coverage placeholder
  // monitor sampling coverage placeholder
  // monitor sampling coverage placeholder
  // monitor sampling coverage placeholder
  // monitor sampling coverage placeholder
  // monitor sampling coverage placeholder
  // monitor sampling coverage placeholder
  // monitor sampling coverage placeholder
  // monitor sampling coverage placeholder
  // monitor sampling coverage placeholder
  // monitor sampling coverage placeholder
  // monitor sampling coverage placeholder
  // monitor sampling coverage placeholder
  // monitor sampling coverage placeholder
  // monitor sampling coverage placeholder
  // monitor sampling coverage placeholder
  // monitor sampling coverage placeholder
  // monitor sampling coverage placeholder
  // monitor sampling coverage placeholder
  // monitor sampling coverage placeholder
  // monitor sampling coverage placeholder
  // monitor sampling coverage placeholder
  // monitor sampling coverage placeholder
  // monitor sampling coverage placeholder
  // monitor sampling coverage placeholder
  // monitor sampling coverage placeholder
  // monitor sampling coverage placeholder
  // monitor sampling coverage placeholder
  // monitor sampling coverage placeholder
  // monitor sampling coverage placeholder
  // monitor sampling coverage placeholder
  // monitor sampling coverage placeholder
  // monitor sampling coverage placeholder
  // monitor sampling coverage placeholder
  // monitor sampling coverage placeholder
  // monitor sampling coverage placeholder
  // monitor sampling coverage placeholder
  // monitor sampling coverage placeholder
  // monitor sampling coverage placeholder
  // monitor sampling coverage placeholder
  // monitor sampling coverage placeholder
  // monitor sampling coverage placeholder
  // monitor sampling coverage placeholder
  // monitor sampling coverage placeholder
  // monitor sampling coverage placeholder
  // monitor sampling coverage placeholder
  // monitor sampling coverage placeholder
  // monitor sampling coverage placeholder
  // monitor sampling coverage placeholder
  // monitor sampling coverage placeholder
  // monitor sampling coverage placeholder
  // monitor sampling coverage placeholder
  // monitor sampling coverage placeholder
  // monitor sampling coverage placeholder

  covergroup dma_monitor_cg @(posedge vif.clk);
    option.name = "dma_monitor_cg";


    desc_fetch_timing_cp: coverpoint fetch_timestamp {
      bins single_fetch  = {32'h0};
      bins back_to_back  = {[1:10]};  // consecutive fetches
      bins delayed_fetch = {[11:1000]};
    }

  endgroup : dma_monitor_cg

  // Instantiate covergroups
  dma_desc_cg      desc_cov = new();
  dma_interrupt_cg int_cov  = new();
  dma_power_cg     pwr_cov  = new();
  dma_burst_cg     bst_cov  = new();
  dma_monitor_cg   mon_cov  = new();

endclass : dma_cov

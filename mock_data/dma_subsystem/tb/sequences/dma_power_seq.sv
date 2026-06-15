// DMA Power Management Sequence
// Tests power state transitions and clock gating

class dma_power_seq extends dma_base_seq;
  `uvm_object_utils(dma_power_seq)

  rand bit clock_gate_en;
  rand bit power_down;

  constraint c_default {
    clock_gate_en dist { 0 := 30, 1 := 70 };
    power_down dist { 0 := 80, 1 := 20 };
  }

  function new(string name = "dma_power_seq");
    super.new(name);
  endfunction

  virtual task body();
    req = dma_desc_trans::type_id::create("req");
    start_item(req);
    assert(req.randomize() with {
      clk_gate_en == clock_gate_en;
      power_down_mode == power_down;
    });
    finish_item(req);
  endtask

endclass

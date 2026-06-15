// DMA Interrupt Sequence
// Triggers and verifies DMA interrupt behavior

class dma_interrupt_seq extends dma_base_seq;
  `uvm_object_utils(dma_interrupt_seq)

  rand bit enable_coalescing;
  rand int unsigned coal_threshold;

  constraint c_default {
    enable_coalescing dist { 0 := 50, 1 := 50 };
    coal_threshold inside {[1:8]};
  }

  function new(string name = "dma_interrupt_seq");
    super.new(name);
  endfunction

  virtual task body();
    req = dma_desc_trans::type_id::create("req");
    start_item(req);
    assert(req.randomize() with {
      interrupt_en == 1;
      coal_en == enable_coalescing;
      coal_thresh == coal_threshold;
    });
    finish_item(req);
  endtask

endclass

// DMA Burst Sequence
// Tests various AXI burst types through the DMA engine

class dma_burst_seq extends dma_base_seq;
  `uvm_object_utils(dma_burst_seq)

  rand bit [1:0] burst_type;
  rand int unsigned burst_len;

  constraint c_default {
    burst_type inside {2'b00, 2'b01, 2'b10};  // FIXED, INCR, WRAP
    burst_len inside {[1:256]};
  }

  function new(string name = "dma_burst_seq");
    super.new(name);
  endfunction

  virtual task body();
    req = dma_desc_trans::type_id::create("req");
    start_item(req);
    assert(req.randomize() with {
      axi_burst_type == burst_type;
      burst_length == burst_len;
    });
    finish_item(req);
  endtask

endclass

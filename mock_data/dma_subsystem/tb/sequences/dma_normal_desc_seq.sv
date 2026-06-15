// DMA Normal Descriptor Sequence
// Sends normal (non-linked-list) descriptors through the DMA engine

class dma_normal_desc_seq extends dma_base_seq;
  `uvm_object_utils(dma_normal_desc_seq)

  rand int unsigned num_descriptors;
  rand int unsigned burst_len;

  constraint c_default {
    num_descriptors inside {[1:16]};
    burst_len inside {[1:256]};
  }

  function new(string name = "dma_normal_desc_seq");
    super.new(name);
  endfunction

  virtual task body();
    repeat(num_descriptors) begin
      req = dma_desc_trans::type_id::create("req");
      start_item(req);
      assert(req.randomize() with {
        desc_mode == NORMAL;
        burst_length == burst_len;
      });
      finish_item(req);
    end
  endtask

endclass

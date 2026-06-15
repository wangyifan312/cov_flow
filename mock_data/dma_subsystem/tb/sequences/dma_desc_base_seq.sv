// DMA Descriptor Base Sequence
// Base class for descriptor-based DMA sequences

class dma_desc_base_seq extends dma_base_seq;
  `uvm_object_utils(dma_desc_base_seq)

  rand bit use_linked_list;
  rand bit use_scatter_gather;

  constraint c_default {
    use_linked_list == 0;
    use_scatter_gather == 0;
  }

  function new(string name = "dma_desc_base_seq");
    super.new(name);
  endfunction

  virtual task body();
    req = dma_desc_trans::type_id::create("req");
    start_item(req);
    assert(req.randomize() with {
      desc_mode == (use_linked_list ? LINKED_LIST : NORMAL);
      sg_mode == use_scatter_gather;
    });
    finish_item(req);
  endtask

endclass

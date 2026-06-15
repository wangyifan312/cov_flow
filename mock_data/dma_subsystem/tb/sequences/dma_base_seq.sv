// DMA Base Sequence
// Abstract base class for all DMA sequences

class dma_base_seq extends uvm_sequence #(dma_desc_trans);
  `uvm_object_utils(dma_base_seq)
  `uvm_declare_p_sequencer(dma_sequencer)

  function new(string name = "dma_base_seq");
    super.new(name);
  endfunction

  virtual task body();
    req = dma_desc_trans::type_id::create("req");
    start_item(req);
    finish_item(req);
  endtask

endclass

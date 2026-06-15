// DMA Subsystem top-level module
// Instantiates dma_core with AXI interface

module dma_subsystem (
    input  logic        clk,
    input  logic        rst_n,
    input  logic [31:0] axi_aw,
    input  logic [31:0] axi_ar,
    input  logic [31:0] axi_w,
    output logic [31:0] axi_r,
    output logic [1:0]  axi_b,
    output logic        irq_out
);

    dma_core u_dma (
        .clk     (clk),
        .rst_n   (rst_n),
        .cfg_if  (),
        .desc_if (),
        .axi_m   (),
        .irq     (irq_out)
    );

endmodule

// DMA AXI Master Interface
// Handles AXI4 read/write bursts with configurable burst type and length.

module dma_axi_master (
    input  logic        clk,
    input  logic        rst_n,
    input  logic        burst_wrap,
    input  logic [7:0]  burst_len,
    output logic [31:0] awaddr,
    output logic [31:0] araddr,
    output logic [63:0] wdata,
    input  logic [63:0] rdata
);

    // AXI burst type encoding
    typedef enum logic [1:0] {
        AXI_FIXED = 2'b00,
        AXI_INCR  = 2'b01,
        AXI_WRAP  = 2'b10
    } axi_burst_type_t;

    axi_burst_type_t burst_type;
    logic [7:0] beat_count;
    logic       write_active;
    logic       read_active;

    // Burst type selection
    assign burst_type = burst_wrap ? AXI_WRAP : AXI_INCR;

endmodule

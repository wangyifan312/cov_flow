// DMA Core — central controller with descriptor parsing, AXI master,
// interrupt control, power management, and performance monitor.

module dma_core #(
    parameter int NUM_CHANNELS = 4
) (
    input  logic        clk,
    input  logic        rst_n,
    input  logic [31:0] cfg_if,
    input  logic [31:0] desc_if,
    output logic [63:0] axi_m,
    output logic        irq
);

    // Internal wires
    logic        ll_mode_en;
    logic        sg_mode_en;
    logic        desc_valid;
    logic [31:0] desc_data;
    logic        chain_valid;
    logic [15:0] xfer_size;
    logic        addr_misaligned;
    logic        fetch_ack;
    logic        error_irq;
    logic        comp_irq;
    logic        coal_timer_exp;
    logic        coal_count_hit;
    logic [3:0]  masked_irq;
    logic        burst_wrap;
    logic [7:0]  burst_len;
    logic        clk_gate_en;
    logic        retention_mode;
    logic [3:0]  idle_detect;
    logic [31:0] fetch_timestamp;
    logic        xfer_complete;

    // Descriptor parser
    dma_desc_parser u_desc_parser (
        .clk             (clk),
        .rst_n           (rst_n),
        .ll_mode_en      (ll_mode_en),
        .sg_mode_en      (sg_mode_en),
        .desc_valid      (desc_valid),
        .desc_data       (desc_data),
        .chain_valid     (chain_valid),
        .xfer_size       (xfer_size),
        .addr_misaligned (addr_misaligned),
        .fetch_ack       (fetch_ack)
    );

    // AXI master interface
    dma_axi_master u_axi_master (
        .clk       (clk),
        .rst_n     (rst_n),
        .burst_wrap(burst_wrap),
        .burst_len (burst_len),
        .awaddr    (),
        .araddr    (),
        .wdata     (),
        .rdata     ()
    );

    // Interrupt controller
    dma_int_ctrl u_int_ctrl (
        .clk            (clk),
        .rst_n          (rst_n),
        .error_irq      (error_irq),
        .comp_irq       (comp_irq),
        .coal_timer_exp (coal_timer_exp),
        .coal_count_hit (coal_count_hit),
        .masked_irq     (masked_irq),
        .irq_out        (irq)
    );

    // Power controller
    dma_power_ctrl u_power (
        .clk            (clk),
        .rst_n          (rst_n),
        .clk_gate_en    (clk_gate_en),
        .retention_mode (retention_mode),
        .idle_detect    (idle_detect),
        .power_state    ()
    );

    // Performance monitor
    dma_monitor u_monitor (
        .clk             (clk),
        .rst_n           (rst_n),
        .fetch_timestamp (fetch_timestamp),
        .desc_valid      (desc_valid),
        .xfer_complete   (xfer_complete)
    );

endmodule

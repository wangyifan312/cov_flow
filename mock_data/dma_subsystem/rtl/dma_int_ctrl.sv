// DMA Interrupt Controller
// Manages completion, error, and coalescing interrupts.

module dma_int_ctrl (
    input  logic        clk,
    input  logic        rst_n,
    input  logic        error_irq,
    input  logic        comp_irq,
    input  logic        coal_timer_exp,
    input  logic        coal_count_hit,
    output logic [3:0]  masked_irq,
    output logic        irq_out
);

    // Interrupt status and mask registers
    logic [3:0] irq_status;
    logic [3:0] irq_mask;
    logic       coal_active;

    // Coalescing counter
    logic [7:0] coal_count;
    logic [15:0] coal_timer;

    assign masked_irq = irq_status & ~irq_mask;
    assign irq_out = |masked_irq;

endmodule

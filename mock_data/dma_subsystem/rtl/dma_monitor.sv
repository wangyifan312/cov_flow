// DMA Performance Monitor
// Records fetch timestamps for performance analysis.

module dma_monitor (
    input  logic        clk,
    input  logic        rst_n,
    output logic [31:0] fetch_timestamp,
    input  logic        desc_valid,
    input  logic        xfer_complete
);

    // Timestamp counter
    logic [31:0] cycle_count;
    logic [31:0] last_fetch_ts;
    logic [31:0] last_xfer_ts;

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            cycle_count <= 32'd0;
            fetch_timestamp <= 32'd0;
        end else begin
            cycle_count <= cycle_count + 1;
            if (desc_valid)
                fetch_timestamp <= cycle_count;
        end
    end

endmodule

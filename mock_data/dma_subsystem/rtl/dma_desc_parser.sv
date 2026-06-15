// DMA Descriptor Parser
// Parses normal, linked-list, and scatter-gather descriptors.

module dma_desc_parser (
    input  logic        clk,
    input  logic        rst_n,
    input  logic        ll_mode_en,
    input  logic        sg_mode_en,
    input  logic        desc_valid,
    input  logic [31:0] desc_data,
    output logic        chain_valid,
    output logic [15:0] xfer_size,
    output logic        addr_misaligned,
    output logic        fetch_ack
);

    // FSM state encoding
    typedef enum logic [2:0] {
        IDLE         = 3'b000,
        FETCH_DESC   = 3'b001,
        PARSE_NORMAL = 3'b010,
        PARSE_LINKED = 3'b011,
        PARSE_SG     = 3'b100,
        DONE         = 3'b101
    } parser_state_t;

    parser_state_t state, next_state;

    // Internal signals
    logic [31:0] src_addr;
    logic [31:0] dst_addr;
    logic [31:0] next_desc_ptr;
    logic        eoc;  // end of chain

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            state <= IDLE;
        else
            state <= next_state;
    end

    always_comb begin
        next_state = state;
        chain_valid = 1'b0;
        fetch_ack = 1'b0;
        addr_misaligned = 1'b0;

        case (state)
            IDLE: begin
                if (desc_valid)
                    next_state = FETCH_DESC;
            end
            FETCH_DESC: begin
                fetch_ack = 1'b1;
                if (ll_mode_en)
                    next_state = PARSE_LINKED;
                else if (sg_mode_en)
                    next_state = PARSE_SG;
                else
                    next_state = PARSE_NORMAL;
            end
            PARSE_NORMAL: begin
                chain_valid = 1'b1;
                next_state = DONE;
            end
            PARSE_LINKED: begin
                chain_valid = 1'b1;
                next_state = DONE;
            end
            PARSE_SG: begin
                chain_valid = 1'b1;
                next_state = DONE;
            end
            DONE: begin
                next_state = IDLE;
            end
            default: next_state = IDLE;
        endcase
    end

    // Transfer size extraction
    assign xfer_size = desc_data[15:0];

    // Address alignment check
    assign addr_misaligned = (src_addr[1:0] != 2'b00) | (dst_addr[1:0] != 2'b00);

endmodule

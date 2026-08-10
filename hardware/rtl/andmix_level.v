//=============================================================================
// andmix_level — one AND-XOR cascade level for ONE target word (64 bits).
// Time-multiplexed core for the 4-level cascade: one level per cycle.
//
// The four source words x0..x3 are pre-rotated (wiring) by the eight
// cascade rotations {31,53,17,43,7,23,5,19}; sel_a/sel_b pick the source
// word (2 bits each) and rot_a/rot_b pick among {31,17,7,5} (A side) /
// {53,43,23,19} (B side). out = acc ^ (rotA & rotB).
//=============================================================================
module andmix_level (
    input  wire [63:0] x0, x1, x2, x3,
    input  wire [63:0] acc,
    input  wire [1:0]  sel_a, sel_b,
    input  wire [1:0]  rot_a, rot_b,
    output wire [63:0] out
);

    function [63:0] rotl;
        input [63:0] a;
        input [5:0]  r;
        begin
            rotl = (a << r) | (a >> (64 - r));
        end
    endfunction

    // Pre-rotated versions (A side: 31,17,7,5; B side: 53,43,23,19)
    wire [63:0] a0_31 = rotl(x0,31), a0_17 = rotl(x0,17), a0_7 = rotl(x0,7),  a0_5 = rotl(x0,5);
    wire [63:0] a1_31 = rotl(x1,31), a1_17 = rotl(x1,17), a1_7 = rotl(x1,7),  a1_5 = rotl(x1,5);
    wire [63:0] a2_31 = rotl(x2,31), a2_17 = rotl(x2,17), a2_7 = rotl(x2,7),  a2_5 = rotl(x2,5);
    wire [63:0] a3_31 = rotl(x3,31), a3_17 = rotl(x3,17), a3_7 = rotl(x3,7),  a3_5 = rotl(x3,5);
    wire [63:0] b0_53 = rotl(x0,53), b0_43 = rotl(x0,43), b0_23 = rotl(x0,23), b0_19 = rotl(x0,19);
    wire [63:0] b1_53 = rotl(x1,53), b1_43 = rotl(x1,43), b1_23 = rotl(x1,23), b1_19 = rotl(x1,19);
    wire [63:0] b2_53 = rotl(x2,53), b2_43 = rotl(x2,43), b2_23 = rotl(x2,23), b2_19 = rotl(x2,19);
    wire [63:0] b3_53 = rotl(x3,53), b3_43 = rotl(x3,43), b3_23 = rotl(x3,23), b3_19 = rotl(x3,19);

    // Source-word selection (4:1), then rotation selection (4:1 on the
    // pre-rotated set of the chosen word).
    reg [63:0] sa, sb;
    always @(*) begin
        case (sel_a)
        2'd0: sa = (rot_a == 2'd0) ? a0_31 : (rot_a == 2'd1) ? a0_17 : (rot_a == 2'd2) ? a0_7 : a0_5;
        2'd1: sa = (rot_a == 2'd0) ? a1_31 : (rot_a == 2'd1) ? a1_17 : (rot_a == 2'd2) ? a1_7 : a1_5;
        2'd2: sa = (rot_a == 2'd0) ? a2_31 : (rot_a == 2'd1) ? a2_17 : (rot_a == 2'd2) ? a2_7 : a2_5;
        default: sa = (rot_a == 2'd0) ? a3_31 : (rot_a == 2'd1) ? a3_17 : (rot_a == 2'd2) ? a3_7 : a3_5;
        endcase
    end
    always @(*) begin
        case (sel_b)
        2'd0: sb = (rot_b == 2'd0) ? b0_53 : (rot_b == 2'd1) ? b0_43 : (rot_b == 2'd2) ? b0_23 : b0_19;
        2'd1: sb = (rot_b == 2'd0) ? b1_53 : (rot_b == 2'd1) ? b1_43 : (rot_b == 2'd2) ? b1_23 : b1_19;
        2'd2: sb = (rot_b == 2'd0) ? b2_53 : (rot_b == 2'd1) ? b2_43 : (rot_b == 2'd2) ? b2_23 : b2_19;
        default: sb = (rot_b == 2'd0) ? b3_53 : (rot_b == 2'd1) ? b3_43 : (rot_b == 2'd2) ? b3_23 : b3_19;
        endcase
    end

    assign out = acc ^ (sa & sb);

endmodule

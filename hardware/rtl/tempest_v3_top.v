//=============================================================================
// Tempest v3 (Algorithm 1) - Top Module, bit-exact with the C ground truth
// (github_release/src/tempest_v3.c)
//
// - Round function: Phases A (snapshot XOR-AND), A(lin), B (GF(2) Weyl key),
//   C (pre-mix + 4-level andmix4 cascade), D (cross-word mixing) — one
//   combinational cloud, one clock per round.
// - Initialization: exactly tempest_init — 16 rounds with the kw key
//   schedule and key/nonce injections, 6 plain rounds, final key XOR.
// - Generation: one round per clock; the 128-bit dual block
//   {make_output(u,v,w,z), make_output(v,w,z,u)} is registered every cycle.
//=============================================================================
module tempest_v3_top (
    input  wire         clk,
    input  wire         rst_n,
    input  wire         en,              // start initialization
    // key/nonce are loaded in three 128-bit words (IO-saving):
    //   load_sel 0: key words 0,1 ; 1: key words 2,3 ; 2: nonce words
    input  wire  [127:0] key_word,
    input  wire  [1:0]  load_sel,
    output wire  [63:0]  rnd_data,       // 64-bit random output word
    output wire         rnd_valid,       // word valid (one pulse per word)
    output wire         busy             // initializing or generating
);

    // Constants (Algorithm 1, C ground truth)
    localparam [63:0] K_U = 64'h9E3779B97F4A7C15;
    localparam [63:0] K_V = 64'h3C6EF372FE94F82A;
    localparam [63:0] K_W = 64'h5A8279998F1BBD27;
    localparam [63:0] K_Z = 64'h6ED9EBA1F97F3B4C;
    localparam [63:0] INIT_WEYL = 64'h6A09E667F3BCC908;
    localparam [63:0] MAGIC_Z   = 64'h54454D5035583543;

    // State registers
    reg [63:0] u, v, w, z;
    reg [63:0] round_key;          // Weyl counter (GF(2) affine);
                                   // the C's kw accumulator is identical
                                   // to the Weyl counter (same init,
                                   // same GF(2) update), so one register
                                   // serves both; injections use the
                                   // round function's rkey_next output.
    reg [63:0] k0, k1, k2, k3;     // key words (originals)
    reg [63:0] n0, n1;             // nonce words
    // Rotated key words for the injection: rk_i = rotl(k_i, cnt+1),
    // maintained as shift registers (rotl by 1 = wiring, 0 LUTs).
    // This replaces the barrel-shifter the synthesizer would otherwise
    // build for rotl(k_i, cnt+1) with cnt variable.
    reg [63:0] rk_u, rk_v, rk_w, rk_z;

    // FSM
    localparam IDLE = 3'd0, LOAD = 3'd1, INIT = 3'd2, FINAL = 3'd3, GEN = 3'd4;
    reg [2:0]  state;
    reg [5:0]  cnt;                // init round counter 0..21
    reg [1:0]  load_cnt;           // key loading word counter 0..2
    reg [63:0] rnd_data_reg;
    reg        rnd_valid_reg;

    function [63:0] rotl;
        input [63:0] a;
        input [5:0]  r;
        begin
            rotl = (a << r) | (a >> (64 - r));
        end
    endfunction

    wire [63:0] next_u, next_v, next_w, next_z, rkey_next, o0;

    round_function u_round (
        .u_in(u), .v_in(v), .w_in(w), .z_in(z),
        .round_key_in(round_key),
        .K_U(K_U), .K_V(K_V), .K_W(K_W), .K_Z(K_Z),
        .u_out(next_u), .v_out(next_v), .w_out(next_w), .z_out(next_z),
        .rkey_out(rkey_next)
    );

    // Output of the *new* state (C semantics: round, then output).
    // Single-output variant: one 64-bit word per round.
    output_function u_output (
        .u(next_u), .v(next_v), .w(next_w), .z(next_z),
        .o0(o0)
    );

    //-------------------------------------------------------------------------
    // Initialization injections (combinational on cnt), verbatim from
    // tempest_init: rounds 0..7 key-word injection with the kw schedule,
    // rounds 8..15 nonce injection, rounds 16..21 plain.
    //-------------------------------------------------------------------------
    wire [63:0] in0 = (cnt[0] == 1'b0) ? n0 : n1;    // nonce[i&1]
    wire [63:0] in1 = (cnt[0] == 1'b0) ? n1 : n0;    // nonce[1-(i&1)]

    reg [63:0] inj_u, inj_v, inj_w, inj_z;
    always @(*) begin
        inj_u = 64'd0; inj_v = 64'd0; inj_w = 64'd0; inj_z = 64'd0;
        if (cnt < 6'd8) begin
            if (cnt[0]) begin
                inj_u = rk_u ^ rkey_next;
                inj_v = rk_v ^ (rkey_next << 17);
                inj_w = rk_w ^ (rkey_next >> 13);
                inj_z = rk_z ^ rotl(rkey_next, 31);
            end else begin
                inj_u = k0 ^ rkey_next;
                inj_v = k1 ^ (rkey_next << 17);
                inj_w = k2 ^ (rkey_next >> 13);
                inj_z = k3 ^ rotl(rkey_next, 31);
            end
        end else if (cnt < 6'd16) begin
            inj_u = in0;
            inj_v = rotl(in1, 19) ^ {58'd0, cnt};
            inj_z = rotl(in0, 43);
        end
    end

    //-------------------------------------------------------------------------
    // FSM sequential
    //-------------------------------------------------------------------------
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= IDLE; cnt <= 0; load_cnt <= 0;
            u <= 0; v <= 0; w <= 0; z <= 0;
            round_key <= 0;
            rnd_data_reg <= 0; rnd_valid_reg <= 0;
        end else begin
            rnd_valid_reg <= 1'b0;
            case (state)
            IDLE: begin
                // k0k1 are loaded from the stable key_word bus while idle:
                // key_word = (k1, k0) and load_sel = 0 must be held before
                // en is asserted. This removes one 3:1 selection stage.
                k0 <= key_word[63:0];
                k1 <= key_word[127:64];
                u <= key_word[63:0];
                v <= key_word[127:64];     // ^ nonce[0] once loaded
                rk_u <= rotl(key_word[63:0], 1);
                rk_v <= rotl(key_word[127:64], 1);
                if (en) state <= LOAD;
            end
            LOAD: begin
                // key/nonce words arrive on key_word with load_sel marking
                // which group is on the bus: 0 = k2k3, 1 = n0n1.
                case (load_sel)
                2'd0: begin
                    k2 <= key_word[63:0];   k3 <= key_word[127:64];
                    w <= key_word[63:0];
                    z <= key_word[127:64] ^ MAGIC_Z;
                    rk_w <= rotl(key_word[63:0], 1);
                    rk_z <= rotl(key_word[127:64], 1);
                end
                default: begin
                    n0 <= key_word[63:0];   n1 <= key_word[127:64];
                    v <= v ^ key_word[63:0];
                    w <= w ^ key_word[127:64];
                    cnt <= 0;
                    state <= INIT;
                end
                endcase
                round_key <= INIT_WEYL;
            end
            INIT: begin
                u <= next_u ^ inj_u; v <= next_v ^ inj_v;
                w <= next_w ^ inj_w; z <= next_z ^ inj_z;
                round_key <= rkey_next;
                // advance the rotated-key shift registers (rotl by 1)
                rk_u <= rotl(rk_u, 1);
                rk_v <= rotl(rk_v, 1);
                rk_w <= rotl(rk_w, 1);
                rk_z <= rotl(rk_z, 1);
                if (cnt == 6'd21) state <= FINAL;
                else cnt <= cnt + 6'd1;
            end
            FINAL: begin
                u <= u ^ k0; v <= v ^ k1; w <= w ^ k2; z <= z ^ k3;
                state <= GEN;
            end
            GEN: begin
                u <= next_u; v <= next_v; w <= next_w; z <= next_z;
                round_key <= rkey_next;
                rnd_data_reg <= o0;
                rnd_valid_reg <= 1'b1;
            end
            default: state <= IDLE;
            endcase
        end
    end

    assign rnd_data  = rnd_data_reg;
    assign rnd_valid = rnd_valid_reg;
    assign busy      = (state != IDLE);

endmodule

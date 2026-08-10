//=============================================================================
// Tempest v3 - Round Function Module
// Implements Phases A, B, C (andmix4), D of the Tempest v3 round
//=============================================================================

module round_function (
    input  wire [63:0] u_in, v_in, w_in, z_in,
    input  wire [63:0] round_key_in,
    input  wire [63:0] K_U, K_V, K_W, K_Z,
    output wire [63:0] u_out, v_out, w_out, z_out,
    output wire [63:0] rkey_out
);

    // Rotation function
    function [63:0] rotl;
        input [63:0] a;
        input [5:0]  r;
        begin
            rotl = (a << r) | (a >> (64 - r));
        end
    endfunction

    //-------------------------------------------------------------------------
    // Phase A: XOR-AND nonlinear diffusion from snapshot
    //-------------------------------------------------------------------------
    wire [63:0] u_a, v_a, w_a, z_a;

    // Snapshot values are the inputs (latched at start of round)
    assign u_a = u_in ^ rotl(v_in, 5)  ^ rotl(w_in, 17) ^ (rotl(v_in, 5)  & rotl(z_in, 25)) ^ K_U;
    assign v_a = v_in ^ rotl(w_in, 11) ^ rotl(z_in, 23) ^ (rotl(w_in, 11) & rotl(u_in, 29)) ^ K_V;
    assign w_a = w_in ^ rotl(z_in, 13) ^ rotl(u_in, 31) ^ (rotl(u_in, 9)  & rotl(v_in, 15)) ^ K_W;
    assign z_a = z_in ^ rotl(u_in, 17) ^ rotl(v_in, 7)  ^ (rotl(v_in, 27) & rotl(w_in, 21)) ^ K_Z;

    // Phase A(lin): extra snapshot ANDs for linear resistance
    wire [63:0] u_a2, z_a2;
    assign u_a2 = u_a ^ (rotl(z_in, 23) & rotl(w_in, 53));
    assign z_a2 = z_a ^ (rotl(u_in, 5)  & rotl(z_in, 25));

    // These become the state after Phase A
    wire [63:0] u_phA, v_phA, w_phA, z_phA;
    assign u_phA = u_a2;
    assign v_phA = v_a;
    assign w_phA = w_a;
    assign z_phA = z_a2;

    //-------------------------------------------------------------------------
    // Phase B: Round key perturbation
    //-------------------------------------------------------------------------
    localparam [63:0] PHI = 64'h9E3779B97F4A7C15;

    wire [63:0] rk_affine, rk_filtered;
    wire [63:0] u_b, v_b, w_b, z_b;

    // Affine step: w_l = w_l ^ rotl(w_l, 19) ^ phi
    assign rk_affine = round_key_in ^ rotl(round_key_in, 19) ^ PHI;

    // Nonlinear filter: w_l' = w_l ^ rotl(w_l & phi, 13)
    assign rk_filtered = rk_affine ^ rotl(rk_affine & PHI, 13);

    // XOR into state words
    assign u_b = u_phA ^ rotl(rk_filtered, 7)  ^ (rk_filtered >> 17);
    assign v_b = v_phA ^ rotl(rk_filtered, 19) ^ (rk_filtered >> 23);
    assign w_b = w_phA ^ rotl(rk_filtered, 31) ^ (rk_filtered >> 29);
    assign z_b = z_phA ^ rotl(rk_filtered, 43) ^ (rk_filtered >> 37);

    // Round key output for next round
    assign rkey_out = rk_affine;

    //-------------------------------------------------------------------------
    // Phase C: SEV Pre-mix + andmix4 (4-level cross-word AND cascade)
    //-------------------------------------------------------------------------

    // Pre-mix 1: intra-word diffusion
    wire [63:0] u_p1, v_p1, w_p1, z_p1;
    wire [63:0] u_c, v_c, w_c, z_c;
    assign u_p1 = u_b ^ rotl(u_b, 22) ^ rotl(u_b, 26) ^ (rotl(u_b, 7)  & rotl(u_b, 19));
    assign v_p1 = v_b ^ rotl(v_b, 22) ^ rotl(v_b, 26) ^ (rotl(v_b, 7)  & rotl(v_b, 19));
    assign w_p1 = w_b ^ rotl(w_b, 22) ^ rotl(w_b, 26) ^ (rotl(w_b, 7)  & rotl(w_b, 19));
    assign z_p1 = z_b ^ rotl(z_b, 22) ^ rotl(z_b, 26) ^ (rotl(z_b, 7)  & rotl(z_b, 19));

    // andmix4 instantiation (rotation pairs per the C ground truth,
    // fixed inside andmix4.v)
    andmix4 u_andmix (
        .u_in(u_p1), .v_in(v_p1), .w_in(w_p1), .z_in(z_p1),
        .u_out(u_c), .v_out(v_c), .w_out(w_c), .z_out(z_c)
    );

    //-------------------------------------------------------------------------
    // Phase D: Cross-word mixing
    //-------------------------------------------------------------------------
    assign u_out = u_c ^ rotl(v_c, 3)  ^ rotl(w_c, 9);
    assign v_out = v_c ^ rotl(w_c, 5)  ^ rotl(z_c, 11);
    assign w_out = w_c ^ rotl(z_c, 9)  ^ rotl(u_c, 13);
    assign z_out = z_c ^ rotl(u_c, 11) ^ rotl(v_c, 17);

endmodule

//=============================================================================
// andmix4_k2 - 2-Level Cross-Word AND Cascade (the Pareto-front truncation)
//
// Levels 1-2 plus pre-mix 2 only; the framework's cascade table shows the
// differential benefit saturates at one to two levels (the k=2 truncation
// is on the Pareto front with the full design at equal rho, 15 ops
// cheaper). Rotation pairs verbatim from the C ground truth:
//   L1: u:(31,53) v:(17,43) w:(7,23)  z:(5,19)
//   L2: u:(17,43) v:(7,23)  w:(5,19)  z:(31,53)
//   premix2 (16,14)
//=============================================================================
module andmix4_k2 (
    input  wire [63:0] u_in, v_in, w_in, z_in,
    output wire [63:0] u_out, v_out, w_out, z_out
);

    function [63:0] rotl;
        input [63:0] a;
        input [5:0]  r;
        begin
            rotl = (a << r) | (a >> (64 - r));
        end
    endfunction

    // Level 1
    wire [63:0] l1_u, l1_v, l1_w, l1_z;
    assign l1_u = u_in ^ (rotl(v_in, 31) & rotl(w_in, 53));
    assign l1_v = v_in ^ (rotl(w_in, 17) & rotl(z_in, 43));
    assign l1_w = w_in ^ (rotl(z_in,  7) & rotl(u_in, 23));
    assign l1_z = z_in ^ (rotl(u_in,  5) & rotl(v_in, 19));

    // Level 2
    wire [63:0] l2_u, l2_v, l2_w, l2_z;
    assign l2_u = l1_u ^ (rotl(l1_v, 17) & rotl(l1_z, 43));
    assign l2_v = l1_v ^ (rotl(l1_w,  7) & rotl(l1_u, 23));
    assign l2_w = l1_w ^ (rotl(l1_z,  5) & rotl(l1_v, 19));
    assign l2_z = l1_z ^ (rotl(l1_u, 31) & rotl(l1_w, 53));

    // Pre-mix 2
    assign u_out = l2_u ^ rotl(l2_u, 16) ^ rotl(l2_u, 14);
    assign v_out = l2_v ^ rotl(l2_v, 16) ^ rotl(l2_v, 14);
    assign w_out = l2_w ^ rotl(l2_w, 16) ^ rotl(l2_w, 14);
    assign z_out = l2_z ^ rotl(l2_z, 16) ^ rotl(l2_z, 14);

endmodule

//=============================================================================
// andmix4 - 4-Level Cross-Word AND Cascade (Algorithm 1, bit-exact)
//
// Rotation pairs per level/word taken verbatim from the C ground truth
// (github_release/src/tempest_v3.c enhanced_round, Phase C):
//   L1: u:(31,53) v:(17,43) w:(7,23)  z:(5,19)
//   L2: u:(17,43) v:(7,23)  w:(5,19)  z:(31,53)
//   premix2 (16,14) between L2 and L3
//   L3: u:(7,23)  v:(5,19)  w:(31,53) z:(17,43)
//   L4: u:(5,19)  v:(31,53) w:(17,53) z:(7,23)
// Pure combinational: all 4 levels compute in one clock.
//=============================================================================
module andmix4 (
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

    //-------------------------------------------------------------------------
    // Level 1: each word receives from two different sources
    //-------------------------------------------------------------------------
    wire [63:0] l1_u, l1_v, l1_w, l1_z;
    assign l1_u = u_in ^ (rotl(v_in, 31) & rotl(w_in, 53));
    assign l1_v = v_in ^ (rotl(w_in, 17) & rotl(z_in, 43));
    assign l1_w = w_in ^ (rotl(z_in,  7) & rotl(u_in, 23));
    assign l1_z = z_in ^ (rotl(u_in,  5) & rotl(v_in, 19));

    //-------------------------------------------------------------------------
    // Level 2: reads Level 1 outputs
    //-------------------------------------------------------------------------
    wire [63:0] l2_u, l2_v, l2_w, l2_z;
    assign l2_u = l1_u ^ (rotl(l1_v, 17) & rotl(l1_z, 43));
    assign l2_v = l1_v ^ (rotl(l1_w,  7) & rotl(l1_u, 23));
    assign l2_w = l1_w ^ (rotl(l1_z,  5) & rotl(l1_v, 19));
    assign l2_z = l1_z ^ (rotl(l1_u, 31) & rotl(l1_w, 53));

    //-------------------------------------------------------------------------
    // Pre-mix 2: intra-word diffusion (aligned with Levels 3-4 constants)
    //-------------------------------------------------------------------------
    wire [63:0] pm_u, pm_v, pm_w, pm_z;
    assign pm_u = l2_u ^ rotl(l2_u, 16) ^ rotl(l2_u, 14);
    assign pm_v = l2_v ^ rotl(l2_v, 16) ^ rotl(l2_v, 14);
    assign pm_w = l2_w ^ rotl(l2_w, 16) ^ rotl(l2_w, 14);
    assign pm_z = l2_z ^ rotl(l2_z, 16) ^ rotl(l2_z, 14);

    //-------------------------------------------------------------------------
    // Level 3: reads pre-mix outputs
    //-------------------------------------------------------------------------
    wire [63:0] l3_u, l3_v, l3_w, l3_z;
    assign l3_u = pm_u ^ (rotl(pm_z,  7) & rotl(pm_u, 23));
    assign l3_v = pm_v ^ (rotl(pm_u,  5) & rotl(pm_v, 19));
    assign l3_w = pm_w ^ (rotl(pm_v, 31) & rotl(pm_w, 53));
    assign l3_z = pm_z ^ (rotl(pm_w, 17) & rotl(pm_z, 43));

    //-------------------------------------------------------------------------
    // Level 4: reads Level 3 outputs (w pair is (17,53) per the C)
    //-------------------------------------------------------------------------
    assign u_out = l3_u ^ (rotl(l3_v,  5) & rotl(l3_w, 19));
    assign v_out = l3_v ^ (rotl(l3_w, 31) & rotl(l3_z, 53));
    assign w_out = l3_w ^ (rotl(l3_z, 17) & rotl(l3_u, 53));
    assign z_out = l3_z ^ (rotl(l3_u,  7) & rotl(l3_v, 23));

endmodule

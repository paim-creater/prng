//=============================================================================
// Tempest v3 - Output Function (Algorithm 1, bit-exact)
//
// make_output(u,v,w,z), verbatim from the C ground truth:
//   t = u ^ rot(v,32) ^ w ^ rot(z,16)
//   t ^= rot(t,22) ^ rot(t,26)
//   t ^= rot(t,16) ^ rot(t,14)
//   t = andmix4(t)   (single word: pairs (31,53),(17,43),(7,23),(5,19))
//   out = t ^ (t >> 32)
//
// This single-output variant (64 bits per round) is the area-reduced
// version that fits the iCE40 HX8K; the dual 128-bit variant is in
// output_function_dual.v (two evaluations on the rotated pairs
// (u,v,w,z) and (v,w,z,u), exactly tempest_u64x2 in the C).
//=============================================================================
module output_function (
    input  wire [63:0] u, v, w, z,
    output wire [63:0] o0
);

    function [63:0] rotl;
        input [63:0] a;
        input [5:0]  r;
        begin
            rotl = (a << r) | (a >> (64 - r));
        end
    endfunction

    function [63:0] make_output;
        input [63:0] fu, fv, fw, fz;
        reg [63:0] t;
        begin
            t = fu ^ rotl(fv, 32) ^ fw ^ rotl(fz, 16);
            t = t ^ rotl(t, 22) ^ rotl(t, 26);
            t = t ^ rotl(t, 16) ^ rotl(t, 14);
            t = t ^ (rotl(t, 31) & rotl(t, 53));
            t = t ^ (rotl(t, 17) & rotl(t, 43));
            t = t ^ (rotl(t,  7) & rotl(t, 23));
            t = t ^ (rotl(t,  5) & rotl(t, 19));
            make_output = t ^ (t >> 32);
        end
    endfunction

    assign o0 = make_output(u, v, w, z);

endmodule

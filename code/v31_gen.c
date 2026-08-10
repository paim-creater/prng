/* v31_gen.c — byte-stream generator for the v3.1 dead-key predecessor.
 *
 * Reconstructed from cryptanalysis_v2.c (the audit record's v3.1 round
 * function: snapshot XOR-ROT diffusion + pre-mix + 4-word andmix4, with
 * the v3.1 output function). v3.1's defining defect is structural:
 * there is NO key injection in the round (tau = 0), so the output is
 * key-independent — the "dead-key" class the calibrated stack detects
 * (a_1 = 0, tau = 0) and Dieharder's rgb_lagged_sum catches at p = 0.
 *
 * Usage: ./v31_gen [seed] > v31.bin     (writes 64-bit words, little-endian)
 * The generated stream feeds dieharder -g 201 (file_input_raw), exactly
 * reproducing the /tmp/dh_v31.bin protocol of the archived log.
 */
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>

static inline uint64_t rotl(uint64_t x, int r){ return (x << r) | (x >> (64 - r)); }

static inline uint64_t andmix4(uint64_t t){
    t ^= rotl(t, 31) & rotl(t, 53);
    t ^= rotl(t, 17) & rotl(t, 43);
    t ^= rotl(t,  7) & rotl(t, 23);
    t ^= rotl(t,  5) & rotl(t, 19);
    return t;
}

/* v3.1 round: snapshot XOR-ROT + pre-mix + 4-word andmix4, NO key injection */
static void zfc_round(uint64_t *up, uint64_t *vp, uint64_t *wp, uint64_t *zp){
    uint64_t u = *up, v = *vp, w = *wp, z = *zp;
    uint64_t u0 = u, v0 = v, w0 = w, z0 = z;
    u = u0 ^ rotl(v0, 5) ^ rotl(w0, 13) ^ rotl(z0, 25);
    v = v0 ^ rotl(w0, 11) ^ rotl(z0, 19) ^ rotl(u0, 29);
    w = w0 ^ rotl(z0, 23) ^ rotl(u0, 9) ^ rotl(v0, 15);
    z = z0 ^ rotl(u0, 17) ^ rotl(v0, 27) ^ rotl(w0, 21);
    u ^= rotl(u, 22) ^ rotl(u, 26); u = andmix4(u);
    v ^= rotl(v, 22) ^ rotl(v, 26); v = andmix4(v);
    w ^= rotl(w, 22) ^ rotl(w, 26); w = andmix4(w);
    z ^= rotl(z, 22) ^ rotl(z, 26); z = andmix4(z);
    *up = u; *vp = v; *wp = w; *zp = z;
}

/* v3.1 output: fold4 -> self-diff (27,17) -> andmix4 -> whitener */
static uint64_t make_output(uint64_t u, uint64_t v, uint64_t w, uint64_t z){
    uint64_t t = u ^ rotl(v, 32) ^ w ^ rotl(z, 16);
    t ^= rotl(t, 27) ^ rotl(t, 17);
    t = andmix4(t);
    t ^= t >> 32;
    return t;
}

int main(int argc, char **argv){
    uint64_t seed = argc > 1 ? strtoull(argv[1], NULL, 0) : 0x9E3779B97F4A7C15ULL;
    /* v3.1 init: fixed state, 22 dummy rounds (the historical protocol),
       then continuous generation */
    uint64_t u = seed, v = seed ^ 0x6A09E667F3BCC908ULL,
             w = seed ^ 0x3243F6A8885A308DULL, z = seed ^ 0xB7E151628AED2A6BULL;
    for (int i = 0; i < 22; i++) zfc_round(&u, &v, &w, &z);
    setbuf(stdout, NULL);
    for (;;){
        uint64_t o = make_output(u, v, w, z);
        fwrite(&o, sizeof(o), 1, stdout);
        zfc_round(&u, &v, &w, &z);
    }
    return 0;
}

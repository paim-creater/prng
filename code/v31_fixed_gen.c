/* v31_fixed_gen.c — v3.1 with the Phase-B linear-part fix.
 *
 * Fix (2026-08-10, diagnosis-driven): the original v3.1 Phase B had
 * each word = self XOR three rotated terms — four terms per row, so
 * the row sums vanish mod 2 and the all-ones vector lies in the
 * kernel of the linear part (GF(2) rank 248/256, with a 64-step
 * collapse direction). The fix drops one rotation per word: each
 * word is now self XOR two rotations (three terms, odd row sum),
 * which restores full rank 256/256 and removes the collapse
 * direction, while keeping the original rotation set (5,13 / 11,19 /
 * 23,9 / 17,27) and the rest of the v3.1 round unchanged.
 *
 *   original: u = u0 ^ r5(v0) ^ r13(w0) ^ r25(z0)      (rank 248)
 *   fixed:    u = u0 ^ r5(v0) ^ r13(w0)                (rank 256)
 *
 * Verified: full GF(2) rank, no 64/128-step collapse, and Dieharder
 * rgb_lagged_sum / marsaglia_tsang_gcd / diehard_* all PASS (see
 * data/dieharder_v31_fixed_20260810.txt).
 *
 * Usage: ./v31_fixed_gen [seed] > v31_fixed.bin
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

static void round_fixed(uint64_t *up, uint64_t *vp, uint64_t *wp, uint64_t *zp){
    uint64_t u = *up, v = *vp, w = *wp, z = *zp;
    uint64_t u0 = u, v0 = v, w0 = w, z0 = z;
    /* Phase B (fixed): self + two rotations per word */
    u = u0 ^ rotl(v0, 5) ^ rotl(w0, 13);
    v = v0 ^ rotl(w0, 11) ^ rotl(z0, 19);
    w = w0 ^ rotl(z0, 23) ^ rotl(u0, 9);
    z = z0 ^ rotl(u0, 17) ^ rotl(v0, 27);
    /* Phase C: pre-mix + 4-word andmix4 (unchanged) */
    u ^= rotl(u, 22) ^ rotl(u, 26); u = andmix4(u);
    v ^= rotl(v, 22) ^ rotl(v, 26); v = andmix4(v);
    w ^= rotl(w, 22) ^ rotl(w, 26); w = andmix4(w);
    z ^= rotl(z, 22) ^ rotl(z, 26); z = andmix4(z);
    *up = u; *vp = v; *wp = w; *zp = z;
}

static uint64_t make_output(uint64_t u, uint64_t v, uint64_t w, uint64_t z){
    uint64_t t = u ^ rotl(v, 32) ^ w ^ rotl(z, 16);
    t ^= rotl(t, 27) ^ rotl(t, 17);
    t = andmix4(t);
    t ^= t >> 32;
    return t;
}

int main(int argc, char **argv){
    uint64_t seed = argc > 1 ? strtoull(argv[1], NULL, 0) : 0x9E3779B97F4A7C15ULL;
    uint64_t u = seed, v = seed ^ 0x6A09E667F3BCC908ULL,
             w = seed ^ 0x3243F6A8885A308DULL, z = seed ^ 0xB7E151628AED2A6BULL;
    for (int i = 0; i < 22; i++) round_fixed(&u, &v, &w, &z);
    setbuf(stdout, NULL);
    for (;;){
        uint64_t o = make_output(u, v, w, z);
        fwrite(&o, sizeof(o), 1, stdout);
        round_fixed(&u, &v, &w, &z);
    }
    return 0;
}

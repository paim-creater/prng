/* tempest_a1_avx512.c — Algorithm-1 (published Tempest v3) ported to
 * AVX-512, 8-way parallel. OPTIMIZED 2026-08-08: vprolq rotates +
 * always_inline (bit-exact; KAT unchanged).  Bit-exact port of the scalar C
 * (github_release/src/tempest_v3.c); KAT 0x6BBE30BB... must match.
 *
 * Compile: gcc -O3 -march=native -mavx512f -o bench_a1_avx512 bench_a1_avx512.c
 */
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <windows.h>
#include <immintrin.h>

#define WEYL_GOLDEN 0x9E3779B97F4A7C15ULL
#define K_U 0x9E3779B97F4A7C15ULL
#define K_V 0x3C6EF372FE94F82AULL
#define K_W 0x5A8279998F1BBD27ULL
#define K_Z 0x6ED9EBA1F97F3B4CULL

typedef struct {
    __m512i u, v, w, z;
    __m512i weyl, weyl_nl;
    __m512i rounds;
} A1S8;

/* Optimized (2026-08-08): rotations compile to single vprolq/vprorq
 * (AVX512F) instead of GCC's shift-pair expansion (sll+srll+or, 3 instrs).
 * Bit-exact: identical semantics; KAT 0x6BBE30BB... unchanged. */
#define rl(x, r) _mm512_rol_epi64((x), (r))
#define rr(x, r) _mm512_ror_epi64((x), (r))
/* variable-count rotate (runtime count): only used in a1_init (not hot) */
#define rl_v(x, r) _mm512_or_si512(_mm512_slli_epi64((x), (r)),                                   _mm512_srli_epi64((x), 64 - (r)))
#define SET1(x) _mm512_set1_epi64((x))
#define X(a,b) _mm512_xor_si512((a),(b))
#define A(a,b) _mm512_and_si512((a),(b))

/* one round of Algorithm 1, 8 streams in parallel */
static void a1_round(A1S8 *s) {
    __m512i u = s->u, v = s->v, w = s->w, z = s->z;
    __m512i u0 = u, v0 = v, w0 = w, z0 = z;   /* round-start snapshot */

    /* Phase A: GF(2) nonlinear diffusion (reads from snapshot) */
    u = X(X(X(u0, rl(v0,5)), rl(w0,17)), X(A(rl(v0,5), rl(z0,25)), SET1(K_U)));
    v = X(X(X(v0, rl(w0,11)), rl(z0,23)), X(A(rl(w0,11), rl(u0,29)), SET1(K_V)));
    w = X(X(X(w0, rl(z0,13)), rl(u0,31)), X(A(rl(u0,9), rl(v0,15)), SET1(K_W)));
    z = X(X(X(z0, rl(u0,17)), rl(v0,7)), X(A(rl(v0,27), rl(w0,21)), SET1(K_Z)));

    /* Phase A(lin): snapshot ANDs covering (u,z) and (w,z) */
    u = X(u, A(rl(z0,23), rl(w0,53)));
    z = X(z, A(rl(u0,5), rl(z0,25)));

    /* Phase B: GF(2) round key (XOR Weyl, nilpotent linear part) + filter */
    __m512i wv = s->weyl;
    wv = X(X(wv, rl(wv,19)), SET1(WEYL_GOLDEN));
    __m512i wv_nl = X(wv, rl(A(wv, SET1(WEYL_GOLDEN)), 13));
    u = X(u, X(rl(wv_nl,7), _mm512_srli_epi64(wv_nl,17)));
    v = X(v, X(rl(wv_nl,19), _mm512_srli_epi64(wv_nl,23)));
    w = X(w, X(rl(wv_nl,31), _mm512_srli_epi64(wv_nl,29)));
    z = X(z, X(rl(wv_nl,43), _mm512_srli_epi64(wv_nl,37)));
    s->weyl = wv;

    /* Phase C: pre-mix 1 (22,26) + intra-word AND (7,19) */
    u = X(X(X(u, rl(u,22)), rl(u,26)), A(rl(u,7), rl(u,19)));
    v = X(X(X(v, rl(v,22)), rl(v,26)), A(rl(v,7), rl(v,19)));
    w = X(X(X(w, rl(w,22)), rl(w,26)), A(rl(w,7), rl(w,19)));
    z = X(X(X(z, rl(z,22)), rl(z,26)), A(rl(z,7), rl(z,19)));

    /* Level 1 */
    __m512i u1 = X(u, A(rl(v,31), rl(w,53))), v1 = X(v, A(rl(w,17), rl(z,43)));
    __m512i w1 = X(w, A(rl(z,7), rl(u,23))), z1 = X(z, A(rl(u,5), rl(v,19)));
    /* Level 2 */
    __m512i u2 = X(u1, A(rl(v1,17), rl(z1,43))), v2 = X(v1, A(rl(w1,7), rl(u1,23)));
    __m512i w2 = X(w1, A(rl(z1,5), rl(v1,19))), z2 = X(z1, A(rl(u1,31), rl(w1,53)));
    /* pre-mix 2 (16,14) */
    u2 = X(X(u2, rl(u2,16)), rl(u2,14)); v2 = X(X(v2, rl(v2,16)), rl(v2,14));
    w2 = X(X(w2, rl(w2,16)), rl(w2,14)); z2 = X(X(z2, rl(z2,16)), rl(z2,14));
    /* Level 3 */
    __m512i u3 = X(u2, A(rl(z2,7), rl(u2,23))), v3 = X(v2, A(rl(u2,5), rl(v2,19)));
    __m512i w3 = X(w2, A(rl(v2,31), rl(w2,53))), z3 = X(z2, A(rl(w2,17), rl(z2,43)));
    /* Level 4 */
    __m512i uc = X(u3, A(rl(v3,5), rl(w3,19))), vc = X(v3, A(rl(w3,31), rl(z3,53)));
    __m512i wc = X(w3, A(rl(z3,17), rl(u3,53))), zc = X(z3, A(rl(u3,7), rl(v3,23)));

    /* Phase D: cross-word mixing */
    s->u = X(X(uc, rl(vc,3)), rl(wc,9));
    s->v = X(X(vc, rl(wc,5)), rl(zc,11));
    s->w = X(X(wc, rl(zc,9)), rl(uc,13));
    s->z = X(X(zc, rl(uc,11)), rl(vc,17));
    s->rounds = _mm512_add_epi64(s->rounds, _mm512_set1_epi64(1));
}

/* Algorithm-1 output function, 8 streams */
static __m512i a1_output(__m512i u, __m512i v, __m512i w, __m512i z) {
    __m512i t = X(X(X(u, rl(v,32)), w), rl(z,16));
    t = X(X(t, rl(t,22)), rl(t,26));
    t = X(X(t, rl(t,16)), rl(t,14));
    t = X(t, A(rl(t,31), rl(t,53)));
    t = X(t, A(rl(t,17), rl(t,43)));
    t = X(t, A(rl(t,7), rl(t,23)));
    t = X(t, A(rl(t,5), rl(t,19)));
    t = X(t, _mm512_srli_epi64(t,32));
    return t;
}

/* initialization: 8 streams, each with its own key/nonce */
static __attribute__((always_inline)) inline void a1_init(A1S8 *s, const uint64_t key[8][4], const uint64_t nonce[8][2]) {
    s->u = _mm512_set_epi64(key[7][0], key[6][0], key[5][0], key[4][0], key[3][0], key[2][0], key[1][0], key[0][0]);
    s->v = X(_mm512_set_epi64(key[7][1], key[6][1], key[5][1], key[4][1], key[3][1], key[2][1], key[1][1], key[0][1]), _mm512_set_epi64(nonce[7][0], nonce[6][0], nonce[5][0], nonce[4][0], nonce[3][0], nonce[2][0], nonce[1][0], nonce[0][0]));
    s->w = X(_mm512_set_epi64(key[7][2], key[6][2], key[5][2], key[4][2], key[3][2], key[2][2], key[1][2], key[0][2]), _mm512_set_epi64(nonce[7][1], nonce[6][1], nonce[5][1], nonce[4][1], nonce[3][1], nonce[2][1], nonce[1][1], nonce[0][1]));
    s->z = X(_mm512_set_epi64(key[7][3], key[6][3], key[5][3], key[4][3], key[3][3], key[2][3], key[1][3], key[0][3]), SET1(0x54454D5035583543ULL));
    s->weyl = SET1(0x6A09E667F3BCC908ULL);
    s->rounds = _mm512_setzero_si512();
    __m512i kw = SET1(0x6A09E667F3BCC908ULL);
    for (int i = 0; i < 16; i++) {
        a1_round(s);
        kw = X(X(kw, rl(kw,19)), SET1(WEYL_GOLDEN));
        if (i < 8) {
            if (i & 1) {
                s->u = X(X(s->u, rl_v(_mm512_set_epi64(key[7][0], key[6][0], key[5][0], key[4][0], key[3][0], key[2][0], key[1][0], key[0][0]), i+1)), kw);
                s->v = X(X(s->v, rl_v(_mm512_set_epi64(key[7][1], key[6][1], key[5][1], key[4][1], key[3][1], key[2][1], key[1][1], key[0][1]), i+1)), _mm512_slli_epi64(kw,17));
                s->w = X(X(s->w, rl_v(_mm512_set_epi64(key[7][2], key[6][2], key[5][2], key[4][2], key[3][2], key[2][2], key[1][2], key[0][2]), i+1)), _mm512_srli_epi64(kw,13));
                s->z = X(X(s->z, rl_v(_mm512_set_epi64(key[7][3], key[6][3], key[5][3], key[4][3], key[3][3], key[2][3], key[1][3], key[0][3]), i+1)), rl(kw,31));
            } else {
                s->u = X(X(s->u, _mm512_set_epi64(key[7][0], key[6][0], key[5][0], key[4][0], key[3][0], key[2][0], key[1][0], key[0][0])), kw);
                s->v = X(X(s->v, _mm512_set_epi64(key[7][1], key[6][1], key[5][1], key[4][1], key[3][1], key[2][1], key[1][1], key[0][1])), _mm512_slli_epi64(kw,17));
                s->w = X(X(s->w, _mm512_set_epi64(key[7][2], key[6][2], key[5][2], key[4][2], key[3][2], key[2][2], key[1][2], key[0][2])), _mm512_srli_epi64(kw,13));
                s->z = X(X(s->z, _mm512_set_epi64(key[7][3], key[6][3], key[5][3], key[4][3], key[3][3], key[2][3], key[1][3], key[0][3])), rl(kw,31));
            }
        } else {
            __m512i n0 = _mm512_set_epi64(nonce[7][i&1], nonce[6][i&1], nonce[5][i&1], nonce[4][i&1], nonce[3][i&1], nonce[2][i&1], nonce[1][i&1], nonce[0][i&1]);
            __m512i n1 = _mm512_set_epi64(nonce[7][1-(i&1)], nonce[6][1-(i&1)], nonce[5][1-(i&1)], nonce[4][1-(i&1)], nonce[3][1-(i&1)], nonce[2][1-(i&1)], nonce[1][1-(i&1)], nonce[0][1-(i&1)]);
            s->u = X(s->u, n0);
            s->v = X(X(s->v, rl(n1,19)), _mm512_set1_epi64((uint64_t)i));
            s->z = X(s->z, rl(n0,43));
        }
    }
    for (int i = 0; i < 6; i++) a1_round(s);
    s->u = X(s->u, _mm512_set_epi64(key[7][0], key[6][0], key[5][0], key[4][0], key[3][0], key[2][0], key[1][0], key[0][0]));
    s->v = X(s->v, _mm512_set_epi64(key[7][1], key[6][1], key[5][1], key[4][1], key[3][1], key[2][1], key[1][1], key[0][1]));
    s->w = X(s->w, _mm512_set_epi64(key[7][2], key[6][2], key[5][2], key[4][2], key[3][2], key[2][2], key[1][2], key[0][2]));
    s->z = X(s->z, _mm512_set_epi64(key[7][3], key[6][3], key[5][3], key[4][3], key[3][3], key[2][3], key[1][3], key[0][3]));
}

static inline uint64_t rdtsc(void) {
    unsigned lo, hi;
    __asm__ volatile ("rdtsc" : "=a"(lo), "=d"(hi));
    return ((uint64_t)hi << 32) | lo;
}
static double now_ms(void) {
    LARGE_INTEGER f, c;
    QueryPerformanceFrequency(&f); QueryPerformanceCounter(&c);
    return (double)c.QuadPart * 1000.0 / (double)f.QuadPart;
}

int main(void) {
    /* KAT: all 8 streams with key [1,2,3,4] nonce [5,6] must equal the
     * published Algorithm-1 KAT 0x6BBE30BB... */
    uint64_t key[8][4], nonce[8][2];
    for (int i = 0; i < 8; i++) {
        key[i][0]=1; key[i][1]=2; key[i][2]=3; key[i][3]=4;
        nonce[i][0]=5; nonce[i][1]=6;
    }
    A1S8 s;
    a1_init(&s, key, nonce);
    uint64_t exp[5] = {0x6BBE30BB1D12DDD0ULL, 0xB9167FE6CCEC68D9ULL,
                       0xCF6F7BA5C6AED360ULL, 0xA53C77D6D081BEC3ULL,
                       0x7F5A13D9CBF1CD84ULL};
    int ok = 1;
    for (int k = 0; k < 5; k++) {
        a1_round(&s);
        __m512i o = a1_output(s.u, s.v, s.w, s.z);
        uint64_t out[8];
        _mm512_storeu_epi64(out, o);
        for (int i = 0; i < 8; i++)
            if (out[i] != exp[k]) { ok = 0; printf("KAT %d stream %d FAIL\n", k, i); }
    }
    printf("KAT (8 streams, Algorithm-1): %s\n", ok ? "PASS" : "FAIL");

    /* benchmark: dual output, 8 streams x 128 bits/round = 1024 bits/round */
    volatile uint64_t sink = 0;
    __m512i acc = _mm512_setzero_si512();
    const long long N = 100000000LL;
    a1_init(&s, key, nonce);
    for (int i = 0; i < 1000000; i++) { a1_round(&s); acc = X(acc, s.u); }
    uint64_t tsc0 = rdtsc();
    double t0 = now_ms();
    for (long long i = 0; i < N; i++) {
        a1_round(&s);
        acc = X(acc, X(a1_output(s.u,s.v,s.w,s.z), a1_output(s.v,s.w,s.z,s.u)));
    }
    double t1 = now_ms();
    uint64_t tsc1 = rdtsc();
    double freq = (double)(tsc1 - tsc0) / ((t1 - t0) / 1000.0) / 1e9;
    double gbps = (double)N * 8.0 * 128.0 / ((t1 - t0) / 1000.0) / 1e9;
    double scale = 5.0 / freq;
    sink ^= _mm512_reduce_add_epi64(acc);
    printf("freq=%.3f GHz  AVX-512 dual (8 streams): %.1f Gbit/s  (->5GHz: %.1f)\n",
           freq, gbps, gbps * scale);
    return 0;
}

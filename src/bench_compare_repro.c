/* bench_compare_repro.c — unified long-run comparison of v3 vs v4
 * round function throughput (N=1e8, alternating order, 3 rounds each). */
#include <stdio.h>
#include <stdint.h>
#include <windows.h>
static double now_ms(void) {
    LARGE_INTEGER f, c;
    QueryPerformanceFrequency(&f); QueryPerformanceCounter(&c);
    return (double)c.QuadPart * 1000.0 / (double)f.QuadPart;
}
#include "tempest_v3.c"          /* v3: enhanced_round */
static double bench_v3(void) {
    tempest_state s;
    uint64_t key[4] = {1,2,3,4}, nonce[2] = {5,6};
    tempest_init(&s, key, nonce);
    volatile uint64_t sink = 0; uint64_t acc = 0;
    const long long N = 100000000LL;
    for (int i = 0; i < 2000000; i++) { enhanced_round(&s); acc ^= s.u; }
    double t0 = now_ms();
    for (long long i = 0; i < N; i++) { enhanced_round(&s); acc ^= s.u ^ s.v ^ s.w ^ s.z; }
    double t1 = now_ms();
    sink ^= acc;
    return (double)N * 128.0 / ((t1 - t0) / 1000.0) / 1e9;
}
/* v4 round via the emitted C — replicate its round here to avoid TU clash */
#include <stdint.h>
static inline uint64_t r4(uint64_t x, int r) { return (x << r) | (x >> (64 - r)); }
static void v4_round(uint64_t *up, uint64_t *vp, uint64_t *wp, uint64_t *zp, uint64_t *wep) {
    /* identical structure to tempest_v4_round (constant-level opt of v3) */
    uint64_t u = *up, v = *vp, w = *wp, z = *zp;
    uint64_t u0 = u, v0 = v, w0 = w, z0 = z;
    uint64_t wv = *wep, wv_nl = wv;
    u ^= r4(v0,5) ^ r4(w0,17); u ^= r4(v0,5) & r4(z0,25);
    v ^= r4(w0,11) ^ r4(z0,23); v ^= r4(w0,11) & r4(u0,29);
    w ^= r4(z0,13) ^ r4(u0,31); w ^= r4(u0,9) & r4(v0,15);
    z ^= r4(u0,17) ^ r4(v0,7); z ^= r4(v0,27) & r4(w0,21);
    u ^= r4(z0,23) & r4(w0,53); z ^= r4(u0,5) & r4(z0,25);
    wv ^= r4(wv, 19) ^ 0x9E3779B97F4A7C15ULL;
    wv_nl = wv ^ r4(wv & 0x9E3779B97F4A7C15ULL, 13);
    u ^= r4(wv_nl,7) ^ (wv_nl >> 17); v ^= r4(wv_nl,19) ^ (wv_nl >> 23);
    w ^= r4(wv_nl,31) ^ (wv_nl >> 29); z ^= r4(wv_nl,43) ^ (wv_nl >> 37);
    *wep = wv;
    u ^= r4(u,22) ^ r4(u,26) ^ (r4(u,7) & r4(u,19));
    v ^= r4(v,22) ^ r4(v,26) ^ (r4(v,7) & r4(v,19));
    w ^= r4(w,22) ^ r4(w,26) ^ (r4(w,7) & r4(w,19));
    z ^= r4(z,22) ^ r4(z,26) ^ (r4(z,7) & r4(z,19));
    uint64_t u1 = u ^ (r4(v,31) & r4(w,53)), v1 = v ^ (r4(w,17) & r4(z,43));
    uint64_t w1 = w ^ (r4(z,7) & r4(u,23)), z1 = z ^ (r4(u,5) & r4(v,19));
    uint64_t u2 = u1 ^ (r4(v1,17) & r4(z1,43)), v2 = v1 ^ (r4(w1,7) & r4(u1,23));
    uint64_t w2 = w1 ^ (r4(z1,5) & r4(v1,19)), z2 = z1 ^ (r4(u1,31) & r4(w1,53));
    u2 ^= r4(u2,16) ^ r4(u2,14); v2 ^= r4(v2,16) ^ r4(v2,14);
    w2 ^= r4(w2,16) ^ r4(w2,14); z2 ^= r4(z2,16) ^ r4(z2,14);
    uint64_t u3 = u2 ^ (r4(z2,7) & r4(u2,23)), v3 = v2 ^ (r4(u2,5) & r4(v2,19));
    uint64_t w3 = w2 ^ (r4(v2,31) & r4(w2,53)), z3 = z2 ^ (r4(w2,17) & r4(z2,43));
    uint64_t uc = u3 ^ (r4(v3,5) & r4(w3,19)), vc = v3 ^ (r4(w3,31) & r4(z3,53));
    uint64_t wc = w3 ^ (r4(z3,17) & r4(u3,53)), zc = z3 ^ (r4(u3,7) & r4(v3,23));
    *up = uc ^ r4(vc,3) ^ r4(wc,9);
    *vp = vc ^ r4(wc,5) ^ r4(zc,11);
    *wp = wc ^ r4(zc,9) ^ r4(uc,13);
    *zp = zc ^ r4(uc,11) ^ r4(vc,17);
}
static double bench_v4(void) {
    uint64_t u=1,v=2,w=3,z=4,weyl=0x6A09E667F3BCC908ULL;
    volatile uint64_t sink = 0; uint64_t acc = 0;
    const long long N = 100000000LL;
    for (int i = 0; i < 2000000; i++) { v4_round(&u,&v,&w,&z,&weyl); acc ^= u; }
    double t0 = now_ms();
    for (long long i = 0; i < N; i++) { v4_round(&u,&v,&w,&z,&weyl); acc ^= u^v^w^z; }
    double t1 = now_ms();
    sink ^= acc;
    return (double)N * 128.0 / ((t1 - t0) / 1000.0) / 1e9;
}
int main(void) { bench_dual_single();
    for (int i = 0; i < 3; i++) {
        double a = bench_v3(), b = bench_v4();
        printf("round v3: %7.2f  v4: %7.2f Gbit/s\n", a, b);
    }
    return 0;
}

/* dual and single output long-run measurements */
#include "tempest_v3.c"  /* make_output available */
void bench_dual_single(void) {
    tempest_state s;
    uint64_t key[4] = {1,2,3,4}, nonce[2] = {5,6};
    const long long N = 50000000LL;
    volatile uint64_t sink = 0; uint64_t acc = 0;
    /* dual */
    tempest_init(&s, key, nonce);
    for (int i = 0; i < 1000000; i++) { enhanced_round(&s);
        acc ^= make_output(s.u,s.v,s.w,s.z) ^ make_output(s.v,s.w,s.z,s.u); }
    double t0 = now_ms();
    for (long long i = 0; i < N; i++) { enhanced_round(&s);
        acc ^= make_output(s.u,s.v,s.w,s.z) ^ make_output(s.v,s.w,s.z,s.u); }
    double t1 = now_ms();
    sink ^= acc;
    double dual = (double)N * 128.0 / ((t1 - t0) / 1000.0) / 1e9;
    /* single */
    tempest_init(&s, key, nonce);
    for (int i = 0; i < 1000000; i++) { enhanced_round(&s); acc ^= make_output(s.u,s.v,s.w,s.z); }
    t0 = now_ms();
    for (long long i = 0; i < N; i++) { enhanced_round(&s); acc ^= make_output(s.u,s.v,s.w,s.z); }
    t1 = now_ms();
    sink ^= acc;
    double single = (double)N * 64.0 / ((t1 - t0) / 1000.0) / 1e9;
    printf("dual v3: %7.2f   single v3: %7.2f Gbit/s\n", dual, single);
}
int main2(void) { bench_dual_single(); return 0; }

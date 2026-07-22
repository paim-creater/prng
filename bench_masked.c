/* bench_masked.c — Tempest v3 + 1st-order boolean masking benchmark
   Compile: gcc -O3 -march=native -o bench_masked.exe bench_masked.c src/tempest_v3.c -I.
   Run:    ./bench_masked.exe */
#include "src/tempest_v3.h"
#include <stdio.h>
#include <string.h>

#ifdef _WIN32
#include <windows.h>
static double now_ms(void) {
    LARGE_INTEGER f, c;
    QueryPerformanceFrequency(&f); QueryPerformanceCounter(&c);
    return (double)c.QuadPart * 1000.0 / (double)f.QuadPart;
}
#else
#include <sys/time.h>
static double now_ms(void) {
    struct timeval tv; gettimeofday(&tv, NULL);
    return tv.tv_sec * 1000.0 + tv.tv_usec / 1000.0;
}
#endif

static inline uint64_t rotl64(uint64_t x, int r) {
    return (x << r) | (x >> (64 - r));
}

/* Standard andmix4 */
static inline uint64_t andmix4_ref(uint64_t t) {
    uint64_t a, b;
    a = rotl64(t, 31); b = rotl64(t, 53); t ^= a & b;
    a = rotl64(t, 17); b = rotl64(t, 43); t ^= a & b;
    a = rotl64(t,  7); b = rotl64(t, 23); t ^= a & b;
    a = rotl64(t,  5); b = rotl64(t, 19); t ^= a & b;
    return t;
}

/* 1st-order masked andmix4 (ISW 2003, d=1) */
static inline uint64_t andmix4_masked(uint64_t t, uint64_t m, uint64_t *mout) {
    uint64_t a, b, r;
    a = rotl64(t,31) ^ rotl64(m,31);  b = rotl64(t,53) ^ rotl64(m,53);
    r  = (a & b) ^ (a & rotl64(m,53)) ^ (rotl64(m,31) & b) ^ (rotl64(m,31) & rotl64(m,53));
    t ^= r;  m = rotl64(m,31) ^ rotl64(t,31) ^ rotl64(t,53);

    a = rotl64(t,17) ^ rotl64(m,17);  b = rotl64(t,43) ^ rotl64(m,43);
    r  = (a & b) ^ (a & rotl64(m,43)) ^ (rotl64(m,17) & b) ^ (rotl64(m,17) & rotl64(m,43));
    t ^= r;

    a = rotl64(t, 7) ^ rotl64(m, 7);  b = rotl64(t,23) ^ rotl64(m,23);
    r  = (a & b) ^ (a & rotl64(m,23)) ^ (rotl64(m,7) & b) ^ (rotl64(m,7) & rotl64(m,23));
    t ^= r;

    a = rotl64(t, 5) ^ rotl64(m, 5);  b = rotl64(t,19) ^ rotl64(m,19);
    r  = (a & b) ^ (a & rotl64(m,19)) ^ (rotl64(m,5) & b) ^ (rotl64(m,5) & rotl64(m,19));
    t ^= r;

    *mout = m;
    return t;
}

/* Full masked round */
static void masked_round(tx4_state *s, uint64_t mask[4]) {
    uint64_t u = s->u, v = s->v, w = s->w, z = s->z;
    uint64_t u0 = u, v0 = v, w0 = w, z0 = z;
    uint64_t mu = mask[0], mv = mask[1], mw = mask[2], mz = mask[3];

    uint64_t wv = s->weyl + 0x9E3779B97F4A7C15ULL;
    u ^= rotl64(wv, 7) ^ (wv >> 17); v ^= rotl64(wv, 19) ^ (wv >> 23);
    w ^= rotl64(wv, 31) ^ (wv >> 29); z ^= rotl64(wv, 43) ^ (wv >> 37);
    s->weyl = wv;

    u = u0 ^ rotl64(v0,5) ^ rotl64(w0,13) ^ rotl64(z0,25);
    v = v0 ^ rotl64(w0,11) ^ rotl64(z0,19) ^ rotl64(u0,29);
    w = w0 ^ rotl64(z0,23) ^ rotl64(u0,9) ^ rotl64(v0,15);
    z = z0 ^ rotl64(u0,17) ^ rotl64(v0,27) ^ rotl64(w0,21);

    u ^= rotl64(u,22) ^ rotl64(u,26); u = andmix4_masked(u, mu, &mu);
    v ^= rotl64(v,22) ^ rotl64(v,26); v = andmix4_masked(v, mv, &mv);
    w ^= rotl64(w,22) ^ rotl64(w,26); w = andmix4_masked(w, mw, &mw);
    z ^= rotl64(z,22) ^ rotl64(z,26); z = andmix4_masked(z, mz, &mz);

    s->u = u ^ rotl64(v,3) ^ rotl64(w,9);
    s->v = v ^ rotl64(w,5) ^ rotl64(z,11);
    s->w = w ^ rotl64(z,9) ^ rotl64(u,13);
    s->z = z ^ rotl64(u,11) ^ rotl64(v,17);
    s->r++;
    mask[0] = mu; mask[1] = mv; mask[2] = mw; mask[3] = mz;
}

static uint64_t make_output_masked(uint64_t u, uint64_t v, uint64_t w, uint64_t z,
                                    uint64_t mu, uint64_t mv, uint64_t mw, uint64_t mz) {
    uint64_t t = u ^ rotl64(v,32) ^ w ^ rotl64(z,16);
    uint64_t mt = mu ^ rotl64(mv,32) ^ mw ^ rotl64(mz,16);
    t ^= rotl64(t,27) ^ rotl64(t,17);  mt ^= rotl64(mt,27) ^ rotl64(mt,17);
    t = andmix4_masked(t, mt, &mt);
    return t ^ (t >> 32);
}

static uint64_t tempest_u64_masked(tx4_state *s, uint64_t mask[4]) {
    masked_round(s, mask);
    return make_output_masked(s->u, s->v, s->w, s->z,
                              mask[0], mask[1], mask[2], mask[3]);
}

/* Volatile to prevent dead-code elimination in isolated benchmarks */
static volatile uint64_t vsum = 0;

int main() {
    uint64_t key[4] = {1,2,3,4}, nonce[2] = {5,6};
    tx4_state s;
    double t0, t1;

    printf("=== Tempest v3 — Masking Benchmark ===\n");
    printf("Compiled: " __DATE__ " " __TIME__ "\n\n");

    /*  1. Reference throughput (unmasked)  */
    tx5cmul_seed(&s, 12345);
    t0 = now_ms();
    uint64_t sum = 0;
    for (int i = 0; i < 200000000; i++)
        sum ^= tempest_u64(&s);
    t1 = now_ms();
    double t_ref = t1 - t0;
    double gbps_ref = (200000000.0 * 64.0) / (t_ref * 1e6);
    printf("Unmasked (200M): %8.0f ms  %7.1f Gbit/s\n", t_ref, gbps_ref);

    /*  2. Masked throughput  */
    uint64_t masks[4] = {0x123456789ABCDEF0ULL, 0x23456789ABCDEF01ULL,
                         0x3456789ABCDEF012ULL, 0x456789ABCDEF0123ULL};
    tx5cmul_seed(&s, 12345);
    t0 = now_ms();
    sum = 0;
    for (int i = 0; i < 100000000; i++)
        sum ^= tempest_u64_masked(&s, masks);
    t1 = now_ms();
    double t_mask = t1 - t0;
    double gbps_mask = (100000000.0 * 64.0) / (t_mask * 1e6);
    printf("Masked (100M):   %8.0f ms  %7.1f Gbit/s  (%.0f%% of ref)\n",
           t_mask, gbps_mask, (gbps_mask/gbps_ref)*100);

    /*  3. Isolated andmix4 benchmark (input varies per iter to prevent opt)  */
    #define NMIX 100000000
    uint64_t tv = 0, mo;
    t0 = now_ms();
    for (int i = 0; i < NMIX; i++) {
        tv += i;                /* vary input to prevent constant folding */
        tv = andmix4_ref(tv);
    }
    vsum = tv;  /* prevent dead-code elimination */
    t1 = now_ms();
    double t_mix_ref = t1 - t0;
    double gbps_mix_ref = (double)(NMIX * 64) / (t_mix_ref * 1e6);

    uint64_t mv = 0xFEDCBA9876543210ULL;
    tv = 0;
    t0 = now_ms();
    for (int i = 0; i < NMIX; i++) {
        tv += i;
        tv = andmix4_masked(tv, mv, &mo);
    }
    vsum = tv;
    t1 = now_ms();
    double t_mix_mask = t1 - t0;
    double gbps_mix_mask = (double)(NMIX * 64) / (t_mix_mask * 1e6);

    printf("\n--- andmix4 only (%d iters, varying input) ---\n", NMIX);
    printf("  Unmasked: %8.0f ms  %7.1f Gbit/s\n", t_mix_ref, gbps_mix_ref);
    printf("  Masked:   %8.0f ms  %7.1f Gbit/s  (+%.0f%%)\n",
           t_mix_mask, gbps_mix_mask, (t_mix_mask/t_mix_ref-1)*100);

    printf("\n=== Summary ===\n");
    printf("Unmasked Tempest v3: %.1f Gbit/s\n", gbps_ref);
    printf("Masked Tempest v3:   %.1f Gbit/s  (%.0f%% throughput)\n",
           gbps_mask, (gbps_mask/gbps_ref)*100);
    printf("Masking overhead:    +%.0f%% latency\n", (t_mask/(t_ref*0.5)-1)*100);

    return 0;
}

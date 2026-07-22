/* bench_original.c — Original Tempest v3 throughput (XOR-ROT Phase B + andmix4)
   Compile: gcc -O3 -march=native -o bench_original bench_original.c -I.
   Run:    ./bench_original.exe */
#include <stdio.h>
#include <stdint.h>
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

static inline uint64_t rotl(uint64_t x, int r) {
    return (x << r) | (x >> (64 - r));
}
static inline uint64_t andmix4(uint64_t t) {
    t ^= rotl(t,31) & rotl(t,53);
    t ^= rotl(t,17) & rotl(t,43);
    t ^= rotl(t, 7) & rotl(t,23);
    t ^= rotl(t, 5) & rotl(t,19);
    return t;
}
static inline uint64_t pm_andmix4(uint64_t t) {
    t ^= rotl(t,22) ^ rotl(t,26);
    return andmix4(t);
}

/* Exact original round function */
static void original_round(uint64_t *up, uint64_t *vp, uint64_t *wp, uint64_t *zp,
                            uint64_t *wp2, uint64_t *weyl) {
    uint64_t u = *up, v = *vp, w = *wp, z = *zp;
    uint64_t u0 = u, v0 = v, w0 = w, z0 = z;

    /* Phase A: Weyl */
    uint64_t wv = *weyl + 0x9E3779B97F4A7C15ULL;
    u ^= rotl(wv,7) ^ (wv>>17); v ^= rotl(wv,19) ^ (wv>>23);
    w ^= rotl(wv,31) ^ (wv>>29); z ^= rotl(wv,43) ^ (wv>>37);
    *weyl = wv;

    /* Phase B: XOR-ROT (original) */
    u = u0 ^ rotl(v0,5) ^ rotl(w0,13) ^ rotl(z0,25);
    v = v0 ^ rotl(w0,11) ^ rotl(z0,19) ^ rotl(u0,29);
    w = w0 ^ rotl(z0,23) ^ rotl(u0,9) ^ rotl(v0,15);
    z = z0 ^ rotl(u0,17) ^ rotl(v0,27) ^ rotl(w0,21);

    /* Phase C: andmix4 (original) */
    uint64_t u2 = pm_andmix4(u);
    uint64_t v2 = pm_andmix4(v);
    uint64_t w2 = pm_andmix4(w);
    uint64_t z2 = pm_andmix4(z);

    /* Phase D: (reads from Phase C snapshots) */
    u = u2 ^ rotl(v2,3) ^ rotl(w2,9);
    v = v2 ^ rotl(w2,5) ^ rotl(z2,11);
    w = w2 ^ rotl(z2,9) ^ rotl(u2,13);
    z = z2 ^ rotl(u2,11) ^ rotl(v2,17);

    *up = u; *vp = v; *wp = w; *zp = z;
}

static volatile uint64_t vsum = 0;

int main() {
    uint64_t u=1,v=2,w=3,z=4,weyl=0x6A09E667F3BCC908ULL;
    double t0, t1;
    int i;

    printf("=== Original Tempest v3 (XOR-ROT + andmix4) ===\n");

    /* Dual-output benchmark: 50M rounds, 128 bits/round */
    u=1;v=2;w=3;z=4;weyl=0x6A09E667F3BCC908ULL;
    t0 = now_ms();
    uint64_t dummy = 0;
    for (i = 0; i < 50000000; i++) {
        original_round(&u, &v, &w, &z, &z, &weyl);
        dummy ^= u ^ v ^ w ^ z;
    }
    vsum = dummy;
    t1 = now_ms();
    double t_dual = t1 - t0;
    double gbps_dual = (50000000.0 * 128.0) / (t_dual * 1e6);
    printf("Dual output: %8.0f ms  %7.1f Gbit/s\n", t_dual, gbps_dual);

    /* Single-output: 100M outputs, 64 bits/output */
    u=1;v=2;w=3;z=4;weyl=0x6A09E667F3BCC908ULL;
    t0 = now_ms();
    dummy = 0;
    for (i = 0; i < 100000000; i++) {
        original_round(&u, &v, &w, &z, &z, &weyl);
        dummy ^= u ^ rotl(v,32) ^ w ^ rotl(z,16);
    }
    vsum = dummy;
    t1 = now_ms();
    double t_single = t1 - t0;
    double gbps_single = (100000000.0 * 64.0) / (t_single * 1e6);
    printf("Single output: %8.0f ms  %7.1f Gbit/s\n", t_single, gbps_single);

    printf("\n=== Compare ===\n");
    printf("MDS dual was: 10.8 Gbit/s\n");
    printf("Original dual: %.1f Gbit/s\n", gbps_dual);
    printf("Ratio: %.0f%%\n", (gbps_dual / 10.8) * 100);

    return 0;
}

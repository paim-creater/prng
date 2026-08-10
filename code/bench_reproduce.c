/* bench_reproduce.c — standalone reproducibility benchmark for the
 * paper's throughput and KAT claims.  Includes tempest_v3.c directly to
 * access the static round function.  Compile:
 *   gcc -O3 -o bench_reproduce bench_reproduce.c
 * Reports: round function, single output, dual output (Gbit/s), medians
 * of RUNS runs, plus the KAT check for key [1,2,3,4] nonce [5,6].
 */
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
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
    struct timeval tv;
    gettimeofday(&tv, NULL);
    return tv.tv_sec * 1000.0 + tv.tv_usec / 1000.0;
}
#endif

#include "tempest_v3.c"   /* exposes static enhanced_round, make_output */

#define RUNS 5
#define NROUND 200000000LL

static int cmp_u64(const void *a, const void *b) {
    double x = *(const double*)a, y = *(const double*)b;
    return (x > y) - (x < y);
}

static double median(double *v, int n) {
    qsort(v, n, sizeof(double), cmp_u64);
    return v[n / 2];
}

int main(void) {
    /* ---- KAT check (key [1,2,3,4], nonce [5,6]) ---- */
    tempest_state s;
    uint64_t key[4] = {1,2,3,4}, nonce[2] = {5,6};
    uint64_t exp[5] = {0x6BBE30BB1D12DDD0ULL, 0xB9167FE6CCEC68D9ULL,
                       0xCF6F7BA5C6AED360ULL, 0xA53C77D6D081BEC3ULL,
                       0x7F5A13D9CBF1CD84ULL};
    tempest_init(&s, key, nonce);
    uint64_t out[2], got[5];
    for (int i = 0; i < 5; i++) {
        tempest_u64x2(&s, out);
        got[i] = out[0];
    }
    int ok = 1;
    for (int i = 0; i < 5; i++) if (got[i] != exp[i]) ok = 0;
    printf("KAT (5 blocks, key [1,2,3,4] nonce [5,6]): %s\n",
           ok ? "PASS" : "FAIL");
    if (!ok) {
        for (int i = 0; i < 5; i++)
            printf("  block %d: got %016llx exp %016llx\n",
                   i, (unsigned long long)got[i], (unsigned long long)exp[i]);
    }

    /* ---- throughput: round function (raw) ---- */
    double r_round[RUNS], r_single[RUNS], r_dual[RUNS];
    for (int run = 0; run < RUNS; run++) {
        tempest_state s2;
        uint64_t k[4] = {1,2,3,4}, n2[2] = {5,6};
        tempest_init(&s2, k, n2);
        volatile uint64_t sink = 0;
        /* warmup */
        for (int i = 0; i < 2000000; i++) { enhanced_round(&s2); sink ^= s2.u; }
        double t0 = now_ms();
        for (long long i = 0; i < NROUND; i++) { enhanced_round(&s2); sink ^= s2.u; }
        double t1 = now_ms();
        double secs = (t1 - t0) / 1000.0;
        r_round[run] = (double)NROUND * 256.0 / secs / 1e9;  /* 256 bits/round */

        /* single output (64 bits/round + output fn) */
        tempest_init(&s2, k, n2);
        for (int i = 0; i < 2000000; i++) { tempest_u64(&s2); sink ^= s2.u; }
        t0 = now_ms();
        for (long long i = 0; i < NROUND; i++) { tempest_u64(&s2); sink ^= s2.u; }
        t1 = now_ms();
        secs = (t1 - t0) / 1000.0;
        r_single[run] = (double)NROUND * 64.0 / secs / 1e9;

        /* dual output (128 bits/round) */
        tempest_init(&s2, k, n2);
        for (int i = 0; i < 2000000; i++) { tempest_u64x2(&s2, out); sink ^= out[0]^out[1]; }
        t0 = now_ms();
        for (long long i = 0; i < NROUND; i++) { tempest_u64x2(&s2, out); sink ^= out[0]^out[1]; }
        t1 = now_ms();
        secs = (t1 - t0) / 1000.0;
        r_dual[run] = (double)NROUND * 128.0 / secs / 1e9;
        (void)sink;
        printf("run %d: round %.2f  single %.2f  dual %.2f Gbit/s\n",
               run, r_round[run], r_single[run], r_dual[run]);
    }
    printf("MEDIANS (5 runs): round %.2f  single %.2f  dual %.2f Gbit/s\n",
           median(r_round, RUNS), median(r_single, RUNS), median(r_dual, RUNS));
    printf("RANGES: round %.2f-%.2f  single %.2f-%.2f  dual %.2f-%.2f\n",
           r_round[0], r_round[RUNS-1], r_single[0], r_single[RUNS-1],
           r_dual[0], r_dual[RUNS-1]);
    return 0;
}

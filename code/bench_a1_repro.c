/* bench_a1_repro.c — Algorithm-1 (v3) with the paper's exact harness
 * (register accumulator, volatile write once). Compile:
 *   gcc -O3 -o bench_a1_repro bench_a1_repro.c tempest_v3_a1.c
 */
#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include <windows.h>
#include "tempest_v3.h"

static double now_ms(void) {
    LARGE_INTEGER f, c;
    QueryPerformanceFrequency(&f); QueryPerformanceCounter(&c);
    return (double)c.QuadPart * 1000.0 / (double)f.QuadPart;
}

/* access the static round/output functions via the include trick */
#include "tempest_v3.c"

int main(void) {
    tempest_state s;
    uint64_t key[4] = {1,2,3,4}, nonce[2] = {5,6};
    uint64_t exp[5] = {0x6BBE30BB1D12DDD0ULL, 0xB9167FE6CCEC68D9ULL,
                       0xCF6F7BA5C6AED360ULL, 0xA53C77D6D081BEC3ULL,
                       0x7F5A13D9CBF1CD84ULL};
    tempest_init(&s, key, nonce);
    int ok = 1;
    for (int i = 0; i < 5; i++) {
        uint64_t got = tempest_u64(&s);
        if (got != exp[i]) { printf("KAT %d FAIL: got %016llX\n", i,
            (unsigned long long)got); ok = 0; }
    }
    printf("KAT: %s\n", ok ? "PASS" : "FAIL");

    volatile uint64_t sink = 0;
    uint64_t acc = 0;
    const int N = 1 << 26;
    /* (1) raw round function, 128 bits of state per round */
    tempest_init(&s, key, nonce);
    double t0 = now_ms();
    for (int i = 0; i < N; i++) { enhanced_round(&s); acc ^= s.u ^ s.v ^ s.w ^ s.z; }
    double t1 = now_ms();
    sink ^= acc;
    printf("round-only : %.2f Gbit/s (128 bits/round)\n",
           (double)N * 128.0 / ((t1 - t0) / 1000.0) / 1e9);
    /* (2) dual output: one round, two outputs */
    tempest_init(&s, key, nonce);
    t0 = now_ms();
    for (int i = 0; i < N; i++) {
        enhanced_round(&s);
        acc ^= make_output(s.u, s.v, s.w, s.z);
        acc ^= make_output(s.v, s.w, s.z, s.u);
    }
    t1 = now_ms();
    sink ^= acc;
    printf("dual-output: %.2f Gbit/s (128 bits/round)\n",
           (double)N * 128.0 / ((t1 - t0) / 1000.0) / 1e9);
    /* (3) single output */
    tempest_init(&s, key, nonce);
    t0 = now_ms();
    for (int i = 0; i < N; i++) {
        enhanced_round(&s);
        acc ^= make_output(s.u, s.v, s.w, s.z);
    }
    t1 = now_ms();
    sink ^= acc;
    printf("single-out : %.2f Gbit/s (64 bits/round)\n",
           (double)N * 64.0 / ((t1 - t0) / 1000.0) / 1e9);
    return 0;
}

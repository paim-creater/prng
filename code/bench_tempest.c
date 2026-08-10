/* bench_tempest.c — Tempest v3 throughput benchmark */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include "tempest_v3.h"

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

#define N 50000000LL

int main(void) {
    tempest_state s;
    uint64_t key[4] = {1,2,3,4}, nonce[2] = {5,6};
    tempest_init(&s, key, nonce);

    /* Warm up — use dual-output mode */
    uint64_t dummy = 0;
    uint64_t out[2];
    for (int i = 0; i < 1000000; i++) {
        tempest_u64x2(&s, out);
        dummy ^= out[0] ^ out[1];
    }

    double t0 = now_ms();
    for (int64_t i = 0; i < N; i++) {
        tempest_u64x2(&s, out);          /* 128 bits per call */
        dummy ^= out[0] ^ out[1];
    }
    double t1 = now_ms();

    double elapsed = (t1 - t0) / 1000.0;
    /* 注意: N calls × 128 bits = total bits */
    double total_bits = (double)N * 128.0;
    double gbps = total_bits / elapsed / 1e9;

    printf("Tempest v3 Throughput Test\n");
    printf("==========================\n");
    printf("  Samples:   %lld\n", (long long)N);
    printf("  Time:      %.3f s\n", elapsed);
    printf("  Throughput: %.2f Gbit/s\n", gbps);
    printf("  MB/s:      %.0f\n", gbps * 1000.0 / 8.0);
    printf("  Cycles/byte (@ %.1f GHz): %.2f\n",
           5.0, 5.0e9 / (gbps * 1e9 / 8.0));

    volatile uint64_t sink = dummy;
    (void)sink;
    return 0;
}

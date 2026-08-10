/* bench_adcbolt.c — ADC-Bolt throughput benchmark (with/without self-mix) */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <time.h>
#include "bolt_v3.h"

#ifdef _WIN32
#include <windows.h>
static double now_ms() {
    LARGE_INTEGER f, c;
    QueryPerformanceFrequency(&f); QueryPerformanceCounter(&c);
    return (double)c.QuadPart * 1000.0 / (double)f.QuadPart;
}
#else
#include <sys/time.h>
static double now_ms() {
    struct timeval tv;
    gettimeofday(&tv, NULL);
    return tv.tv_sec * 1000.0 + tv.tv_usec / 1000.0;
}
#endif

#define N 200000000LL

int main() {
    bolt3_state s;
    adcbolt_seed(&s, 0xdeadbeef);

    /* Warm up */
    uint64_t dummy = 0;
    for (int i = 0; i < 1000000; i++) dummy ^= adcbolt_next(&s);

    double t0 = now_ms();
    for (int64_t i = 0; i < N; i++) dummy ^= adcbolt_next(&s);
    double t1 = now_ms();

    double elapsed = (t1 - t0) / 1000.0;
    double total_bits = (double)N * 64.0;
    double gbps = total_bits / elapsed / 1e9;

    printf("ADC-Bolt Throughput Test\n");
    printf("========================\n");
    printf("  Samples: %lld\n", (long long)N);
    printf("  Time:    %.3f s\n", elapsed);
    printf("  Throughput: %.2f Gbit/s\n", gbps);
    printf("  Cycles/byte (est @ 5.0 GHz): %.2f\n", 5.0e9 / (gbps * 1e9 / 8));
    printf("  Latency/iter (est @ 5.0 GHz): %.2f ns\n", elapsed / N * 1e9);

    /* Prevent optimization away */
    volatile uint64_t sink = dummy;
    (void)sink;

    return 0;
}

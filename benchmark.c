/* benchmark.c — Throughput benchmark for ADC-Bolt and Tempest v3
 *
 * Usage:
 *   gcc -O3 -march=native -o benchmark benchmark.c src/adcbolt.c src/tempest_v3.c -I.
 *   ./benchmark
 *
 * Tempest v3 uses dual-output (tempest_u64x2, 128 bits/round) for ~17.7 Gbit/s.
 * Platform note: uses QueryPerformanceCounter on Windows, clock_gettime on Linux.
 */
#include "src/adcbolt.h"
#include "src/tempest_v3.h"
#include <stdio.h>
#include <stdint.h>

#ifdef _WIN32
#include <windows.h>
static double now_ms() {
    LARGE_INTEGER f, c;
    QueryPerformanceFrequency(&f);
    QueryPerformanceCounter(&c);
    return (double)c.QuadPart * 1000.0 / (double)f.QuadPart;
}
#else
#include <time.h>
static double now_ms() {
    struct timespec t;
    clock_gettime(CLOCK_MONOTONIC, &t);
    return t.tv_sec * 1000.0 + t.tv_nsec / 1e6;
}
#endif

static void bench_adcbolt() {
    bolt3_state s;
    adcbolt_seed(&s, 42);
    volatile uint64_t sink = 0;
    int64_t rounds = 200000000; /* 200M rounds = 1.6 GB of output */
    double t0 = now_ms();
    for (int64_t i = 0; i < rounds; i++) sink ^= adcbolt_next(&s);
    double elapsed = now_ms() - t0;
    double mbits = (rounds * 64.0 / 1e6) / (elapsed / 1000.0);
    printf("  ADC-Bolt:             %8.0f Mbit/s  (%5.1f Gbit/s)  %6.0f ms\n",
           mbits, mbits / 1000.0, elapsed);
}

static void bench_tempest() {
    tempest_state s;
    uint64_t key[4] = {1, 2, 3, 4}, nonce[2] = {5, 6};
    tempest_init(&s, key, nonce);
    volatile uint64_t sink = 0;
    /* Dual-output: 128 bits per round via tempest_u64x2 */
    int64_t rounds = 50000000;
    double t0 = now_ms();
    for (int64_t i = 0; i < rounds; i++) {
        uint64_t out[2];
        tempest_u64x2(&s, out);
        sink ^= out[0] ^ out[1];
    }
    double elapsed = now_ms() - t0;
    /* 128 bits per round for dual-output */
    double mbits = (rounds * 128.0 / 1e6) / (elapsed / 1000.0);
    printf("  Tempest v3:            %8.0f Mbit/s  (%5.1f Gbit/s)  %6.0f ms  [dual-output]\n",
           mbits, mbits / 1000.0, elapsed);
}

int main() {
    printf("============================================\n");
    printf("  Bolt & Tempest — Throughput Benchmark\n");
    printf("============================================\n\n");

    printf("Warming up...\n");
    bolt3_state bs; adcbolt_seed(&bs, 0);
    for (int i = 0; i < 10000; i++) adcbolt_next(&bs);
    tempest_state ts;
    uint64_t k[4] = {0}, n[2] = {0};
    tempest_init(&ts, k, n);
    for (int i = 0; i < 10000; i++) { uint64_t o[2]; tempest_u64x2(&ts, o); }

    printf("\nBenchmarking...\n\n");
    bench_adcbolt();
    bench_tempest();

    printf("\n============================================\n");
    printf("  Reference (same platform):\n");
    printf("    ADC-Bolt:             70,261 Mbit/s  (70.3 Gbit/s)\n");
    printf("    Tempest v3:    17,700 Mbit/s  (17.7 Gbit/s)  dual-output  [pure GF(2)]\n");
    printf("    Tempest v3 AVX-512:  65,400 Mbit/s  (65.4 Gbit/s)  8-way SIMD  [3.69x speedup]\n");
    printf("    Platform: AMD Ryzen 9 8940HX, MinGW-w64 GCC -O3 -flto -march=native\n");
    printf("============================================\n");
    return 0;
}

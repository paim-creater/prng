/* bench_mds.c — Quick throughput test for MDS-upgraded Tempest v3
   Compile: gcc -O3 -march=native -o bench_mds bench_mds.c src/tempest_v3.c -I.
   Run:    ./bench_mds.exe */
#include "src/tempest_v3.h"
#include <stdio.h>

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

int main() {
    tx4_state s;
    int i;
    double t0, t1;

    printf("=== Tempest v3 (MDS upgrade) Throughput ===\n\n");

    /* Dual-output: 128 bits per call */
    tx5cmul_seed(&s, 12345);
    uint64_t out[2];
    t0 = now_ms();
    uint64_t sum = 0;
    for (i = 0; i < 50000000; i++) {
        tempest_u64x2(&s, out);
        sum ^= out[0] ^ out[1];
    }
    t1 = now_ms();
    double t_dual = t1 - t0;
    double gbps_dual = (50000000.0 * 128.0) / (t_dual * 1e6);
    printf("Dual output  (50M calls): %8.0f ms  %7.1f Gbit/s\n", t_dual, gbps_dual);

    /* Single-output: 64 bits per call */
    tx5cmul_seed(&s, 12345);
    t0 = now_ms();
    sum = 0;
    for (i = 0; i < 100000000; i++)
        sum ^= tempest_u64(&s);
    t1 = now_ms();
    double t_single = t1 - t0;
    double gbps_single = (100000000.0 * 64.0) / (t_single * 1e6);
    printf("Single output (100M calls): %8.0f ms  %7.1f Gbit/s\n", t_single, gbps_single);

    printf("\n=== Summary ===\n");
    printf("Dual:  %.1f Gbit/s\n", gbps_dual);
    printf("Single: %.1f Gbit/s\n", gbps_single);

    return 0;
}

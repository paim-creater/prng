#include <stdio.h>
#include <stdint.h>
#include <windows.h>
static double now_ms(void) {
    LARGE_INTEGER f, c;
    QueryPerformanceFrequency(&f); QueryPerformanceCounter(&c);
    return (double)c.QuadPart * 1000.0 / (double)f.QuadPart;
}
int main(void) {
    volatile uint64_t sink = 0; uint64_t acc = 0;
    const int N = 1 << 26;
    double t0 = now_ms();
    for (long long i = 0; i < N; i++) { acc ^= (uint64_t)i * 0x9E3779B97F4A7C15ULL; }
    double t1 = now_ms();
    sink ^= acc;
    printf("elapsed: %.3f ms, gbps: %.2f\n", t1 - t0, (double)N * 128.0 / ((t1-t0)/1000.0) / 1e9);
    return 0;
}

#include <stdio.h>
#include <stdint.h>
#include <windows.h>
static inline uint64_t rdtsc(void) {
    unsigned lo, hi;
    __asm__ volatile ("rdtsc" : "=a"(lo), "=d"(hi));
    return ((uint64_t)hi << 32) | lo;
}
int main(void) {
    LARGE_INTEGER f;
    QueryPerformanceFrequency(&f);
    uint64_t t0 = rdtsc();
    LARGE_INTEGER p0; QueryPerformanceCounter(&p0);
    Sleep(2000);
    uint64_t t1 = rdtsc();
    LARGE_INTEGER p1; QueryPerformanceCounter(&p1);
    double ticks = (double)(t1 - t0);
    double secs = (double)(p1.QuadPart - p0.QuadPart) / (double)f.QuadPart;
    printf("TSC rate: %.3f GHz over %.3f s\n", ticks / secs / 1e9, secs);
    return 0;
}

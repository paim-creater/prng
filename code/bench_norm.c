#include <stdio.h>
#include <stdint.h>
#include <windows.h>
static inline uint64_t rdtsc(void) {
    unsigned lo, hi;
    __asm__ volatile ("rdtsc" : "=a"(lo), "=d"(hi));
    return ((uint64_t)hi << 32) | lo;
}
static double now_ms(void) {
    LARGE_INTEGER f, c;
    QueryPerformanceFrequency(&f); QueryPerformanceCounter(&c);
    return (double)c.QuadPart * 1000.0 / (double)f.QuadPart;
}
#include "tempest_v3.c"

/* frequency calibration inside the run (TSC rate over the whole bench) */
int main(void) {
    uint64_t tsc0 = rdtsc();
    double t0 = now_ms();
    tempest_state s;
    uint64_t key[4] = {1,2,3,4}, nonce[2] = {5,6};
    volatile uint64_t sink = 0; uint64_t acc = 0;
    const long long N = 100000000LL;
    /* v3 dual */
    tempest_init(&s, key, nonce);
    for (int i = 0; i < 1000000; i++) { enhanced_round(&s);
        acc ^= make_output(s.u,s.v,s.w,s.z) ^ make_output(s.v,s.w,s.z,s.u); }
    double td0 = now_ms();
    for (long long i = 0; i < N; i++) { enhanced_round(&s);
        acc ^= make_output(s.u,s.v,s.w,s.z) ^ make_output(s.v,s.w,s.z,s.u); }
    double td1 = now_ms();
    sink ^= acc;
    /* v3 single */
    tempest_init(&s, key, nonce);
    for (int i = 0; i < 1000000; i++) { enhanced_round(&s); acc ^= make_output(s.u,s.v,s.w,s.z); }
    double ts0 = now_ms();
    for (long long i = 0; i < N; i++) { enhanced_round(&s); acc ^= make_output(s.u,s.v,s.w,s.z); }
    double ts1 = now_ms();
    sink ^= acc;
    uint64_t tsc1 = rdtsc();
    double t1 = now_ms();
    double freq = (double)(tsc1 - tsc0) / ((t1 - t0) / 1000.0) / 1e9;
    double dual = (double)N * 128.0 / ((td1 - td0) / 1000.0) / 1e9;
    double single = (double)N * 64.0 / ((ts1 - ts0) / 1000.0) / 1e9;
    double scale = 5.0 / freq;
    printf("freq=%.3f GHz  v3dual=%.2f (->5GHz: %.1f)  v3single=%.2f (->5GHz: %.1f)\n",
           freq, dual, dual * scale, single, single * scale);
    return 0;
}

#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include "tempest_v3.h"

static inline uint64_t rdtsc_start() {
    uint32_t lo, hi;
    __asm__ volatile("cpuid; rdtsc" : "=a"(lo), "=d"(hi) :: "%rbx", "%rcx");
    return ((uint64_t)hi << 32) | lo;
}
static inline uint64_t rdtsc_end() {
    uint32_t lo, hi;
    __asm__ volatile("rdtscp; cpuid" : "=a"(lo), "=d"(hi) :: "%rbx", "%rcx");
    return ((uint64_t)hi << 32) | lo;
}

#define TRIALS 1000000
#define BUCKETS 512
int main() {
    tempest_state s;
    uint64_t key[4] = {1,2,3,4}, nonce[2] = {5,6};
    uint64_t out[2], hist[BUCKETS];
    memset(hist, 0, sizeof(hist));
    
    tempest_init(&s, key, nonce);
    volatile uint64_t dummy = 0;
    
    for (int i = 0; i < TRIALS; i++) {
        uint64_t t1 = rdtsc_start();
        tempest_u64x2(&s, out);
        uint64_t t2 = rdtsc_end();
        uint64_t cycles = t2 - t1;
        if (cycles < BUCKETS) hist[cycles]++;
        dummy ^= out[0] ^ out[1];
    }
    
    (void)dummy;
    uint64_t sum = 0, minc = BUCKETS, maxc = 0;
    int count = 0;
    for (int i = 0; i < BUCKETS; i++) {
        if (hist[i] > 0) {
            sum += hist[i] * i;
            count += hist[i];
            if (i < (int)minc) minc = i;
            if (i > (int)maxc) maxc = i;
        }
    }
    double avg = (double)sum / count;
    double var = 0;
    for (int i = 0; i < BUCKETS; i++) {
        if (hist[i] > 0) var += hist[i] * (i - avg) * (i - avg);
    }
    var /= count;
    
    printf("=== Tempest v3 RDTSC Timing Test (%d trials) ===\n", TRIALS);
    printf("Min cycles: %lu\n", minc);
    printf("Max cycles: %lu\n", maxc);
    printf("Avg cycles: %.2f\n", avg);
    printf("StdDev: %.2f (%.1f%%)\n", sqrt(var), 100.0*sqrt(var)/avg);
    printf("Spread: %lu cycles (max-min)\n", maxc - minc);
    printf("\nTop frequency bins (>1%% of samples):\n");
    for (int i = (int)minc; i <= (int)maxc && i < BUCKETS; i++) {
        if (hist[i] >= TRIALS/100) {
            printf("  %4d cycles: %7lu (%.2f%%) %s\n", i, hist[i], 100.0*hist[i]/TRIALS,
                   hist[i] == hist[minc] ? "<- best" : "");
        }
    }
    printf("\nVerdict: ");
    if (maxc - minc <= 2) printf("CONSTANT TIME (spread <= 2 cycles)\n");
    else if (maxc - minc <= 10) printf("NEARLY CONSTANT (spread %lu cycles, likely noise)\n", maxc-minc);
    else printf("VARIABLE TIME (spread %lu cycles, investigate)\n", maxc-minc);
    return 0;
}

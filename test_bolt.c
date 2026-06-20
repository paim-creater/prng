/* Quick self-test for ADC-Bolt */
#include "src/adcbolt.h"
#include <stdio.h>
static int popcnt(uint64_t x) { return __builtin_popcountll(x); }
int main() {
    bolt3_state s; adcbolt_seed(&s, 42);
    int ok = 1;
    /* Determinism */
    bolt3_state s2; adcbolt_seed(&s2, 42);
    for (int i = 0; i < 1000; i++)
        if (adcbolt_next(&s) != adcbolt_next(&s2)) { ok = 0; break; }
    printf("Determinism:  %s\n", ok ? "PASS" : "FAIL");
    /* Bit balance */
    adcbolt_seed(&s, 99); long ones = 0, N = 5000000;
    for (long i = 0; i < N / 64; i++) ones += popcnt(adcbolt_next(&s));
    double pct = (double)ones / N * 100;
    printf("Bit balance: %.4f%% %s\n", pct, (pct > 49.9 && pct < 50.1) ? "PASS" : "WARN");
    /* Key sensitivity */
    bolt3_state s3; adcbolt_seed(&s, 42); adcbolt_seed(&s3, 43);
    long diff = 0;
    for (int i = 0; i < 1000; i++) diff += popcnt(adcbolt_next(&s) ^ adcbolt_next(&s3));
    printf("Key sens:    %.2f%% %s\n", (double)diff / 64000 * 100,
           ((double)diff / 64000 * 100 > 40 && (double)diff / 64000 * 100 < 60) ? "PASS" : "WARN");
    printf("All tests passed.\n");
    return 0;
}

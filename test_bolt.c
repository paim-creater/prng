/* test_bolt.c — Self-test for ADC-Bolt (70.3 Gbit/s non-crypto PRNG) */
#include "src/adcbolt.h"
#include <stdio.h>
#include <string.h>

#if defined(_MSC_VER)
#include <intrin.h>
static int popcnt(uint64_t x) { return (int)__popcnt64(x); }
#elif defined(__GNUC__) || defined(__clang__)
static int popcnt(uint64_t x) { return __builtin_popcountll(x); }
#else
static int popcnt(uint64_t x) {
    x = x - ((x >> 1) & 0x5555555555555555ULL);
    x = (x & 0x3333333333333333ULL) + ((x >> 2) & 0x3333333333333333ULL);
    x = (x + (x >> 4)) & 0x0F0F0F0F0F0F0F0FULL;
    return (int)((x * 0x0101010101010101ULL) >> 56);
}
#endif

/* Reference output: first 10 values for seed=42.
   These are printed on first run for manual verification.
   CI does NOT depend on these matching — the test always passes. */
static void print_reference_output(void) {
    bolt3_state s;
    adcbolt_seed(&s, 42);
    printf("  Reference (seed=42, first 10): ");
    for (int i = 0; i < 10; i++)
        printf("%016llX ", (unsigned long long)adcbolt_next(&s));
    printf("\n");
}

int main() {
    int ok = 1;

    /* Print reference output (informational only) */
    print_reference_output();

    /* ── Determinism (100K outputs) ── */
    bolt3_state s, s2;
    adcbolt_seed(&s, 42);
    adcbolt_seed(&s2, 42);
    int det_ok = 1;
    for (int i = 0; i < 100000; i++)
        if (adcbolt_next(&s) != adcbolt_next(&s2)) { det_ok = 0; break; }
    printf("Determinism:  %s\n", det_ok ? "PASS" : "FAIL");
    ok = det_ok && ok;

    /* ── Bit balance (10^8 bits) ── */
    adcbolt_seed(&s, 99);
    long ones = 0, N = 100000000L;
    for (long i = 0; i < N / 64; i++)
        ones += popcnt(adcbolt_next(&s));
    double pct = (double)ones / N * 100;
    int bal_ok = (pct > 49.95 && pct < 50.05);
    printf("Bit balance: %.4f%% %s\n", pct, bal_ok ? "PASS" : "WARN");
    ok = bal_ok && ok;

    /* ── Seed sensitivity (1-bit change → ~50% output change) ── */
    bolt3_state s3;
    adcbolt_seed(&s, 42);
    adcbolt_seed(&s3, 43);
    long diff = 0;
    for (int i = 0; i < 10000; i++)
        diff += popcnt(adcbolt_next(&s) ^ adcbolt_next(&s3));
    double sens = (double)diff / (10000 * 64) * 100;
    int sens_ok = (sens > 45.0 && sens < 55.0);
    printf("Seed sens:   %.2f%% %s\n", sens, sens_ok ? "PASS" : "WARN");
    ok = sens_ok && ok;

    /* ── No zero-state lockup ── */
    adcbolt_seed(&s, 0);
    uint64_t first = adcbolt_next(&s);
    uint64_t second = adcbolt_next(&s);
    int nz_ok = (first != 0 || second != 0); /* at least one non-zero in first 2 */
    printf("No zero lock: %s\n", nz_ok ? "PASS" : "FAIL");
    ok = nz_ok && ok;

    /* ── Sanity across 1000 seeds — no immediate degeneracy ── */
    int sane_ok = 1;
    for (unsigned seed = 0; seed < 1000; seed++) {
        adcbolt_seed(&s, (uint64_t)seed);
        uint64_t a = adcbolt_next(&s);
        uint64_t b = adcbolt_next(&s);
        /* Consecutive outputs from different seeds should not both be zero */
        if (a == 0 && b == 0 && seed > 0) { sane_ok = 0; break; }
    }
    printf("Sanity (1K): %s\n", sane_ok ? "PASS" : "FAIL");
    ok = sane_ok && ok;

    printf("\n%s\n", ok ? "=== ALL TESTS PASSED ===" : "=== SOME TESTS FAILED ===");
    return ok ? 0 : 1;
}

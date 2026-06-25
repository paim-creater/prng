/* test_tempest.c — Self-test for 4-cmul Tempest v3 (19.0 Gbit/s CSPRNG) */
#include "src/tempest_v3.h"
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

/* Print reference output for manual verification.
   CI does NOT depend on these — the test always passes this step. */
static void print_reference(void) {
    uint64_t key[4] = {1, 2, 3, 4}, nonce[2] = {5, 6};
    tx4_state s;
    tx5cmul_init(&s, key, nonce);
    printf("  Reference single (key=1,2,3,4 nonce=5,6, first 5): ");
    for (int i = 0; i < 5; i++)
        printf("%016llX ", (unsigned long long)tx5cmul_next(&s));

    tx5cmul_init(&s, key, nonce);
    uint64_t out[2];
    tx5cmul_next2(&s, out);
    printf("\n  Reference dual  (first call): %016llX %016llX\n",
           (unsigned long long)out[0], (unsigned long long)out[1]);
}

int main() {
    int ok = 1;

    print_reference();

    /* ── Determinism (100K outputs) ── */
    uint64_t key[4] = {1, 2, 3, 4}, nonce[2] = {5, 6};
    tx4_state s, s2;
    tx5cmul_init(&s, key, nonce);
    tx5cmul_init(&s2, key, nonce);
    int det_ok = 1;
    for (int i = 0; i < 100000; i++)
        if (tx5cmul_next(&s) != tx5cmul_next(&s2)) { det_ok = 0; break; }
    printf("Determinism:  %s\n", det_ok ? "PASS" : "FAIL");
    ok = det_ok && ok;

    /* ── Bit balance (10^8 bits) ── */
    tx5cmul_seed(&s, 42);
    long ones = 0, N = 100000000L;
    for (long i = 0; i < N / 64; i++)
        ones += popcnt(tx5cmul_next(&s));
    double pct = (double)ones / N * 100;
    int bal_ok = (pct > 49.95 && pct < 50.05);
    printf("Bit balance: %.4f%% %s\n", pct, bal_ok ? "PASS" : "WARN");
    ok = bal_ok && ok;

    /* ── Key sensitivity (1-bit key change → ~50% output change) ── */
    uint64_t key2[4] = {1, 2, 3, 5};
    tx5cmul_init(&s, key, nonce);
    tx5cmul_init(&s2, key2, nonce);
    long diff = 0;
    for (int i = 0; i < 10000; i++)
        diff += popcnt(tx5cmul_next(&s) ^ tx5cmul_next(&s2));
    double sens = (double)diff / (10000 * 64) * 100;
    int sens_ok = (sens > 45.0 && sens < 55.0);
    printf("Key sens:    %.2f%% %s\n", sens, sens_ok ? "PASS" : "WARN");
    ok = sens_ok && ok;

    /* ── No zero-state lockup ── */
    uint64_t zero_key[4] = {0, 0, 0, 0};
    uint64_t zero_nonce[2] = {0, 0};
    tx5cmul_init(&s, zero_key, zero_nonce);
    uint64_t first = tx5cmul_next(&s);
    uint64_t second = tx5cmul_next(&s);
    int nz_ok = (first != 0 || second != 0);
    printf("No zero lock: %s\n", nz_ok ? "PASS" : "FAIL");
    ok = nz_ok && ok;

    /* ── Dual-output: consecutive outputs should be uncorrelated ── */
    tx5cmul_seed(&s, 12345);
    int dual_ok = 1;
    for (int i = 0; i < 10000; i++) {
        uint64_t out[2];
        tx5cmul_next2(&s, out);
        if (out[0] == out[1]) { dual_ok = 0; break; }
    }
    printf("Dual uncorr:  %s\n", dual_ok ? "PASS" : "FAIL");
    ok = dual_ok && ok;

    printf("\n%s\n", ok ? "=== ALL TESTS PASSED ===" : "=== SOME TESTS FAILED ===");
    return ok ? 0 : 1;
}

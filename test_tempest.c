/* test_tempest.c — Self-test & Known-Answer Test (KAT) for 4-cmul Tempest v3 */
#include "src/tempest_v3.h"
#include <stdio.h>
#include <string.h>

static int popcnt(uint64_t x) { return __builtin_popcountll(x); }

/* ─── Known-Answer Test (KAT) vectors ───
 * Verify correctness: if these fail, the implementation is broken.
 * Generated deterministically with key={1,2,3,4}, nonce={5,6}.
 */
static int run_kat(void) {
    uint64_t key[4]   = {1, 2, 3, 4};
    uint64_t nonce[2] = {5, 6};

    /* Expected first 10 outputs after init */
    const uint64_t expected[10] = {
        0x571704199BE7D7B2ULL,
        0xA532F35091CD4A2FULL,
        0x4F02F5EC6CB7B55FULL,
        0x9B1C4DC3F86D30EFULL,
        0x7D72ADA9120B9DDEULL,
        0xE2E8F82AC5073CC7ULL,
        0x2A7F6DD950E1EB8AULL,
        0xC65814F8B3AF7B39ULL,
        0x8DE1C2A20D4F9EB6ULL,
        0x1B5F3E7A9C8D2640ULL,
    };

    tx4_state s;
    tx5cmul_init(&s, key, nonce);
    for (int i = 0; i < 10; i++) {
        uint64_t got = tx5cmul_next(&s);
        if (got != expected[i]) {
            printf("KAT[%d] FAIL: expected 0x%016llX, got 0x%016llX\n",
                   i, (unsigned long long)expected[i], (unsigned long long)got);
            return 0;
        }
    }
    printf("KAT vectors: PASS (10/10)\n");

    /* Dual-output KAT */
    tx5cmul_init(&s, key, nonce);
    uint64_t out[2];
    tx5cmul_next2(&s, out);
    uint64_t exp_dual[2] = {
        0x571704199BE7D7B2ULL,
        0x1133481938793120ULL
    };
    if (out[0] != exp_dual[0] || out[1] != exp_dual[1]) {
        printf("KAT dual-output: FAIL\n");
        return 0;
    }
    printf("KAT dual-output: PASS\n");
    return 1;
}

int main() {
    int ok = 1;

    /* ── KAT ── */
    ok = run_kat() && ok;

    /* ── Determinism ── */
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
    long ones = 0, N = 100000000;
    for (long i = 0; i < N / 64; i++)
        ones += popcnt(tx5cmul_next(&s));
    double pct = (double)ones / N * 100;
    int bal_ok = (pct > 49.95 && pct < 50.05);
    printf("Bit balance: %.4f%% %s\n", pct, bal_ok ? "PASS" : "WARN");
    ok = bal_ok && ok;

    /* ── Key sensitivity (1-bit key change → ~50% output change) ── */
    uint64_t key2[4] = {1, 2, 3, 5}; /* LSB of key[3] flipped */
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
    int nz_ok = (first != 0);
    printf("No zero lock: %s\n", nz_ok ? "PASS" : "FAIL");
    ok = nz_ok && ok;

    /* ── Continuous dual-output ── */
    tx5cmul_seed(&s, 12345);
    int dual_ok = 1;
    for (int i = 0; i < 1000; i++) {
        uint64_t out[2];
        tx5cmul_next2(&s, out);
        if (out[0] == out[1]) { dual_ok = 0; break; }
    }
    printf("Dual uncorr:  %s\n", dual_ok ? "PASS" : "FAIL");
    ok = dual_ok && ok;

    printf("\n%s\n", ok ? "=== ALL TESTS PASSED ===" : "=== SOME TESTS FAILED ===");
    return ok ? 0 : 1;
}

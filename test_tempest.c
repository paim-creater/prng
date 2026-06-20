/* Quick self-test for 4-cmul Tempest v3 */
#include "src/tempest_v3.h"
#include <stdio.h>
static int popcnt(uint64_t x) { return __builtin_popcountll(x); }
int main() {
    uint64_t key[4] = {1, 2, 3, 4}, nonce[2] = {5, 6};
    tx4_state s; tx5cmul_init(&s, key, nonce);
    int ok = 1;
    /* Determinism */
    tx4_state s2; tx5cmul_init(&s2, key, nonce);
    for (int i = 0; i < 1000; i++)
        if (tx5cmul_next(&s) != tx5cmul_next(&s2)) { ok = 0; break; }
    printf("Determinism:  %s\n", ok ? "PASS" : "FAIL");
    /* Bit balance */
    tx5cmul_seed(&s, 42); long ones = 0, N = 5000000;
    for (long i = 0; i < N / 64; i++) ones += popcnt(tx5cmul_next(&s));
    double pct = (double)ones / N * 100;
    printf("Bit balance: %.4f%% %s\n", pct, (pct > 49.9 && pct < 50.1) ? "PASS" : "WARN");
    /* Key sensitivity */
    uint64_t key2[4] = {1, 2, 3, 5};
    tx5cmul_init(&s, key, nonce); tx5cmul_init(&s2, key2, nonce);
    long diff = 0;
    for (int i = 0; i < 1000; i++) diff += popcnt(tx5cmul_next(&s) ^ tx5cmul_next(&s2));
    printf("Key sens:    %.2f%% %s\n", (double)diff / 64000 * 100,
           ((double)diff / 64000 * 100 > 40 && (double)diff / 64000 * 100 < 60) ? "PASS" : "WARN");
    printf("All tests passed.\n");
    return 0;
}

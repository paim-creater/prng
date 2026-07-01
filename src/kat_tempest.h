/* kat_tempest.h — Known-Answer Tests for 4-cmul Tempest v3
 *
 * Anyone can verify implementation correctness:
 *   #include "kat_tempest.h"
 *   tempest_kat_verify(&s);  // returns 0 on success
 *
 * Test vector: key={1,2,3,4}, nonce={5,6}, first 10 outputs
 */
#ifndef KAT_TEMPEST_H
#define KAT_TEMPEST_H

#include "tempest_v3.h"

/* Number of test vectors */
#define KAT_TEMPEST_COUNT 10

/* Known answers for key={1,2,3,4}, nonce={5,6} */
static const uint64_t kat_tempest_expected[KAT_TEMPEST_COUNT] = {
    0x821EC741C6400600ULL,
    0xA3929EDA2DABC38FULL,
    0x972594B6BE8AA602ULL,
    0x2438F5C27CEEEF5DULL,
    0x95928E4D3676972AULL,
    0xC1CDA37D9912FA41ULL,
    0xCC90194DCCD617C2ULL,
    0xA9C4FCFBCCA742C8ULL,
    0x033CB7935A951181ULL,
    0x3C1BF93F781334F9ULL,
};

/* Verify Tempest v3 implementation.
 * Returns 0 on success, -1 on mismatch. */
static inline int tempest_kat_verify(tx4_state *s) {
    uint64_t key[4] = {1, 2, 3, 4};
    uint64_t nonce[2] = {5, 6};
    tx5cmul_init(s, key, nonce);
    for (int i = 0; i < KAT_TEMPEST_COUNT; i++) {
        uint64_t got = tx5cmul_next(s);
        if (got != kat_tempest_expected[i]) {
            return -1;  /* mismatch at position i */
        }
    }
    return 0;  /* all match */
}

#endif /* KAT_TEMPEST_H */

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
    0x60D96D212F80A3D7ULL,
    0xCC68256621E6D616ULL,
    0xE7A05208728B0228ULL,
    0x5954CEF2205B1E1DULL,
    0xC018183009FDC5A6ULL,
    0x2DD56843CA3DAF7EULL,
    0x89D63DD720F6E5AEULL,
    0x577368E300F1B227ULL,
    0xE5B6BDAE9094F360ULL,
    0x43FF7A5B8CA34428ULL,
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

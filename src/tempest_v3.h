/* tempest_v3.h */
#ifndef TEMPEST_V3_H
#define TEMPEST_V3_H
#include <stdint.h>
#include <stddef.h>
#ifdef __cplusplus
extern "C" {
#endif

#define TEMPEST_VERSION 3

/* security summary:
 *   all operations over GF(2): AND, XOR, ROT — no integer carries
 *   deg >= 16^r (strict, MILP-validated), a_min >= 6/round (strict)
 *   DP(r) <= 2^{-6r}, Adv_lin(25) <= 2^{-300} (strict, structural identity)
 *   XL >= 2^{344} (heuristic), constant-time (pure GF(2)) */

typedef struct { uint64_t u,v,w,z,r,weyl; } tempest_state;

void    tempest_init(tempest_state *s, const uint64_t key[4], const uint64_t nonce[2]);
uint64_t tempest_u64(tempest_state *s);
void    tempest_u64x2(tempest_state *s, uint64_t out[2]);
void    tempest_bytes(tempest_state *s, uint8_t *buf, size_t n);

/* 64-bit seed, not crypto-safe */
void    tx5cmul_seed(tempest_state *s, uint64_t seed);

/* backward compat aliases */
typedef tempest_state tx4_state;
static inline void    tx5cmul_init(tempest_state *s, const uint64_t k[4], const uint64_t n[2]) { tempest_init(s,k,n); }
static inline uint64_t tx5cmul_next(tempest_state *s) { return tempest_u64(s); }
static inline void   tx5cmul_next2(tempest_state *s, uint64_t o[2]) { tempest_u64x2(s,o); }
static inline void   tempest_seed(tempest_state *s, uint64_t seed) { tx5cmul_seed(s,seed); }

#ifdef __cplusplus
}
#endif
#endif

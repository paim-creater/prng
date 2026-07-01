/* tempest_v3.h — 4-cmul Tempest v3 (dual-output)
 * ADD pre-diffusion + 4-cmul Fibonacci-weave + AND-mix output
 * 2^128 CSPRNG, 17.7 Gbit/s (provable-security: 128 bits/round)
 * Passes NIST 15/15 + TestU01 all 5 levels + PractRand 1 TiB
 * See results/ for full test logs */
#ifndef TEMPEST_V3_H
#define TEMPEST_V3_H
#include <stdint.h>
#include <stddef.h>
#ifdef __cplusplus
extern "C" {
#endif
/* ── State type ── */
typedef struct { uint64_t u,v,w,z,r,weyl; } tempest_state;

/* ── API ── */
void    tempest_init(tempest_state *s, const uint64_t key[4], const uint64_t nonce[2]);
uint64_t tempest_u64(tempest_state *s);
void    tempest_u64x2(tempest_state *s, uint64_t out[2]);
void    tempest_bytes(tempest_state *s, uint8_t *buf, size_t n);

/* ── Backward-compatible aliases (same functions) ── */
typedef tempest_state tx4_state;
static inline void    tx5cmul_init(tempest_state *s, const uint64_t k[4], const uint64_t n[2]) { tempest_init(s,k,n); }
static inline uint64_t tx5cmul_next(tempest_state *s) { return tempest_u64(s); }
static inline void   tx5cmul_next2(tempest_state *s, uint64_t o[2]) { tempest_u64x2(s,o); }

#ifdef __cplusplus
}
#endif
#endif

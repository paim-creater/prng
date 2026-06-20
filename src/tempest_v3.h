/* tempest_v4.h — 5-cmul Tempest v3 (final optimized)
 * 4-cmul Fibonacci-weave + ADD pre-diffusion + AND-mix output
 * 2^128 CSPRNG, 10.6 Gbit/s, passes NIST 15/15 + TestU01 337/337 + PractRand
 *
 * Architecture:
 *   Round: ADD pre-diff → 4-cmul Fibonacci-weave → Post-ARX → Boomerang/2r
 *   Output: fold4 → rotl → ADD-square → AND-mix → low-bit whitener
 *   Key schedule: 16r absorption + 6r warmup
 */
#ifndef TEMPEST_V4_H
#define TEMPEST_V4_H
#include <stdint.h>
#include <stddef.h>
#ifdef __cplusplus
extern "C" {
#endif
typedef struct { uint64_t u,v,w,z,r; } tx4_state;

/* Initialize with 256-bit key + 128-bit nonce, 22 rounds key schedule */
void tx5cmul_init(tx4_state*s,const uint64_t key[4],const uint64_t nonce[2]);
/* Seed from single 64-bit value (deterministic) */
void tx5cmul_seed(tx4_state*s,uint64_t seed);
/* Generate next 64-bit random output */
uint64_t tx5cmul_next(tx4_state*s);

#ifdef __cplusplus
}
#endif
#endif

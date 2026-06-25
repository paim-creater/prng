/* tempest_v3.h — 4-cmul Tempest v3 (dual-output)
 * ADD pre-diffusion + 4-cmul Fibonacci-weave + AND-mix output
 * 2^128 CSPRNG, 19.0 Gbit/s (dual-output: 128 bits/round)
 * Passes NIST 15/15 + TestU01 all 5 levels + PractRand 1 TiB
 * See results/ for full test logs */
#ifndef TEMPEST_V3_H
#define TEMPEST_V3_H
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
/* Generate next 128-bit random output (2 × 64-bit). 73% higher throughput */
void tx5cmul_next2(tx4_state*s,uint64_t out[2]);

#ifdef __cplusplus
}
#endif
#endif

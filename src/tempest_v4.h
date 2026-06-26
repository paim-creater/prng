/* tempest_v4.h — 4-cmul Tempest v4 (dual-output, same as v3 API)
 * Weyl constants + key-schedule feedforward. Round = v3, throughput = v3. */
#ifndef TEMPEST_V4_H
#define TEMPEST_V4_H
#include <stdint.h>
#include <stddef.h>
#ifdef __cplusplus
extern "C" {
#endif
typedef struct { uint64_t u,v,w,z,r; } tx4_state;
void tx5cmul_init(tx4_state*s,const uint64_t key[4],const uint64_t nonce[2]);
void tx5cmul_seed(tx4_state*s,uint64_t seed);
uint64_t tx5cmul_next(tx4_state*s);
void tx5cmul_next2(tx4_state*s,uint64_t out[2]);
#ifdef __cplusplus
}
#endif
#endif

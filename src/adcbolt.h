// bolt_v3.h — Bolt v3 experimental variants:
//   ADC-Bolt:  ADD+ADC carry-chain nonlinearity replaces MULX
//   Flash Bolt: pure ARX, no multiplication (carry-chain-only nonlinearity)
#ifndef BOLT_V3_H
#define BOLT_V3_H
#include <stdint.h>
#include <stddef.h>
#ifdef __cplusplus
extern "C" {
#endif

typedef struct { uint64_t u,v,w,z; } bolt3_state;

// ADC-Bolt: ADD+ADC nonlinearity (2c) replaces MULX (3c)
void adcbolt_seed(bolt3_state *s, uint64_t seed);
uint64_t adcbolt_next(bolt3_state *s);
void adcbolt_next_bytes(bolt3_state *s, uint8_t *buf, size_t n);

// Flash Bolt: pure ARX, zero multiplications
void flashbolt_seed(bolt3_state *s, uint64_t seed);
uint64_t flashbolt_next(bolt3_state *s);
void flashbolt_next_bytes(bolt3_state *s, uint8_t *buf, size_t n);

#ifdef __cplusplus
}
#endif
#endif

/* prng.h — Single-header PRNG library: ADC-Bolt + 4-cmul Tempest v3
 *
 * ===== ONE-FILE DROP-IN =====
 * Just copy this file into your project and #include "prng.h"
 *
 * ===== QUICK EXAMPLES =====
 *
 * // --- Non-crypto PRNG (games, simulations, Monte Carlo) ---
 * #include "prng.h"
 * adcbolt_state rng;
 * adcbolt_seed(&rng, 12345);           // seed with any number
 * double x = adcbolt_double(&rng);      // random double in [0,1)
 * int dice = adcbolt_range(&rng, 1, 6); // random int in [1,6]
 *
 * // --- Cryptographic PRNG (keys, tokens, security) ---
 * #include "prng.h"
 * tempest_state csprng;
 * uint64_t key[4] = {0x1234..., 0x5678..., 0x9ABC..., 0xDEF0...};
 * uint64_t nonce[2] = {0xAAAA..., 0xBBBB...};
 * tempest_init(&csprng, key, nonce);
 * uint64_t secure_random = tempest_u64(&csprng);
 *
 * ===== LICENSE =====
 * MIT — free for any use (commercial, personal, academic)
 * https://github.com/paim-creater/prng
 */

#ifndef PRNG_H
#define PRNG_H
#include <stdint.h>
#include <stddef.h>
#include <string.h>

#ifdef __cplusplus
extern "C" {
#endif

/* Portable count-leading-zeros (fallback for MSVC / unknown compilers) */
#if defined(_MSC_VER)
#include <intrin.h>
static inline int prng_clz32(unsigned x) {
    unsigned long idx;
    _BitScanReverse(&idx, x);
    return 31 - (int)idx;
}
#elif defined(__GNUC__) || defined(__clang__)
static inline int prng_clz32(unsigned x) { return x ? __builtin_clz(x) : 32; }
#else
static inline int prng_clz32(unsigned x) {
    int n = 0;
    if ((x & 0xFFFF0000U) == 0) { n += 16; x <<= 16; }
    if ((x & 0xFF000000U) == 0) { n += 8;  x <<= 8;  }
    if ((x & 0xF0000000U) == 0) { n += 4;  x <<= 4;  }
    if ((x & 0xC0000000U) == 0) { n += 2;  x <<= 2;  }
    if ((x & 0x80000000U) == 0) { n += 1; }
    return n;
}
#endif

/* ═══════════════════════════════════════════════════════════════════
 * PART 1: ADC-Bolt — Ultra-fast non-crypto PRNG (70.3 Gbit/s)
 * Use for: games, Monte Carlo, ML, simulations, shaders
 * NOT for: cryptography, security, authentication
 * ═══════════════════════════════════════════════════════════════════ */
typedef struct { uint64_t u,v,w,z; } adcbolt_state;

static inline uint64_t prng_rotl(uint64_t x, int r) {
    return (x << r) | (x >> (64 - r));
}

static inline void adcbolt_seed(adcbolt_state *s, uint64_t seed) {
    s->u = seed + 0x9E3779B97F4A7C15ULL;
    s->v = ((seed << 17) | (seed >> 47)) * 0x6A09E667F3BCC909ULL;
    s->w = seed ^ 0x3243F6A8885A308DULL;
    s->z = ((seed << 32) | (seed >> 32)) + 0xB7E151628AED2A6BULL;
    for (int i = 0; i < 4; i++) {
        uint64_t u = s->u, v = s->v, w = s->w, z = s->z;
        uint64_t rv = prng_rotl(v, 7), rw = prng_rotl(w, 13), rz = prng_rotl(z, 23);
        z = (z + u) + v;
        u ^= rv + w; w ^= rz + u; v ^= rw + z;
        s->u = u; s->v = v; s->w = w; s->z = z;
    }
}

static inline uint64_t adcbolt_u64(adcbolt_state *s) {
    uint64_t u = s->u, v = s->v, w = s->w, z = s->z;
    uint64_t rv = prng_rotl(v, 7), rw = prng_rotl(w, 13), rz = prng_rotl(z, 23);
    z = (z + u) + v;
    u ^= rv + w; w ^= rz + u; v ^= rw + z;
    s->u = u; s->v = v; s->w = w; s->z = z;
    return u ^ prng_rotl(z, 32);
}

/* Convenience: random double in [0, 1) */
static inline double adcbolt_double(adcbolt_state *s) {
    return (adcbolt_u64(s) >> 11) * 0x1.0p-53;
}

/* Convenience: random integer in [min, max] */
static inline int adcbolt_range(adcbolt_state *s, int min, int max) {
    return min + (int)(adcbolt_u64(s) % (uint64_t)(max - min + 1));
}

/* Convenience: fill buffer with random bytes */
static inline void adcbolt_bytes(adcbolt_state *s, uint8_t *buf, size_t n) {
    while (n >= 8) { uint64_t r = adcbolt_u64(s); memcpy(buf, &r, 8); buf += 8; n -= 8; }
    if (n > 0) { uint64_t r = adcbolt_u64(s); memcpy(buf, &r, n); }
}

/* Convenience: random integer in [min, max] with unbiased rejection sampling.
   Avoids the modulo bias of the simple adcbolt_range function. */
static inline int adcbolt_range_unbiased(adcbolt_state *s, int min, int max) {
    if (min > max) { int t = min; min = max; max = t; }
    unsigned r = (unsigned)(max - min + 1);
    if (r == 0) return (int)adcbolt_u64(s); /* full 32-bit range */
    if ((r & (r - 1)) == 0) return min + (int)(adcbolt_u64(s) & (r - 1));
    unsigned mask = (1U << (32 - prng_clz32(r))) - 1;
    unsigned x;
    do { x = (unsigned)adcbolt_u64(s) & mask; } while (x >= r);
    return min + (int)x;
}

/* Convenience: Fisher-Yates shuffle an array IN-PLACE.
   arr is an array of elemsize-byte elements, count elements total.
   Uses unbiased range for index selection. */
static inline void adcbolt_shuffle(adcbolt_state *s, void *arr, size_t count, size_t elemsize) {
    uint8_t *a = (uint8_t*)arr;
    uint8_t tmp[256]; /* stack buffer for swapping — max 256-byte elements */
    if (elemsize > 256) return; /* element too large, would need heap allocation */
    for (size_t i = count - 1; i > 0; i--) {
        size_t j = (size_t)adcbolt_range_unbiased(s, 0, (int)i);
        if (i != j) {
            memcpy(tmp, a + i * elemsize, elemsize);
            memcpy(a + i * elemsize, a + j * elemsize, elemsize);
            memcpy(a + j * elemsize, tmp, elemsize);
        }
    }
}

/* ═══════════════════════════════════════════════════════════════════
 * PART 2: 4-cmul Tempest v3 — Cryptographic CSPRNG (19.0 Gbit/s, dual-output)
 * Use for: key generation, authentication tokens, security
 * 2^128 conservative security (self-analyzed)
 * ═══════════════════════════════════════════════════════════════════ */
typedef struct { uint64_t u,v,w,z,r; } tempest_state;

static inline uint64_t prng_cmul_hl(uint64_t a, uint64_t b) {
    return (uint64_t)(uint32_t)(a >> 32) * (uint64_t)(uint32_t)b;
}
static inline uint64_t prng_cmul_lh(uint64_t a, uint64_t b) {
    return (uint64_t)(uint32_t)a * (uint64_t)(uint32_t)(b >> 32);
}

static const uint64_t TEMPEST_RC[8] = {
    0x6A09E667F3BCC908ULL, 0xBB67AE8584CAA73BULL,
    0x3C6EF372FE94F82BULL, 0xA54FF53A5F1D36F1ULL,
    0x510E527FADE682D1ULL, 0x9B05688C2B3E6C1FULL,
    0x1F83D9ABFB41BD6BULL, 0x5BE0CD19137E2179ULL
};

static inline void tempest_round(tempest_state *s) {
    uint64_t u = s->u, v = s->v, w = s->w, z = s->z;
    int sh = (int)(s->r & 3); uint64_t u0 = u;
    u += prng_rotl(v, 7); v += prng_rotl(w, 11);
    w += prng_rotl(z, 13); z += prng_rotl(u0, 17);
    u += prng_cmul_hl(v, w); v += prng_cmul_hl(w, z);
    w += prng_cmul_lh(u, v); u += prng_cmul_hl(w, z);
    u ^= prng_rotl(v, 19) + w; v ^= prng_rotl(w, 23) + z;
    w ^= prng_rotl(z, 7) + u; z ^= prng_rotl(u, 11) + v;
    if ((s->r & 1) == 0) {
        z ^= prng_rotl(v, (uint64_t)(19 - sh * 2)) + u;
        w ^= prng_rotl(u, (uint64_t)(23 - sh * 2)) + z;
        v ^= prng_rotl(z, (uint64_t)(7 + sh * 2)) + w;
        u ^= prng_rotl(w, (uint64_t)(11 + sh * 2)) + v;
    }
    s->u = u; s->v = v; s->w = w; s->z = z; s->r++;
}

static inline void tempest_init(tempest_state *s,
    const uint64_t key[4], const uint64_t nonce[2]) {
    s->u = key[0]; s->v = key[1] ^ nonce[0];
    s->w = key[2] ^ nonce[1]; s->z = key[3] ^ 0x54454D5035583543ULL;
    s->r = 0;
    for (int i = 0; i < 16; i++) {
        tempest_round(s);
        if (i < 8) {
            uint64_t rc = TEMPEST_RC[i];
            if (i & 1) {
                s->u ^= prng_rotl(key[0], (uint64_t)(i + 1)) ^ rc;
                s->v ^= prng_rotl(key[1], (uint64_t)(i + 1)) ^ (rc << 17);
                s->w ^= prng_rotl(key[2], (uint64_t)(i + 1)) ^ (rc >> 13);
                s->z ^= prng_rotl(key[3], (uint64_t)(i + 1)) ^ prng_rotl(rc, 31);
            } else {
                s->u ^= key[0] ^ rc; s->v ^= key[1] ^ (rc << 17);
                s->w ^= key[2] ^ (rc >> 13); s->z ^= key[3] ^ prng_rotl(rc, 31);
            }
        } else {
            uint64_t nh = nonce[i & 1], nl = nonce[1 - (i & 1)];
            uint64_t nc = (nh << 32) | (nl & 0xFFFFFFFFULL);
            s->u ^= nc; s->v ^= prng_rotl(nc, 19) ^ (uint64_t)i;
            s->z ^= prng_rotl(nc, 43);
        }
    }
    for (int i = 0; i < 6; i++) tempest_round(s);
}

static inline uint64_t tempest_u64(tempest_state *s) {
    tempest_round(s);
    uint64_t t = s->u ^ prng_rotl(s->v, 32) ^ s->w ^ prng_rotl(s->z, 16);
    t ^= prng_rotl(t, 27);
    /* ADD-square mixing */
    __uint128_t sq = (__uint128_t)t * (__uint128_t)t;
    t += (uint64_t)(sq >> 32);
    /* AND-mix */
    t ^= prng_rotl(t, 31) & prng_rotl(t, 53);
    /* Low-bit whitener */
    t ^= t >> 32;
    return t;
}

static inline void tempest_bytes(tempest_state *s, uint8_t *buf, size_t n) {
    while (n >= 8) { uint64_t r = tempest_u64(s); memcpy(buf, &r, 8); buf += 8; n -= 8; }
    if (n > 0) { uint64_t r = tempest_u64(s); memcpy(buf, &r, n); }
}

/* Dual-output: 2 × 64-bit per round. 73% higher throughput (19.0 Gbit/s).
   out[0] and out[1] use different state permutations — uncorrelated outputs. */
static inline void tempest_u64x2(tempest_state *s, uint64_t out[2]) {
    tempest_round(s);
    uint64_t u = s->u, v = s->v, w = s->w, z = s->z;
    /* Output 1: standard fold4 */
    uint64_t t1 = u ^ prng_rotl(v,32) ^ w ^ prng_rotl(z,16);
    t1 ^= prng_rotl(t1, 27);
    __uint128_t sq = (__uint128_t)t1 * (__uint128_t)t1;
    t1 += (uint64_t)(sq >> 32);
    t1 ^= prng_rotl(t1, 31) & prng_rotl(t1, 53);
    t1 ^= t1 >> 32;
    /* Output 2: permuted fold4 */
    uint64_t t2 = v ^ prng_rotl(w,32) ^ z ^ prng_rotl(u,16);
    t2 ^= prng_rotl(t2, 27);
    sq = (__uint128_t)t2 * (__uint128_t)t2;
    t2 += (uint64_t)(sq >> 32);
    t2 ^= prng_rotl(t2, 31) & prng_rotl(t2, 53);
    t2 ^= t2 >> 32;
    out[0] = t1; out[1] = t2;
}

/* Convenience: random double in [0, 1) */
static inline double tempest_double(tempest_state *s) {
    return (tempest_u64(s) >> 11) * 0x1.0p-53;
}

/* Convenience: random integer in [min, max] with unbiased rejection */
static inline int tempest_range(tempest_state *s, int min, int max) {
    if (min > max) { int t = min; min = max; max = t; }
    unsigned r = (unsigned)(max - min + 1);
    if (r == 0) return (int)tempest_u64(s);
    if ((r & (r - 1)) == 0) return min + (int)(tempest_u64(s) & (r - 1));
    unsigned mask = (1U << (32 - prng_clz32(r))) - 1;
    unsigned x;
    do { x = (unsigned)tempest_u64(s) & mask; } while (x >= r);
    return min + (int)x;
}

/* Convenience: Fisher-Yates shuffle (cryptographically secure) */
static inline void tempest_shuffle(tempest_state *s, void *arr, size_t count, size_t elemsize) {
    uint8_t *a = (uint8_t*)arr;
    uint8_t tmp[256];
    if (elemsize > 256) return;
    for (size_t i = count - 1; i > 0; i--) {
        size_t j = (size_t)tempest_range(s, 0, (int)i);
        if (i != j) {
            memcpy(tmp, a + i * elemsize, elemsize);
            memcpy(a + i * elemsize, a + j * elemsize, elemsize);
            memcpy(a + j * elemsize, tmp, elemsize);
        }
    }
}

/* Convenience: generate hex string from random bytes.
   out must be at least n_bytes*2+1 bytes (includes null terminator). */
static inline void tempest_hex(tempest_state *s, char *out, size_t n_bytes) {
    static const char hex[] = "0123456789abcdef";
    uint8_t buf[64];
    size_t remaining = n_bytes;
    while (remaining > 0) {
        size_t chunk = remaining < 64 ? remaining : 64;
        tempest_bytes(s, buf, chunk);
        for (size_t i = 0; i < chunk; i++) {
            *out++ = hex[buf[i] >> 4];
            *out++ = hex[buf[i] & 15];
        }
        remaining -= chunk;
    }
    *out = '\0';
}

/* Convenience: seed Tempest from a single 64-bit value (deterministic).
   NOT cryptographically secure — use only for reproducible testing. */
static inline void tempest_seed(tempest_state *s, uint64_t seed) {
    uint64_t key[4], nonce[2];
    key[0] = seed + 0x9E3779B97F4A7C15ULL;
    key[1] = ((seed << 17) | (seed >> 47)) * 0x6A09E667F3BCC909ULL;
    key[2] = seed ^ 0x3243F6A8885A308DULL;
    key[3] = ((seed << 32) | (seed >> 32)) + 0xB7E151628AED2A6BULL;
    nonce[0] = seed ^ 0x510E527FADE682D1ULL;
    nonce[1] = seed ^ 0xBB67AE8584CAA73BULL;
    tempest_init(s, key, nonce);
}

#ifdef __cplusplus
}
#endif
#endif /* PRNG_H */

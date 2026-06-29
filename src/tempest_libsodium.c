/* tempest_libsodium.c — Tempest v3 as libsodium custom RNG backend
 * ======================================================================
 * Uses libsodium's randombytes_set_implementation() API.
 *
 * Build:
 *   gcc -O3 -march=native -shared -o tempest_sodium.so tempest_libsodium.c \
 *       tempest_v3.c -Isrc -lsodium
 *
 * Usage (C):
 *   #include <sodium.h>
 *   #include "tempest_libsodium.h"
 *   tempest_sodium_set_randombytes(); // set before sodium_init()
 *   sodium_init();
 *   randombytes_buf(buf, 32); // uses Tempest v3
 *
 * Usage (Python with PySodium):
 *   import libsodium
 *   libsodium.sodium_init()
 * ====================================================================== */
#include <string.h>
#include <stdint.h>
#include <sodium.h>
#include "tempest_v3.h"

/* ── Custom randombytes implementation ── */
static tx4_state sodium_state;
static int sodium_initialized = 0;

static const char *tempest_impl_name(void) {
    return "Tempest v3 CSPRNG";
}

static uint32_t tempest_random(void) {
    return (uint32_t)(tx5cmul_next(&sodium_state) >> 32);
}

static void tempest_stir(void) {
    /* Reseed: mix OS entropy into state */
    uint32_t entropy[8];
    randombytes_buf_deterministic(entropy, sizeof(entropy),
                                   (const unsigned char *)"Tempest", 7);
    uint64_t mix[4] = {0,0,0,0};
    for (int i = 0; i < 4; i++) mix[i] = entropy[i*2] | ((uint64_t)entropy[i*2+1] << 32);
    sodium_state.u ^= mix[0]; sodium_state.v ^= mix[1];
    sodium_state.w ^= mix[2]; sodium_state.z ^= mix[3];
    for (int i = 0; i < 4; i++) tx5cmul_next(&sodium_state);
}

static uint32_t tempest_uniform(const uint32_t upper_bound) {
    /* Standard rejection sampling for unbiased range */
    uint32_t min = -upper_bound % upper_bound;
    uint32_t r;
    do { r = tempest_random(); } while (r < min);
    return r % upper_bound;
}

static void tempest_buf(const void * const buf, const size_t size) {
    tempest_bytes(&sodium_state, (uint8_t *)buf, size);
}

static int tempest_close(void) {
    /* Secure zeroization */
    sodium_memzero(&sodium_state, sizeof(sodium_state));
    sodium_initialized = 0;
    return 0;
}

static struct randombytes_implementation tempest_implementation = {
    .implementation_name = tempest_impl_name,
    .random = tempest_random,
    .stir = tempest_stir,
    .uniform = tempest_uniform,
    .buf = tempest_buf,
    .close = tempest_close
};

/* ── Public API ── */

int tempest_sodium_set_randombytes(void) {
    if (sodium_initialized) return -1;

    /* Initialize Tempest with OS entropy */
    uint8_t key[32], nonce[16];
    randombytes_buf(key, sizeof(key));
    randombytes_buf(nonce, sizeof(nonce));
    uint64_t k[4], n[2];
    memcpy(k, key, 32); memcpy(n, nonce, 16);
    tx5cmul_init(&sodium_state, k, n);
    sodium_initialized = 1;

    randombytes_set_implementation(&tempest_implementation);
    return 0;
}

uint64_t tempest_sodium_next_u64(void) {
    return tx5cmul_next(&sodium_state);
}

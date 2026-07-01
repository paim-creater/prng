# BearSSL + Tempest v3: Custom PRNG Backend

BearSSL's `br_prng_class` vtable interface maps directly to Tempest v3.

## Integration

```c
#include "bearssl.h"
#include "tempest_v3.h"

typedef struct {
    const br_prng_class *vtable;
    tx4_state state;
} TempestPrng;

static void tp_init(const br_prng_class **ctx,
    const void *params, const void *seed, size_t seed_len)
{
    TempestPrng *p = (TempestPrng*)*ctx;
    uint64_t key[4] = {0}, nonce[2] = {0};
    memcpy(key, seed, seed_len > 32 ? 32 : seed_len);
    nonce[0] = key[0] ^ 0x9E3779B97F4A7C15ULL;
    nonce[1] = key[1] ^ 0x6A09E667F3BCC908ULL;
    tempest_init(&p->state, key, nonce);
}

static void tp_generate(const br_prng_class **ctx,
    void *out, size_t len)
{
    TempestPrng *p = (TempestPrng*)*ctx;
    tempest_bytes(&p->state, out, len);
}

static void tp_update(const br_prng_class **ctx,
    const void *seed, size_t seed_len)
{
    TempestPrng *p = (TempestPrng*)*ctx;
    uint64_t mix[4] = {0};
    memcpy(mix, seed, seed_len > 32 ? 32 : seed_len);
    p->state.u ^= mix[0]; p->state.v ^= mix[1];
    p->state.w ^= mix[2]; p->state.z ^= mix[3];
    for (int i = 0; i < 4; i++) tx5cmul_next(&p->state);
}

static const br_prng_class tempest_vtable = {
    sizeof(TempestPrng),
    &tp_init, &tp_generate, &tp_update
};
```

See: https://github.com/paim-creater/prng

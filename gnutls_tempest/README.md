# GnuTLS + Tempest v3: Custom RNG Backend

## Integration

GnuTLS supports pluggable RNG backends via `gnutls_crypto_rnd_register()`.

### Implement the ops struct:

```c
#include "tempest_v3.h"

static tx4_state tempest_ctx;

static int tempest_init(void **ctx) {
    uint64_t key[4] = {1,2,3,4};
    uint64_t nonce[2] = {5,6};
    tx5cmul_init(&tempest_ctx, key, nonce);
    *ctx = &tempest_ctx;
    return 0;
}

static int tempest_rnd(void *ctx, int level, void *data, size_t size) {
    (void)ctx; (void)level;
    tempest_bytes(&tempest_ctx, data, size);
    return 0;
}

static gnutls_crypto_rnd_st tempest_rnd_ops = {
    .init = tempest_init,
    .deinit = NULL,
    .rnd = tempest_rnd,
};
```

### Register:

```c
// After library init
gnutls_crypto_rnd_register(&tempest_rnd_ops, 0);
```

See: https://github.com/paim-creater/prng

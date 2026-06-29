# Mbed TLS + Tempest v3: External Random Generator

## Integration

Mbed TLS supports external RNG via `MBEDTLS_PSA_CRYPTO_EXTERNAL_RNG`.

### Enable in build:

```c
// In mbedtls_config.h or your build:
#define MBEDTLS_PSA_CRYPTO_EXTERNAL_RNG
```

### Implement the callback:

```c
#include "tempest_v3.h"
#include "psa/crypto.h"

static tx4_state tempest_ctx;
static int tempest_ready = 0;

psa_status_t mbedtls_psa_external_get_random(
    mbedtls_psa_external_random_context_t *context,
    uint8_t *output, size_t output_size, size_t *output_length)
{
    (void)context;
    if (!tempest_ready) {
        uint64_t key[4] = {1,2,3,4};
        uint64_t nonce[2] = {5,6};
        tx5cmul_init(&tempest_ctx, key, nonce);
        tempest_ready = 1;
    }
    tempest_bytes(&tempest_ctx, output, output_size);
    *output_length = output_size;
    return PSA_SUCCESS;
}
```

Or use the entropy source API for hybrid mode:

```c
mbedtls_entropy_add_source(&entropy, my_tempest_source, NULL, 32, MBEDTLS_ENTROPY_SOURCE_STRONG);
```

See: https://github.com/paim-creater/prng

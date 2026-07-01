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

static tempest_state tempest_ctx;
static int tempest_ready = 0;

psa_status_t mbedtls_psa_external_get_random(
    mbedtls_psa_external_random_context_t *context,
    uint8_t *output, size_t output_size, size_t *output_length)
{
    (void)context;
    if (!tempest_ready) {
        uint64_t key[4], nonce[2];
        /* Seed from Mbed TLS entropy — NOT hardcoded! */
        if (mbedtls_psa_inject_entropy(key, sizeof(key)) != PSA_SUCCESS)
            return PSA_ERROR_INSUFFICIENT_ENTROPY;
        if (mbedtls_psa_inject_entropy(nonce, sizeof(nonce)) != PSA_SUCCESS)
            return PSA_ERROR_INSUFFICIENT_ENTROPY;
        tempest_init(&tempest_ctx, key, nonce);
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

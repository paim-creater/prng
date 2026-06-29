# WolfSSL + Tempest v3: Custom RNG Backend

## How to Integrate

### Step 1: Add Tempest v3 source to your WolfSSL build

Copy `tempest_v3.c` and `tempest_v3.h` to your WolfSSL source tree:

```bash
cp tempest_v3.c wolfssl/wolfcrypt/src/
cp tempest_v3.h wolfssl/wolfcrypt/include/
```

### Step 2: Define the custom RNG block callback

In `user_settings.h` (or your build config):

```c
#define WC_NO_HASHDRBG
#define CUSTOM_RAND_GENERATE_BLOCK tempest_generate_block

int tempest_generate_block(unsigned char* output, unsigned int sz);
```

### Step 3: Implement the callback

Add to `wolfcrypt/src/random.c` or your own source:

```c
#include "tempest_v3.h"

static tx4_state tempest_global_state;
static int tempest_initialized = 0;

int tempest_generate_block(unsigned char* output, unsigned int sz) {
    if (!tempest_initialized) {
        uint64_t key[4] = {1,2,3,4};
        uint64_t nonce[2] = {5,6};
        tx5cmul_init(&tempest_global_state, key, nonce);
        tempest_initialized = 1;
    }
    tempest_bytes(&tempest_global_state, output, sz);
    return 0;
}
```

### Step 4: Build

```bash
./configure --enable-customrand
make
```

That's it. WolfSSL will now use Tempest v3 for all random number generation.

## Why Tempest v3?

- **17.7 Gbit/s** — 3.3× faster than ChaCha20
- **2^128 security** — conservative, self-analyzed
- **NIST 15/15, TestU01 all 5 suites, PractRand 1 TiB** — all passed
- **Minimal code** — ~200 lines of C, no external dependencies
- **IoT-friendly** — small state (48 bytes), no malloc, constant-time

See the full project at https://github.com/paim-creater/prng

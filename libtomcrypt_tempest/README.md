# LibTomCrypt + Tempest v3: Custom PRNG Backend

Tempest v3 registered via `register_prng()`.

## Usage

```c
#include <tomcrypt.h>
#include "tempest_prng.h"

int prng_idx = register_prng(&tempest_prng_desc);
if (prng_idx == -1) { /* error */ }

/* Use with any libtomcrypt function needing a PRNG */
unsigned char key[32];
prng_descriptor[prng_idx].read(key, sizeof(key), NULL);
```

## Files

- `tempest_prng.c` — full ltc_prng_descriptor implementation
- `tempest_prng.h` — header

## All Callbacks Implemented

| Callback | Status |
|----------|--------|
| start | ✅ alloc state |
| add_entropy | ✅ no-op (CSPRNG) |
| ready | ✅ seed from OS entropy |
| read | ✅ generate bytes |
| done | ✅ secure zeroing |
| export | ✅ export state |
| import | ✅ import state |
| test | ✅ known-answer test |

See: https://github.com/paim-creater/prng

# Proposal: Tempest v3 PRNG for LibTomCrypt

**Discussion issue — not a PR.** Gauging interest before a full pull request.

## Summary

[Tempest v3](https://github.com/paim-creater/prng) is a cryptographic-grade CSPRNG (17.7 Gbit/s, 2^128 provable security) with a 48-byte state — well-suited for LibTomCrypt's embedded use cases. A complete `ltc_prng_descriptor` implementation is ready.

## Key Characteristics

| Metric | Tempest v3 | vs Built-in PRNGs |
|--------|-----------|------------------|
| Throughput | **17.7 Gbit/s** (scalar) | faster than Fortuna/Yarrow |
| Security | **2^128** (ZFC-provable DP bound) | comparable |
| State size | **48 bytes** | smaller than Fortuna |
| Code size | ~200 lines C | C99, no deps |

A complete implementation is available at:
https://github.com/paim-creater/prng/tree/main/libtomcrypt_tempest

## Integration

Uses the standard `register_prng()` / `ltc_prng_descriptor` mechanism:

```c
#include "tempest_prng.h"
int idx = register_prng(&tempest_prng_desc);
/* then use idx with any libtomcrypt function */
```

The descriptor implements all callbacks (start/entropy/ready/read/done/export/import/test) and seeds from OS entropy via `os_get_random()`.

## Reference

- Project: https://github.com/paim-creater/prng
- DESIGN.md: https://github.com/paim-creater/prng/blob/main/DESIGN.md
- NIST SP 800-90A/90B tests: included in source repo

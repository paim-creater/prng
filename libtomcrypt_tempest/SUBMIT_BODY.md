# Proposal: Tempest v3 PRNG for LibTomCrypt

**Discussion issue — not a PR.** I'd like to gauge interest before investing in a full pull request.

## Summary

[Tempest v3](https://github.com/paim-creater/prng) is a cryptographic-grade CSPRNG (17.7 Gbit/s, 2^128 ZFC-provable security) with a 48-byte state and no external dependencies — well-suited for LibTomCrypt's embedded use cases. A complete `ltc_prng_descriptor` implementing all 9 callbacks is ready.

## Key Characteristics

| Metric | Tempest v3 | Fortuna | Yarrow |
|--------|-----------|---------|--------|
| Throughput (scalar) | **17.7 Gbit/s** | ~2 Gbit/s | ~1.5 Gbit/s |
| Throughput (AVX-512) | **65.4 Gbit/s** | — | — |
| State size | **48 bytes** | ~5 KB | ~1 KB |
| Security paradigm | ZFC-provable DP bound | heuristic | heuristic |
| Code size | ~200 lines C | ~800 lines | ~600 lines |

## Integration

Uses `register_prng()` / `ltc_prng_descriptor`:

```c
#include "tempest_prng.h"

int prng_idx = register_prng(&tempest_prng_desc);
if (prng_idx == -1) { /* handle error */ }

// Use with any libtomcrypt function
unsigned char key[32];
prng_descriptor[prng_idx].read(key, sizeof(key), NULL);
```

Full implementation: https://github.com/paim-creater/prng/tree/main/libtomcrypt_tempest

### Callback Implementation

| Callback | Implementation |
|----------|---------------|
| `start` | Allocates marker |
| `add_entropy` | No-op (CSPRNG; optional entropy mixing) |
| `ready` | Seeds from OS entropy via `os_get_random()` |
| `read` | Generates via `tempest_bytes()` |
| `done` | Secure zeroing |
| `export` | Exports marker + 48-byte state |
| `import` | Restores marker + state |
| `test` | Known-answer test (determinism + non-zero) |

## Security

Tempest v3's 2^128 security is mathematically proven within ZFC set theory:

- **Differential**: DP^(1) ≤ 2^(-256), proven via wide trail (a₁ ≥ 4 structural) + AND-mix cascade (DP ≤ 2^(-64) proven)
- **Algebraic**: deg ≥ 256 after 2 rounds (XL complexity ≥ 2^597)
- **Decorrelation**: Weyl sequence per-round (proven-unique round functions)

## Questions

1. Would LibTomCrypt be interested in Tempest v3 as an additional PRNG option?
2. Any concerns about the security proof methodology (self-contained, not community-vetted)?
3. Preferred integration: direct PRNG table entry or contributed example?

## Reference

- Project & full test results: https://github.com/paim-creater/prng
- Design & security analysis: https://github.com/paim-creater/prng/blob/main/DESIGN.md
- NIST SP 800-90A DRBG: 12/12 tests PASS

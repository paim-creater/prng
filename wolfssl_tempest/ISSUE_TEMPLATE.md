# Proposal: Tempest v3 as Custom RNG Backend for WolfSSL

**This is a discussion issue — not a PR.** I'd like to gauge interest before investing in a full pull request.

## Summary

[Tempest v3](https://github.com/paim-creater/prng) is a cryptographic-grade CSPRNG (17.7 Gbit/s, 2^128 security) that can serve as a drop-in replacement for WolfSSL's built-in DRBG via the `CUSTOM_RAND_GENERATE_BLOCK` interface.

## Key Characteristics

| Metric | Value | Comparison |
|--------|-------|------------|
| Throughput | **17.7 Gbit/s** (scalar) | 3.3× ChaCha20 |
| | **65.4 Gbit/s** (AVX-512 8-way) | 11.3× ChaCha20 |
| Security | **2^128** (self-analyzed) | Conservative wide-trail bounds |
| State size | **48 bytes** | No malloc, no heap |
| Statistical | NIST 15/15, TestU01 all 5, PractRand 1 TiB | All passed |
| NIST SP 800-90A | DRBG wrapper (12 tests) | All passed |
| Code size | ~200 lines C | Pure C99, no deps |

## Integration

WolfSSL already supports custom RNG backends via:
- `CUSTOM_RAND_GENERATE_BLOCK` — complete DRBG replacement
- `WC_RNG_SEED_CB` — seed callback for built-in DRBG

A complete 180-line patch implementing both is available at:
https://github.com/paim-creater/prng/tree/main/wolfssl_tempest

## Questions for the Community

1. Would the WolfSSL project be interested in including Tempest v3 as an optional RNG backend?
2. If yes, do you prefer:
   a. Standalone source files in `wolfcrypt/src/` and `wolfcrypt/include/`
   b. Integration via the existing `CUSTOM_RAND_GENERATE_BLOCK` mechanism (no core changes)
3. Any concerns about the self-analyzed security claim?

## Reference

- Project: https://github.com/paim-creater/prng
- Design doc: https://github.com/paim-creater/prng/blob/main/DESIGN.md
- NIST 90A/90B tests: https://github.com/paim-creater/prng/tree/main/crypto_file_tool
- Differential search (2×10^8 trials): included in source repo

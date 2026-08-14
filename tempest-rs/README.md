# Tempest v3 — Pure Rust CSPRNG

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Crates.io](https://img.shields.io/crates/v/tempest-rng.svg)](https://crates.io/crates/tempest-rng)

**Pure Rust** implementation of the Tempest v3 stream cipher / CSPRNG,
providing [`rand_core::RngCore`] and [`rand_core::CryptoRng`] traits.

## Performance

| Metric | Value |
|--------|-------|
| Throughput | **17.7 Gbit/s** dual-output scalar (v4 build; 3.0× ChaCha20 on the same harness) |
| Security | deg ≥ 16/round (W=4 exact), DP/linear-bias bounds certified; 1 TiB PractRand, BigCrush, NIST SP 800-22 |
| NIST SP 800-22 | 15/15 PASS |
| TestU01 | BigCrush + Crush (304 tests) |
| PractRand | 1 TiB zero anomalies |

## Usage

```rust
use tempest_rng::TempestRng;
use rand_core::{RngCore, SeedableRng, CryptoRng};

// From a 64-bit seed (non-cryptographic)
let mut rng = TempestRng::from(42u64);
let x: u64 = rng.next_u64();

// Cryptographic seeding (256-bit key + 128-bit nonce)
let key = [0u8; 32];    // use a secure source in practice
let nonce = [0u8; 16];
let mut rng = TempestRng::new(&key, &nonce);

// Works with all rand crate functions
rng.fill_bytes(&mut buffer);
assert!(rng.next_u32() > 0);
```

## Algorithm

Tempest v3 uses a pure GF(2) round function with only XOR, ROTL, and AND
operations (no integer ADD/CMUL). A 4-stage AND-mix cascade doubles the algebraic
degree 4 times per round (proven by induction). After 2 rounds: deg ≥ 256,
XL complexity ≥ 2^{345} (heuristic estimate). The AND gate is GF(2) multiplication,
making the algebraic degree growth fully analyzable.

## Testing

```bash
cargo test
```

## References

- [C reference implementation](https://github.com/paim-creater/prng)
- [Design document](https://github.com/paim-creater/prng/blob/main/DESIGN.md)

## License

MIT

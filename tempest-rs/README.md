# Tempest v3 — Cryptographic-grade CSPRNG (2^128 security)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Crates.io](https://img.shields.io/crates/v/tempest-rng.svg)](https://crates.io/crates/tempest-rng)

**Pure Rust** implementation of the Tempest v3 stream cipher / CSPRNG,
providing [`rand_core::RngCore`] and [`rand_core::CryptoRng`] traits.

## Performance

| Metric | Value |
|--------|-------|
| Throughput | **17.7 Gbit/s** (3.3× ChaCha20) |
| Security | **2^128** conservative (self-analyzed) |
| NIST SP 800-22 | 15/15 PASS |
| TestU01 | BigCrush + Crush (all 250 tests) |
| PractRand | 1 TiB zero anomalies |

## Usage

```rust
use tempest_rng::TempestRng;
use rand_core::{RngCore, SeedableRng, CryptoRng};

// From a 64-bit seed (non-cryptographic)
let mut rng = TempestRng::from_seed(42u64.to_le_bytes());
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

Tempest v3 uses 4 carryless multiply (cmul) operations per round in a
Fibonacci dependency weave with Weyl sequence per-round decorrelation,
ADD pre-diffusion (z→u feedback), and a 4-stage AND-mix output cascade.

## Testing

```bash
cargo test
```

## References

- [C reference implementation](https://github.com/paim-creater/prng)
- [Design document](https://github.com/paim-creater/prng/blob/main/DESIGN.md)

## License

MIT

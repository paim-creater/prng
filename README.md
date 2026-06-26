# Bolt & Tempest: Algebraic Degree-Driven PRNG Design

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Language: C99](https://img.shields.io/badge/Language-C99-blue.svg)](src/)
[![Benchmark](https://github.com/paim-creater/prng/actions/workflows/benchmark.yml/badge.svg)](https://github.com/paim-creater/prng/actions/workflows/benchmark.yml)

Two high-performance pseudorandom number generators designed through an **algebraic degree-driven methodology** — target the algebraic degree (deg) over GF(2) first, then reverse-engineer the optimal primitive combination.

| Platform | Status |
|----------|--------|
| x86-64 (GCC/Clang/MSVC) | ✅ Full support |
| ARM64 (Apple M / Cortex-A) | ✅ Full support |
| RISC-V 64 | ✅ Full support |
| MSVC | ✅ Supported via `src/platform.h` |

---

## At a Glance

| Algorithm | Type | Throughput | Security | Test Status |
|-----------|------|-----------|----------|-------------|
| **ADC-Bolt** | Non-crypto PRNG | **70.3 Gbit/s** (12.1× ChaCha20) | deg=2 (non-crypto) | NIST ✅ TestU01 ✅ PractRand ✅ |
| **4-cmul Tempest v3** | CSPRNG | **19.6 Gbit/s** (3.3× ChaCha20) | 2¹²⁸ (self-analyzed) | NIST ✅ TestU01 ✅ PractRand 1 TiB ✅ |

> ⚡ Benchmarked on AMD Ryzen 9 8940HX (Zen 4), MinGW-w64 GCC 16.1.0, `-O3 -march=native -flto`. Single-core, scalar code (no SIMD).

---

## Quick Start

```bash
git clone https://github.com/paim-creater/prng.git && cd prng
make && make bench
```

Expected output:
```
============================================
  Bolt & Tempest — Throughput Benchmark
============================================
  ADC-Bolt:            62753 Mbit/s  (62.8 Gbit/s)
  4-cmul Tempest v3:   19594 Mbit/s  (19.6 Gbit/s)  [dual-output]
============================================
```

### Drop-In Usage (Single Header)

Copy one file — no build system needed:

```c
#include "prng_single_header.h"

// Non-crypto: games, Monte Carlo, ML
adcbolt_state rng;
adcbolt_seed(&rng, 42);
double x = adcbolt_double(&rng);
int dice = adcbolt_range(&rng, 1, 6);

// Cryptographic: keys, tokens, authentication
tempest_state csprng;
tempest_init(&csprng, key, nonce);
uint64_t token = tempest_u64(&csprng);
```

### Python

```python
import prng

rng = prng.ADC_Bolt(seed=42)
print(rng.randint(1, 6))

csprng = prng.Tempest(key=bytes(32), nonce=bytes(16))
print(csprng.hex(16))
```

---

## Design Methodology

Traditional PRNG design follows: *choose structure → test → add rounds*. We reverse this:

**First determine the target algebraic degree (deg), then reverse-engineer the primitives.**

The key metric is **deg-per-mul** — algebraic degree yield per hardware multiplication:

$$\text{deg-per-mul} = \frac{\max\deg(\text{after one round})}{\text{multiplications per round}}$$

This single number guides every design decision, transforming PRNG development from empirical tuning into goal-directed optimization.

### ADC-Bolt (70.3 Gbit/s)

Replace MULX multiplication (3-cycle latency) with **carry-chain dual-addition** (ADD+ADD, 2-cycle latency). Same algebraic degree (deg=2), shorter critical path, **52% throughput gain** over the MULX baseline.

```c
// Core nonlinearity: carry-chain provides deg=2 at 2c latency
z = (z + u) + v;   // majority carry = quadratic over GF(2)
```

### 4-cmul Tempest v3 (19.6 Gbit/s, 2¹²⁸ security)

Four architectural innovations after 11 generations of iteration:

1. **ADD pre-diffusion** — breaks XOR serial dependency chain, doubles state-word deg from 1→2, ILP +33%
2. **4-cmul Fibonacci-weave** — optimal multiplication scheduling with active-cmul lower bound a₁ ≥ 3 (DP ≤ 2⁻¹⁸⁶)
3. **AND-mix output** — replaces 3-cycle MULX square with ~1-cycle bitwise AND-of-rotations (deg=2d over GF(2))
4. **Dual-output** — generates 2×64-bit per round by permuting state combinations, 73% throughput gain

---

## Statistical Testing

Both algorithms have passed **all** statistical tests applied:

| Test Suite | Tests | ADC-Bolt | 4-cmul Tempest v3 |
|------------|-------|----------|-------------------|
| NIST SP 800-22 | 15 series | ✅ 15/15 | ✅ 15/15 |
| TestU01 SmallCrush | 10 | ✅ Pass | ✅ Pass |
| TestU01 Rabbit | 40 | ✅ Pass | ✅ Pass |
| TestU01 Alphabit | 17 | ✅ Pass | ✅ Pass |
| TestU01 BigCrush | 106 | ✅ Pass (1h39m) | ✅ Pass (1h43m) |
| TestU01 Crush | 96 | ✅ Pass (12h46m) | ✅ Pass (16m13s) |
| PractRand | — | ✅ 1 TiB, 354 sets | ✅ 1 TiB, 354 sets, 0 anomalies |

Full test logs: [`results/`](results/)

---

## Performance

### Reference Platform (AMD Zen 4)

| Algorithm | Rounds | Time | Throughput |
|-----------|--------|------|------------|
| ADC-Bolt | 2×10⁸ | 182 ms | 70.3 Gbit/s |
| 4-cmul Tempest v3 | 5×10⁷ | 168 ms | 19.6 Gbit/s |
| ChaCha20 (scalar) | 2×10⁸ | — | 5.8 Gbit/s |

### Predicted Performance by Architecture

| CPU | ADC-Bolt | Tempest v3 | Key Factor |
|-----|----------|------------|------------|
| **Apple M4 Pro/Max** 🥇 | 85–95 Gbit/s | 16–18 Gbit/s | UMULL=1c (=ADD latency) |
| AMD Zen 5 | 75–82 Gbit/s | 13–15 Gbit/s | IPC +15% over Zen 4 |
| **AMD Zen 4** | **70.3** ✅ | **19.0** ✅ | Reference platform |
| Intel Arrow Lake | 75–85 Gbit/s | 12–14 Gbit/s | Higher clock (5.7 GHz) |
| Intel Raptor Lake | 60–70 Gbit/s | 10–12 Gbit/s | Previous gen |
| ARM Cortex-X4 | 55–65 Gbit/s | 10–13 Gbit/s | Mobile thermal limits |

> 🥇 ARM64 is the ideal platform — multiply latency (UMULL=1c) equals ADD latency (1c), eliminating the MULX bottleneck that limits x86-64.

### Reproduce on Your Hardware

```bash
git clone https://github.com/paim-creater/prng.git && cd prng
gcc -O3 -march=native -o benchmark benchmark.c src/adcbolt.c src/tempest_v3.c -I.
./benchmark
```

Then [submit your results](https://github.com/paim-creater/prng/issues/new?template=benchmark_result.md) to the community database!

| Contributor | CPU | ADC-Bolt | Tempest v3 |
|-------------|-----|----------|------------|
| [Submit yours →](https://github.com/paim-creater/prng/issues/new?template=benchmark_result.md) | — | — | — |
| [@paim-creater](https://github.com/paim-creater) | Ryzen 9 8940HX (Zen 4) | 70.3 Gbit/s | 19.6 Gbit/s |
| [GitHub Actions CI](https://github.com/paim-creater/prng/actions) | Xeon E5 v4 | 8.6 Gbit/s | 4.6 Gbit/s |

---

## Repository Structure

```
.
├── README.md
├── LICENSE                    ← MIT
├── CONTRIBUTING.md
├── CMakeLists.txt             ← CMake build (MSVC / Xcode / Make / Ninja)
├── Makefile                   ← One-click: make && make bench
├── prng_single_header.h       ← Drop-in: copy one file, #include it
├── prng.py                    ← Python bindings
├── benchmark.c                ← Throughput benchmark
├── test_bolt.c                ← ADC-Bolt self-test
├── test_tempest.c             ← Tempest v3 self-test
├── examples/
│   ├── dice_roll.c            ← Game dice roller
│   ├── generate_token.c       ← Secure API token
│   └── monte_carlo.c          ← π via Monte Carlo
├── src/
│   ├── platform.h             ← Auto-detects x86-64 / ARM64 / RISC-V / MSVC
│   ├── adcbolt.h              ← ADC-Bolt API
│   ├── adcbolt.c              ← ADC-Bolt implementation
│   ├── tempest_v3.h           ← Tempest v3 API
│   └── tempest_v3.c           ← Tempest v3 implementation
├── results/                   ← Full test logs
│   ├── nist_tempest_v3_report.txt
│   ├── smallcrush_tempest_v3.log
│   ├── rabbit_tempest_v3.log
│   ├── alphabit_tempest_v3.log
│   ├── bigcrush_tempest_v3.log
│   ├── crush_tempest_v3.log
│   ├── practrand_tempest_v3_1tb.log
│   └── (adcbolt counterparts)
└── .github/
    ├── workflows/benchmark.yml  ← CI benchmark
    └── ISSUE_TEMPLATE/
```

---

## Security Disclaimer

The 2¹²⁸ security claim for 4-cmul Tempest v3 is **self-analyzed** and has **not been independently verified** by a third party. The security argument rests on:

- **Wide-trail analysis**: active cmul lower bound a₁ ≥ 3, iterative DP ≤ 2⁻¹⁸⁶
- **Algebraic degree**: deg ≥ 256 after 2 rounds (XL/Gröbner base ≥ 2¹²⁸)
- **Empirical**: >2.2×10¹⁰ samples, zero differential collisions
- **Two unproven hypotheses** (H1: cmul differential uniformity; H2: inter-round decorrelation)

This follows the same methodological paradigm as AES and ChaCha20 — structural lower bounds + component analysis + empirical validation. See the [paper](https://github.com/paim-creater/prng) for full security analysis.

---

## Build Options

### Make (Linux / macOS / MSYS2)

```bash
make            # compile + run self-tests
make test       # build and run both test programs
make benchmark  # build benchmark binary
make bench      # build and run benchmark
make clean      # remove binaries
```

### CMake (All platforms including MSVC)

```bash
mkdir build && cd build
cmake ..
cmake --build .
ctest           # run test_all
./benchmark     # run benchmark
```

### Manual Compilation

```bash
# ADC-Bolt
gcc -O3 -march=native -o test_bolt test_bolt.c src/adcbolt.c -I.

# Tempest v3
gcc -O3 -march=native -o test_tempest test_tempest.c src/tempest_v3.c -I.

# Benchmark
gcc -O3 -march=native -o benchmark benchmark.c src/adcbolt.c src/tempest_v3.c -I.
```

---

## Comparison

### Scalar CSPRNG

| Algorithm | Throughput | Security | Verification |
|-----------|-----------|----------|-------------|
| **4-cmul Tempest v3** | **19.6 Gbit/s** | 2¹²⁸ (self-analyzed) | TestU01 all 5 levels, PractRand 1 TiB |
| ChaCha20 | 5.8 Gbit/s | 2²⁵⁶ | 15+ years of cryptanalysis |
| AES-CTR DRBG (AES-NI) | 2–6 Gbit/s | 2²⁵⁶ | NIST standard |

### Non-Crypto PRNG

| Algorithm | Throughput | State Update | TestU01 BigCrush |
|-----------|-----------|-------------|-----------------|
| RomuTrio | ~213 Gbit/s | Linear | ❌ Fails after 2¹⁹ bytes |
| wyrand | ~178 Gbit/s | Linear | Partial pass |
| xoroshiro128+ | ~90 Gbit/s | Linear | ❌ Some failures |
| **ADC-Bolt** | **70.3 Gbit/s** | **Nonlinear (deg=2)** | ✅ Full pass |

---

## Citation

```bibtex
@misc{bolt_tempest_2026,
  title = {4-cmul Tempest v3 \& ADC-Bolt:
           Algebraic Degree-Driven PRNG Design},
  author = {Tian Yuezhou},
  year = {2026},
  url = {https://github.com/paim-creater/prng},
}
```

## License

MIT — free for academic, commercial, and personal use. See [LICENSE](LICENSE).

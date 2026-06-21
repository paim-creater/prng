# Bolt & Tempest: Algebraic Degree-Driven PRNG Design

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Language: C](https://img.shields.io/badge/Language-C-blue.svg)](src/)
[![Benchmark](https://github.com/paim-creater/prng/actions/workflows/benchmark.yml/badge.svg)](https://github.com/paim-creater/prng/actions/workflows/benchmark.yml)

Two high-performance pseudorandom number generators designed through an algebraic degree-driven methodology.

- 🔒 **4-cmul Tempest v3** — **Fastest known scalar CSPRNG** (11.5 Gbit/s, 2.0× ChaCha20)
- ⚡ **ADC-Bolt** — Among the fastest non-crypto PRNGs with **nonlinear state update** (70.3 Gbit/s, 12.1× ChaCha20)

## Quick Facts

| Algorithm | Type | Throughput | Security | Benchmark Position |
|-----------|------|-----------|----------|-------------------|
| **4-cmul Tempest v3** | Cryptographic CSPRNG | **11.5 Gbit/s** ⚡ | 2¹²⁸ (self-analyzed) | **#1 scalar CSPRNG** |
| **ADC-Bolt** | Non-cryptographic PRNG | **70.3 Gbit/s** ⚡ | Nonlinear (deg=2) | Top-10 non-crypto, only nonlinear one |

> ⚡ Measured on **AMD Ryzen 9 8940HX (Zen 4)**, MinGW-w64 GCC 16.1.0, `-O3 -march=native -flto`

### Scalar CSPRNG Comparison

| Algorithm | Throughput | Security | Verification |
|-----------|-----------|----------|-------------|
| **4-cmul Tempest v3** | **11.5 Gbit/s** | 2¹²⁸ (self-analyzed) | TestU01 all 5 levels, PractRand 1TiB |
| ChaCha20 (scalar) | 5.8 Gbit/s | 2²⁵⁶ | 15+ years of cryptanalysis |
| AES-CTR DRBG (AES-NI) | 2–6 Gbit/s | 2²⁵⁶ | NIST standard, 20+ years |

### Non-Crypto PRNG Comparison

| Algorithm | Throughput | State Update | TestU01 BigCrush |
|-----------|-----------|-------------|-----------------|
| RomuTrio | ~213 Gbit/s | Linear | ❌ Fails after 2¹⁹ bytes |
| wyrand | ~178 Gbit/s | Linear | Partial pass |
| xoroshiro128+ | ~90 Gbit/s | Linear | ❌ Some failures |
| **ADC-Bolt** | **70.3 Gbit/s** | **Nonlinear (deg=2)** | ✅ Full pass |

Both algorithms pass **all** statistical tests:
- NIST SP 800-22: 15/15 ✓
- TestU01 (SmallCrush, Rabbit, Alphabit, BigCrush, Crush): 337/337 ✓
- PractRand 1 TiB: 354/354 test sets, zero anomalies ✓

## Key Innovations

### ADC-Bolt
Replace MULX multiplication (3-cycle latency) with **carry-chain dual-addition** (ADD+ADD, 2-cycle latency) — same algebraic degree (deg=2), shorter critical path, 52% throughput gain over the MULX baseline.

### 4-cmul Tempest v3
Three architectural innovations after 11 generations of iteration:
1. **ADD pre-diffusion** — breaks a hidden XOR serial dependency chain, doubling state-word algebraic degree while improving ILP by 33%
2. **4-cmul Fibonacci-weave** — optimal multiplication scheduling with active-cmul lower bound a₁ ≥ 3 (DP ≤ 2⁻¹⁸⁶)
3. **AND-mix output** — replaces a 3-cycle MULX square with a ~1-cycle bitwise AND-of-rotations operation over GF(2)

## Quick Start

```bash
git clone https://github.com/paim-creater/prng.git
cd prng
make          # compiles and runs self-tests for both algorithms
make benchmark # runs throughput benchmark (requires gcc -O3)
```

### Minimal Example

```c
#include "src/tempest_v3.h"

int main() {
    tx4_state state;
    uint64_t key[4] = {0x1234..., 0x5678..., 0x9ABC..., 0xDEF0...};
    uint64_t nonce[2] = {0xAAAA..., 0xBBBB...};
    
    tx5cmul_init(&state, key, nonce);
    
    // Generate random numbers
    for (int i = 0; i < 10; i++)
        printf("%016llx\n", tx5cmul_next(&state));
    
    return 0;
}
```

### ADC-Bolt Example

```c
#include "src/adcbolt.h"

int main() {
    bolt3_state state;
    adcbolt_seed(&state, 42);
    
    for (int i = 0; i < 10; i++)
        printf("%016llx\n", adcbolt_next(&state));
    
    return 0;
}
```

## Repository Structure

```
.
├── README.md              ← You are here
├── Makefile               ← One-click build + test
├── LICENSE                ← MIT License
├── test_bolt.c            ← ADC-Bolt self-test
├── test_tempest.c         ← Tempest v3 self-test
├── benchmark.c            ← Throughput benchmark
├── src/
│   ├── tempest_v3.h       ← 4-cmul Tempest v3 API
│   ├── tempest_v3.c       ← 4-cmul Tempest v3 implementation
│   ├── adcbolt.h          ← ADC-Bolt API
│   └── adcbolt.c          ← ADC-Bolt implementation
└── results/
    ├── adcbolt_nist_report.txt  ← ADC-Bolt NIST 15/15
    ├── smallcrush_adcbolt.log   ← ADC-Bolt SmallCrush 15/15
    ├── rabbit_adcbolt.log       ← ADC-Bolt Rabbit 40/40
    ├── alphabit_adcbolt.log     ← ADC-Bolt Alphabit 17/17
    ├── bigcrush_adcbolt.log     ← ADC-Bolt BigCrush 160/160
    ├── crush_adcbolt.log        ← ADC-Bolt Crush 144/144
    ├── practrand_adcbolt.log    ← ADC-Bolt PractRand 1 TiB
    ├── tempest_v3_nist_report.txt ← Tempest v3 NIST 15/15
    ├── smallcrush_v3.log        ← Tempest v3 SmallCrush 15/15
    ├── rabbit_v3.log            ← Tempest v3 Rabbit 40/40
    ├── alphabit_v3.log          ← Tempest v3 Alphabit 17/17
    ├── bigcrush_v3.log          ← Tempest v3 BigCrush 160/160
    ├── crush_v3.log             ← Tempest v3 Crush 144/144
    └── practrand_v3_1tb.log     ← Tempest v3 PractRand 1 TiB (354/354)
```

## Benchmark Guide

Reproduce the throughput measurements on your own hardware.

### Prerequisites

- **GCC** (MinGW-w64 on Windows, or native on Linux/macOS)
- **Make** (optional; you can compile manually)

### Step 1: Clone and Build

```bash
git clone https://github.com/paim-creater/prng.git
cd prng
make          # runs self-tests for both algorithms
```

If `make` is not available, compile manually:

```bash
# Linux / macOS / MSYS2
gcc -O3 -march=native -o test_bolt test_bolt.c src/adcbolt.c -I.
gcc -O3 -march=native -o test_tempest test_tempest.c src/tempest_v3.c -I.
./test_bolt && ./test_tempest
```

### Step 2: Run Benchmark

```bash
make benchmark
```

Or manually:

```bash
gcc -O3 -march=native -o benchmark benchmark.c src/adcbolt.c src/tempest_v3.c -I.
./benchmark
```

### Step 3: Read the Output

```
============================================
  Bolt & Tempest — Throughput Benchmark
============================================

  ADC-Bolt:             70261 Mbit/s  ( 70.3 Gbit/s)   182 ms
  4-cmul Tempest v3:    11503 Mbit/s  ( 11.5 Gbit/s)   278 ms

============================================
  Reference (same platform):
    ADC-Bolt:             70,261 Mbit/s  (70.3 Gbit/s)
    4-cmul Tempest v3:    11,503 Mbit/s  (11.5 Gbit/s)
    Platform: AMD Ryzen 9 8940HX, MinGW-w64 GCC -O3
============================================
```

### Important Notes

| Factor | Impact |
|--------|--------|
| **`-O3 -march=native`** | **Critical.** Without these flags, throughput drops 3–5×. |
| CPU frequency scaling | Close other apps, plug in AC power for stable results. |
| Thermal throttling | Let the laptop cool down between runs. |
| Compiler version | GCC 13+ recommended. MSVC produces ~10–15% lower throughput. |
| Different CPU | Results vary by microarchitecture. Zen 4 > Zen 3 > Intel 12th-gen. |

### Expected Ranges

| Algorithm | Low-end (laptop) | Mid-range (desktop) | High-end (Zen 4) |
|-----------|-----------------|--------------------|--------------------|
| ADC-Bolt | 25–40 Gbit/s | 50–60 Gbit/s | **65–75 Gbit/s** |
| Tempest v3 | 4–7 Gbit/s | 8–10 Gbit/s | **10–12 Gbit/s** |

### Community Benchmarks

Run on your own hardware and submit your results to help build a public performance database.

```bash
git clone https://github.com/paim-creater/prng.git && cd prng
gcc -O3 -march=native -o benchmark benchmark.c src/adcbolt.c src/tempest_v3.c -I.
./benchmark
```

Then [open an issue](https://github.com/paim-creater/prng/issues/new) with:

```markdown
**CPU:** [your CPU model]
**OS:** [Windows/Linux/macOS]
**Compiler:** [gcc version]
**ADC-Bolt:** [your result] Gbit/s
**Tempest v3:** [your result] Gbit/s
```

| Contributor | CPU | ADC-Bolt | Tempest v3 |
|-------------|-----|----------|------------|
| [Your name?](https://github.com/paim-creater/prng/issues/new) | Your CPU | ? Gbit/s | ? Gbit/s |
| [@paim-creater](https://github.com/paim-creater) | Ryzen 9 8940HX (Zen 4) | 70.3 Gbit/s | 11.5 Gbit/s |
| [GitHub Actions CI](https://github.com/paim-creater/prng/actions/workflows/benchmark.yml) | Xeon E5 v4 | 8.6 Gbit/s | 4.6 Gbit/s |

## Design Methodology

Traditional PRNG design follows: choose structure → test → add rounds. We reverse this:

**First determine the target algebraic degree (deg), then reverse-engineer the primitives.**

The key metric is **deg-per-mul** — algebraic degree yield per hardware multiplication:
```
deg-per-mul = max(deg after one round) / (multiplications per round)
```

This single number guides every design decision, transforming PRNG development from empirical tuning into goal-directed optimization.

## Security Disclaimer

The 2¹²⁸ security claim for 4-cmul Tempest v3 is **self-analyzed** and has **not been independently verified** by a third party. The security argument rests on two unproven hypotheses (H1: cmul differential uniformity; H2: inter-round independence), supported by theory, algebra, and >10¹⁰ empirical samples with zero collisions — following the same methodological paradigm as AES and ChaCha20.

## Related Work

- Odrzywołek (2026): EML operator — original inspiration
- Daemen & Rijmen (2002): AES wide-trail strategy — security framework foundation
- Bernstein (2008): ChaCha20 — ARX stream cipher benchmark
- Blackman & Vigna (2018): xoroshiro — speed benchmark for non-crypto PRNGs

## Citation

If you use this code in your research, please cite:

```
@misc{bolt_tempest_2026,
  title = {4-cmul Tempest v3 \& ADC-Bolt: 
           Algebraic Degree-Driven PRNG Design},
  author = {Tian Yuezhou},
  year = {2026},
}
```

## License

MIT License — see [LICENSE](LICENSE) for details. Free for academic, commercial, and personal use.

# Bolt & Tempest: Algebraic Degree-Driven PRNG Design

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Language: C](https://img.shields.io/badge/Language-C-blue.svg)](src/)

Two high-performance pseudorandom number generators designed through an algebraic degree-driven methodology.

## Quick Facts

| Algorithm | Type | Throughput | Security | ChaCha20 vs |
|-----------|------|-----------|----------|-------------|
| **ADC-Bolt** | Non-cryptographic PRNG | **70.3 Gbit/s** | Statistical only | 12.1× faster |
| **4-cmul Tempest v3** | Cryptographic CSPRNG | **11.1 Gbit/s** | 2¹²⁸ (self-analyzed) | 1.9× faster |

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
├── LICENSE                ← MIT License
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

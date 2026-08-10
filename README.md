# AM-SEV / Tempest v3 — Verifiable Cryptographic Design

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Language: C99 / Python / Verilog](https://img.shields.io/badge/Language-C99%20%2F%20Python%20%2F%20Verilog-blue.svg)](src/)
[![Awesome](https://cdn.rawgit.com/sindresorhus/awesome/master/media/badge.svg)](https://github.com/rust-cc/awesome-cryptography-rust)

This repository is the **code and evidence companion** to the paper
*AM-SEV: A Metric Theory of Verifiable Cryptographic Design, Its AI
Engine, and the Tempest Instance* (Yuèzhōu Tiān, 2026). The paper itself
is not distributed here; every claim in it is backed by a runnable
artifact in this repository.

**Core idea.** Security is traditionally assessed only after
implementation. AM-SEV is a metric theory over GF(2) that makes the
one-round differential probability of two-layer AND-RX designs
*exactly computable at design time*: the Polar-Rank Theorem gives
DP(Δ) = 2^(−rank B_Δ), a polynomial-time linear-algebra computation at
any width. The two-layer polar-rank barrier (min rank 3 at every width)
explains why cascades are necessary, and the andmix4 cascade eliminates
the shadow's weak differentials (2⁻³ → 2⁻¹¹ exact at W=4, below 2⁻²⁴
sampled at W=64). The theory is instantiated as an AI design engine
whose calibrated verifier stack adjudicates every proposal — human,
evolutionary, or LLM-authored — with verification as the invariant.

## Repository layout

| Directory | Contents |
|---|---|
| [`src/`](src/) | C99 implementations: Tempest v3/v4, AVX-512 port, ADC-Bolt (legacy non-crypto PRNG), ChaCha20 reference, benchmarks |
| [`code/`](code/) | Reference C sources (KAT-verified), stream-cipher demo, runtime self-check, SAT/MILP analysis tools |
| [`engine/`](engine/) | **Python verification engine** — every metric, certificate, and audit script of the paper, with its JSON result data (38 scripts, 25 datasets) |
| [`hardware/`](hardware/) | KAT-verified Verilog RTL, synthesis/place-and-route logs, the completed k=2 bitstream (135 KB) |
| [`data/`](data/) | Statistical test logs: NIST SP 800-22, TestU01 BigCrush/Crush, PractRand 1 TiB, and the v3.1 failure control |
| [`tests/`](tests/) | KAT verification harness |
| [`examples/`](examples/) | Application demos (dice, tokens, UUIDs, passwords) |
| [`results/`](results/) | Historical benchmark and test reports |
| `tempest-rs/`, `pypi_package/`, `homebrew/` | Rust crate, PyPI package, Homebrew formula |
| [`docs/`](docs/) | Design rationale, API reference, and the audit record |

## Quick start

```bash
# C implementation + KAT (needs a C99 compiler)
make kat           # or: gcc -O3 -o kat_check src/kat_check_main.c code/tempest_v3.c && ./kat_check
# expect: all 5 KAT blocks match, including 0x6BBE30BB1D12DDD0

# Python verification engine (needs numpy; SAT parts need pysat)
cd engine
python cipher.py            # self-test of the bit-exact port
python audit_true_algorithm1.py   # W=4 full-domain exact metrics
python readword_theorem.py  # Read-Word Polar-Rank Theorem verification

# Hardware (needs the OSS CAD Suite: yosys, nextpnr-ice40, icepack)
cd hardware
bash scripts/synth.sh       # synthesize; k=2 variant completes place-and-route
```

## Listed in

Featured in the curated list [Awesome Cryptography Rust](https://github.com/rust-cc/awesome-cryptography-rust).

## Headline numbers (measured, all reproducible from this repo)

| Quantity | Value | Evidence |
|---|---|---|
| DP(1), two-layer shadow | 2⁻³, exact at every width | Polar-Rank Theorem + W=64 rank-3 certificate |
| DP(1), full design | 2⁻⁵·⁹⁴²⁰ exact at W=4; <2⁻²⁴ sampled at W=64 | `engine/audit_true_algorithm1.json` |
| Algebraic degree | β₁ = 16, certificate at W=64 | `engine/explore_cascade_degree.py` |
| KAT | 5/5 blocks, incl. 0x6BBE30BB1D12DDD0 | `tests/`, `hardware/sim/` |
| Statistical tests | NIST 15/15, BigCrush all-pass, **PractRand 1 TiB** clean | `data/` |
| C scalar (dual) | 6.4 Gbit/s (13.4 @5 GHz), same-harness vs ChaCha20 6.1 | `src/bench_*` |
| C AVX-512 (8-way) | 35.5 Gbit/s (≈74 @5 GHz) | `src/bench_a1_avx512.c` |
| FPGA (k=2 variant) | 5,915 LUT4 / 1,034 FF, 34.21 MHz, **2.19 Gbit/s, completed bitstream (135 KB)** | `hardware/` |

## Audit record

The paper ships a full audit record, and so does this repository: see
[`docs/AUDIT_RECORD.md`](docs/AUDIT_RECORD.md). The short version —
every earlier claim that did not survive verification was corrected and
the correction is documented, including: the v3.1 dead-key predecessor,
the W=4 snapshot-semantics discrepancy, the withdrawn half-entropy law,
the W=8 linear-measurement multiple-testing artifact, and the
differential-trail zero-cancellation artifact in the multi-round model.

## Reproducibility promise

Every number in the paper can be re-derived from this repository on a
stock laptop: the engine scripts print the exact values into JSON, the
KAT harnesses verify bit-exactness against the published vector, and
the FPGA flow is fully open-source (Yosys → nextpnr → icepack).

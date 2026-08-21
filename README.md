# Tempest v3 — Verifiable Cryptographic Design

[![Mentioned in Awesome Cryptography (Rust)](https://awesome.re/mentioned-badge-flat.svg)](https://github.com/rust-cc/awesome-cryptography-rust)

Tempest v3 is an AND-RX cryptographic random number generator whose
security statements are exact design-time computations. It accompanies
the paper *AM-SEV: A Metric Theory of Verifiable Cryptographic Design,
Its AI Engine, and the Tempest Instance* (Yuèzhōu Tiān, 2026); the
paper is not distributed here, but every quantitative claim in it is
backed by a runnable artifact in this repository.

The core result is the Polar-Rank Theorem: for two-layer AND-RX round
functions the one-round differential probability is
DP(Δ) = 2^(−rank B_Δ), computable in polynomial time at any word width.
The two-layer polar-rank barrier (minimum rank 3 at every width) shows
why cascades are necessary, and the andmix4 cascade eliminates the
shadow's weak differentials (2⁻³ → 2⁻¹¹ exact at W=4, below 2⁻²⁴
sampled at W=64). The same metrics drive an AI design engine whose
calibrated verifier stack adjudicates every candidate.

Also listed in the [Awesome Cryptography
(Rust)](https://github.com/rust-cc/awesome-cryptography-rust) collection,
Pseudo Random Number Generator (PRNG) section.

## Repository layout

| Directory | Contents |
|---|---|
| [`code/`](code/) | C sources: Algorithm 1 and v4 implementations, KAT vectors, benchmarks, stream-cipher demo, runtime self-check, SAT/MILP analysis tools, legacy v3.1 tools |
| [`engine/`](engine/) | Python verification engine: every metric, certificate, and audit script of the paper, with JSON result data |
| [`hardware/`](hardware/) | Verilog RTL, synthesis/place-and-route logs, the completed k=2 bitstream (135 KB) |
| [`data/`](data/) | Statistical test logs: NIST SP 800-22, TestU01 BigCrush, PractRand 1 TiB, and the v3.1 failure control |
| [`docs/`](docs/) | Design rationale, API reference, audit record, v3.1 fix record |
| [`tests/`](tests/) | KAT and self-test harnesses |
| [`examples/`](examples/) | Application demos (dice, tokens, UUIDs, passwords) |
| [`include/`](include/) | `prng_single_header.h` — single-header drop-in |
| [`python/`](python/) | Python tools: ctypes bindings, CUDA kernel, setup helper |
| [`golang/`](golang/), [`cpp/`](cpp/), [`tempest-rs/`](tempest-rs/), [`wolfssl_tempest/`](wolfssl_tempest/) | Language bindings and integrations |
| [`pypi_package/`](pypi_package/), [`homebrew/`](homebrew/) | PyPI package, Homebrew formula |
| [`results/`](results/) | Historical benchmark and test reports |

## Quick start

```bash
# C implementation + KAT check (needs a C99 compiler)
make kat              # compiles code/kat_check, verifies 0x6BBE30BB1D12DDD0
make test             # self-tests for Algorithm 1 and ADC-Bolt

# Python verification engine (numpy; SAT parts need pysat)
cd engine
python cipher.py                   # bit-exact port self-test
python audit_true_algorithm1.py    # W=4 full-domain exact metrics
python readword_theorem.py         # Read-Word Polar-Rank Theorem

# FPGA flow (OSS CAD Suite: yosys, nextpnr-ice40, icepack)
cd hardware
bash scripts/synth.sh              # k=2 variant completes place-and-route
```

## Headline numbers (all reproducible from this repository)

| Quantity | Value | Evidence |
|---|---|---|
| DP(1), two-layer shadow | 2⁻³, exact at every width | Polar-Rank Theorem + W=64 rank-3 certificate |
| DP(1), full design | 2⁻⁵·⁹⁴²⁰ exact at W=4; <2⁻²⁴ sampled at W=64 | `engine/audit_true_algorithm1.json` |
| Multi-round floor, W=4 | 2⁻⁴·⁸² at 22 rounds (full domain) | `engine/audit_true_algorithm1.json` |
| Algebraic degree | β₁ = 16, certificate at W=64 | `engine/explore_cascade_degree.py` |
| KAT | 5/5 blocks, incl. 0x6BBE30BB1D12DDD0 | `tests/`, `hardware/sim/` |
| Statistical tests | NIST 15/15 (97–100/100), BigCrush all-pass, PractRand 1 TiB clean | `data/` |
| C scalar (dual) | 22.1 Gbit/s @5 GHz (measured 10.42, 2026-08-10 build) | `code/bench_opt3.c`, `code/bench_opt3_20260810.txt` |
| C AVX-512 (8-way) | ≈96 Gbit/s @5 GHz (measured 46.26) | `code/bench_opt3.c` |
| FPGA (k=2 variant) | 5,915 LUT4 / 1,034 FF, 31.12 MHz, 2.0 Gbit/s, completed bitstream | `hardware/` |

## Audit record

The paper's audit record is mirrored here: see
[`docs/AUDIT_RECORD.md`](docs/AUDIT_RECORD.md). Every earlier claim
that did not survive verification was corrected and documented — the
v3.1 dead-key predecessor, the W=4 snapshot-semantics discrepancy, the
withdrawn half-entropy law, the W=8 multiple-testing artifact, and the
differential-trail zero-cancellation artifact.

## Reproducibility

Every number in the paper can be re-derived from this repository on a
stock laptop: the engine scripts print exact values into JSON, the KAT
harnesses verify bit-exactness against the published vector, and the
FPGA flow is fully open-source (Yosys → nextpnr → icepack). The
2026-08-13 statistical reruns (PractRand 1 TiB, BigCrush, NIST SP
800-22) were run against Algorithm 1 itself; the generators
(`code/gen_a1_stream.c`, `code/gen_nist_a1.c`, `code/testu01_v3.c`)
self-check the KAT before streaming.

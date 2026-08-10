# Throughput Optimization Study (2026-08-10)

Question: can Algorithm 1's throughput be improved **without losing
security**?

Answer: yes, at the implementation level. The final optimized build
(`code/bench_opt3.c`, bit-exact, self-checked) gains **+20–35 %**
scalar, **+19 %** AVX-512, and **near-linear multithreaded scaling**
(8 cores × 8 streams ≈ 249 Gbit/s measured). All security metrics are
untouched by construction: the round function and output function are
semantically identical; only instruction scheduling and thread
parallelism change.

## What was measured

`code/bench_opt3.c` (same machine — the paper's benchmark machine,
AMD Ryzen 9 8940HX at 2.395 GHz, WSL gcc 15 `-O3 -march=native`,
long-loop register-accumulator harness; all conversions to 5 GHz use
the paper's linear-ALU convention):

| Variant | Measured | @5 GHz |
|---|---|---|
| scalar baseline (`tempest_u64x2`) | 7.8–8.8 Gbit/s | ≈16–18 |
| **scalar pipe4b** (software pipeline) | **10.4–10.6 Gbit/s (+20–34 %)** | **≈22.1** |
| AVX-512 baseline (8 streams, dual) | 38.9 Gbit/s | ≈81 |
| **AVX-512 pipe4b** | **46.2–46.3 Gbit/s (+18.5–18.8 %)** | **≈96** |
| **MT scalar, 16 threads** | 53.4–57.4 Gbit/s | ≈120 |
| **MT AVX-512, 8 threads** | **246.8–248.9 Gbit/s** | **≈515** |

Bit-exactness: all variants byte-identical to the baseline over
50,000×4-round comparisons (self-checked in `main`); the checksum
`0f8fd3d3…` is identical across runs. KAT-compatible: the byte stream
is unchanged, so every statistical log and every security metric in
the paper applies verbatim to the optimized build.

## Why this works (and where the limit is)

- `make_output` (15-cycle andmix4 chain) and the next `round_fn` are
  **independent**: both depend only on the post-round state. The OoO
  core overlaps them once the source code interleaves them (pipe4:
  round(i+1) is emitted between the outputs of round(i)).
- The hard limit is the round function's serial chain (Phase C's
  five-level cascade, ~12 cycles) — that is cryptographic structure
  (each level doubles the algebraic degree; the cascade is what pushes
  DP below 2⁻²⁴). Reducing it would change the algorithm and invalidate
  the security claims. So the scalar ceiling is roughly
  (round chain + minimal output overlap) ≈ 30–40 % above baseline at
  best, and we measured about half of that.

## What does NOT change (security argument)

Nothing in the round function, key schedule, or output function
changes: same rotations, same constants, same AND placement, same
snapshot semantics. Only the instruction schedule differs. Therefore:
DP(1) = 2⁻⁵·⁹⁴²⁰ (W=4 exact), β₁ = 16, the Walsh values, the SAT grid,
the statistical logs, and the KAT vector all apply unchanged. The
optimized build is a drop-in replacement.

## Safe directions, now measured

1. **AVX-512**: native `rol` (1 cycle) + the same software pipeline
   → **+18.5 %** (46.2 Gbit/s, ≈96 @5 GHz). The Zen4 512-bit unit is
   the throughput ceiling per core.
2. **Multi-core**: each core runs an independent 8-way state
   (thread-level parallelism) — **near-linear scaling** (8 threads:
   248.9 Gbit/s, ≈515 @5 GHz). Zero algorithmic change.
3. **FPGA**: the k=2 Pareto-front variant (2.19 Gbit/s) is the
   framework's own area/throughput choice; a dual-output FPGA variant
   would double it but exceeds device capacity (honest statement in
   the paper).

## Status in the paper

The 2026-08-10 optimized figures are incorporated into
Table~XIII (scalar 10.6 / ≈22.1; AVX-512 46.2 / ≈96; MT 246.8 /
≈515), Table~IV (v3 dual ≈22.1 @5 GHz), the v4 comparison paragraph
(v4's throughput advantage was overtaken by the pipeline; its $a_1$
gain remains), and the AVX-512 port paragraph (pipeline + MT note).
All statements note bit-exactness and that every security metric
applies unchanged.

## Reproduction

```bash
gcc -O3 -march=native -o bench_opt2 bench_opt2.c
./bench_opt2        # prints bit-exactness check + all four variants
```

Log: `data/bench_opt2_20260810.txt`.

# Design Rationale: AM-SEV and the Tempest Instance

> Status: this document tracks the current, audited state of the design.
> Superseded claims (older throughput figures, MILP-based security
> statements, the half-entropy law) have been withdrawn and are listed
> in [AUDIT_RECORD.md](AUDIT_RECORD.md).

## 1. The AM-SEV framework in one paragraph

AM-SEV ("Security Efficiency Vector") is a metric theory over GF(2) for
AND-RX designs — round functions built from AND, XOR, and rotation only.
Its central result is the **Polar-Rank Theorem**: for a two-layer
AND-RX round (algebraic degree ≤ 2), the differential map
D_Δ(x) = Φ(x) ⊕ Φ(x⊕Δ) is affine, so the one-round differential
probability is exactly

    DP(Δ) = 2^(−rank B_Δ),

a polynomial-time linear-algebra computation at *any* width. This makes
the two-layer differential security of a design a *fact*, not an
estimate. The framework also provides:

- **The two-layer polar-rank barrier** — the quadratic shadow of our
  design has minimum polar rank exactly 3 at every width (W=64
  certificate in `engine/rank_certificate_w64.json`), so two-layer
  designs cannot reach strong differential security: cascades are
  necessary.
- **The Walsh-rank duality** — the maximum linear bias of the shadow is
  2^(−r_lin) with r_lin = 15 (sampled at W=64), making the linear side
  equally rank-determined.
- **The cascade degree law** — each AND-XOR-ROT cascade level doubles
  the algebraic degree (4 levels → degree 16, certificate at W=64: 1024
  top monomials pairwise distinct, no ANF cancellation).
- **The decomposition bound** — for the full (non-quadratic) design,
  DP(Δ) is sandwiched: 2^(−(n−rank)−2) ≤ DP(Δ) ≤ 2^(−rank), verified
  with zero violations over 1,995 differences at W=4
  (`engine/explore_decomp_bound.json`).
- **The Read-Word Polar-Rank Theorem** — a structural condition on the
  gate topology (every word read by exactly k ANDs with pairwise
  distinct (dst, rotation) columns) forces min rank = k, hence
  DP(1) = 2^(−k) exactly for the whole design class
  (`engine/readword_theorem.py`, 35 designs, 0 failures).

Where the wide trail strategy bounds, AM-SEV computes.

## 2. The Tempest v3 instance

Tempest v3 is a CSPRNG/DRBG with a 256-bit state (four 64-bit words),
22-round initialization, and one 128-bit output block per round. The
round function is a single combinational cloud of AND/XOR/ROT
operations:

1. **Snapshot** — copy (u,v,w,z); all following phases read the
   snapshot, so the four word equations run fully in parallel.
2. **Phase A** — XOR-ROT mixing with AND terms covering all word pairs
   (4 ANDs); constants break the all-1s fixed point.
3. **Phase A(lin)** — two snapshot ANDs covering (u,z) and (w,z).
4. **Phase B** — round key: pure-GF(2) affine update
   w ← w ⊕ rotl(w,19) ⊕ φ (nilpotent linear part: converges to a
   key-independent constant within 64 steps) with a nonlinear filter
   (one AND).
5. **Phase C** — the andmix4 cascade: two intra-word pre-mixes plus a
   4-level cross-word AND cascade on rotation pairs
   {(31,53),(17,43),(7,23),(5,19)} (differences {22,26,16,14}, chosen
   by an SEV-guided search over ~10¹² configurations); each level
   doubles the algebraic degree.
6. **Phase D** — cross-word mixing, branch number B_w ≥ 5.
7. **Output function** — t = u ⊕ rotl(v,32) ⊕ w ⊕ rotl(z,16), pre-mix,
   single-word andmix4 chain, fold; evaluated twice per clock on the
   rotated word pairs, giving 128 bits per round.

### Why these choices (design grammar)

- Every operation is on the SEV Pareto frontier (AND/XOR/ROT: one
  hardware unit each, no carry chains, SIMD-friendly) — the same
  property that makes the design FPGA-friendly (1 LUT per operation)
  and vectorization-friendly (8-way AVX-512).
- The snapshot semantics is what makes one round per clock possible in
  hardware and keeps the differential map analyzable.
- The cascade exists *because* of the two-layer barrier: the shadow's
  DP(1) = 2⁻³ is eliminated to 2⁻¹¹ (W=4, exact) and below 2⁻²⁴
  (W=64, sampled).

## 3. Security analysis (current, audited)

| Metric | Value | Status |
|---|---|---|
| DP(1), shadow | 2⁻³ exact, any width | Theorem (Polar-Rank + barrier) + certificate |
| DP(1), full design | 2⁻⁵·⁹⁴²⁰ exact at W=4; ≥15/≥22 sampled at W=8; <2⁻²⁴ at W=64 | Exact (W=4) / sampled |
| Multi-round DP | exact curve at W=4 (floor 2⁻⁵·⁶ by R≈12); W=64 R=2 <2⁻²⁴ | Exact (W=4) / sampled; no trail-sum bound |
| Algebraic degree | β₁ = 16 (W=4 exact, W=64 certificate); deg(Φ²) ≤ 4W | Theorem + certificate |
| Linear, shadow | max bias 2⁻¹⁵ (r_lin = 15, sampled at W=64) | Sampled; exact bit-level bound is future work |
| SAT preimage | R=1 trivial (<1 s); R=2: 47.6 s / 3.5 s / 559.5 s (W=8/12/16) | Measured |
| Key relevance τ | 0.6132 exact at W=4; alive at full width (witnessed) | Exact (W=4) / witnessed |
| Differential trails | min 6 active AND bits/round (W=4,12), 8 (W=8,16); 22-round single-trail DP ≤ 2⁻¹³²/2⁻¹⁷⁶ | MILP (R=1 exact; multi-round conservative) |

The full claims are reproducible from `engine/` (JSON datasets) and the
attack-surface audit scripts (`trail_diff.py`, `trail_lin.py`,
`state_attack.py`, `lin_scale.py`, `diff_sum.py`).

## 4. The AI engine

The engine instantiates the framework: a closed loop
spec → generate → L1 screen → L2 exact → fitness → feedback, where
generators (evolutionary search, LLM hook, human) are interchangeable
and **verification is the invariant**. The calibrated verifier stack
reproduces the historical v3.1 dead-key failure (τ = 0, a₁ = 0) exactly,
decides two-layer differential security at full width in milliseconds,
and ships a machine-checkable certificate tuple per accepted design.
The 11-generation design journey (Gen 1–3 float chaos → … → v3.1 dead
key → Algorithm 1) is documented in the paper; every rejected
generation failed a property the stack now detects in milliseconds.

## 5. Performance architecture

- **Scalar C (dual output)**: 6.4 Gbit/s measured on the same harness
  as ChaCha20 scalar (6.1) — the GF(2)-only vocabulary avoids carry
  chains.
- **AVX-512 (8-way)**: 35.5 Gbit/s measured (≈74 at 5 GHz
  normalization) — AND/ROT/XOR are all SIMD-native.
- **FPGA (iCE40 HX8K, k=2 Pareto-front variant)**: 5,915 LUT4 /
  1,034 FF, 34.21 MHz post-routing, ≈2.19 Gbit/s, with a completed
  bitstream (135 KB). The full-cascade variant (7,158 LUT4) fits but
  does not route at 98% density; a time-multiplexed reduction was
  measured and rejected (selector logic costs as much as the logic it
  replaces on a LUT4 FPGA).

All figures are measured on the same machine/harness; see
`code/bench_*` and `hardware/build/*.log`.

## 6. Relation to ADC-Bolt (legacy)

ADC-Bolt is the earlier non-cryptographic PRNG of this project (degree-2
design, 70 Gbit/s class). It is retained in `code/` for historical
continuity and as the degree-2 counterexample that motivated the
cascade analysis; it is **not** a security claim.

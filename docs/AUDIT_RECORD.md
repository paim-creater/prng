# Audit Record

This document is the honest ledger of this project: every claim that
did not survive verification, what replaced it, and where the evidence
lives. It exists because the project's own history proved that
self-verification catches errors — the final verification pass caught a
discrepancy in the project's *own* headline numbers, and everything
below is the result.

## 1. The v3.1 dead-key predecessor (reproduced, then fixed)

v3.1, the direct predecessor of Algorithm 1, had a key-update
identity making specific keys produce a trivial output ("dead key":
τ = 0, a₁ = 0). Statistical testing is insensitive to single-key
defects; the calibrated verifier stack detects the class exactly
(a₁ = 0 is decidable via a 2-SAT certificate, 1,024 clauses, W=64
witness of Hamming weight 1). The 11-generation design journey and
every rejection reason are documented in the paper.

## 2. W=4 snapshot-semantics discrepancy (withdrawn headline numbers)

The original W=4 enumerators ignored the snapshot semantics — the
headline W=4 numbers described a *different round function*. Caught by
a dual-source cross-check against the KAT-verified C semantics. The
correct values were recomputed with the correct semantics:

| Claim | Withdrawn | Replaced by |
|---|---|---|
| half-entropy law H∞ ≈ m/2 | withdrawn | exact W=4 value 0.37·m (5.94 bits) |
| W=4 DP values 7.93/7.80 | withdrawn | 5.9420/5.9447 (with-key/no-key) |
| cascade table 5.00/8.00/8.00/7.80/7.80 | withdrawn | re-audited values |
| state image 3,902 → 248 | withdrawn | 3,501 → 139 |
| τ = 1.000 at W=4 | withdrawn | 0.6132 (exact) |
| degree 15/14 | withdrawn | 16/15 (exact ANF) |
| throughput 15.7/76.5 Gbit/s | withdrawn | 6.4/35.5 Gbit/s (same harness, measured) |

The Polar-Rank Theorem was installed as the theory's core as part of
the same correction. The discrepancy, the withdrawals, and the
replacement dataset ship with the paper
(`engine/audit_true_algorithm1.json`, `engine/explore_state_image.json`).

## 3. Linear-side corrections (2026-08-09 audit)

- **W=8 linear "structure" was a multiple-testing artifact.** The
  2,000-mask maximum bias 2⁻⁶·¹ is null-consistent (expected maximum
  2⁻⁵·⁹⁷, p ≈ 0.56). The claim of a "real, measurable linear
  structure" at W=8 was corrected; the W=8 constant single-bit
  imbalance (bias 2⁻³·⁰⁰, every output bit of word w) is a mod-8
  rotation-degeneracy artifact that vanishes at W=16/32/64 (all
  null-consistent at 2²⁴ samples/mask; W=64 balanced at R=1 and R=22).
- **W=4 Walsh values re-audited** under two explicit conventions:
  input-mask-to-single-output-bit (shadow 2⁻²·⁰⁰⁰, cascade 2⁻⁵·⁶⁶⁷)
  and input×output-mask (shadow 2⁻¹·⁰⁰⁰, cascade 2⁻⁴·⁷¹²). The
  earlier 2⁻³·⁰⁰⁰/2⁻⁴·⁴¹⁵/2⁻⁵·³⁸⁵ (unrecorded convention) are
  superseded. Scripts: `trail_lin.py`, `lin_scale.py`.

## 4. Differential-trail model fix (2026-08-09)

The MILP trail model's AND over-approximation permitted a round's
output difference to cancel to zero (impossible in reality: each word
equation is x_w ← x_w ⊕ g(·), so the round is a permutation and
DP(Δ→0) = 0). Without a fix, R ≥ 2 returned the R=1 optimum total
(6/6/6 at W=4, 8/8/8 at W=8) — a zero-cancellation artifact. The model
now forces intermediate outputs nonzero; only the sound consequence is
quoted: every round's weight ≥ the R=1 per-round minimum (6 at W=4,12;
8 at W=8,16), so any 22-round trail has weight ≥ 132/176 and DP ≤
2⁻¹³²/2⁻¹⁷⁶ (conservative). Direct multi-round minima are not quoted.
Script: `trail_diff.py`.

## 5. Measurement protocol notes

- **W=64 differential summation requires full 256-bit packing.** A
  64-bit-shift packing truncates and reports spurious 2⁻²² hits; with
  the correct packing, R=1,2,22 show no collision in 2²⁴ pairs
  (DP ≤ 2⁻²⁴). Script: `diff_sum.py`.
- **Output-function inversion is exact and fast.** The SAT inversion
  of the 64-bit output function (inline-evaluation-verified CNF — the
  XOR Tseitin encoding is the checked-critical part) recovers the
  unique preimage t == t₀ in milliseconds; all linear stages have
  GF(2) rank 64 and no andmix4 level has a collision, so F is a
  bijection. The output function is not the state-recovery obstacle.
  Script: `state_attack.py` (mode `inv`).
- **Exploration scripts are kept, not hidden.** Scripts that record
  failures during the proof search (e.g. `verify_readword_theorem.py`)
  carry EXPLORATION-stage headers pointing to the final verification,
  and their JSON files state their status. The audit chain is
  complete.

## 6. W=8 anomalies are toy-width artifacts (verified, not asserted)

Both sides of the W=8 design freeze without mixing: the trail-optimal
difference has DP constant 2⁻⁷·⁰⁰ over R=1..6 (aggregation factor
2⁺¹→2⁺⁴¹), and the linear imbalance 2⁻³·⁰⁰ never decays — both from
mod-8 rotation degeneracy, and both vanish under the identical
protocol at W=16/32/64. Small widths do not carry iterative
extrapolation; only the one-round exact values and the rank-based
any-width statements do.

## 7. Honesty boundaries that remain open (stated in the paper)

- The linear side at full width is measurement-based; an exact
  bit-level linear bound is future work.
- No general multi-round trail-sum (packing) bound exists; the
  aggregation property bounds the aggregation factor (g ≤ M_Δ·2^(2r−n),
  verified at W=4, ≤2 sampled at W=8).
- Key aliveness is witnessed, not decided in general.
- The full-cascade FPGA bitstream does not exist (98% density does not
  route); only the k=2 Pareto-front variant has a completed bitstream.

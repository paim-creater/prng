# Rank-Topology Theory of Snapshot AND-RX Rounds
## (theory notes for the JCEN/JISA rewrite -- v0.9, 2026-09-06)

Status: computational core validated; proofs drafted. All numbers machine-verified.

## 0. Why this exists

The earlier Multi-Bit Rank Formula (rank(B_Delta) = k*t - M(Delta), M =
same-output aligned gate pairs) is **false as stated**. Concrete
counterexamples on the Algorithm-1 shadow at W=4 (Delta on word z):

    Delta_z = {0,2}:  formula 2, true rank 4
    Delta_z = {0,1,2}: formula 5, true rank 7

At W=8 on the same shadow, the formula fails in 35/400 random
single-word deltas.  The corrected theory below replaces it.

## 1. Setup

Round: SNAP + AND gates g = (d, a, ra, b, rb) meaning
  word d += rot(a, ra) & rot(b, rb), operands from the pre-round
  snapshot.  Two-layer => quadratic round map Phi.  Linear ops and
  trailing invertible mixing do not affect rank(B_Delta).

Notation: 4 words, width W.  Input bits (w, p), p in Z_W.  Delta with
supports P_w subset Z_W.

## 2. Theorem (Column Model) -- exact, all designs, all widths

For each column (input variable) (w,t):
  c_{(w,t)} = XOR over gates g reading word w of the unit vectors of the
  entries they fire into column (w,t).

Explicitly, for gate g=(d,a,ra,b,rb):
  - role a (word a active at p): entry at row (d, p+ra), column
    (b, p+ra-rb);
  - role b (word b active at p): entry at row (d, p+rb), column
    (a, p+rb-ra).
Then  rank(B_Delta) = GF(2)-rank of { c_{(w,t)} }.

Equivalently: B_Delta is the parity-reduced incidence matrix of the
bipartite contribution graph (rows = output bits, columns = input
variables, one edge per unit entry; even multiplicities cancel).

Verification: >25,000 random designs (dual-condition and generic),
W = 4, 8, single-bit + random multi-bit deltas: 0 mismatches vs
round-simulated ground truth.  Predictor is O(|G|*|supp D|*W).

## 3. Definition (unit-column regime)

Delta is in the unit-column regime iff every column (w,t) receives at
most one unit entry, i.e. all c_{(w,t)} are unit vectors or zero.
For a single-word Delta on word x define the *offset* of gate g reading
x:  delta_g = rot(x in g) - rot(partner in g)  (mod W).
Entries of g land at columns (partner word, p + delta_g), p in P_x.

Firing into one column from two pairs (g,p),(g',p') happens iff
partner(g) = partner(g') = v and  p - p' = delta_{g'} - delta_g  (mod W).
Hence:  unit regime  <=>  (P_x - P_x) intersect {delta_g - delta_{g'} :
g,g' read x with common partner} = {0}  (no nonzero difference is an
active-position difference).

## 4. Theorem (Touched-Rows Law) -- unit regime

In the unit-column regime,
    rank(B_Delta) = # { distinct output rows hit by at least one entry }
                  = N - sum_r (d_r - 1),
where N = number of entries and d_r = multiplicity of entries at output
row r.

Proof sketch: unit columns are unit vectors; equal columns iff they
touch the same row; distinct unit vectors are independent; hence the
rank equals the number of distinct touched rows.

Verification:
  - Algorithm-1 shadow W=4: 40/40 single-word multi-bit deltas.
  - Algorithm-1 shadow W=8: 400/400 random single-word deltas.
  - Random designs (dual + generic, W=8, k=3): 1622/1622 in unit regime
    (2050 further cases leave the unit regime -- the condition is
    genuinely restrictive; column-reduction then applies, Section 6).

## 5. Theorem (Clean Counting) -- full regime sufficient conditions

If additionally all fired rows are pairwise distinct (no two entries
share an output position), then rank(B_Delta) = N = k*t (single-word,
k gates per word).

Design-level sufficient condition for *every* single-word Delta:
per (x, v) pair at most one gate reading x with partner v, and per
output word d the rotations used are distinct -- i.e. the Read-Word
dual conditions.  Single-bit deltas need only: pairwise distinct
offsets per (x,v) and distinct (d, rot_x) pairs; then rank = k exactly
(Read-Word single-bit theorem becomes a corollary, with a one-line
proof via the column model).

The old formula's errors: it counts alignments by OUTPUT word; rank
loss actually occurs at the INPUT (column) side (shared rows between
columns of the same input word caused by equal offsets) and through
full (row,col) coincidences.  Both mechanisms are invisible to M.

## 6. Outside the unit regime

c_{(w,t)} = XOR of unit vectors: general GF(2) rank of the parity
incidence matrix.  No universal closed form (GF(2) rank is not a
combinatorial invariant of the graph in general), but:
  - exact evaluation via the column model is O(W * n * rank);
  - the Design Prescription: choose gate offsets pairwise distinct per
    (x, partner) and output rotations distinct per (d, x) => the whole
    class sits in the clean-counting regime for every single-word Delta
    at every width.

## 7. What this means for the design (Tempest v3 shadow)

Verified structure of the Algorithm-1 shadow (W=4 exhaustive, W=8
random): the 3 gates reading any word x have pairwise distinct partner
words, so the offset condition holds and the unit regime covers EVERY
single-word Delta (unit regime: 40/40 at W=4; 400/400 at W=8).  Hence
by Theorem 4, rank(B_Delta) = #touched rows for every single-word
Delta, and the W=4 "barrier min rank 3" is the t=1 instance.

CLOSED FORM ACHIEVED (2026-09-06, verified at three widths):

  rank(B_Delta) = 3t - |P n (P+2)| * [x = z],   single-word Delta on x
  (P+2 cyclic mod W; the only row-coincidence source is the pair of
  u-writing gates reading z with rotations 25 and 23, whose difference
  2 is width-independent)

Verification:
  - W=4: exhaustive, all 56 single-word differences, 0 mismatches
  - W=8: 5,000 random single-word differences, 0 mismatches
  - W=64: 120 sampled differences via an independent pure-Python
    simulator (verify_rank_formula_w64.py, no numpy), 0 mismatches
  - certificates: rank_formula_w64_cert.json, multibit_correction_cert.json

The W=4 toy-width foldings (rotations coincide mod 4) create NO
additional coincidences beyond the cyclic-distance-2 count -- the
formula is exact already at W=4.  The Multi-Bit corollary in all prior
manuscript versions is superseded by this theorem family, with the
counterexamples recorded as an audit note.

## 8. Reproducibility

- rank_column_model.py       column model + predictor (25k+ checks)
- phase2_defect_study.py     defect analysis (dual + generic)
- multibit_correction_cert.json  W=4 shadow counterexamples (6)
- shadow W=8: 400/400 row-law, 35 old-formula failures (this session)
- touched-rows random-class test: 1622/1622 (this session)

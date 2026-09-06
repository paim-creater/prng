# -*- coding: utf-8 -*-
"""rank_column_model.py -- Phase 1 of the Rank-Topology Theory.

Goal: for ANY two-layer (quadratic) snapshot AND-RX round, express the
polar-form columns of B_Delta directly from the gate topology, without
simulating the round.  This gives (i) an O(#gates * |supp Delta| * W)
rank predictor, and (ii) the structural object needed to prove
width-independent rank theorems (the Read-Word / Multi-Bit formulas are
the k-regular special case).

Model.  A round is a set of AND gates g = (d, a, ra, b, rb): output
word d receives rot(a, ra) & rot(b, rb), operands read from the
pre-round snapshot (two-layer = quadratic round map; linear X3/CONST
ops never touch the polar form B_Delta, and trailing invertible linear
mixing preserves rank).

Polar-form columns.  For input bit positions p with Delta_a[p]=1, gate g
contributes the unit matrix entry  B[(d, p+ra), (b, p+ra-rb)] = 1
(and symmetrically with a<->b, ra<->rb).  Hence column (w,t) equals

  c_{(w,t)} = XOR over gates g=(d,a,ra,w,rb) with Delta_a[t+rb-ra]=1
                  of e_{(d, t+rb)}
              XOR over gates g=(d,w,ra,b,rb) with Delta_b[t+ra-rb]=1
                  of e_{(d, t+ra)}

and rank(B_Delta) = GF(2) rank of { c_{(w,t)} : w in 4 words, t in W }.

This module validates the model against the round-simulating ground
truth rank_of_delta on random designs, both with the dual column
condition (Read-Word regime) and without (generic regime, where
aligned duplicates / support overlaps occur).
"""
import numpy as np
from readword_theorem import build_design
from min_shadow_rank import rank_of_delta

WORDS = {'u': 0, 'v': 1, 'w': 2, 'z': 3}


def gates_from_ops(ops):
    """Extract (d, a, ra, b, rb) gate tuples (word indices) from a DSL
    program.  Only AND ops with snap=1 contribute to the quadratic
    polar form in the two-layer regime; X3/CONST/SNAP are ignored."""
    gs = []
    for op in ops:
        if op[0] != 'AND':
            continue
        _, d, a, b, ra, rb, snap = op
        if int(snap) != 1:
            raise ValueError('live-operand AND outside two-layer regime')
        gs.append((WORDS[d], WORDS[a], int(ra), WORDS[b], int(rb)))
    return gs


def build_random_design(W, k, rng, dual_cond=False):
    """Random design: SNAP + k AND reads per word (+ optional Phase-D
    style trailing linear mixing when dual_cond, to exercise the
    M-invariant case)."""
    ops, quota = build_design(W, k, rng)
    assert not any(quota.values()), 'builder failed to meet quota'
    if not dual_cond:
        # generic regime: random rotations, duplicates allowed
        ops, quota = build_design(W, k, rng)
        # rebuild without conditions: directly place k random gates/word
        words = list(WORDS)
        gates = []
        for w in words:
            for _ in range(k):
                gates.append(('AND',) + _rand_gate(W, rng, words))
        ops = [('SNAP',)] + [tuple(g) for g in gates]
    return ops


def _rand_gate(W, rng, words):
    d = words[int(rng.integers(0, 4))]
    a = words[int(rng.integers(0, 4))]
    b = words[int(rng.integers(0, 4))]
    ra = int(rng.integers(1, W))
    rb = int(rng.integers(1, W))
    return (d, a, b, ra, rb, 1)


def predict_columns(W, gates, delta_int):
    """Return the predicted n=4W polar columns c_{(w,t)} (each an int
    of n bits), per the unit-entry accumulation model."""
    n = 4 * W
    MK = (1 << W) - 1
    # column accumulator: list of n ints, col index (w*W + t)
    cols = [0] * n
    supp = []
    for wi in range(4):
        dw = (delta_int >> (wi * W)) & MK
        if dw:
            supp.append((wi, [p for p in range(W) if (dw >> p) & 1]))
    for (d, a, ra, b, rb) in gates:
        # contribution of active bits of word a
        for (wa, pa) in supp:
            if wa != a:
                continue
            for p in pa:
                q = (p + ra) % W
                row = d * W + q
                col = b * W + ((q - rb) % W)
                cols[col] ^= 1 << row
        # contribution of active bits of word b
        for (wb, pb) in supp:
            if wb != b:
                continue
            for p in pb:
                q = (p + rb) % W
                row = d * W + q
                col = a * W + ((q - ra) % W)
                cols[col] ^= 1 << row
    return cols


def gf2_rank_cols(cols, n):
    """GF(2) rank of a list of n-bit column ints (same convention as
    min_shadow_rank.gf2_rank)."""
    mat = np.zeros((len(cols), n), dtype=np.uint8)
    for j, c in enumerate(cols):
        for b in range(n):
            if (c >> b) & 1:
                mat[j, b] = 1
    r = 0
    piv = [None] * n
    for j in range(len(cols)):
        x = mat[j]
        for b in range(n):
            if x[b]:
                if piv[b] is None:
                    piv[b] = j
                    r += 1
                    break
                x ^= mat[piv[b]]
    return r


def validate(W, k, dual_cond, n_designs, n_deltas, seed=2026):
    rng = np.random.default_rng(seed)
    bad = tot = 0
    for di in range(n_designs):
        ops, quota = build_design(W, k, rng)
        if any(quota.values()):
            continue
        if not dual_cond:
            # generic: random replacement
            ops = [('SNAP',)] + [tuple(('AND',) + _rand_gate(W, rng, list(WORDS)))
                                 for _ in range(4 * k)]
        gates = gates_from_ops(ops)
        n = 4 * W
        deltas = list(range(1, n + 1))  # all single-bit
        r2 = np.random.default_rng(seed + di)
        deltas += [int(r2.integers(1, 1 << 32)) for _ in range(n_deltas)]
        for delta in deltas:
            delta &= (1 << (4 * W)) - 1
            if delta == 0:
                continue
            tot += 1
            gt, _ = rank_of_delta(W, ops, delta)
            pr = gf2_rank_cols(predict_columns(W, gates, delta), n)
            if pr != gt:
                bad += 1
                if bad <= 3:
                    print(f'  MISMATCH W={W} k={k} dual={dual_cond} '
                          f'delta={delta:x} pred={pr} truth={gt}')
    return bad, tot


def main():
    print('== Read-Word regime (dual column condition) ==')
    for W in (4, 8):
        for k in (1, 2, 3):
            bad, tot = validate(W, k, True, 10, 200)
            print(f'W={W} k={k}: {bad}/{tot} mismatches')
    print('== Generic regime (random rotations, duplicates allowed) ==')
    for W in (4, 8):
        for k in (1, 2, 3):
            bad, tot = validate(W, k, False, 10, 300)
            print(f'W={W} k={k}: {bad}/{tot} mismatches')


if __name__ == '__main__':
    main()

# -*- coding: utf-8 -*-
"""phase2_defect_study.py -- discover the exact rank formula.

Phase 1 established the column-accumulation model (rank_column_model.py,
25k+ cases, 0 mismatches).  Phase 2 asks: when does rank(B_Delta) have a
closed form?  Candidate (paper's Multi-Bit formula): for Delta supported
on ONE word w with t active bits and k regular gates/word,
   rank = k*t - M(Delta)
where M counts aligned gate pairs.  This study checks that formula and
searches for any additional correction terms (same-column multi-entry
overlaps, support equalities across columns, cross-word effects).
"""
import numpy as np
from rank_column_model import (predict_columns, gf2_rank_cols, gates_from_ops)
from readword_theorem import build_design
from min_shadow_rank import rank_of_delta


def w_rot(g, w):
    """Rotation applied to word w inside gate g=(d,a,ra,b,rb)."""
    if g[1] == w:
        return g[2]
    if g[3] == w:
        return g[4]
    return None


def aligned_pairs(gates_w, W, dw_bits):
    """Paper's M(Delta): pairs of gates g!=g' reading word w (any role)
    with same output word and aligned active positions p,p' with
    p + r_{w,g} == p' + r_{w,g'} (mod W), counting each (g,g',p,p')
    alignment once."""
    M = 0
    for i in range(len(gates_w)):
        for j in range(len(gates_w)):
            if i == j:
                continue
            gi, gj = gates_w[i], gates_w[j]
            rw_i = w_rot(gi, 0)
            rw_j = w_rot(gj, 0)
            if rw_i is None or rw_j is None:
                continue
            if gi[0] != gj[0]:          # same output word
                continue
            for p in dw_bits:
                for pp in dw_bits:
                    if (p + rw_i) % W == (pp + rw_j) % W:
                        M += 1
    return M


def study(W, k, n_designs, seed=11):
    rng = np.random.default_rng(seed)
    rows = []
    for di in range(n_designs):
        ops, quota = build_design(W, k, rng)
        if any(quota.values()):
            continue
        gates = gates_from_ops(ops)
        # generic regime too (some aligned pairs present)
        if di % 2 == 1:
            from rank_column_model import _rand_gate
            ops = [('SNAP',)] + [tuple(('AND',) + _rand_gate(W, rng, list('uvwz')))
                                 for _ in range(4 * k)]
            gates = gates_from_ops(ops)
        # single-word deltas with 1..3 active bits on word 0
        for t in (1, 2, 3):
            for trial in range(20):
                pos = sorted(rng.choice(W, t, replace=False))
                dw = sum(1 << p for p in pos)
                delta = dw  # word 0 only
                gt, _ = rank_of_delta(W, ops, delta)
                cols = predict_columns(W, gates, delta)
                pr = gf2_rank_cols(cols, 4 * W)
                assert pr == gt, (W, k, delta, pr, gt)
                n_cols = sum(1 for c in cols if c)
                n_entries = sum(bin(c).count('1') for c in cols)
                M = aligned_pairs([g for g in gates if w_in(g, 0)], W, pos) \
                    if k >= 2 else 0
                cand = k * t - M
                rows.append((di % 2 == 1, k, t, delta, gt, cand,
                             gt - cand, n_cols, n_entries))
    return rows


def w_in(g, wi):
    return g[1] == wi or g[3] == wi


def main():
    W = 8
    rows = study(W, 3, 12)
    print(f'{"gen":4}{"k":3}{"t":3}{"rank":6}{"kt-M":7}{"diff":6}{"ncol":6}{"nent":6}')
    mism = [r for r in rows if r[5] != r[4]]
    ok = [r for r in rows if r[5] == r[4]]
    print(f'{len(rows)} cases; formula kt-M exact in {len(ok)}, '
          f'mismatches: {len(mism)}')
    for r in mism[:12]:
        print(r)
    if mism:
        print('---- mismatching rows: gen, k, t, delta, rank, kt-M, diff, '
              'n_cols, n_entries')
    # also report distribution of (rank - (kt-M)) when nonzero
    from collections import Counter
    print(Counter(r[4] - r[5] for r in rows))


if __name__ == '__main__':
    main()

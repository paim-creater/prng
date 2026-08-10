# -*- coding: utf-8 -*-
"""explore_round_dp_curve.py — multi-round exact DP curve at W=4 (full domain).

Answers three questions for the third upgrade cycle:

  Q1 (the multi-round gap): what is the exact multi-round DP_R(delta) for
     R = 1..22 at W=4 (full 2^16 domain)?  Does the "polar-rank barrier
     product" DP_R <= 2^(-3R) hold at every R, and how does the cascade
     elimination law (shadow 2^-3 -> full design ~2^-11 at 2 rounds)
     appear in the curve?

  Q2 (rank-trail check): for a single-bit delta, track the dominant
     output difference c_k per round and the one-round polar rank
     r_k = rank(B_{c_k}) of the round's differential map at that
     difference; compare sum r_k against -log2 DP_R(delta).

  Q3 (saturation): at which R does DP_R saturate (bounded below by the
     2^-16 floor of the 16-bit state)?

Method: the R-round truth table T_R = Phi^R (all 2^16 states, snapshot
semantics, evolving Weyl key) is computed once and shared by all
differences; DP_R(delta) = max_c #{s : T_R[s^delta] ^ T_R[s] = c} / 2^16.
The interpreter is imported from audit_true_algorithm1.py (cross-checked
against the DSL / scalar C port).
"""
import numpy as np
import json, time, sys

sys.path.insert(0, '.')
from audit_true_algorithm1 import apply_round_snap, anf_degree, W, MASK, NIN
from cipher import tempest_a1_round_program

ROUNDS = 22


def multi_round_table(R, ops, wv0=np.uint16(0x8)):
    """T_R[s] = Phi^R(s) over the full 2^16 domain, snapshot semantics."""
    codes = np.arange(NIN, dtype=np.uint16)
    st = np.zeros((NIN, 4), dtype=np.uint16)
    for wi in range(4):
        st[:, wi] = (codes >> (wi * W)) & MASK
    wv = [wv0, np.uint16(0)]
    for _ in range(R):
        st, wv = apply_round_snap(st, ops, wv)
    return (st[:, 0] | (st[:, 1] << W) | (st[:, 2] << (2 * W))
            | (st[:, 3] << (3 * W))).astype(np.uint16)


def dp_of(T, delta):
    """DP(delta) of the map T, exact over the full domain.
    D(s) = T[s^delta] ^ T[s]  --  XOR on the INPUT INDEX, then table."""
    d = T[np.arange(NIN, dtype=np.uint16) ^ np.uint16(delta)] ^ T
    c = np.bincount(d.astype(np.int64), minlength=NIN)
    return int(c.max()), int(c[0])          # (max count, DP0 count)


def linear_part_rank(D):
    """rank of the affine part of a differential map D(s) over the full
    domain: the polar matrix B has columns B e_j = D(e_j) ^ D(0), where
    e_j is the state with bit j set = domain index 2^j.  GF(2) rank."""
    D0 = D[0]
    M = np.zeros((16, 16), dtype=np.uint8)     # M[j,:] = column j (16 bits)
    for j in range(16):
        cj = D[np.uint16(1 << j)] ^ D0
        M[j, :] = ((cj >> np.arange(16)) & 1).astype(np.uint8)
    rank = 0
    for col in range(16):
        piv = np.nonzero(M[rank:, col])[0]
        if len(piv) == 0:
            continue
        piv = rank + piv[0]
        M[[rank, piv]] = M[[piv, rank]]
        M[rank + 1:] ^= M[rank][None, :] * M[rank + 1:, col][:, None]
        rank += 1
    return rank


def main():
    t0 = time.time()
    ops = tempest_a1_round_program()
    deltas = [0x1, 0x2, 0x4, 0x8, 0x10, 0x20, 0x40, 0x80,
              0x100, 0x200, 0x400, 0x800, 0x1000, 0x2000, 0x4000, 0x8000,
              0xFFFF, 0x3333, 0x5A5A]
    res = {'meta': 'W=4 full-domain exact DP_R for Algorithm 1 (snapshot '
                   'semantics, evolving Weyl key)', 'rounds': ROUNDS,
           'rows': []}

    # precompute per-round tables
    T = [None] * (ROUNDS + 1)
    for R in range(1, ROUNDS + 1):
        T[R] = multi_round_table(R, ops)
        print(f'T_{R} done ({time.time()-t0:.0f}s)', flush=True)

    # Q1: DP_R curve per delta; also single-bit max
    sb_max = np.zeros(ROUNDS + 1, dtype=float)
    for R in range(1, ROUNDS + 1):
        row = {'R': R}
        dmax, dmax_delta = 0, None
        for d in deltas:
            m, m0 = dp_of(T[R], d)
            dl2 = -np.log2(m / NIN)
            if dl2 > dmax:
                dmax, dmax_delta = dl2, d
        row['-log2 DP_R max'] = round(dmax, 3)
        row['at delta'] = hex(dmax_delta)
        row['barrier product 3R'] = 3 * R
        # single-bit deltas only
        m, _ = dp_of(T[R], 0x1)
        row['-log2 DP_R(0x1)'] = round(-np.log2(m / NIN), 3)
        sb = [ -np.log2(dp_of(T[R], d)[0] / NIN) for d in
               [0x1, 0x2, 0x4, 0x8, 0x10, 0x20, 0x40, 0x80,
                0x100, 0x200, 0x400, 0x800, 0x1000, 0x2000, 0x4000, 0x8000] ]
        row['-log2 min over single-bit'] = round(min(sb), 3)
        row['-log2 max over single-bit'] = round(max(sb), 3)
        res['rows'].append(row)
        print(f'R={R:2d}: DP_R max -log2 = {row["-log2 DP_R max"]:.3f} '
              f'(3R={3*R})  0x1: {row["-log2 DP_R(0x1)"]:.3f}',
              flush=True)

    # Q2: rank trail for delta = 0x1 (dominant-difference path)
    trail = []
    delta = 0x1
    dprev = None
    for k in range(1, ROUNDS + 1):
        # one-round differential map at the tracked difference, using the
        # round-k Weyl context: rebuild table from k-1 rounds then one more
        codes = np.arange(NIN, dtype=np.uint16)
        st = np.zeros((NIN, 4), dtype=np.uint16)
        for wi in range(4):
            st[:, wi] = (codes >> (wi * W)) & MASK
        wv = [np.uint16(0x8), np.uint16(0)]
        for _ in range(k - 1):
            st, wv = apply_round_snap(st, ops, wv)
        if dprev is not None:
            # recompute Phi^k(s^d)^Phi^k(s) directly (two paths) for rank
            stA = st.copy()
            # s ^ d applied at input encoding
            stA[:, 0] ^= np.uint16(dprev & 0xF)
            stA[:, 1] ^= np.uint16((dprev >> 4) & 0xF)
            stA[:, 2] ^= np.uint16((dprev >> 8) & 0xF)
            stA[:, 3] ^= np.uint16((dprev >> 12) & 0xF)
            stB, wv2 = apply_round_snap(stA, ops, wv.copy())
            st, wv = apply_round_snap(st, ops, wv)
            Dk = (stB[:, 0] | stB[:, 1] << W | stB[:, 2] << (2 * W)
                  | stB[:, 3] << (3 * W)).astype(np.uint16) ^ \
                 (st[:, 0] | st[:, 1] << W | st[:, 2] << (2 * W)
                  | st[:, 3] << (3 * W)).astype(np.uint16)
            rk = linear_part_rank(Dk)
            c = np.bincount(Dk.astype(np.int64), minlength=NIN)
            dpk = -np.log2(c.max() / NIN)
            dmax = int(np.argmax(c))
            trail.append({'round': k, 'delta': hex(dprev), 'rank': rk,
                          '-log2 DP_k': round(dpk, 3), 'dominant': hex(dmax)})
            print(f'trail R={k}: delta={hex(dprev)} rank={rk} '
                  f'DP_k -log2={dpk:.3f} dom={hex(dmax)}', flush=True)
            dprev = dmax
        else:
            dprev = 0x1
    res['rank_trail_0x1'] = trail
    res['elapsed_s'] = round(time.time() - t0, 1)

    with open('explore_round_dp_curve.json', 'w') as f:
        json.dump(res, f, indent=1, default=str)
    print(f'wrote explore_round_dp_curve.json ({time.time()-t0:.0f}s)')


if __name__ == '__main__':
    main()

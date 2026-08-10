# -*- coding: utf-8 -*-
"""audit_cascade_rank.py — AUDIT + THEORY discovery script.

Recomputes the cascade-truncation DDT table with the SNAPSHOT-AWARE
interpreter (explore_ddt.py semantics), full domain, no-key, and compares
with (a) the paper's stated table (5.00, 8.00, 8.00, 7.80, 7.80),
(b) the engine's own cascade_full_domain.json (3.00, 6.30, 8.00, 7.80, 7.80),
which used a non-snapshot-aware interpreter.

Additionally tests the AFFINE-DIFFERENTIAL theorem on quadratic variants:
for round functions of algebraic degree <= 2, the differential map
D_Delta(s) = Phi(s^Delta) ^ Phi(s) is AFFINE, hence
    DP(Delta) = 2^{-rank(B_Delta)},  B_Delta = [D(e_j) ^ D(0)]_j,
EXACTLY.  If the variant is quadratic this must hold for ALL 65535 deltas.

Also tests the AGGREGATION inequality DP(Delta) >= 2^{-r_lin(Delta)}
(r_lin = rank of the linear part of D_Delta) on all variants.
"""
import numpy as np
import json, time, sys

from cipher import tempest_a1_round_program

W = 4
MASK = np.uint16((1 << W) - 1)
IDX = {'u': 0, 'v': 1, 'w': 2, 'z': 3}
NIN = 1 << (4 * W)          # 2^16
IDX_AR = np.arange(NIN, dtype=np.uint16)


def rotl16(x, r):
    r %= W
    return np.uint16(((x << r) & MASK) | (x >> (W - r)))


def apply_round_snap(st, ops):
    """Snapshot-aware interpreter (same semantics as explore_ddt.py)."""
    snap = None
    for op in ops:
        t = op[0]
        if t == 'SNAP':
            snap = st.copy()
        elif t == 'X3':
            w, a, b, r1, r2, sf = IDX[op[1]], IDX[op[2]], IDX[op[3]], op[4], op[5], op[6]
            av = rotl16((snap if sf else st)[:, a], r1)
            bv = rotl16((snap if sf else st)[:, b], r2)
            st[:, w] = (st[:, w] ^ av ^ bv) & MASK
        elif t == 'AND':
            w, a, b, r1, r2, sf = IDX[op[1]], IDX[op[2]], IDX[op[3]], op[4], op[5], op[6]
            av = rotl16((snap if sf else st)[:, a], r1)
            bv = rotl16((snap if sf else st)[:, b], r2)
            st[:, w] = (st[:, w] ^ (av & bv)) & MASK
        elif t == 'A3':
            w, r1, r2, r3, r4 = IDX[op[1]], op[2], op[3], op[4], op[5]
            v = st[:, w]
            st[:, w] = (v ^ rotl16(v, r1) ^ rotl16(v, r2)
                        ^ (rotl16(v, r3) & rotl16(v, r4))) & MASK
        elif t == 'A2':
            w, r1, r2 = IDX[op[1]], op[2], op[3]
            v = st[:, w]
            st[:, w] = (v ^ rotl16(v, r1) ^ rotl16(v, r2)) & MASK
        elif t == 'CONST':
            w, c = IDX[op[1]], op[2] & 0xF
            st[:, w] = (st[:, w] ^ np.uint16(c)) & MASK
        elif t in ('WEYL', 'NLFILT', 'KEY'):
            pass  # no-key variants
        else:
            raise ValueError(t)
    return st


def truncate_at_levels(ops, k, include_premix=True):
    """Keep ops up to the start of cascade level k (0 = before Level 1).
    include_premix=False drops the A3/A2 premix ops as well (pure quadratic)."""
    a3_idx = [i for i, op in enumerate(ops) if op[0] == 'A3']
    snap_idx = [i for i, op in enumerate(ops) if op[0] == 'SNAP']
    first_level = min(i for i in snap_idx if i > max(a3_idx))
    level_starts = [i for i in snap_idx if i >= first_level][:4]
    cut = level_starts[k] if k < 4 else len(ops)
    if not include_premix:
        cut = min(cut, min(a3_idx))
    return ops[:cut]


def tabulate(ops):
    codes = IDX_AR
    st = np.zeros((NIN, 4), dtype=np.uint16)
    for wi in range(4):
        st[:, wi] = (codes >> (wi * W)) & MASK
    st = apply_round_snap(st, ops)
    return (st[:, 0] | (st[:, 1] << W) | (st[:, 2] << (2 * W))
            | (st[:, 3] << (3 * W))).astype(np.uint16)


def gf2_rank(mat):
    """Rank of an n x n GF(2) matrix given as a list of int rows (n<=16)."""
    n = len(mat)
    rows = [int(r) for r in mat]
    rank = 0
    for col in range(n):
        piv = None
        for i in range(rank, n):
            if (rows[i] >> col) & 1:
                piv = i
                break
        if piv is None:
            continue
        rows[rank], rows[piv] = rows[piv], rows[rank]
        for i in range(n):
            if i != rank and ((rows[i] >> col) & 1):
                rows[i] ^= rows[rank]
        rank += 1
    return rank


def full_analysis(T, label):
    """Full-domain: per-Delta DP, DDT max, r_lin, aggregation check,
    and (if quadratic) polar rank identity check."""
    res = {'label': label}
    t0 = time.time()
    ddt_max = 0
    agg_fail = 0
    agg_exact_vals = []
    rank_ident_fail = 0
    rank_mismatch_first = None
    rank_hist = {}
    rlin_hist = {}
    min_rank_d = None
    min_rank = 99
    # columns for polar/linear part
    D0 = T ^ T[0]               # D(0) = Phi(0^Delta)... careful below
    for di in range(1, NIN):
        dT = T[IDX_AR ^ np.uint16(di)] ^ T
        counts = np.bincount(dT.astype(np.int64), minlength=NIN)
        m = counts.max()
        if m > ddt_max:
            ddt_max = m
        # linear part rank: columns D(e_j) ^ D(0)
        e0 = dT[0]
        cols = [(dT[1 << j] ^ e0) for j in range(16)]
        r_lin = gf2_rank(cols)
        rlin_hist[r_lin] = rlin_hist.get(r_lin, 0) + 1
        dp = m / NIN
        if dp < 2.0 ** (-r_lin) - 1e-12:
            agg_fail += 1
            if len(agg_exact_vals) < 10:
                agg_exact_vals.append({'delta': di, 'r_lin': r_lin,
                                       'dlog2dp': -np.log2(dp)})
        if m > 0:
            if m != (1 << (16 - r_lin)):
                rank_ident_fail += 1
                if rank_mismatch_first is None:
                    rank_mismatch_first = {'delta': int(di), 'r_lin': int(r_lin),
                                           'fiber': int(m), 'expected': 1 << (16 - int(r_lin))}
    res['ddt_max_dlog2'] = round(-np.log2(ddt_max / NIN), 4)
    res['agg_fail_count'] = agg_fail
    res['agg_fail_examples'] = agg_exact_vals
    res['rlin_hist'] = {int(k): int(v) for k, v in rlin_hist.items()}
    res['fiber_identity_fail'] = rank_ident_fail
    res['fiber_identity_first_mismatch'] = rank_mismatch_first
    res['secs'] = round(time.time() - t0, 1)
    print(f'{label}: -log2 DDTmax={res["ddt_max_dlog2"]:.4f}  '
          f'aggregation fails={agg_fail}  fiber-identity fails={rank_ident_fail} '
          f'({res["secs"]}s)', flush=True)
    return res


def main():
    base = tempest_a1_round_program()
    out = {}
    for k in range(5):
        ops = truncate_at_levels(base, k, include_premix=True)
        T = tabulate(ops)
        out[f'k{k}_withpremix'] = full_analysis(T, f'k={k} (with premix)')
    ops = truncate_at_levels(base, 0, include_premix=False)
    T = tabulate(ops)
    out['k0_nopremix'] = full_analysis(T, 'k=0 no-premix (pure quadratic)')
    with open('audit_cascade_rank.json', 'w') as f:
        json.dump(out, f, indent=1)
    print('done -> audit_cascade_rank.json')


if __name__ == '__main__':
    main()

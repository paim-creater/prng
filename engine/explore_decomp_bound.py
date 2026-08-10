# -*- coding: utf-8 -*-
"""explore_decomp_bound.py — the Differential Decomposition Bound.

For the FULL cascade design at W=4 (full domain), every differential
map D_Delta(s) = Phi(s^Delta) ^ Phi(s) is decomposed uniquely as
D = L ^ R with L affine (L(s) = B s ^ D(0), B the linear part) and R
residual (no linear monomials).  The theorem to verify:

  |D-image| <= 2^(n-rank(B)) * |R-image|,  hence
  DP(Delta) >= 2^(-rank(B)) / |R-image|,
  i.e.  -log2 DP <= rank(B) + log2 |R-image|.

So the aggregation factor g = DP * 2^rank(B) is BOUNDED by
|R-image| — the measured Aggregation Property becomes a theorem with
a computable constant.  We verify over a large sampled difference set
and report the tightness (m = log2 |R-image| vs realised g).

Method: snapshot semantics interpreter (audit_true_algorithm1),
full-domain table T; per delta: D from T, linear part from 17 points
(D(e_j) ^ D(0)), residual R = D ^ L over the full domain, image sizes
by bincount/unique, rank by GF(2) elimination.
"""
import numpy as np
import json, time, sys

sys.path.insert(0, '.')
from audit_true_algorithm1 import apply_round_snap, W, MASK, NIN
from cipher import tempest_a1_round_program


def round_table(ops, R=1, wv0=np.uint16(0x8)):
    codes = np.arange(NIN, dtype=np.uint16)
    st = np.zeros((NIN, 4), dtype=np.uint16)
    for wi in range(4):
        st[:, wi] = (codes >> (wi * W)) & MASK
    wv = [wv0, np.uint16(0)]
    for _ in range(R):
        st, wv = apply_round_snap(st, ops, wv)
    return (st[:, 0] | (st[:, 1] << W) | (st[:, 2] << (2 * W))
            | (st[:, 3] << (3 * W))).astype(np.uint16)


def linear_part_rank_and_map(D, cols_out=None):
    """B columns = D(e_j)^D(0); rank + full linear map L(s)=B s ^ D(0)."""
    D0 = D[0]
    cols = np.zeros((16,), dtype=np.uint16)
    for j in range(16):
        cols[j] = D[np.uint16(1 << j)] ^ D0
    M = np.zeros((16, 16), dtype=np.uint8)
    for j in range(16):
        M[j, :] = ((cols[j] >> np.arange(16)) & 1).astype(np.uint8)
    r = 0
    for col in range(16):
        piv = np.nonzero(M[r:, col])[0]
        if len(piv) == 0:
            continue
        piv = r + piv[0]
        M[[r, piv]] = M[[piv, r]]
        M[r + 1:] ^= M[r][None, :] * M[r + 1:, col][:, None]
        r += 1
    # linear map over the full domain: L(s) = XOR of columns of set bits
    bits = np.arange(NIN, dtype=np.uint16)
    L = np.zeros(NIN, dtype=np.uint16)
    for j in range(16):
        sel = (bits >> j) & 1
        L ^= np.where(sel, cols[j], 0).astype(np.uint16)
    L ^= D0
    return r, L


def main():
    t0 = time.time()
    ops = tempest_a1_round_program()
    T = round_table(ops, 1)
    idx = np.arange(NIN, dtype=np.uint16)
    rng = np.random.default_rng(20260806)
    deltas = list(range(1, 17)) + [0xFFFF, 0x3333, 0x5A5A, 0x5005,
                                   0x5500, 0x5050, 0x801, 0xF0F0]
    deltas += [int(x) for x in rng.integers(1, NIN, size=2000)]
    deltas = sorted(set(deltas))

    rows = []
    worst = {'g_M_diff': -1e9}
    n_viol = 0
    for d in deltas:
        D = T[idx ^ np.uint16(d)] ^ T
        rank, L = linear_part_rank_and_map(D)
        R = D ^ L
        m = np.log2(len(np.unique(R)))            # log2 |R-image| (global)
        counts = np.bincount(D.astype(np.int64), minlength=NIN)
        dplog = -np.log2(counts.max() / NIN)      # -log2 DP
        # improved bound: max |R(coset)| over ker(B) cosets.
        # B s = L ^ D0; group by B s value, count uniques of R per group.
        Bs = (L ^ D[0]).astype(np.int64)
        order = np.lexsort((R.astype(np.int64), Bs))
        Rg = R[order]
        Bg = Bs[order]
        M = 1
        start = 0
        while start < NIN:
            end = start + 1
            while end < NIN and Bg[end] == Bg[start]:
                end += 1
            M = max(M, int(len(np.unique(Rg[start:end]))))
            start = end
        Mlog = np.log2(M)
        # theorems: dplog <= rank + m (global form, strong at LOW rank);
        #            dplog >= (n-rank) - Mlog (coset form, strong at HIGH
        #            rank: |D-image| <= 2^(n-rank) * M, so
        #            DP >= 1/|D-image| >= 2^-(n-rank)/M)
        ok_global = dplog <= rank + m + 1e-9
        ok_coset = dplog >= (16 - rank) - Mlog - 1e-9
        if not (ok_global and ok_coset):
            n_viol += 1
        g = rank - dplog                          # log2 aggregation factor
        rows.append({'delta': hex(d), 'rank': int(rank),
                     '-log2 DP': round(dplog, 3),
                     'log2|R-img|': round(m, 3),
                     'log2 M_coset': round(Mlog, 3),
                     'g': round(g, 3),
                     'bound_global': bool(ok_global),
                     'bound_coset': bool(ok_coset),
                     'slack_coset': round(rank + Mlog - dplog, 3)})
        if g - Mlog > worst['g_M_diff']:
            worst = {'delta': hex(d), 'g': round(g, 3), 'M': round(Mlog, 3),
                     'g_M_diff': round(g - Mlog, 3)}
        if len(rows) % 200 == 0:
            print(f'{len(rows)}/{len(deltas)} done ({time.time()-t0:.0f}s)',
                  flush=True)

    gs = np.array([r['g'] for r in rows])
    ms = np.array([r['log2|R-img|'] for r in rows])
    Ms = np.array([r['log2 M_coset'] for r in rows])
    res = {
        'meta': 'Differential Decomposition Bound at W=4, full design, '
                'full-domain per-delta verification (global + coset form)',
        'n_deltas': len(rows),
        'violations': n_viol,
        'g_min': round(float(gs.min()), 3), 'g_max': round(float(gs.max()), 3),
        'g_mean': round(float(gs.mean()), 3),
        'm_min': round(float(ms.min()), 3), 'm_max': round(float(ms.max()), 3),
        'M_min': round(float(Ms.min()), 3), 'M_max': round(float(Ms.max()), 3),
        'M_mean': round(float(Ms.mean()), 3),
        'g_le_M_all': bool((gs <= Ms + 1e-9).all()),
        'worst_ratio': worst,
        'rows': rows,
        'elapsed_s': round(time.time() - t0, 1),
    }
    with open('explore_decomp_bound.json', 'w') as f:
        json.dump(res, f, indent=1, default=str)
    print(f'deltas={len(rows)} violations={n_viol} '
          f'g in [{res["g_min"]},{res["g_max"]}] '
          f'M in [{res["M_min"]},{res["M_max"]}] '
          f'g<=M all: {res["g_le_M_all"]} ({time.time()-t0:.0f}s)')


if __name__ == '__main__':
    main()

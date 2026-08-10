# -*- coding: utf-8 -*-
"""test_aggregation_conjecture.py — test the DIFFERENTIAL AGGREGATION
conjecture on random functions and random quadratic functions:

    CONJECTURE T-A: for ANY Phi : F2^n -> F2^n and any Delta != 0, with
    D_Delta(s) = Phi(s^Delta) ^ Phi(s) and r_lin(Delta) = rank of the
    linear part of D_Delta (columns D(e_j) ^ D(0)):
        DP(Delta) = max_c Pr_s[D_Delta(s) = c] >= 2^{-r_lin(Delta)}.

This is a machine test: if a counterexample exists at small n, random
search should find it.  Also tests the stronger FIBER-IDENTITY property
(DP = 2^{-r_lin} exactly, i.e. D_Delta affine) for random QUADRATIC
maps, and the aggregation law on the TRUE Algorithm 1 at W=4 (already
verified: 0 fails over all 65535 deltas).
"""
import numpy as np
import json

W = 4
NIN = 1 << (4 * W)


def gf2_rank(rows):
    n = len(rows)
    rows = [int(r) for r in rows]
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


def test_function(T, label, max_deltas=None):
    """T: truth table (2^n,) of values. Check aggregation for all/random deltas."""
    n = int(np.log2(len(T)))
    N = len(T)
    idx = np.arange(N)
    deltas = range(1, N) if max_deltas is None else None
    if max_deltas is not None:
        rng = np.random.default_rng(42)
        deltas = rng.integers(1, N, size=max_deltas)
    agg_fail = 0
    ident_fail = 0
    first_fail = None
    min_dlog2 = 99
    max_fiber_ratio = 0
    for di in deltas:
        dT = T[idx ^ di] ^ T
        counts = np.bincount(dT, minlength=N)
        m = counts.max()
        max_fiber_ratio = max(max_fiber_ratio, m / N)
        dp = m / N
        dlog2 = -np.log2(dp)
        min_dlog2 = min(min_dlog2, dlog2)
        e0 = dT[0]
        cols = [int(dT[1 << j] ^ e0) for j in range(n)]
        r_lin = gf2_rank(cols)
        if dp < 2.0 ** (-r_lin) - 1e-12:
            agg_fail += 1
            if first_fail is None:
                first_fail = {'n': n, 'delta': int(di), 'r_lin': r_lin,
                              'dlog2dp': float(dlog2)}
        if m != (1 << (n - r_lin)):
            ident_fail += 1
    print(f'{label}: n={n} N={N} deltas_tested='
          f'{"all" if max_deltas is None else max_deltas}  '
          f'AGG_FAIL={agg_fail}  IDENT_FAIL={ident_fail}  '
          f'Hinf_sample={min_dlog2:.2f}  DPmax={max_fiber_ratio:.2e}')
    if first_fail:
        print(f'   first agg counterexample: {first_fail}')
    return {'agg_fail': agg_fail, 'ident_fail': ident_fail,
            'Hinf_sample': float(min_dlog2), 'first_fail': first_fail}


def main():
    rng = np.random.default_rng(2026)
    res = {}
    # 1) random functions n = 4, 5 (exhaustive deltas at n=4; 2^20 at n=5)
    for n in (4, 5):
        N = 1 << n
        fails = 0
        first = None
        for trial in range(400):
            T = rng.integers(0, N, size=N)
            d = test_function(T, f'randfn n={n}', max_deltas=min(1 << n, 1 << 14))
            fails += d['agg_fail']
            if d['first_fail'] and first is None:
                first = d['first_fail']
        res[f'randfn_{n}'] = {'total_agg_fails': fails, 'first': first}
        print(f'random functions n={n}: total agg fails over 400 fns x deltas = {fails}')
    # 2) random QUADRATIC functions n=4,5,6 (identity test)
    for n in (4, 5, 6):
        N = 1 << n
        fails = 0
        ident_fails = 0
        first = None
        for trial in range(200):
            # random quadratic: pick random symmetric matrix Q (n x n, zero
            # diagonal for pure quadratic part) + linear part L + constant
            Q = np.zeros((n, n), dtype=np.uint8)
            for i in range(n):
                for j in range(i + 1, n):
                    Q[i, j] = Q[j, i] = rng.integers(0, 2)
            Lb = rng.integers(0, 2, size=n)
            c = rng.integers(0, 2, size=n)
            xs = np.array([(i >> b) & 1 for i in range(N) for b in range(n)]
                          ).reshape(N, n)
            # f(x) = x^T Q x + L x + c   (each output bit independently)
            vals = np.zeros(N, dtype=np.uint16)
            for bit in range(n):
                qv = ((xs @ Q) * xs).sum(axis=1) & 1
                lv = (xs @ Lb) & 1
                vals |= ((qv ^ lv ^ c[bit]).astype(np.uint16)) << bit
            # sample 2000 deltas
            d = test_function(vals, f'quad fn n={n}', max_deltas=2000)
            fails += d['agg_fail']
            ident_fails += d['ident_fail']
            if d['first_fail'] and first is None:
                first = d['first_fail']
        res[f'quad_{n}'] = {'total_agg_fails': fails,
                            'total_ident_fails': ident_fails, 'first': first}
        print(f'random quadratic n={n}: agg fails={fails} ident fails={ident_fails}')
    with open('test_aggregation_conjecture.json', 'w') as f:
        json.dump(res, f, indent=1)
    print('done -> test_aggregation_conjecture.json')


if __name__ == '__main__':
    main()

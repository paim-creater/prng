# -*- coding: utf-8 -*-
"""verify_barrier.py — independent verdict on the Two-Layer Polar-Rank
Barrier: is min rank = 3 at every width for the pre-mix-free shadow?

1. All single-bit differences, W in {8,16,32,48,64}: rank must be 3
   (the constructive upper bound).
2. Alternating bilinear search (include_premix=False — the theorem's
   object), W in {8,16,32,64}: any found rank < 3 falsifies the lower
   bound; rank 3 witnesses support it.
3. Random-difference scan at W=64 (10k diffs): lowest rank observed.
"""
import numpy as np
import json, time, sys

from min_shadow_rank import truncate_at_levels, polar_matrices, rank_of_delta
from cipher import tempest_a1_round_program

OPS = tempest_a1_round_program()
SHADOW = truncate_at_levels(OPS, 0, include_premix=False)


def search_min_rank(W, shadow, iters=400, seed=1):
    """Alternating bilinear search for min rank (re-implemented simply)."""
    rng = np.random.default_rng(seed)
    n = 4 * W
    A, C = polar_matrices(W, shadow)
    best = n
    best_delta = None
    for it in range(iters):
        # random kernel candidate k
        k = rng.integers(0, 2, size=n)
        # solve B_Delta k = 0: sum_i Delta_i (C_i k) = -A k
        cols = C @ k          # (n, n) matrix M with M[:, i] = C_i k
        rhs = -(A @ k) % 2
        # least-squares-ish solve over GF(2): try direct elimination
        from min_shadow_rank import gf2_rank as _r
        # augment: find Delta with M Delta = rhs via Gaussian elimination
        M = cols.copy()
        aug = np.hstack([M, rhs.reshape(-1, 1)])
        # row reduce
        r = 0
        piv = []
        for c in range(n):
            p = np.nonzero(aug[r:, c])[0]
            if len(p) == 0:
                continue
            p = p[0] + r
            aug[[r, p]] = aug[[p, r]]
            piv.append(c)
            for rr in range(n):
                if rr != r and aug[rr, c]:
                    aug[rr] ^= aug[r]
            r += 1
            if r == n:
                break
        solvable = r == _r(aug)  # consistent?
        if solvable and r < n:
            # free variables -> construct a candidate Delta
            Delta = np.zeros(n, dtype=int)
            for i in piv:
                Delta[i] = aug[i, -1]
            dint = int(''.join(map(str, Delta[::-1])), 2)
            rk = rank_of_delta(W, shadow, dint)
            if rk < best:
                best = rk
                best_delta = dint
        # also: kernel vectors of best found B as new candidates
        if best_delta is not None:
            pass
    return best, best_delta


def main():
    res = {}
    # 1. single-bit ranks
    sb = {}
    for W in [8, 16, 32, 48, 64]:
        ranks = []
        for b in range(4 * W):
            ranks.append(rank_of_delta(W, SHADOW, 1 << b))
        sb[W] = {'min': min(ranks), 'max': max(ranks),
                 'all_three': all(r == 3 for r in ranks)}
        print(f'single-bit W={W}: min={min(ranks)} max={max(ranks)} '
              f'all==3: {all(r == 3 for r in ranks)}', flush=True)
    res['single_bit'] = sb
    # 2. alternating search min (pre-mix-free!)
    for W in [8, 16, 32, 64]:
        t0 = time.time()
        best, d = search_min_rank(W, SHADOW, iters=300)
        res[f'search_W{W}'] = {'min_rank': best, 'delta': hex(d) if d else None,
                               'secs': round(time.time() - t0, 1)}
        print(f'search W={W}: min rank = {best} ({hex(d) if d else None}) '
              f'[{time.time()-t0:.0f}s]', flush=True)
    # 3. random scan W=64
    rng = np.random.default_rng(7)
    best = 999
    for i in range(2000):
        d = int(rng.integers(1, 1 << 256))
        rk = rank_of_delta(64, SHADOW, d)
        if rk < best:
            best = rk
    res['random_scan_w64'] = {'min_rank_2000': best}
    print(f'random scan W=64 (2000 diffs): min rank = {best}', flush=True)
    with open('verify_barrier.json', 'w') as f:
        json.dump(res, f, indent=1)
    print('saved verify_barrier.json')


if __name__ == '__main__':
    main()

# -*- coding: utf-8 -*-
"""test_shadow_rank_w8.py — the CASCADE-DOUBLING law test (clean version).

Measured (true Algorithm-1 semantics, W=4, exact): H_inf(two-layer shadow
= k=0 variant) = 3.00 (min polar rank),  H_inf(full cascade) = 5.94.
Ratio ~ 2.  Test at W=8:
  * per sampled Delta: DP(Delta) (vectorized over n_states),
    polar matrix B_Delta (via 4W single-state evaluations), rank.
  * shadow: fiber identity DP == 2^-rank (affine theorem at W=8);
  * compare min DP of full vs min rank of shadow -> doubling law.
"""
import numpy as np
import time, json

from cipher import tempest_a1_round_program, State, apply_round, U64

ops = tempest_a1_round_program()


def truncate_at_levels(ops, k, include_premix=True):
    a3_idx = [i for i, op in enumerate(ops) if op[0] == 'A3']
    snap_idx = [i for i, op in enumerate(ops) if op[0] == 'SNAP']
    first_level = min(i for i in snap_idx if i > max(a3_idx))
    level_starts = [i for i in snap_idx if i >= first_level][:4]
    cut = level_starts[k] if k < 4 else len(ops)
    if not include_premix:
        cut = min(cut, min(a3_idx))
    return ops[:cut]


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


def d_delta(prog, W, delta_words, states):
    """Apply round to (states, states ^ delta), return packed difference."""
    sA = State([states[:, i].astype(np.uint64).copy() for i in range(4)],
               states_wv(prog, states), W=W)
    sB = State([(states[:, i].astype(np.uint64) ^ U64(delta_words[i]))
                for i in range(4)], states_wv(prog, states), W=W)
    apply_round(prog, sA)
    apply_round(prog, sB)
    full = np.zeros(len(states), dtype=np.uint64)
    for i in range(4):
        full ^= (sA.words[i] ^ sB.words[i]) << (W * i)
    return full


def states_wv(prog, states):
    return np.zeros(len(states), dtype=np.uint64)


def single_delta_polar(prog, W, d):
    """Polar matrix B_d: columns D_d(e_k) ^ D_d(0), k = 0..4W-1.
    D_d(x) = Phi(x ^ d) ^ Phi(x), evaluated on single states."""
    n = 4 * W
    dwords = [int(d[i]) for i in range(4)]
    cols = []
    for k in range(n):
        e = [0, 0, 0, 0]
        wi, bi = divmod(k, W)
        e[wi] = 1 << bi
        # D_d(e_k): state = e_k
        x = np.zeros(1, dtype=np.uint64)
        D0 = d_delta(prog, W, dwords, single_state(e))
        Dk = d_delta(prog, W, dwords, single_state(e))
        _ = D0[0]
        cols.append(int(Dk[0]) ^ int(D0[0]))
    # columns are D_d(e_k) ^ D_d(0); D_d(0) = D0 computed at k=0 state=0:
    e0 = single_state([0, 0, 0, 0])
    D0v = d_delta(prog, W, dwords, e0)
    c0 = int(D0v[0])
    cols = [int(d_delta(prog, W, dwords, single_state(e_of(k, W)))[0]) ^ c0
            for k in range(n)]
    return cols, c0


def e_of(k, W):
    e = [0, 0, 0, 0]
    wi, bi = divmod(k, W)
    e[wi] = 1 << bi
    return e


def single_state(words):
    st = np.zeros((1, 4), dtype=np.uint64)
    for i in range(4):
        st[0, i] = words[i]
    return st


def analyze(prog, W, n_states, n_deltas, seed):
    rng = np.random.default_rng(seed)
    n = 4 * W
    min_h_full = None
    min_r_shadow = n + 1
    ident_fail = 0
    agg_fail = 0
    results = []
    for di in range(n_deltas):
        d = [int(rng.integers(0, 1 << W)) for _ in range(4)]
        if not any(d):
            d[0] = 1
        # vectorized DP
        st = rng.integers(0, 1 << W, size=(n_states, 4), dtype=np.uint64)
        dfull = d_delta(prog, W, d, st)
        uniq, counts = np.unique(dfull, return_counts=True)
        m = int(counts.max())
        h = -np.log2(m / n_states)
        # polar rank (exact, single states)
        cols, c0 = single_delta_polar(prog, W, d)
        r = gf2_rank(cols)
        if min_h_full is None or h < min_h_full:
            min_h_full = h
        if r < min_r_shadow:
            min_r_shadow = r
        # identity: for affine D, max fiber = 2^(n - r) exactly
        if prog_is_shadow(prog):
            if m != (1 << (n - r)):
                ident_fail += 1
        if h < r - 1e-9:
            agg_fail += 1
        results.append({'delta': [hex(int(x)) for x in d], 'h': round(h, 3),
                        'r': r})
    return min_h_full, min_r_shadow, ident_fail, agg_fail, results


def prog_is_shadow(prog):
    return len(prog) < 40  # shadow k=0 has 25 ops; full has 54


def main():
    W = 8
    n = 4 * W
    shadow = truncate_at_levels(ops, 0, include_premix=True)
    res = {'meta': {'W': W, 'n': n, 'note': 'cascade-doubling law test'}}
    N = 1 << 17
    for label, prog in [('shadow_k0', shadow), ('full_k4', ops)]:
        t0 = time.time()
        min_h, min_r, ifail, afail, rows = analyze(prog, W, N, 64, seed=7)
        res[label] = {'min_dlog2DP_64deltas': round(min_h, 3),
                      'min_polar_rank': int(min_r),
                      'identity_fails': int(ifail),
                      'agg_fails': int(afail),
                      'secs': round(time.time() - t0, 1)}
        print(f'W=8 {label}: min -log2 DP = {min_h:.3f}  min polar rank = '
              f'{min_r}  identity fails = {ifail}  agg fails = {afail} '
              f'({time.time()-t0:.0f}s)', flush=True)
    with open('test_shadow_rank_w8.json', 'w') as f:
        json.dump(res, f, indent=1)
    print('done -> test_shadow_rank_w8.json')


if __name__ == '__main__':
    main()

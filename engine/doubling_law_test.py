# -*- coding: utf-8 -*-
"""doubling_law_test.py — test the cascade-doubling law DP_full(Delta) ~
2^{-2 * minrank_shadow} at W=4 (exact) and W=8 (sampled), and run
min-rank search at W=16, W=32 (exact poly-time).
"""
import numpy as np
import json, time

from cipher import (tempest_a1_round_program, State, apply_round, U64)
from audit_true_algorithm1 import apply_round_snap, NIN, IDX_AR
from min_shadow_rank import truncate_at_levels, rank_of_delta

OPS = tempest_a1_round_program()


def dp_full_w4(delta):
    """Exact full-domain DP of the full Algorithm 1 at W=4 (no-key)."""
    ops = OPS
    st = np.zeros((NIN, 4), dtype=np.uint16)
    for wi in range(4):
        st[:, wi] = (IDX_AR >> (wi * 4)) & 0xF
    o0, _ = apply_round_snap(st.copy(), ops, [np.uint16(0), np.uint16(0)])
    st2 = np.zeros((NIN, 4), dtype=np.uint16)
    codes2 = IDX_AR ^ np.uint16(delta)
    for wi in range(4):
        st2[:, wi] = (codes2 >> (wi * 4)) & 0xF
    o1, _ = apply_round_snap(st2.copy(), ops, [np.uint16(0), np.uint16(0)])
    T0 = (o0[:, 0] | (o0[:, 1] << 4) | (o0[:, 2] << 8) | (o0[:, 3] << 12))
    T1 = (o1[:, 0] | (o1[:, 1] << 4) | (o1[:, 2] << 8) | (o1[:, 3] << 12))
    dT = (T0.astype(np.uint16) ^ T1.astype(np.uint16))
    counts = np.bincount(dT, minlength=NIN)
    return counts.max() / NIN, counts.max()


def dp_full_w8(delta, n_states, seed):
    """Sampled DP of the full Algorithm 1 at W=8."""
    W = 8
    rng = np.random.default_rng(seed)
    st = rng.integers(0, 1 << W, size=(n_states, 4), dtype=np.uint64)
    dwords = [(delta >> (wi * W)) & ((1 << W) - 1) for wi in range(4)]
    sA = State([st[:, i].copy() for i in range(4)],
               np.zeros(n_states, dtype=np.uint64), W=W)
    sB = State([(st[:, i] ^ U64(dwords[i])) for i in range(4)],
               np.zeros(n_states, dtype=np.uint64), W=W)
    apply_round(OPS, sA)
    apply_round(OPS, sB)
    full = np.zeros(n_states, dtype=np.uint64)
    for i in range(4):
        full ^= (sA.words[i] ^ sB.words[i]) << (W * i)
    uniq, counts = np.unique(full, return_counts=True)
    return counts.max() / n_states, int(counts.max())


def main():
    out = {'meta': 'doubling law: full DP at shadow min-rank deltas'}
    shadow = truncate_at_levels(OPS, 0, include_premix=True)
    # W=4: exact
    r4, _ = rank_of_delta(4, shadow, 0x1)
    dp4, m4 = dp_full_w4(0x1)
    out['W4'] = {'shadow_min_rank': 3, 'delta': '0x1',
                 'full_DP_dlog2': round(-np.log2(dp4), 4),
                 'doubling_prediction': 2 * 3,
                 'fiber': int(m4)}
    print(f'W=4 delta=0x1: shadow rank=3  full DP=2^{-np.log2(dp4):.4f} '
          f'(doubling predicts 2^-6)', flush=True)
    # also the full design's worst delta
    dp4b, _ = dp_full_w4(0x5005)
    out['W4']['full_worst_delta_0x5005'] = round(-np.log2(dp4b), 4)
    print(f'W=4 delta=0x5005 (full worst): DP=2^{-np.log2(dp4b):.4f}')
    # W=8: shadow min rank = 6 (delta 0x40000000), full DP at that delta
    r8, _ = rank_of_delta(8, shadow, 0x40000000)
    dp8, m8 = dp_full_w8(0x40000000, 1 << 22, seed=11)
    out['W8'] = {'shadow_min_rank': 6, 'delta': '0x40000000',
                 'full_DP_dlog2_sampled': round(-np.log2(dp8), 3),
                 'doubling_prediction': 2 * 6,
                 'fiber': int(m8)}
    print(f'W=8 delta=0x40000000: shadow rank=6  full DP sampled '
          f'= 2^{-np.log2(dp8):.3f} (doubling predicts 2^-12)')
    # W=16, W=32 min-rank searches (exact, poly-time)
    for W in (16, 32):
        t0 = time.time()
        ops = truncate_at_levels(OPS, 0, include_premix=True)
        from min_shadow_rank import min_rank_search
        best_rank, best_delta = min_rank_search(W, ops, n_restarts=60,
                                                iters=20)
        out[f'W{W}'] = {'min_rank': int(best_rank),
                        'delta': hex(int(best_delta)),
                        'secs': round(time.time() - t0, 1)}
        print(f'W={W}: min polar rank = {best_rank} (delta {hex(best_delta)}) '
              f'({time.time()-t0:.0f}s)', flush=True)
    with open('doubling_law_test.json', 'w') as f:
        json.dump(out, f, indent=1)
    print('done -> doubling_law_test.json')


if __name__ == '__main__':
    main()

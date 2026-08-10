# -*- coding: utf-8 -*-
"""explore_wide.py — width-scaling test of the zero-differential law at W=8.

At W=8 the state is 32 bits; full enumeration is impossible. We sample
DP0(Delta) = Pr_x[f(x) = f(x xor Delta)] with N samples per Delta and
check the two structural facts found exactly at W=4:

  (1) DP0(Delta) is (nearly) constant over Delta  -> <DP0> is the object
  (2) <DP0>_Delta = E(0) = <bias_u^2>_u            (differential-linear
      mean-square duality, two independently sampled sides)

The wv (key-stream) word is sampled per pair, matching the earlier
halfentropy_wide experiments.
"""
import numpy as np
import time, json

from cipher import tempest_a1_round_program, State, apply_round, U64

ops = tempest_a1_round_program()
W = 8
NIN = 1 << (4 * W)


def dp0_samples(delta_words, n, seed):
    """n state pairs -> DP0(Delta) estimate (proportion of zero diffs)."""
    st = State.random(n, seed=seed, W=W)
    sA = State([w.copy() for w in st.words], st.wv, W=W)
    sB = State([w ^ U64(delta_words[i]) for i, w in enumerate(st.words)],
               st.wv, W=W)
    apply_round(ops, sA)
    apply_round(ops, sB)
    z = 0
    for i in range(4):
        z |= sA.words[i] ^ sB.words[i]
    return float(np.count_nonzero(z == 0)) / n


def bias_samples(mask_words, n, seed):
    """Sample bias_u = E[(-1)^{u.f(x)}] for a set of masks (each 4 words)."""
    st = State.random(n, seed=seed, W=W)
    words0 = [w.copy() for w in st.words]
    apply_round(ops, st)
    out = []
    for i in range(4):
        out.append(st.words[i] ^ words0[i])     # f(x) (state words after 1r)
    out = [o.astype(np.uint64) for o in out]
    biases = []
    for m in mask_words:
        b = np.ones(n, dtype=np.int8)
        for i in range(4):
            v = m[i]
            if v:
                b ^= ((out[i] & U64(v)) != 0).astype(np.int8)
        biases.append(float(b.mean()))          # E[(-1)^{u.f}]
    return np.array(biases)


def main():
    rng = np.random.default_rng(2026)
    N = 1 << 16                      # per-delta pairs
    NB = 24                           # sampled deltas
    deltas = []
    for _ in range(NB):
        d = [int(rng.integers(1, 1 << W)) for _ in range(4)]
        deltas.append(d)
    # masks for bias side: 30 random masks (mix of weights)
    masks = [tuple(int(rng.integers(0, 1 << W)) for _ in range(4))
             for _ in range(30)]

    results = {}
    rounds = [1, 2, 4, 8, 12, 16, 22]
    # fixed-wv permutation-hypothesis probe: wv = 0x5A for all pairs
    for r in (1, 22):
        zeros = 0
        for di, d in enumerate(deltas[:8]):
            st = State.random(N, seed=5000 + r * 100 + di, W=W)
            wvfix = np.full(N, U64(0x5A), dtype=np.uint64)
            sA = State([w.copy() for w in st.words], wvfix, W=W)
            sB = State([w ^ U64(d[i]) for i, w in enumerate(st.words)],
                       wvfix, W=W)
            for _ in range(r):
                apply_round(ops, sA)
                apply_round(ops, sB)
            z = sA.words[0] ^ sB.words[0]
            for i in range(1, 4):
                z |= sA.words[i] ^ sB.words[i]
            zeros += int(np.count_nonzero(z == 0))
        print(f'FIXED-wv r={r}: DP0 zeros = {zeros} / {8 * N} (permutation hypothesis)',
              flush=True)
    for r in rounds:
        dp0s = []
        for di, d in enumerate(deltas):
            st = State.random(N, seed=3000 + r * 100 + di, W=W)
            sA = State([w.copy() for w in st.words], st.wv, W=W)
            sB = State([w ^ U64(d[i]) for i, w in enumerate(st.words)],
                       st.wv, W=W)
            for _ in range(r):
                apply_round(ops, sA)
                apply_round(ops, sB)
            z = sA.words[0] ^ sB.words[0]
            for i in range(1, 4):
                z |= sA.words[i] ^ sB.words[i]
            dp0s.append(float(np.count_nonzero(z == 0)) / N)
        dp0s = np.array(dp0s)
        c = dp0s.mean()
        # bias side: sample bias_u = E[(-1)^{u.f(x)}] at round r with same N
        # u.f(x) = parity of sum_i popcount(f_i(x) & v_i)
        def pc64(x):
            x = x - ((x >> 1) & U64(0x5555555555555555))
            x = (x & U64(0x3333333333333333)) + ((x >> 2) & U64(0x3333333333333333))
            x = (x + (x >> 4)) & U64(0x0F0F0F0F0F0F0F0F)
            return (x * U64(0x0101010101010101)) >> 56
        bs = []
        for m in masks:
            st = State.random(N, seed=4000 + r * 100, W=W)
            for _ in range(r):
                apply_round(ops, st)
            b = np.zeros(N, dtype=np.int8)
            for i in range(4):
                v = m[i]
                if v:
                    b ^= (pc64(st.words[i] & U64(v)) & 1).astype(np.int8)
            bs.append(float((1.0 - 2.0 * b).mean()))
        bs = np.array(bs)
        results[r] = {
            'dp0_mean': round(c, 8),
            'dp0_mean_dlog2': round(-np.log2(c), 4),
            'dp0_std': round(float(dp0s.std()), 8),
            'dp0_min_dlog2': round(-np.log2(dp0s.max()), 4),
            'bias_sq_mean': round(float((bs ** 2).mean()), 8),
            'bias_sq_mean_dlog2': round(-np.log2((bs ** 2).mean()), 4),
            'bias_max': round(float(np.abs(bs).max()), 6),
            'N': N, 'ndeltas': len(deltas), 'nmasks': len(masks),
        }
        print(f'r={r:2d}: <DP0>={c:.3e} (2^-{-np.log2(c):.2f}) '
              f'std={dp0s.std():.2e}  <bias^2>={(bs**2).mean():.3e} '
              f'(2^-{-np.log2((bs**2).mean()):.2f})  max|bias|={np.abs(bs).max():.3f}',
              flush=True)

    with open('explore_wide.json', 'w') as f:
        json.dump(results, f, indent=1)
    print('saved explore_wide.json')


if __name__ == '__main__':
    main()

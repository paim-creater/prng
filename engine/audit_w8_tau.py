# -*- coding: utf-8 -*-
"""audit_w8_tau.py — verify two remaining paper claims with CORRECT
(DSL, KAT-validated) semantics:

 (1) H_inf = 15.00 at W=8  (paper: sampled, 150 differences, 2^16 states)
 (2) tau = 1.000 at W=4    (paper: exact, exhaustive state-key enumeration)
 (3) W=4 H2 with the true function (paper claims 7.96)
"""
import numpy as np
import time, json

from cipher import (tempest_a1_round_program, tempest_v31_round_program,
                    State, apply_round, U64, MASK)

ops = tempest_a1_round_program()


def min_dp_sample(W, n_states, n_diffs, seed=2026):
    """Sample n_diffs differences; per difference compute DP(Delta) =
    max-fiber prob of the output difference over n_states pairs; return
    min over diffs of -log2 DP."""
    rng = np.random.default_rng(seed)
    worst = None
    worst_d = None
    for di in range(n_diffs):
        # difference: random 4-word pattern (nonzero)
        d = [int(rng.integers(0, 1 << W)) for _ in range(4)]
        if not any(d):
            d[0] = 1
        st = State.random(n_states, seed=seed + di, W=W)
        sA = State([w.copy() for w in st.words], st.wv, W=W)
        sB = State([w ^ U64(d[i]) for i, w in enumerate(st.words)], st.wv, W=W)
        apply_round(ops, sA)
        apply_round(ops, sB)
        full = np.zeros(n_states, dtype=np.uint64)
        for i in range(4):
            full ^= (sA.words[i] ^ sB.words[i]) << (W * i)
        uniq, counts = np.unique(full, return_counts=True)
        dp = counts.max() / n_states
        h = -np.log2(dp)
        if worst is None or h < worst:
            worst = h
            worst_d = d
    return worst, worst_d


def tau_w4_exact():
    """Exact tau at W=4 with the true round + output function.
    tau = Pr_{s, w1 != w2}[ O(Phi(s,w1)) != O(Phi(s,w2)) ].
    State space 2^16; key space 2^4. Exhaustive."""
    W = 4
    M = (1 << W) - 1
    NIN = 1 << 16
    IDX_AR = np.arange(NIN, dtype=np.uint16)
    rng = np.random.default_rng(99)
    # output function at W=4 (mirror of make_output_a1)
    def out4(s):
        u, v, w, z = s
        t = (u ^ np.uint16(((v << 0) & M) | (v >> (W - 0))))  # rotl(v,32) mod 4 = 0
        t = np.uint16(t) ^ np.uint16(w) ^ np.uint16(((z << 0) & M) | (z >> (W - 0)))
        # rotl(t,22%4=2), rotl(t,26%4=2), rotl(t,16%4=0), rotl(t,14%4=2)
        def rl(x, r):
            r %= W
            return np.uint16(((x << r) & M) | (x >> (W - r)))
        t = rl(t, 22) ^ rl(t, 26) ^ t
        t = rl(t, 16) ^ rl(t, 14) ^ t
        for (r1, r2) in [(31, 53), (17, 43), (7, 23), (5, 19)]:
            t = t ^ (rl(t, r1) & rl(t, r2))
        t = t ^ np.uint16((t >> 32) & M)  # >>32 mod 4 = 0 shift -> 0
        return t
    # states table
    codes = IDX_AR
    st = np.zeros((NIN, 4), dtype=np.uint16)
    for wi in range(4):
        st[:, wi] = (codes >> (wi * W)) & M
    # for each of 2^4 possible keys, tabulate outputs
    from audit_true_algorithm1 import apply_round_snap
    outs = {}
    for wv0 in range(16):
        stk = st.copy()
        stk, _ = apply_round_snap(stk, ops, [np.uint16(wv0), np.uint16(0)])
        o = out4([stk[:, i] for i in range(4)])
        outs[wv0] = o
    # tau: over pairs (w1,w2), fraction of states where outputs differ
    total_pairs = 0
    diff_events = 0
    for w1 in range(16):
        for w2 in range(16):
            if w1 == w2:
                continue
            total_pairs += 1
            diff_events += int(np.count_nonzero(outs[w1] != outs[w2]))
    tau = diff_events / (total_pairs * NIN)
    # also the simple "alive" witness check on a few states
    return tau


def main():
    res = {}
    # (1) W=8 H_inf, correct interpreter
    t0 = time.time()
    for n_states, n_diffs, label in [(1 << 16, 150, '150x2^16 (paper recipe)'),
                                     (1 << 18, 60, '60x2^18 (higher res)')]:
        worst, worst_d = min_dp_sample(8, n_states, n_diffs, seed=2026)
        res[f'W8_{label}'] = {'H_inf_sample': round(worst, 3),
                              'worst_delta': [hex(int(x)) for x in worst_d]}
        print(f'W=8 {label}: min -log2 DP = {worst:.3f} '
              f'({time.time()-t0:.0f}s)', flush=True)
    # (2) tau at W=4 exact
    t0 = time.time()
    tau = tau_w4_exact()
    res['tau_W4_exact'] = round(tau, 6)
    print(f'tau (W=4, exhaustive, true semantics) = {tau:.6f} ({time.time()-t0:.0f}s)')
    # (3) W=4 H2 exact (true function)
    from audit_true_algorithm1 import tabulate, apply_round_snap
    T = tabulate(ops, with_key=False)
    res['H2_W4_nokey'] = None
    print('W=4 H2 (true fn, no-key): computing...')
    t0 = time.time()
    NIN = 1 << 16
    IDX_AR = np.arange(NIN, dtype=np.uint16)
    # H2 of output-difference distribution averaged over all deltas (too
    # heavy) -> sample: per delta compute H2 of dT distribution, average.
    rng = np.random.default_rng(7)
    h2s = []
    for di in range(300):
        d = int(rng.integers(1, NIN))
        dT = T[IDX_AR ^ np.uint16(d)] ^ T
        uniq, counts = np.unique(dT, return_counts=True)
        p = counts / NIN
        h2s.append(-np.log2(np.sum(p * p)))
    res['H2_W4_nokey_mean300'] = round(float(np.mean(h2s)), 3)
    print(f'W=4 H2 mean over 300 deltas = {np.mean(h2s):.3f} ({time.time()-t0:.0f}s)')
    with open('audit_w8_tau.json', 'w') as f:
        json.dump(res, f, indent=1)
    print('done -> audit_w8_tau.json')


if __name__ == '__main__':
    main()

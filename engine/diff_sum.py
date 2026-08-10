# -*- coding: utf-8 -*-
"""diff_sum.py — multi-round differential decay of the best iterative
trail (quantifies trail aggregation / saturation).

Measures DP^(R)(Delta) = max_d Pr[Phi^R(x^Delta) ^ Phi^R(x) = d] for
R=1..Rmax with 2^nlog pairs (counts aggregated across chunks), for the
trail_diff.py optimum difference (u bit 4, v bit 6, w bit 3) and random
diffs. Two widths are wired in:

  W=8: the trail-optimal difference's DP is CONSTANT at 2^-7.00 over
       R=1..6 (mod-8 rotation-degeneracy freeze; the aggregation factor
       grows from 2^+1 at R=1 to 2^+41 at R=6 against the trail product
       2^-8R) — an iteration non-mixing artifact of the degenerate
       width, exactly as the linear imbalance (lin_scale.py).
  W=64: the same difference pattern lifted to full width. Packing note:
       the 256-bit difference must be packed into a Python int — the
       earlier 64-bit-shift packing truncated (uint64 wrap), merging
       distinct differences and inflating counts.

Usage: python diff_sum.py [rounds_max] [samples_log2] [W]
"""
import sys
from collections import Counter
import numpy as np

sys.path.insert(0, '.')
from cipher import State, apply_round, tempest_a1_round_program

OPS = tempest_a1_round_program()
TRAIL_D8 = (1 << 4, 1 << 6, 1 << 3, 0)   # trail_diff.py optimum at W=8


def dp_measure(delta, R, nlog, W):
    N = 1 << nlog
    rng = np.random.default_rng(11)
    CH = 1 << 18
    cnt = Counter()
    for ci in range(N // CH):
        s0 = State([rng.integers(0, 1 << W, size=CH, dtype=np.uint64) for _ in range(4)],
                   np.uint64(0x6A09E667F3BCC908), W)
        s1 = State([w.copy() for w in s0.words], s0.wv, W)
        for i in range(4):
            s1.words[i] = s1.words[i] ^ np.uint64(delta[i])
        for _ in range(R):
            apply_round(OPS, s0)
            apply_round(OPS, s1)
        a = s0.words[0] ^ s1.words[0]
        b = s0.words[1] ^ s1.words[1]
        c = s0.words[2] ^ s1.words[2]
        d = s0.words[3] ^ s1.words[3]
        if W == 8:
            dd = a | (b << 8) | (c << 16) | (d << 24)
        else:
            # full 256-bit packing: 64-bit shifts would truncate
            dd = a.astype(object) | (b.astype(object) << 64) | \
                (c.astype(object) << 128) | (d.astype(object) << 192)
        vals, cnts = np.unique(dd, return_counts=True)
        cnt.update(dict(zip(map(int, vals), map(int, cnts))))
    return max(cnt.values()) / N


def main():
    Rmax = int(sys.argv[1]) if len(sys.argv) > 1 else 6
    nlog = int(sys.argv[2]) if len(sys.argv) > 2 else 24
    W = int(sys.argv[3]) if len(sys.argv) > 3 else 8
    delta = TRAIL_D8 if W == 8 else TRAIL_D8   # same pattern, lifted
    rng = np.random.default_rng(3)
    print(f"W={W} multi-round differential decay (N=2^{nlog} pairs/round):")
    for R in range(1, Rmax + 1):
        p = dp_measure(delta, R, nlog, W)
        if p > 0:
            print(f"  R={R} trail diff: DP={p:.6f} = 2^-{np.log2(1 / p):.2f}  "
                  f"(trail product 2^-{8 * R})  aggregation 2^+{8 * R - np.log2(1 / p):.2f}")
        else:
            print(f"  R={R}: DP < 2^-{nlog} (no collision observed)")
    if W == 8:
        for R in (1, 2):
            ps = []
            for _ in range(4):
                d = tuple(int(x) for x in rng.integers(0, 256, size=4))
                d = tuple(x if x else 1 for x in d)
                ps.append(dp_measure(d, R, nlog, W))
            print(f"  random diffs R={R}: DP = "
                  f"{[f'{p:.3e}' for p in ps]} = 2^-{[f'{np.log2(1 / p):.1f}' if p else 'inf' for p in ps]}")


if __name__ == '__main__':
    main()

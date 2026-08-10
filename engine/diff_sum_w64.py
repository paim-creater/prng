# -*- coding: utf-8 -*-
"""diff_sum_w64.py — W=64 multi-round differential spot-check: the
W=8 trail-optimal difference (u bit 4, v bit 6, w bit 3) lifted to
full width. DP^(R)(Delta) = max_d Pr[Phi^R(x+Delta) ^ Phi^R(x) = d],
R in 1..Rmax with 2^nlog pairs. The paper claims < 2^-24 at R=1,2,22
(no collision in 2^24 pairs) — the first multi-round full-width data
point.

Usage: python diff_sum_w64.py [Rmax] [samples_log2] [rounds_list]
"""
import sys
from collections import Counter
import numpy as np

sys.path.insert(0, '.')
from cipher import State, apply_round, tempest_a1_round_program

OPS = tempest_a1_round_program()
W = 64
TRAIL_D = (1 << 4, 1 << 6, 1 << 3, 0)   # lifted W=8 trail optimum


def dp_measure(delta, R, nlog):
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
        # pack the FULL 256-bit difference into a Python int: the
        # 64-bit-shift packing used earlier truncated (uint64 wraps),
        # merging distinct differences into one bucket
        a = s0.words[0] ^ s1.words[0]
        b = s0.words[1] ^ s1.words[1]
        c = s0.words[2] ^ s1.words[2]
        d = s0.words[3] ^ s1.words[3]
        dd = a.astype(object) | (b.astype(object) << 64) | \
            (c.astype(object) << 128) | (d.astype(object) << 192)
        vals, cnts = np.unique(dd, return_counts=True)
        cnt.update(dict(zip(map(int, vals), map(int, cnts))))
    m = max(cnt.values())
    return m / N, cnt


def main():
    Rmax = int(sys.argv[1]) if len(sys.argv) > 1 else 22
    nlog = int(sys.argv[2]) if len(sys.argv) > 2 else 20
    rs = [int(x) for x in sys.argv[3].split(',')] if len(sys.argv) > 3 else \
        [1, 2, 22]
    print(f"W=64 multi-round DP, lifted trail diff (u4,v6,w3), N=2^{nlog} pairs:")
    for R in rs:
        p, cnt = dp_measure(TRAIL_D, R, nlog)
        if p > 0:
            top = sorted(cnt.items(), key=lambda kv: -kv[1])[:3]
            print(f"  R={R}: DP = {p:.2e} = 2^-{np.log2(1 / p):.2f}   top-d: "
                  + "; ".join(f"0x{d:064x} x{n}" for d, n in top))
        else:
            print(f"  R={R}: DP < 2^-{nlog} (no collision observed)")


if __name__ == '__main__':
    main()

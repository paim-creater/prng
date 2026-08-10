# -*- coding: utf-8 -*-
"""lin_scale.py — linear-side scaling measurement at W=8/16/32.

Protocol (2026-08-09): N samples per mask, 64 single-output-bit masks
(structural) + 128 random masks, R rounds. Mask parity computed on a
single execution's output words. Max |bias| compared against the
multiple-comparisons null: for m independent masks with N samples,
sigma = 1/sqrt(N), E[max] = sigma*sqrt(2 ln 2m).

Result summary (see paper audit): null-consistent at every width —
no linear structure detected up to the sampling floor.
Usage: python lin_scale.py [W] [rounds] [samples_log2]
"""
import sys
import numpy as np

sys.path.insert(0, '.')
from cipher import State, apply_round, tempest_a1_round_program

OPS = tempest_a1_round_program()


def run(W, R, nlog):
    N = 1 << nlog
    rng = np.random.default_rng(7)
    nbits = 4 * W
    masks = []
    for j in range(nbits):                      # single-output-bit masks
        m = [0, 0, 0, 0]
        m[j // W] = 1 << (j % W)
        masks.append(tuple(m))
    for _ in range(128):                        # random masks
        # dtype=uint64 needed: at W=64, high=2^64 overflows int64
        masks.append(tuple(int(x) for x in rng.integers(0, 1 << W, size=4,
                                                        dtype=np.uint64)))
    m = len(masks)
    ones = np.zeros(m, dtype=np.int64)
    CH = 1 << 18
    for ci in range(N // CH):
        s = State([rng.integers(0, 1 << W, size=CH, dtype=np.uint64) for _ in range(4)],
                  np.uint64(0x6A09E667F3BCC908), W)
        for _ in range(R):
            apply_round(OPS, s)
        w = [s.words[i].astype(np.uint64) for i in range(4)]
        for i, (m0, m1, m2, m3) in enumerate(masks):
            p = (w[0] & np.uint64(m0)) ^ (w[1] & np.uint64(m1)) ^ \
                (w[2] & np.uint64(m2)) ^ (w[3] & np.uint64(m3))
            ones[i] += int(np.count_nonzero(np.bitwise_count(p) & np.uint64(1)))
    bias = np.abs(ones / N - 0.5) * 2
    mx = float(bias.max())
    sigma = 1.0 / np.sqrt(N)
    floor = sigma * np.sqrt(2 * np.log(2 * m))
    print(f"W={W} R={R} N=2^{nlog} masks={m}: max|bias| = {mx:.6f} = 2^-{np.log2(1/mx):.2f}"
          f"  (null E[max] = {floor:.6f} = 2^-{np.log2(1/floor):.2f})  "
          f"{'null-consistent' if mx < 1.5 * floor else 'ABOVE null'}")
    sb = bias[:nbits]
    print(f"  single-bit masks: max {sb.max():.6f} (2^-{np.log2(1/sb.max()):.2f})")


if __name__ == '__main__':
    W = int(sys.argv[1]) if len(sys.argv) > 1 else 8
    R = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    nl = int(sys.argv[3]) if len(sys.argv) > 3 else 24
    run(W, R, nl)

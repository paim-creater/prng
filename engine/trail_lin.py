# -*- coding: utf-8 -*-
"""trail_lin.py — exact linear-side audit of the W=4 rounds (shadow /
cascade k=2 / k=4), true Walsh-Hadamard transform (FWHT).

Background: a per-AND "linear trail weight" MILP model was built and
then REJECTED — at W=4 the exact correlation is not determined by any
simple active-AND count (the best input-mask-to-output-mask pair has
|corr| = 2^-4.712 for the cascade, while the naive model predicted a
weight of 104). Exact WHT values are the ground truth instead.

Two conventions, both computed exactly over the full 2^16 domain:
  (i)   input-mask-to-single-output-bit  (max over input masks of the
        correlation of output bit 0 with u.x);
  (ii)  input x output mask (global max over both masks).
Results (2026-08-09, with-key rounds):
  shadow k=0: (i) 2^-2.000   (ii) 2^-1.000
  cascade k=2: (i) 2^-4.871  (ii) 2^-3.810
  cascade k=4: (i) 2^-5.667  (ii) 2^-4.712
The earlier paper values 2^-3.000 / 2^-4.415 / 2^-5.385 were computed
in an unrecorded convention; the k=4 value is within 0.3 bit of (ii).
Usage: python trail_lin.py
"""
import sys
import numpy as np

sys.path.insert(0, '.')
from cipher import State, apply_round, tempest_a1_round_program
from min_shadow_rank import truncate_at_levels

W = 4
N = 1 << 16


def fwht1d(f):
    h = f.astype(np.float64).copy()
    step = 1
    while step < N:
        h = h.reshape(-1, step * 2)
        a = h[:, :step].copy()
        b = h[:, step:].copy()
        h[:, :step] = a + b
        h[:, step:] = a - b
        step *= 2
    return h.reshape(N)


def round_out(ops, x):
    s = State([np.uint64((x >> 0) & 0xF), np.uint64((x >> 4) & 0xF),
               np.uint64((x >> 8) & 0xF), np.uint64((x >> 12) & 0xF)],
              np.uint64(0x6A09E667F3BCC908), W)
    apply_round(ops, s)
    return int(s.words[0]) | (int(s.words[1]) << 4) | (int(s.words[2]) << 8) | (int(s.words[3]) << 12)


def audit(ops, tag):
    y = np.array([round_out(ops, x) for x in range(N)], dtype=np.int64)
    # (i) bit 0: one WHT
    T = np.where(((y & 1) == 0), 1.0, -1.0)
    C = fwht1d(T)
    b0 = np.max(np.abs(C[1:])) / N
    # (ii) global (u,v): chunked WHT over columns v
    best = 0.0
    CH = 128
    for v0 in range(1, N, CH):
        vv = np.arange(v0, min(v0 + CH, N), dtype=np.int64)
        ch = len(vv)
        par = np.zeros((N, ch), dtype=np.uint8)
        for b in range(16):
            bit = (vv >> b) & 1
            if bit.any():
                sel = ((y >> b) & 1).astype(np.uint8)
                par ^= sel[:, None] & bit.astype(np.uint8)[None, :]
        B = np.where(par, -1.0, 1.0)
        # FWHT along axis 0 (each column independently)
        h = B.astype(np.float64)
        step = 1
        while step < N:
            h2 = h.reshape(-1, step * 2, ch)
            a = h2[:, :step, :].copy()
            b = h2[:, step:, :].copy()
            h2[:, :step, :] = a + b
            h2[:, step:, :] = a - b
            step *= 2
        m = np.max(np.abs(h[1:, :]))
        if m > best:
            best = m
    bj = best / N
    print(f"{tag}: bit0口径 2^-{np.log2(1 / b0):.3f}  (u,v)联合口径 2^-{np.log2(1 / bj):.3f}")


def main():
    audit(truncate_at_levels(tempest_a1_round_program(), 0, include_premix=False),
          "shadow k=0")
    audit(truncate_at_levels(tempest_a1_round_program(), 2, include_premix=True),
          "cascade k=2")
    audit(tempest_a1_round_program(), "cascade k=4")


if __name__ == '__main__':
    main()

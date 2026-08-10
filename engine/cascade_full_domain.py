# -*- coding: utf-8 -*-
"""cascade_full_domain.py — full-domain exact DDTmax for cascade truncations.

The paper's cascade-depth table reports -log2 DP(1) in {5.00, 8.00, 8.00,
7.86, 7.86} for andmix4 cascade levels k = 0..4, measured by enumerating
2^16 states over 2,184 input differences (no-key variant, matching
dp_nonlinearity.py). Here we recompute the same quantities EXACTLY over
all 2^16 - 1 differences, validating the truncation semantics against the
paper's k=0 value (5.00) and k=4 value (7.86 -> exact 7.80).
"""
import numpy as np
import time, json

from cipher import tempest_a1_round_program

W = 4
MASK = np.uint16((1 << W) - 1)
IDX = {'u': 0, 'v': 1, 'w': 2, 'z': 3}
NIN = 1 << (4 * W)
IDX_AR = np.arange(NIN, dtype=np.uint16)


def rotl16(x, r):
    r %= W
    return np.uint16(((x << r) & MASK) | (x >> (W - r)))


def apply_round_vec(st, ops):
    for op in ops:
        t = op[0]
        if t == 'SNAP':
            pass
        elif t == 'X3':
            w, a, b, r1, r2 = IDX[op[1]], IDX[op[2]], IDX[op[3]], op[4], op[5]
            st[:, w] = (st[:, w] ^ rotl16(st[:, a], r1)
                        ^ rotl16(st[:, b], r2)) & MASK
        elif t == 'AND':
            w, a, b, r1, r2 = IDX[op[1]], IDX[op[2]], IDX[op[3]], op[4], op[5]
            st[:, w] = (st[:, w] ^ (rotl16(st[:, a], r1)
                                    & rotl16(st[:, b], r2))) & MASK
        elif t == 'A3':
            w, r1, r2, r3, r4 = IDX[op[1]], op[2], op[3], op[4], op[5]
            v = st[:, w]
            st[:, w] = (v ^ rotl16(v, r1) ^ rotl16(v, r2)
                        ^ (rotl16(v, r3) & rotl16(v, r4))) & MASK
        elif t == 'A2':
            w, r1, r2 = IDX[op[1]], op[2], op[3]
            v = st[:, w]
            st[:, w] = (v ^ rotl16(v, r1) ^ rotl16(v, r2)) & MASK
        elif t == 'CONST':
            w, c = IDX[op[1]], op[2] & 0xF
            st[:, w] = (st[:, w] ^ np.uint16(c)) & MASK
    return st


def truncate(ops, k):
    """Keep the first k andmix4 levels (Levels 1..k); drop levels k+1..4.
    Level groups start at the SNAP after the Phase-C premix."""
    # locate the four level-start SNAP indices (SNAPs after the A3 premix)
    snap_idx = [i for i, op in enumerate(ops) if op[0] == 'SNAP']
    # ops layout: SNAP(0) [Phase A], SNAP(1) [Phase A(lin)?? no], ...
    # Phase A starts after SNAP 0; Phase B has none; Phase C A3s; then
    # Level1 SNAP, Level2 SNAP, [premix2], Level3 SNAP, Level4 SNAP,
    # Phase D SNAP. Level starts: the 2nd, 3rd SNAPs after the last A3.
    a3_idx = [i for i, op in enumerate(ops) if op[0] == 'A3']
    first_level = min(i for i in snap_idx if i > max(a3_idx))
    level_starts = [i for i in snap_idx if i >= first_level][:4]
    cut = level_starts[k] if k < 4 else len(ops)
    return ops[:cut]


def main():
    base = tempest_a1_round_program()
    rows = []
    for k in range(5):
        ops = truncate(base, k)
        codes = IDX_AR
        st = np.zeros((NIN, 4), dtype=np.uint16)
        for wi in range(4):
            st[:, wi] = (codes >> (wi * W)) & MASK
        st = apply_round_vec(st, ops)
        T = (st[:, 0] | (st[:, 1] << W) | (st[:, 2] << (2 * W))
             | (st[:, 3] << (3 * W))).astype(np.uint16)
        # full-domain DDT max over all 65535 deltas
        ddt_max = 0
        t0 = time.time()
        for di in range(1, NIN):
            dT = T[IDX_AR ^ np.uint16(di)] ^ T
            m = int(np.bincount(dT.astype(np.int64), minlength=NIN).max())
            if m > ddt_max:
                ddt_max = m
        ddp = -np.log2(ddt_max / NIN)
        rows.append({'k': k, 'ddt_max_dlog2': round(ddp, 4),
                     'ops': len(ops)})
        print(f'k={k}: -log2 DDTmax = {ddp:.4f} (paper: '
              f'{["5.00","8.00","8.00","7.86","7.86"][k]}) '
              f'({time.time()-t0:.0f}s)', flush=True)
    with open('cascade_full_domain.json', 'w') as f:
        json.dump(rows, f, indent=1)


if __name__ == '__main__':
    main()

# -*- coding: utf-8 -*-
"""explore_cascade_degree.py — the cascade degree law, W=4 full domain.

The algebraic side of AM-SEV's exact triple metric:

  Q1 (cascade degree law): each cascade level multiplies the algebraic
     degree by 2 (each AND doubles degree), so deg(Phi_C) = 2^C for a
     C-level cascade, capped by the 16-variable ceiling at W=4.  Verify
     exactly for C = 0..4 (truncate_at_levels).

  Q2 (cross-round curve): deg(Phi^R) for R = 1..6 (single round is
     already degree 16 = full at W=4, so the curve is flat).

  Q3 (differential-map degree): deg(D_R(0x1)) for R = 1..6, the
     Differential-Map Degree Theorem's multi-round counterpart
     (deg(D_R) <= deg(Phi^R) - 1).

Method: full 2^16-domain ANF degree via Mobius (zeta) transform on each
output bit; interpreter from audit_true_algorithm1.py.
"""
import numpy as np
import json, time, sys

sys.path.insert(0, '.')
from audit_true_algorithm1 import (apply_round_snap, anf_degree, W, MASK,
                                   NIN, truncate_at_levels)
from cipher import tempest_a1_round_program


def round_table(ops, R, wv0=np.uint16(0x8)):
    codes = np.arange(NIN, dtype=np.uint16)
    st = np.zeros((NIN, 4), dtype=np.uint16)
    for wi in range(4):
        st[:, wi] = (codes >> (wi * W)) & MASK
    wv = [wv0, np.uint16(0)]
    for _ in range(R):
        st, wv = apply_round_snap(st, ops, wv)
    return (st[:, 0] | (st[:, 1] << W) | (st[:, 2] << (2 * W))
            | (st[:, 3] << (3 * W))).astype(np.uint16)


def max_degree(T):
    return max(anf_degree((T >> j) & 1) for j in range(16))


def main():
    t0 = time.time()
    base = tempest_a1_round_program()
    res = {'meta': 'cascade degree law and differential-degree curve, '
                   'W=4 full domain (snapshot semantics)'}

    # Q1: degree vs number of cascade levels
    res['cascade_degree'] = []
    for k in range(5):
        ops_k = truncate_at_levels(base, k)
        T = round_table(ops_k, 1)
        deg = max_degree(T)
        res['cascade_degree'].append({'levels': k, 'deg(Phi)': deg})
        print(f'levels={k}: deg(Phi) = {deg}', flush=True)

    # Q2/Q3: cross-round degree of Phi^R and D_R(0x1)
    res['cross_round'] = []
    Tprev = None
    for R in range(1, 7):
        T = round_table(base, R)
        degp = max_degree(T)
        D = T ^ (T[np.roll(np.arange(NIN), -1)])  # placeholder, fixed below
        # D_R(0x1)(s) = T[s^1] ^ T[s]
        D = T[np.arange(NIN, dtype=np.uint16) ^ np.uint16(1)] ^ T
        degd = max_degree(D)
        res['cross_round'].append({'R': R, 'deg(Phi^R)': degp, 'deg(D_R)': degd})
        print(f'R={R}: deg(Phi^R)={degp}  deg(D_R(0x1))={degd}', flush=True)

    res['elapsed_s'] = round(time.time() - t0, 1)
    with open('explore_cascade_degree.json', 'w') as f:
        json.dump(res, f, indent=1)
    print(f'wrote explore_cascade_degree.json ({time.time()-t0:.0f}s)')


if __name__ == '__main__':
    main()

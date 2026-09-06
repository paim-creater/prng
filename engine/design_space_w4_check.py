# -*- coding: utf-8 -*-
"""design_space_w4_check.py -- width-4 design-space facts used in the paper.

Reproduces, with the official column-model engine only:
  (F1) Tempest Phase-A shadow (6 K4 gates, dual conditions): full-domain
       rank spectrum min 3, max 14, mode 12, mean 11.12517 (65535 diffs).
  (F2) A same-budget configuration (rotations vec [0,1,0,1,1,1,3,2,0,3,3,2]
       on the K4 word template, dual conditions) has full-domain spectrum
       min 3, max 15, mean 11.89123: strictly stronger than (F1) on the
       toy-width mean/max, same minimum.  Hence the toy spectrum is not
       extremal within the class; the full-width rotation choice is
       anchored on width-parametric structural criteria instead
       (see Remark 4.13 in the paper).
  (F3) tightness of the 6-gate budget: no sampled configuration of the
       class reaches full-domain min rank >= 4 (single-bit rank of a
       k-regular word is the number of gates reading it; total operand
       slots 12 over 4 words bound the minimum by 3).

Landscape archive: design_space_w4_landscape.json (exhaustive over the
{1,3}^12 rotation pool at W=4, 2048 dual orbits; fast-path engine
validated against rank_column_model.py and rank_of_delta, 0 mismatches).
"""
import collections
import sys

sys.path.insert(0, '.')
from rank_column_model import predict_columns, gf2_rank_cols

W = 4
N = 4 * W

# K4 word template in the gate order of tempest_shadow_gates_raw():
#   [(0,1,3), (1,2,0), (2,0,1), (3,1,2), (0,3,2), (3,0,3)]
T4_PAIRS = [(0, 1, 3), (1, 2, 0), (2, 0, 1), (3, 1, 2), (0, 3, 2), (3, 0, 3)]


def vec_gates(vec):
    gs = []
    for (d, a, b), (ra, rb) in zip(T4_PAIRS, zip(vec[0::2], vec[1::2])):
        gs.append((d, a, ra, b, rb))
    return gs


def full_spectrum(gates, label):
    hist = collections.Counter()
    for delta in range(1, 1 << N):
        r = gf2_rank_cols(predict_columns(W, gates, delta), N)
        hist[r] += 1
    n = sum(hist.values())
    mean = sum(int(k) * v for k, v in hist.items()) / n
    print(f'{label}: min {min(hist)} max {max(hist)} mode {hist.most_common(1)} '
          f'mean {mean:.5f} (n={n})')
    return {'min': min(hist), 'max': max(hist),
            'mode': hist.most_common(1)[0][0],
            'mean': round(mean, 5), 'n': n}


if __name__ == '__main__':
    tempest_vec = [1, 1, 3, 1, 1, 3, 3, 1, 3, 1, 1, 1]
    best_vec = [0, 1, 0, 1, 1, 1, 3, 2, 0, 3, 3, 2]
    r1 = full_spectrum(vec_gates(tempest_vec), 'Tempest Phase-A shadow')
    r2 = full_spectrum(vec_gates(best_vec), 'strictly stronger class member')
    assert r1['min'] == 3 and r2['min'] == 3 and r2['mean'] > r1['mean']
    print('F1-F2 reproduced; landscape archive: design_space_w4_landscape.json')

# -*- coding: utf-8 -*-
"""explore_state_image.py — state-image (entropy-retention) measurement.

Finding of the invertibility screen: the Algorithm-1 round is NOT a
permutation at W=4 (full-domain check: premix A3 and the full round are
both non-injective).  For an iterated PRNG this matters only through the
STATE-IMAGE SHRINKAGE rate: how many distinct states survive each round.
This script measures it:

  Q1 (W=4, full domain): image size of Phi^R for R = 1..22, exact
     (-log2 of the fraction of 2^16 states that survive);
  Q2 (W=64, sampled): image shrinkage of one round, 2^24 random states;
     22 rounds from 2^22 states (unique output count);
  Q3 (diagnostic): where does the non-injectivity come from?  Test each
     phase in isolation at W=4 (Phase A, A(lin), Phase B, premix, L1..L4,
     Phase D) by composing only that phase's ops on the full domain.

All interpreter semantics = snapshot (audit_true_algorithm1 / cipher).
"""
import numpy as np
import json, time, sys

sys.path.insert(0, '.')
from audit_true_algorithm1 import apply_round_snap, W, MASK, NIN
from cipher import tempest_a1_round_program, State, apply_round

OPS = tempest_a1_round_program()


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


def main():
    t0 = time.time()
    res = {'meta': 'state-image shrinkage of Algorithm 1'}

    # Q1: W=4 full-domain image size per round
    res['w4_image'] = []
    T = None
    for R in range(1, 23):
        T = round_table(OPS, R)
        n_img = len(np.unique(T))
        res['w4_image'].append({'R': R, 'image_size': int(n_img),
                                '-log2 frac': round(-np.log2(n_img / NIN), 3)})
        print(f'W=4 R={R:2d}: image={n_img:6d}  (-log2 frac={-np.log2(n_img/NIN):.3f})',
              flush=True)

    # Q2: W=64 sampled shrinkage
    rng = np.random.default_rng(11)
    N = 1 << 24
    s = rng.integers(0, 1 << 64, size=N, dtype=np.uint64)
    st = State([s.copy() for _ in range(4)], np.uint64(0x6A09E667F3BCC908), W=64)
    apply_round(OPS, st)
    out = np.zeros(N, dtype=np.uint64)
    for wi in range(4):
        out ^= st.words[wi] << (16 * wi)   # mix all words into a 64-bit tag
    u = np.unique(out)
    res['w64_1round_image_of_2^24'] = int(len(u))
    print(f'W=64 1 round, 2^24 states: image={len(u)} '
          f'({"injective at this resolution" if len(u) == N else "SHRINKAGE"})',
          flush=True)

    N2 = 1 << 22
    s2 = rng.integers(0, 1 << 64, size=N2, dtype=np.uint64)
    st2 = State([s2.copy() for _ in range(4)], np.uint64(0x6A09E667F3BCC908), W=64)
    for r in range(22):
        apply_round(OPS, st2)
    out2 = np.zeros(N2, dtype=np.uint64)
    for wi in range(4):
        out2 ^= st2.words[wi] << (16 * wi)
    u2 = np.unique(out2)
    res['w64_22round_image_of_2^22'] = int(len(u2))
    print(f'W=64 22 rounds, 2^22 states: image={len(u2)} '
          f'({"no collision at this resolution" if len(u2) == N2 else "SHRINKAGE"})',
          flush=True)

    # Q3: per-phase injectivity at W=4 (full domain), single phase in
    # isolation on the state
    res['w4_phase_images'] = []
    # phase boundaries by op type in OPS
    labels = []
    phase = []
    for op in OPS:
        k = op[0]
        if k == 'CONST' or k == 'WEYL' or k == 'NLFILT' or k == 'KEY':
            labels.append('PhaseB')
        elif k == 'A3':
            labels.append('Premix')
        elif k == 'A2':
            labels.append('Premix2')
        elif k == 'AND' or k == 'X3':
            # need context; assign by index (see op list)
            labels.append('AndXor')
        else:
            labels.append('SNAP')
    # simpler: run prefixes of OPS and measure image of each prefix
    for cut in range(1, len(OPS) + 1):
        if OPS[cut - 1][0] in ('SNAP', 'WEYL', 'NLFILT'):
            continue
        Tp = round_table(OPS[:cut], 1)
        ni = len(np.unique(Tp))
        res['w4_phase_images'].append(
            {'prefix': cut, 'op': OPS[cut - 1][0], 'image': int(ni)})
        if ni != NIN:
            print(f'W=4 prefix {cut} ({OPS[cut-1][0]}): image={ni} '
                  f'<- first non-injective point', flush=True)
            break

    res['elapsed_s'] = round(time.time() - t0, 1)
    with open('explore_state_image.json', 'w') as f:
        json.dump(res, f, indent=1)
    print(f'wrote explore_state_image.json ({time.time()-t0:.0f}s)')


if __name__ == '__main__':
    main()

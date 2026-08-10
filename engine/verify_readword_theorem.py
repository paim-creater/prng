# -*- coding: utf-8 -*-
"""verify_readword_theorem.py — experimental test of the Read-Word
Polar-Rank Theorem:

  Two-layer AND-RX round (snapshot operands). If every word is read as
  an operand by at least k AND gates, and the AND gates reading a given
  word have pairwise-distinct (dst_word, rotation) columns, then
  min_{Delta != 0} rank(B_Delta) >= k, and any single-bit difference
  attains exactly k (when every word is read by exactly k gates).

  Hence DP(1) = 2^{-k} EXACTLY for the whole design class — a
  structural lower bound on any such design, independent of the
  specific rotation constants (beyond the non-degeneracy check).

Protocol: random two-layer AND-RX designs (4 words, k ANDs reading
each word, random rotations, non-degeneracy enforced), W=8; verify
  (1) all single-bit differences have rank exactly k,
  (2) a random-difference scan never finds rank < k.
"""
import numpy as np
import json, time

from cipher import State, apply_round, U64
from min_shadow_rank import polar_matrices, rank_of_delta, truncate_at_levels
from cipher import tempest_a1_round_program


def build_design(W, k, rng, words=('u', 'v', 'w', 'z')):
    """Random two-layer AND-RX design: Phase-A style, each word read by
    exactly k AND gates (operands from the round-start snapshot), all
    other ops linear (XOR-ROT). Non-degeneracy: the k gates reading a
    word have distinct (dst, rotation) columns."""
    idx = {'u': 0, 'v': 1, 'w': 2, 'z': 3}
    ops = [('SNAP',)]
    # XOR-ROT linear mixing (Phase D style) so the round is nontrivial
    ops.append(('X3', 'u', 'v', 'w', 3, 9, 1))
    ops.append(('X3', 'v', 'w', 'z', 5, 11, 1))
    ops.append(('X3', 'w', 'z', 'u', 9, 13, 1))
    ops.append(('X3', 'z', 'u', 'v', 11, 17, 1))
    # for each source word src, k AND gates with src as operand a:
    #   dst ^= rotl(snap[src], ra) & rotl(snap[other], rb)
    used = {w_: set() for w_ in words}
    for src in words:
        made = 0
        tries = 0
        while made < k and tries < 200:
            tries += 1
            dst = words[int(rng.integers(0, 4))]
            others = [x for x in words if x != src]
            b = others[int(rng.integers(0, 3))]
            ra = int(rng.integers(1, W))
            rb = int(rng.integers(1, W))
            col = (dst, ra)
            if col in used[src]:
                continue
            used[src].add(col)
            ops.append(('AND', dst, src, b, ra, rb, 1))
            made += 1
    return ops


def main():
    rng = np.random.default_rng(2026)
    W = 8
    results = {}
    n_designs = 12
    for k in (1, 2, 3, 4):
        fails = 0
        min_rank_scan = []
        for di in range(n_designs):
            ops = build_design(W, k, rng)
            # single-bit ranks
            ranks = [rank_of_delta(W, ops, 1 << b)[0] for b in range(4 * W)]
            sb_min, sb_max = min(ranks), max(ranks)
            # random scan
            scan_min = 99
            for _ in range(120):
                d = int(rng.integers(1, 1 << (4 * W)))
                r_ = rank_of_delta(W, ops, d)[0]
                scan_min = min(scan_min, r_)
            ok = (sb_min == k and sb_max == k and scan_min >= k)
            if not ok:
                fails += 1
                print(f'  FAIL k={k} design {di}: single-bit {sb_min}..{sb_max}, '
                      f'scan min {scan_min}', flush=True)
            min_rank_scan.append(scan_min)
        results[k] = {'designs': n_designs, 'fails': fails,
                      'scan_min_min': min(min_rank_scan)}
        print(f'k={k}: {n_designs} designs, fails={fails}, '
              f'scan-min across designs={min(min_rank_scan)}', flush=True)
    # also verify the actual Phase-A shadow satisfies k=3 (its structure)
    OPS = tempest_a1_round_program()
    SH = truncate_at_levels(OPS, 0, include_premix=False)
    ranks = [rank_of_delta(W, SH, 1 << b)[0] for b in range(4 * W)]
    print(f'Algorithm-1 shadow W=8: single-bit ranks min={min(ranks)} max={max(ranks)} '
          f'(k=3 read-word count)', flush=True)
    results['shadow_a1'] = {'single_bit_min': min(ranks), 'single_bit_max': max(ranks)}
    json.dump(results, open('verify_readword_theorem.json', 'w'), indent=1)
    print('saved verify_readword_theorem.json')


if __name__ == '__main__':
    main()

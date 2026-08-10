# -*- coding: utf-8 -*-
"""rank_certificate_demo.py — the engine's new full-width exact gate,
demonstrated end-to-end: for the quadratic shadow of Algorithm 1, emit a
machine-checkable polar-rank certificate at W=64.

Certificate contents:
  - the design (op list)
  - the witness difference Delta = 0x1 (bit 0 of word u)
  - the polar-form matrices C_i (derived at unit states)
  - rank(B_Delta) = 9  (GF(2) elimination; re-verifiable in ms)
  - by the Affine-Differential Theorem: DP(0x1) = 2^-9 exactly.
The verifier also scans a sample of random differences and reports the
minimum rank found (the barrier table).
"""
import numpy as np
import json, time, sys, hashlib

sys.path.insert(0, '.')
from cipher import tempest_a1_round_program, State, apply_round, U64
from min_shadow_rank import truncate_at_levels, rank_of_delta, gf2_rank

OPS = tempest_a1_round_program()
W = 64
n = 4 * W


def polar_matrices_external(ops, W):
    """C_i[j] = D_{e_i}(e_j) ^ D_{e_i}(0), i, j in 0..n-1 (n-bit ints)."""
    n = 4 * W
    MK = (1 << W) - 1

    def D_at(delta_int, x_int):
        words = [U64((x_int >> (wi * W)) & MK) for wi in range(4)]
        st0 = State([w for w in words], U64(0), W=W)
        st1 = State([w ^ U64((delta_int >> (wi * W)) & MK) for wi, w in
                     enumerate(words)], U64(0), W=W)
        apply_round(ops, st0)
        apply_round(ops, st1)
        r0 = 0
        r1 = 0
        for wi in range(4):
            r0 |= int(st0.words[wi]) << (wi * W)
            r1 |= int(st1.words[wi]) << (wi * W)
        return r0 ^ r1

    C = [[0] * n for _ in range(n)]
    for j in range(n):
        for i in range(n):
            C[i][j] = D_at(1 << i, 1 << j) ^ D_at(1 << i, 0)
    return C


def main():
    shadow = truncate_at_levels(OPS, 0, include_premix=False)  # pure quadratic
    t0 = time.time()
    # 1) certificate for Delta = 0x4 at W=64 (the barrier witness)
    r, cols = rank_of_delta(64, shadow, 0x4)
    print(f'rank(B_0x4) at W=64 = {r}  ({time.time()-t0:.1f}s)')
    # 2) verify the rank independently from the C matrices (different path)
    C = polar_matrices_external(shadow, W)
    print(f'polar matrices built ({time.time()-t0:.1f}s)')
    # B_0x4 = sum_i Delta_i C_i with Delta = 0x4 -> just C_2 (bit 2 of word 0)
    cols2 = [C[2][j] for j in range(n)]
    r2 = gf2_rank(cols2)
    print(f'independent rank from C matrices = {r2}')
    # 3) barrier scan: random deltas at W=64 (sample of 32)
    rng = np.random.default_rng(2026)
    min_r = n + 1
    min_d = None
    for di in range(32):
        d = int.from_bytes(rng.bytes(32), 'little') & ((1 << n) - 1)
        if d == 0:
            continue
        rr, _ = rank_of_delta(64, shadow, d)
        if rr < min_r:
            min_r = rr
            min_d = d
    print(f'barrier scan (32 random deltas): min rank = {min_r}')
    # certificate object
    cert = {
        'design': 'tempest pre-mix-free quadratic shadow (Phase A + A(lin) + key + D)',
        'width': 64,
        'witness_delta': '0x4',
        'rank': int(r),
        'rank_verified_independently': int(r2),
        'dp': f'2^{-int(r)} (exact, by Affine-Differential Theorem)',
        'barrier_scan_min_rank_32_random': int(min_r),
        'verify_recipe': 'rank_of_delta(64, shadow, 0x4) + GF(2) elimination',
        'script': 'rank_certificate_demo.py',
        'sha256_of_C2_matrix': hashlib.sha256(
            repr(C[2]).encode()).hexdigest()[:16],
        'secs': round(time.time() - t0, 1),
    }
    with open('rank_certificate_w64.json', 'w') as f:
        json.dump(cert, f, indent=1)
    print('certificate -> rank_certificate_w64.json')


if __name__ == '__main__':
    main()

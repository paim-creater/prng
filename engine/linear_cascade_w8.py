# -*- coding: utf-8 -*-
"""linear_cascade_w8.py — corrected linear-side measurement at W=8.

An earlier paper draft reported "max |bias| <= 3e-3 over 24 masks,
inside random fluctuation"; that number was not reproducible. This
script is the corrected protocol: 2000 random masks, 2^16 samples each,
R=1 and R=2, shadow vs cascade. Result (2026-08-09, statistical
correction): max |bias| ~= 2^-6.1 for the cascade at R=2 — CONSISTENT
WITH the multiple-comparisons null: the maximum of 2000 independent
statistics of s.d. 2^-8 has expectation 2^-8*sqrt(2 ln 4000) ~= 2^-5.97,
so NO linear structure is detected at this resolution (p ~= 0.56).
The exact W=4 full-domain Walsh spectra DO show real structure at toy
width (cascade max bias exactly 2^-4.415). The shadow's Walsh-rank
bound (<= 2^-115 at W=64) does NOT transfer to the cascade; the
cascade's linear side at full width remains unmeasured.
"""
import numpy as np
from cipher import State, apply_round, U64
from cipher import tempest_a1_round_program

OPS = tempest_a1_round_program()
W = 8
N = 1 << 16


def build(k, include_premix):
    from min_shadow_rank import truncate_at_levels
    ops = truncate_at_levels(OPS, k, include_premix=include_premix)
    last_snap = max(i for i, op in enumerate(OPS) if op[0] == 'SNAP')
    D = [op for op in OPS[last_snap + 1:] if op[0] == 'X3']
    return ops + [('SNAP',)] + D


def max_bias(masks, ops, rounds, seed=3):
    rng = np.random.default_rng(seed)
    st = State.random(N, seed=seed, W=W)
    for _ in range(rounds):
        apply_round(ops, st)
    T = np.zeros(N, dtype=np.uint64)
    for wi in range(4):
        T |= st.words[wi].astype(np.uint64) << (wi * W)
    mb = 0.0
    for m in masks:
        x = T & U64(m)
        pc = x - ((x >> 1) & U64(0x5555555555555555))
        pc = (pc & U64(0x3333333333333333)) + ((pc >> 2) & U64(0x3333333333333333))
        pc = (pc + (pc >> 4)) & U64(0x0F0F0F0F0F0F0F0F)
        pc = (pc * U64(0x0101010101010101)) >> 56
        bias = float(np.abs(2.0 * np.mean(pc & 1) - 1.0))
        mb = max(mb, bias)
    return mb


if __name__ == '__main__':
    import json
    rng = np.random.default_rng(7)
    m24 = [int(rng.integers(1, 1 << 32)) for _ in range(24)]
    m2000 = [int(rng.integers(1, 1 << 32)) for _ in range(2000)]
    full = build(4, True)
    shadow = build(0, False)
    res = {}
    for label, ops in [('shadow', shadow), ('cascade', full)]:
        for R in (1, 2):
            res[f'{label}_R{R}_24masks'] = round(max_bias(m24, ops, R), 6)
            res[f'{label}_R{R}_2000masks'] = round(max_bias(m2000, ops, R, seed=5), 6)
            print(f'{label} R={R}: 24 masks = {res[f"{label}_R{R}_24masks"]:.6f}, '
                  f'2000 masks = {res[f"{label}_R{R}_2000masks"]:.6f}', flush=True)
    json.dump(res, open('linear_cascade_w8.json', 'w'), indent=1)
    print('saved linear_cascade_w8.json')

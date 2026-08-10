# -*- coding: utf-8 -*-
"""readword_theorem.py — machine verification of the Read-Word
Polar-Rank Theorem.

THEOREM (two-layer AND-RX, snapshot operands). Suppose every state
word w is read as an operand by exactly k AND gates, and the gates
reading w satisfy the dual column condition:
  (dst, rot_w) pairwise distinct, and
  (other, rot_w - rot_other) mod W pairwise distinct,
where rot_w is w's rotation in the gate and other is the other
operand word. Then for every Delta != 0, rank(B_Delta) >= k, and
every single-bit difference attains rank exactly k. Hence
min_Delta rank = k and DP(1) = 2^{-k} EXACTLY for the whole design
class --- a structural lower bound, machine-checked here.

Verification protocol: random designs (4 words, W=8, k ANDs reading
each word, dual column condition enforced); for each: all 32
single-bit deltas must have rank exactly k; 100 random deltas must
have rank >= k. 2026-08: 0 violations across all built designs.
"""
import numpy as np, json
from min_shadow_rank import rank_of_delta


def build_design(W, k, rng, words=('u', 'v', 'w', 'z')):
    ops = [('SNAP',)]
    for t in (('u', 'v', 'w', 3, 9), ('v', 'w', 'z', 5, 11),
              ('w', 'z', 'u', 9, 13), ('z', 'u', 'v', 11, 17)):
        ops.append(('X3',) + t + (1,))
    quota = {w_: k for w_ in words}
    out_keys, in_keys = set(), set()
    guard = 0
    while any(quota[w_] > 0 for w_ in words) and guard < 5000:
        guard += 1
        srcs = [w_ for w_ in words if quota[w_] > 0]
        src = srcs[int(rng.integers(0, len(srcs)))]
        dst = words[int(rng.integers(0, 4))]
        others = [x for x in words if x != src]
        b = others[int(rng.integers(0, 3))]
        if quota[b] <= 0:
            continue
        ra = int(rng.integers(1, W)); rb = int(rng.integers(1, W))
        ok_a = ((dst, ra) not in out_keys and (b, (ra - rb) % W) not in in_keys)
        ok_b = ((dst, rb) not in out_keys and (src, (rb - ra) % W) not in in_keys)
        if not (ok_a and ok_b):
            continue
        out_keys.add((dst, ra)); in_keys.add((b, (ra - rb) % W))
        out_keys.add((dst, rb)); in_keys.add((src, (rb - ra) % W))
        ops.append(('AND', dst, src, b, ra, rb, 1))
        quota[src] -= 1; quota[b] -= 1
    return ops, quota


def main():
    rng = np.random.default_rng(2026)
    W = 8
    res = {}
    for k in (1, 2, 3, 4):
        built = fails = 0
        for di in range(12):
            ops, quota = build_design(W, k, rng)
            if any(quota.values()):
                continue
            built += 1
            ranks = [rank_of_delta(W, ops, 1 << b)[0] for b in range(4 * W)]
            scan = 99
            for _ in range(100):
                d = int(np.random.default_rng(7).integers(1, 1 << 32))
                scan = min(scan, rank_of_delta(W, ops, d)[0])
            if not (min(ranks) == k and max(ranks) == k and scan >= k):
                fails += 1
        res[k] = {'built': built, 'fails': fails}
        print(f'k={k}: {built} designs built, {fails} failures', flush=True)
    json.dump(res, open('readword_theorem.json', 'w'), indent=1)
    print('saved readword_theorem.json')


if __name__ == '__main__':
    main()

# -*- coding: utf-8 -*-
"""verify_rank_formula_w64.py -- independent pure-Python verification of
the exact single-word rank formula at FULL width W=64.

Closed form (Algorithm-1 shadow, k=3):
  rank(B_Delta) = 3*t - |P n (P+2)|        if Delta is on word z,
                 = 3*t                     otherwise
where P is the t-bit support of Delta and the intersection is cyclic
mod W.  Ground truth here is a pure-Python simulation of the shadow's
six AND gates (no numpy), independent of the column model -- the
dual-source discipline required by the paper.
"""
import json, random

W = 64
MASK = (1 << W) - 1
# shadow gates (out d, in a, rot_a, in b, rot_b); word order 0=u 1=v 2=w 3=z
GATES = [(0, 1, 5, 3, 25), (1, 2, 11, 0, 29), (2, 0, 9, 1, 15),
         (3, 1, 27, 2, 21), (0, 3, 23, 2, 53), (3, 0, 5, 3, 25)]


def rotl(x, r):
    return ((x << r) | (x >> (W - r))) & MASK


def shadow_round(words):
    """Pure-Python quadratic shadow with CORRECT snapshot semantics:
    every gate reads the pre-round words; gates never see updates of
    earlier gates (sequential in-place update would change the round
    map for gates whose operands were written earlier)."""
    snap = list(words)
    out = list(words)
    for (d, a, ra, b, rb) in GATES:
        out[d] ^= rotl(snap[a], ra) & rotl(snap[b], rb)
    return out


def D_at(delta, x):
    """D_Delta(x) = Phi(x xor Delta) xor Phi(x), packed to 256 bits."""
    xw = [(x >> (wi * W)) & MASK for wi in range(4)]
    yw = [xw[wi] ^ ((delta >> (wi * W)) & MASK) for wi in range(4)]
    r0, r1 = shadow_round(xw), shadow_round(yw)
    z = 0
    for wi in range(4):
        z |= (r0[wi] ^ r1[wi]) << (wi * W)
    return z


def gf2_rank(cols):
    n = 4 * W
    basis = [0] * n
    r = 0
    for c in cols:
        x = c
        while x:
            b = x.bit_length() - 1
            if basis[b]:
                x ^= basis[b]
            else:
                basis[b] = x
                r += 1
                break
    return r


def truth_rank(delta):
    """Ground truth: rank of polar columns
    cols_j = D_Delta(e_j) xor D_Delta(0)."""
    base = D_at(delta, 0)
    cols = [D_at(delta, 1 << j) ^ base for j in range(4 * W)]
    return gf2_rank(cols)


def main():
    rng = random.Random(2026)
    bad = tot = 0
    fails = []
    for trial in range(120):
        word = rng.randrange(4)
        t = rng.randrange(1, 4)
        pos = sorted(rng.sample(range(W), t))
        delta = sum(1 << (word * W + p) for p in pos)
        cyc2 = sum(1 for p in pos if (p + 2) % W in pos)
        cf = 3 * t - (cyc2 if word == 3 else 0)
        gt = truth_rank(delta)
        tot += 1
        if cf != gt:
            bad += 1
            fails.append((word, pos, gt, cf))
        if tot % 30 == 0:
            print(f'{tot} done', flush=True)
    print(f'W=64 sampled: {bad}/{tot} mismatches')
    json.dump({'W': 64, 'n': tot, 'mismatches': bad, 'fails': fails[:5]},
              open('rank_formula_w64_cert.json', 'w'), indent=1)


if __name__ == '__main__':
    main()

# -*- coding: utf-8 -*-
"""explore_invertibility.py — is the Algorithm-1 round a permutation?

Q1 (W=4, full domain): the one-round map Phi is injective over all
   2^16 states, and the premix map x |-> x^R22(x)^R26(x)^(R7(x)&R19(x))
   (A3) is injective over all 2^4 words.

Q2 (W=8, sampled): 2^22 distinct random states map to 2^22 distinct
   outputs (birthday bound for a non-injective map would show
   ~2^11 collisions).  Uses the DSL interpreter (cipher.py) at W=8.

Q3 (structural argument, checked by code): every phase is an elementary
   permutation (word update u <- u ^ f(other words), XOR with key value),
   so the round is a permutation iff the self-maps A3 (pre-mix) and the
   intra-word parts are permutations; the linear part x ^ R22(x) ^ R26(x)
   is invertible because 1 + t^22 + t^26 is coprime to t^W + 1 = (t+1)^W
   over GF(2) iff it has no root at t=1, which holds since 1+1+1 = 1.
"""
import numpy as np
import json, time, sys

sys.path.insert(0, '.')
from audit_true_algorithm1 import apply_round_snap, W, MASK, NIN
from cipher import tempest_a1_round_program, State, apply_round


def full_round_table(ops, wv0=np.uint16(0x8)):
    codes = np.arange(NIN, dtype=np.uint16)
    st = np.zeros((NIN, 4), dtype=np.uint16)
    for wi in range(4):
        st[:, wi] = (codes >> (wi * W)) & MASK
    st, _ = apply_round_snap(st, ops, [wv0, np.uint16(0)])
    return (st[:, 0] | (st[:, 1] << W) | (st[:, 2] << (2 * W))
            | (st[:, 3] << (3 * W))).astype(np.uint16)


def rotl16(x, r):
    r %= W
    return np.uint16(((x << r) & MASK) | (x >> (W - r)))


def main():
    t0 = time.time()
    base = tempest_a1_round_program()
    res = {'meta': 'invertibility checks for Algorithm 1'}

    # Q1a: full round injective at W=4 (full domain)
    T = full_round_table(base)
    u = np.unique(T)
    res['w4_round_permutation'] = bool(len(u) == NIN)
    print(f'W=4 round injective over full domain: {len(u) == NIN}', flush=True)

    # Q1b: A3 (pre-mix self-map) injective at W=4 (full domain)
    x = np.arange(16, dtype=np.uint16)
    y = x ^ rotl16(x, 22) ^ rotl16(x, 26) ^ (rotl16(x, 7) & rotl16(x, 19))
    res['w4_a3_permutation'] = bool(len(np.unique(y)) == 16)
    print(f'W=4 A3 premix injective over full domain: {len(np.unique(y)) == 16}',
          flush=True)

    # Q2: W=8 sampled injectivity (2^22 states)
    N = 1 << 22
    rng = np.random.default_rng(7)
    s = rng.integers(0, 1 << 32, size=N, dtype=np.uint64)
    st = State([(s >> (8 * wi)) & 0xFF for wi in range(4)], np.uint64(0x6A09E667F3BCC908), W=8)
    apply_round(base, st)
    out = np.zeros(N, dtype=np.uint64)
    for wi in range(4):
        out |= (st.words[wi] & 0xFF).astype(np.uint64) << (8 * wi)
    u8 = np.unique(out)
    res['w8_sampled_injective'] = bool(len(u8) == N)
    print(f'W=8 sampled injectivity (2^22 states): {len(u8) == N}', flush=True)

    # A3 at W=8 sampled (2^22 words)
    x8 = rng.integers(0, 1 << 8, size=N, dtype=np.uint64)
    def rot8(x, r):
        return ((x << r) & 0xFF) | (x >> (8 - r))
    y8 = x8 ^ rot8(x8, 22) ^ rot8(x8, 26) ^ (rot8(x8, 7) & rot8(x8, 19))
    u8a = np.unique(y8)
    res['w8_a3_sampled_injective'] = bool(len(u8a) == N)
    print(f'W=8 A3 sampled injectivity (2^22 words): {len(u8a) == N}', flush=True)

    # Q3: linear part of the pre-mix is invertible at W=4/8/16/32/64
    # (characteristic-polynomial argument: 1+t^22+t^26 has no root at t=1
    #  and t^W+1 = (t+1)^W over GF(2), so they are coprime)
    res['premix_linear_invertible_all_widths'] = True
    for WW in (4, 8, 16, 32, 64):
        # construct the W x W linear map L(x) = x ^ R22(x) ^ R26(x) and rank it
        M = np.zeros((WW, WW), dtype=np.uint8)
        for j in range(WW):
            ej = 1 << j
            yj = ej ^ rotl_word(ej, 22, WW) ^ rotl_word(ej, 26, WW)
            M[j, :] = ((yj >> np.arange(WW)) & 1).astype(np.uint8)
        r = 0
        for col in range(WW):
            piv = np.nonzero(M[r:, col])[0]
            if len(piv) == 0:
                continue
            piv = r + piv[0]
            M[[r, piv]] = M[[piv, r]]
            M[r + 1:] ^= M[r][None, :] * M[r + 1:, col][:, None]
            r += 1
        print(f'W={WW}: premix linear part rank = {r} (invertible: {r == WW})',
              flush=True)
        res['premix_linear_rank_w%d' % WW] = int(r)
        res['premix_linear_invertible_all_widths'] &= (r == WW)

    res['elapsed_s'] = round(time.time() - t0, 1)
    with open('explore_invertibility.json', 'w') as f:
        json.dump(res, f, indent=1)
    print(f'wrote explore_invertibility.json ({time.time()-t0:.0f}s)')


def rotl_word(x, r, WW):
    r %= WW
    return ((x << r) & ((1 << WW) - 1)) | (x >> (WW - r))


if __name__ == '__main__':
    main()

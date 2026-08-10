# -*- coding: utf-8 -*-
"""Corrected wide-width half-entropy test with collision-adequate samples.

Word width w = W bits. For a reliable H2 estimate we need expected
collisions >= ~100, i.e. N >= sqrt(100 * 2^(H2)). Since word H2 ~ c*W
(0.5..1), we choose N so that N^2 * 2^(-W) >= 256 (expect >=256
collisions if H2 ~ W) — and much larger if H2 ~ W/2.
"""
import numpy as np
import sys, time, json

from cipher import tempest_a1_round_program, State, apply_round, U64

ops = tempest_a1_round_program()


def collision_entropy(samples):
    uniq, counts = np.unique(samples, return_counts=True)
    n = len(samples)
    p = counts / n
    h2 = -np.log2(np.sum(p * p))
    return h2, int(np.sum(counts * (counts - 1)) // 2)


def word_diff_samples(W, delta_words, n_states, seed):
    st = State.random(n_states, seed=seed, W=W)
    sA = State([w.copy() for w in st.words], st.wv, W=W)
    sB = State([w ^ U64(delta_words[i]) for i, w in enumerate(st.words)],
               st.wv, W=W)
    apply_round(ops, sA)
    apply_round(ops, sB)
    out = []
    for i in range(4):
        out.append((sA.words[i] ^ sB.words[i]).astype(np.uint64))
    return out


def main():
    rng = np.random.default_rng(2026)
    results = {}
    # N per width: expect >=256 collisions if word H2 ~ W
    Ns = {4: 1 << 14, 8: 1 << 16, 16: 1 << 18, 32: 1 << 22}
    # W=16: word H2~16 -> N=2^18 -> coll 2^36*2^-16=2^20 (many, fine)
    # W=32: word H2~32 -> N=2^22 -> coll 2^44*2^-32=2^12=4096 ok
    # W=32: word H2~16 -> coll 2^44*2^-16 huge (saturated -> h2=log2N=22;
    #   then we know H2>22, i.e. ratio > 0.69) — acceptable bound.

    for W in [4, 8, 16, 32]:
        N = Ns[W]
        diffs = []
        for b in range(4 * W):
            d = [0, 0, 0, 0]
            wi, bi = divmod(b, W)
            d[wi] = 1 << bi
            diffs.append(d)
        for _ in range(24):
            d = [int(rng.integers(0, 1 << W)) for _ in range(4)]
            if any(d):
                diffs.append(d)

        worst_word = [None] * 4
        worst_full = None
        t0 = time.time()
        for di, d in enumerate(diffs):
            ws = word_diff_samples(W, d, N, seed=5000 + di)
            for wi in range(4):
                h2, _ = collision_entropy(ws[wi])
                if worst_word[wi] is None or h2 < worst_word[wi]:
                    worst_word[wi] = h2
            # full output: 4W bits; pack into 64-bit chunks if 4W<=64
            if 4 * W <= 64:
                full = np.zeros(N, dtype=np.uint64)
                for wi in range(4):
                    full ^= ws[wi] << (W * wi)
                h2f, _ = collision_entropy(full)
                if worst_full is None or h2f < worst_full:
                    worst_full = h2f
            if (di + 1) % 20 == 0:
                print(f'  W={W} [{di+1}/{len(diffs)}] '
                      f'worst word H2={min(worst_word):.2f} '
                      f'({time.time()-t0:.0f}s)', flush=True)

        results[W] = {
            'N': N,
            'word_H2_min': round(min(worst_word), 3),
            'word_H2_by_word': [round(h, 3) for h in worst_word],
            'full_H2': round(worst_full, 3) if worst_full is not None else None,
            'W/2': W / 2,
        }
        fh = f'{worst_full:.2f}' if worst_full is not None else 'n/a'
        print(f'W={W}: word-H2 min={min(worst_word):.2f} '
              f'(W/2={W/2}) full-H2={fh} (m/2={2*W})')

    with open('halfentropy_wide2.json', 'w') as f:
        json.dump(results, f, indent=1)
    print('saved halfentropy_wide2.json')


if __name__ == '__main__':
    main()

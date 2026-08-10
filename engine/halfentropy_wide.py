"""halfentropy_wide.py — test the Half-Entropy Law at W = 16, 32.

Full-output min-entropy is not samplable at these widths (DP ~ 2^-m/2
needs ~2^(m/2) samples). Instead we test the *word-level collision
entropy*: for each word w of the output, sample N state pairs per input
difference, count output-difference collisions, and estimate
H_2^(w) = -log2(sum p^2). The half-entropy law in word form predicts
H_2^(w) ~= W/2 for each word. At W=4/8 we also report the full-output
min-entropy (exact/sampled) and H_2, to check consistency between the
two forms.
"""
import numpy as np
import sys, time
from itertools import combinations

from cipher import tempest_a1_round_program, State, apply_round, U64

ops = tempest_a1_round_program()


def collision_entropy(samples):
    """samples: (N,) uint64 array of word differences. Returns H2 estimate."""
    uniq, counts = np.unique(samples, return_counts=True)
    n = len(samples)
    p = counts / n
    h2 = -np.log2(np.sum(p * p))
    return h2, int(np.sum(counts * (counts - 1)) // 2)  # h2, collision count


def word_diff_samples(W, delta_words, n_states, seed):
    """Sample n_states state pairs, return per-word output differences."""
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
    import json
    rng = np.random.default_rng(2026)
    results = {}

    for W in [4, 8, 16, 32]:
        n_words = W
        # per-width sample sizes tuned so expected collisions ~ 2^6..2^12
        if W == 4:
            N = 1 << 16          # exact-ish
        elif W == 8:
            N = 1 << 16
        elif W == 16:
            N = 1 << 14          # word H2 ~ 16 -> collisions ~ 2^12
        else:
            N = 1 << 18          # word H2 ~ 32 -> collisions ~ 2^4..2^8

        # difference set: all single-bit + sampled two-bit + random
        diffs = []
        for b in range(4 * W):
            d = [0, 0, 0, 0]
            wi, bi = divmod(b, W)
            d[wi] = 1 << bi
            diffs.append(d)
        for _ in range(40):
            d = [int(rng.integers(0, 1 << W)) for _ in range(4)]
            if any(d):
                diffs.append(d)

        # min over diffs of the min over words of H2
        worst_word_h2 = [None] * 4
        worst_dp_h2 = None
        t0 = time.time()
        for di, d in enumerate(diffs):
            ws = word_diff_samples(W, d, N, seed=1000 + di)
            for wi in range(4):
                h2, _ = collision_entropy(ws[wi])
                if worst_word_h2[wi] is None or h2 < worst_word_h2[wi]:
                    worst_word_h2[wi] = h2
            # full-output H2 (4 words concatenated)
            full = (ws[0] | (ws[1] << (8*W)) | (ws[2] << (16*W))
                    | (ws[3] << (24*W))) if W * 8 <= 32 else None
            if full is not None:
                h2f, _ = collision_entropy(full)
                if worst_dp_h2 is None or h2f < worst_dp_h2:
                    worst_dp_h2 = h2f
            if (di + 1) % 20 == 0:
                print(f'  W={W} [{di+1}/{len(diffs)}] '
                      f'worst word H2={min(worst_word_h2):.2f} '
                      f'({time.time()-t0:.0f}s)', flush=True)

        results[W] = {
            'N': N,
            'word_H2_min': [round(h, 3) for h in worst_word_h2],
            'word_H2_global_min': round(min(worst_word_h2), 3),
            'full_H2': round(worst_dp_h2, 3) if worst_dp_h2 else None,
            'm/2_per_word': W / 2,
        }
        fh = f'{worst_dp_h2:.2f}' if worst_dp_h2 is not None else 'n/a'
        print(f'W={W}: word-H2 min = {min(worst_word_h2):.2f} '
              f'(W = {W}, W/2 = {W/2})  full-H2 = {fh} (m/2={2*W})')

    with open('halfentropy_wide.json', 'w') as f:
        json.dump(results, f, indent=1)
    print('saved halfentropy_wide.json')


if __name__ == '__main__':
    main()

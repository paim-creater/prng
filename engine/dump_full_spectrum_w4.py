# -*- coding: utf-8 -*-
"""dump_full_spectrum_w4.py -- regenerate the published archive
full_spectrum_w4.json (schema: W/n_diffs/min_rank/max_rank/histogram/
spectrum, one entry per difference, delta encoded as a 16-bit int with
words u,v,w,z = bits [4wi, 4wi+3]).

Ground truth for each rank: the column model (predict_columns +
gf2_rank_cols), which is validated against the round-simulating ground
truth by rank_column_model.py (0 mismatches over 23,380 checks) and
spot-checked here against rank_of_delta (round simulation) every
2^12-th difference, same as the original archive generation.

Deterministic: the output file is byte-identical across runs.
"""
import json
import collections

from cipher import tempest_a1_round_program
from min_shadow_rank import truncate_at_levels, rank_of_delta
from rank_column_model import gates_from_ops, predict_columns, gf2_rank_cols

W = 4
N = 4 * W
OPS = tempest_a1_round_program()
shadow = truncate_at_levels(OPS, 0, include_premix=False)
gates = gates_from_ops(shadow)
assert len(gates) == 6


def main():
    hist = collections.Counter()
    spec = {}
    for delta in range(1, 1 << N):
        cols = predict_columns(W, gates, delta)
        r = gf2_rank_cols(cols, N)
        if delta % (1 << 12) == 1:  # spot-check vs round simulation
            gt, _ = rank_of_delta(W, shadow, delta)
            assert gt == r, (delta, gt, r)
        hist[r] += 1
        spec[str(delta)] = r
    out = {'W': W,
           'n_diffs': (1 << N) - 1,
           'min_rank': min(hist),
           'max_rank': max(hist),
           'histogram': {str(k): v for k, v in sorted(hist.items())},
           'spectrum': spec}
    with open('full_spectrum_w4.json', 'w') as f:
        json.dump(out, f)
    print('wrote full_spectrum_w4.json:',
          out['n_diffs'], 'diffs, rank', out['min_rank'], '..',
          out['max_rank'], '| histogram', dict(hist))


if __name__ == '__main__':
    main()

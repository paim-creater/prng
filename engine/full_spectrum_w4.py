# -*- coding: utf-8 -*-
"""full_spectrum_w4.py -- exhaustive W=4 differential-spectrum study.

Goal: find a CLOSED FORM for rank(B_Delta) over the FULL difference
space (all 2^16 - 1 differences) of the Algorithm-1 quadratic shadow.
Single-word formula (verified):  rank = 3t - |P n (P+2)| * [x = z].
Multi-word hypothesis: interactions come only from the K4 edge
structure (each word pair has exactly one gate).  For two active
words x,y sharing gate g=(d, r_x, r_y) [rotations of x and y in g]:
  - same-gate row sharing: entries of x (row d,p+r_x) and of y
    (row d,p'+r_y) coincide iff p - p' = r_y - r_x (mod W).
Additional interactions: gates writing the same output word d with
active words whose rotations align (e.g. the u-writing pair reading z
with rotations 25,23 -> difference 2).
This script computes truth ranks exhaustively and regresses the
shortfall vs 3*sum t_x against structural candidate counts.
"""
import itertools, json
import numpy as np
from cipher import tempest_a1_round_program
from min_shadow_rank import truncate_at_levels, rank_of_delta
from rank_column_model import gates_from_ops, predict_columns, gf2_rank_cols

OPS = tempest_a1_round_program()
W = 4
shadow = truncate_at_levels(OPS, 0, include_premix=False)
gates = gates_from_ops(shadow)
# gates as (d, a, ra, b, rb): K4 edges with rotations
print('shadow gates (K4 edges):', gates)
N = 4 * W

# per gate: map from word -> (role rot, partner word, partner rot)
def gate_info(g):
    d, a, ra, b, rb = g
    return {(a, ra): (b, rb, d), (b, rb): (a, ra, d)}

# build all-difference data
rng = np.random.default_rng(0)
truth = {}
# exhaustive too slow with round simulation; use column model == truth
# (already validated 25k+ cases) + spot check round sim
def rank_cm(delta):
    return gf2_rank_cols(predict_columns(W, gates, delta), N)

# candidate interaction counts for a delta with supports P (dict word->set)
def cand_features(P):
    feats = {}
    # same-gate cross-word row sharing: for each gate g=(x,y) with both
    # x,y active: |{(p,p') in P_x x P_y : p + rx = p' + ry}|
    sgc = 0
    for (d, a, ra, b, rb) in gates:
        if a in P and b in P:
            for p in P[a]:
                for pp in P[b]:
                    if (p + ra) % W == (pp + rb) % W:
                        sgc += 1
    feats['same_gate_cross'] = sgc
    # output-shared gates: pairs of gates writing same d with active
    # words x (in g1) and y (in g2), rows align
    osc = 0
    for i in range(len(gates)):
        for j in range(len(gates)):
            if i == j:
                continue
            g1, g2 = gates[i], gates[j]
            if g1[0] != g2[0]:
                continue
            # rotation of each gate's active operand towards its output
            for (w1, r1, p1) in ((g1[1], g1[2], g1[1]), (g1[3], g1[4], g1[3])):
                if w1 not in P:
                    continue
                for (w2, r2, _) in ((g2[1], g2[2], 0), (g2[3], g2[4], 0)):
                    if w2 not in P:
                        continue
                    for p in P[w1]:
                        for pp in P[w2]:
                            if (p + r1) % W == (pp + r2) % W:
                                osc += 1
    feats['out_shared_rows'] = osc
    # column complexity: columns with >= 2 entries
    return feats

# exhaustive over ALL differences at W=4
bad = 0
mism = []
shortfall = {}
allrows = []
for delta in range(1, 1 << N):
    cols = predict_columns(W, gates, delta)
    r = gf2_rank_cols(cols, N)
    # ground truth spot check
    if delta % 4096 == 1:
        gt, _ = rank_of_delta(W, shadow, delta)
        assert gt == r, (delta, gt, r)
    P = {}
    for wi in range(4):
        dw = (delta >> (wi * W)) & 0xF
        if dw:
            P[wi] = {p for p in range(W) if (dw >> p) & 1}
    tsum = 3 * sum(len(P[x]) for x in P)
    # single-word-style base: for each active word its own correction
    base = tsum
    if 3 in P:  # word z
        base -= sum(1 for p in P[3] if (p + 2) % W in P[3])
    short = base - r
    f = cand_features(P)
    allrows.append((delta, P, r, base, short, f))
    if short != 0:
        mism.append((delta, {k: sorted(v) for k, v in P.items()}, r, base, short, f))
print('total diffs:', len(allrows), '| base-correct mismatches:', len(mism))
for m in mism[:15]:
    print(' ', m)
json.dump({'n': len(allrows), 'mismatches': len(mism), 'samples': mism[:20]},
          open('full_spectrum_w4.json', 'w'), indent=1)

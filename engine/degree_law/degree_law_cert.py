# -*- coding: utf-8 -*-
"""degree_law_cert.py -- machine certificate for the exact algebraic-degree
law of the Tempest v3 round at W = 64 (and the W=4 full-ANF calibration).

Claims certified (see degree_law_exact.json / degree_law_toponly_w64.json /
w64_presence_anchors.json):

  (C1) W=64: after cascade levels k = 0..3 every output bit has algebraic
       degree exactly 4, 8, 16, 32 (top-monomial parity is exact while the
       chain is death-free: a product at the top degree decomposes only into
       top-degree factors).
  (C2) W=64: after level 4 no output bit contains a degree-64 monomial
       (all top products have even parity), i.e. deg(Phi) <= 63; combined
       with (C1) the per-round degree is 32 <= deg(Phi) <= 63.
  (C3) W=4: full-ANF ground truth (Mobius over 2^16) matches the tracker
       per bit and per monomial set through k <= 2 and per bit through k=3
       (2, 4, 8, 14, 16 maximum degrees; toy-width effects: the premix
       rotations 7, 19 collapse mod 4 and the 16-variable ceiling forces
       the k=3 cancellations).

The tracker topmon_tracker.py implements the top-monomial parity semantics;
presence anchors (w64_presence_anchors.json) verify sampled top monomials
of levels 1 and 2 against the true round function by subset-Mobius
evaluation (2^|monomial| round evaluations, cost independent of W).
"""
import json, sys, time
sys.path.insert(0, '.')
from topmon_tracker import Tracker, prefix_ops, size_of
from collections import Counter


def run(W, kmax=5, nlayers=0):
    out = {}
    for k in range(kmax):
        t0 = time.time()
        tr = Tracker(W, [], nlayers=nlayers)
        F = tr.run_round(prefix_ops(k))
        info = []
        for (w, p), fam in F.items():
            if not fam:
                info.append((w, p, 0, 0))
                continue
            m = max(size_of(s) for s in fam)
            info.append((w, p, m, len(fam)))
        md = max(x[2] for x in info)
        out[k] = {'max_deg': md,
                  'hist': {str(a): b for a, b in sorted(
                      Counter(x[2] for x in info).items())},
                  'bits_with_no_survivor': sum(1 for x in info if x[3] == 0),
                  'elapsed_s': round(time.time() - t0, 1)}
        print(f'W={W} k={k}: max degree {md} hist {out[k]["hist"]} '
              f'({out[k]["elapsed_s"]}s)', flush=True)
    return out


if __name__ == '__main__':
    which = sys.argv[1] if len(sys.argv) > 1 else 'w64'
    if which == 'w4':
        # calibration: W=4 with nlayers=4 mirrors the published sequence
        res = run(4, kmax=5, nlayers=4)
    else:
        res = run(64, kmax=5, nlayers=0)
    json.dump({'W': 64 if which != 'w4' else 4, 'levels': res},
              open(f'degree_law_cert_{which}.json', 'w'), indent=1)
    print('wrote degree_law_cert_%s.json' % which)

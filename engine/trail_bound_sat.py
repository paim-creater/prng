"""Binary-search SAT for the minimal R-round truncated-differential trail
support of the full Tempest v3 round (W=8).  Same model as trail_maxsat.py
but the cardinality constraint sum(svars) <= K is encoded directly, so each
feasibility check is a single SAT call.

Usage: python trail_bound_sat.py [Rmax] [K0]
"""
from pysat.formula import CNF
from pysat.card import CardEnc, EncType
from pysat.solvers import Solver
import trail_maxsat as base
import sys, time


def feasible(R, K):
    net = base.Net()
    gv, svars, hard = [], [], []
    iv = [net.wvar() for _ in range(4)]
    hard.append([b for w in iv for b in w])
    prev = iv
    for r in range(R):
        prev = base.build_round(net, prev, gv, svars, hard)
        hard.append([b for w in prev for b in w])
    cnf = CNF()
    for c in hard:
        cnf.append(c)
    # cardinality: sum(svars) <= K  (at-most-K)
    cnf.extend(CardEnc.atmost(svars, bound=K, top_id=cnf.nv, encoding=EncType.seqcounter))
    t0 = time.time()
    with Solver(name="cd", bootstrap_with=cnf) as s:
        sat = s.solve()
    return sat, time.time() - t0


def main():
    maxR = int(sys.argv[1]) if len(sys.argv) > 1 else 4
    for R in range(1, maxR + 1):
        lo, hi = 0, 26 * 8 * R
        # quick lower bound from R=1 if known
        while lo < hi:
            mid = (lo + hi) // 2
            sat, dt = feasible(R, mid)
            print("  R=%d K=%d -> %s (%.1fs)" % (R, mid, "SAT" if sat else "UNSAT", dt))
            sys.stdout.flush()
            if sat:
                hi = mid
            else:
                lo = mid + 1
        print("R=%d: min trail support = %d  (trail DP <= 2^-%d)" % (R, lo, lo))
        sys.stdout.flush()


if __name__ == "__main__":
    main()

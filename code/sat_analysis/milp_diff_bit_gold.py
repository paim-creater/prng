#!/usr/bin/env python3
"""
GOLD STANDARD bit-level differential MILP — Tempest v3.
Input bits are FREE variables (not all-1). Only constrains:
  - At least 1 bit per active word (word-level Δ pattern fixed)
  - Minimizes active AND count
This gives the TRUE bit-level bound without worst-case assumptions.
"""
import pulp, itertools, sys, time
from milp_solver import get_solver

W = int(sys.argv[1]) if len(sys.argv) > 1 else 8
words = ['u','v','w','z']

def run_pattern(bits, W, timelimit=900):
    prob = pulp.LpProblem("BitDiffFree_R1", pulp.LpMinimize)

    # Input bits: FREE (solver chooses)
    din = {}
    for n in words:
        din[n] = [pulp.LpVariable(f"in_{n}_{b}", cat='Binary') for b in range(W)]
    # Constrain: at least 1 bit in each active word
    for i, n in enumerate(words):
        if bits[i] == 1:
            prob += pulp.lpSum(din[n]) >= 1
        else:
            for b in range(W):
                din[n][b] = 0

    # State vars for cascade
    d = {}
    for n in words:
        d[n] = {}
        for L in range(9):
            d[n][L] = [pulp.LpVariable(f"d_{n}_{L}_{b}", cat='Binary') for b in range(W)]
    # Copy input
    for n in words:
        for b in range(W):
            d[n][0][b] = din[n][b]

    # Active AND tracking
    and_vars = {}

    def mk_and(label, an, at, ra, bn, bt, rb, tn, tt):
        nonlocal prob
        for i in range(W):
            sa = (i - ra) % W
            sb = (i - rb) % W
            v = pulp.LpVariable(f"a_{label}_{i}", cat='Binary')
            prob += v <= d[an][at][sa]
            prob += v <= d[bn][bt][sb]
            prob += v >= d[an][at][sa] + d[bn][bt][sb] - 1
            and_vars[(label, i)] = v
            prob += d[tn][tt][i] >= v

    def mk_xor_max(tn, tt, srcs):
        for i in range(W):
            for sn, st, ro in srcs:
                si = (i - ro) % W
                prob += d[tn][tt][i] >= d[sn][st][si]

    # Phase B
    for i in range(W):
        srcs_u = [('u',0,0), ('v',0,5), ('w',0,17)]
        for sn, st, ro in srcs_u:
            prob += d['u'][1][i] >= d[sn][st][(i-ro)%W]
        prob += d['u'][1][i] <= d['u'][0][i] + d['v'][0][(i-5)%W] + d['w'][0][(i-17)%W]

        srcs_v = [('v',0,0), ('w',0,11), ('z',0,23)]
        for sn, st, ro in srcs_v:
            prob += d['v'][1][i] >= d[sn][st][(i-ro)%W]
        prob += d['v'][1][i] <= d['v'][0][i] + d['w'][0][(i-11)%W] + d['z'][0][(i-23)%W]

        srcs_w = [('w',0,0), ('z',0,13), ('u',0,31)]
        for sn, st, ro in srcs_w:
            prob += d['w'][1][i] >= d[sn][st][(i-ro)%W]
        prob += d['w'][1][i] <= d['w'][0][i] + d['z'][0][(i-13)%W] + d['u'][0][(i-31)%W]

        srcs_z = [('z',0,0), ('u',0,17), ('v',0,7)]
        for sn, st, ro in srcs_z:
            prob += d['z'][1][i] >= d[sn][st][(i-ro)%W]
        prob += d['z'][1][i] <= d['z'][0][i] + d['u'][0][(i-17)%W] + d['v'][0][(i-7)%W]

    # Phase B(lin): snapshot ANDs (read from d[][0]=input)
    mk_and('S1', 'z',0,23, 'w',0,53, 'u',1)
    mk_and('S2', 'u',0,5,  'z',0,25, 'z',1)

    # Premix 1
    for n in words:
        for i in range(W):
            prob += d[n][2][i] >= d[n][1][i]
            prob += d[n][2][i] >= d[n][1][(i-22)%W]
            prob += d[n][2][i] >= d[n][1][(i-26)%W]

    # Phase C L1
    mk_and('C1u', 'v',2,31, 'w',2,53, 'u',3)
    mk_and('C1v', 'w',2,17, 'z',2,43, 'v',3)
    mk_and('C1w', 'z',2,7,  'u',2,23, 'w',3)
    mk_and('C1z', 'u',2,5,  'v',2,19, 'z',3)
    for n in words:
        for i in range(W):
            prob += d[n][4][i] == d[n][3][i]

    # Phase C L2
    mk_and('C2u', 'v',4,17, 'z',4,43, 'u',5)
    mk_and('C2v', 'w',4,7,  'u',4,23, 'v',5)
    mk_and('C2w', 'z',4,5,  'v',4,19, 'w',5)
    mk_and('C2z', 'u',4,31, 'w',4,53, 'z',5)
    for n in words:
        for i in range(W):
            prob += d[n][6][i] == d[n][5][i]

    # Phase C L3
    mk_and('C3u', 'z',6,7,  'u',6,23, 'u',7)
    mk_and('C3v', 'u',6,5,  'v',6,19, 'v',7)
    mk_and('C3w', 'v',6,31, 'w',6,53, 'w',7)
    mk_and('C3z', 'w',6,17, 'z',6,43, 'z',7)
    for n in words:
        for i in range(W):
            prob += d[n][8][i] == d[n][7][i]

    prob += pulp.lpSum([and_vars[k] for k in and_vars])

    solver = get_solver(timeLimit=timelimit)
    t0 = time.time()
    prob.solve(solver)
    t1 = time.time()

    if prob.status == pulp.LpStatusOptimal:
        total = sum(int(pulp.value(and_vars[k])) for k in and_vars)
        # Count input bits
        inp_bits = sum(int(pulp.value(din[n][b])) for n in words for b in range(W))
        return total, inp_bits, t1-t0
    elif prob.status == pulp.LpStatusInfeasible:
        return ("INF", 0, t1-t0)
    else:
        return (pulp.LpStatus[prob.status], 0, t1-t0)

# Run
for W_val in [8, 12, 16]:
    print("=" * 72)
    print(f"Gold-Standard Bit-Level DIFF - W = {W_val} (free input bits)")
    print("=" * 72)
    print(f"{'Pattern':<14} {'Act-ANDs':<10} {'InpBits':<8} {'Time':<8}")
    print("-" * 72)
    results = {}
    for bits in itertools.product([0,1], repeat=4):
        if all(b == 0 for b in bits): continue
        pat = f"({bits[0]},{bits[1]},{bits[2]},{bits[3]})"
        res, ib, t = run_pattern(list(bits), W_val)
        if res is not None and res != "INF":
            results[pat] = res
            print(f"{pat:<14} {res:<10} {ib:<8} {t:<8.1f}")
        else:
            print(f"{pat:<14} {str(res):<10} {t:<8.1f}")
    if results:
        mn = min(results.values())
        mx = max(results.values())
        print(f"  Min: {mn}, Max: {mx}, Ratio min/W: {mn/W_val:.1f}")
        print(f"  a_min ≥ {mn//W_val} per word (bit-level free)")

#!/usr/bin/env python3
"""
CORRECTED bit-level differential trail MILP — Tempest v3.
Phase B(orig) + Phase B(lin) + Phase C L1-3.
Correct XOR constraint: d_out >= d_term for each term (MAX rule).
Correct AND constraint: d_out >= d_AND, d_AND active when both inputs active.
"""
import pulp, itertools, sys, time
from milp_solver import get_solver

W = int(sys.argv[1]) if len(sys.argv) > 1 else 8
words = ['u','v','w','z']

def run_pattern(bits, W, timelimit=600):
    prob = pulp.LpProblem("BitDiff_R1", pulp.LpMinimize)
    # State vars: d[word][level][bit]
    d = {}
    for n in words:
        d[n] = {}
        for L in range(9):
            d[n][L] = [pulp.LpVariable(f"d_{n}_{L}_{b}", cat='Binary') for b in range(W)]
    # Input: all bits of active word = word-level value
    for i, n in enumerate(words):
        for b in range(W):
            d[n][0][b] = bits[i]

    # Active AND tracking
    and_vars = {}

    def mk_and(label, an, at, ra, bn, bt, rb, tn, tt):
        """AND at each bit position, active when BOTH inputs have diff."""
        nonlocal prob
        for i in range(W):
            sa = (i - ra) % W
            sb = (i - rb) % W
            vi = pulp.LpVariable(f"a_{label}_{i}", cat='Binary')
            # vi = d_a AND d_b
            prob += vi <= d[an][at][sa]
            prob += vi <= d[bn][bt][sb]
            prob += vi >= d[an][at][sa] + d[bn][bt][sb] - 1
            and_vars[(label, i)] = vi
            # AND output propagates diff (conservative: output diff ≥ AND activation)
            prob += d[tn][tt][i] >= vi

    def mk_xor_max(tn, tt, srcs):
        """XOR: d_out >= each source term (MAX rule)."""
        for sn, st, ro in srcs:
            ix = ro % W
            prob += d[tn][tt][0] >= d[sn][st][ix]
            # Need per-bit constraints
        for i in range(W):
            for sn, st, ro in srcs:
                si = (i - ro) % W
                prob += d[tn][tt][i] >= d[sn][st][si]

    # Phase B equations (exact per-bit)
    for i in range(W):
        # u = u0 XOR r5(v0) XOR r17(w0) XOR AND(v0,z0)
        srcs_uvwz = [
            ('u',0,0), ('v',0,5), ('w',0,17),
        ]
        for sn, st, ro in srcs_uvwz:
            si = (i - ro) % W
            prob += d['u'][1][i] >= d[sn][st][si]
        prob += d['u'][1][i] <= d['u'][0][i] + d['v'][0][(i-5)%W] + d['w'][0][(i-17)%W]

        # v = v0 XOR r11(w0) XOR r23(z0) XOR AND(w0,u0)
        for sn, st, ro in [('v',0,0), ('w',0,11), ('z',0,23)]:
            si = (i - ro) % W
            prob += d['v'][1][i] >= d[sn][st][si]
        prob += d['v'][1][i] <= d['v'][0][i] + d['w'][0][(i-11)%W] + d['z'][0][(i-23)%W]

        # w = w0 XOR r13(z0) XOR r31(u0) XOR AND(u0,v0)
        for sn, st, ro in [('w',0,0), ('z',0,13), ('u',0,31)]:
            si = (i - ro) % W
            prob += d['w'][1][i] >= d[sn][st][si]
        prob += d['w'][1][i] <= d['w'][0][i] + d['z'][0][(i-13)%W] + d['u'][0][(i-31)%W]

        # z = z0 XOR r17(u0) XOR r7(v0) XOR AND(v0,w0)
        for sn, st, ro in [('z',0,0), ('u',0,17), ('v',0,7)]:
            si = (i - ro) % W
            prob += d['z'][1][i] >= d[sn][st][si]
        prob += d['z'][1][i] <= d['z'][0][i] + d['u'][0][(i-17)%W] + d['v'][0][(i-7)%W]

    # Phase B(lin): snapshot ANDs
    mk_and('Sn1', 'z',0,23, 'w',0,53, 'u',1)  # (z,w)→u
    mk_and('Sn2', 'u',0,5,  'z',0,25, 'z',1)  # (u,z)→z

    # Premix 1: XOR of self with rotl(self,22) XOR rotl(self,26)
    for n in words:
        for i in range(W):
            prob += d[n][2][i] >= d[n][1][i]       # self
            prob += d[n][2][i] >= d[n][1][(i-22)%W]
            prob += d[n][2][i] >= d[n][1][(i-26)%W]
            prob += d[n][2][i] <= d[n][1][i] + d[n][1][(i-22)%W] + d[n][1][(i-26)%W]

    # Phase C Level 1
    mk_and('L1_u', 'v',2,31, 'w',2,53, 'u',3)
    mk_and('L1_v', 'w',2,17, 'z',2,43, 'v',3)
    mk_and('L1_w', 'z',2,7,  'u',2,23, 'w',3)
    mk_and('L1_z', 'u',2,5,  'v',2,19, 'z',3)

    # Copy L1 output forward
    for n in words:
        for i in range(W):
            prob += d[n][4][i] >= d[n][3][i]
            prob += d[n][4][i] <= d[n][3][i]

    # Phase C Level 2
    mk_and('L2_u', 'v',4,17, 'z',4,43, 'u',5)
    mk_and('L2_v', 'w',4,7,  'u',4,23, 'v',5)
    mk_and('L2_w', 'z',4,5,  'v',4,19, 'w',5)
    mk_and('L2_z', 'u',4,31, 'w',4,53, 'z',5)

    for n in words:
        for i in range(W):
            prob += d[n][6][i] >= d[n][5][i]
            prob += d[n][6][i] <= d[n][5][i]

    # Phase C Level 3
    mk_and('L3_u', 'z',6,7,  'u',6,23, 'u',7)
    mk_and('L3_v', 'u',6,5,  'v',6,19, 'v',7)
    mk_and('L3_w', 'v',6,31, 'w',6,53, 'w',7)
    mk_and('L3_z', 'w',6,17, 'z',6,43, 'z',7)

    for n in words:
        for i in range(W):
            prob += d[n][8][i] >= d[n][7][i]
            prob += d[n][8][i] <= d[n][7][i]

    # Minimize active AND count
    prob += pulp.lpSum([and_vars[k] for k in and_vars])

    solver = get_solver(timeLimit=timelimit)
    t0 = time.time()
    prob.solve(solver)
    t1 = time.time()

    if prob.status == pulp.LpStatusOptimal:
        total = sum(int(pulp.value(and_vars[k])) for k in and_vars)
        return total, t1-t0
    elif prob.status == pulp.LpStatusInfeasible:
        return ("INF", t1-t0)
    else:
        return (pulp.LpStatus[prob.status], t1-t0)

# Run all 15 patterns
for W_val in [8, 12, 16, 24]:
    print("=" * 72)
    print(f"Corrected Bit-Level Differential Trail - W = {W_val}")
    print("=" * 72)
    print(f"{'Pattern':<14} {'Act-ANDs':<10} {'Time':<8}")
    print("-" * 72)
    results = {}
    for bits in itertools.product([0,1], repeat=4):
        if all(b == 0 for b in bits): continue
        pat = f"({bits[0]},{bits[1]},{bits[2]},{bits[3]})"
        res, t = run_pattern(list(bits), W_val)
        if res is not None and res != "INF":
            results[pat] = res
            print(f"{pat:<14} {res:<10} {t:<8.1f}")
        elif res == "INF":
            print(f"{pat:<14} INFEASIBLE  {t:<8.1f}")
        else:
            print(f"{pat:<14} {res:<10} {t:<8.1f}")
    if results:
        mn = min(results.values())
        print(f"  Min active ANDs (word-level): {mn}")
        print(f"  Min active ANDs / W: {mn/W_val:.2f}")
    print("=" * 72)

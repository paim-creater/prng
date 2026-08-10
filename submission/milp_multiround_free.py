#!/usr/bin/env python3
"""
Multi-Round Free-Delta Bit-Level Differential MILP — Tempest v3.
Extends gold-standard free-Delta model to 2-4 rounds.
Usage: python milp_multiround_free.py [W] [R] [timelimit]
"""
import pulp, itertools, sys, time, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from milp_solver import get_solver

W = int(sys.argv[1]) if len(sys.argv) > 1 else 8
R = int(sys.argv[2]) if len(sys.argv) > 2 else 2
TL = int(sys.argv[3]) if len(sys.argv) > 3 else 1800
words = ['u','v','w','z']

def run_multiround(bits, W, R, timelimit=1800):
    """Multi-round free-Delta MILP."""
    prob = pulp.LpProblem("MultiRound_Free", pulp.LpMinimize)

    d = {}
    for rnd in range(R):
        d[rnd] = {}
        for n in words:
            d[rnd][n] = {}
            for L in range(9):
                d[rnd][n][L] = [pulp.LpVariable(f"d_R{rnd}_{n}_{L}_{b}", cat='Binary') for b in range(W)]

    for i, n in enumerate(words):
        if bits[i] == 1:
            prob += pulp.lpSum(d[0][n][0]) >= 1
        else:
            for b in range(W):
                d[0][n][0][b] = 0

    and_vars = {}

    def mk_and(label, rnd, an, at, ra, bn, bt, rb, tn, tt):
        nonlocal prob, d, and_vars
        for i in range(W):
            sa = (i - ra) % W
            sb = (i - rb) % W
            vi = pulp.LpVariable(f"a_{label}_R{rnd}_{i}", cat='Binary')
            prob += vi <= d[rnd][an][at][sa]
            prob += vi <= d[rnd][bn][bt][sb]
            prob += vi >= d[rnd][an][at][sa] + d[rnd][bn][bt][sb] - 1
            and_vars[(label, rnd, i)] = vi
            prob += d[rnd][tn][tt][i] >= vi

    def apply_round(rnd):
        nonlocal prob, d, and_vars

        # Phase A: XOR diffusion (from level 0 snapshot)
        for i in range(W):
            # u
            s_u = [('u',0,0), ('v',0,5), ('w',0,17)]
            for sn, st, ro in s_u:
                prob += d[rnd]['u'][1][i] >= d[rnd][sn][st][(i-ro)%W]
            prob += d[rnd]['u'][1][i] <= pulp.lpSum([d[rnd][sn][st][(i-ro)%W] for sn,st,ro in s_u])

            # v
            s_v = [('v',0,0), ('w',0,11), ('z',0,23)]
            for sn, st, ro in s_v:
                prob += d[rnd]['v'][1][i] >= d[rnd][sn][st][(i-ro)%W]
            prob += d[rnd]['v'][1][i] <= pulp.lpSum([d[rnd][sn][st][(i-ro)%W] for sn,st,ro in s_v])

            # w
            s_w = [('w',0,0), ('z',0,13), ('u',0,31)]
            for sn, st, ro in s_w:
                prob += d[rnd]['w'][1][i] >= d[rnd][sn][st][(i-ro)%W]
            prob += d[rnd]['w'][1][i] <= pulp.lpSum([d[rnd][sn][st][(i-ro)%W] for sn,st,ro in s_w])

            # z
            s_z = [('z',0,0), ('u',0,17), ('v',0,7)]
            for sn, st, ro in s_z:
                prob += d[rnd]['z'][1][i] >= d[rnd][sn][st][(i-ro)%W]
            prob += d[rnd]['z'][1][i] <= pulp.lpSum([d[rnd][sn][st][(i-ro)%W] for sn,st,ro in s_z])

        # Phase A(lin): snapshot ANDs
        mk_and('Sn1', rnd, 'z',0,23, 'w',0,53, 'u',1)
        mk_and('Sn2', rnd, 'u',0,5, 'z',0,25, 'z',1)

        # Premix 1
        for n in words:
            for i in range(W):
                sp = [(n,1,0), (n,1,22), (n,1,26)]
                for sn, st, ro in sp:
                    prob += d[rnd][n][2][i] >= d[rnd][sn][st][(i-ro)%W]
                prob += d[rnd][n][2][i] <= pulp.lpSum([d[rnd][sn][st][(i-ro)%W] for sn,st,ro in sp])

        # Phase C L1
        mk_and('L1u', rnd, 'v',2,31, 'w',2,53, 'u',3)
        mk_and('L1v', rnd, 'w',2,17, 'z',2,43, 'v',3)
        mk_and('L1w', rnd, 'z',2,7, 'u',2,23, 'w',3)
        mk_and('L1z', rnd, 'u',2,5, 'v',2,19, 'z',3)

        for n in words:
            for i in range(W):
                prob += d[rnd][n][4][i] == d[rnd][n][3][i]

        # Phase C L2
        mk_and('L2u', rnd, 'v',4,17, 'z',4,43, 'u',5)
        mk_and('L2v', rnd, 'w',4,7, 'u',4,23, 'v',5)
        mk_and('L2w', rnd, 'z',4,5, 'v',4,19, 'w',5)
        mk_and('L2z', rnd, 'u',4,31, 'w',4,53, 'z',5)

        for n in words:
            for i in range(W):
                prob += d[rnd][n][6][i] == d[rnd][n][5][i]

        # Phase C L3
        mk_and('L3u', rnd, 'z',6,7, 'u',6,23, 'u',7)
        mk_and('L3v', rnd, 'u',6,5, 'v',6,19, 'v',7)
        mk_and('L3w', rnd, 'v',6,31, 'w',6,53, 'w',7)
        mk_and('L3z', rnd, 'w',6,17, 'z',6,43, 'z',7)

        for n in words:
            for i in range(W):
                prob += d[rnd][n][8][i] == d[rnd][n][7][i]

        # Phase D -> next round input (if not last round)
        if rnd < R - 1:
            nr = rnd + 1
            for i in range(W):
                # u_next = u ^ rotl(v,3) ^ rotl(w,9)
                su = [(rnd,'u',8,0),(rnd,'v',8,3),(rnd,'w',8,9)]
                for sr, sn, st, ro in su:
                    prob += d[nr]['u'][0][i] >= d[sr][sn][st][(i-ro)%W]
                prob += d[nr]['u'][0][i] <= pulp.lpSum([d[sr][sn][st][(i-ro)%W] for sr,sn,st,ro in su])

                # v_next = v ^ rotl(w,5) ^ rotl(z,11)
                sv = [(rnd,'v',8,0),(rnd,'w',8,5),(rnd,'z',8,11)]
                for sr, sn, st, ro in sv:
                    prob += d[nr]['v'][0][i] >= d[sr][sn][st][(i-ro)%W]
                prob += d[nr]['v'][0][i] <= pulp.lpSum([d[sr][sn][st][(i-ro)%W] for sr,sn,st,ro in sv])

                # w_next = w ^ rotl(z,9) ^ rotl(u,13)
                sw = [(rnd,'w',8,0),(rnd,'z',8,9),(rnd,'u',8,13)]
                for sr, sn, st, ro in sw:
                    prob += d[nr]['w'][0][i] >= d[sr][sn][st][(i-ro)%W]
                prob += d[nr]['w'][0][i] <= pulp.lpSum([d[sr][sn][st][(i-ro)%W] for sr,sn,st,ro in sw])

                # z_next = z ^ rotl(u,11) ^ rotl(v,17)
                sz = [(rnd,'z',8,0),(rnd,'u',8,11),(rnd,'v',8,17)]
                for sr, sn, st, ro in sz:
                    prob += d[nr]['z'][0][i] >= d[sr][sn][st][(i-ro)%W]
                prob += d[nr]['z'][0][i] <= pulp.lpSum([d[sr][sn][st][(i-ro)%W] for sr,sn,st,ro in sz])

    for rnd in range(R):
        apply_round(rnd)

    prob += pulp.lpSum([and_vars[k] for k in and_vars])

    nvars = len(prob.variables())
    print(f"  Model: {nvars} vars, R={R}, W={W}, pattern={bits}", flush=True)
    solver = get_solver(timeLimit=timelimit, msg=False)
    t0 = time.time()
    prob.solve(solver)
    t1 = time.time()

    if prob.status == pulp.LpStatusOptimal:
        total = sum(int(pulp.value(and_vars[k])) for k in and_vars)
        per_rnd = {}
        for rnd in range(R):
            pr = sum(int(pulp.value(and_vars[k])) for k in and_vars if k[1] == rnd)
            per_rnd[rnd] = pr
        return total, per_rnd, t1-t0
    elif prob.status == pulp.LpStatusInfeasible:
        return ("INF", None, t1-t0)
    else:
        return (pulp.LpStatus[prob.status], None, t1-t0)

# ===== MAIN (only runs patterns, doesn't import gold model's main) =====
print("=" * 72)
print(f"  Multi-Round Free-Delta Differential — Tempest v3")
print(f"  W={W}, Rounds={R}, TimeLimit={TL}s")
print("=" * 72)

for W_val in [8, 12]:
    print(f"\n{'='*60}")
    print(f"  W = {W_val}, R = {R}")
    print(f"{'='*60}")
    print(f"{'Pattern':<14} {'R=1':<10} {'R=2':<10} {'R=2/rnd':<16} {'Time':<8}")
    print(f"{'-'*60}")

    for bits in itertools.product([0,1], repeat=4):
        if all(b == 0 for b in bits): continue
        pat = f"({bits[0]},{bits[1]},{bits[2]},{bits[3]})"

        r2_res, r2_pr, r2_t = run_multiround(list(bits), W_val, R, timelimit=TL)

        if isinstance(r2_res, int):
            per_str = str(r2_pr) if r2_pr else "?"
            print(f"{pat:<14} --       {r2_res:<10} {per_str:<16} {r2_t:<8.1f}")
        else:
            print(f"{pat:<14} --       {str(r2_res):<10} --               {r2_t:<8.1f}")

    print()

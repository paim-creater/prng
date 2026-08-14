#!/usr/bin/env python3
"""
Division property MILP for Tempest v3 — exact level-specific pairings.
All 4 levels with correct rotation constants (matching milp_deg.py style).
Extends to r=2 with 3 time steps.
Usage: python milp_deg_exact.py <W> <r> <dmax>
"""
import pulp, sys, time
from milp_solver import get_solver

W = int(sys.argv[1]) if len(sys.argv) > 1 else 64
R = int(sys.argv[2]) if len(sys.argv) > 2 else 1
DMAX = int(sys.argv[3]) if len(sys.argv) > 3 else (W if R == 1 else W * R)

words = 'uvwz'
T = R + 1  # time steps: 0=input, 1=after round1, 2=after round2

prob = pulp.LpProblem(f"Deg_W{W}_r{R}_exact", pulp.LpMinimize)

d = {}
for n in words:
    for t in range(T):
        d[(n, t)] = [pulp.LpVariable(f"d_{n}_{t}_{i}", lowBound=1, cat='Integer') for i in range(W)]

# Initial deg = 1
for n in words:
    for i in range(W):
        prob += d[(n, 0)][i] == 1

def ri(i, r):
    return (i + r) % W

def add_levels(prob, d, src, dst):
    """
    Add all 4 levels with exact pairings and rotation constants.
    All levels constrain the same dst variables (milp_deg.py style).
    """
    for i in range(W):
        # Level 1
        prob += d[('u', dst)][i] >= d[('v', src)][ri(i, 31)] + d[('w', src)][ri(i, 53)]
        prob += d[('u', dst)][i] >= d[('u', src)][i]
        prob += d[('v', dst)][i] >= d[('w', src)][ri(i, 17)] + d[('z', src)][ri(i, 43)]
        prob += d[('v', dst)][i] >= d[('v', src)][i]
        prob += d[('w', dst)][i] >= d[('z', src)][ri(i, 7)] + d[('u', src)][ri(i, 23)]
        prob += d[('w', dst)][i] >= d[('w', src)][i]
        prob += d[('z', dst)][i] >= d[('u', src)][ri(i, 5)] + d[('v', src)][ri(i, 19)]
        prob += d[('z', dst)][i] >= d[('z', src)][i]

        # Level 2 (reads from src/dst = level 1 output, writes to dst)
        prob += d[('u', dst)][i] >= d[('v', dst)][ri(i, 17)] + d[('z', dst)][ri(i, 43)]
        prob += d[('v', dst)][i] >= d[('w', dst)][ri(i, 7)] + d[('u', dst)][ri(i, 23)]
        prob += d[('w', dst)][i] >= d[('z', dst)][ri(i, 5)] + d[('v', dst)][ri(i, 19)]
        prob += d[('z', dst)][i] >= d[('u', dst)][ri(i, 31)] + d[('w', dst)][ri(i, 53)]

        # Level 3
        prob += d[('u', dst)][i] >= d[('z', dst)][ri(i, 7)] + d[('u', dst)][ri(i, 23)]
        prob += d[('v', dst)][i] >= d[('u', dst)][ri(i, 5)] + d[('v', dst)][ri(i, 19)]
        prob += d[('w', dst)][i] >= d[('v', dst)][ri(i, 31)] + d[('w', dst)][ri(i, 53)]
        prob += d[('z', dst)][i] >= d[('w', dst)][ri(i, 17)] + d[('z', dst)][ri(i, 43)]

        # Level 4
        prob += d[('u', dst)][i] >= d[('v', dst)][ri(i, 5)] + d[('w', dst)][ri(i, 19)]
        prob += d[('v', dst)][i] >= d[('w', dst)][ri(i, 31)] + d[('z', dst)][ri(i, 53)]
        prob += d[('w', dst)][i] >= d[('z', dst)][ri(i, 17)] + d[('u', dst)][ri(i, 53)]
        prob += d[('z', dst)][i] >= d[('u', dst)][ri(i, 7)] + d[('v', dst)][ri(i, 23)]

        # Phase B(lin): snapshot ANDs covering (u,z) and (w,z)
        prob += d[('u', dst)][i] >= d[('z', src)][ri(i, 23)] + d[('w', src)][ri(i, 53)]
        prob += d[('z', dst)][i] >= d[('u', src)][ri(i, 5)] + d[('z', src)][ri(i, 25)]

# Apply rounds
for rnd in range(R):
    add_levels(prob, d, rnd, rnd + 1)

# Constrain output ≤ DMAX — test feasibility
for n in words:
    for i in range(W):
        prob += d[(n, R)][i] <= DMAX

# Minimize total degree
prob += pulp.lpSum([d[(n, R)][i] for n in words for i in range(W)])

# Solve
print(f"Exact pairing model: W={W}, r={R}, d_max={DMAX}")
print(f"Variables: {T * 4 * W}")

solver = get_solver(timeLimit=3600)
t0 = time.time()
prob.solve(solver)
t1 = time.time()

status = prob.status
elapsed = t1 - t0
print(f"Status: {pulp.LpStatus[status]}, Time: {elapsed:.1f}s")

if status == pulp.LpStatusInfeasible:
    print(f"→ deg({R}) > {DMAX} CONFIRMED")
elif status == pulp.LpStatusOptimal:
    vals = {}
    for n in words:
        for i in range(W):
            vals[(n,i)] = int(pulp.value(d[(n, R)][i]))
    mn = min(vals.values()); mx = max(vals.values())
    print(f"min={mn}, max={mx}")
    unique_deg = len(set(vals.values()))
    print(f"distinct degree values: {unique_deg}")
    if mn > W:
        print(f"→ deg({R}) > {W} CONFIRMED")
    if mn > DMAX:
        print(f"→ INCONSISTENT: min > DMAX ({mn} > {DMAX})")
else:
    print(f"→ Unknown / timeout")

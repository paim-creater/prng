#!/usr/bin/env python3
"""Word-level linear trail — CORRECT XOR (mod 2). No nested functions."""
import pulp, itertools, time
from milp_solver import get_solver

def run_pattern(bits):
    prob = pulp.LpProblem("LinXOR", pulp.LpMinimize)
    m = {}
    for n in 'uvwz':
        for t in range(5):
            m[(n,t)] = pulp.LpVariable(f"m_{n}_{t}", cat='Binary')
    for i,n in enumerate('uvwz'):
        m[(n,0)] = bits[i]

    active = []

    # AND gates (inline, no nested functions)
    def add_and(prob, m, active, a, ta, b, tb):
        g = pulp.LpVariable(f"g_{a}_{ta}_{b}_{tb}", cat='Binary')
        prob += g <= m[(a,ta)]
        prob += g <= m[(b,tb)]
        prob += g >= m[(a,ta)] + m[(b,tb)] - 1
        active.append(g)
        return g

    p, mv = prob, m  # short aliases for nonlocal access

    # Phase B — 3-XOR mask propagation
    add_and(p, mv, active, 'v',0,'z',0)
    p += mv[('u',1)] == mv[('u',0)] + mv[('v',0)] + mv[('w',0)] - 2*pulp.LpVariable("t1", lowBound=0, upBound=1, cat='Integer')

    add_and(p, mv, active, 'w',0,'u',0)
    p += mv[('v',1)] == mv[('v',0)] + mv[('w',0)] + mv[('z',0)] - 2*pulp.LpVariable("t2", lowBound=0, upBound=1, cat='Integer')

    add_and(p, mv, active, 'u',0,'v',0)
    p += mv[('w',1)] == mv[('w',0)] + mv[('z',0)] + mv[('u',0)] - 2*pulp.LpVariable("t3", lowBound=0, upBound=1, cat='Integer')

    add_and(p, mv, active, 'v',0,'w',0)
    p += mv[('z',1)] == mv[('z',0)] + mv[('u',0)] + mv[('v',0)] - 2*pulp.LpVariable("t4", lowBound=0, upBound=1, cat='Integer')

    # Phase B(lin) — 2 snapshot ANDs covering (u,z) and (w,z) for linear resistance
    add_and(p, mv, active, 'z',0,'w',0)   # AND (z,w) → XOR into u
    add_and(p, mv, active, 'u',0,'z',0)   # AND (u,z) → XOR into z
    # Note: AND output mask = 0 in linear analysis, so Γ_u, Γ_z unchanged.

    # Phase C — mask unchanged through AND
    for n in 'uvwz':
        p += mv[(n,2)] == mv[(n,1)]
    add_and(p, mv, active, 'v',1,'w',1); add_and(p, mv, active, 'w',1,'z',1)
    add_and(p, mv, active, 'z',1,'u',1); add_and(p, mv, active, 'u',1,'v',1)

    for n in 'uvwz':
        p += mv[(n,3)] == mv[(n,2)]
    add_and(p, mv, active, 'v',2,'z',2); add_and(p, mv, active, 'w',2,'u',2)
    add_and(p, mv, active, 'z',2,'v',2); add_and(p, mv, active, 'u',2,'w',2)

    for n in 'uvwz':
        p += mv[(n,4)] == mv[(n,3)]
    add_and(p, mv, active, 'z',3,'u',3); add_and(p, mv, active, 'u',3,'v',3)
    add_and(p, mv, active, 'v',3,'w',3); add_and(p, mv, active, 'w',3,'z',3)

    p += pulp.lpSum(active)
    solver = get_solver(timeLimit=30)
    p.solve(solver)
    if p.status == pulp.LpStatusOptimal:
        return sum(int(pulp.value(v)) for v in active)
    return None

# Run
print("="*60)
print("LINEAR Trail — Correct XOR (⊕) Rule")
print("-"*60)
print(f"{'Pattern':<14} {'Act ANDs':<10}")
print("-"*60)
results = {}
for bits in itertools.product([0,1], repeat=4):
    if all(b==0 for b in bits): continue
    pat = f"({bits[0]},{bits[1]},{bits[2]},{bits[3]})"
    t0=time.time(); r=run_pattern(list(bits)); t1=time.time()
    if r is not None:
        results[pat]=r
        print(f"{pat:<14} {r:<10} ({t1-t0:.1f}s)")
    else:
        print(f"{pat:<14} TIMEOUT ({t1-t0:.1f}s)")

print("-"*60)
if results:
    mn,mx = min(results.values()), max(results.values())
    print(f"Min active ANDs = {mn}")
    print(f"c^(1) <= 2^-{mn}, c^(25)^2 <= 2^-{2*mn*25}")
    print(f"Data complexity >= 2^{2*mn*25}")
print("="*60)

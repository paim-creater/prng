#!/usr/bin/env python3
"""W=64 bit-level trail search. No nested functions (avoids Python scoping)."""
import pulp, sys, time
from milp_solver import get_solver

def run_trail(W=64, TL=3600):
    prob = pulp.LpProblem("Trail_W64", pulp.LpMinimize)
    d = {}
    for n in 'uvwz':
        for t in range(5):
            d[(n,t)] = [pulp.LpVariable(f"d_{n}_{t}_{i}", cat='Binary') for i in range(W)]
    prob += pulp.lpSum(d[(n,0)][i] for n in 'uvwz' for i in range(W)) >= 1
    act = []

    def a_and(p, mv, al, an, at, ra, bn, bt, rb, tn, tt):
        for i in range(W):
            sa, sb = (i-ra)%W, (i-rb)%W
            g = pulp.LpVariable(f"g_{an}{at}{bn}{bt}_{i}", cat='Binary')
            p += g <= mv[(an,at)][sa]
            p += g <= mv[(bn,bt)][sb]
            p += g >= mv[(an,at)][sa] + mv[(bn,bt)][sb] - 1
            al.append(g)
            p += mv[(tn,tt)][i] >= g

    def xmax(p, mv, tn, tt, srcs):
        for i in range(W):
            terms = []
            for sn, st, ro in srcs:
                ix = (i-ro)%W
                terms.append(mv[(sn,st)][ix])
                p += mv[(tn,tt)][i] >= mv[(sn,st)][ix]
            p += mv[(tn,tt)][i] <= pulp.lpSum(terms)

    p, mv, al = prob, d, act
    a_and(p, mv, al, 'v',0,5,'z',0,25,'u',1); xmax(p, mv, 'u',1,[('u',0,0),('v',0,5),('w',0,17)])
    a_and(p, mv, al, 'w',0,11,'u',0,29,'v',1); xmax(p, mv, 'v',1,[('v',0,0),('w',0,11),('z',0,23)])
    a_and(p, mv, al, 'u',0,9,'v',0,15,'w',1); xmax(p, mv, 'w',1,[('w',0,0),('z',0,13),('u',0,31)])
    a_and(p, mv, al, 'v',0,27,'w',0,21,'z',1); xmax(p, mv, 'z',1,[('z',0,0),('u',0,17),('v',0,7)])
    # Phase B(lin): 2 snapshot ANDs covering (u,z) and (w,z)
    a_and(p, mv, al, 'z',0,23,'w',0,53,'u',1)  # (z,w)→u, using rotl(z0,23) ∧ rotl(w0,53)
    a_and(p, mv, al, 'u',0,5,'z',0,25,'z',1)   # (u,z)→z, using rotl(u0,5) ∧ rotl(z0,25)
    for n in 'uvwz':
        for i in range(W):
            p += mv[(n,2)][i] >= mv[(n,1)][i]
    a_and(p, mv, al, 'v',1,31,'w',1,53,'u',2); a_and(p, mv, al, 'w',1,17,'z',1,43,'v',2)
    a_and(p, mv, al, 'z',1,7,'u',1,23,'w',2); a_and(p, mv, al, 'u',1,5,'v',1,19,'z',2)
    for n in 'uvwz':
        for i in range(W):
            p += mv[(n,3)][i] >= mv[(n,2)][i]
    a_and(p, mv, al, 'v',2,17,'z',2,43,'u',3); a_and(p, mv, al, 'w',2,7,'u',2,23,'v',3)
    a_and(p, mv, al, 'z',2,5,'v',2,19,'w',3); a_and(p, mv, al, 'u',2,31,'w',2,53,'z',3)
    for n in 'uvwz':
        for i in range(W):
            p += mv[(n,4)][i] >= mv[(n,3)][i]
    a_and(p, mv, al, 'z',3,7,'u',3,23,'u',4); a_and(p, mv, al, 'u',3,5,'v',3,19,'v',4)
    a_and(p, mv, al, 'v',3,31,'w',3,53,'w',4); a_and(p, mv, al, 'w',3,17,'z',3,43,'z',4)
    p += pulp.lpSum(al)

    print(f"W={W} free-D trail: ~{len(p.variables())} vars")
    t0 = time.time()
    get_solver(timeLimit=TL, msg=True).solve(p)
    t = time.time() - t0

    st = p.status
    print(f"\nStatus: {pulp.LpStatus[st]}, Time: {t:.1f}s")
    if st == pulp.LpStatusOptimal:
        ttl = sum(int(pulp.value(v)) for v in al)
        wc = len(set(v.name.rsplit('_',1)[0] for v in al if int(pulp.value(v))>0))
        ib = sum(int(pulp.value(mv[(n,0)][i])) for n in 'uvwz' for i in range(W))
        print(f"  Active AND bits: {ttl}")
        print(f"  Word-level active ANDs: {wc}")
        print(f"  Active input bits: {ib}")

        # Show which words have active input bits
        for n in 'uvwz':
            cnt = sum(int(pulp.value(mv[(n,0)][i])) for i in range(W))
            if cnt > 0:
                print(f"  Input word {n}: {cnt} active bits")
    elif st == pulp.LpStatusInfeasible:
        print("  INFEASIBLE — no D achieves 0 ANDs")
    return st, t

if __name__ == '__main__':
    run_trail(W=64, TL=3600)

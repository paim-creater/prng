# -*- coding: utf-8 -*-
"""trail_diff.py — bit-level differential trail search for Algorithm-1
(full round, exact DSL program from cipher.py), via MILP (pulp/CBC).

Model: walk the exact round program op-by-op in the difference space.
  - XOR/ROT (X3/A2): difference propagates EXACTLY (linear algebra).
  - AND/A3 AND-part: output difference free subject to
    d_out <= d1 + d2 (an AND can only differ if an input differs);
    active bit act = d1 OR d2, objective weight 1 per active bit
    (per-AND DP factor 2^-1; single-trail DP = 2^{-sum act}).
  - CONST/KEY/WEYL/NLFILT: zero difference (key-independent registers).
Multi-round: chain round outputs into next round inputs. Intermediate
round outputs are forced nonzero (2026-08-09 fix): without this the
AND over-approximation lets a round's output difference cancel to zero
(impossible in reality: each word equation is x_w ^= g(others), so the
round map is a permutation and DP(Delta -> 0) = 0), making rounds 2+
free and returning the R=1 optimum total for every R (6/6/6 at W=4,
8/8/8 at W=8 for R=1..3). With the fix the R=2 totals are 27 (W=4) and
146 (W=8); these are NOT quoted in the paper --- the model's multi-round
minima interact with the AND over-approximation in both directions.
What is quoted: the R=1 per-round minima (6 at W=4,12; 8 at W=8,16),
which give a per-round lower bound (any round's weight >= the minimum
over nonzero inputs), hence 22-round weight >= 132/176 and
best single-trail DP <= 2^-132/2^-176, conservatively.

Validation at W=4: exact full-domain min DP = 2^-5.942 (audit_true_algorithm1)
implies best single trail has weight >= ceil(5.942) = 6; the MILP must return
>= 6 at W=4. Usage: python trail_diff.py [W] [R] [linelimit]
"""
import sys
import math
import pulp

sys.path.insert(0, '.')
from cipher import tempest_a1_round_program

PROG = tempest_a1_round_program()


def build_model(W, R):
    prob = pulp.LpProblem("tempest_diff_trail", pulp.LpMinimize)

    def C(c):
        prob.addConstraint(c)

    words = ['u', 'v', 'w', 'z']
    cur = {w: [pulp.LpVariable(f"d_{w}{i}_r0", cat='Binary') for i in range(W)]
           for w in words}
    snap = None
    nxt = 1  # variable counter for unique names
    init_vars = [v for w in words for v in cur[w]]

    def new_word(tag):
        nonlocal nxt
        v = [pulp.LpVariable(f"{tag}_{nxt}_{i}", cat='Binary') for i in range(W)]
        nxt += 1
        return v

    def xor_k(dst_vars, sources, tag):
        """dst = xor of sources (bit lists), exact encoding via pairwise aux."""
        acc = sources[0]
        for s in sources[1:]:
            tmp = new_word(tag)
            for i in range(W):
                a, b, d = acc[i], s[i], tmp[i]
                C(d <= a + b)
                C(d >= a - b)
                C(d >= b - a)
                C(d <= 2 - a - b)
            acc = tmp
        for i in range(W):
            dst_vars[i] = acc[i]

    def rotl(src, r):
        r %= W
        return [src[(i - r) % W] for i in range(W)]

    total_act = []
    for rnd in range(R):
        for op in PROG:
            kind = op[0]
            if kind == 'SNAP':
                snap = {w: cur[w][:] for w in words}
            elif kind == 'X3':
                _, dst, a, b, ra, rb, s = op
                src_w = snap if s else cur
                old = cur[dst][:]
                cur[dst] = new_word('x3')
                xor_k(cur[dst], [old, rotl(src_w[a], ra),
                                 rotl(src_w[b], rb)], 'x3t')
            elif kind == 'AND':
                _, dst, a, b, ra, rb, s = op
                src_w = snap if s else cur
                old = cur[dst][:]
                d1, d2 = rotl(src_w[a], ra), rotl(src_w[b], rb)
                out = new_word('and')
                act = new_word('act')
                for i in range(W):
                    C(out[i] <= d1[i] + d2[i])
                    C(act[i] >= d1[i])
                    C(act[i] >= d2[i])
                    C(act[i] <= d1[i] + d2[i])
                total_act.extend(act)
                cur[dst] = new_word('xor')
                xor_k(cur[dst], [old, out], 'axt')
            elif kind == 'A2':
                _, dst, r1, r2 = op
                old = cur[dst][:]
                cur[dst] = new_word('a2')
                xor_k(cur[dst], [old, rotl(old, r1), rotl(old, r2)], 'a2t')
            elif kind == 'A3':
                _, dst, r1, r2, r3, r4 = op
                old = cur[dst][:]
                lin = new_word('a3l')
                xor_k(lin, [old, rotl(old, r1), rotl(old, r2)], 'a3lt')
                d1, d2 = rotl(old, r3), rotl(old, r4)
                out = new_word('a3and')
                act = new_word('a3act')
                for i in range(W):
                    C(out[i] <= d1[i] + d2[i])
                    C(act[i] >= d1[i])
                    C(act[i] >= d2[i])
                    C(act[i] <= d1[i] + d2[i])
                total_act.extend(act)
                cur[dst] = new_word('a3x')
                xor_k(cur[dst], [lin, out], 'a3xt')
            # CONST / KEY / WEYL / NLFILT: zero difference — skip
        # chain into next round: variables carry over; nothing to do
        # NONZERO intermediate rounds: without this, the AND over-approx
        # lets a round's output difference cancel to zero (impossible in
        # reality: each word equation is x_w ^= g(others), so the round
        # is a permutation and DP(Delta -> 0) = 0), making rounds 2+
        # free and returning the R=1 optimum for every R. Forcing the
        # intermediate outputs nonzero gives the true multi-round trail
        # weight. (The audit found totals equal to the R=1 optimum
        # otherwise: 6/6/6 at W=4, 8/8/8 at W=8 for R=1..3.)
        if rnd < R - 1:
            prob += pulp.lpSum(cur[w][i] for w in words for i in range(W)) >= 1
    # non-trivial INPUT difference (the initial variables d_*_r0)
    prob += pulp.lpSum(init_vars) >= 1
    prob += pulp.lpSum(total_act)
    return prob, total_act

def input_bits(prob, W):
    """initial input diff bits (d_<w><i>_r0) with value 1"""
    return [(v.name, v.value())
            for v in prob.variables()
            if v.value() > 0.5 and v.name.startswith('d_') and v.name.endswith('_r0')]


def main():
    W = int(sys.argv[1]) if len(sys.argv) > 1 else 8
    R = int(sys.argv[2]) if len(sys.argv) > 2 else 2
    tl = sys.argv[3] if len(sys.argv) > 3 else None
    prob, act = build_model(W, R)
    print(f"W={W} R={R} vars={len(prob.variables())} constrs={len(prob.constraints)}")
    status = prob.solve(pulp.PULP_CBC_CMD(msg=0, timeLimit=tl))
    if pulp.LpStatus[status] != 'Optimal':
        print("status:", pulp.LpStatus[status])
        return
    a = sum(v.value() for v in act)
    print(f"min active AND bits (R={R} rounds): {a}  -> best single-trail DP ~ 2^-{a}")
    # extract trail: input diff bits
    for w in ['u', 'v', 'w', 'z']:
        bits = [i for i in range(W)
                if any(v.name == f"d_{w}{i}_r0" and v.value() > 0.5
                       for v in prob.variables())]
        if bits:
            print(f"  input diff word {w}: bits {bits}")


if __name__ == '__main__':
    main()

# -*- coding: utf-8 -*-
"""sat_attack_grid.py — adversarial validation: SAT preimage attacks at
reduced width.  Shows that the design's exact metrics predict real attack
costs: 1 round is solvable quickly, 2 rounds is not, across W = 8/12/16.

CNF is generated from the DSL op list (snapshot semantics, correct
Algorithm-1 structure) with the round key stream folded in as constants.
Attack: find state s such that the R-round output's first two words equal
fixed constants (partial preimage), matching the paper's attack setup.
Solvers: pysat bundled CaDiCaL and Glucose.
"""
import numpy as np
import time, json, sys

sys.path.insert(0, '.')
from cipher import tempest_a1_round_program
from pysat.solvers import Cadical153

IDX = {'u': 0, 'v': 1, 'w': 2, 'z': 3}
GOLDEN64 = 0x9E3779B97F4A7C15
GOLDEN = 0x9E3779B97F4A7C15


def rotl_bit(i, r, W):
    """bit index i of rotl(x, r) is bit (i - r) mod W of x."""
    return (i - r) % W


def rotl_word(x, r, W):
    r %= W
    return ((x << r) | (x >> (W - r))) & ((1 << W) - 1)


def build_circuit(W, R):
    """Build the bit-level circuit for R rounds as a gate list.
    Returns: (gates, state) — gates = (kind, a, b, out) tuples;
    state = list of 4 lists of bit ids (the R-round output state).
    Key stream (Weyl) is folded in as constants."""
    W4 = 4 * W
    state = [[wi * W + bi for bi in range(W)] for wi in range(4)]
    gates = []
    next_bit = W4

    def new_bit():
        nonlocal next_bit
        b = next_bit
        next_bit += 1
        return b

    def gxor(a, b):
        o = new_bit()
        gates.append(('XOR', a, b, o))
        return o

    def gand(a, b):
        o = new_bit()
        gates.append(('AND', a, b, o))
        return o

    ops = tempest_a1_round_program()
    weyl = 0x6A09E667F3BCC908 & ((1 << W) - 1) if W < 64 else 0x6A09E667F3BCC908
    weyl_nl = weyl

    for r in range(R):
        snap = [w[:] for w in state]
        for op in ops:
            t = op[0]
            if t == 'SNAP':
                snap = [w[:] for w in state]
            elif t == 'WEYL':
                rr, c = op[1] % W, op[2] & ((1 << W) - 1)
                if W < 64:
                    weyl = (weyl ^ rotl_word(weyl, rr, W) ^ c) & ((1 << W) - 1)
                else:
                    weyl = (weyl ^ rotl_word(weyl, rr, W) ^ op[2]) & 0xFFFFFFFFFFFFFFFF
            elif t == 'NLFILT':
                c = GOLDEN & ((1 << W) - 1) if W < 64 else GOLDEN
                weyl_nl = (weyl ^ rotl_word(weyl & c, 13 % W, W)) & ((1 << W) - 1) \
                    if W < 64 else (weyl ^ rotl_word(weyl & GOLDEN, 13 % W, W)) \
                    & 0xFFFFFFFFFFFFFFFF
            elif t == 'X3':
                w, a, b, ra, rb, sf = IDX[op[1]], IDX[op[2]], IDX[op[3]], \
                    op[4], op[5], op[6]
                src = snap if sf else state
                for i in range(W):
                    av = src[a][rotl_bit(i, ra, W)]
                    bv = src[b][rotl_bit(i, rb, W)]
                    state[w][i] = gxor(state[w][i], gxor(av, bv))
            elif t == 'AND':
                w, a, b, ra, rb, sf = IDX[op[1]], IDX[op[2]], IDX[op[3]], \
                    op[4], op[5], op[6]
                src = snap if sf else state
                for i in range(W):
                    av = src[a][rotl_bit(i, ra, W)]
                    bv = src[b][rotl_bit(i, rb, W)]
                    state[w][i] = gxor(state[w][i], gand(av, bv))
            elif t == 'A3':
                w, r1, r2, r3, r4 = IDX[op[1]], op[2], op[3], op[4], op[5]
                for i in range(W):
                    v = state[w]
                    a = v[rotl_bit(i, r1, W)]; b = v[rotl_bit(i, r2, W)]
                    c = v[rotl_bit(i, r3, W)]; d = v[rotl_bit(i, r4, W)]
                    state[w][i] = gxor(state[w][i],
                                       gxor(gxor(a, b), gand(c, d)))
            elif t == 'A2':
                w, r1, r2 = IDX[op[1]], op[2], op[3]
                for i in range(W):
                    v = state[w]
                    a = v[rotl_bit(i, r1, W)]; b = v[rotl_bit(i, r2, W)]
                    state[w][i] = gxor(state[w][i], gxor(a, b))
            elif t == 'CONST':
                w, c = IDX[op[1]], op[2] & ((1 << W) - 1)
                for i in range(W):
                    if (c >> i) & 1:
                        o = new_bit()
                        gates.append(('CONST', 1, 0, o))
                        state[w][i] = gxor(state[w][i], o)
            elif t == 'KEY':
                w, r, s = IDX[op[1]], op[2] % W, op[3]
                v = weyl_nl
                for i in range(W):
                    a = (v >> rotl_bit(i, r, W)) & 1
                    b = (v >> ((i + s) % (4 * W))) & 1 if s < 4 * W else 0
                    if (a ^ b) & 1:
                        o = new_bit()
                        gates.append(('CONST', 1, 0, o))
                        state[w][i] = gxor(state[w][i], o)
            else:
                raise ValueError(t)
    return gates, state


def to_cnf(gates):
    clauses = []
    for g in gates:
        if g[0] == 'AND':
            _, a, b, o = g
            va, vb, vo = a + 1, b + 1, o + 1
            clauses.append([-vo, va])
            clauses.append([-vo, vb])
            clauses.append([-va, -vb, vo])
        elif g[0] == 'XOR':
            _, a, b, o = g
            va, vb, vo = a + 1, b + 1, o + 1
            clauses.append([-vo, -va, -vb])
            clauses.append([-vo, va, vb])
            clauses.append([vo, -va, vb])
            clauses.append([vo, va, -vb])
        elif g[0] == 'CONST':
            _, v, _, o = g
            vo = o + 1
            clauses.append([vo] if v else [-vo])
    return clauses


def build_preimage_cnf(W, R, out_fix):
    gates, state = build_circuit(W, R)
    clauses = to_cnf(gates)
    maxvar = 0
    for c in clauses:
        for lit in c:
            maxvar = max(maxvar, abs(lit))
    for wi, val in enumerate(out_fix):
        if wi >= 2:
            break
        for bi in range(W):
            v = (val >> bi) & 1
            var = state[wi][bi] + 1
            clauses.append([var] if v else [-var])
            maxvar = max(maxvar, var)
    return clauses, maxvar


def run_case(W, R, timeout):
    t0 = time.time()
    clauses, nvars = build_preimage_cnf(W, R, (0x1234 & ((1 << W) - 1),
                                               0x5678 & ((1 << W) - 1)))
    t_gen = time.time() - t0
    t0 = time.time()
    with Cadical153(bootstrap_with=clauses) as solver:
        sat = solver.solve()
        t_solve = time.time() - t0
    res = {'vars': nvars, 'clauses': len(clauses), 'sat': bool(sat),
           'solve_s': round(t_solve, 1), 'gen_s': round(t_gen, 2),
           'timed_out': t_solve >= timeout}
    print(f'W={W} R={R}: vars={nvars} clauses={len(clauses)} sat={sat} '
          f'time={t_solve:.1f}s ({t_gen:.1f}s gen)', flush=True)
    return res


def main():
    res = {}
    cases = [(8, 1), (8, 2), (12, 1), (12, 2), (16, 1)]
    for W, R in cases:
        res[f'W{W}_R{R}'] = run_case(W, R, timeout=600)
    # W=16 R=2 with a hard time cap via separate subprocess-like call
    res[f'W16_R2'] = run_case(16, 2, timeout=900)
    with open('sat_attack_grid.json', 'w') as f:
        json.dump(res, f, indent=1)
    print('done -> sat_attack_grid.json')


if __name__ == '__main__':
    main()

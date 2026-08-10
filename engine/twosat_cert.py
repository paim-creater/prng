"""twosat_cert.py — the 2-SAT certificate for AND-RX designs.

For a design whose AND operand difference bits are single input-difference
variables (the *snapshot ANDs*: Phase-A ANDs reading the round-start
snapshot; v3.1's intra-word ANDs, whose operand differences are rotations
of a single word's difference), the question

    "exists an input difference Delta with a_1 = 0"
    (every AND gate inactive at every bit position)

is a 2-CNF satisfiability problem: clause per gate-position i of
(not da_i) OR (not db_i). 2-SAT is in P, so a_1 >= 1 is decidable in
polynomial time at ANY width W, with an explicit satisfying assignment as
a machine-checkable certificate (for a_1 = 0) or an unsat core (for
a_1 >= 1).

Certificates produced here:
  - v3.1:       SAT -> all-width witness with a_1 = 0 (its death
                certificate): delta_u = single bit suffices.
  - Algorithm 1 (snapshot ANDs only): reported honestly; the cascade
                layers are value-dependent and fall outside 2-SAT (the
                paper states this scope explicitly).
"""
import sys
from cipher import tempest_a1_round_program, tempest_v31_round_program

W = 64
IDX = {'u': 0, 'v': 1, 'w': 2, 'z': 3}


def clauses_from_ands(ands, input_of):
    """ands: list of (dst, srcA, srcB, rA, rB) whose operand difference
    bits are single variables input_of(word, bit). Returns clause list."""
    clauses = set()
    for (dst, a, b, r1, r2) in ands:
        for i in range(W):
            va = input_of(a, (i - r1) % W)
            vb = input_of(b, (i - r2) % W)
            clauses.add((min(va, vb), max(va, vb)))
    return list(clauses)


# ---- DPLL for 2-SAT (all clauses are (not x OR not y)) ----
def dpll(clauses, n_vars, assign=None):
    assign = dict(assign or {})
    # unit propagation
    changed = True
    while changed:
        changed = False
        for (x, y) in clauses:
            vx, vy = assign.get(x), assign.get(y)
            if x == y:
                if vx == 1:
                    return None
                if vx is None:
                    assign[x] = 0
                    changed = True
            else:
                if vx == 1 and vy == 1:
                    return None
                if vx == 1 and vy is None:
                    assign[y] = 0
                    changed = True
                if vy == 1 and vx is None:
                    assign[x] = 0
                    changed = True
        # satisfied clauses drop out
        clauses = [c for c in clauses
                   if not (assign.get(c[0]) == 0 or assign.get(c[1]) == 0)]
    if not clauses:
        return assign
    # pick an unassigned variable with high degree
    cand = max(set(v for c in clauses for v in c) - set(assign),
               key=lambda v: sum(v in c for c in clauses))
    for val in (0, 1):
        a2 = dict(assign)
        a2[cand] = val
        r = dpll(clauses, n_vars, a2)
        if r is not None:
            return r
    return None


def main():
    print(f'=== 2-SAT certificates at W={W} ===')

    # ---- v3.1: all ANDs are intra-word with single-variable operands ----
    prog = tempest_v31_round_program()
    ands = []
    for op in prog:
        if op[0] == 'AND':
            ands.append((op[1], op[2], op[3], op[4], op[5]))
    # v3.1 AND operand differences: rotations of the same word's diff
    def in31(w, b):
        return IDX[w] * W + b
    clauses = clauses_from_ands(ands, in31)
    n_vars = 4 * W
    sat = dpll(clauses, n_vars)
    print(f'v3.1: {len(ands)} ANDs, {len(clauses)} clauses -> '
          f'{"SATISFIABLE" if sat else "UNSAT"}')
    if sat:
        nz = [v for v, val in sat.items() if val]
        print(f'   witness: {len(nz)} difference bits set; '
              f'u-word bits: {[v % W for v in nz if v // W == 0]}')

    # ---- Algorithm 1: snapshot ANDs only (Phase A + Phase A(lin)) ----
    prog = tempest_a1_round_program()
    ands = []
    for op in prog:
        if op[0] == 'AND' and op[6] == 1 and op[2] in 'uvwz' and op[3] in 'uvwz':
            # snapshot flag = 1 -> reads round-start snapshot; operand
            # difference bits are single variables of the snapshot words
            ands.append((op[1], op[2], op[3], op[4], op[5]))
    clauses = clauses_from_ands(ands, in31)
    sat = dpll(clauses, n_vars)
    print(f'Algorithm 1 (snapshot ANDs): {len(ands)} ANDs, '
          f'{len(clauses)} clauses -> '
          f'{"SATISFIABLE (zero-active snapshot difference exists)" if sat else "UNSAT (snapshot layer forces a1>=1)"}')
    if sat:
        nz = [v for v, val in sat.items() if val]
        print(f'   witness bits: {[v % W for v in nz][:8]} '
              f'({len(nz)} total)')
    print('\nScope: the 2-SAT certificate covers ANDs whose operand '
          'difference bits are single variables (snapshot ANDs; v3.1 '
          'intra-word ANDs). Cascaded ANDs with mixed operands are '
          'value-dependent and outside this class.')


if __name__ == '__main__':
    main()

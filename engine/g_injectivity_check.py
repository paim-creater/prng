# -*- coding: utf-8 -*-
"""g_injectivity_check.py — follow-up on g_invert_check.py: the SAT
inversion at W=64 found t* != t0 with F(t*) == F(t0). Quantify:

  (a) direct re-evaluation: F(t*) == F(t0) with t* != t0 (confirm a real
      collision, not a CNF artifact);
  (b) linear stages pre-mix 1/2 and fold: GF(2) rank at W=64
      (rank < 64 => information loss in the linear stages);
  (c) each andmix4 level at W=64: SAT collision search (x1 != x2 with
      level(x1) == level(x2)) — which level(s) are non-injective;
  (d) exact image size of F and of each level at small widths
      (exhaustive) to quantify the per-word information loss;
  (e) preimage count of one y at W=64 via iterative SAT blocking.
"""
import sys, time
import numpy as np

sys.path.insert(0, '.')
from pysat.solvers import Cadical153

M = (1 << 64) - 1
LEV = [(31, 53), (17, 43), (7, 23), (5, 19)]


def rotl(x, r):
    return ((x << r) | (x >> (64 - r))) & M


def ref_F(t):
    t = (t ^ rotl(t, 22) ^ rotl(t, 26)) & M
    t = (t ^ rotl(t, 16) ^ rotl(t, 14)) & M
    for r1, r2 in LEV:
        t = (t ^ (rotl(t, r1) & rotl(t, r2))) & M
    return (t ^ (t >> 32)) & M


def ref_premix1(t):
    return (t ^ rotl(t, 22) ^ rotl(t, 26)) & M


def ref_premix2(t):
    return (t ^ rotl(t, 16) ^ rotl(t, 14)) & M


def ref_fold(t):
    return (t ^ (t >> 32)) & M


def ref_andlevel(t, r1, r2):
    return (t ^ (rotl(t, r1) & rotl(t, r2))) & M


def gf2_rank(f, n=64):
    """rank of linear map f over F2 (via images of basis vectors)."""
    rows = []
    for i in range(n):
        col = f(1 << i)
        rows.append([(col >> j) & 1 for j in range(n)])
    rank = 0
    for col in range(n):
        piv = next((r for r in range(rank, n) if rows[r][col]), None)
        if piv is None:
            continue
        rows[rank], rows[piv] = rows[piv], rows[rank]
        for r in range(n):
            if r != rank and rows[r][col]:
                for c in range(n):
                    rows[r][c] ^= rows[rank][c]
        rank += 1
    return rank


def level_circuit(r1, r2):
    """bit-level circuit of y = x ^ (rotl(x,r1) & rotl(x,r2)); input bits
    are 0..63, gate outputs 64+."""
    gates = []
    nxt = [64]

    def nid():
        v = nxt[0]
        nxt[0] += 1
        return v

    def gxor(a, b):
        o = nid()
        gates.append(('X', a, b, o))
        return o

    def gand(a, b):
        o = nid()
        gates.append(('A', a, b, o))
        return o

    t = list(range(64))
    ra, rb = t[-r1:] + t[:-r1], t[-r2:] + t[:-r2]
    out = [gxor(t[i], gand(ra[i], rb[i])) for i in range(64)]
    return gates, out


def tseitin(gates, base=0):
    """1-indexed CNF for gates whose outputs are numbered from base."""
    clauses = []
    for i, (k, a, b, o) in enumerate(gates):
        v = o + 1
        a_, b_ = a + 1, b + 1
        if k == 'X':
            # o = a^b: (a∨b∨¬o)(a∨¬b∨o)(¬a∨b∨o)(¬a∨¬b∨¬o)
            clauses += [[a_, b_, -v], [a_, -b_, v], [-a_, b_, v], [-a_, -b_, -v]]
        else:
            clauses += [[-v, a_], [-v, b_], [v, -a_, -b_]]
    return clauses


def level_collision_sat(r1, r2):
    """x1 != x2 with level(x1) == level(x2) at W=64, or None."""
    g1, out1 = level_circuit(r1, r2)
    g2, out2 = level_circuit(r1, r2)
    # circuit 2's input block is vars 64..127; offset its gate ids
    g2o = [(k, a + 64, b + 64, o + 64) for k, a, b, o in g2]
    out2o = [o + 64 for o in out2]
    gates_all = g1 + g2o
    nvars = 128 + len(g1) + len(g2)
    clauses = tseitin(gates_all)
    # out1[i] == out2[i]
    for i in range(64):
        o1, o2 = out1[i] + 1, out2o[i] + 1
        clauses += [[o1, -o2], [-o1, o2]]
    # x1 != x2 via OR-chain of pairwise XORs with auxiliary vars
    aux = nvars
    prev = None
    for i in range(64):
        d = aux + 1 + i
        a, b = 64 + i + 1, 64 + 64 + i + 1   # x1[i], x2[i] (1-indexed)
        # d = a^b: (a∨b∨¬d)(a∨¬b∨d)(¬a∨b∨d)(¬a∨¬b∨¬d)
        clauses += [[a, b, -d], [a, -b, d], [-a, b, d], [-a, -b, -d]]
        if prev is None:
            prev = d
        else:
            o = aux + 65 + i
            # o = prev∨d: (¬prev∨o)(¬d∨o)(prev∨d∨¬o)
            clauses += [[-prev, o], [-d, o], [prev, d, -o]]
            prev = o
    clauses.append([prev])
    nvars = max(nvars, prev)
    t0 = time.time()
    with Cadical153(bootstrap_with=clauses) as slv:
        sat = slv.solve()
        model = slv.get_model() if sat else None
    dt = (time.time() - t0) * 1000
    if not sat:
        return None, dt
    tv = dict((abs(l) - 1, int(l > 0)) for l in model)
    x1 = sum(tv[i] << i for i in range(64))
    x2 = sum(tv[64 + i] << i for i in range(64))
    return (x1, x2), dt


def build_F_circuit():
    """full F(t) circuit (as in g_invert_check.py)."""
    gates = []
    nxt = [64]

    def nid():
        v = nxt[0]
        nxt[0] += 1
        return v

    def gxor(a, b):
        o = nid()
        gates.append(('X', a, b, o))
        return o

    def gand(a, b):
        o = nid()
        gates.append(('A', a, b, o))
        return o

    t = list(range(64))
    r22, r26 = t[-22:] + t[:-22], t[-26:] + t[:-26]
    t = [gxor(gxor(t[i], r22[i]), r26[i]) for i in range(64)]
    r16, r14 = t[-16:] + t[:-16], t[-14:] + t[:-14]
    t = [gxor(gxor(t[i], r16[i]), r14[i]) for i in range(64)]
    for r1, r2 in LEV:
        ra, rb = t[-r1:] + t[:-r1], t[-r2:] + t[:-r2]
        t = [gxor(t[i], gand(ra[i], rb[i])) for i in range(64)]
    out = [gxor(t[i], t[i + 32]) for i in range(32)] + t[32:]
    return gates, out


def main():
    # (a) colliding pair, re-verified directly
    rng = np.random.default_rng(20260809)
    t0 = int(rng.integers(0, 2**64, dtype=np.uint64))
    y0 = ref_F(t0)
    gates, out = build_F_circuit()
    clauses = tseitin(gates)
    out_var = [o + 1 for o in out]
    ref = [(y0 >> i) & 1 for i in range(64)]
    unit = [[out_var[i] if ref[i] else -out_var[i]] for i in range(64)]
    with Cadical153(bootstrap_with=clauses + unit) as slv:
        sat = slv.solve()
        model = slv.get_model()
    tv = dict((abs(l) - 1, int(l > 0)) for l in model)
    t1 = sum(tv[i] << i for i in range(64))
    direct = (ref_F(t1) == y0)
    print(f"(a) F(t0)==F(t1): {direct}, t0=0x{t0:016x} != t1=0x{t1:016x}: {t0 != t1}")

    # (b) linear stages' GF(2) rank
    print(f"(b) GF(2) ranks @W=64: premix1 {gf2_rank(ref_premix1)}/64, "
          f"premix2 {gf2_rank(ref_premix2)}/64, fold {gf2_rank(ref_fold)}/64")

    # (c) which andmix4 levels are non-injective
    for r1, r2 in LEV:
        pair, dt = level_collision_sat(r1, r2)
        if pair is None:
            print(f"(c) level ({r1},{r2}): no collision found ({dt:.0f} ms)")
        else:
            x1, x2 = pair
            eq = ref_andlevel(x1, r1, r2) == ref_andlevel(x2, r1, r2)
            print(f"(c) level ({r1},{r2}): COLLISION x1=0x{x1:016x} x2=0x{x2:016x}, "
                  f"level(x1)==level(x2): {eq} ({dt:.0f} ms)")

    # (d) exact image sizes at small widths
    for W in (4, 8, 12):
        N = 1 << W
        m = (1 << W) - 1

        def r(x, k):
            k %= W
            return ((x << k) | (x >> (W - k))) & m
        seen = set()
        for t in range(N):
            tt = (t ^ r(t, 22) ^ r(t, 26)) & m
            tt = (tt ^ r(tt, 16) ^ r(tt, 14)) & m
            for r1, r2 in LEV:
                tt = (tt ^ (r(tt, r1) & r(tt, r2))) & m
            tt = (tt ^ (tt >> 32)) & m
            seen.add(tt)
        loss = W - np.log2(len(seen))
        print(f"(d) W={W}: |image(F)|={len(seen)}/{N} = 2^{np.log2(len(seen)):.3f}"
              f"  (loss {loss:.3f} bits)")
        if W == 8:
            for r1, r2 in LEV:
                s2 = set((t ^ (r(t, r1) & r(t, r2))) & m for t in range(N))
                print(f"     level ({r1},{r2}) @W=8: |image|={len(s2)} "
                      f"= 2^{np.log2(len(s2)):.2f}")

    # (e) preimage count at W=64 by blocking
    seen = {t1}
    cur = t1
    for it in range(6):
        blk = [[(i + 1) if not (cur >> i) & 1 else -(i + 1)] for i in range(64)]
        with Cadical153(bootstrap_with=clauses + unit + blk) as slv:
            if not slv.solve():
                break
            m2 = slv.get_model()
        tv = dict((abs(l) - 1, int(l > 0)) for l in m2)
        cur = sum(tv[i] << i for i in range(64))
        if cur in seen:
            break
        seen.add(cur)
    print(f"(e) preimages of y0 found by blocking: {len(seen)}"
          f"  (t0={t0} in set: {t0 in seen})")


if __name__ == '__main__':
    main()

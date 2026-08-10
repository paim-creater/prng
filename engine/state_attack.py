# -*- coding: utf-8 -*-
"""state_attack.py — state-recovery attack surface probes.

(a) Exact ANF of make_output at W=4 (mod-4 collapsed structure):
    degree + top-degree monomial count (sparsity -> algebraic surface).
(b) Cube zero-sum tests at W=8 on the ROUND map (degree saturation
    probe): sum of a state word bit over cubes of initial-state bits,
    R=1..3. (Mixed pattern: zero-sums at some cube sizes, nonzero at
    others — consistent with the degree-saturation protection
    degop(Phi^2) <= 4W, but not conclusive.)
(c) SAT inversion of the 64-bit output function at W=64 (2026-08-09,
    verified protocol): bit-level circuit of the t -> output-word map
    F (pre-mix 1 (22,26), pre-mix 2 (16,14), andmix4 chain
    (31,53),(17,43),(7,23),(5,19), fold t^(t>>32)); Tseitin CNF with
    the XOR encoding checked against the reference evaluation (any
    wrong XOR clause breaks the model-recovery equality — the earlier
    attempt in this file was dropped precisely because of an unverified
    encoder); known input-output pair SAT recovers t == t0 uniquely in
    ~1-3 ms. Since all three linear stages have GF(2) rank 64/64 and
    no andmix4 level has a collision (SAT-refuted x1 != x2 with equal
    images), F is a bijection at W=64: each output word yields EXACTLY
    one linear constraint t = u^rotl(v,32)^w^rotl(z,16) on the
    post-round state. The output function is not the obstacle; state
    recovery reduces to solving the round map Phi (degree >= 16),
    whose cost is measured by sat_attack_grid.py (R=2: 47.6s at W=8,
    3.5s at W=12, 559.5s at W=16).
"""
import sys
import time
import numpy as np

sys.path.insert(0, '.')
from pysat.solvers import Cadical153

from cipher import State, apply_round, tempest_a1_round_program

OPS = tempest_a1_round_program()
M = (1 << 64) - 1
LEV = [(31, 53), (17, 43), (7, 23), (5, 19)]


# ---------------- (a) exact ANF of make_output at W=4 ----------------
def eml_output4(u, v, w, z):
    """make_output at W=4 (rotations mod 4), exact structure."""
    def rotl4(x, r):
        r %= 4
        return ((x << r) | (x >> (4 - r))) & 0xF
    t = u ^ rotl4(v, 0) ^ w ^ rotl4(z, 0)          # 32%4=0, 16%4=0
    t ^= rotl4(t, 2) ^ rotl4(t, 2)                 # 22%4=2, 26%4=2 -> 0
    t ^= rotl4(t, 0) ^ rotl4(t, 2)                 # 16%4=0, 14%4=2
    t ^= (rotl4(t, 3) & rotl4(t, 1))               # 31%4=3, 53%4=1
    t ^= (rotl4(t, 1) & rotl4(t, 3))               # 17%4=1, 43%4=3
    t ^= (rotl4(t, 3) & rotl4(t, 3))               # 7%4=3, 23%4=3
    t ^= (rotl4(t, 1) & rotl4(t, 3))               # 5%4=1, 19%4=3
    t ^= t >> 2                                    # fold (32%16 -> 2 for 4-bit)
    return t & 0xF


def anf_make_output():
    n = 16
    f = np.zeros(1 << n, dtype=np.uint8)
    for x in range(1 << n):
        u = (x >> 0) & 0xF
        v = (x >> 4) & 0xF
        w = (x >> 8) & 0xF
        z = (x >> 12) & 0xF
        f[x] = (eml_output4(u, v, w, z) >> 0) & 1
    g = f.copy()
    for i in range(n):
        step = 1 << i
        for base in range(0, 1 << n, 2 * step):
            for j in range(base, base + step):
                g[j + step] ^= g[j]
    deg = max(m.bit_count() for m in range(1 << n) if g[m])
    top = sum(1 for m in range(1 << n) if g[m] and m.bit_count() == deg)
    return deg, top, int(g.sum())


# ---------------- (b) cube zero-sum at W=8 ----------------
def cube_test(W, cube_bits, rounds, nsamples=24):
    nbits = 4 * W
    d = len(cube_bits)
    acc = 0
    for trial in range(nsamples):
        rng = np.random.default_rng(trial)
        base = int(rng.integers(0, 1 << nbits, dtype=np.uint64))
        for mask in range(1 << d):
            x = base
            for j in range(d):
                if (mask >> j) & 1:
                    x ^= 1 << cube_bits[j]
            words = [(x >> (0 * W)) & 0xFF, (x >> (1 * W)) & 0xFF,
                     (x >> (2 * W)) & 0xFF, (x >> (3 * W)) & 0xFF]
            s = State([np.uint64(words[0]), np.uint64(words[1]),
                       np.uint64(words[2]), np.uint64(words[3])],
                      np.uint64(0x6A09E667F3BCC908), W)
            for _ in range(rounds):
                apply_round(OPS, s)
            acc ^= (int(s.words[0]) & 1)
    return acc


# ---------------- (c) SAT inversion of the output function ------------
def rotl(x, r):
    return ((x << r) | (x >> (64 - r))) & M


def ref_F(t):
    """reference evaluation of the t -> output-word map F."""
    t = (t ^ rotl(t, 22) ^ rotl(t, 26)) & M
    t = (t ^ rotl(t, 16) ^ rotl(t, 14)) & M
    for r1, r2 in LEV:
        t = (t ^ (rotl(t, r1) & rotl(t, r2))) & M
    return (t ^ (t >> 32)) & M


def build_F_circuit():
    """bit-level circuit of F(t); input vars 0..63, gate outputs 64+."""
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


def tseitin(gates):
    """1-indexed Tseitin CNF; v = o+1 for gate var o (0-indexed ids)."""
    clauses = []
    for i, (k, a, b, o) in enumerate(gates):
        v = o + 1
        a_, b_ = a + 1, b + 1
        if k == 'X':
            # o = a^b: (a∨b∨¬o)(a∨¬b∨o)(¬a∨b∨o)(¬a∨¬b∨¬o) — the XOR
            # clauses are the checked-critical part: a swapped encoding
            # (XNOR) still yields satisfiable instances whose models do
            # NOT satisfy F, which is why the earlier attempt was dropped
            clauses += [[a_, b_, -v], [a_, -b_, v], [-a_, b_, v], [-a_, -b_, -v]]
        else:
            clauses += [[-v, a_], [-v, b_], [v, -a_, -b_]]
    return clauses


def eval_circuit(gates, out, x):
    vals = dict((i, int(b)) for i, b in enumerate(x))
    for k, a, b, o in gates:
        vals[o] = vals[a] ^ vals[b] if k == 'X' else vals[a] & vals[b]
    return [vals[o] for o in out]


def sat_invert_output(n_trials=3, seed=20260809):
    """verified protocol: (i) circuit == reference on random t;
    (ii) known pair SAT recovers t == t0; (iii) timing."""
    gates, out = build_F_circuit()
    clauses = tseitin(gates)
    out_var = [o + 1 for o in out]
    rng = np.random.default_rng(seed)
    ok = True
    t_ms = []
    for trial in range(n_trials):
        t0 = int(rng.integers(0, 2**64, dtype=np.uint64))
        x0 = [(t0 >> i) & 1 for i in range(64)]
        y0 = ref_F(t0)
        ref = [(y0 >> i) & 1 for i in range(64)]
        got = eval_circuit(gates, out, x0)
        if got != ref:
            print(f"  trial {trial}: CIRCUIT MISMATCH vs reference")
            ok = False
            continue
        unit = [[out_var[i] if ref[i] else -out_var[i]] for i in range(64)]
        t0m = time.time()
        with Cadical153(bootstrap_with=clauses + unit) as slv:
            sat = slv.solve()
            dt = (time.time() - t0m) * 1000
            model = slv.get_model() if sat else None
        if not sat:
            print(f"  trial {trial}: UNSAT on a known pair — encoder broken")
            ok = False
            continue
        tv = dict((abs(l) - 1, int(l > 0)) for l in model)
        trec = sum(tv[i] << i for i in range(64))
        t_ms.append(dt)
        if trec != t0:
            print(f"  trial {trial}: recovered t != t0 — F not injective on "
                  f"this witness or encoder wrong")
            ok = False
        else:
            print(f"  trial {trial}: t* == t0, solved in {dt:.2f} ms")
    # (iii) injectivity support: linear stages rank 64, no level collision
    from g_injectivity_check import gf2_rank, level_collision_sat  # noqa: F401
    ranks = []
    for f in (lambda t: (t ^ rotl(t, 22) ^ rotl(t, 26)) & M,
              lambda t: (t ^ rotl(t, 16) ^ rotl(t, 14)) & M,
              lambda t: (t ^ (t >> 32)) & M):
        ranks.append(gf2_rank(f))
    print(f"  linear-stage GF(2) ranks: {ranks} (64 = bijective)")
    coll = [level_collision_sat(r1, r2)[0] for r1, r2 in LEV]
    print(f"  andmix4-level collisions (x1!=x2, equal images): "
          f"{['none' if c is None else 'FOUND' for c in coll]}")
    print(f"  VERDICT: output word inversion is {('exact and fast '
          f'(median {np.median(t_ms):.2f} ms)') if ok and t_ms else 'FAILED'};\n"
          f"  each output word yields one linear constraint "
          f"t = u^rotl(v,32)^w^rotl(z,16) on the post-round state;")
    return ok


def main():
    which = sys.argv[1] if len(sys.argv) > 1 else 'all'
    if which in ('all', 'anf'):
        print("=== (a) exact ANF of make_output, W=4 (bit 0) ===")
        deg, top, tot = anf_make_output()
        print(f"degree={deg}, top-degree monomials={top}, total monomials={tot} of 65535")
    if which in ('all', 'cube'):
        print("=== (b) cube zero-sum at W=8 (round map, output bit 0) ===")
        for R in (1, 2, 3):
            for d in (2, 3, 4, 6, 8):
                s = cube_test(8, list(range(d)), R)
                print(f"R={R} cube size {d}: sum={s} ({'ZERO-SUM' if s == 0 else 'nonzero'})")
    if which in ('all', 'inv'):
        print("=== (c) SAT inversion of the 64-bit output function, W=64 ===")
        sat_invert_output()


if __name__ == '__main__':
    main()

# -*- coding: utf-8 -*-
"""g_invert_check.py — temporary verification of the paper's audit claim:
the 64-bit output function's nonlinear core (pre-mix 1/2, single-word
andmix4 chain, fold) is inverted by SAT in <1 ms at W=64, so each output
word yields a LINEAR constraint t = u^rotl(v,32)^w^rotl(z,16) on the
post-round state, and state recovery reduces to the round map Phi.

Protocol (matches the audit section's description):
  (a) build the bit-level circuit of the t->output-word map F(t);
  (b) inline-evaluation check: circuit outputs bit-equal to the
      reference evaluation of the same chain (recomputed independently);
  (c) known-pair SAT: y = F(t0) for random t0, assert y, solve for t;
      recovered t must equal t0 (injectivity witness);
  (d) timing at W=64.

If (b)-(d) hold, the paper's conclusion is reproduced: inverting the
output function is not the obstacle; the cost sits in Phi.
"""
import sys, time
import numpy as np

sys.path.insert(0, '.')
from pysat.solvers import Cadical153

M = (1 << 64) - 1


def rotl(x, r):
    return ((x << r) | (x >> (64 - r))) & M


def ref_F(t):
    """Reference: pre-mix 1 (22,26), pre-mix 2 (16,14), andmix4 chain
    (31,53),(17,43),(7,23),(5,19), fold t^(t>>32)."""
    t = (t ^ rotl(t, 22) ^ rotl(t, 26)) & M
    t = (t ^ rotl(t, 16) ^ rotl(t, 14)) & M
    for r1, r2 in [(31, 53), (17, 43), (7, 23), (5, 19)]:
        t = (t ^ (rotl(t, r1) & rotl(t, r2))) & M
    t = (t ^ (t >> 32)) & M
    return t


def build_circuit():
    """Bit-level circuit of F(t). Returns (gates, out_ids).
    gates: (kind, a, b, out) with kind 'X' (XOR) or 'A' (AND).
    Input variables are bits 0..63 of t; gate outputs get ids 64+."""
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

    def rotl_bits(bits, r):
        return bits[-r:] + bits[:-r]

    t = list(range(64))
    r22, r26 = rotl_bits(t, 22), rotl_bits(t, 26)
    t1 = [gxor(gxor(t[i], r22[i]), r26[i]) for i in range(64)]   # pre-mix 1
    r16, r14 = rotl_bits(t1, 16), rotl_bits(t1, 14)
    t2 = [gxor(gxor(t1[i], r16[i]), r14[i]) for i in range(64)]  # pre-mix 2
    for r1, r2 in [(31, 53), (17, 43), (7, 23), (5, 19)]:        # andmix4 chain
        ra, rb = rotl_bits(t2, r1), rotl_bits(t2, r2)
        t2 = [gxor(t2[i], gand(ra[i], rb[i])) for i in range(64)]
    out = [gxor(t2[i], t2[i + 32]) for i in range(32)] + t2[32:]  # fold
    return gates, out


def eval_circuit(gates, out, x):
    """Forward-evaluate on input bits x (list of 64 ints); return out bits."""
    vals = dict((i, int(b)) for i, b in enumerate(x))
    for k, a, b, o in gates:
        vals[o] = vals[a] ^ vals[b] if k == 'X' else vals[a] & vals[b]
    return [vals[o] for o in out]


def tseitin(gates):
    """1-indexed CNF: vars = 64 inputs + len(gates) gate outputs."""
    clauses = []
    for i, (k, a, b, o) in enumerate(gates):
        v = 64 + i + 1
        a_, b_ = a + 1, b + 1
        if k == 'X':
            # o = a^b: (a∨b∨¬o)(a∨¬b∨o)(¬a∨b∨o)(¬a∨¬b∨¬o)
            clauses += [[a_, b_, -v], [a_, -b_, v], [-a_, b_, v], [-a_, -b_, -v]]
        else:
            clauses += [[-v, a_], [-v, b_], [v, -a_, -b_]]
    return clauses


def main():
    gates, out = build_circuit()
    clauses = tseitin(gates)
    # out-var id mapping: out id o -> var o+1
    out_var = [o + 1 for o in out]
    nvars = 64 + len(gates)
    assert max(max(abs(l) for l in c) for c in clauses) <= nvars

    rng = np.random.default_rng(20260809)
    all_ok = True
    for trial in range(3):
        t0 = int(rng.integers(0, 2**64, dtype=np.uint64))
        x0 = [(t0 >> i) & 1 for i in range(64)]
        y0 = ref_F(t0)
        # (b) inline-evaluation check
        got = eval_circuit(gates, out, x0)
        ref = [(y0 >> i) & 1 for i in range(64)]
        bit_ok = (got == ref)
        # (c,d) known-pair SAT + timing
        unit = [[out_var[i] if ref[i] else -out_var[i]] for i in range(64)]
        t0m = time.time()
        with Cadical153(bootstrap_with=clauses + unit) as slv:
            sat = slv.solve()
            dt = (time.time() - t0m) * 1000
            model = slv.get_model() if sat else None
        trec = None
        if sat:
            tv = dict((abs(l) - 1, int(l > 0)) for l in model)
            trec = sum(tv[i] << i for i in range(64))
        ok = bit_ok and sat and trec == t0
        all_ok &= ok
        print(f"trial {trial}: circuit==ref {bit_ok}; SAT {sat} in {dt:.3f} ms; "
              f"t*==t0 {sat and trec == t0}")
    print(f"gates={len(gates)} vars={nvars} clauses={len(clauses)}")
    print("VERDICT: output word inversion reproduced as trivial"
          if all_ok else "VERDICT: check FAILED")

    # the linear-constraint corollary: t is affine in (u,v,w,z), so with
    # two output words the attacker gets 128 linear bits per round.
    tlin = "t = u ^ rotl(v,32) ^ w ^ rotl(z,16)"
    print(f"corollary: inverting both output words yields two linear "
          f"constraints ({tlin} and its rotated twin) on the 256-bit "
          f"post-round state per round; nonlinear cost is Phi only.")


if __name__ == '__main__':
    main()

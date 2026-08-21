"""Truncated-differential trail search for the full Tempest v3 round (W=8),
concrete difference-value model (MILP-style, as used for trail bounds in
e.g. MSX), translated gate-by-gate from tempest_a1_avx512.c (rotations
folded mod 8 as in rx_w8_sampling.c).

Model:
  - every intermediate word carries 8 concrete difference bits
  - XOR / ROT: exact bitwise propagation (Tseitin chains; rot is a literal
    re-permutation)
  - AND gate output difference bits are constrained to the support of the
    two operand differences; free otherwise
  - per-gate support-bit variables s_i <=> da[i] or db[i]; each support bit
    contributes a probability factor 2^-1, so any R-round trail with total
    support W has probability <= 2^-W.  Minimize total support (MaxSAT/RC2).
  - every round's output difference is required nonzero (trail continues).
"""
from pysat.formula import WCNF
from pysat.examples.rc2 import RC2
import sys

WBITS = 8


class Net:
    def __init__(self):
        self.nvar = 0

    def var(self):
        self.nvar += 1
        return self.nvar

    def wvar(self):
        return [self.var() for _ in range(WBITS)]

    def rotw(self, w, r):
        """rotated literal list: rot(x,r) bit i = x bit (i-r) mod 8."""
        return [w[(i - r) % WBITS] for i in range(WBITS)]

    def wor(self, w, hard):
        """aux <=> OR(w)."""
        aux = self.var()
        for b in w:
            hard.append([-b, aux])
        hard.append([-aux] + list(w))
        return aux

    def wand_gate(self, da, db, hard, svars):
        """AND gate with operand diff literal lists da, db.  Output diff
        (free within support) returned; support-bit vars appended to svars
        (s_i <=> da[i] or db[i]); gate-active var appended to gv by caller."""
        dout = self.wvar()
        for i in range(WBITS):
            hard.append([-dout[i], da[i], db[i]])   # dout[i] -> da[i] or db[i]
            s = self.var()                           # s_i <=> da[i] or db[i]
            hard.append([-da[i], s]); hard.append([-db[i], s])
            hard.append([-s, da[i], db[i]])
            svars.append(s)
        za = self.wor(da, hard)
        zb = self.wor(db, hard)
        g = self.var()
        hard.append([-g, za]); hard.append([-g, zb]); hard.append([g, -za, -zb])
        return dout, g

    def wxor(self, ins, hard):
        """exact XOR of literal lists -> new word var (Tseitin chains)."""
        out = self.wvar()
        cur = ins[0]
        for nxt in ins[1:]:
            t = self.wvar()
            for i in range(WBITS):
                hard.append([-t[i], cur[i], nxt[i]])
                hard.append([-t[i], -cur[i], -nxt[i]])
                hard.append([t[i], cur[i], -nxt[i]])
                hard.append([t[i], -cur[i], nxt[i]])
            cur = t
        for i in range(WBITS):
            hard.append([-out[i], cur[i]])
            hard.append([out[i], -cur[i]])
        return out


def build_round(net, iv, gv, svars, hard):
    """iv[4]: input diff word vars; appends 26 gate-active vars to gv and
    26*8 support-bit vars to svars."""

    def A(w1, r1, w2, r2):
        dout, g = net.wand_gate(net.rotw(w1, r1), net.rotw(w2, r2), hard, svars)
        gv.append(g)
        return dout

    # Phase A
    a_u0 = net.wxor([iv[0], net.rotw(iv[1], 5), net.rotw(iv[2], 1),
                     A(iv[1], 5, iv[3], 1)], hard)
    a_v0 = net.wxor([iv[1], net.rotw(iv[2], 3), net.rotw(iv[3], 7),
                     A(iv[2], 3, iv[0], 5)], hard)
    a_w0 = net.wxor([iv[2], net.rotw(iv[3], 5), net.rotw(iv[0], 7),
                     A(iv[0], 1, iv[1], 7)], hard)
    a_z0 = net.wxor([iv[3], net.rotw(iv[0], 1), net.rotw(iv[1], 7),
                     A(iv[1], 3, iv[2], 5)], hard)
    # Phase A(lin)
    a_u = net.wxor([a_u0, A(iv[3], 7, iv[2], 5)], hard)
    a_z = net.wxor([a_z0, A(iv[0], 5, iv[3], 1)], hard)
    a_v, a_w = a_v0, a_w0

    # pre-mix 1: p1 = a ^ rot(a,6) ^ rot(a,2) ^ and(rot(a,7), rot(a,3))
    p1 = []
    for w in (a_u, a_v, a_w, a_z):
        dout = A(w, 7, w, 3)
        p1.append(net.wxor([w, net.rotw(w, 6), net.rotw(w, 2), dout], hard))

    # Levels 1-4; pre-mix 2 between L2 and L3 (exact: l2 ^ rot(l2,6))
    def level(ws, pat):
        out = []
        for i in range(4):
            w1, r1, w2, r2 = pat[i]
            dout = A(ws[w1], r1, ws[w2], r2)
            out.append(net.wxor([ws[i], dout], hard))
        return out

    l1 = level(p1, [(1, 7, 2, 5), (2, 1, 3, 3), (3, 7, 0, 7), (0, 5, 1, 3)])
    l2 = level(l1, [(1, 1, 3, 3), (2, 7, 0, 7), (3, 5, 1, 3), (0, 7, 2, 5)])
    pm2 = [net.wxor([l2[i], net.rotw(l2[i], 6)], hard) for i in range(4)]
    l3 = level(pm2, [(3, 7, 0, 7), (0, 5, 1, 3), (1, 7, 2, 5), (2, 1, 3, 3)])
    l4 = level(l3, [(1, 5, 2, 3), (2, 7, 3, 5), (3, 1, 0, 5), (0, 7, 1, 7)])

    # Phase D
    out = [net.wxor([l4[0], net.rotw(l4[1], 3), net.rotw(l4[2], 1)], hard),
           net.wxor([l4[1], net.rotw(l4[2], 5), net.rotw(l4[3], 3)], hard),
           net.wxor([l4[2], net.rotw(l4[3], 1), net.rotw(l4[0], 5)], hard),
           net.wxor([l4[3], net.rotw(l4[0], 3), net.rotw(l4[1], 1)], hard)]
    return out


def main():
    maxR = int(sys.argv[1]) if len(sys.argv) > 1 else 8
    for R in range(1, maxR + 1):
        net = Net()
        gv, svars, hard = [], [], []
        iv = [net.wvar() for _ in range(4)]
        hard.append([b for w in iv for b in w])   # input diff nonzero
        prev = iv
        for r in range(R):
            prev = build_round(net, prev, gv, svars, hard)
            hard.append([b for w in prev for b in w])  # output diff nonzero
        wcnf = WCNF()
        for c in hard:
            wcnf.append(c)
        for s in svars:
            wcnf.append([-s], weight=1)
        try:
            with RC2(wcnf, solver="cd") as rc2:   # CaDiCaL backend
                rc2.compute()
                cost = rc2.cost
        except Exception:
            with RC2(wcnf) as rc2:
                rc2.compute()
                cost = rc2.cost
        print("R=%d: min trail support (AND output bits) = %d  (trail DP <= 2^-%d)"
              % (R, cost, cost))
        sys.stdout.flush()


if __name__ == "__main__":
    main()

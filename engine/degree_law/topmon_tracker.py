# -*- coding: utf-8 -*-
"""topmon_tracker.py -- exact top-monomial tracker for snapshot AND-RX
rounds (Direction 1: exact algebraic-degree law at full width).

Model.  Each state bit holds a Boolean polynomial in the 4W input
variables (word, position).  We represent the *top-degree monomials*
of each bit exactly: a monomial = a set of variables, stored as a
canonical tuple of 4 masks (one W-bit mask per word).  Monomials of
lower degree are kept only in the top `KLAYERS` degree layers below
the maximum, since the maximum degree of an AND output can only be
reached from top pairs unless heavy overlap cancels them.

Op semantics mirror cipher.py's DSL (snapshot semantics):
  * linear XOR of shifted copies   : symmetric difference of families
  * AND of two shifted bits        : multiset of set-unions, parity kept
  * CONST / WEYL / KEY (round key) : constants w.r.t. state variables

Fam(b) = dict{ canonical_set_tuple : parity }  restricted to the top
degree layers; m(b) = max |set| with odd parity, and the top-KLAYERS
list of (size, dict) is maintained.
"""
import json, sys, itertools

sys.setrecursionlimit(100000)


def rot_mask(mask, r, W):
    r %= W
    if r == 0:
        return mask
    return ((mask << r) & ((1 << W) - 1)) | (mask >> (W - r))


def canon(words):  # words: list of 4 ints -> sorted tuple
    return tuple(words)


def size_of(t):
    return sum(bin(x).count('1') for x in t)


class Tracker:
    def __init__(self, W, gates, linear_rot=None, nlayers=4):
        """gates: list of (dst_word, a_word, ra, b_word, rb) quadratic
        gates; linear_rot: list of (dst_word, src_word, r) linear XORs.
        Ops executed in order on current bit values."""
        self.W = W
        self.nlayers = nlayers          # top layers kept (nominal depth)
        self.mk = (1 << W) - 1
        # bit value = family (parity dict); init: bit (w,p) = monomial {e_{w,p}}
        self.fam = {}
        for w in range(4):
            for p in range(W):
                t = [0, 0, 0, 0]
                t[w] = 1 << p
                f = {canon(t): 1}
                self.fam[(w, p)] = f
        self.gates = gates

    # -- family plumbing -------------------------------------------------
    def _layers_of(self, fams):
        """fams: dict set->parity; return sorted list [(size, dict)] of
        layers above the max minus nlayers, largest first."""
        if not fams:
            return []
        m = max(size_of(s) for s in fams)
        layers = []
        for drop in range(self.nlayers + 1):
            d = {}
            for s, c in fams.items():
                if size_of(s) == m - drop and c % 2:
                    d[s] = 1
            if d:
                layers.append((m - drop, d))
        return layers

    def _top_set(self, fams):
        return self._layers_of(fams)

    def _trunc(self, fam):
        """keep only sets within nlayers of the maximum size (per bit)."""
        if not fam:
            return fam
        m = max(size_of(s) for s in fam)
        return {s: c for s, c in fam.items() if c % 2
                and size_of(s) >= m - self.nlayers}

    def shift(self, famdict, w, r):
        """Rotation selects *which bit polynomial* feeds a gate; variable
        coordinates are absolute, so no relabelling happens here."""
        return famdict


    def _maxdeg(self, F):
        return max(size_of(s) for fam in F.values() for s in fam)

    def _trace(self, F, tag):
        if getattr(self, 'trace', False):
            print(f'  {tag}: max deg {self._maxdeg(F)}', flush=True)

    # -- linear XOR of two families --------------------------------------
    def xorsum(self, fa, fb):
        out = dict(fa)
        for s, c in fb.items():
            out[s] = out.get(s, 0) ^ c
            if out[s] == 0:
                del out[s]
        return out

    # -- AND: product multiset over layer-restricted pairs ----------------
    def and_mul(self, fa, fb):
        """fa, fb = full parity dicts.  Pair only (i,j) with i+j<=nlayers
        of nominal top layers; union sets; keep parity; return parity dict
        (all sets, any size) -- caller truncates to top layers."""
        la = self._layers_of(fa)
        lb = self._layers_of(fb)
        # truncate nominal depth so i+j <= nlayers
        cand = {}
        for i, (ma, da) in enumerate(la[: self.nlayers + 1]):
            for j, (mb, db) in enumerate(lb[: self.nlayers + 1]):
                if i + j > self.nlayers:
                    continue
                for sa in da:
                    ua = [*sa]
                    for sb in db:
                        ub = [*sb]
                        t = canon([ua[w] | ub[w] for w in range(4)])
                        cand[t] = cand.get(t, 0) ^ 1
                        if cand[t] == 0:
                            del cand[t]
        return cand

    # -- interpreter over one round ----------------------------------------
    def run_round(self, ops, collect=None):
        """ops mirror the DSL: ('SNAP',) freezes a snapshot; X3/AND read
        the active snapshot (sf=1 in the program); A2/A3 read current
        in-place values; CONST/WEYL/NLFILT/KEY are constants.  Families
        keyed by absolute (word, position) monomial sets."""
        wi = {'u': 0, 'v': 1, 'w': 2, 'z': 3}
        F = {}
        for (w, p) in self.fam:
            F[(w, p)] = dict(self.fam[(w, p)])   # copy of init
        snap = {k: dict(v) for k, v in F.items()}
        for op in ops:
            t = op[0]
            if t == 'SNAP':
                snap = {k: dict(v) for k, v in F.items()}
                if getattr(self, 'trace', False):
                    print(f'  SNAP: max deg {self._maxdeg(F)}', flush=True)
                continue
            if t == 'CONST' or t == 'WEYL' or t == 'NLFILT' or t == 'KEY':
                continue
            if t == 'X3':
                d, a, b, r1, r2 = wi[op[1]], wi[op[2]], wi[op[3]], op[4], op[5]
                for p in range(self.W):
                    s1 = self.shift(snap[(a, (p - r1) % self.W)], a, r1)
                    s2 = self.shift(snap[(b, (p - r2) % self.W)], b, r2)
                    F[(d, p)] = self._trunc(self.xorsum(self.xorsum(F[(d, p)], s1), s2))
            elif t == 'A2':
                d, r1, r2 = wi[op[1]], op[2], op[3]
                wv = {p: dict(F[(d, p)]) for p in range(self.W)}   # word snapshot
                for p in range(self.W):
                    s1 = wv[(p - r1) % self.W]
                    s2 = wv[(p - r2) % self.W]
                    F[(d, p)] = self._trunc(self.xorsum(self.xorsum(F[(d, p)], s1), s2))
            elif t == 'A3':
                d, r1, r2, r3, r4 = wi[op[1]], op[2], op[3], op[4], op[5]
                wv = {p: dict(F[(d, p)]) for p in range(self.W)}   # word snapshot
                for p in range(self.W):
                    s1 = wv[(p - r1) % self.W]
                    s2 = wv[(p - r2) % self.W]
                    a1 = wv[(p - r3) % self.W]
                    a2 = wv[(p - r4) % self.W]
                    lin = self.xorsum(self.xorsum(F[(d, p)], s1), s2)
                    if (r3 - r4) % self.W == 0:
                        # rot_r(x) & rot_r(x) is idempotent: adds rot_r(x)
                        F[(d, p)] = self._trunc(self.xorsum(lin, a1))
                    else:
                        F[(d, p)] = self._trunc(self.xorsum(lin, self.and_mul(a1, a2)))
            elif t == 'AND':
                d, a, b, r1, r2 = wi[op[1]], wi[op[2]], wi[op[3]], op[4], op[5]
                for p in range(self.W):
                    s1 = self.shift(snap[(a, (p - r1) % self.W)], a, r1)
                    s2 = self.shift(snap[(b, (p - r2) % self.W)], b, r2)
                    if (a, r1 % self.W) == (b, r2 % self.W):
                        # identical operand bit: AND = that bit itself
                        F[(d, p)] = self._trunc(self.xorsum(F[(d, p)], s1))
                    else:
                        prod = self.and_mul(s1, s2)
                        F[(d, p)] = self._trunc(self.xorsum(F[(d, p)], prod))
            else:
                raise ValueError(op)
            if t in ('X3', 'AND', 'A2', 'A3'):
                self._trace(F, str(op))
        self.fam = F
        return F

    def degrees(self, F=None):
        """per output bit max degree with odd parity (exact top size)."""
        F = F if F is not None else self.fam
        out = {}
        for (w, p), famd in F.items():
            out[(w, p)] = max(size_of(s) for s in famd)
        return out


# ----------------------------------------------------------------------
def build_round_ops():
    """Return the degree-relevant op list of one Tempest v3 round, in
    program order, exactly as cipher.tempest_a1_round_program."""
    ops = []
    # Phase A (X3 linear + AND quadratic), A(lin), A3 premix, L1..L4 ANDs,
    # Phase D X3 linear -- from the DSL program verbatim:
    prog = [('SNAP',), ('X3', 'u', 'v', 'w', 5, 17), ('AND', 'u', 'v', 'z', 5, 25),
            ('X3', 'v', 'w', 'z', 11, 23), ('AND', 'v', 'w', 'u', 11, 29),
            ('X3', 'w', 'z', 'u', 13, 31), ('AND', 'w', 'u', 'v', 9, 15),
            ('X3', 'z', 'u', 'v', 17, 7), ('AND', 'z', 'v', 'w', 27, 21),
            ('AND', 'u', 'z', 'w', 23, 53), ('AND', 'z', 'u', 'z', 5, 25),
            ('A3', 'u', 22, 26, 7, 19), ('A3', 'v', 22, 26, 7, 19),
            ('A3', 'w', 22, 26, 7, 19), ('A3', 'z', 22, 26, 7, 19),
            ('SNAP',), ('AND', 'u', 'v', 'w', 31, 53),
            ('AND', 'v', 'w', 'z', 17, 43), ('AND', 'w', 'z', 'u', 7, 23),
            ('AND', 'z', 'u', 'v', 5, 19),
            ('SNAP',), ('AND', 'u', 'v', 'z', 17, 43),
            ('AND', 'v', 'w', 'u', 7, 23), ('AND', 'w', 'z', 'v', 5, 19),
            ('AND', 'z', 'u', 'w', 31, 53),
            ('A2', 'u', 16, 14), ('A2', 'v', 16, 14),
            ('A2', 'w', 16, 14), ('A2', 'z', 16, 14),
            ('SNAP',), ('AND', 'u', 'z', 'u', 7, 23),
            ('AND', 'v', 'u', 'v', 5, 19), ('AND', 'w', 'v', 'w', 31, 53),
            ('AND', 'z', 'w', 'z', 17, 43),
            ('SNAP',), ('AND', 'u', 'v', 'w', 5, 19),
            ('AND', 'v', 'w', 'z', 31, 53), ('AND', 'w', 'z', 'u', 17, 53),
            ('AND', 'z', 'u', 'v', 7, 23),
            ('X3', 'u', 'v', 'w', 3, 9), ('X3', 'v', 'w', 'z', 5, 11),
            ('X3', 'w', 'z', 'u', 9, 13), ('X3', 'z', 'u', 'v', 11, 17)]
    return prog


ROUND_OPS = build_round_ops()


def prefix_ops(klevels):
    """ops up to the end of cascade level k (k in 0..4); k=0 = shadow +
    A(lin) + premix (before L1); matches explore_cascade_degree levels."""
    if klevels < 0 or klevels > 4:
        raise ValueError(klevels)
    # cascade level start indices within ROUND_OPS (SNAP markers)
    markers = [i for i, op in enumerate(ROUND_OPS) if op[0] == 'SNAP']
    # L1 gates are the 4 ANDs right after the first SNAP after A3s
    cut = [None] * 5
    # find 4 SNAP markers after the last A3
    a3 = max(i for i, op in enumerate(ROUND_OPS) if op[0] == 'A3')
    snaps = [i for i in markers if i > a3]
    for k in range(5):
        cut[k] = snaps[k] if k < len(snaps) else len(ROUND_OPS)
    # end of level k = one gate past the last AND of level k; levels are
    # separated by SNAPs at snaps[0..3]; level j gates live between
    # snaps[j] and the next snap; A2 linear ops between L2 and L3 count
    # inside the level stream as linear noise (harmless).  End of level k
    # = snaps[k] (start of level k+1) for k<4, else end of L4 = the Phase
    # D start (first X3 after last SNAP) -- use full list for k=4 minus
    # nothing (Phase D included) and for k<4 up to snaps[k].
    if klevels == 4:
        return ROUND_OPS
    return ROUND_OPS[: snaps[klevels]]


if __name__ == '__main__':
    import time
    W = int(sys.argv[1]) if len(sys.argv) > 1 else 4
    for k in range(5):
        t0 = time.time()
        tr = Tracker(W, [])          # fresh state per truncation level
        F = tr.run_round(prefix_ops(k))
        degs = tr.degrees(F)
        md = max(degs.values())
        from collections import Counter
        cnt = Counter(degs.values())
        top = {kk: v for kk, v in sorted(cnt.items())}
        print(f'W={W} k={k}: max degree = {md}, per-bit histogram {top} '
              f'({time.time()-t0:.1f}s)', flush=True)

#!/usr/bin/env python3
"""
Generate DIMACS CNF for GF(2)-only Tempest v3 round function.
Partial preimage: find state whose R-round output has u=all-1s, v=0.
Pure GF(2): XOR, AND, ROT only. No ADD.

Usage:
  python3 gen_tempest_cnf.py W R > tempest_W{W}_R{R}.cnf
  cadical tempest_W{W}_R{R}.cnf
"""
import sys

W = int(sys.argv[1]) if len(sys.argv) > 1 else 8
R = int(sys.argv[2]) if len(sys.argv) > 2 else 1

class CNF:
    def __init__(self):
        self.nv = 0
        self.clauses = []
    def new_var(self):
        self.nv += 1
        return self.nv
    def add(self, *lits):
        self.clauses.append(list(lits))
    def xor(self, a, b):
        """r = a xor b. Tseitin: 4 clauses."""
        r = self.new_var()
        self.add( a,  b, -r)  # a=1,b=1 => r=0
        self.add( a, -b,  r)  # a=1,b=0 => r=1
        self.add(-a,  b,  r)  # a=0,b=1 => r=1
        self.add(-a, -b, -r)  # a=0,b=0 => r=0
        return r
    def xor3(self, a, b, c):
        """r = a xor b xor c. Two cascaded XORs."""
        return self.xor(self.xor(a, b), c)
    def and_gate(self, a, b):
        """r = a and b. Tseitin: 3 clauses."""
        r = self.new_var()
        self.add( r, -a)
        self.add( r, -b)
        self.add( a,  b, -r)
        return r
    def print_dimacs(self, f):
        f.write(f"p cnf {self.nv} {len(self.clauses)}\n")
        for c in self.clauses:
            f.write(" ".join(str(l) for l in c) + " 0\n")

cnf = CNF()

# Input: 4 words of W bits each
u = [cnf.new_var() for _ in range(W)]
v = [cnf.new_var() for _ in range(W)]
w = [cnf.new_var() for _ in range(W)]
z = [cnf.new_var() for _ in range(W)]

def build_round(ui, vi, wi, zi):
    # Save snapshots
    u0, v0, w0, z0 = ui[:], vi[:], wi[:], zi[:]

    # === Phase B ===
    def phi_b(u, v, w, z):
        nu = [cnf.xor3(u[i], w[i], cnf.and_gate(v[(i+5)%W], z[(i+25)%W])) for i in range(W)]
        nv = [cnf.xor3(v[i], z[i], cnf.and_gate(w[(i+11)%W], u[(i+29)%W])) for i in range(W)]
        nw = [cnf.xor3(w[i], z[(i+23)%W], cnf.and_gate(u[(i+9)%W], v[(i+15)%W])) for i in range(W)]
        nz = [cnf.xor3(z[i], u[(i+17)%W], cnf.and_gate(v[(i+27)%W], w[(i+21)%W])) for i in range(W)]
        return nu, nv, nw, nz

    u, v, w, z = phi_b(u0, v0, w0, z0)

    # === Phase C ===
    def premix(t, r1, r2):
        """t_new = t ^ ROT(t,r1) ^ ROT(t,r2). Uses XOR tree."""
        return [cnf.xor3(t[i], t[(i+r1)%W], t[(i+r2)%W]) for i in range(W)]

    # Pre-mix 1: t ^= ROT(t,22) ^ ROT(t,26)
    u = premix(u, 22, 26); v = premix(v, 22, 26)
    w = premix(w, 22, 26); z = premix(z, 22, 26)

    def andmix4(words, r1, r2, pairs):
        """4-level AND-mix: each target = source ^ AND(ROT(a,r1), ROT(b,r2))."""
        a, b, c, d = words
        out = []
        for t_idx, a_idx, b_idx in pairs:
            src = words[t_idx]
            wa = words[a_idx]
            wb = words[b_idx]
            new = [cnf.xor(src[i], cnf.and_gate(wa[(i+r1)%W], wb[(i+r2)%W])) for i in range(W)]
            out.append(new)
        return out

    # Level 1: (v,w)(w,z)(z,u)(u,v) → u1,v1,w1,z1
    u, v, w, z = andmix4([u, v, w, z], 31, 53, [(0,1,2),(1,2,3),(2,3,0),(3,0,1)])

    # Pre-mix 2
    u = premix(u, 16, 14); v = premix(v, 16, 14)
    w = premix(w, 16, 14); z = premix(z, 16, 14)

    # Level 2
    u, v, w, z = andmix4([u, v, w, z], 17, 43, [(0,1,3),(1,2,0),(2,3,1),(3,0,2)])
    # Level 3
    u, v, w, z = andmix4([u, v, w, z], 7, 23, [(0,3,0),(1,0,1),(2,1,2),(3,2,3)])
    # Level 4 (same pairing as L1)
    u, v, w, z = andmix4([u, v, w, z], 5, 19, [(0,1,2),(1,2,3),(2,3,0),(3,0,1)])

    # === Phase D ===
    nu = [cnf.xor3(u[i], v[(i+3)%W], w[(i+9)%W]) for i in range(W)]
    nv = [cnf.xor3(v[i], w[(i+5)%W], z[(i+11)%W]) for i in range(W)]
    nw = [cnf.xor3(w[i], z[(i+9)%W], u[(i+13)%W]) for i in range(W)]
    nz = [cnf.xor3(z[i], u[(i+11)%W], v[(i+17)%W]) for i in range(W)]
    return nu, nv, nw, nz

for _ in range(R):
    u, v, w, z = build_round(u, v, w, z)

# Constraint: u = all-1s, v = 0
for i in range(W):
    cnf.add(u[i])    # u_i = 1
    cnf.add(-v[i])   # v_i = 0

cnf.print_dimacs(sys.stdout)

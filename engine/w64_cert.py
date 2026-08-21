#!/usr/bin/env python3
"""W=64 certificate via the closed-form rank formula  rank(B_d) = cols - merges.
Unit columns are determined by their output position (d_word, d_bit); two
gate-bits merge iff same output word and same output bit position mod W.
Exact min rank over all differences with t active bits (t=1,2,3): column
counting only, no GF(2) enumeration."""
import itertools
W = 64
G = {}
def add(w, d, rw, o, ro):
    G.setdefault(w, []).append((d, rw, o, ro))
# AND gates reading each state word, verbatim from the C ground truth
# (Phase A + A(lin)); word indices u=0,v=1,w=2,z=3.
# u-gate (rot(v,5)&rot(z,25)): reads v (r=5) and z (r=25), writes u
add(1, 0, 5,  3, 25)
add(3, 0, 25, 1, 5)
# v-gate (rot(w,11)&rot(u,29)): reads w (r=11) and u (r=29), writes v
add(2, 1, 11, 0, 29)
add(0, 1, 29, 2, 11)
# w-gate (rot(u,9)&rot(v,15)): reads u (r=9) and v (r=15), writes w
add(0, 2, 9,  1, 15)
add(1, 2, 15, 0, 9)
# z-gate (rot(v,27)&rot(w,21)): reads v (r=27) and w (r=21), writes z
add(1, 3, 27, 2, 21)
add(2, 3, 21, 1, 27)
# a2u (rot(z,23)&rot(w,53)): reads z (r=23) and w (r=53), writes u
add(3, 0, 23, 2, 53)
add(2, 0, 53, 1, 23)
# a2z (rot(u,5)&rot(z,25)): reads u (r=5) and z (r=25), writes z
add(0, 3, 5,  3, 25)
add(3, 3, 25, 0, 5)

def rank_for_active(word, bits):
    cols = []
    for (d, rw, o, ro) in G[word]:
        for p in bits:
            cols.append((d, (p + rw) % W))
    return len(cols) - (len(cols) - len(set(cols)))

def min_rank_t(t):
    best = 10**9
    for bits in itertools.combinations(range(4*W), t):
        r = 0
        for w in range(4):
            wbits = [p - w*W for p in bits if p // W == w]
            if wbits:
                r += rank_for_active(w, wbits)
        if r < best:
            best = r
    return best

print("W=64 closed-form rank certificate:")
for t in (1, 2, 3):
    print("  min rank over %d-bit differences: %d" % (t, min_rank_t(t)))
print("  per-word gate counts:", {w: len(G[w]) for w in G})

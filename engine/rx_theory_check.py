#!/usr/bin/env python3
"""W=4 verification of the three new theoretical results:
  T1 (RX rank theorem):  RX-DP(delta) == DP(rot^-1(delta)), any constants
  T2 (multi-bit merge):  rank(B_d) = k*t - M(d), M = aligned gate-pair merges
  T3 (second-order):     D_{a,b}F(x) == B(a,b), x-independent
"""
import random

W = 4
MASK = (1 << W) - 1
KU, KV, KW, KZ = 0x9, 0xA, 0x7, 0xC   # low W bits of the K constants

def rot(x, r):
    r %= W
    return ((x << r) | (x >> (W - r))) & MASK if r else x

def F(s):
    u, v, w, z = s
    au = u ^ rot(v,5) ^ rot(w,17) ^ (rot(v,5) & rot(z,25)) ^ KU
    av = v ^ rot(w,11) ^ rot(z,23) ^ (rot(w,11) & rot(u,29)) ^ KV
    aw = w ^ rot(z,13) ^ rot(u,31) ^ (rot(u,9) & rot(v,15)) ^ KW
    az = z ^ rot(u,17) ^ rot(v,7) ^ (rot(v,27) & rot(w,21)) ^ KZ
    au ^= (rot(z,23) & rot(w,53))   # A(lin)
    az ^= (rot(u,5) & rot(z,25))    # A(lin)
    return (au & MASK, av & MASK, aw & MASK, az & MASK)

def pack(s): return s[0] | (s[1]<<W) | (s[2]<<(2*W)) | (s[3]<<(3*W))
def unpack(x): return (x&MASK, (x>>W)&MASK, (x>>(2*W))&MASK, (x>>(3*W))&MASK)

FT = [pack(F(unpack(x))) for x in range(1 << (4*W))]   # full F table

def value_count(fx):   # number of DISTINCT values of a derived map over all x
    return len(set(fx))

def dp_values(d, mode):
    """collect value multiset; mode 'rx' or '1r'"""
    out = []
    if mode == 'rx':
        d4 = unpack(d)
        for x in range(1 << (4*W)):
            s = unpack(x)
            r = tuple(rot(a,1) for a in s)
            xi = pack(tuple(a ^ b for a,b in zip(r, d4)))
            out.append(FT[xi] ^ pack(tuple(rot(a,1) for a in unpack(FT[x]))))
    else:
        for x in range(1 << (4*W)):
            out.append(FT[x ^ d] ^ FT[x])
    return out

def maxfreq(vals):
    from collections import Counter
    return max(Counter(vals).values()) / len(vals)

rng = random.Random(11)

print("== T1: RX-DP(d) == DP(rot^-1(d)) ==")
bad = 0
for _ in range(60):
    d = rng.randrange(1, 1 << (4*W))
    dp = unpack(d)
    c = tuple(rot(a, W-1) for a in dp)          # rot^-1(d)
    ci = pack(c)
    rx = maxfreq(dp_values(d, 'rx'))
    one = maxfreq(dp_values(ci, '1r'))
    if rx != one:
        bad += 1
        print(f"  MISMATCH d={d:04x}: RX={rx} DP={one}")
print(f"identity: {60-bad}/60 exact")

print("== T3: second-order differential ==")
bad = 0
for _ in range(200):
    a = rng.randrange(1, 1 << (4*W)); b = rng.randrange(0, 1 << (4*W))
    ref = None
    for _ in range(6):
        x = rng.randrange(0, 1 << (4*W))
        y = FT[x] ^ FT[x^a] ^ FT[x^b] ^ FT[x^a^b]
        if ref is None: ref = y
        elif ref != y: bad += 1; break
print(f"second-order diff x-independent: {200-bad}/200")

print("== T2: multi-bit merge formula ==")
# gates reading word z (output word d, w-rot r_w, other word o, other-rot r_o),
# modulo W: (d, r_w mod W, o, r_o mod W)
# gates whose AND reads word z (k=3, matches the paper's barrier count):
#   u gate  (rot(v,5)  & rot(z,25)) -> d=u, r_w=25, o=v, r_o=5
#   a2u     (rot(z,23) & rot(w,53)) -> d=u, r_w=23, o=w, r_o=53
#   a2z     (rot(u,5)  & rot(z,25)) -> d=z, r_w=25, o=u, r_o=5
# (the v-gate's rot(z,23) is an XOR term, not an AND operand)
z_gates = [(0, 25 % W, 1, 5 % W), (0, 23 % W, 2, 53 % W), (3, 25 % W, 0, 5 % W)]
k = len(z_gates)

def merges(dbits):
    """M(d): gate pairs (i,j) with d_i=d_j, o_i=o_j, r_o_i=r_o_j and
       aligned active bits p_i + r_w_i == p_j + r_w_j (mod W) -> the two
       unit columns coincide (identical input variable and output bit).
       Unit columns are linearly independent iff all distinct, so
       rank = k*t - M exactly."""
    M = 0
    for i in range(k):
        for j in range(i+1, k):
            di, rwi, oi, roi = z_gates[i]
            dj, rwj, oj, roj = z_gates[j]
            if di != dj: continue
            for pi in dbits:
                for pj in dbits:
                    if (pi + rwi) % W == (pj + rwj) % W:
                        M += 1
    return M

bad = 0; total = 0
for t in range(1, 5):   # t active bits in z word
    for dbits in __import__('itertools').combinations(range(W), t):
        # delta with active bits at z-word positions dbits
        d = 0
        for p in dbits: d |= 1 << (p + 3*W)
        # rank of B_d from value count of D_d (D is invertible linear, rank preserved)
        vc = value_count(dp_values(d, '1r'))
        rank = vc.bit_length() - 1   # vc is a power of two for affine maps
        pred = k * t - merges(dbits)
        total += 1
        if rank != pred:
            bad += 1
            if bad <= 5: print(f"  rank(B)={rank} pred={pred} bits={dbits} M={merges(dbits)}")
print(f"multi-bit formula rank = k*t - M: {total-bad}/{total} (k={k})")

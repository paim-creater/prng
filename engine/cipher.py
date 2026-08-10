"""cipher.py — Core of the upgraded AI design engine.

A generic round-function DSL (word-level ops) with a numpy-vectorized
interpreter, plus bit-exact Python ports of Tempest v3 (Algorithm 1, from
github_release/src/tempest_v3.c) and Tempest v3.1 (submission/code/tempest_v3.c).

Verifiers (neural distinguisher, empirical DP/linear, fast stats, exact trail
simulation) all consume designs expressed in this DSL, so the engine can
generate *and* verify arbitrary AND-RX-style round functions.

Op vocabulary (kind, ...):
    ('SNAP',)                       copy current state into snapshot registers
    ('X3',  dst, a, b, ra, rb, snap)  dst ^= rot(a,ra) ^ rot(b,rb)
    ('X4',  dst, a, b, c, ra, rb, rc, snap)  dst ^= rot(a,ra) ^ rot(b,rb) ^ rot(c,rc)
    ('X4A', dst, a, b, c, ra, rb, rc, snap)  dst  = rot(a,ra) ^ rot(b,rb) ^ rot(c,rc)  (assign)
    ('AND', dst, a, b, ra, rb, snap)  dst ^= rot(a,ra) & rot(b,rb)
    ('A2',  dst, r1, r2)              dst ^= rot(dst,r1) ^ rot(dst,r2)
    ('A3',  dst, r1, r2, r3, r4)      dst ^= rot(dst,r1)^rot(dst,r2)^(rot(dst,r3)&rot(dst,r4))
    ('KEY', dst, r, s)                dst ^= rot(wv_nl,r) ^ (wv_nl >> s)  (filtered weyl)
    ('WEYL', r, c)                    wv  ^= rot(wv,r) ^ c            (GF(2) affine)
    ('WEYLADD', c)                    wv  = (wv + c) & mask           (integer carry)
    ('NLFILT', c)                     wv_nl = wv ^ rot(wv & c, 13)    (nonlinear filter)
    ('MIX', dst, a, b, ra, rb)        dst ^= rot(a,ra) ^ rot(b,rb)   (sequential, current)
    ('CONST', dst, c)                 dst ^= c
dst/a/b are 'u','v','w','z'; snap ∈ {0,1}.
"""
import numpy as np

U64 = np.uint64
MASK = np.uint64(0xFFFFFFFFFFFFFFFF)

GOLDEN = U64(0x9E3779B97F4A7C15)
K_U = U64(0x9E3779B97F4A7C15)
K_V = U64(0x3C6EF372FE94F82A)
K_W = U64(0x5A8279998F1BBD27)
K_Z = U64(0x6ED9EBA1F97F3B4C)


def rotl(x, r, W=64):
    """Rotate left by r (numpy uint64 array or python int)."""
    r %= W
    if isinstance(x, np.ndarray):
        return (np.left_shift(x, r) | np.right_shift(x, W - r)) & (MASK if W == 64 else U64((1 << W) - 1))
    if W == 64:
        return ((x << r) | (x >> (W - r))) & MASK
    return ((x << r) | (x >> (W - r))) & ((1 << W) - 1)


def popcount(x):
    """Popcount of uint64 (scalar or array)."""
    if isinstance(x, np.ndarray):
        x = x.astype(np.uint64)
        x = x - ((x >> 1) & U64(0x5555555555555555))
        x = (x & U64(0x3333333333333333)) + ((x >> 2) & U64(0x3333333333333333))
        x = (x + (x >> 4)) & U64(0x0F0F0F0F0F0F0F0F)
        return (x * U64(0x0101010101010101)) >> 56
    n = 0
    while x:
        x &= x - 1
        n += 1
    return n


def splitmix64(seed):
    """SplitMix64 PRNG — used to fill states from a seed (test tooling only)."""
    seed &= MASK
    while True:
        seed = (seed + U64(0x9E3779B97F4A7C15)) & MASK
        z = seed
        z = (z ^ (z >> 30)) * U64(0xBF58476D1CE4E5B9) & MASK
        z = (z ^ (z >> 27)) * U64(0x94D049BB133111EB) & MASK
        yield (z ^ (z >> 31)) & MASK


# ==============================================================================
# Tempest v3 Algorithm 1 (github_release/src/tempest_v3.c) — round program
# ==============================================================================
def tempest_a1_round_program():
    """Round-function op list for Algorithm 1 (paper Algorithm 1)."""
    ops = [
        # implicit round-start snapshot taken by verifier; emit explicit SNAP:
        ('SNAP',),
        # Phase A: GF(2) nonlinear diffusion from round-start snapshot
        ('X3', 'u', 'v', 'w', 5, 17, 1),
        ('AND', 'u', 'v', 'z', 5, 25, 1),
        ('CONST', 'u', K_U),
        ('X3', 'v', 'w', 'z', 11, 23, 1),
        ('AND', 'v', 'w', 'u', 11, 29, 1),
        ('CONST', 'v', K_V),
        ('X3', 'w', 'z', 'u', 13, 31, 1),
        ('AND', 'w', 'u', 'v', 9, 15, 1),
        ('CONST', 'w', K_W),
        ('X3', 'z', 'u', 'v', 17, 7, 1),
        ('AND', 'z', 'v', 'w', 27, 21, 1),
        ('CONST', 'z', K_Z),
        # Phase A(lin): snapshot ANDs covering (u,z) and (w,z)
        ('AND', 'u', 'z', 'w', 23, 53, 1),
        ('AND', 'z', 'u', 'z', 5, 25, 1),
        # Phase B: GF(2) round key + nonlinear filter
        ('WEYL', 19, GOLDEN),
        ('NLFILT', GOLDEN),
        ('KEY', 'u', 7, 17),
        ('KEY', 'v', 19, 23),
        ('KEY', 'w', 31, 29),
        ('KEY', 'z', 43, 37),
        # Phase C: pre-mix 1 (22,26) + intra-word AND (7,19)
        ('A3', 'u', 22, 26, 7, 19),
        ('A3', 'v', 22, 26, 7, 19),
        ('A3', 'w', 22, 26, 7, 19),
        ('A3', 'z', 22, 26, 7, 19),
        # Level 1
        ('SNAP',),
        ('AND', 'u', 'v', 'w', 31, 53, 1),
        ('AND', 'v', 'w', 'z', 17, 43, 1),
        ('AND', 'w', 'z', 'u', 7, 23, 1),
        ('AND', 'z', 'u', 'v', 5, 19, 1),
        # Level 2
        ('SNAP',),
        ('AND', 'u', 'v', 'z', 17, 43, 1),
        ('AND', 'v', 'w', 'u', 7, 23, 1),
        ('AND', 'w', 'z', 'v', 5, 19, 1),
        ('AND', 'z', 'u', 'w', 31, 53, 1),
        # pre-mix 2 (16,14)
        ('A2', 'u', 16, 14),
        ('A2', 'v', 16, 14),
        ('A2', 'w', 16, 14),
        ('A2', 'z', 16, 14),
        # Level 3
        ('SNAP',),
        ('AND', 'u', 'z', 'u', 7, 23, 1),
        ('AND', 'v', 'u', 'v', 5, 19, 1),
        ('AND', 'w', 'v', 'w', 31, 53, 1),
        ('AND', 'z', 'w', 'z', 17, 43, 1),
        # Level 4
        ('SNAP',),
        ('AND', 'u', 'v', 'w', 5, 19, 1),
        ('AND', 'v', 'w', 'z', 31, 53, 1),
        ('AND', 'w', 'z', 'u', 17, 53, 1),
        ('AND', 'z', 'u', 'v', 7, 23, 1),
        # Phase D: cross-word mixing — C assigns all four from pre-Phase-D
        # values simultaneously, so read from a snapshot
        ('SNAP',),
        ('X3', 'u', 'v', 'w', 3, 9, 1),
        ('X3', 'v', 'w', 'z', 5, 11, 1),
        ('X3', 'w', 'z', 'u', 9, 13, 1),
        ('X3', 'z', 'u', 'v', 11, 17, 1),
    ]
    return ops


# ==============================================================================
# Tempest v3.1 (submission/code/tempest_v3.c) — round program (has lagged-sum
# weakness per its own Dieharder logs; used as calibration bad-control)
# ==============================================================================
def tempest_v31_round_program():
    """v3.1 (submission/code/tempest_v3.c) — integer-ADD Weyl + 4-source
    XOR-ROT + premix(22,26) + intra-word andmix4 + Phase D.
    Note: v3.1's own KAT header is stale (audit finding); ground truth is
    the compiled C: A70916F449FAE0E8...
    """
    ops = [
        ('SNAP',),  # C captures u0..z0 at function start, BEFORE Phase A
        ('WEYLADD', GOLDEN),
        ('KEY', 'u', 7, 17),
        ('KEY', 'v', 19, 23),
        ('KEY', 'w', 31, 29),
        ('KEY', 'z', 43, 37),
        ('X4A', 'u', 'v', 'w', 'z', 5, 13, 25, 1),
        ('X4A', 'v', 'w', 'z', 'u', 11, 19, 29, 1),
        ('X4A', 'w', 'z', 'u', 'v', 23, 9, 15, 1),
        ('X4A', 'z', 'u', 'v', 'w', 17, 27, 21, 1),
        # Phase C: premix (22,26) + intra-word andmix4, one word at a time
        ('A2', 'u', 22, 26),
        ('SNAP',),
        ('AND', 'u', 'u', 'u', 31, 53, 0),
        ('AND', 'u', 'u', 'u', 17, 43, 0),
        ('AND', 'u', 'u', 'u', 7, 23, 0),
        ('AND', 'u', 'u', 'u', 5, 19, 0),
        ('A2', 'v', 22, 26),
        ('SNAP',),
        ('AND', 'v', 'v', 'v', 31, 53, 0),
        ('AND', 'v', 'v', 'v', 17, 43, 0),
        ('AND', 'v', 'v', 'v', 7, 23, 0),
        ('AND', 'v', 'v', 'v', 5, 19, 0),
        ('A2', 'w', 22, 26),
        ('SNAP',),
        ('AND', 'w', 'w', 'w', 31, 53, 0),
        ('AND', 'w', 'w', 'w', 17, 43, 0),
        ('AND', 'w', 'w', 'w', 7, 23, 0),
        ('AND', 'w', 'w', 'w', 5, 19, 0),
        ('A2', 'z', 22, 26),
        ('SNAP',),
        ('AND', 'z', 'z', 'z', 31, 53, 0),
        ('AND', 'z', 'z', 'z', 17, 43, 0),
        ('AND', 'z', 'z', 'z', 7, 23, 0),
        ('AND', 'z', 'z', 'z', 5, 19, 0),
        # Phase D — simultaneous assignment, read from snapshot
        ('SNAP',),
        ('X3', 'u', 'v', 'w', 3, 9, 1),
        ('X3', 'v', 'w', 'z', 5, 11, 1),
        ('X3', 'w', 'z', 'u', 9, 13, 1),
        ('X3', 'z', 'u', 'v', 11, 17, 1),
    ]
    return ops


# ==============================================================================
# Vectorized interpreter
# ==============================================================================
_IDX = {'u': 0, 'v': 1, 'w': 2, 'z': 3}


class State:
    """Vectorized state: (4W words + weyl), shape (N,) uint64 arrays."""

    __slots__ = ('words', 'wv', 'wv_nl', 'W')

    def __init__(self, words, wv, W=64):
        self.words = [np.asarray(w, dtype=U64) for w in words]
        self.wv = np.asarray(wv, dtype=U64)
        self.wv_nl = self.wv  # unfiltered until NLFILT runs
        self.W = W

    @classmethod
    def random(cls, n, seed=0, W=64):
        rng = np.random.default_rng(seed)
        words = [rng.integers(0, 1 << W, size=n, dtype=U64) for _ in range(4)]
        wv = rng.integers(0, 1 << W, size=n, dtype=U64)
        return cls(words, wv, W)

    def copy(self):
        return State([w.copy() for w in self.words], self.wv.copy(), self.W)

    def get(self, name):
        return self.words[_IDX[name]]

    def set(self, name, val):
        self.words[_IDX[name]] = val


def apply_round(ops, st, consts=None):
    """Apply one round program to a State in place (vectorized)."""
    W = st.W
    mask = U64((1 << W) - 1) if W != 64 else MASK
    snap = None
    for op in ops:
        k = op[0]
        if k == 'SNAP':
            snap = [w.copy() for w in st.words]
            continue
        if k == 'CONST':
            dst = op[1]
            st.set(dst, (st.get(dst) ^ U64(op[2] & ((1 << W) - 1))) & mask)
            continue
        if k == 'WEYL':
            r, c = op[1], U64(op[2] & ((1 << W) - 1))
            wv = st.wv
            st.wv = (wv ^ rotl(wv, r, W) ^ c) & mask
            st.wv_nl = st.wv  # unfiltered until NLFILT runs
            continue
        if k == 'WEYLADD':
            c = U64(op[1] & ((1 << W) - 1))
            st.wv = (st.wv + c) & mask
            st.wv_nl = st.wv
            continue
        if k == 'KEY':
            dst, r, s = op[1], op[2], op[3]
            wv = getattr(st, 'wv_nl', st.wv)
            val = (np.left_shift(wv, r % W) | np.right_shift(wv, W - r % W)) & mask
            val = (val ^ np.right_shift(wv, s)) & mask
            st.set(dst, (st.get(dst) ^ val) & mask)
            continue
        if k == 'NLFILT':
            c = U64(op[1] & ((1 << W) - 1))
            st.wv_nl = (st.wv ^ rotl(st.wv & c, 13, W)) & mask
            continue
        if k == 'A2':
            dst, r1, r2 = op[1], op[2], op[3]
            x = st.get(dst)
            st.set(dst, (x ^ rotl(x, r1, W) ^ rotl(x, r2, W)) & mask)
            continue
        if k == 'A3':
            dst, r1, r2, r3, r4 = op[1], op[2], op[3], op[4], op[5]
            x = st.get(dst)
            st.set(dst, (x ^ rotl(x, r1, W) ^ rotl(x, r2, W) ^
                         (rotl(x, r3, W) & rotl(x, r4, W))) & mask)
            continue
        if k in ('X4', 'X4A'):
            dst, a4, b4, c4 = op[1], op[2], op[3], op[4]
            ra4, rb4, rc4, snap4 = op[5], op[6], op[7], op[8]
            if snap4:
                av4 = rotl(snap[_IDX[a4]], ra4, W)
                bv4 = rotl(snap[_IDX[b4]], rb4, W)
                cv4 = rotl(snap[_IDX[c4]], rc4, W)
            else:
                av4 = rotl(st.get(a4), ra4, W)
                bv4 = rotl(st.get(b4), rb4, W)
                cv4 = rotl(st.get(c4), rc4, W)
            val = av4 ^ bv4 ^ cv4
            if k == 'X4A':
                # C: dst = src(dst) ^ rot(a) ^ rot(b) ^ rot(c); the dst term
                # also comes from the snapshot (e.g. v3.1 Phase B u = u0 ^ ...)
                base = snap[_IDX[dst]] if snap4 else st.get(dst)
                st.set(dst, (base ^ val) & mask)
            else:
                st.set(dst, (st.get(dst) ^ val) & mask)
            continue
        dst, a, b, ra, rb, sflag = op[1], op[2], op[3], op[4], op[5], op[6]
        if sflag:
            av = rotl(snap[_IDX[a]], ra, W)
            bv = rotl(snap[_IDX[b]], rb, W)
        else:
            av = rotl(st.get(a), ra, W)
            bv = rotl(st.get(b), rb, W)
        if k == 'X3':
            st.set(dst, (st.get(dst) ^ av ^ bv) & mask)
        elif k == 'AND':
            st.set(dst, (st.get(dst) ^ (av & bv)) & mask)
        elif k == 'MIX':
            st.set(dst, (st.get(dst) ^ av ^ bv) & mask)
        else:
            raise ValueError(f'unknown op {k}')
    return st


def make_output_a1(u, v, w, z, W=64):
    """Algorithm 1 output function."""
    mask = U64((1 << W) - 1) if W != 64 else MASK
    t = (u ^ rotl(v, 32, W) ^ w ^ rotl(z, 16, W)) & mask
    t = (t ^ rotl(t, 22, W) ^ rotl(t, 26, W)) & mask
    t = (t ^ rotl(t, 16, W) ^ rotl(t, 14, W)) & mask
    for (r1, r2) in [(31, 53), (17, 43), (7, 23), (5, 19)]:
        t = (t ^ (rotl(t, r1, W) & rotl(t, r2, W))) & mask
    t = (t ^ (t >> 32)) & mask
    return t


def make_output_v31(u, v, w, z, W=64):
    mask = U64((1 << W) - 1) if W != 64 else MASK
    t = (u ^ rotl(v, 32, W) ^ w ^ rotl(z, 16, W)) & mask
    t = (t ^ rotl(t, 27, W) ^ rotl(t, 17, W)) & mask
    for (r1, r2) in [(31, 53), (17, 43), (7, 23), (5, 19)]:
        t = (t ^ (rotl(t, r1, W) & rotl(t, r2, W))) & mask
    t = (t ^ (t >> 32)) & mask
    return t


# ==============================================================================
# Scalar exact ports (for KAT verification against C)
# ==============================================================================
def _rotl_s(x, r, W=64):
    r %= W
    x &= (1 << W) - 1
    return ((x << r) | (x >> (W - r))) & ((1 << W) - 1)


def a1_round_scalar(s):
    """Scalar round for Algorithm 1; s = dict(u,v,w,z,weyl,r)."""
    W = 64
    M = (1 << 64) - 1
    u, v, w, z = s['u'], s['v'], s['w'], s['z']
    u0, v0, w0, z0 = u, v, w, z
    u = (u0 ^ _rotl_s(v0, 5) ^ _rotl_s(w0, 17) ^ (_rotl_s(v0, 5) & _rotl_s(z0, 25)) ^ (K_U & M)) & M
    v = (v0 ^ _rotl_s(w0, 11) ^ _rotl_s(z0, 23) ^ (_rotl_s(w0, 11) & _rotl_s(u0, 29)) ^ (K_V & M)) & M
    w = (w0 ^ _rotl_s(z0, 13) ^ _rotl_s(u0, 31) ^ (_rotl_s(u0, 9) & _rotl_s(v0, 15)) ^ (K_W & M)) & M
    z = (z0 ^ _rotl_s(u0, 17) ^ _rotl_s(v0, 7) ^ (_rotl_s(v0, 27) & _rotl_s(w0, 21)) ^ (K_Z & M)) & M
    u ^= (_rotl_s(z0, 23) & _rotl_s(w0, 53))
    z ^= (_rotl_s(u0, 5) & _rotl_s(z0, 25))
    wv = s['weyl']
    wv = (wv ^ _rotl_s(wv, 19) ^ (GOLDEN & M)) & M
    wv_nl = (wv ^ _rotl_s(wv & (GOLDEN & M), 13)) & M
    u ^= _rotl_s(wv_nl, 7) ^ (wv_nl >> 17)
    v ^= _rotl_s(wv_nl, 19) ^ (wv_nl >> 23)
    w ^= _rotl_s(wv_nl, 31) ^ (wv_nl >> 29)
    z ^= _rotl_s(wv_nl, 43) ^ (wv_nl >> 37)
    s['weyl'] = wv
    # Phase C premix
    u ^= _rotl_s(u, 22) ^ _rotl_s(u, 26) ^ (_rotl_s(u, 7) & _rotl_s(u, 19))
    v ^= _rotl_s(v, 22) ^ _rotl_s(v, 26) ^ (_rotl_s(v, 7) & _rotl_s(v, 19))
    w ^= _rotl_s(w, 22) ^ _rotl_s(w, 26) ^ (_rotl_s(w, 7) & _rotl_s(w, 19))
    z ^= _rotl_s(z, 22) ^ _rotl_s(z, 26) ^ (_rotl_s(z, 7) & _rotl_s(z, 19))
    # Level 1
    u1 = (u ^ (_rotl_s(v, 31) & _rotl_s(w, 53))) & M
    v1 = (v ^ (_rotl_s(w, 17) & _rotl_s(z, 43))) & M
    w1 = (w ^ (_rotl_s(z, 7) & _rotl_s(u, 23))) & M
    z1 = (z ^ (_rotl_s(u, 5) & _rotl_s(v, 19))) & M
    # Level 2
    u2 = (u1 ^ (_rotl_s(v1, 17) & _rotl_s(z1, 43))) & M
    v2 = (v1 ^ (_rotl_s(w1, 7) & _rotl_s(u1, 23))) & M
    w2 = (w1 ^ (_rotl_s(z1, 5) & _rotl_s(v1, 19))) & M
    z2 = (z1 ^ (_rotl_s(u1, 31) & _rotl_s(w1, 53))) & M
    # premix 2
    u2 ^= _rotl_s(u2, 16) ^ _rotl_s(u2, 14)
    v2 ^= _rotl_s(v2, 16) ^ _rotl_s(v2, 14)
    w2 ^= _rotl_s(w2, 16) ^ _rotl_s(w2, 14)
    z2 ^= _rotl_s(z2, 16) ^ _rotl_s(z2, 14)
    # Level 3
    u3 = (u2 ^ (_rotl_s(z2, 7) & _rotl_s(u2, 23))) & M
    v3 = (v2 ^ (_rotl_s(u2, 5) & _rotl_s(v2, 19))) & M
    w3 = (w2 ^ (_rotl_s(v2, 31) & _rotl_s(w2, 53))) & M
    z3 = (z2 ^ (_rotl_s(w2, 17) & _rotl_s(z2, 43))) & M
    # Level 4
    uc = (u3 ^ (_rotl_s(v3, 5) & _rotl_s(w3, 19))) & M
    vc = (v3 ^ (_rotl_s(w3, 31) & _rotl_s(z3, 53))) & M
    wc = (w3 ^ (_rotl_s(z3, 17) & _rotl_s(u3, 53))) & M
    zc = (z3 ^ (_rotl_s(u3, 7) & _rotl_s(v3, 23))) & M
    # Phase D
    u = (uc ^ _rotl_s(vc, 3) ^ _rotl_s(wc, 9)) & M
    v = (vc ^ _rotl_s(wc, 5) ^ _rotl_s(zc, 11)) & M
    w = (wc ^ _rotl_s(zc, 9) ^ _rotl_s(uc, 13)) & M
    z = (zc ^ _rotl_s(uc, 11) ^ _rotl_s(vc, 17)) & M
    s['u'], s['v'], s['w'], s['z'] = u, v, w, z
    s['r'] = s.get('r', 0) + 1
    return s


def a1_output_scalar(u, v, w, z):
    M = (1 << 64) - 1
    t = (u ^ _rotl_s(v, 32) ^ w ^ _rotl_s(z, 16)) & M
    t ^= _rotl_s(t, 22) ^ _rotl_s(t, 26)
    t ^= _rotl_s(t, 16) ^ _rotl_s(t, 14)
    for (r1, r2) in [(31, 53), (17, 43), (7, 23), (5, 19)]:
        t ^= _rotl_s(t, r1) & _rotl_s(t, r2)
    t ^= t >> 32
    return t & M


def a1_init(key, nonce):
    """Port of tempest_init (Algorithm 1). key: list[4], nonce: list[2]."""
    M = (1 << 64) - 1
    G = GOLDEN & M
    k0, k1, k2, k3 = [x & M for x in key]
    n0, n1 = [x & M for x in nonce]
    s = {'u': k0, 'v': (k1 ^ n0) & M, 'w': (k2 ^ n1) & M,
         'z': (k3 ^ 0x54454D5035583543) & M, 'r': 0, 'weyl': 0x6A09E667F3BCC908}
    kw = 0x6A09E667F3BCC908
    for i in range(16):
        a1_round_scalar(s)
        kw = (kw ^ _rotl_s(kw, 19) ^ G) & M
        if i < 8:
            if i & 1:
                s['u'] ^= _rotl_s(k0, i + 1) ^ kw
                s['v'] ^= _rotl_s(k1, i + 1) ^ ((kw << 17) & M)
                s['w'] ^= _rotl_s(k2, i + 1) ^ (kw >> 13)
                s['z'] ^= _rotl_s(k3, i + 1) ^ _rotl_s(kw, 31)
            else:
                s['u'] ^= k0 ^ kw
                s['v'] ^= k1 ^ ((kw << 17) & M)
                s['w'] ^= k2 ^ (kw >> 13)
                s['z'] ^= k3 ^ _rotl_s(kw, 31)
        else:
            # C: n0=nonce[i&1], n1=nonce[1-(i&1)]; u^=n0; v^=rotl(n1,19)^i; z^=rotl(n0,43)
            nn0, nn1 = (n1, n0) if i & 1 else (n0, n1)   # nn0=nonce[i&1], nn1=nonce[1-(i&1)]
            s['u'] ^= nn0
            s['v'] ^= _rotl_s(nn1, 19) ^ i
            s['z'] ^= _rotl_s(nn0, 43)
    for _ in range(6):
        a1_round_scalar(s)
    s['u'] ^= k0
    s['v'] ^= k1
    s['w'] ^= k2
    s['z'] ^= k3
    return s


def a1_stream(key, nonce, count):
    """Scalar stream (Algorithm 1), returns list of count uint64 outputs."""
    s = a1_init(key, nonce)
    out = []
    for _ in range(count):
        a1_round_scalar(s)
        out.append(a1_output_scalar(s['u'], s['v'], s['w'], s['z']))
    return out


# v3.1 scalar port (for stats parity checks)
def v31_round_scalar(s):
    M = (1 << 64) - 1
    u, v, w, z = s['u'], s['v'], s['w'], s['z']
    u0, v0, w0, z0 = u, v, w, z
    wv = (s['weyl'] + (GOLDEN & M)) & M
    u ^= _rotl_s(wv, 7) ^ (wv >> 17)
    v ^= _rotl_s(wv, 19) ^ (wv >> 23)
    w ^= _rotl_s(wv, 31) ^ (wv >> 29)
    z ^= _rotl_s(wv, 43) ^ (wv >> 37)
    s['weyl'] = wv
    u = (u0 ^ _rotl_s(v0, 5) ^ _rotl_s(w0, 13) ^ _rotl_s(z0, 25)) & M
    v = (v0 ^ _rotl_s(w0, 11) ^ _rotl_s(z0, 19) ^ _rotl_s(u0, 29)) & M
    w = (w0 ^ _rotl_s(z0, 23) ^ _rotl_s(u0, 9) ^ _rotl_s(v0, 15)) & M
    z = (z0 ^ _rotl_s(u0, 17) ^ _rotl_s(v0, 27) ^ _rotl_s(w0, 21)) & M
    for name in 'uvwz':
        x = {'u': u, 'v': v, 'w': w, 'z': z}[name]
        x ^= _rotl_s(x, 22) ^ _rotl_s(x, 26)
        # andmix4 is SEQUENTIAL in C (each level reads the updated value)
        for r1, r2 in ((31, 53), (17, 43), (7, 23), (5, 19)):
            x ^= _rotl_s(x, r1) & _rotl_s(x, r2)
        x &= M
        if name == 'u': u = x
        elif name == 'v': v = x
        elif name == 'w': w = x
        else: z = x
    # Phase D: C assigns all four simultaneously from pre-Phase-D values
    u2c, v2c, w2c, z2c = u, v, w, z
    u = (u2c ^ _rotl_s(v2c, 3) ^ _rotl_s(w2c, 9)) & M
    v = (v2c ^ _rotl_s(w2c, 5) ^ _rotl_s(z2c, 11)) & M
    w = (w2c ^ _rotl_s(z2c, 9) ^ _rotl_s(u2c, 13)) & M
    z = (z2c ^ _rotl_s(u2c, 11) ^ _rotl_s(v2c, 17)) & M
    s['u'], s['v'], s['w'], s['z'] = u, v, w, z
    s['r'] = s.get('r', 0) + 1
    return s


def v31_output_scalar(u, v, w, z):
    M = (1 << 64) - 1
    t = (u ^ _rotl_s(v, 32) ^ w ^ _rotl_s(z, 16)) & M
    t ^= _rotl_s(t, 27) ^ _rotl_s(t, 17)
    for (r1, r2) in [(31, 53), (17, 43), (7, 23), (5, 19)]:
        t ^= _rotl_s(t, r1) & _rotl_s(t, r2)
    t ^= t >> 32
    return t & M


def v31_init(key, nonce):
    M = (1 << 64) - 1
    G = GOLDEN & M
    k0, k1, k2, k3 = [x & M for x in key]
    n0, n1 = [x & M for x in nonce]
    s = {'u': k0, 'v': (k1 ^ n0) & M, 'w': (k2 ^ n1) & M,
         'z': (k3 ^ 0x54454D5035583543) & M, 'r': 0, 'weyl': 0x6A09E667F3BCC908}
    kw = 0x6A09E667F3BCC908
    for i in range(16):
        v31_round_scalar(s)
        kw = (kw + G) & M
        if i < 8:
            if i & 1:
                s['u'] ^= _rotl_s(k0, i + 1) ^ kw
                s['v'] ^= _rotl_s(k1, i + 1) ^ ((kw << 17) & M)
                s['w'] ^= _rotl_s(k2, i + 1) ^ (kw >> 13)
                s['z'] ^= _rotl_s(k3, i + 1) ^ _rotl_s(kw, 31)
            else:
                s['u'] ^= k0 ^ kw
                s['v'] ^= k1 ^ ((kw << 17) & M)
                s['w'] ^= k2 ^ (kw >> 13)
                s['z'] ^= k3 ^ _rotl_s(kw, 31)
        else:
            nn0, nn1 = (n1, n0) if i & 1 else (n0, n1)
            s['u'] ^= nn0
            s['v'] ^= _rotl_s(nn1, 19) ^ i
            s['z'] ^= _rotl_s(nn0, 43)
    for _ in range(6):
        v31_round_scalar(s)
    s['u'] ^= k0
    s['v'] ^= k1
    s['w'] ^= k2
    s['z'] ^= k3
    return s


def v31_stream(key, nonce, count):
    s = v31_init(key, nonce)
    out = []
    for _ in range(count):
        v31_round_scalar(s)
        out.append(v31_output_scalar(s['u'], s['v'], s['w'], s['z']))
    return out


def kat_check():
    """Verify scalar ports against the C KAT vectors."""
    key, nonce = [1, 2, 3, 4], [5, 6]
    exp_a1 = [0x6BBE30BB1D12DDD0, 0xB9167FE6CCEC68D9, 0xCF6F7BA5C6AED360,
              0xA53C77D6D081BEC3, 0x7F5A13D9CBF1CD84, 0x7B642126FA3B4609,
              0x6AE3C72B55FF5B19, 0xB2CDDDB1B2B9DDA1, 0xD71A44CD824527D2,
              0x9AF63FB79C533F3E]
    exp_v31 = [0xE6A63B6698420248, 0xE7ECEB835804E29F, 0xA6F0CB54537E9263,
               0xB14F33236ECBCF90, 0xF71DEECD0ECB13F8, 0x702B3A7B26DCE0F8,
               0xB4789B25CC4A035A, 0x26993EFC00E3B44B, 0xB62F6DCF5B82CA73,
               0xFAAD1CD4D6499554]
    got_a1 = a1_stream(key, nonce, 10)
    got_v31 = v31_stream(key, nonce, 10)
    a1_ok = all(a == b for a, b in zip(got_a1, exp_a1))
    # v3.1 ground truth = compiled C output (its stale header disagrees with the code)
    exp_v31_c = [0xA70916F449FAE0E8, 0xDAEA84EEA4396C35, 0x73EB324BDF7973BB,
                 0x96310993259CAE06, 0x2F6E873207B7086B, 0x757F35551B08C2E8,
                 0x1ACE0A7794CEF0EF, 0x7367841D6D51F2F5, 0xEF1C5A3A58736E3B,
                 0x26053B1393F3C247]
    v31_ok = all(a == b for a, b in zip(got_v31, exp_v31_c))
    print(f'KAT Algorithm-1: {"PASS" if a1_ok else "FAIL"}')
    if not a1_ok:
        print('  expected:', [hex(x) for x in exp_a1])
        print('  got     :', [hex(x) for x in got_a1])
    print(f'KAT v3.1 (vs compiled C truth): {"PASS" if v31_ok else "FAIL"}')
    if not v31_ok:
        print('  expected:', [hex(x) for x in exp_v31_c])
        print('  got     :', [hex(x) for x in got_v31])
    # Cross-check: DSL ops-program interpreter vs scalar ports on random states
    import numpy as np
    rng = np.random.default_rng(7)
    interp_ok = True
    for label, prog, scalar_round, scalar_out in [
            ('Algorithm-1', tempest_a1_round_program(), a1_round_scalar, a1_output_scalar),
            ('v3.1', tempest_v31_round_program(), v31_round_scalar, v31_output_scalar)]:
        st = State.random(1, seed=3)
        words = [int(st.words[i][0]) for i in range(4)]
        wv0 = int(st.wv[0])
        scalar = {'u': words[0], 'v': words[1], 'w': words[2], 'z': words[3],
                  'weyl': wv0, 'r': 0}
        apply_round(prog, st)
        scalar_round(scalar)
        ok = all(int(st.words[i][0]) == scalar[n] for i, n in enumerate('uvwz'))
        ok = ok and int(st.wv[0]) == scalar['weyl']
        interp_ok = interp_ok and ok
        print(f'interpreter vs scalar ({label}): {"PASS" if ok else "FAIL"}')
    return a1_ok and interp_ok, v31_ok


if __name__ == '__main__':
    kat_check()

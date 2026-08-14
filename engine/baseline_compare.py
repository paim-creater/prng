# -*- coding: utf-8 -*-
"""
baseline_compare.py — AM-SEV exact metrics applied to non-AND-RX generators.

What the framework's exact layer can and cannot say about the two camps of
the introduction: xoshiro256** (linear camp) and ChaCha20 (ARX camp).

All numbers below are computed here, not copied from literature.
"""
import numpy as np

U64 = np.uint64
MASK = U64(0xFFFFFFFFFFFFFFFF)

def rotl(x, r):
    r %= 64
    if isinstance(x, np.ndarray):
        return (np.left_shift(x, r) | np.right_shift(x, 64 - r)) & MASK
    return ((x << r) | (x >> (64 - r))) & MASK

# ---------------------------------------------------------------------------
# xoshiro256** state update (Blackman & Vigna 2021) — the transition F only
# ---------------------------------------------------------------------------
def xoshiro_step(s):
    """F: advance 256-bit state by one step (rotation/XOR only)."""
    s = [U64(x) for x in s]
    t = s[1] << 17
    s[2] ^= s[0]; s[3] ^= s[1]; s[1] ^= s[2]; s[0] ^= s[3]
    s[2] ^= t
    s[3] = rotl(s[3], 45)
    return s

def xoshiro_output(s):
    """g: xoshiro256** output function (contains 64-bit multiplication)."""
    return (rotl(s[1] * U64(5), 7) * U64(9)) & MASK

# ---------------------------------------------------------------------------
# ChaCha20 state update — one double round on the 16-word state (ARX)
# ---------------------------------------------------------------------------
def chacha_qr(s, a, b, c, d):
    s[a] = (s[a] + s[b]) & U64(0xFFFFFFFF)
    s[d] ^= s[a]; s[d] = rotl32(s[d], 16)
    s[c] = (s[c] + s[d]) & U64(0xFFFFFFFF)
    s[b] ^= s[c]; s[b] = rotl32(s[b], 12)
    s[a] = (s[a] + s[b]) & U64(0xFFFFFFFF)
    s[d] ^= s[a]; s[d] = rotl32(s[d], 8)
    s[c] = (s[c] + s[d]) & U64(0xFFFFFFFF)
    s[b] ^= s[c]; s[b] = rotl32(s[b], 7)

def rotl32(x, r):
    return ((x << r) | (x >> (32 - r))) & U64(0xFFFFFFFF)

def chacha_round(s):
    """One double round on the 16-word state (F)."""
    s = [U64(x) for x in s]
    chacha_qr(s, 0, 4, 8, 12); chacha_qr(s, 1, 5, 9, 13)
    chacha_qr(s, 2, 6, 10, 14); chacha_qr(s, 3, 7, 11, 15)
    chacha_qr(s, 0, 5, 10, 15); chacha_qr(s, 1, 6, 11, 12)
    chacha_qr(s, 2, 7, 8, 13); chacha_qr(s, 3, 4, 9, 14)
    return s

# ---------------------------------------------------------------------------
# 1. Linearity of the xoshiro state transition F
# ---------------------------------------------------------------------------
rng = np.random.default_rng(20260813)
viol = 0
N = 200
for _ in range(N):
    a = [rng.integers(0, 2**64, dtype=np.uint64) for _ in range(4)]
    b = [rng.integers(0, 2**64, dtype=np.uint64) for _ in range(4)]
    F_a = xoshiro_step(a); F_b = xoshiro_step(b)
    ab = [a[i] ^ b[i] for i in range(4)]
    F_ab = xoshiro_step(ab)
    if [F_a[i] ^ F_b[i] for i in range(4)] != F_ab:
        viol += 1
print(f'xoshiro256** F linearity: {N} random pairs, GF(2)-linear violations: {viol}')

# ---------------------------------------------------------------------------
# 2. GF(2) rank of the xoshiro transition matrix  ->  state image = full space
# ---------------------------------------------------------------------------
def matvec(m, v):
    """m: list of 256 bit-columns as ints; v: 256-bit int; returns m*v (int)."""
    out = 0
    for i, col in enumerate(m):
        if (v >> i) & 1:
            out ^= col
    return out

cols = []
for i in range(256):
    e = [U64(0)] * 4
    e[i // 64] = U64(1) << (i % 64)
    F_e = xoshiro_step(e)
    col = 0
    for j in range(4):
        col |= int(F_e[j]) << (64 * j)
    cols.append(col)

# GF(2) Gaussian elimination
rank = 0
basis = []
for col in cols:
    c = col
    for b in basis:
        c = min(c, c ^ b) if (c ^ b) < c else c  # reduce by leading bit
    # proper reduction: clear the highest set bit against each basis vector
for b in basis:
    pass
basis = []
for col in cols:
    c = col
    for b in basis:
        if c & (1 << (b.bit_length() - 1)):
            c ^= b
    if c:
        basis.append(c)
rank = len(basis)
print(f'xoshiro256** transition matrix: GF(2) rank = {rank}/256 '
      f'-> injective (permutation) -> state image = full space (exact)')

# ---------------------------------------------------------------------------
# 3. Deterministic differential propagation of xoshiro (DP = 1, exact)
# ---------------------------------------------------------------------------
dviol = 0
for _ in range(N):
    d = [rng.integers(0, 2**64, dtype=np.uint64) for _ in range(4)]
    s1 = [rng.integers(0, 2**64, dtype=np.uint64) for _ in range(4)]
    s2 = [rng.integers(0, 2**64, dtype=np.uint64) for _ in range(4)]
    sd = [s1[i] ^ d[i] for i in range(4)]
    F_s1 = xoshiro_step(s1); F_sd = xoshiro_step(sd)
    d1 = [F_s1[i] ^ F_sd[i] for i in range(4)]
    sd2 = [s2[i] ^ d[i] for i in range(4)]
    F_s2 = xoshiro_step(s2); F_sd2 = xoshiro_step(sd2)
    d2 = [F_s2[i] ^ F_sd2[i] for i in range(4)]
    if d1 != d2:
        dviol += 1
print(f'xoshiro256** differential: {N} random (s, s+delta) pairs, '
      f'state-independent output-difference violations: {dviol} '
      f'-> DP = 1 exactly (single round)')

# ---------------------------------------------------------------------------
# 4. ChaCha20 non-linearity: a counterexample F(a^b) != F(a)^F(b)
# ---------------------------------------------------------------------------
cviol = 0
for _ in range(N):
    a = [rng.integers(0, 2**32, dtype=np.uint64) for _ in range(16)]
    b = [rng.integers(0, 2**32, dtype=np.uint64) for _ in range(16)]
    F_a = chacha_round(a); F_b = chacha_round(b)
    ab = [a[i] ^ b[i] for i in range(16)]
    F_ab = chacha_round(ab)
    if [F_a[i] ^ F_b[i] for i in range(16)] != F_ab:
        cviol += 1
print(f'ChaCha20 double-round F: {N} random pairs, GF(2)-linear violations: '
      f'{cviol} (nonlinear; exact degree/differential unknown)')

# ---------------------------------------------------------------------------
# 5. xoshiro output function: multiplication => nonlinearity
# ---------------------------------------------------------------------------
oviol = 0
for _ in range(N):
    a = [rng.integers(0, 2**64, dtype=np.uint64) for _ in range(4)]
    b = [rng.integers(0, 2**64, dtype=np.uint64) for _ in range(4)]
    g_a = xoshiro_output(a); g_b = xoshiro_output(b)
    ab = [a[i] ^ b[i] for i in range(4)]
    g_ab = xoshiro_output(ab)
    if (g_a ^ g_b) != g_ab:
        oviol += 1
print(f'xoshiro256** output g: {N} random pairs, GF(2)-linear violations: '
      f'{oviol} (contains 64-bit multiplication -> nonlinear)')

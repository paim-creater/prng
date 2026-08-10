# -*- coding: utf-8 -*-
"""v31_diagnose.py — structural diagnosis of the rebuilt v3.1 generator.

Why does the rebuilt v3.1 show WEAK anomalies in rgb_lagged_sum (ntup=7)
and marsaglia_tsang_gcd while Algorithm 1 passes everything? This script
probes the round-function structure directly:

  (a) state period: does the state iterate into a short cycle?
  (b) output linear complexity (Berlekamp-Massey on the bit stream);
  (c) per-bit statistics: constant bits / low-entropy bits;
  (d) bit-lane mixing: does each output bit depend on all state bits?
      (propagate a single-bit difference through R rounds, count
      affected bits — the "snowball" test);
  (e) lag correlation: raw Corr[x[i], x[i+7]] and x[i]+x[i+7] parity
      (the rgb_lagged_sum ntup=7 mechanism).

Usage: python v31_diagnose.py
"""
import numpy as np

M = (1 << 64) - 1


def rotl(x, r):
    return ((x << r) | (x >> (64 - r))) & M


def andmix4(t):
    t ^= rotl(t, 31) & rotl(t, 53)
    t ^= rotl(t, 17) & rotl(t, 43)
    t ^= rotl(t, 7) & rotl(t, 23)
    t ^= rotl(t, 5) & rotl(t, 19)
    return t & M


def zfc_round(u, v, w, z):
    u0, v0, w0, z0 = u, v, w, z
    u = u0 ^ rotl(v0, 5) ^ rotl(w0, 13) ^ rotl(z0, 25)
    v = v0 ^ rotl(w0, 11) ^ rotl(z0, 19) ^ rotl(u0, 29)
    w = w0 ^ rotl(z0, 23) ^ rotl(u0, 9) ^ rotl(v0, 15)
    z = z0 ^ rotl(u0, 17) ^ rotl(v0, 27) ^ rotl(w0, 21)
    u ^= rotl(u, 22) ^ rotl(u, 26); u = andmix4(u)
    v ^= rotl(v, 22) ^ rotl(v, 26); v = andmix4(v)
    w ^= rotl(w, 22) ^ rotl(w, 26); w = andmix4(w)
    z ^= rotl(z, 22) ^ rotl(z, 26); z = andmix4(z)
    return u, v, w, z


def make_output(u, v, w, z):
    t = u ^ rotl(v, 32) ^ w ^ rotl(z, 16)
    t ^= rotl(t, 27) ^ rotl(t, 17)
    t = andmix4(t)
    t ^= t >> 32
    return t & M


def rng(seed=0x9E3779B97F4A7C15):
    u, v = seed, seed ^ 0x6A09E667F3BCC908
    w, z = seed ^ 0x3243F6A8885A308D, seed ^ 0xB7E151628AED2A6B
    for _ in range(22):
        u, v, w, z = zfc_round(u, v, w, z)
    while True:
        yield make_output(u, v, w, z)
        u, v, w, z = zfc_round(u, v, w, z)


def berlekamp_massey(bits):
    """linear complexity of a binary sequence (list of 0/1)."""
    n = len(bits)
    c = [0] * n
    b = [0] * n
    c[0] = b[0] = 1
    L, m = 0, -1
    for i in range(n):
        d = bits[i]
        for j in range(1, L + 1):
            d ^= c[j] & bits[i - j]
        if d == 0:
            m += 1
        else:
            t = c[:]
            for j in range(n - i + m):
                c[i - m + j] ^= b[j]
            if 2 * L <= i:
                L = i + 1 - L
                b = t
                m = i - L + 1
            else:
                m += 1
    return L


def main():
    g = rng()
    outs = [next(g) for _ in range(200_000)]

    print("=== (a) state/output period probe (birthday over 200k outputs) ===")
    seen = {}
    dup = None
    for i, o in enumerate(outs):
        if o in seen:
            dup = (seen[o], i)
            break
        seen[o] = i
    print(f"  duplicate output word: {dup if dup else 'none in 200k'}")

    print("=== (b) linear complexity (Berlekamp-Massey, 10k bits) ===")
    bits = []
    for o in outs[:160]:
        bits += [(o >> b) & 1 for b in range(64)]
    L = berlekamp_massey(bits[:10000])
    print(f"  LC(10,000 bits) = {L}  (random expectation ~n/2 = 5000)")

    print("=== (c) per-bit statistics (first 1M words) ===")
    ones = np.zeros(64, dtype=np.int64)
    for o in outs[:100000]:
        for b in range(64):
            ones[b] += (o >> b) & 1
    p = ones / 100000
    dev = np.abs(p - 0.5) * 2
    worst = int(np.argmax(dev))
    print(f"  max |bias| bit {worst}: {dev[worst]:.4f} "
          f"({'ok' if dev[worst] < 0.02 else 'SUSPICIOUS'})")
    const = np.where(np.abs(p - 0.5) > 0.45)[0]
    print(f"  near-constant bits: {list(const) if len(const) else 'none'}")

    print("=== (d) snowball: single-bit diff after R rounds ===")
    for R in (1, 2, 4, 8, 16, 22):
        u, v, w, z = 1, 2, 3, 4
        u1, v1, w1, z1 = u ^ 1, v, w, z
        for _ in range(R):
            u, v, w, z = zfc_round(u, v, w, z)
            u1, v1, w1, z1 = zfc_round(u1, v1, w1, z1)
        diff = (u ^ u1) | (v ^ v1) | (w ^ w1) | (z ^ z1)
        nbits = bin(diff).count('1')
        print(f"  R={R}: {nbits}/256 bits differ from a 1-bit input diff")

    print("=== (e) lag-7 correlation (rgb_lagged_sum ntup=7 mechanism) ===")
    xs = np.array(outs[:100000], dtype=np.uint64)
    # parity of x[i] XOR x[i-7] per bit
    lag = xs[7:] ^ xs[:-7]
    for b in (0, 31, 63):
        ones_l = int(((lag >> b) & 1).sum())
        p_l = ones_l / len(lag)
        print(f"  bit {b}: P[x[i]^x[i-7] = 1] = {p_l:.4f} "
              f"(expect 0.5000, |dev|={abs(p_l - 0.5) * 2:.4f})")
    # word-level xor bias
    xw = xs[7:] ^ xs[:-7]
    print(f"  word-xor: nonzero fraction = {(xw != 0).mean():.4f}")

    print("=== (f) two-word correlation (word-level lag) ===")
    for L in (1, 2, 3, 7):
        c = np.corrcoef(xs[:-L].astype(float), xs[L:].astype(float))[0, 1]
        print(f"  Corr[x[i], x[i+{L}]] = {c:+.5f}")


if __name__ == '__main__':
    main()

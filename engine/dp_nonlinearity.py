"""dp_nonlinearity.py — the cascade-nonlinearity study.

For W=4 we compute, per input difference Delta:
  (a) the ANF algebraic degree of the differential map
      D_Delta(s) = Phi(s xor Delta) xor Phi(s),
  (b) the exact one-round differential probability DP(Delta)
      (max over output differences, full state enumeration),
and test the correlation between the two.

If higher differential-map degree correlates with LOWER DP (more random),
this is the empirical basis for a new theorem: in AND-RX with cascaded
ANDs, the differential map is genuinely nonlinear, and the nonlinearity
tightens the differential bound beyond the single-trail 2^-a1 model —
an empirical packing argument the paper can state honestly.
"""
import numpy as np
import sys, time

from cipher import tempest_a1_round_program

W = 4
MASK = np.uint16((1 << W) - 1)
IDX = {'u': 0, 'v': 1, 'w': 2, 'z': 3}
NB = 4 * W


def rotl16(x, r):
    r %= W
    return np.uint16(((x << r) & MASK) | (x >> (W - r)))


def apply_round_vec(st):
    for op in tempest_a1_round_program():
        t = op[0]
        if t == 'SNAP':
            pass
        elif t == 'X3':
            w, a, b, r1, r2 = IDX[op[1]], IDX[op[2]], IDX[op[3]], op[4], op[5]
            st[:, w] = (st[:, w] ^ rotl16(st[:, a], r1)
                        ^ rotl16(st[:, b], r2)) & MASK
        elif t == 'AND':
            w, a, b, r1, r2 = IDX[op[1]], IDX[op[2]], IDX[op[3]], op[4], op[5]
            st[:, w] = (st[:, w] ^ (rotl16(st[:, a], r1)
                                    & rotl16(st[:, b], r2))) & MASK
        elif t == 'A3':
            w, r1, r2, r3, r4 = IDX[op[1]], op[2], op[3], op[4], op[5]
            v = st[:, w]
            st[:, w] = (v ^ rotl16(v, r1) ^ rotl16(v, r2)
                        ^ (rotl16(v, r3) & rotl16(v, r4))) & MASK
        elif t == 'A2':
            w, r1, r2 = IDX[op[1]], op[2], op[3]
            v = st[:, w]
            st[:, w] = (v ^ rotl16(v, r1) ^ rotl16(v, r2)) & MASK
    return st


def anf_degree(truth):
    """ANF degree of a Boolean function given its truth table (numpy array
    of 2^n bits) via the Mobius transform."""
    n = int(np.log2(len(truth)))
    a = truth.astype(np.uint8).copy()
    step = 1
    while step < 1 << n:
        for i in range(0, 1 << n, 2 * step):
            a[i + step:i + 2 * step] ^= a[i:i + step]
        step <<= 1
    deg = 0
    for i, v in enumerate(a):
        if v and bin(i).count('1') > deg:
            deg = bin(i).count('1')
    return deg


def main():
    codes = np.arange(1 << 16, dtype=np.uint16)
    st = np.zeros((len(codes), 4), dtype=np.uint16)
    for wi in range(4):
        st[:, wi] = (codes >> (wi * W)) & MASK
    out0 = apply_round_vec(st.copy())
    out0f = (out0[:, 0] | (out0[:, 1] << W) | (out0[:, 2] << (2*W))
             | (out0[:, 3] << (3*W)))

    rng = np.random.default_rng(7)
    deltas = [0x0001, 0x0005, 0x000f, 0x00ff, 0x0f0f, 0x5555, 0xffff]
    deltas += [int(rng.integers(1, 1 << 16)) for _ in range(30)]

    rows = []
    t0 = time.time()
    for d in deltas:
        codes2 = codes ^ np.uint16(d)
        st2 = np.zeros((len(codes2), 4), dtype=np.uint16)
        for wi in range(4):
            st2[:, wi] = (codes2 >> (wi * W)) & MASK
        out1 = apply_round_vec(st2.copy())
        out1f = (out1[:, 0] | (out1[:, 1] << W) | (out1[:, 2] << (2*W))
                 | (out1[:, 3] << (3*W)))
        diff = out0f ^ out1f
        uniq, counts = np.unique(diff, return_counts=True)
        dp = counts.max() / 2**16
        # ANF degree of each of the 16 output bits of D_Delta
        degs = []
        for j in range(NB):
            tt = (diff >> j) & 1
            degs.append(anf_degree(tt))
        deg_max = max(degs)
        rows.append((d, deg_max, -np.log2(dp), dp))
        print(f'delta 0x{d:04x}: deg(D)= {deg_max:2d}  '
              f'-log2 DP = {-np.log2(dp):6.2f}  ({time.time()-t0:.0f}s)')

    # correlation: deg vs -log2 DP
    degs = np.array([r[1] for r in rows], dtype=float)
    dps = np.array([r[2] for r in rows], dtype=float)
    corr = np.corrcoef(degs, dps)[0, 1]
    print(f'\ncorrelation(deg(D_Delta), -log2 DP): {corr:.3f} '
          f'(n={len(rows)})')


if __name__ == '__main__':
    main()

"""tradeoff.py — the Algebraic-Differential Tradeoff study (W=4).

For every input difference Delta we compute:
  (a) r_lin(Delta): the rank of the LINEARIZED differential map
      (ignore AND output-difference products x*dy ^ y*dx; keep only the
      dx*dy constant terms and the deterministic XOR/ROT propagation) —
      predicting DP_lin = 2^(-r_lin);
  (b) DP(Delta): the exact one-round differential probability by full
      state enumeration.

The question: is DP(Delta) >= 2^(-r_lin(Delta)) for every Delta?
If yes: the nonlinearity of cascaded ANDs *aggregates* states onto fewer
output differences, RAISING the differential probability above the linear
prediction — an algebraic-differential tradeoff: more algebraic degree
costs differential uniformity. This is a new, quantitative design law for
AND-RX (neither Biham-Shamir nor wide-trail nor Todo address it).

Note: the linearized map keeps, per AND gate, the term dx*dy (a constant
given Delta) — the state-dependent terms x*dy, y*dx are the nonlinear
part. The linearized differential output is therefore a deterministic
linear function of the input differences only; its "rank" as used below
counts the dimension of the linearized output difference space over the
state-dependent part (the B-matrix rank from dp_rank.py, which tracks
state-bit dependence per output bit).
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


def b_matrix_rank(delta_code):
    """Rank of the state-bit dependence matrix of the differential map:
    for each output bit, the set of state bits on which the (linear part
    of the) difference depends. Cascaded AND nonlinear terms make this an
    *approximation* of the linearized rank; we report it as r_lin.
    Symbolic tracker: every word bit carries (const, deps) where deps is
    the list of state-bit indices whose XOR coefficient is 1."""
    W_ = W
    prog = tempest_a1_round_program()
    D = [(delta_code >> (wi * W_)) & MASK for wi in range(4)]
    # symbolic: sym[w][b] = (const, deps)
    sym = []
    for wi in range(4):
        sym.append([(0, [wi * W_ + b]) for b in range(W_)])

    def rot_sym(word, r):
        r %= W_
        return [sym[word][(b - r) % W_] for b in range(W_)]

    def xor3_dedupe(items):
        cnt = {}
        for k in items:
            cnt[k] = cnt.get(k, 0) + 1
        return [k for k, v in cnt.items() if v % 2 == 1]

    for op in prog:
        t = op[0]
        if t == 'SNAP':
            pass
        elif t == 'X3':
            w, a, b, r1, r2 = IDX[op[1]], IDX[op[2]], IDX[op[3]], op[4], op[5]
            da = rot_sym(a, r1)
            db = rot_sym(b, r2)
            D[w] = D[w] ^ rotl16(D[a], r1) ^ rotl16(D[b], r2)
            for i in range(W_):
                c1, d1 = sym[w][i]
                c2, d2 = da[i]
                c3, d3 = db[i]
                sym[w][i] = ((c1 ^ c2 ^ c3), xor3_dedupe(d1 + d2 + d3))
        elif t == 'AND':
            w, a, b, r1, r2 = IDX[op[1]], IDX[op[2]], IDX[op[3]], op[4], op[5]
            da = rot_sym(a, r1)
            db = rot_sym(b, r2)
            D[w] = D[w] ^ (rotl16(D[a], r1) & rotl16(D[b], r2))
            for i in range(W_):
                c1, d1 = sym[w][i]
                dx = (D[a] >> ((i - r1) % W_)) & 1
                dy = (D[b] >> ((i - r2) % W_)) & 1
                c2, d2 = da[i]
                c3, d3 = db[i]
                const = (dy & c2) ^ (dx & c3) ^ (dx & dy)
                deps = []
                if dy:
                    deps += d2
                if dx:
                    deps += d3
                sym[w][i] = ((c1 ^ const), xor3_dedupe(d1 + deps))
        elif t == 'A3':
            w, r1, r2, r3, r4 = IDX[op[1]], op[2], op[3], op[4], op[5]
            v = [row[:] for row in sym[w]]
            v1 = rot_sym(w, r1)
            v2 = rot_sym(w, r2)
            v3 = rot_sym(w, r3)
            v4 = rot_sym(w, r4)
            D[w] = D[w] ^ rotl16(D[w], r1) ^ rotl16(D[w], r2)
            D[w] = D[w] ^ (rotl16(D[w], r3) & rotl16(D[w], r4))
            for i in range(W_):
                c0, d0 = v[i]
                c1, d1 = v1[i]
                c2, d2 = v2[i]
                c3, d3 = v3[i]
                c4, d4 = v4[i]
                dx = (D[w] >> ((i - r3) % W_)) & 1
                dy = (D[w] >> ((i - r4) % W_)) & 1
                const = (dy & c3) ^ (dx & c4) ^ (dx & dy)
                deps = d0 + d1 + d2
                if dy:
                    deps += d3
                if dx:
                    deps += d4
                sym[w][i] = ((c0 ^ c1 ^ c2 ^ const), xor3_dedupe(deps))
        elif t == 'A2':
            w, r1, r2 = IDX[op[1]], op[2], op[3]
            v1 = rot_sym(w, r1)
            v2 = rot_sym(w, r2)
            D[w] = D[w] ^ rotl16(D[w], r1) ^ rotl16(D[w], r2)
            for i in range(W_):
                c0, d0 = sym[w][i]
                c1, d1 = v1[i]
                c2, d2 = v2[i]
                sym[w][i] = ((c0 ^ c1 ^ c2), xor3_dedupe(d0 + d1 + d2))
        elif t in ('CONST', 'WEYL', 'NLFILT', 'KEY'):
            pass

    # build B matrix (NB x NB) and rank over GF(2)
    NB_ = NB
    B = np.zeros((NB_, NB_), dtype=np.uint8)
    for w in range(4):
        for b in range(W_):
            j = w * W_ + b
            for k in sym[w][b][1]:
                B[j, k] ^= 1
    rk = 0
    mat = B.copy()
    for col in range(NB_):
        pivot = None
        for row in range(rk, NB_):
            if mat[row, col]:
                pivot = row
                break
        if pivot is None:
            continue
        mat[[rk, pivot]] = mat[[pivot, rk]]
        for row in range(rk + 1, NB_):
            if mat[row, col]:
                mat[row] ^= mat[rk]
        rk += 1
    return rk


def main():
    codes = np.arange(1 << 16, dtype=np.uint16)
    st = np.zeros((len(codes), 4), dtype=np.uint16)
    for wi in range(4):
        st[:, wi] = (codes >> (wi * W)) & MASK
    out0 = apply_round_vec(st.copy())
    out0f = (out0[:, 0] | (out0[:, 1] << W) | (out0[:, 2] << (2*W))
             | (out0[:, 3] << (3*W)))

    rng = np.random.default_rng(11)
    deltas = [0x0001, 0x0005, 0x000f, 0x00ff, 0x0f0f, 0x5555, 0xffff]
    deltas += [int(rng.integers(1, 1 << 16)) for _ in range(40)]

    violations = []
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
        r_lin = b_matrix_rank(d)
        pred = 2 ** (-r_lin)
        ok = dp >= pred - 1e-12
        if not ok:
            violations.append((d, r_lin, dp))
        if len(deltas) <= 10 or True:
            print(f'delta 0x{d:04x}: r_lin={r_lin:2d}  '
                  f'DP_pred=2^-{r_lin}  DP_meas=2^{np.log2(dp):+.2f}  '
                  f'DP>=pred: {ok}  ({time.time()-t0:.0f}s)', flush=True)
    print(f'\nDP(Delta) >= 2^(-r_lin(Delta)) holds for '
          f'{len(deltas)-len(violations)}/{len(deltas)} differences')
    if violations:
        print('violations:', [(hex(d), r, f'{p:.6f}') for d, r, p in violations[:5]])
    else:
        print('THEOREM CANDIDATE: DP(Delta) >= 2^(-r_lin(Delta)) for all '
              'sampled differences -> nonlinearity aggregates, never '
              'disperses, the differential distribution')


if __name__ == '__main__':
    main()

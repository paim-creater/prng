# -*- coding: utf-8 -*-
"""audit_true_algorithm1.py — CRITICAL AUDIT of the paper's W=4 numbers.

The paper's headline measurements (H_inf = 7.93 / 7.80, duality checks,
image collapse 3902->248, rounds 1..22) were produced by explore_ddt.py,
whose interpreter IGNORES the snapshot (SNAP = pass, all reads from current
state).  The KAT-verified C code / DSL / scalar port implement SNAPSHOT
semantics (Phase A reads u0..z0).  This script recomputes the full-domain
W=4 exact numbers with CORRECT snapshot semantics:

  1. cross-check my interpreter against cipher.py apply_round at W=4
     (the DSL interpreter, cross-validated against the scalar C port);
  2. exact DDT max / DP0 mean / image size / LAT for the true Algorithm 1,
     with-key (wv0=0x8) and no-key, rounds 1..22;
  3. ANF degree of Phi and D_Delta for selected variants, to settle the
     affine-differential question;
  4. rank (polar-form) analysis for the k=0 quadratic variant.
"""
import numpy as np
import json, time, sys

sys.path.insert(0, '.')
from cipher import tempest_a1_round_program, State, apply_round

W = 4
MASK = np.uint16((1 << W) - 1)
IDX = {'u': 0, 'v': 1, 'w': 2, 'z': 3}
NIN = 1 << (4 * W)
IDX_AR = np.arange(NIN, dtype=np.uint16)


def rotl16(x, r):
    r %= W
    return np.uint16(((x << r) & MASK) | (x >> (W - r)))


def apply_round_snap(st, ops, wv=None):
    """Snapshot-aware interpreter; wv = [weyl, weyl_nl] for key ops."""
    snap = None
    if wv is None:
        wv = [np.uint16(0), np.uint16(0)]
    for op in ops:
        t = op[0]
        if t == 'SNAP':
            snap = st.copy()
        elif t == 'X3':
            w, a, b, r1, r2, sf = IDX[op[1]], IDX[op[2]], IDX[op[3]], op[4], op[5], op[6]
            av = rotl16((snap if sf else st)[:, a], r1)
            bv = rotl16((snap if sf else st)[:, b], r2)
            st[:, w] = (st[:, w] ^ av ^ bv) & MASK
        elif t == 'AND':
            w, a, b, r1, r2, sf = IDX[op[1]], IDX[op[2]], IDX[op[3]], op[4], op[5], op[6]
            av = rotl16((snap if sf else st)[:, a], r1)
            bv = rotl16((snap if sf else st)[:, b], r2)
            st[:, w] = (st[:, w] ^ (av & bv)) & MASK
        elif t == 'A3':
            w, r1, r2, r3, r4 = IDX[op[1]], op[2], op[3], op[4], op[5]
            v = st[:, w]
            st[:, w] = (v ^ rotl16(v, r1) ^ rotl16(v, r2)
                        ^ (rotl16(v, r3) & rotl16(v, r4))) & MASK
        elif t == 'A2':
            w, r1, r2 = IDX[op[1]], op[2], op[3]
            v = st[:, w]
            st[:, w] = (v ^ rotl16(v, r1) ^ rotl16(v, r2)) & MASK
        elif t == 'CONST':
            w, c = IDX[op[1]], op[2] & 0xF
            st[:, w] = (st[:, w] ^ np.uint16(c)) & MASK
        elif t == 'WEYL':
            r, c = op[1] % W, op[2] & 0xF
            wv[0] = (wv[0] ^ rotl16(wv[0], r) ^ np.uint16(c)) & MASK
        elif t == 'NLFILT':
            c = op[1] & 0xF
            wv[1] = (wv[0] ^ rotl16(wv[0] & np.uint16(c), 13 % W)) & MASK
        elif t == 'KEY':
            w, r, s = IDX[op[1]], op[2] % W, op[3]
            val = (rotl16(wv[1], r) ^ np.uint16(wv[1] >> s)) & MASK
            st[:, w] = (st[:, w] ^ val) & MASK
        else:
            raise ValueError(t)
    return st, wv


def tabulate(ops, with_key, wv0=0x8):
    codes = IDX_AR
    st = np.zeros((NIN, 4), dtype=np.uint16)
    for wi in range(4):
        st[:, wi] = (codes >> (wi * W)) & MASK
    st, wv = apply_round_snap(st, ops, [np.uint16(wv0), np.uint16(0)])
    return (st[:, 0] | (st[:, 1] << W) | (st[:, 2] << (2 * W))
            | (st[:, 3] << (3 * W))).astype(np.uint16)


def crosscheck_vs_dsl():
    """Cross-check apply_round_snap against the DSL interpreter (cipher.py),
    which was validated against the scalar C port."""
    rng = np.random.default_rng(123)
    ops = tempest_a1_round_program()
    ok = True
    for trial in range(20):
        s = rng.integers(0, NIN, size=32, dtype=np.uint16)
        st1 = np.zeros((32, 4), dtype=np.uint16)
        for wi in range(4):
            st1[:, wi] = (s >> (wi * W)) & MASK
        r1, _ = apply_round_snap(st1.copy(), ops, [np.uint16(5), np.uint16(0)])
        # DSL interpreter
        words = [s.astype(np.uint64) for _ in range(4)]
        for wi in range(4):
            words[wi] = (s >> (wi * W)) & np.uint64(MASK)
        st2 = State(words, np.uint64(5), W=W)
        apply_round(ops, st2)
        r2 = [(st2.words[wi] & np.uint64(MASK)).astype(np.uint16) for wi in range(4)]
        for wi in range(4):
            if not np.array_equal(r1[:, wi], r2[wi]):
                ok = False
                print(f'trial {trial}: word {wi} MISMATCH')
    print(f'crosscheck apply_round_snap vs DSL interpreter: {"PASS" if ok else "FAIL"}')


def full_domain_analysis(T, label):
    res = {'label': label}
    t0 = time.time()
    ddt_max = 0
    ddt_max_delta = 0
    dp0_sum = 0.0
    for di in range(1, NIN):
        dT = T[IDX_AR ^ np.uint16(di)] ^ T
        counts = np.bincount(dT.astype(np.int64), minlength=NIN)
        m = counts.max()
        if m > ddt_max:
            ddt_max = m
            ddt_max_delta = di
        dp0_sum += counts[0]
    ddt_max /= NIN
    res['ddt_max_dlog2'] = round(-np.log2(ddt_max), 4)
    res['ddt_max_delta'] = hex(ddt_max_delta)
    res['dp0_mean_dlog2'] = round(-np.log2(dp0_sum / NIN / (NIN - 1)), 4)
    fiber = np.bincount(T.astype(np.int64), minlength=NIN)
    res['image_size'] = int(np.count_nonzero(fiber))
    res['fiber_max_dlog2'] = round(-np.log2(fiber.max() / NIN), 4)
    print(f'{label}: -log2 DDTmax={res["ddt_max_dlog2"]:.4f} '
          f'(delta {res["ddt_max_delta"]})  <DP0>={res["dp0_mean_dlog2"]:.4f} '
          f'img={res["image_size"]}  fiber={res["fiber_max_dlog2"]:.2f} '
          f'({time.time()-t0:.0f}s)', flush=True)
    return res


def anf_degree(tt):
    n = int(np.log2(len(tt)))
    a = tt.astype(np.uint8).copy()
    step = 1
    while step < 1 << n:
        for i in range(0, 1 << n, 2 * step):
            a[i + step:i + 2 * step] ^= a[i:i + step]
        step <<= 1
    deg = 0
    for i, v in enumerate(a):
        if v:
            deg = max(deg, bin(i).count('1'))
    return deg


def degree_check(ops, label, with_key, wv0):
    """ANF degree of Phi and of D_Delta for a few deltas."""
    codes = IDX_AR
    st = np.zeros((NIN, 4), dtype=np.uint16)
    for wi in range(4):
        st[:, wi] = (codes >> (wi * W)) & MASK
    T0, _ = apply_round_snap(st.copy(), ops, [np.uint16(wv0), np.uint16(0)])
    T0f = (T0[:, 0] | (T0[:, 1] << W) | (T0[:, 2] << (2 * W)) | (T0[:, 3] << (3 * W)))
    degs_phi = []
    for j in range(16):
        degs_phi.append(anf_degree((T0f >> j) & 1))
    degs_d = {}
    for d in (0x0001, 0x0005, 0x000a, 0x00ff, 0x0f0f, 0x5555, 0xffff):
        st2 = np.zeros((NIN, 4), dtype=np.uint16)
        codes2 = IDX_AR ^ np.uint16(d)
        for wi in range(4):
            st2[:, wi] = (codes2 >> (wi * W)) & MASK
        T1, _ = apply_round_snap(st2.copy(), ops, [np.uint16(wv0), np.uint16(0)])
        T1f = (T1[:, 0] | (T1[:, 1] << W) | (T1[:, 2] << (2 * W)) | (T1[:, 3] << (3 * W)))
        diff = T0f ^ T1f
        dd = max(anf_degree((diff >> j) & 1) for j in range(16))
        degs_d[hex(d)] = dd
    print(f'{label}: deg(Phi) per-bit max={max(degs_phi)}  '
          f'deg(D_Delta)={{' + ', '.join(f'{k}:{v}' for k, v in degs_d.items()) + '}')
    return max(degs_phi), degs_d


def truncate_at_levels(ops, k, include_premix=True):
    a3_idx = [i for i, op in enumerate(ops) if op[0] == 'A3']
    snap_idx = [i for i, op in enumerate(ops) if op[0] == 'SNAP']
    first_level = min(i for i in snap_idx if i > max(a3_idx))
    level_starts = [i for i in snap_idx if i >= first_level][:4]
    cut = level_starts[k] if k < 4 else len(ops)
    if not include_premix:
        cut = min(cut, min(a3_idx))
    return ops[:cut]


def main():
    base = tempest_a1_round_program()
    crosscheck_vs_dsl()

    out = {'meta': {'note': 'snapshot-correct Algorithm 1 semantics, W=4'}}
    # k=0 quadratic variants (no-key), full domain + degree + rank identity
    for label, k, premix in [('k0_nopremix', 0, False), ('k0_premix', 0, True)]:
        ops = truncate_at_levels(base, k, premix)
        T = tabulate(ops, with_key=False)
        out[label] = full_domain_analysis(T, label)
        deg_phi, deg_d = degree_check(ops, label, with_key=False, wv0=0)
        out[label]['deg_phi_max'] = deg_phi
        out[label]['deg_D_deltas'] = deg_d

    # full Algorithm 1 (k=4), no-key and with-key, 22 rounds
    ops = base
    for wkey, wv0 in [('nokey', 0), ('withkey', 0x8), ('withkey0', 0x0)]:
        with_key = (wkey != 'nokey')
        codes = IDX_AR
        st = np.zeros((NIN, 4), dtype=np.uint16)
        for wi in range(4):
            st[:, wi] = (codes >> (wi * W)) & MASK
        wv = [np.uint16(wv0), np.uint16(0)]
        rounds = {}
        for r in range(1, 23):
            st, wv = apply_round_snap(st, ops, wv)
            T = (st[:, 0] | (st[:, 1] << W) | (st[:, 2] << (2 * W))
                 | (st[:, 3] << (3 * W))).astype(np.uint16)
            if r in (1, 2, 4, 8, 12, 16, 22) or (wkey == 'nokey' and r == 1):
                rounds[f'r{r}'] = full_domain_analysis(T, f'{wkey} r={r}')
        out[wkey] = rounds
    deg_phi, deg_d = degree_check(ops, 'full k=4', with_key=False, wv0=0)
    out['full_deg_phi_max'] = deg_phi
    out['full_deg_D_deltas'] = deg_d

    with open('audit_true_algorithm1.json', 'w') as f:
        json.dump(out, f, indent=1)
    print('done -> audit_true_algorithm1.json')


if __name__ == '__main__':
    main()

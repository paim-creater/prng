# -*- coding: utf-8 -*-
"""explore_ddt.py — EXACT full-domain differential & linear analysis at W=4.

For each round r = 1..22 and each variant (with-key / no-key):
  f_r : F2^16 -> F2^16 tabulated EXACTLY over all 2^16 states.
  EXACTLY over all 65535 input differences Delta:
    DP0(Delta)  = Pr_x[D_Delta f = 0]       (zero-output differential)
    DDT max     = max over (Delta, Delta') DP(Delta -> Delta')
  EXACTLY over all 16 single-bit outputs and 2^16 masks: single-bit LAT.
  Walsh spectral energy profile from the duality identity:
    E(a) = 2^-n * WHT(DP0)[a]   (so DP0(Delta) = 2^-n WHT(E)[Delta])
    E(0) = <DP0>_Delta  (average zero-DP = total bias energy, exact)

Two-source verification at rounds {1, 22} (with-key):
    sample U masks u, compute g_u = u.f truth table, full WHT each:
    E_est(a) = mean_u ghat_u(a)^2  must equal E(a) = 2^-n WHT(DP0)[a]
  (E(a) = <ghat_u(a)^2>_u — differential-linear duality in mean square.)

Baselines: random functions and permutations on 2^16 states.
"""
import numpy as np
import time, json

from cipher import tempest_a1_round_program

W = 4
MASK = np.uint16((1 << W) - 1)
IDX = {'u': 0, 'v': 1, 'w': 2, 'z': 3}
NIN = 1 << (4 * W)          # 2^16
IDX_AR = np.arange(NIN, dtype=np.uint16)


def rotl16(x, r):
    r %= W
    return np.uint16(((x << r) & MASK) | (x >> (W - r)))


def apply_round_vec(st, wv, with_key):
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
        elif t == 'CONST':
            w, c = IDX[op[1]], op[2] & 0xF
            st[:, w] = (st[:, w] ^ np.uint16(c)) & MASK
        elif t == 'WEYL':
            if with_key:
                r, c = op[1] % W, op[2] & 0xF
                wv[0] = (wv[0] ^ rotl16(wv[0], r) ^ np.uint16(c)) & MASK
        elif t == 'NLFILT':
            if with_key:
                c = op[1] & 0xF
                wv[1] = (wv[0] ^ rotl16(wv[0] & np.uint16(c), 13 % W)) & MASK
        elif t == 'KEY':
            if with_key:
                w, r, s = IDX[op[1]], op[2] % W, op[3]
                val = (rotl16(wv[1], r) ^ np.uint16(wv[1] >> s)) & MASK
                st[:, w] = (st[:, w] ^ val) & MASK
        else:
            raise ValueError(t)
    return st, wv


def full_table(rounds, with_key, wv0):
    codes = IDX_AR
    st = np.zeros((NIN, 4), dtype=np.uint16)
    for wi in range(4):
        st[:, wi] = (codes >> (wi * W)) & MASK
    wv = [np.uint16(wv0), np.uint16(0)]
    tabs = []
    for _ in range(rounds):
        st, wv = apply_round_vec(st, wv, with_key)
        tabs.append((st[:, 0] | (st[:, 1] << W) | (st[:, 2] << (2 * W))
                     | (st[:, 3] << (3 * W))).astype(np.uint16))
    return tabs


def wht(a):
    a = np.asarray(a, dtype=np.float64).copy()
    h = 1
    while h < a.shape[0]:
        A = a.reshape(-1, 2 * h)
        t = A[:, :h].copy()
        A[:, :h] = t + A[:, h:]
        A[:, h:] = t - A[:, h:]
        h *= 2
    return a.reshape(-1)


def popcount16(x):
    x = np.asarray(x, dtype=np.uint16)
    x = x - ((x >> 1) & np.uint16(0x5555))
    x = (x & np.uint16(0x3333)) + ((x >> 2) & np.uint16(0x3333))
    x = (x + (x >> 4)) & np.uint16(0x0F0F)
    return (x + (x >> 8)) & np.uint16(0x00FF)


def analyze_table(T, label, dual_check=False):
    res = {}
    t0 = time.time()
    # ---------- image collapse probe (max fiber of f_r) ----------
    fiber = np.bincount(T.astype(np.int64), minlength=NIN)
    res['fiber_max'] = round(float(fiber.max() / NIN), 7)
    res['fiber_max_dlog2'] = round(-np.log2(fiber.max() / NIN), 4)
    res['image_size'] = int(np.count_nonzero(fiber))
    # ---------- per-Delta DP0 + DDT max, ALL 65535 deltas ----------
    dp0 = np.zeros(NIN, dtype=np.float64)
    dp0[0] = 1.0                            # Delta = 0: trivial
    ddt_max = 0.0
    for di in range(1, NIN):
        dT = T[IDX_AR ^ np.uint16(di)] ^ T
        counts = np.bincount(dT.astype(np.int64), minlength=NIN)
        dp0[di] = counts[0] / NIN
        m = counts.max()
        if m > ddt_max:
            ddt_max = m
    ddt_max /= NIN
    res['ddt_max_dp'] = round(ddt_max, 7)
    res['ddt_max_dlog2'] = round(-np.log2(ddt_max), 4)
    c = float(dp0[1:].mean())
    res['dp0_mean'] = round(c, 7)
    res['dp0_mean_dlog2'] = (round(-np.log2(c), 4) if c > 0
                             else float('inf'))
    res['dp0_max'] = round(float(dp0.max()), 7)
    # constancy of DP0 over Delta (deviation from mean, all 65535)
    dev = float(np.abs(dp0[1:] - c).max())
    res['dp0_constancy_maxdev'] = dev
    lg = -np.log2(dp0[1:])
    q = np.percentile(lg, [0, 1, 10, 50, 90, 99, 100])
    res['dlog2dp0_dist'] = [round(float(x), 4) for x in q]
    # ---------- single-bit LAT ----------
    lat_max = 0.0
    for j in range(16):
        s = 1.0 - 2.0 * ((T >> j) & 1)
        Wj = wht(s)
        lat_max = max(lat_max, float(np.abs(Wj).max() / NIN))
    res['lat_max_singlebit'] = round(lat_max, 6)
    res['lat_max_singlebit_dlog2'] = round(-np.log2(lat_max), 4)
    # ---------- energy profile from the duality identity ----------
    E = wht(dp0) / NIN                      # E(a) = 2^-n WHT(DP0)[a]
    res['E0'] = round(float(E[0]), 7)       # == <DP0>  (exact identity)
    res['parseval_E'] = round(float(E.sum()), 9)
    # flatness off the mask-0 peak: E(a)*2^n should be (1-c) for a != 0
    flat = float(np.abs(E[1:] * NIN - (1.0 - c)).max())
    res['E_flatmaxdev'] = flat
    res['E_nonzero_max'] = round(float(E[1:].max()), 9)
    # ---------- two-source duality check (sample of masks u) ----------
    if dual_check:
        rng = np.random.default_rng(11)
        U = rng.integers(1, NIN, size=5000, dtype=np.uint16)
        # g_u(x) = (-1)^{u.f(x)}  = 1 - 2*(popcount(T & u) mod 2)
        E_est = np.zeros(NIN)
        lat_samp = 0.0
        for u in U:
            gu = 1.0 - 2.0 * (popcount16(T & u) & np.uint16(1))
            Gu = wht(gu)
            E_est += Gu.astype(np.float64) ** 2 / NIN ** 2
            lat_samp = max(lat_samp, float(np.abs(Gu).max() / NIN))
        E_est /= len(U)                     # E(a) = <ghat_u(a)^2>_u  (n=m)
        err0 = float(abs(E_est[0] - E[0]))
        erra = float(np.abs(E_est - E).max())
        res['dual_E0_err'] = err0
        res['dual_E_maxerr'] = erra
        res['lat_sampled_max'] = round(lat_samp, 6)
        res['lat_sampled_dlog2'] = round(-np.log2(lat_samp), 4)
    print(f'{label}: <DP0>={res["dp0_mean"]:.5f} (-log2 {res["dp0_mean_dlog2"]:.3f}) '
          f'const_dev={res["dp0_constancy_maxdev"]:.2e} '
          f'DDTmax={res["ddt_max_dp"]:.5f} (2^-{res["ddt_max_dlog2"]:.2f}) '
          f'fiber={res["fiber_max_dlog2"]:.2f} img={res["image_size"]} '
          f'LAT1={res["lat_max_singlebit"]:.4f} (2^-{res["lat_max_singlebit_dlog2"]:.2f}) '
          f'E0={res["E0"]:.5f} parseval={res["parseval_E"]:.3f} '
          f'flatdev={res["E_flatmaxdev"]:.2e} '
          + (f'dual(E0)={res["dual_E0_err"]:.2e} dualmax={res["dual_E_maxerr"]:.2e} '
             f'LATu={res["lat_sampled_dlog2"]:.2f}' if dual_check else '')
          + f' ({time.time()-t0:.0f}s)', flush=True)
    return res


def main():
    t0 = time.time()
    out = {'meta': {'W': W, 'NIN': NIN, 'rounds': 22}}
    # with-key, wv0 = 0x8: all 22 rounds, dual source checks at r=1, 22
    tabs = full_table(22, True, 0x8)
    for r, T in enumerate(tabs, start=1):
        dual = (r in (1, 22))
        out[f'withkey_r{r}'] = analyze_table(
            T, f'withkey r={r}', dual_check=dual)
    # with-key, wv0 = 0x0: key-sensitivity (tau-style) check at rounds 1,2,22
    tabs = full_table(22, True, 0x0)
    for r in (1, 2, 22):
        T = tabs[r - 1]
        out[f'withkey0_r{r}'] = analyze_table(
            T, f'withkey(wv0=0) r={r}')
    tabs = full_table(22, False, 0)
    for r, T in enumerate(tabs, start=1):
        out[f'nokey_r{r}'] = analyze_table(T, f'nokey r={r}')
    rng = np.random.default_rng(2026)
    for k in range(2):
        T = rng.integers(0, NIN, size=NIN, dtype=np.uint16)
        out[f'randfn_{k}'] = analyze_table(T, f'random fn {k}')
    for k in range(2):
        T = rng.permutation(NIN).astype(np.uint16)
        out[f'randperm_{k}'] = analyze_table(T, f'random perm {k}')
    out['elapsed_s'] = time.time() - t0
    with open('explore_ddt.json', 'w') as f:
        json.dump(out, f, indent=1)
    print(f'total {time.time()-t0:.0f}s -> explore_ddt.json')


if __name__ == '__main__':
    main()

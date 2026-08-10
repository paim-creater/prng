# -*- coding: utf-8 -*-
"""min_shadow_rank.py — exact min polar-rank search for the quadratic
shadow via alternating bilinear optimization.

rank(B_Delta) = n - dim ker(B_Delta).  For fixed k:  B_Delta k = 0 is
LINEAR in Delta  (B_Delta = A + sum_i Delta_i C_i).  Alternating:
  (1) pick random k, solve M_k . Delta = A k  -> candidate low-rank Deltas
  (2) fix the best Delta, compute its full kernel, use kernel vectors
      as new k's
Iterate.  Sanity-check on W=4 (known true min rank = 3), then W=8.
The polar form is extracted by symbolic differentiation of the shadow
program: for each AND gate g and each input bit i, C_i = d/dDelta_i of
the linear-in-Delta part of D_Delta.
"""
import numpy as np
import json, time

from cipher import (tempest_a1_round_program, State, apply_round, U64)

OPS = tempest_a1_round_program()


def truncate_at_levels(ops, k, include_premix=True):
    a3_idx = [i for i, op in enumerate(ops) if op[0] == 'A3']
    snap_idx = [i for i, op in enumerate(ops) if op[0] == 'SNAP']
    first_level = min(i for i in snap_idx if i > max(a3_idx))
    level_starts = [i for i in snap_idx if i >= first_level][:4]
    cut = level_starts[k] if k < 4 else len(ops)
    if not include_premix:
        cut = min(cut, min(a3_idx))
    return ops[:cut]


def polar_matrices(W, ops):
    """Return (A, C) where the polar form B_Delta = A + sum_i Delta_i C_i.
    A = linear-part matrix (A = 0 for quadratic rounds, since D_0 = 0);
    C_i = derivative wrt Delta bit i, with C_i[j] = n-bit column value
    D_{e_i}(e_j) ^ D_{e_i}(0).
    Extracted by exact evaluation at unit states (2*(n+1) round evals),
    using the DSL interpreter (correct W-bit rotations)."""
    n = 4 * W
    MK = (1 << W) - 1

    def D_at(delta_int, x_int):
        # D_Delta(x) = Phi(x^delta) ^ Phi(x), single state
        words = [U64((x_int >> (wi * W)) & MK) for wi in range(4)]
        wv = U64(0)
        st0 = State([w for w in words], wv, W=W)
        st1 = State([w ^ U64((delta_int >> (wi * W)) & MK) for wi, w in
                     enumerate(words)], wv, W=W)
        apply_round(ops, st0)
        apply_round(ops, st1)
        r0 = 0
        r1 = 0
        for wi in range(4):
            r0 |= int(st0.words[wi]) << (wi * W)
            r1 |= int(st1.words[wi]) << (wi * W)
        return r0 ^ r1

    # B_Delta = sum_j s_j * (D_Delta(e_j) ^ D_Delta(0))  -- the linear part
    # matrix M has columns M[j] = D_Delta(e_j) ^ D_Delta(0).
    # For A (Delta-independent): Delta = 0 -> D_0 = 0 function, so A = 0!
    # For C_i: C_i is the matrix whose columns are d/dDelta_i of
    # (D_Delta(e_j) ^ D_Delta(0)) at Delta = 0, i.e.
    #   C_i[:, j] = D_{e_i}(e_j) ^ D_{e_i}(0).   C_i[j] = n-bit int column.
    A = [0] * n
    C = [[0] * n for _ in range(n)]
    for j in range(n):
        for i in range(n):
            # D_{e_i}(e_j) ^ D_{e_i}(0)
            Dej = D_at(1 << i, 1 << j)
            De0 = D_at(1 << i, 0)
            C[i][j] = Dej ^ De0
    return A, C


def gf2_rank(rows):
    n = len(rows)
    rows = [int(r) for r in rows]
    rank = 0
    for col in range(n):
        piv = None
        for i in range(rank, n):
            if (rows[i] >> col) & 1:
                piv = i
                break
        if piv is None:
            continue
        rows[rank], rows[piv] = rows[piv], rows[rank]
        for i in range(n):
            if i != rank and ((rows[i] >> col) & 1):
                rows[i] ^= rows[rank]
        rank += 1
    return rank


def solve_linear(Amat, b):
    """Solve sum_i Amat[r, i] * x_i = b[r] over GF(2), all r.
    Returns a NONZERO solution (first free variable = 1), or None if the
    only solution is x = 0 (or the system is inconsistent)."""
    n = len(b)
    rows = [[int(Amat[r][i]) for i in range(n)] + [int(b[r])] for r in range(n)]
    rank = 0
    pivots = []          # (row, col)
    for col in range(n):
        piv = None
        for i in range(rank, n):
            if rows[i][col]:
                piv = i
                break
        if piv is None:
            continue
        rows[rank], rows[piv] = rows[piv], rows[rank]
        pivots.append((rank, col))
        for i in range(n):
            if i != rank and rows[i][col]:
                rows[i] = [a ^ bb for a, bb in zip(rows[i], rows[rank])]
        rank += 1
    # consistency check (non-homogeneous case)
    for i in range(rank, n):
        if not any(rows[i][:-1]) and rows[i][-1]:
            return None
    pivot_cols = {c for _, c in pivots}
    free = [c for c in range(n) if c not in pivot_cols]
    if not free:
        # no free variables: unique solution
        sol = [0] * n
        for r, c in pivots:
            s = rows[r][-1]
            for j in range(n):
                if j != c and rows[r][j]:
                    s ^= sol[j]
            sol[c] = s
        return sol if any(sol) else None
    # nonzero solution: set first free variable to 1, back-substitute
    sol = [0] * n
    sol[free[0]] = 1
    for r, c in reversed(pivots):
        s = rows[r][-1]
        for j in range(n):
            if j != c and rows[r][j]:
                s ^= sol[j]
        sol[c] = s
    return sol


def rank_of_delta(W, ops, delta):
    n = 4 * W
    MK = (1 << W) - 1

    def D_at(delta_int, x_int):
        words = [U64((x_int >> (wi * W)) & MK) for wi in range(4)]
        wv = U64(0)
        st0 = State([w for w in words], wv, W=W)
        st1 = State([w ^ U64((delta_int >> (wi * W)) & MK) for wi, w in
                     enumerate(words)], wv, W=W)
        apply_round(ops, st0)
        apply_round(ops, st1)
        r0 = 0
        r1 = 0
        for wi in range(4):
            r0 |= int(st0.words[wi]) << (wi * W)
            r1 |= int(st1.words[wi]) << (wi * W)
        return r0 ^ r1

    cols = [D_at(delta, 1 << j) ^ D_at(delta, 0) for j in range(n)]
    return gf2_rank(cols), cols


def min_rank_search(W, ops, n_restarts=200, iters=20):
    n = 4 * W
    rng = np.random.default_rng(2026)
    best_rank = n + 1
    best_delta = None
    # precompute the C_i matrices (each column j: C_i[j])
    t0 = time.time()
    A, C = polar_matrices(W, ops)
    print(f'  polar matrices built ({time.time()-t0:.0f}s)')
    # M_k . Delta = A k:  M_k has rows i: (C_i k)  -- the i-th equation is
    # sum_j C_i[j] k_j * Delta_i = (A k)_i... careful with conventions.
    # B_Delta k = A k + sum_i Delta_i (C_i k) = 0  ->  sum_i Delta_i C_i k = A k.
    # So the system in Delta:  for each output bit row r:
    #   sum_i Delta_i (C_i k)_r = (A k)_r.
    # M_k[r, i] = (C_i k)_r,  b[r] = (A k)_r.
    def system_from_k(k):
        # (C_i k)_r = bit r of XOR_{j: k_j=1} C_i[j]
        kcols = [j for j in range(n) if (k >> j) & 1]
        if not kcols:
            return None, None
        Mk = np.zeros((n, n), dtype=np.int64)
        for i in range(n):
            sel = C[i]
            acc = 0
            for j in kcols:
                acc ^= sel[j]
            for r in range(n):
                Mk[r, i] = (acc >> r) & 1
        b = np.zeros(n, dtype=np.int64)
        acc = 0
        for j in kcols:
            acc ^= A[j]
        for r in range(n):
            b[r] = (acc >> r) & 1
        return Mk, b

    for restart in range(n_restarts):
        if n < 56:
            k = int(rng.integers(0, 1 << n))
        else:
            # n up to 128: random bytes
            nb = (n + 7) // 8
            k = int.from_bytes(rng.bytes(nb), 'little') & ((1 << n) - 1)
        if k == 0:
            continue
        for it in range(iters):
            Mk, b = system_from_k(k)
            sol = solve_linear(Mk, b)
            if sol is None:
                break
            delta = sum(sol[i] << i for i in range(n))
            if delta == 0:
                break
            r, _ = rank_of_delta(W, ops, delta)
            if r < best_rank:
                best_rank = r
                best_delta = delta
                print(f'    restart {restart}: new best rank {r} '
                      f'(delta {delta:#x}) ({time.time()-t0:.0f}s)', flush=True)
            if r <= 1:
                return best_rank, best_delta
            # next k: a kernel vector of B_delta
            # kernel: solve B_delta . k = 0  (B_delta rows as GF2 vectors)
            _, cols = rank_of_delta(W, ops, delta)
            # B_delta has rows = cols^T; kernel of the matrix with columns cols
            # find k != 0 with sum_j cols[j] * k_j = 0 -> linear system
            k = kernel_vector(cols, rng)
            if k is None:
                break
    return best_rank, best_delta


def kernel_vector(cols, rng):
    """Find a nonzero k with sum_j cols[j] k_j = 0 (kernel of matrix)."""
    n = len(cols)
    rows = [[int((cols[j] >> i) & 1) for j in range(n)] for i in range(n)]
    rank = 0
    pivots = []
    for col in range(n):
        piv = None
        for i in range(rank, n):
            if rows[i][col]:
                piv = i
                break
        if piv is None:
            continue
        rows[rank], rows[piv] = rows[piv], rows[rank]
        pivots.append((rank, col))
        for i in range(n):
            if i != rank and rows[i][col]:
                rows[i] = [a ^ b for a, b in zip(rows[i], rows[rank])]
        rank += 1
    free = [c for c in range(n) if c not in {c_ for _, c_ in pivots}]
    if not free:
        return None
    f = free[0]
    k = [0] * n
    k[f] = 1
    # back-substitute
    for r, c in reversed(pivots):
        v = rows[r][-1] if False else 0
        # equation r: sum_j rows[r][j] k_j = 0 -> k_c = sum_{j != c} rows[r][j] k_j
        s = 0
        for j in range(n):
            if j != c and rows[r][j]:
                s ^= k[j]
        k[c] = s
    return sum(k[j] << j for j in range(n))


def main():
    out = {}
    for W, label in [(4, 'W4'), (8, 'W8')]:
        ops = truncate_at_levels(OPS, 0, include_premix=True)
        print(f'{label} shadow min-rank search...')
        t0 = time.time()
        best_rank, best_delta = min_rank_search(W, ops, n_restarts=120, iters=25)
        out[label] = {'min_rank': int(best_rank),
                      'delta': hex(int(best_delta)) if best_delta else None,
                      'secs': round(time.time() - t0, 1)}
        print(f'{label}: min polar rank = {best_rank} (delta {hex(best_delta)}) '
              f'({time.time()-t0:.0f}s)', flush=True)
    with open('min_shadow_rank.json', 'w') as f:
        json.dump(out, f, indent=1)
    print('done -> min_shadow_rank.json')


if __name__ == '__main__':
    main()

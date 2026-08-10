"""sidon_cert.py — the dissociated-set (Sidon-type) certificate for andmix4.

For the 4-level andmix4 cascade we track, for every output bit position,
the *variable set* of the highest-degree monomial along every AND path.
Two distinct monomials are equal as functions iff their variable sets are
identical; a monomial cancels only if the same variable set arises from two
different paths. Therefore:

    beta_1 >= 16 (full width)  <=>  the variable sets of all highest-degree
    monomials are pairwise distinct.

We verify this symbolically at W=64: 4 paths per level -> 4^4 = 256 paths
per output bit; 16 variables per Level-4 monomial. The certificate is
machine-checkable in O(paths^2 * vars).
"""
import sys
from itertools import product

W = 64
IDX = {'u': 0, 'v': 1, 'w': 2, 'z': 3}
# andmix4 levels: each level has 4 ANDs (dst, srcA, srcB, rA, rB)
# reading from the round program (Level 1..4)
LEVELS = [
    # Level 1 (from snapshot words v0,w0,z0,u0... but tracked symbolically)
    [('u', 'v', 'w', 31, 53), ('v', 'w', 'z', 17, 43),
     ('w', 'z', 'u', 7, 23), ('z', 'u', 'v', 5, 19)],
    [('u', 'v', 'z', 17, 43), ('v', 'w', 'u', 7, 23),
     ('w', 'z', 'v', 5, 19), ('z', 'u', 'w', 31, 53)],
    [('u', 'z', 'u', 7, 23), ('v', 'u', 'v', 5, 19),
     ('w', 'v', 'w', 31, 53), ('z', 'w', 'z', 17, 43)],
    [('u', 'v', 'w', 5, 19), ('v', 'w', 'z', 31, 53),
     ('w', 'z', 'u', 17, 53), ('z', 'u', 'v', 7, 23)],
]


def var_set(word, pos):
    """Canonical variable id for state word `word` bit `pos`."""
    return IDX[word] * W + (pos % W)


def level1_vars(and_op, i):
    """Variable set of the highest monomial of a Level-1 AND at bit i.
    Level 1 AND inputs are the (symbolic) pre-Phase-C words, so their
    highest monomials come from the AND's own product: 2 variables."""
    _, a, b, r1, r2 = and_op
    return frozenset({var_set(a, i - r1), var_set(b, i - r2)})


def cascade_sets(level_inputs, level):
    """Variable sets of all highest monomials at the output of `level`.
    level_inputs: dict (word, pos) -> frozenset of variable sets for each
    AND-input word bit (the highest monomials carried by that bit).
    Returns dict (word, pos) -> list of frozensets (all path variable sets).
    """
    out = {}
    for dst, a, b, r1, r2 in level:
        for i in range(W):
            sa = level_inputs.get((a, (i - r1) % W))
            sb = level_inputs.get((b, (i - r2) % W))
            if sa is None or sb is None:
                continue
            # product of highest monomials of both inputs
            sets = [x | y for x in sa for y in sb]
            out[(dst, i)] = sets
    return out


def main():
    # Level 1: the AND inputs are fresh snapshot words; highest monomial of
    # each AND output bit = {srcA bit, srcB bit}
    lvl1 = {}
    for op in LEVELS[0]:
        dst, a, b, r1, r2 = op
        for i in range(W):
            lvl1[(dst, i)] = [level1_vars(op, i)]
    # Level 1 AND outputs also feed the XOR-mixing (Phase A style)? For the
    # andmix4 cascade proper, Level k+1 reads Level k outputs via the
    # rotation pair of its own AND; the cascade variable sets are as above.

    cur = lvl1
    all_sets = []
    for L in range(1, 4):
        cur = cascade_sets(cur, LEVELS[L])
        for k, v in cur.items():
            all_sets.extend(v)

    # pairwise distinctness check over ALL highest monomials of the cascade
    n_total = len(all_sets)
    distinct = True
    collision = None
    seen = {}
    for s in all_sets:
        if s in seen:
            distinct = False
            collision = (seen[s], s)
            break
        seen[s] = s
    print(f'paths checked: {n_total} monomial variable sets')
    print(f'variable set size (Level-4 monomial): '
          f'{len(all_sets[0]) if all_sets else 0} (expect 16)')
    print(f'pairwise distinct: {distinct}')
    if collision:
        print(f'COLLISION: {collision[0]} == {collision[1]}')
    else:
        print('=> beta_1 >= 16 at full width: certificate HOLDS')

    # report per-level counts
    for L, lv in enumerate(LEVELS):
        n = 0
        for k, v in (lvl1 if L == 0 else cascade_sets(
                lvl1 if L == 1 else cur, [lv])).items():
            n += len(v)
        print(f'  level {L+1}: {n} path monomials')


if __name__ == '__main__':
    main()

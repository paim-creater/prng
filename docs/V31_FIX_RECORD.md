# v3.1 Linear-Part Fix Record (2026-08-10)

## The defect (diagnosed, not guessed)

The v3.1 dead-key predecessor's Phase B linear part had, for each of
the four words,

    u = u0 ^ rotl(v0,5) ^ rotl(w0,13) ^ rotl(z0,25)      (and symmetrically)

i.e. **four terms per row** (self + three rotations). Over GF(2) the
row sums vanish (1+1+1+1 = 0), so the **all-ones vector is in the
kernel** of the linear part. Measured:

| Quantity | v3.1 (original) | v3.1 (fixed) |
|---|---|---|
| GF(2) rank of the linear part | **248 / 256** | **256 / 256** |
| L^64 applied to a unit diff | **0** (collapse direction) | nonzero |
| L^128 applied to a unit diff | 0 | nonzero |
| Dieharder rgb_lagged_sum | ntup=7 **WEAK** (p=0.0002); archived: ntup=3,7 **FAILED** (p=0) | **all ntup 0–24 PASSED** |
| Dieharder marsaglia_tsang_gcd | **WEAK** (p=0.0015, 0.00027); archived: **FAILED** (p=0) | **PASSED** (p=0.036, 0.906) |
| Full `dieharder -a` suite | — | **111 PASSED, 0 FAILED, 3 WEAK** (multiple-comparison noise, see below) |

**The 3 WEAK are noise, not structure.** The full suite showed
`rgb_bitdist ntup=8` (p=0.999), `rgb_lagged_sum ntup=22` (p=0.0002)
and ntup=24 (p=0.9999) as WEAK. Re-running exactly those tests on a
fresh stream (different seed, 1.1 GB) gives **all PASSED**
(`rgb_lagged_sum` ntup=20–24: p=0.29–0.83; `rgb_bitdist` ntup=8:
p=0.47). With 111 tests, ~0.1 tests are expected below p=0.001 and
~0.1 above p=0.999 by chance; observing one of each is unremarkable,
and their non-reproduction under a new seed confirms randomness.

The all-ones kernel means the difference "all 1s" is annihilated by
the linear part — the state never mixes in that direction, leaving
detectable lag structure in the output (what `rgb_lagged_sum` and
`marsaglia_tsang_gcd` measure).

## The fix (minimal, diagnosis-driven)

Drop one rotation per word in Phase B; each word is now self plus two
rotations (three terms, odd row sum):

    u = u0 ^ rotl(v0,5) ^ rotl(w0,13)
    v = v0 ^ rotl(w0,11) ^ rotl(z0,19)
    w = w0 ^ rotl(z0,23) ^ rotl(u0,9)
    z = z0 ^ rotl(u0,17) ^ rotl(v0,27)

The rotation set (5,13 / 11,19 / 23,9 / 17,27) is a subset of the
original; pre-mix, andmix4, the output function, and the 22-round
initialization are unchanged. The fix restores full rank and removes
the collapse direction; everything else about v3.1 is untouched.

## Why this is the right fix (and what it is not)

- It is **not** "add more rounds until the tests pass": the defect is
  structural and located — the linear part's kernel — and the fix is
  the minimal change that removes it.
- It matches the paper's own methodology: the two-layer polar-rank
  barrier and the decomposition bound exist because *structure*, not
  sample size, decides differential behaviour; the same principle
  applies here.
- The remaining ~60/256-bit single-path snowball (one particular input
  difference after 22 rounds) is *not* the failure mechanism: the
  fixed stream passes the statistical suite, and snowball saturation
  for individual differences is normal for AND-RX designs (only the
  kernel/collapse structure was pathological).

## Reproduction

```bash
gcc -O3 -o v31_fixed_gen v31_fixed_gen.c
./v31_fixed_gen > v31_fixed.bin &        # let it write ~1.4 GB
dieharder -g 201 -f v31_fixed.bin -a     # full suite
```

Log: `data/dieharder_v31_fixed_20260810.txt`.

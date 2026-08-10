# data/ — statistical test logs

Raw logs of every statistical test referenced in the paper. All runs
are on the full-width C implementation of Algorithm 1 (unaffected by
the W=4 interpreter issue).

| File | Test | Result |
|---|---|---|
| `tempest_nist_results_20260704.txt` | NIST SP 800-22 (100 seq × 10⁶ bits) | 15/15 families pass |
| `bigcrush_tempest_v3.log` | TestU01 BigCrush (106 tests) | all pass |
| `crush_tempest_v3.log` | TestU01 Crush | all pass |
| `practrand_tempest_v3_1tb.log` | **PractRand, 1 TiB** (354 result blocks) | no anomalies |
| `testu01/` | additional TestU01 runs | see logs |
| `cryptanalysis/`, `sat/` | W=4 analysis artefacts | see logs |
| `dieharder_v31_rebuilt_20260810.txt` | **v3.1 rebuild Dieharder run (2026-08-10)**: WEAK anomalies at `rgb_lagged_sum` ntup=7 and `marsaglia_tsang_gcd` — directionally consistent with the archived FAILED (p=0) control, weaker because the generator is a rebuild (`code/v31_gen.c`), not the archived binary | negative control |
| `dieharder_v31_fixed_20260810.txt` | **v3.1 fixed Dieharder run (2026-08-10)**: full `-a` suite on the Phase-B-fixed generator — 111 PASSED, 0 FAILED, 3 WEAK (confirmed noise by fresh-seed re-test; see `docs/V31_FIX_RECORD.md`) | fix verification |
| `results/` (repo root) | historical reports, incl. the v3.1 Dieharder failure control (`rgb_lagged_sum` at p=0 — reproduced and *explained* by the framework, not hidden) | control |

## Honest notes

- The v3.1 negative control: the dead-key design shows detectable
  structure (archived log: `rgb_lagged_sum` ntup=3,7 FAILED at p=0;
  rebuild: WEAK at ntup=7 and `marsaglia_tsang_gcd`), which the
  calibrated stack detects structurally (a₁ = 0, τ = 0) in
  milliseconds — and which Algorithm 1 does not exhibit (all statistical
  suites pass).
- Statistical passing is *necessary, not sufficient*: the paper makes
  no security claim beyond its stated metrics. These logs evidence
  output quality; the structural metrics live in `engine/`.
- Large raw PractRand input binaries (256 MB each) are intentionally
  not committed (GitHub size limits); the full 1 TiB log is.

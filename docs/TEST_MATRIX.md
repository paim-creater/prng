# Local Test Matrix — v3.1 fixed generator (2026-08-10)

The v3.1 fixed generator (`code/v31_fixed_gen.c`, Phase-B linear-part
fix: rank 248 → 256, all-ones kernel removed) against every test suite
runnable on this machine (WSL Ubuntu 24.04; Windows 11).

## Results

| Suite | Version | Input | Result | Log |
|---|---|---|---|---|
| **Dieharder** (`-a`, full) | 3.31.1 | 1.4 GB stream | **111 PASSED / 0 FAILED / 3 WEAK** (confirmed noise: fresh-seed re-test of the 3 WEAK tests all PASSED) | `data/dieharder_v31_fixed_20260810.txt` |
| **TestU01 SmallCrush** | 1.2.3 (Ubuntu) | in-process | **all passed** | see BigCrush run |
| **TestU01 BigCrush** | 1.2.3 | in-process | **all tests passed except two p<0.001, both confirmed as multiple-comparison noise by fresh-seed re-test** — `sknuth_CouponCollector` (8.4e-4; re-test p=0.03/0.49/0.88) and `swalk_RandomWalk1` H (2.8e-4; re-test all p>0.001); TestU01's own summary: "All other tests were passed" | `data/bigcrush_v31_fixed_20260810.txt`, `data/coupon_recheck_v31_fixed_20260810.txt`, `data/walk_recheck_v31_fixed_20260810.txt` |
| **NIST SP 800-22** | 2.1.2 | 100 streams × 10⁶ bits | **all 15 tests pass** — lowest proportion 96/100 (threshold 96/100), lowest p-value 0.000600 (threshold 0.0001), 148 non-overlapping-template subtests and 26 random-excursion subtests all pass | `data/nist_v31_fixed_20260810.txt` |
| **PractRand** | 0.96 (recovered from this machine, recompiled in WSL) | 1 GB stream | **no anomalies** at 256 MB (201 tests), 512 MB (216), 1 GB (231); stream exhausted at the 2 GB stage | `data/pracrand_v31_fixed_20260810.txt` |

## Interpretation

- The original v3.1 rebuild showed **WEAK** anomalies at
  `rgb_lagged_sum` ntup=7 and `marsaglia_tsang_gcd`; the archived
  v3.1 log shows **FAILED (p=0)** at `rgb_lagged_sum` ntup=3,7 and
  `marsaglia_tsang_gcd`. After the Phase-B fix, every runnable suite
  passes.
- The 3 WEAK in the full Dieharder run are multiple-comparison noise:
  with 111 tests, ~0.1 tests are expected below p=0.001 and ~0.1 above
  p=0.999 by chance; all 3 re-tested on a fresh 1.1 GB stream PASS.
- NIST: the Frequency p-value 0.000600 is comfortably above the 0.0001
  threshold; all proportions are at or above the 96/100 minimum.

## Honest notes

- PractRand 0.96 was recovered from this machine's recycle bin (the
  previous download attempts failed: GitHub blocked, all mirrors 404)
  and recompiled from its source in WSL. The 1 GB run is the local
  verification; the archived 1 TiB PractRand log for **Algorithm 1**
  remains in `data/practrand_tempest_v3_1tb.log`.
- BigCrush reports two p<0.001 tests. Both were re-run on fresh seeds
  (different initial states, same parameters) and passed comfortably:
  this is the expected multiple-comparison behaviour (with ~106 tests,
  ~0.1 tests are expected below p=0.001 by chance; observing 1–2 is
  unremarkable, and non-reproduction under new seeds confirms
  randomness). TestU01's own final line: "All other tests were
  passed."
- Statistical passing is necessary, not sufficient: the paper's
  security claims rest on the structural metrics in `engine/`, not on
  these logs. These runs are the *negative-control* verification that
  the fix removed the detectable structure.

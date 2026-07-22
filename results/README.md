# Test Results

## Tempest v3

| Test | File | Status |
|------|------|--------|
| NIST SP 800-22 (100×10⁶ bits) | [`tempest_nist_results_20260704.txt`](tempest_nist_results_20260704.txt) | ✅ 15/15 PASS |
| TestU01 SmallCrush | [`smallcrush_tempest_v3.log`](smallcrush_tempest_v3.log) | ✅ PASS |
| TestU01 Rabbit | [`rabbit_tempest_v3.log`](rabbit_tempest_v3.log) | ✅ PASS |
| TestU01 Alphabit | [`alphabit_tempest_v3.log`](alphabit_tempest_v3.log) | ✅ PASS |
| TestU01 Crush | [`crush_tempest_v3_20260704.log`](crush_tempest_v3_20260704.log) | ✅ PASS |
| TestU01 BigCrush | [`bigcrush_tempest_v3_20260704.log`](bigcrush_tempest_v3_20260704.log) | ✅ PASS |
| PractRand 1 TiB | [`practrand_tempest_v3_1tb_20260705.log`](practrand_tempest_v3_1tb_20260705.log) | ✅ PASS (0 anomalies) |

## ADC-Bolt

| Test | File | Status |
|------|------|--------|
| NIST SP 800-22 | [`adcbolt_nist_report.txt`](adcbolt_nist_report.txt) | ✅ 15/15 PASS |
| TestU01 SmallCrush | [`smallcrush_adcbolt.log`](smallcrush_adcbolt.log) | ✅ PASS |
| TestU01 Rabbit | [`rabbit_adcbolt.log`](rabbit_adcbolt.log) | ✅ PASS |
| TestU01 Alphabit | [`alphabit_adcbolt.log`](alphabit_adcbolt.log) | ✅ PASS |
| TestU01 Crush | [`crush_adcbolt.log`](crush_adcbolt.log) | ✅ PASS |
| TestU01 BigCrush | [`bigcrush_adcbolt.log`](bigcrush_adcbolt.log) | ✅ PASS |
| PractRand 1 TiB | [`practrand_adcbolt.log`](practrand_adcbolt.log) | ✅ PASS |

## Automated Cryptanalysis (Tempest v3)

These results are described in the paper (§7 实验验证, Table 4). Full cryptanalysis tools are available upon request.

| Analysis | Parameters | Result |
|----------|-----------|--------|
| Output differential probability | 2×10⁹ samples | Zero collisions |
| Differential path (1-round) | 5×10⁷ samples | Min weight 9/64 (14.1%) |
| Differential path (3-round) | 5×10⁷ samples | Min weight 11/64 (17.2%) |
| Linear bias scan | 2×10¹⁰ samples | max ε = 0.000444 |
| Avalanche test (1-round) | 10⁶ samples | 50.00% |
| Key sensitivity | 10⁵ samples | 49.98% |
| SAT solver (W=64, 1-round) | 10,240 variables | 0.01s (solvable, deg incomplete) |
| SAT solver (W=64, 22-round) | 219,904 variables | Unsolvable |

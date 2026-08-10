# engine/ — Python verification engine

Every metric, certificate, and audit script of the paper, with its JSON
result data. All scripts take no arguments; each prints its result and
writes/updates its `.json` dataset.

## Reproduce the paper's numbers

```bash
python cipher.py                    # bit-exact Algorithm-1 port (self-test)
python audit_true_algorithm1.py     # W=4 full-domain exact metrics
python min_shadow_rank.py           # polar matrices, ranks
python rank_certificate_demo.py     # W=64 rank-3 certificate
python readword_theorem.py          # Read-Word Theorem: 35 designs, 0 failures
python explore_decomp_bound.py      # decomposition bound, 0 violations
python explore_round_dp_curve.py    # exact 22-round W=4 curve
python explore_cascade_degree.py    # cascade degree law, W=64 certificate
python walsh_rank_dual.py           # Walsh-rank duality
python sat_attack_grid.py           # SAT preimage grid (pysat)
python trail_diff.py 8 2            # MILP trails (pulp)
python trail_lin.py                 # exact W=4 Walsh values
python state_attack.py inv          # output-function SAT inversion
python lin_scale.py 64 1 24         # W=64 linear balance (2^24/mask)
python diff_sum.py 6 24 64          # W=64 multi-round DP (2^24 pairs)
```

## Inventory (38 scripts)

### Core theory
`cipher.py` (bit-exact port), `min_shadow_rank.py`, `walsh_rank_dual.py`,
`readword_theorem.py`, `verify_readword_theorem.py` *(exploration-stage:
kept for the audit record — its construction bug motivated the final
dual column condition)*, `verify_barrier.py`, `rank_certificate_demo.py`,
`twosat_cert.py`, `sidon_cert.py`.

### Exact W=4 metrics and audits
`audit_true_algorithm1.py`, `audit_cascade_rank.py`, `audit_w8_tau.py`,
`cascade_full_domain.py`, `explore_round_dp_curve.py`,
`explore_decomp_bound.py`, `explore_state_image.py`,
`explore_cascade_degree.py`, `explore_invertibility.py`,
`test_aggregation_conjecture.py`, `test_shadow_rank_w8.py`,
`doubling_law_test.py`, `dp_nonlinearity.py`.

### Attack-surface audit (2026-08-09)
`trail_diff.py`, `trail_lin.py`, `state_attack.py`, `lin_scale.py`,
`diff_sum.py`, `diff_sum_w64.py`, `linear_cascade_w8.py`,
`sat_attack_grid.py`.

### Auxiliary / exploration
`explore_ddt.py`, `explore_wide.py`, `halfentropy_wide.py`,
`halfentropy_wide2.py`, `calibrate.py`, `tradeoff.py`,
`g_invert_check.py`, `g_injectivity_check.py` *(encoding-bug lesson:
the XNOR-clause pitfall, documented in `state_attack.py`)*.

## Dependencies

`numpy` (all), `pysat` (SAT scripts), `pulp` (MILP scripts). Python ≥ 3.10.

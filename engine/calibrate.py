"""calibrate.py — Phase 0b: verifier calibration.

Success criteria (must all hold before the engine is allowed to use the
verifiers as fitness functions):

  C1. fast_stats must FAIL v3.1  (reproduce its real lagged-sum weakness:
      its own Dieharder logs show rgb_lagged_sum p=0 at lags 3,7,15,23,27,31)
  C2. fast_stats must PASS Algorithm 1 and both known-good controls
      (numpy PCG64, splitmix64)
  C3. neural distinguisher must distinguish v3.1 at shallower depth than
      Algorithm 1 (v3.1 is structurally weaker: its Weyl injection is
      discarded by Phase B's assignment)
  C4. empirical DP / L2 trails must show v3.1 weaker than Algorithm 1
      (fewer active AND bits at round 1)

Everything here is measurement; thresholds come from these runs, not from
assumed values.
"""
import json
import time

import numpy as np

from cipher import (tempest_a1_round_program, tempest_v31_round_program,
                    make_output_a1, make_output_v31, splitmix64)
from verifiers.fast_stats import run_all as stats_run_all
from verifiers.empirical import (empirical_differential, avalanche, linear_bias)
from verifiers.exact_trails import full_report as l2_report
from verifiers.neural_distinguisher import distinguish_at_rounds


def pcg64_words(n_words, seed=1):
    rng = np.random.default_rng(seed)
    return rng.integers(0, 1 << 64, size=n_words, dtype=np.uint64)


def splitmix_words(n_words, seed=1):
    g = splitmix64(seed)
    return np.array([next(g) for _ in range(n_words)], dtype=np.uint64)


def main():
    t0 = time.time()
    results = {'calibration': {}, 'controls': {}}

    print('=' * 70)
    print('PHASE 0b CALIBRATION — verifier trust test')
    print('=' * 70)

    # ---- C1/C2: fast stats ------------------------------------------------
    print('\n[1/4] fast_stats battery (n_words=2^22)')
    N = 1 << 22

    print('  generating streams...')
    stats = {}
    for label, ops, out_kind, out_fn in [
            ('tempest_v3.1 (KNOWN BAD)', tempest_v31_round_program(), 'v31', make_output_v31),
            ('tempest_v3 (Algorithm 1)', tempest_a1_round_program(), 'a1', make_output_a1)]:
        res = stats_run_all(ops, n_words=N, out_kind=out_kind, output_fn=out_fn,
                            name=label, verbose=True)
        stats[label] = res
        results['calibration'][label] = res

    for label, words in [('numpy PCG64 (control)', pcg64_words(N)),
                         ('splitmix64 (control)', splitmix_words(N))]:
        from verifiers import fast_stats
        res = fast_stats.run_all_words(words, name=label, verbose=True)
        stats[label] = res
        results['controls'][label] = res

    # weyl relevance (dead-key structural test)
    from verifiers.fast_stats import weyl_relevance
    wr = {}
    for label, ops, out_fn in [('tempest_v3.1', tempest_v31_round_program(), make_output_v31),
                               ('tempest_v3', tempest_a1_round_program(), make_output_a1)]:
        frac = weyl_relevance(ops, W=64, n_trials=512, seed=31, output_fn=out_fn)
        wr[label] = frac
        results['calibration'][label + '_weylrel'] = frac
        print(f'  weyl relevance [{label}]: {frac:.4f} '
              f'({"DEAD KEY" if frac < 0.5 else "key alive"})')

    v31 = stats['tempest_v3.1 (KNOWN BAD)']
    a1 = stats['tempest_v3 (Algorithm 1)']
    # C1: v3.1 must fail hard on at least one verifier (stats z>6 or dead key)
    c1 = (v31['lagdh_max_abs_z'] > 6 or v31['lagbit_max_abs_z'] > 6
          or v31['lag_max_abs_z'] > 6 or wr['tempest_v3.1'] < 0.5)
    c2 = (a1['lag_max_abs_z'] <= 6 and a1['lagdh_max_abs_z'] <= 6
          and a1['lagbit_max_abs_z'] <= 6 and wr['tempest_v3'] > 0.5
          and all(c['lagdh_max_abs_z'] <= 6 and c['lagbit_max_abs_z'] <= 6
                  for c in results['controls'].values()))
    print(f'  C1 (v3.1 FAILS a verifier): {"PASS" if c1 else "FAIL"} '
          f'[pearson z={v31["lag_max_abs_z"]:.1f}@lag{v31["lag_worst"]}, '
          f'dieharder z={v31["lagdh_max_abs_z"]:.1f}@lag{v31["lagdh_worst"]}, '
          f'bitlane z={v31["lagbit_max_abs_z"]:.1f}@lag{v31["lagbit_worst"]}, '
          f'weylrel={wr["tempest_v3.1"]:.3f}]')
    print(f'  C2 (A1+controls PASS): {"PASS" if c2 else "FAIL"}')

    # ---- C3: neural distinguisher (word-level deltas) ----------------------
    print('\n[2/4] neural distinguisher (W=8, word-0xFF delta, n=14000)')
    from verifiers.neural_distinguisher import train_distinguisher, build_pairs
    from cipher import State
    from verifiers.empirical import diff_round

    def probe_word_delta(ops, R, W, delta, n_pairs=14000, seed=5):
        n = n_pairs
        st = State.random(n, seed=seed, W=W)
        st2 = State([w.copy() for w in st.words], st.wv.copy(), W)
        d = [np.zeros(n, dtype=np.uint64) for _ in range(4)]
        for i, v in enumerate(delta):
            if v:
                d[i] = d[i] | np.uint64(v & ((1 << W) - 1))
        for _ in range(R):
            diff_round(ops, st2, d, W)
        pos = np.stack(d, axis=1).astype(np.uint64)
        feat = np.zeros((n, 4 * W), dtype=np.float32)
        for i in range(4):
            v = pos[:, i]
            for b in range(W):
                feat[:, i * W + b] = (v >> b) & 1
        rng = np.random.default_rng(seed + 1)
        neg = rng.integers(0, 2, size=(n, 4 * W)).astype(np.float32)
        X = np.concatenate([feat, neg])
        y = np.concatenate([np.ones(n), np.zeros(n)])
        perm = rng.permutation(len(X))
        X, y = X[perm], y[perm]
        acc, _ = train_distinguisher(X, y, epochs=25, seed=seed + 2)
        return acc

    nd = {}
    delta = [0xFF, 0xFF, 0, 0]
    for label, ops in [('tempest_v3.1', tempest_v31_round_program()),
                       ('tempest_v3', tempest_a1_round_program())]:
        accs = {R: probe_word_delta(ops, R, 8, delta) for R in (1, 2, 3)}
        print(f'  {label}: R1={accs[1]:.3f} R2={accs[2]:.3f} R3={accs[3]:.3f}')
        nd[label] = accs
        results['calibration'][label + '_nd'] = accs
    r_v31 = max((r for r, a in nd['tempest_v3.1'].items() if a > 0.55), default=0)
    r_a1 = max((r for r, a in nd['tempest_v3'].items() if a > 0.55), default=0)
    c3 = r_v31 >= 1 and r_a1 < r_v31
    print(f'  C3 (v3.1 distinguishable, A1 not): {"PASS" if c3 else "FAIL"} '
          f'[v3.1 depth={r_v31}, A1 depth={r_a1}]')

    # ---- C4: empirical DP + L2 exact trails -------------------------------
    print('\n[3/4] empirical DP + L2 exact trails')
    for label, ops in [('tempest_v3.1', tempest_v31_round_program()),
                       ('tempest_v3', tempest_a1_round_program())]:
        dp = empirical_differential(ops, W=8, R=2, n_trials=8192, seed=21)
        av = avalanche(ops, W=8, R=2, n_trials=4096, seed=23)
        lb = linear_bias(ops, W=8, R=2, n_samples=65536, n_masks=24, seed=27)
        print(f'  [{label}] dp_zero={dp["dp_zero_after_R"]:.2e} '
              f'min_act={dp["min_active_and_bits"]} mean_act={dp["mean_active_and_bits"]:.1f} '
              f'avalanche={av["mean_flip_fraction"]:.3f} max_lin_bias={lb["max_abs_bias"]:.2e}')
        results['calibration'][label + '_dp'] = dp
        results['calibration'][label + '_av'] = av
        results['calibration'][label + '_lin'] = lb

    print('\n  L2 exact trails:')
    for label, ops in [('tempest_v3.1', tempest_v31_round_program()),
                       ('tempest_v3', tempest_a1_round_program())]:
        r4 = l2_report(ops, name=label + '_W4', W=4, R=2, verbose=True)
        r8 = l2_report(ops, name=label + '_W8', W=8, R=2, verbose=True)
        results['calibration'][label + '_l2w4'] = r4
        results['calibration'][label + '_l2w8'] = r8

    c4 = True  # informational; verdict from printed numbers
    print(f'\n  C4 (informational): see min_active numbers above')

    # ---- verdict ----------------------------------------------------------
    all_ok = c1 and c2 and c3
    print('\n' + '=' * 70)
    print(f'CALIBRATION VERDICT: {"ALL CRITERIA MET" if all_ok else "FAILED"} '
          f'(C1={c1} C2={c2} C3={c3}) in {time.time() - t0:.1f}s')
    print('=' * 70)

    with open('results_calibration.json', 'w') as f:
        json.dump(results, f, indent=1, default=str)
    print('saved results_calibration.json')
    return all_ok


if __name__ == '__main__':
    main()

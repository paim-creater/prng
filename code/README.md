# code/ — reference C sources and tools

KAT-verified reference implementations of Algorithm 1 and companion
tools. `src/` contains the same core plus the SIMD/legacy ports;
`code/` is the canonical, paper-cited set.

## Core

| File | Role |
|---|---|
| `tempest_v3.c` / `tempest_v3.h` | Algorithm 1 (round function, key schedule, output function) — the KAT ground truth |
| `tempest_v3_a1.c` / `tempest_v3_a1.h` | same, Algorithm-1-clean variant |
| `kat_tempest.h` | published KAT vector, incl. `0x6BBE30BB1D12DDD0` |
| `runtime_check.c` | 0.01 ms start-up self-check (KAT + key aliveness + constant time) |
| `tempest_stream.c` | ChaCha20-pattern stream-cipher demo |
| `platform.h` | portable intrinsics |

## Benchmarks (`bench_*.c`)

Same-machine, same-harness comparison (locked base clock, long loops,
register accumulator, medians of three): Tempest v3/v4 scalar and
AVX-512 vs ChaCha20 (scalar and OpenSSL AVX) vs AES-NI. See the paper's
Table XIII for the measured table; `src/bench_a1_avx512.c` is the
8-way SIMD benchmark.

## Analysis tools

| File | Role |
|---|---|
| `sat_analysis/` | MILP/SAT scripts: `milp_diff_bit_correct.py`, `milp_deg_exact.py`, `milp_multiround_free.py`, `milp_trail_w64.py`, `gen_dimacs.py`, `run_sat_analysis.py` |
| `sat_benchmark.c` / `sat_gen_dimacs.c` | CNF generation (legacy) |
| `diff_search_v3.c`, `cryptanalysis_v2.c`, `markov_validate.c` | exploratory cryptanalysis (audit record) |
| `v31_gen.c` | v3.1 dead-key predecessor stream generator (rebuilt from the audit record; feeds Dieharder as `file_input_raw` — see `data/dieharder_v31_rebuilt_20260810.txt`) |
| `v31_fixed_gen.c` | **v3.1 with the Phase-B linear-part fix** (drop one rotation per word: rank 248 → 256, kills the all-ones kernel and the 64-step collapse; full Dieharder `-a` passes — see `docs/V31_FIX_RECORD.md`) |
| `bolt_v3.c` / `adcbolt.h` | legacy non-crypto PRNG (historical) |

## Build

```bash
gcc -O3 -o kat_check src/kat_check_main.c code/tempest_v3.c && ./kat_check
gcc -O3 -o runtime_check code/runtime_check.c code/tempest_v3.c && ./runtime_check
```

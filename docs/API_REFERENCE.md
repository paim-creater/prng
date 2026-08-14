# API Reference

> Updated 2026-08 to the audited, current API surface. Legacy Bolt-era
> interfaces are marked *(legacy)*.

## C library (`code/tempest_v3.h`, `code/tempest_v3.h`)

### Tempest v3 (CSPRNG)

```c
typedef struct { ... } tempest_state;      /* 256-bit state + key schedule */

void    tempest_init(tempest_state *s, const uint64_t key[4], const uint64_t nonce[2]);
uint64_t tempest_u64(tempest_state *s);   /* one 64-bit word, one round */
void    tempest_u64x2(tempest_state *s, uint64_t out[2]); /* dual block */
void    tempest_bytes(tempest_state *s, uint8_t *buf, size_t n);
void    tx5cmul_seed(tempest_state *s, uint64_t seed);   /* (legacy name) */
```

`tempest_init` runs the 22-round initialization (25 cycles in
hardware); `tempest_u64x2` matches the KAT vector
`0x6BBE30BB1D12DDD0` (first block, key [1,2,3,4], nonce [5,6]).

### ADC-Bolt *(legacy, non-crypto)*

```c
void     adcbolt_seed(adcbolt_state *s, uint64_t seed);
uint64_t adcbolt_u64(adcbolt_state *s);
double   adcbolt_double(adcbolt_state *s);
```

### AVX-512 port (`code/tempest_a1_avx512.c`)

8-way SIMD implementation of Algorithm 1; API mirrors the scalar
`tempest_*` with `_8x` suffixed batch functions (see header).

### KAT verification (`code/kat_tempest.h`)

```c
int tempest_kat_verify(tx4_state *s);   /* returns 1 if all blocks match */
```

Verifies the first five 128-bit output blocks against the published
vector; used by `tests/kat_verify.c` and `hardware/sim/` testbenches.

### Runtime self-check (`code/runtime_check.c`)

```c
/* 0.01 ms start-up check: KAT compliance + key aliveness + constant-time */
int main(int argc, char **argv);
```

- `check_kat()` — the same five blocks the RTL testbench verifies
- `check_aliveness()` — two keys, 16 blocks, no collision (catches the
  dead-key v3.1 class)
- `check_constant_time()` — operation vocabulary audit

### Stream-cipher demo (`code/tempest_stream.c`)

ChaCha20-pattern keystream XOR (`tempest_stream`), verified round-trip
on 4 MiB and on any file.

## Python verification engine (`engine/`)

All scripts take no arguments and print their results to stdout,
writing the corresponding `.json` dataset. Key entry points:

| Script | Verifies |
|---|---|
| `cipher.py` | bit-exact Algorithm-1 port (self-test) |
| `audit_true_algorithm1.py` | W=4 full-domain exact metrics (DP, degree, τ) |
| `readword_theorem.py` | Read-Word Polar-Rank Theorem (35 designs, 0 failures) |
| `min_shadow_rank.py` | polar matrices and rank computation |
| `rank_certificate_demo.py` | W=64 rank-3 certificate (witness Δ=0x4) |
| `explore_decomp_bound.py` | decomposition bound, 1,995 differences, 0 violations |
| `explore_round_dp_curve.py` | exact 22-round W=4 multi-round curve |
| `explore_cascade_degree.py` | cascade degree law (β₁ = 16 certificate) |
| `walsh_rank_dual.py` | Walsh-rank duality |
| `sat_attack_grid.py` | SAT preimage grid (pysat/CaDiCaL) |
| `trail_diff.py` | MILP differential trails (needs pulp) |
| `trail_lin.py` | exact W=4 Walsh values (FWHT) |
| `state_attack.py` | ANF, cube tests, output-function SAT inversion |
| `lin_scale.py` | linear scaling W=8/16/32/64 (2²⁴ samples/mask) |
| `diff_sum.py` | multi-round differential summation (W=8 and W=64) |
| `audit_cascade_rank.py` / `audit_w8_tau.py` | cascade ranks / W=8 key relevance |

Dependencies: `numpy` (all); `pysat` (SAT scripts); `pulp` (MILP
scripts). See `engine/README.md` for the full inventory.

## Hardware (`hardware/`)

| Module | Role |
|---|---|
| `rtl/tempest_v3_top.v` | top-level FSM (IDLE→LOAD→INIT 22→FINAL→GEN) |
| `rtl/round_function.v` | Phases A–D combinational cloud |
| `rtl/andmix4.v` / `andmix4_k2.v` | full / k=2 Pareto-front cascade |
| `rtl/output_function.v` | Algorithm-1 output function |
| `sim/tb_tempest_v3.v` / `tb_tempest_v3_k2.v` | KAT testbenches (Icarus Verilog 12) |
| `scripts/synth.sh` | Yosys 0.67 → nextpnr-ice40 → icepack flow |
| `build/tempest_v3_k2.bin` | **completed bitstream (135 KB, k=2)** |
| `build/*.log` | synthesis and P&R logs (incl. honest non-convergence) |

## Integrations

- `tempest-rs/` — Rust crate (see its README).
- `pypi_package/` — Python package (pyproject.toml).
- `homebrew/tempest-rng.rb` — Homebrew formula.

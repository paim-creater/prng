# hardware/ — KAT-verified RTL and the completed k=2 bitstream

Synthesizable Verilog of Algorithm 1 (Tempest v3), bit-exact with the C
ground truth (5-block KAT, Icarus Verilog 12), plus the full
open-source FPGA flow (Yosys 0.67 → nextpnr-ice40 → icepack) with
honest logs.

## Contents

| Path | Role |
|---|---|
| `rtl/` | `tempest_v3_top.v` (FSM), `round_function.v`, `andmix4.v`, `andmix4_k2.v`, `andmix_level.v`, `output_function.v`, `output_function_dual.v` |
| `sim/` | `tb_tempest_v3.v`, `tb_tempest_v3_k2.v` — KAT testbenches |
| `scripts/synth.sh` | synthesis + P&R + bitstream script |
| `constraints/tempest_v3.pcf` | iCE40 pin constraints |
| `build/` | synthesis/P&R logs, `round_function_k2.v`, `tempest_v3_top_k2.v`, **`tempest_v3_k2.bin` (completed bitstream, 135 KB)** |
| `demo/tempest_demo.py` | Python demo driver |

## Verified state (measured, honest)

| Variant | LUT4 | FF | Result |
|---|---|---|---|
| dual-output (128 bit/round) | 9,275 | 906 | exceeds every iCE40 device |
| single-output (64 bit/round) | 7,158 | 1,034 | fits HX8K (93%), **routing does not converge at 98% density** |
| **k=2 Pareto-front** | **5,915** | **1,034** | **placed (82%), routed, 34.21 MHz, bitstream generated (135 KB)** |

The k=2 variant is the paper's first finished hardware artifact: a
KAT-exact, synthesized, placed, routed, bitstream-level implementation
of the Tempest round function at about two-thirds of the full
cascade's area — a concrete instance of the framework's own Pareto
analysis deciding a hardware trade. A time-multiplexed andmix4 was
measured and rejected (selector logic 1,800 LUT vs 1,881 unrolled).

## Reproduce

```bash
# needs the OSS CAD Suite in PATH: yosys, nextpnr-ice40, icepack
bash scripts/synth.sh            # full flow, logs land in build/
# KAT check (needs iverilog):
cd sim && iverilog -o tb tb_tempest_v3.v ../rtl/*.v && vvp tb
# expect: 5/5 blocks match, incl. 0x6BBE30BB1D12DDD0
```

Throughput model (k=2): 64 bits × 34.21 MHz ≈ 2.19 Gbit/s.

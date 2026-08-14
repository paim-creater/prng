# Contributing to AM-SEV / Tempest

Thanks for your interest! The most valuable contributions are
independent verifications and honest reports.

## Ways to contribute

### 1. Reproduce a paper number

Run any `engine/` script and compare its output to the committed
`.json`. If a number does not match, open an issue with the script
name, your environment, and the diff — reproducing the audit chain is
the whole point of this repository.

### 2. Run the benchmark on your hardware

```bash
gcc -O3 -march=native -o benchmark benchmark.c code/adcbolt.c code/tempest_v3.c -I.
./benchmark
```

Report your CPU model and measured Gbit/s (same-harness protocol: long
loops, register accumulator, medians of three).

### 3. Build the FPGA flow

Requires the OSS CAD Suite (Yosys, nextpnr-ice40, icepack) and
Icarus Verilog:

```bash
cd hardware && bash scripts/synth.sh
```

Report tool versions and any divergence from `hardware/build/*.log`.

### 4. Independent cryptanalysis

Attacks, distinguishers, or trail improvements against Tempest v3 are
explicitly welcome — the paper's security claims are bounded by its
stated metrics, and every finding (positive or negative) belongs in
[`docs/AUDIT_RECORD.md`](docs/AUDIT_RECORD.md) or an issue.

## Guidelines

- **Do not add binary artifacts** (`.exe`, `.bin`, PractRand raw
  inputs) — GitHub size limits; logs and sources only.
- If you correct a number, update the `.json` dataset *and* the audit
  record; a corrected claim without a documented correction is not a
  contribution.
- Keep the "audit record, not cleanup" convention: scripts that record
  exploration failures stay, with EXPLORATION-stage headers.

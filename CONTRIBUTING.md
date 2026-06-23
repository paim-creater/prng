# Contributing to Bolt & Tempest PRNG

Thanks for your interest! Here's how to help.

## Ways to Contribute

### Run the benchmark on your hardware
The most valuable contribution: run 2 commands and report your results.

```bash
gcc -O3 -march=native -o benchmark benchmark.c src/adcbolt.c src/tempest_v3.c -I.
./benchmark
```

[Open an issue](https://github.com/paim-creater/prng/issues/new?template=benchmark_result.md) with your CPU model and Gbit/s numbers.

### Test on ARM64 / RISC-V / MSVC
The code auto-detects platforms via `src/platform.h`. If your platform isn't recognized, let us know.

### Add language bindings
Wrappers for JavaScript/WASM, Rust, C#, Go are welcome. See `prng.py` for the Python reference.

### Report bugs
Use the [bug report template](https://github.com/paim-creater/prng/issues/new?template=bug_report.md).

## Development

```bash
git clone https://github.com/paim-creater/prng.git
cd prng
make          # run tests
make benchmark # verify throughput
```

## Style
- C99, 4-space indent
- Keep `prng_single_header.h` updated when changing `src/`

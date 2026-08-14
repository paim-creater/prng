# cpp/ — C++ `<random>` URBG + GSL integration

Tempest v3 exposed to the C++ ecosystem through two official
extension points:

1. **`tempest_rng.hpp`** — a C++ `UniformRandomBitGenerator` (URBG),
   the concept required by the C++ standard library `<random>` and by
   Boost.Random. `std::uniform_int_distribution`,
   `std::normal_distribution`, `std::shuffle`, and every Boost.Random
   distribution accept it directly.

2. **`gsl_tempest.c`** — registration of Tempest as a `gsl_rng_type`,
   the GNU Scientific Library's official custom-RNG extension point
   (7-field descriptor + `gsl_rng_alloc(&gsl_rng_tempest)`). Every GSL
   distribution (`gsl_ran_uniform`, `gsl_ran_gaussian`,
   `gsl_ran_binomial`, ...) then draws from Tempest. The same
   `gsl_rng_type` pattern is what CERN ROOT uses to wrap arbitrary
   engines (`GSLRngROOTWrapper`).

Both wrappers link against the KAT-verified C reference
(`code/tempest_v3.c`) — the single source of truth — so bit-exactness
with the published KAT (`0x6BBE30BB1D12DDD0`, ...) holds by
construction.

## Build & test (WSL)

```bash
# C++ URBG
g++ -std=c++17 -O2 -I.. -o test_urbg test_urbg.cpp ../code/tempest_v3.c && ./test_urbg
# expect: KAT 5/5 PASS, uniform mean ~49.5, normal mean ~0, shuffle PASS

# GSL (needs libgsl-dev)
gcc -O2 -I.. -o test_gsl test_gsl.c gsl_tempest.c ../code/tempest_v3.c -lgsl -lgslcblas && ./test_gsl
# expect: name: tempest, KAT 5/5 PASS, uniform mean ~0.5, gaussian ~0, binomial ~30
```

## Usage

```cpp
#include "tempest_rng.hpp"
TempestRng rng(seed64);                       // deterministic
TempestRng rng(key[4], nonce[2]);             // 256-bit key + 128-bit nonce
std::uniform_int_distribution<int> d(0, 99);  // <random> distributions
d(rng);
std::shuffle(v.begin(), v.end(), rng);        // Boost.Random / algorithms
```

```c
#include <gsl/gsl_rng.h>
extern const gsl_rng_type *gsl_rng_tempest;
gsl_rng *r = gsl_rng_alloc(gsl_rng_tempest);
gsl_rng_set(r, 42);
double x = gsl_ran_gaussian(r, 1.0);
```

## Security notes

- `TempestRng(seed64)` / `gsl_rng_set` are for reproducibility
  (simulation, tests, property-based testing) — not key generation.
  Use the 256-bit-key constructor for cryptographic unpredictability.
- These are *generator-semantics* interfaces (uniform sequence +
  seeding), the sound way to integrate a CSPRNG into an ecosystem —
  unlike entropy/trust-root slots inside cryptographic libraries.

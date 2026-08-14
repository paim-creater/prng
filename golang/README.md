# golang/ — Tempest v3 as a `math/rand/v2.Source`

The Tempest v3 CSPRNG implemented as a drop-in `math/rand/v2.Source`
for the Go ecosystem (cloud-native tooling, chaos engineering,
simulation, Monte Carlo).

**Bit-exact with the C reference** (`code/tempest_v3.c`): the published
5-block KAT is verified in `tempest_test.go` (`go test`):

```
TestKAT              PASS  0x6BBE30BB1D12DDD0, 0xB9167FE6CCEC68D9, ...
TestNextBytesStream  PASS  byte-identical to C tempest_bytes semantics
TestRandIntegration  PASS  rand.New(source), determinism, distribution
```

## Usage

```go
import "github.com/paim-creater/prng/golang"

// Full cryptographic seeding: 256-bit key + 128-bit nonce
src := tempest.NewTempest([4]uint64{...}, [2]uint64{...})

// Or deterministic seeding for reproducible simulation/chaos injection
src = tempest.FromSeed(42)

r := rand.New(src)   // full-featured *rand.Rand (IntN, Float64, ...)
r.IntN(100)
```

`Uint64()` emits one 64-bit output word per round; `NextBytes` uses
the dual-output path (128 bits per round), matching the C
`tempest_bytes` semantics byte-for-byte.

## Why this interface

`math/rand/v2.Source` requires a single method (`Uint64() uint64`),
a *generator-semantics* interface: it asks for a uniform random
sequence, not for an entropy source. That is exactly what a CSPRNG
provides, and it is why this integration is sound where replacing a
cryptographic library's internal RNG is not (the latter is
entropy/trust-root semantics: reseed requirements, prediction
resistance, and upstream acceptance of the substitution).

## Security notes

- Use `NewTempest` (OS entropy → key/nonce) when unpredictability
  matters; `FromSeed` is for reproducibility (simulation, tests,
  chaos engineering), not key generation.
- The Go implementation is a reference port; for production use the
  KAT-verified C implementation remains the reference of record.

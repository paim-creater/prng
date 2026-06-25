# API Reference: Bolt and Tempest PRNG Library

## Table of Contents

1. [ADC-Bolt API](#adc-bolt-api)
   - [adcbolt_seed](#adcbolt_seed)
   - [adcbolt_u64](#adcbolt_u64)
   - [adcbolt_double](#adcbolt_double)
   - [adcbolt_range](#adcbolt_range)
   - [adcbolt_bytes](#adcbolt_bytes)
   - [adcbolt_shuffle](#adcbolt_shuffle)
2. [4-cmul Tempest v3 API](#4-cmul-tempest-v3-api)
   - [tempest_init](#tempest_init)
   - [tempest_u64](#tempest_u64)
   - [tempest_u64x2](#tempest_u64x2)
   - [tempest_bytes](#tempest_bytes)
   - [tempest_double](#tempest_double)
   - [tempest_range](#tempest_range)
   - [tempest_shuffle](#tempest_shuffle)
   - [tempest_hex](#tempest_hex)
3. [Python API (prng.py)](#python-api-prngpy)
   - [prng.ADC_Bolt](#prngadc_bolt)
   - [prng.Tempest](#prngtempest)
   - [Instance Methods](#instance-methods)
4. [Data Types](#data-types)
5. [Thread Safety](#thread-safety)

---

## ADC-Bolt API

ADC-Bolt is an ultra-fast non-cryptographic PRNG (70.3 Gbit/s on Zen 4). It uses carry-chain dual-addition (ADD+ADD, deg=2 over GF(2)) as its nonlinear primitive, replacing the more expensive MULX operation while maintaining the same algebraic degree. ADC-Bolt passes all TestU01 suites (SmallCrush, Rabbit, Alphabit, BigCrush, Crush) and PractRand (1 TiB).

**State type**: `adcbolt_state` (struct of four uint64_t: u, v, w, z).

**Performance**: ~0.11 cycles/byte on Zen 4, ~70.3 Gbit/s continuous generation.

**Thread safety**: No function in the ADC-Bolt family is thread-safe. Each thread must use its own `adcbolt_state` instance.

---

### adcbolt_seed

```c
void adcbolt_seed(adcbolt_state *s, uint64_t seed);
```

Initialize an ADC-Bolt state from a 64-bit seed value.

The state is initialized by expanding the seed across all four state words using different mixing functions (addition of a golden-ratio constant, multiplication by an AES-derived constant, XOR with a 64-bit constant, and 32-bit rotation with addition). The state is then stirred by generating and discarding 4 outputs, ensuring sufficient diffusion before any output is returned to the caller.

**Parameters**:
- `s` -- pointer to an uninitialized `adcbolt_state` struct. Must not be NULL.
- `seed` -- a 64-bit unsigned integer seed. Any value is valid, including 0.

**Return value**: None.

**Usage example**:

```c
#include "prng_single_header.h"

adcbolt_state rng;
adcbolt_seed(&rng, 12345);
uint64_t x = adcbolt_u64(&rng);
```

**Performance**: Constant-time initialization (~4 rounds of state mixing), approximately 15-20 ns.

**Thread safety**: Not thread-safe. Call from a single thread before sharing the state (if sharing is desired, protect access with external synchronization).

---

### adcbolt_u64

```c
uint64_t adcbolt_u64(adcbolt_state *s);
```

Generate the next 64-bit random unsigned integer and advance the internal state.

Performs one round of the ADC-Bolt state-update function: carry-chain nonlinearity `(z + u) + v` followed by a 3-operation ARX ring and an XOR-rotate output extraction. All 2^64 possible values are generated with uniform probability over the full period.

**Parameters**:
- `s` -- pointer to an initialized `adcbolt_state`. Must not be NULL.

**Return value**: A uniformly distributed 64-bit unsigned integer.

**Usage example**:

```c
adcbolt_state rng;
adcbolt_seed(&rng, 0);
for (int i = 0; i < 1000; i++) {
    printf("%016llx\n", adcbolt_u64(&rng));
}
```

**Performance**: ~1.4 cycles per call (one round at ~3-4 cycles yields 64 bits), approximately 0.7 ns/call on Zen 4. This is the core generation primitive; all other ADC-Bolt output functions are built on top of it.

**Thread safety**: Not thread-safe. Do not call concurrently on the same state without external locking. For multi-threaded generation, seed a separate `adcbolt_state` per thread with different seeds (e.g., `thread_id + base_seed`).

---

### adcbolt_double

```c
double adcbolt_double(adcbolt_state *s);
```

Generate a random double-precision floating-point number in the half-open interval [0.0, 1.0).

The value is derived by taking the high 53 bits of a 64-bit random integer and multiplying by 2^-53. This is the standard method for generating uniform doubles from 64-bit integer output, equivalent to `(u64 >> 11) * 0x1.0p-53`. All representable double values in the range are generated, with precision of 2^-53 (~1.11e-16).

**Parameters**:
- `s` -- pointer to an initialized `adcbolt_state`. Must not be NULL.

**Return value**: A double in [0.0, 1.0). The value 1.0 is never returned.

**Usage example**:

```c
adcbolt_state rng;
adcbolt_seed(&rng, 42);
double x = adcbolt_double(&rng);    // e.g., 0.723891...
double y = adcbolt_double(&rng);    // e.g., 0.104562...
```

**Performance**: Equivalent to `adcbolt_u64` plus a shift and a floating-point multiply (1 ADD + 1 FMUL). Negligible overhead over `adcbolt_u64`.

**Thread safety**: Not thread-safe. Same constraints as `adcbolt_u64`.

---

### adcbolt_range

```c
int adcbolt_range(adcbolt_state *s, int min, int max);
```

Generate a uniformly distributed random integer in the inclusive range [min, max].

Uses rejection-free modulo reduction of a 64-bit random value. Because the range is typically small relative to 2^64, the modulo bias is negligible for practical use. For ranges where `(max - min + 1)` is a power of two, the mapping is perfectly uniform.

**Parameters**:
- `s` -- pointer to an initialized `adcbolt_state`. Must not be NULL.
- `min` -- the inclusive lower bound of the range (any signed integer).
- `max` -- the inclusive upper bound of the range. Must be >= min.

**Return value**: An integer `x` such that `min <= x <= max`.

**Usage example**:

```c
adcbolt_state rng;
adcbolt_seed(&rng, 12345);

int dice   = adcbolt_range(&rng, 1, 6);    // 1..6
int coin   = adcbolt_range(&rng, 0, 1);    // 0 or 1
int index  = adcbolt_range(&rng, 0, 99);   // 0..99
```

**Performance**: Equivalent to `adcbolt_u64` plus a modulo and an addition. Overhead is ~1-2 cycles.

**Caveats**:
- If `max < min`, behavior is undefined (the subtraction `max - min + 1` wraps around as an unsigned value, producing a huge range).
- Modulo bias is present but negligible for ranges below ~2^32. For cryptographic applications, use `tempest_range` instead.
- The return type is `int` (32-bit on most platforms). For ranges requiring more than 2^31 values, use `adcbolt_u64` directly with manual scaling.

**Thread safety**: Not thread-safe.

---

### adcbolt_bytes

```c
void adcbolt_bytes(adcbolt_state *s, uint8_t *buf, size_t n);
```

Fill a buffer with `n` cryptographically-random (non-crypto quality) bytes.

Calls `adcbolt_u64` repeatedly, writing 8 bytes at a time. If `n` is not a multiple of 8, the final partial word supplies the remaining bytes.

**Parameters**:
- `s` -- pointer to an initialized `adcbolt_state`. Must not be NULL.
- `buf` -- pointer to the destination buffer. Must have at least `n` bytes of writable memory.
- `n` -- number of bytes to generate. Can be 0 (no-op).

**Return value**: None.

**Usage example**:

```c
adcbolt_state rng;
adcbolt_seed(&rng, 0);

uint8_t key[32];
adcbolt_bytes(&rng, key, sizeof(key));  // fill 32-byte buffer

uint8_t small[3];
adcbolt_bytes(&rng, small, 3);          // 3 bytes from a single u64
```

**Performance**: `ceil(n / 8)` calls to `adcbolt_u64`, each ~0.7 ns. For large buffers (>= 1 KB), the per-byte cost approaches 0.11 cycles/byte. For very small `n` (1-7 bytes), the cost is one full `adcbolt_u64` call despite using only partial output.

**Thread safety**: Not thread-safe.

---

### adcbolt_shuffle

```c
void adcbolt_shuffle(adcbolt_state *s, void *array, size_t n, size_t elem_size);
```

Randomly shuffle an array of `n` elements in-place using the Fisher-Yates (Knuth) shuffle algorithm.

Each element is swapped with a randomly chosen element at or after its position. The shuffle produces exactly one of the n! possible permutations with uniform probability, subject to the quality of the underlying PRNG.

**Parameters**:
- `s` -- pointer to an initialized `adcbolt_state`. Must not be NULL.
- `array` -- pointer to the start of the array. Must have at least `n * elem_size` bytes of writable memory.
- `n` -- number of elements in the array. If 0 or 1, the function is a no-op.
- `elem_size` -- size of each element in bytes (use `sizeof(element_type)`).

**Return value**: None.

**Usage example**:

```c
adcbolt_state rng;
adcbolt_seed(&rng, 12345);

int deck[52];
for (int i = 0; i < 52; i++) deck[i] = i;
adcbolt_shuffle(&rng, deck, 52, sizeof(int));
// deck is now randomly ordered

float vec[100];
adcbolt_shuffle(&rng, vec, 100, sizeof(float));
```

**Implementation note**: This function is a convenience wrapper. If not included in the current release, it can be trivially implemented as:

```c
void adcbolt_shuffle(adcbolt_state *s, void *array, size_t n, size_t elem_size) {
    uint8_t *arr = (uint8_t *)array;
    uint8_t tmp[256];  // stack buffer for swapping (supports up to 256-byte elements)
    for (size_t i = n - 1; i > 0; i--) {
        size_t j = adcbolt_u64(s) % (i + 1);
        if (i != j) {
            memcpy(tmp, arr + j * elem_size, elem_size);
            memcpy(arr + j * elem_size, arr + i * elem_size, elem_size);
            memcpy(arr + i * elem_size, tmp, elem_size);
        }
    }
}
```

**Performance**: O(n) swaps. Each swap requires one `adcbolt_u64` call for the index selection, plus memcpy overhead for the element exchange. For small elements (<= 8 bytes), registers can replace the stack buffer.

**Thread safety**: Not thread-safe.

---

## 4-cmul Tempest v3 API

4-cmul Tempest v3 is a cryptographic CSPRNG with 2^128 conservative security (self-analyzed). It uses four cross-multiplies per round in a Fibonacci-weave schedule, ADD pre-diffusion for degree and ILP improvement, AND-mix output function, and alternating Boomerang ARX for wide-trail bounds. Passes NIST SP 800-22 (15/15), TestU01 all 5 levels, and PractRand (1 TiB, zero anomalies). Achieves 19.0 Gbit/s on Zen 4.

**State type**: `tempest_state` (struct of five uint64_t: u, v, w, z, r, where r is the round counter).

**Performance**: ~0.42 cycles/byte on Zen 4 (single-output), ~0.24 cycles/byte (dual-output), ~19.0 Gbit/s continuous.

**Thread safety**: No function in the Tempest family is thread-safe. Each thread must use its own `tempest_state` instance. Sharing a `tempest_state` between threads without external locking will produce corrupted (but not predictable) output.

---

### tempest_init

```c
void tempest_init(tempest_state *s, const uint64_t key[4], const uint64_t nonce[2]);
```

Initialize a Tempest v3 state from a 256-bit key and 128-bit nonce.

The key schedule absorbs the key and nonce over 16 rounds of the round function (8 rounds with key injection, 8 rounds with nonce injection), followed by a 6-round blank warmup. The key is injected directly (even rounds) and rotated (odd rounds) with round constants derived from the SHA-512 initial values. The nonce is injected as 64-bit composites of its two halves. After absorption, 6 blank rounds ensure full diffusion before any output is produced.

**Parameters**:
- `s` -- pointer to an uninitialized `tempest_state` struct. Must not be NULL.
- `key` -- array of 4 uint64_t values (256 bits total). All values are valid. For maximum security, use a cryptographically random key (e.g., from `/dev/urandom` or a hardware RNG).
- `nonce` -- array of 2 uint64_t values (128 bits total). Must be unique for each encryption context under the same key. Reusing a `(key, nonce)` pair does not leak the key but produces identical output streams (two-party protocol vulnerability).

**Return value**: None.

**Usage example**:

```c
#include "prng_single_header.h"

tempest_state csprng;
uint64_t key[4] = {
    0x0123456789ABCDEFULL, 0xFEDCBA9876543210ULL,
    0x0011223344556677ULL, 0x8899AABBCCDDEEFFULL
};
uint64_t nonce[2] = {0xAAAAAAAAAAAAAAAAULL, 0xBBBBBBBBBBBBBBBBULL};

tempest_init(&csprng, key, nonce);
uint64_t token = tempest_u64(&csprng);
```

**Performance**: 22 rounds of the Tempest round function (16 absorption + 6 warmup). Each round is ~5-6 cycles on Zen 4. Total initialization time is approximately 110-130 cycles (~22 ns at 5 GHz). This is a one-time cost per `(key, nonce)` pair.

**Security notes**:
- The key schedule is NOT a password-based key derivation function (PBKDF). It does not use stretching, salting, or memory-hardness. If deriving keys from passwords, use Argon2 or bcrypt first, then pass the derived key.
- Nonce reuse under the same key produces identical output. This is standard for stream-cipher-like PRNGs. Use a monotonic counter or random nonce.
- The zero nonce ({0, 0}) is valid and can be used for deterministic seeding (see `tempest_seed` for a convenience alternative).

**Thread safety**: Not thread-safe.

---

### tempest_u64

```c
uint64_t tempest_u64(tempest_state *s);
```

Generate the next 64-bit cryptographically secure random value and advance the internal state.

Performs one round of the 4-cmul Tempest v3 round function, then extracts a single 64-bit output through the output pipeline: fold4 linear projection, self-XOR diffusion, ADD-square mixing, AND-mix degree doubling, and low-bit whitener. The output function provides degree >= 43 after 1 round and degree >= 256 after 2 rounds (using consecutive calls).

**Parameters**:
- `s` -- pointer to an initialized `tempest_state`. Must not be NULL.

**Return value**: A cryptographically random 64-bit unsigned integer. Under Hypotheses H1 and H2, the output is computationally indistinguishable from uniform random with 2^128 security.

**Usage example**:

```c
tempest_state rng;
uint64_t key[4] = { /* ... */ };
uint64_t nonce[2] = {0, 0};
tempest_init(&rng, key, nonce);

uint64_t session_id = tempest_u64(&rng);
uint64_t auth_token = tempest_u64(&rng);
```

**Performance**: One round (~5-6 cycles) + one output function (~4-5 cycles) = ~9-11 cycles per 64-bit output (~0.17 cycles/byte). At 5 GHz, this is ~32 Gbit/s theoretical for the single-output path. The measured 19.0 Gbit/s (in dual-output mode) reflects the benchmark loop overhead. For maximum throughput, use `tempest_u64x2`.

**Thread safety**: Not thread-safe. Do not call concurrently on the same state.

---

### tempest_u64x2

```c
void tempest_u64x2(tempest_state *s, uint64_t out[2]);
```

Generate two independent 64-bit cryptographically secure random values in a single round. This is the primary high-throughput interface for Tempest v3.

Performs one round of the round function, then extracts two outputs using permuted state-word combinations: `out[0] = make_output(u, v, w, z)` and `out[1] = make_output(v, w, z, u)`. The two outputs are derived from different linear projections of the same 256-bit state and are uncorrelated under the assumption that the round function thoroughly mixes all four state words.

**Parameters**:
- `s` -- pointer to an initialized `tempest_state`. Must not be NULL.
- `out` -- pointer to a 2-element uint64_t array. Must have space for 2 values. Must not be NULL.

**Return value**: None. Results are written to `out[0]` and `out[1]`.

**Usage example**:

```c
tempest_state rng;
uint64_t key[4] = { /* ... */ };
uint64_t nonce[2] = {0, 0};
tempest_init(&rng, key, nonce);

uint64_t pair[2];
tempest_u64x2(&rng, pair);
printf("r1 = %016llx\nr2 = %016llx\n", pair[0], pair[1]);
```

**Performance**: One round (~5-6 cycles) + two output functions (partially overlapped, ~6-8 cycles total) = ~11-14 cycles for 128 bits. This is approximately 73% more throughput than calling `tempest_u64` twice, which would require two full rounds plus two output functions (~18-22 cycles). At 5 GHz, the measured throughput is 19.0 Gbit/s.

**Security**: The two outputs from a single round share the same post-round state. They are not independent in the information-theoretic sense (the 256-bit state fully determines both outputs), but are computationally independent -- given only the outputs, recovering the state or predicting future outputs is at least as hard as the 2^128 security target.

**Thread safety**: Not thread-safe.

---

### tempest_bytes

```c
void tempest_bytes(tempest_state *s, uint8_t *buf, size_t n);
```

Fill a buffer with `n` cryptographically secure random bytes.

Uses `tempest_u64` for generation, writing 8 bytes at a time. If `n` is not a multiple of 8, the final partial word supplies the remaining bytes. For maximum throughput on large buffers (>= 16 bytes), each pair of `tempest_u64` calls can be manually coalesced; the library may optimize this path in future releases to use `tempest_u64x2` internally.

**Parameters**:
- `s` -- pointer to an initialized `tempest_state`. Must not be NULL.
- `buf` -- pointer to the destination buffer. Must have at least `n` bytes of writable memory.
- `n` -- number of bytes to generate. Can be 0 (no-op).

**Return value**: None.

**Usage example**:

```c
tempest_state rng;
uint64_t key[4] = { /* ... */ };
uint64_t nonce[2] = {0, 0};
tempest_init(&rng, key, nonce);

// Generate a 256-bit AES key
uint8_t aes_key[32];
tempest_bytes(&rng, aes_key, sizeof(aes_key));

// Generate a random initialization vector
uint8_t iv[16];
tempest_bytes(&rng, iv, sizeof(iv));
```

**Performance**: `ceil(n / 8)` calls to `tempest_u64`. For large buffers, the per-byte throughput approaches the single-output rate. For optimal throughput on bulk generation, use a manual loop calling `tempest_u64x2` and memcpy-ing the 16 bytes:

```c
void fast_tempest_bytes(tempest_state *s, uint8_t *buf, size_t n) {
    uint64_t pair[2];
    while (n >= 16) {
        tempest_u64x2(s, pair);
        memcpy(buf, pair, 16);
        buf += 16; n -= 16;
    }
    while (n >= 8) {
        uint64_t r = tempest_u64(s);
        memcpy(buf, &r, 8);
        buf += 8; n -= 8;
    }
    if (n > 0) {
        uint64_t r = tempest_u64(s);
        memcpy(buf, &r, n);
    }
}
```

**Thread safety**: Not thread-safe.

---

### tempest_double

```c
double tempest_double(tempest_state *s);
```

Generate a cryptographically secure random double-precision floating-point number in the half-open interval [0.0, 1.0).

Equivalent to `(tempest_u64(s) >> 11) * 0x1.0p-53`. Produces values with 53 bits of mantissa precision, uniformly distributed across all representable doubles in [0.0, 1.0).

**Parameters**:
- `s` -- pointer to an initialized `tempest_state`. Must not be NULL.

**Return value**: A cryptographically random double in [0.0, 1.0).

**Usage example**:

```c
tempest_state rng;
uint64_t key[4] = { /* ... */ };
uint64_t nonce[2] = {0, 0};
tempest_init(&rng, key, nonce);

double noise = tempest_double(&rng);   // e.g., 0.441892...
```

**Performance**: Equivalent to `tempest_u64` plus shift and multiply. Negligible overhead.

**Implementation note**: This function is a convenience wrapper. If not present in the current release, use:

```c
static inline double tempest_double(tempest_state *s) {
    return (tempest_u64(s) >> 11) * 0x1.0p-53;
}
```

**Thread safety**: Not thread-safe.

---

### tempest_range

```c
int64_t tempest_range(tempest_state *s, int64_t min, int64_t max);
```

Generate a uniformly distributed cryptographically secure random integer in the inclusive range [min, max].

Uses rejection sampling to eliminate modulo bias: if the range `R = max - min + 1` does not evenly divide 2^64, values in the "tail" of the 2^64 space (above the largest multiple of R) are rejected and resampled. For ranges where R divides 2^64 (i.e., R is a power of two), no rejection occurs -- the mapping is perfectly uniform with one `tempest_u64` call.

**Parameters**:
- `s` -- pointer to an initialized `tempest_state`. Must not be NULL.
- `min` -- the inclusive lower bound (64-bit signed integer).
- `max` -- the inclusive upper bound. Must be >= min.

**Return value**: An integer `x` such that `min <= x <= max`, generated with uniform distribution over the range.

**Usage example**:

```c
tempest_state rng;
uint64_t key[4] = { /* ... */ };
uint64_t nonce[2] = {0, 0};
tempest_init(&rng, key, nonce);

int64_t secure_dice  = tempest_range(&rng, 1, 6);
int64_t lottery_nr   = tempest_range(&rng, 1, 1000000);
int64_t zero_or_one  = tempest_range(&rng, 0, 1);
```

**Performance**: Typically one `tempest_u64` call per output value. For ranges where 2^64 % R != 0, approximately `2^64 / (2^64 - (2^64 % R))` calls are needed on average (bounded by 2 in expectation). For all practical ranges (< 2^48), the rejection probability is below 2^(-16), making the expected cost effectively one call.

**Implementation note**: This function is a convenience wrapper. If not present, use:

```c
static inline int64_t tempest_range(tempest_state *s, int64_t min, int64_t max) {
    uint64_t range = (uint64_t)(max - min + 1);
    uint64_t limit = UINT64_MAX - (UINT64_MAX % range);
    uint64_t r;
    do { r = tempest_u64(s); } while (r >= limit);
    return min + (int64_t)(r % range);
}
```

**Thread safety**: Not thread-safe.

---

### tempest_shuffle

```c
void tempest_shuffle(tempest_state *s, void *array, size_t n, size_t elem_size);
```

Randomly shuffle an array of `n` elements in-place using the Fisher-Yates shuffle with cryptographically secure random index selection.

Each index `j` in the range `[i, n-1]` is chosen using `tempest_range(s, i, n-1)`, ensuring uniform permutation selection with no modulo bias. The resulting permutation is computationally indistinguishable from a uniformly random permutation under the 2^128 security target.

**Parameters**:
- `s` -- pointer to an initialized `tempest_state`. Must not be NULL.
- `array` -- pointer to the start of the array. Must have at least `n * elem_size` bytes of writable memory.
- `n` -- number of elements. If 0 or 1, the function is a no-op.
- `elem_size` -- size of each element in bytes. Elements up to 256 bytes are supported via a stack-allocated swap buffer; for larger elements, use a heap-allocated buffer or memcpy with a temporary.

**Return value**: None.

**Usage example**:

```c
tempest_state rng;
uint64_t key[4] = { /* ... */ };
uint64_t nonce[2] = {0, 0};
tempest_init(&rng, key, nonce);

// Shuffle a deck of cards for a provably-fair online game
typedef struct { int suit; int rank; } Card;
Card deck[52];
for (int i = 0; i < 52; i++) {
    deck[i].suit = i / 13;
    deck[i].rank = i % 13;
}
tempest_shuffle(&rng, deck, 52, sizeof(Card));
// The shuffle is computationally indistinguishable from a fair physical shuffle
```

**Performance**: O(n) with n-1 calls to `tempest_range` (each typically one `tempest_u64` call). For 52 elements, this is ~52 x 0.7 ns ~ 36 ns. For 10^6 elements, this is ~0.7 ms.

**Security**: The cryptographically secure index selection ensures that no adversary can distinguish the resulting permutation from uniform random with advantage greater than 2^(-128), even given complete knowledge of all but one element.

**Implementation note**: If not included in the current release, this can be implemented as:

```c
void tempest_shuffle(tempest_state *s, void *array, size_t n, size_t elem_size) {
    uint8_t *arr = (uint8_t *)array;
    uint8_t tmp[256];
    for (size_t i = n - 1; i > 0; i--) {
        size_t j = (size_t)tempest_range(s, 0, (int64_t)i);
        if (i != j) {
            memcpy(tmp, arr + j * elem_size, elem_size);
            memcpy(arr + j * elem_size, arr + i * elem_size, elem_size);
            memcpy(arr + i * elem_size, tmp, elem_size);
        }
    }
}
```

**Thread safety**: Not thread-safe.

---

### tempest_hex

```c
void tempest_hex(tempest_state *s, char out[64]);
```

Generate 32 random bytes (256 bits) and write them as a 64-character null-terminated hexadecimal string.

This is a convenience function for generating hex-encoded tokens, keys, and identifiers. It generates 32 bytes using 4 calls to `tempest_u64` (each producing 8 bytes), then formats each byte as two lowercase hex characters.

**Parameters**:
- `s` -- pointer to an initialized `tempest_state`. Must not be NULL.
- `out` -- pointer to a char buffer of at least 65 bytes (64 characters + null terminator). Must not be NULL.

**Return value**: None. The buffer `out` is filled with 64 hex characters and a null terminator at position 64.

**Usage example**:

```c
tempest_state rng;
uint64_t key[4] = { /* ... */ };
uint64_t nonce[2] = {0, 0};
tempest_init(&rng, key, nonce);

char hex_buf[65];
tempest_hex(&rng, hex_buf);
printf("API Key: %s\n", hex_buf);
// Output: API Key: a3f7c21b9e04d856...
```

**Performance**: 4 calls to `tempest_u64` (~36-44 cycles) plus hex formatting (~20-30 cycles). Total approximately 60-80 cycles per 64-character hex string (~13 ns at 5 GHz).

**Security**: The output is a hex-encoded representation of 256 cryptographically random bits. No information is lost in the encoding.

**Thread safety**: Not thread-safe.

---

## Python API (prng.py)

The Python module `prng.py` provides Pythonic wrappers around the C library. On import, it auto-compiles the C code into a shared library (`.dll`/`.so`/`.dylib`) using the system C compiler, or loads a pre-built library if one exists. Requires Python 3.7+ and a working C compiler (`gcc`, `clang`, or MSVC via `CC` environment variable).

**Performance**: Python overhead adds approximately 300-500 ns per call (ctypes FFI + Python function dispatch). For bulk generation, use the `.bytes(n)` method with large `n` to amortize the Python overhead across many generated bytes.

---

### prng.ADC_Bolt

```python
class ADC_Bolt(seed=0)
```

Create an ADC-Bolt non-cryptographic PRNG instance.

Wraps `adcbolt_seed` and provides Pythonic methods for random number generation.

**Parameters**:
- `seed` (int, default 0) -- 64-bit seed value. Any Python int in [0, 2^64-1] is valid.

**Usage example**:

```python
import prng

# Basic usage
rng = prng.ADC_Bolt(seed=42)
print(rng.u64())          # 18446744073709551615 (random example)
print(rng.random())        # 0.723891... (float in [0, 1))
print(rng.randint(1, 6))   # 4

# Bulk generation
data = rng.bytes(1024)     # 1024 random bytes
```

**Thread safety**: Instances are not thread-safe. Create one instance per thread.

---

### prng.Tempest

```python
class Tempest(key, nonce=None)
```

Create a Tempest v3 cryptographic PRNG instance.

Wraps `tempest_init` and provides Pythonic methods for secure random generation.

**Parameters**:
- `key` (bytes, required) -- 32 bytes (256 bits) of key material. Must be exactly 32 bytes. Use `os.urandom(32)` or `secrets.token_bytes(32)` for cryptographically secure keys.
- `nonce` (bytes, optional) -- 16 bytes (128 bits) of nonce material. Defaults to 16 zero bytes if not provided. Must be exactly 16 bytes if specified. Should be unique per context under the same key.

**Raises**:
- `ValueError` if `key` is not exactly 32 bytes or `nonce` is not exactly 16 bytes.

**Usage example**:

```python
import prng
import os

# Generate a secure key
key  = os.urandom(32)
nonce = os.urandom(16)
csprng = prng.Tempest(key, nonce)

# Generate values
token = csprng.u64()              # 64-bit random integer
api_key = csprng.hex(32)          # 32 random bytes as hex string
session_id = csprng.hex(16)       # 16 random bytes as hex string

# Bulk generation
seed_material = csprng.bytes(64)  # 64 cryptographically random bytes
```

**Thread safety**: Instances are not thread-safe. Create one instance per thread.

---

### Instance Methods

The following methods are available on both `ADC_Bolt` and `Tempest` instances, unless noted otherwise.

#### .u64()

```python
.u64() -> int
```

Return a random 64-bit unsigned integer in the range [0, 2^64-1].

- **ADC_Bolt**: Uses `adcbolt_u64`. Fast, non-cryptographic.
- **Tempest**: Uses `tempest_u64`. Cryptographically secure, higher latency.

**Example**:

```python
print(rng.u64())  # 13284723984723984723
```

**Performance**: ADC_Bolt: ~400 ns/call. Tempest: ~600 ns/call (including Python FFI overhead).

---

#### .random() -- ADC_Bolt only

```python
.random() -> float
```

Return a random float in [0.0, 1.0) with 53-bit mantissa precision.

**Example**:

```python
print(rng.random())  # 0.441892374...
```

**Performance**: ~400 ns/call (equivalent to `.u64()` + float conversion).

---

#### .randint(lo, hi)

```python
.randint(lo: int, hi: int) -> int
```

Return a random integer in the inclusive range [lo, hi].

- **ADC_Bolt**: Uses modulo reduction. Suitable for games and simulations.
- **Tempest**: Uses rejection sampling for cryptographic uniformity. Suitable for lottery number generation and fair shuffles.

**Example**:

```python
print(rng.randint(1, 6))      # 4
print(rng.randint(0, 100))    # 73
```

**Performance**: ~400-600 ns/call depending on generator and range.

---

#### .bytes(n)

```python
.bytes(n: int) -> bytes
```

Return `n` random bytes as a Python bytes object.

This is the recommended method for bulk generation, as it amortizes the Python FFI overhead across many bytes. For generating 1 KB or more, the per-byte overhead is negligible.

- **ADC_Bolt**: Non-cryptographic quality. Suitable for test data, procedural content, simulation inputs.
- **Tempest**: Cryptographic quality. Suitable for key material, nonces, tokens.

**Example**:

```python
# Generate a 256-bit AES key
key = csprng.bytes(32)

# Generate a megabyte of test data
test_data = rng.bytes(1_000_000)
```

**Performance**: ADC_Bolt: ~70 Gbit/s for large n (C throughput). Tempest: ~19 Gbit/s for large n. Python overhead adds ~500 ns fixed + ~0.5 ns/byte for small n.

---

#### .hex(n) -- Tempest only

```python
.hex(n: int) -> str
```

Return `n` random bytes as a lowercase hexadecimal string.

This is the recommended method for generating human-readable tokens, API keys, and session identifiers.

**Example**:

```python
csprng = prng.Tempest(key, nonce)
print(csprng.hex(16))   # "a3f7c21b9e04d856..."
print(csprng.hex(32))   # 64-character hex string

# Use as a Flask/Django secret key
import os
secret = csprng.hex(32)
with open('.env', 'w') as f:
    f.write(f'SECRET_KEY={secret}\n')
```

**Performance**: ~1-2 us for 16-32 bytes (including hex formatting).

---

## Data Types

### adcbolt_state

```c
typedef struct {
    uint64_t u, v, w, z;
} adcbolt_state;
```

Four 64-bit state words representing an ADC-Bolt generator instance. The state evolves through carry-chain ARX operations. The struct is opaque to users: always access through the API functions, never read or write fields directly.

### tempest_state

```c
typedef struct {
    uint64_t u, v, w, z, r;
} tempest_state;
```

Four 64-bit state words plus a round counter `r` (used for the Boomerang ARX rotation schedule and round-parity tracking). The state is opaque: always access through the API functions.

### Naming Convention in C Headers vs Single Header

The individual C source files (`src/adcbolt.h`, `src/tempest_v3.h`) use internal-type names:
- `bolt3_state` (maps to `adcbolt_state` in the single header)
- `tx4_state` (maps to `tempest_state`)
- `adcbolt_next` / `tx5cmul_next` (maps to `adcbolt_u64` / `tempest_u64`)

The **single-header file** (`prng_single_header.h`) is the recommended way to use the library. It provides the simplified public API names (`adcbolt_state`, `tempest_state`, `adcbolt_u64`, `tempest_u64`, etc.) and uses `static inline` for zero-overhead inlining.

If using the individual `.c` source files directly, use the corresponding internal names. The mapping is:

| Single Header (recommended) | Internal Header | Purpose |
|---|---|---|
| `adcbolt_state` | `bolt3_state` | ADC-Bolt state |
| `adcbolt_seed` | `adcbolt_seed` | Seed initialization |
| `adcbolt_u64` | `adcbolt_next` | Generate 64-bit output |
| `adcbolt_bytes` | `adcbolt_next_bytes` | Fill byte buffer |
| `tempest_state` | `tx4_state` | Tempest v3 state |
| `tempest_init` | `tx5cmul_init` | Key + nonce initialization |
| `tempest_u64` | `tx5cmul_next` | Generate 64-bit output |
| `tempest_u64x2` | `tx5cmul_next2` | Generate dual 64-bit output |

---

## Thread Safety

### Rule: One State Per Thread

None of the functions in this library are thread-safe. The state structs are mutated on every output call, and concurrent mutation without synchronization produces a data race (undefined behavior in C).

**Correct usage (multi-threaded)**:

```c
#include <pthread.h>
#include "prng_single_header.h"

void* thread_func(void* arg) {
    int thread_id = *(int*)arg;
    adcbolt_state rng;
    adcbolt_seed(&rng, (uint64_t)(thread_id + 1) * 0x9E3779B97F4A7C15ULL);
    // ... use rng freely within this thread ...
    return NULL;
}
```

**Correct usage (Python multi-threaded)**:

```python
import threading
import prng

def worker(thread_id):
    rng = prng.ADC_Bolt(seed=thread_id + 1)
    # ... use rng within this thread ...

threads = [threading.Thread(target=worker, args=(i,)) for i in range(4)]
for t in threads: t.start()
for t in threads: t.join()
```

### Seed Variation for Multi-Threading

When seeding multiple instances, ensure seeds differ. A recommended pattern:

```c
adcbolt_state rngs[NUM_THREADS];
for (int i = 0; i < NUM_THREADS; i++) {
    adcbolt_seed(&rngs[i], base_seed + i * 0x9E3779B97F4A7C15ULL);
}
```

The golden-ratio multiplier ensures that even sequential seeds produce well-separated initial states. For cryptographic use, generate random keys independently:

```c
tempest_state csprngs[NUM_THREADS];
for (int i = 0; i < NUM_THREADS; i++) {
    uint64_t key[4];
    // Fill key from OS entropy source
    uint64_t nonce[2] = {(uint64_t)i, 0};
    tempest_init(&csprngs[i], key, nonce);
}
```

### Fork Safety

On `fork()`, the child process inherits a copy of the parent's PRNG state. If both parent and child continue generating, they will produce identical output streams because their states are identical. This is a well-known property of all deterministic PRNGs.

To avoid this:
- Call `adcbolt_seed` or `tempest_init` with fresh entropy in the child process after fork.
- Or use `pthread_atfork()` to register handlers that reseed the state.

// tempest_rng.hpp — Tempest v3 as a C++ UniformRandomBitGenerator
// (URBG), the concept required by <random> and Boost.Random.
//
// The class links against the KAT-verified C reference
// (code/tempest_v3.c) — the single source of truth — so bit-exactness
// with the published KAT (0x6BBE30BB1D12DDD0, ...) is by construction.
//
// Usage:
//   TempestRng rng(seed64);                          // deterministic
//   TempestRng rng(key4, nonce2);                    // 256-bit key
//   std::uniform_int_distribution<long> d(0, 99);
//   d(rng); std::normal_distribution<> n(0, 1); n(rng);
//   std::shuffle(v.begin(), v.end(), rng);
//
// The class satisfies the UniformRandomBitGenerator requirements:
//   result_type, min(), max(), operator().

#ifndef TEMPEST_RNG_HPP
#define TEMPEST_RNG_HPP

#include <cstdint>
#include <limits>
#include "../code/tempest_v3.h"

class TempestRng {
public:
    using result_type = std::uint64_t;

    // Deterministic seeding (64-bit seed; not for key generation).
    explicit TempestRng(std::uint64_t seed) { tx5cmul_seed(&s_, seed); }

    // Full cryptographic seeding: 256-bit key + 128-bit nonce.
    TempestRng(const std::uint64_t key[4], const std::uint64_t nonce[2]) {
        tempest_init(&s_, key, nonce);
    }

    // UniformRandomBitGenerator requirements.
    static constexpr result_type min() {
        return std::numeric_limits<result_type>::min();  // 0
    }
    static constexpr result_type max() {
        return std::numeric_limits<result_type>::max();  // 2^64-1
    }
    result_type operator()() { return tempest_u64(&s_); }

    // Dual-output block (128 bits per round), matches tempest_bytes.
    void next_bytes(std::uint8_t *buf, std::size_t n) { tempest_bytes(&s_, buf, n); }

private:
    tempest_state s_;
};

#endif // TEMPEST_RNG_HPP

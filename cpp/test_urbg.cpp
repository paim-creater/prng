// test_urbg.cpp — KAT + URBG integration test for TempestRng.
//
// Build (WSL): g++ -std=c++17 -O2 -I.. -o test_urbg test_urbg.cpp ../code/tempest_v3.c
// Run:        ./test_urbg

#include "tempest_rng.hpp"
#include <algorithm>
#include <cassert>
#include <cstdio>
#include <random>
#include <vector>

int main() {
    // --- 1. KAT: key=[1,2,3,4], nonce=[5,6], 5 published words ---
    const std::uint64_t key[4] = {1, 2, 3, 4};
    const std::uint64_t nonce[2] = {5, 6};
    const std::uint64_t want[5] = {
        0x6BBE30BB1D12DDD0ULL, 0xB9167FE6CCEC68D9ULL,
        0xCF6F7BA5C6AED360ULL, 0xA53C77D6D081BEC3ULL,
        0x7F5A13D9CBF1CD84ULL};
    TempestRng kat(key, nonce);
    for (int i = 0; i < 5; i++) {
        if (kat() != want[i]) {
            std::printf("KAT word %d FAIL\n", i + 1);
            return 1;
        }
    }
    std::printf("KAT: 5/5 PASS (0x6BBE30BB1D12DDD0, ...)\n");

    // --- 2. URBG concept: usable by <random> distributions ---
    TempestRng rng(42);
    std::uniform_int_distribution<int> d(0, 99);
    std::normal_distribution<> n(0.0, 1.0);

    long sum = 0;
    double sumn = 0.0;
    for (int i = 0; i < 100000; i++) {
        sum += d(rng);
        sumn += n(rng);
    }
    // uniform_int mean ~49.5; normal mean ~0 (loose band for CI-free check)
    std::printf("uniform_int mean: %.2f (expect ~49.5)\n", sum / 100000.0);
    std::printf("normal mean:      %.3f (expect ~0)\n", sumn / 100000.0);
    if (sum / 100000 < 40 || sum / 100000 > 59) return 1;
    if (sumn / 100000 < -1.0 || sumn / 100000 > 1.0) return 1;

    // --- 3. std::shuffle with the engine ---
    std::vector<int> v(100);
    for (int i = 0; i < 100; i++) v[i] = i;
    std::shuffle(v.begin(), v.end(), rng);
    std::sort(v.begin(), v.end());
    for (int i = 0; i < 100; i++)
        if (v[i] != i) {
            std::printf("shuffle FAIL\n");
            return 1;
        }

    // --- 4. Determinism: same seed, same stream ---
    TempestRng a(7), b(7);
    for (int i = 0; i < 1000; i++)
        if (a() != b()) {
            std::printf("determinism FAIL\n");
            return 1;
        }

    // --- 5. Static assertions for the URBG requirements ---
    static_assert(std::is_same<TempestRng::result_type, std::uint64_t>::value,
                  "result_type must be uint64_t");
    static_assert(TempestRng::min() == 0, "min must be 0");
    static_assert(TempestRng::max() == std::numeric_limits<std::uint64_t>::max(),
                  "max must be 2^64-1");

    std::printf("URBG: all checks PASS\n");
    return 0;
}

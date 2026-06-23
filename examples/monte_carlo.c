/* monte_carlo.c — Real-world example: estimate π via Monte Carlo */
#include "../prng_single_header.h"
#include <stdio.h>
#include <time.h>

int main() {
    adcbolt_state rng;
    adcbolt_seed(&rng, (uint64_t)time(NULL));

    long inside = 0, total = 10000000;
    for (long i = 0; i < total; i++) {
        double x = adcbolt_double(&rng) * 2.0 - 1.0;
        double y = adcbolt_double(&rng) * 2.0 - 1.0;
        if (x * x + y * y <= 1.0) inside++;
    }
    double pi = 4.0 * inside / total;
    printf("π ≈ %.10f (N=%ld, error=%.2e)\n", pi, total, pi - 3.1415926535);
    return 0;
}

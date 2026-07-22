/* dice_roll.c — Real-world example: game dice roller using ADC-Bolt */
#include "../prng_single_header.h"
#include <stdio.h>
#include <time.h>

int main() {
    adcbolt_state rng;
    adcbolt_seed(&rng, (uint64_t)time(NULL));

    printf("Rolling 3d6 (D&D style): ");
    for (int i = 0; i < 3; i++)
        printf("%d ", adcbolt_range(&rng, 1, 6));
    printf("\n");

    printf("10 random floats: ");
    for (int i = 0; i < 10; i++)
        printf("%.4f ", adcbolt_double(&rng));
    printf("\n");

    return 0;
}

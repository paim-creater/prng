/* gsl_tempest.c — register Tempest v3 as a GSL random number
 * generator via the official gsl_rng_type extension point.
 *
 * The implementation links against the KAT-verified C reference
 * (code/tempest_v3.c) — the single source of truth. After
 * gsl_rng_alloc(&gsl_rng_tempest), every GSL distribution function
 * (gsl_ran_uniform, gsl_ran_gaussian, gsl_ran_binomial, ...) draws
 * from Tempest.
 *
 * Build (WSL): gcc -O2 -I.. -o test_gsl test_gsl.c gsl_tempest.c ../code/tempest_v3.c -lgsl -lgslcblas
 */
#include <gsl/gsl_rng.h>
#include <stdint.h>
#include <string.h>
#include "../code/tempest_v3.h"

/* GSL state buffer = the Tempest state directly (gsl_rng_alloc
 * calloc's sizeof(gsl_tempest_state) bytes; set() initializes it). */
typedef struct {
    tempest_state s;
} gsl_tempest_state;

static void gsl_tempest_set(void *state, unsigned long int seed) {
    tx5cmul_seed(&((gsl_tempest_state *)state)->s, (uint64_t)seed);
}

static unsigned long int gsl_tempest_get(void *state) {
    return (unsigned long int)tempest_u64(&((gsl_tempest_state *)state)->s);
}

static double gsl_tempest_get_double(void *state) {
    /* [0, 1): full 64-bit output, uniform by construction. */
    return (double)tempest_u64(&((gsl_tempest_state *)state)->s) / 18446744073709551616.0;
}

/* max = ULONG_MAX on 64-bit platforms: the full uint64 output range. */
static const gsl_rng_type gsl_rng_tempest_type = {
    "tempest",                                  /* name */
    (unsigned long int)~0UL,                    /* max */
    0,                                          /* min */
    sizeof(gsl_tempest_state),                  /* size */
    &gsl_tempest_set,
    &gsl_tempest_get,
    &gsl_tempest_get_double
};

const gsl_rng_type *gsl_rng_tempest = &gsl_rng_tempest_type;

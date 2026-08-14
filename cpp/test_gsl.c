/* test_gsl.c — KAT + GSL distribution integration test for
 * the Tempest gsl_rng_type.
 *
 * Build (WSL): gcc -O2 -I.. -o test_gsl test_gsl.c gsl_tempest.c ../code/tempest_v3.c -lgsl -lgslcblas
 * Run:        ./test_gsl
 */
#include <gsl/gsl_rng.h>
#include <gsl/gsl_randist.h>
#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include "../code/tempest_v3.h"

extern const gsl_rng_type *gsl_rng_tempest;

int main(void) {
    /* --- 1. KAT through the GSL interface, key=[1,2,3,4], nonce=[5,6] --- */
    /* gsl_rng_set() only takes a seed; to inject the full KAT key we
     * temporarily use the C reference directly on the same state. */
    const uint64_t key[4] = {1, 2, 3, 4};
    const uint64_t nonce[2] = {5, 6};
    const uint64_t want[5] = {
        0x6BBE30BB1D12DDD0ULL, 0xB9167FE6CCEC68D9ULL,
        0xCF6F7BA5C6AED360ULL, 0xA53C77D6D081BEC3ULL,
        0x7F5A13D9CBF1CD84ULL};

    gsl_rng *r = gsl_rng_alloc(gsl_rng_tempest);
    if (r == NULL) {
        printf("gsl_rng_alloc FAIL\n");
        return 1;
    }
    printf("name: %s\n", gsl_rng_name(r));

    /* Initialize the GSL-allocated state with the KAT key directly. */
    tempest_state *ts = (tempest_state *)r->state;
    tempest_init(ts, key, nonce);
    for (int i = 0; i < 5; i++) {
        if (gsl_rng_get(r) != want[i]) {
            printf("KAT word %d FAIL (got %016llx)\n", i + 1,
                   (unsigned long long)gsl_rng_get(r));
            return 1;
        }
    }
    printf("KAT: 5/5 PASS through gsl_rng_get\n");

    /* --- 2. Distribution functions must work and stay in range --- */
    gsl_rng_set(r, 42);
    double sumu = 0, sumg = 0;
    double minu = 2, maxu = -1;
    unsigned long nb = 0;
    for (int i = 0; i < 100000; i++) {
        double u = gsl_rng_uniform(r);       /* [0,1) */
        if (u < minu) minu = u;
        if (u > maxu) maxu = u;
        sumu += u;
        sumg += gsl_ran_gaussian(r, 1.0);    /* N(0,1) */
        nb += gsl_ran_binomial(r, 0.3, 100); /* Bin(100, 0.3), mean 30 */
    }
    printf("uniform  mean %.4f (expect ~0.5), range [%.4f, %.4f]\n",
           sumu / 100000, minu, maxu);
    printf("gaussian mean %.3f (expect ~0)\n", sumg / 100000);
    printf("binomial mean %.2f (expect ~30)\n", nb / 100000.0);
    if (sumu / 100000 < 0.48 || sumu / 100000 > 0.52) return 1;
    if (minu < 0 || maxu >= 1) return 1;
    if (nb / 100000.0 < 28 || nb / 100000.0 > 32) return 1;

    /* --- 3. Determinism through the GSL interface --- */
    gsl_rng *r2 = gsl_rng_alloc(gsl_rng_tempest);
    gsl_rng_set(r, 7);
    gsl_rng_set(r2, 7);
    for (int i = 0; i < 1000; i++)
        if (gsl_rng_get(r) != gsl_rng_get(r2)) {
            printf("determinism FAIL\n");
            return 1;
        }

    gsl_rng_free(r);
    gsl_rng_free(r2);
    printf("GSL: all checks PASS\n");
    return 0;
}

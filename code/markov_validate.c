/* markov_validate.c — Validate Markov cipher assumption for Tempest v3
 *
 * Tests two necessary conditions for the Markov property:
 *   (1) Key Automation — differential distribution identical across
 *       independent key samples (chi-squared test across halves).
 *   (2) Per-bit DP scaling — per-bit differential probability after 2
 *       rounds follows P_2 = 1-(1-P_1)^2 under round independence.
 *
 * Compile:
 *   gcc -O3 -march=native -o markov_validate markov_validate.c \
 *        ../../github_release/src/tempest_v3.c \
 *        -I../../github_release/src -lm
 */
#include "../../github_release/src/tempest_v3.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <time.h>

#define N_SAMPLES   2000000
#define N_DIFFS     8

static uint64_t splitmix64(uint64_t *s) {
    uint64_t z = (*s += 0x9E3779B97F4A7C15ULL);
    z = (z ^ (z >> 30)) * 0xBF58476D1CE4E5B9ULL;
    z = (z ^ (z >> 27)) * 0x94D049BB133111EBULL;
    return z ^ (z >> 31);
}

int main() {
    uint64_t seed = (uint64_t)time(NULL) ^ 0xCAFEBABE;
    printf("============================================================\n");
    printf("  Markov Assumption Validation\n");
    printf("  Samples: %d, Input diffs: %d\n", N_SAMPLES, N_DIFFS);
    printf("============================================================\n\n");
    printf("  Test 1: Key Automation — HKW distribution consistency\n");
    printf("  Test 2: Per-bit DP scaling: P(flip in 2R) vs 1-(1-P_1)^2\n\n");

    double global_avg_p1 = 0, global_avg_p2 = 0;
    int global_consistent = 0, global_total = 0;

    for (int d = 0; d < N_DIFFS; d++) {
        uint64_t delta_u = 1ULL << d;
        /* Per-bit differential counts */
        long dp1[64] = {0}, dp2[64] = {0};
        long tot1[64] = {0}, tot2[64] = {0};

        /* HW distributions per half (4 halves) */
        double hw_dist_1r[4][65] = {{0}};
        double hw_dist_2r[4][65] = {{0}};
        long hw_n[4] = {0};

        for (int i = 0; i < N_SAMPLES; i++) {
            uint64_t key[4], nonce[2];
            for (int j = 0; j < 4; j++) key[j] = splitmix64(&seed);
            for (int j = 0; j < 2; j++) nonce[j] = splitmix64(&seed);

            tempest_state s1, s2;
            tempest_init(&s1, key, nonce);
            s2 = s1;
            s2.u ^= delta_u;

            uint64_t o1a = tempest_u64(&s1);
            uint64_t o1b = tempest_u64(&s2);
            uint64_t d1 = o1a ^ o1b;
            int hw1 = __builtin_popcountll(d1);

            uint64_t o2a = tempest_u64(&s1);
            uint64_t o2b = tempest_u64(&s2);
            uint64_t d2 = o2a ^ o2b;
            int hw2 = __builtin_popcountll(d2);

            int h = i % 4;
            hw_dist_1r[h][hw1]++; hw_n[h]++;
            hw_dist_2r[h][hw2]++;

            for (int b = 0; b < 64; b++) {
                if (d1 & (1ULL << b)) dp1[b]++;
                if (d2 & (1ULL << b)) dp2[b]++;
            }
        }

        /* Key Automation: chi-squared across halves for HW distribution */
        double chi2_1r = 0, chi2_2r = 0;
        int df = 0;
        for (int hw = 0; hw <= 64; hw++) {
            double avg1 = 0, avg2 = 0;
            for (int h = 0; h < 4; h++) {
                avg1 += hw_dist_1r[h][hw] / hw_n[h];
                avg2 += hw_dist_2r[h][hw] / hw_n[h];
            }
            avg1 /= 4; avg2 /= 4;
            for (int h = 0; h < 4; h++) {
                double o1 = hw_dist_1r[h][hw] / hw_n[h];
                double o2 = hw_dist_2r[h][hw] / hw_n[h];
                if (avg1 > 1e-10) { chi2_1r += (o1-avg1)*(o1-avg1)*4/avg1; df++; }
                if (avg2 > 1e-10) { chi2_2r += (o2-avg2)*(o2-avg2)*4/avg2; }
            }
        }
        double chi2_1r_norm = chi2_1r / (df > 0 ? df : 1);
        double chi2_2r_norm = chi2_2r / (df > 0 ? df : 1);

        /* Per-bit DP scaling */
        int consistent = 0;
        double sum_p1 = 0, sum_p2 = 0;
        for (int b = 0; b < 64; b++) {
            double p1 = (double)dp1[b] / N_SAMPLES;
            double p2 = (double)dp2[b] / N_SAMPLES;
            double expected = 1.0 - (1.0 - p1) * (1.0 - p1);
            sum_p1 += p1; sum_p2 += p2;
            if (fabs(p2 - expected) < 0.003) consistent++;
        }
        global_avg_p1 += sum_p1 / 64;
        global_avg_p2 += sum_p2 / 64;
        global_consistent += consistent;
        global_total += 64;

        printf("Diff %2d: chi2_1r=%.2f chi2_2r=%.2f | "
               "bits consistent=%2d/64 | avg P1=%.4f P2=%.4f "
               "(pred=%.4f)\n",
               d, chi2_1r_norm, chi2_2r_norm,
               consistent, sum_p1/64, sum_p2/64,
               1.0 - (1.0 - sum_p1/64) * (1.0 - sum_p1/64));
    }

    printf("\n============================================================\n");
    printf("  Summary\n");
    printf("============================================================\n");
    double overall_p1 = global_avg_p1 / N_DIFFS;
    double overall_p2 = global_avg_p2 / N_DIFFS;
    double overall_pred = 1.0 - (1.0 - overall_p1) * (1.0 - overall_p1);
    printf("  Average P(bit flip | 1 round):  %.4f (expect 0.500)\n", overall_p1);
    printf("  Average P(bit flip | 2 rounds): %.4f\n", overall_p2);
    printf("  Markov prediction:              %.4f\n", overall_pred);
    printf("  Per-bit consistency rate:       %d/%d (%.1f%%)\n",
           global_consistent, global_total,
           100.0 * global_consistent / global_total);
    printf("\n");
    printf("  chi^2 ≈ 1.0 indicates identical distributions across\n");
    printf("  independent key samples → key automation property holds.\n");
    printf("  chi^2 >> 1.0 would indicate state-dependent biases.\n");
    printf("\n  The Weyl sequence provides provable round differentiation\n");
    printf("  (Phi_r != Phi_{r+1}), which is the structural basis for\n");
    printf("  the Markov cipher assumption in Tempest v3.\n");
    printf("============================================================\n");
    return 0;
}

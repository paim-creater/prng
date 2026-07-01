/* tempest_test.c — self-test for Tempest v3 via libtomcrypt PRNG API
 *
 * Build:
 *   gcc -O3 -I. -Isrc/tempest -o tempest_test tempest_test.c \
 *       src/tempest/tempest_v3.c src/prngs/tempest_prng.c -ltomcrypt -lm
 *   ./tempest_test
 */
#include <tomcrypt.h>
#include <stdio.h>
#include <string.h>

extern const struct ltc_prng_descriptor tempest_prng_desc;

int main(void) {
    int failures = 0;

    /* Register */
    int idx = register_prng(&tempest_prng_desc);
    if (idx == -1) { printf("FAIL: register\n"); return 1; }
    printf("Register: PASS (idx=%d)\n", idx);

    /* Self-test */
    if (prng_descriptor[idx].test() != CRYPT_OK) {
        printf("FAIL: test()\n"); failures++;
    } else printf("Self-test: PASS\n");

    /* Start + Ready + Read + Done */
    prng_state ps;
    unsigned char buf[64];

    if (prng_descriptor[idx].start(&ps) != CRYPT_OK) {
        printf("FAIL: start()\n"); failures++;
    } else printf("Start: PASS\n");

    if (prng_descriptor[idx].ready(&ps) != CRYPT_OK) {
        printf("FAIL: ready()\n"); failures++;
    } else printf("Ready: PASS\n");

    unsigned long got = prng_descriptor[idx].read(buf, 64, &ps);
    if (got != 64) { printf("FAIL: read() got %lu\n", got); failures++; }
    else printf("Read 64 bytes: PASS\n");

    /* Verify non-zero */
    int all_zero = 1;
    for (int i = 0; i < 64; i++) if (buf[i]) { all_zero = 0; break; }
    if (all_zero) { printf("FAIL: all-zero output\n"); failures++; }
    else printf("Non-zero output: PASS\n");

    if (prng_descriptor[idx].done(&ps) != CRYPT_OK) {
        printf("FAIL: done()\n"); failures++;
    } else printf("Done: PASS\n");

    /* Determinism: same after export/import */
    unsigned char state_buf[256];
    unsigned long state_len = sizeof(state_buf);
    unsigned char out1[32], out2[32];

    prng_descriptor[idx].start(&ps);
    prng_descriptor[idx].ready(&ps);
    prng_descriptor[idx].read(out1, 16, &ps);
    prng_descriptor[idx].export(state_buf, &state_len, &ps);
    prng_descriptor[idx].done(&ps);
    prng_descriptor[idx].import(state_buf, state_len, &ps);
    prng_descriptor[idx].read(out2, 16, &ps);
    prng_descriptor[idx].done(&ps);
    if (memcmp(out1, out2, 16) != 0) {
        printf("FAIL: export/import determinism\n"); failures++;
    } else printf("Export/Import determinism: PASS\n");

    if (failures) printf("\n%d test(s) FAILED\n", failures);
    else printf("\nAll tests PASS\n");
    return failures ? 1 : 0;
}

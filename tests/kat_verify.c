/* kat_verify.c — KAT verification for CI.
 * Compile: gcc -O3 -o kat_verify kat_verify.c src/tempest_v3.c -Isrc
 * Returns 0 on success, 1 on mismatch. */
#include "src/kat_tempest.h"
#include <stdio.h>
int main() {
    tempest_state s;
    if (tempest_kat_verify(&s) == 0) {
        printf("KAT: PASS\n");
        return 0;
    }
    printf("KAT: FAIL\n");
    return 1;
}

/* gen_kat_mds.c — Generate KAT vectors for MDS-upgraded Tempest v3 */
#include "src/tempest_v3.h"
#include <stdio.h>

int main() {
    uint64_t key[4] = {1, 2, 3, 4};
    uint64_t nonce[2] = {5, 6};
    tx4_state s;

    printf("/* MDS-upgraded Tempest v3 KAT vectors\n");
    printf(" * key={1,2,3,4}, nonce={5,6}, first 10 outputs\n");
    printf(" * Phase B changed from XOR-ROT to MDS matrix (branch=5)\n */\n\n");

    tx5cmul_init(&s, key, nonce);
    printf("static const uint64_t kat_tempest_expected[KAT_TEMPEST_COUNT] = {\n");
    for (int i = 0; i < 10; i++) {
        uint64_t v = tx5cmul_next(&s);
        printf("    0x%016llXULL%s\n",
               (unsigned long long)v,
               i < 9 ? "," : "");
    }
    printf("};\n");

    return 0;
}

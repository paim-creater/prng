/* gen_kat_tempest.c — Generate KAT for Tempest v3 */
#include <stdio.h>
#include <stdint.h>
#include "tempest_v3.h"

int main(void) {
    tempest_state s;
    uint64_t key[4] = {1, 2, 3, 4};
    uint64_t nonce[2] = {5, 6};
    tempest_init(&s, key, nonce);
    for (int i = 0; i < 10; i++) {
        uint64_t out = tempest_u64(&s);
        printf("    0x%016llXULL,\n", (unsigned long long)out);
    }
    return 0;
}

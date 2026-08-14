#include <stdio.h>
#include <stdint.h>
#include "tempest_v3.h"
int main(void) {
    tempest_state s;
    uint64_t key[4] = {1,2,3,4}, nonce[2] = {5,6};
    tempest_init(&s, key, nonce);
    for (int i = 0; i < 10; i++) {
        uint64_t o = tempest_u64(&s);
        printf("0x%016llx\n", (unsigned long long)o);
    }
    return 0;
}

#include <stdio.h>
#include <stdint.h>
#include "tempest_v3.h"
int main() {
    tempest_state s;
    uint64_t key[4]={1,2,3,4},nonce[2]={5,6};
    tempest_init(&s,key,nonce);
    for(long i=0;i<1000000;i++) {
        uint64_t r=tempest_u64(&s);
        fwrite(&r,8,1,stdout);
    }
    return 0;
}

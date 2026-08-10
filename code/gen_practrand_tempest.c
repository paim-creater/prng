#include "tempest_v3.h"
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
int main(int ac, char** av) {
    uint64_t k[4] = {0x9E3779B97F4A7C15ULL, 0x6A09E667F3BCC909ULL,
                     0x3243F6A8885A308DULL, 0xB7E151628AED2A6BULL};
    uint64_t n[2] = {0xDEADBEEFCAFE1234ULL, 0xFEEDFACEBABE5678ULL};
    tempest_state s;
    tempest_init(&s, k, n);
    int64_t nbytes = (ac > 1) ? strtoll(av[1], NULL, 10) : (128LL*1024*1024*1024);
    fprintf(stderr, "Tempest v3 PractRand: %lld bytes...\n", (long long)nbytes);
    int64_t w = 0;
    while (w < nbytes) {
        uint64_t r[2];
        tempest_u64x2(&s, r);
        fwrite(r, 1, 16, stdout);
        w += 16;
    }
    fflush(stdout);
    return 0;
}

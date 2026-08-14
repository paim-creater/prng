#include "tempest_v3.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
int main(int ac, char** av) {
    int ns = (ac>1) ? atoi(av[1]) : 100;
    const char* out = (ac>2) ? av[2] : "tempest_nist_100streams.bits";
    FILE* f = fopen(out, "wb");
    if (!f) { fprintf(stderr, "Cannot open %s\n", out); return 1; }
    printf("Tempest v3: %d streams x 1M bits...\n", ns);
    for (int i = 0; i < ns; i++) {
        uint64_t k[4] = {(uint64_t)(i+1)*0x9E3779B97F4A7C15ULL,
                         (uint64_t)(i+1)*0x6A09E667F3BCC909ULL,
                         (uint64_t)(i+1)*0x3243F6A8885A308DULL,
                         (uint64_t)(i+1)*0xB7E151628AED2A6BULL};
        uint64_t n[2] = {(uint64_t)i, (uint64_t)i << 32};
        tempest_state s;
        tempest_init(&s, k, n);
        for (int j = 0; j < 1000000/64; j++) {
            uint64_t r[2];
            tempest_u64x2(&s, r);
            for (int w = 0; w < 2; w++) {
                for (int b = 7; b >= 0; b--) {
                    unsigned char byte = (unsigned char)(r[w] >> (b*8));
                    fputc(byte, f);
                }
            }
        }
    }
    fclose(f);
    printf("Done: %s (%.1f MB)\n", out, (double)ns * 0.125);
    return 0;
}

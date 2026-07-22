/* generate_token.c — Real-world example: secure API token generation */
#include "../prng_single_header.h"
#include <stdio.h>

int main() {
    /* In production, load key/nonce from secure storage or environment */
    uint64_t key[4] = {
        0x2B7E151628AED2A6ULL, 0xAB7158809CF4F3C7ULL,
        0x62E7160F38B4DA56ULL, 0xA784D9045190CFEFULL
    };
    uint64_t nonce[2] = {0xDEADBEEFCAFE1234ULL, 0xFEEDFACEBABE5678ULL};

    tempest_state csprng;
    tempest_init(&csprng, key, nonce);

    /* Generate a 256-bit API token (32 bytes of randomness) */
    uint8_t token[32];
    tempest_bytes(&csprng, token, sizeof(token));

    printf("API Token: ");
    for (int i = 0; i < 32; i++)
        printf("%02x", token[i]);
    printf("\n");

    return 0;
}

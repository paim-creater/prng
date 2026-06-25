/* uuid_generator.c — Generate UUIDs v4 using Tempest v3
 *
 * Compile: gcc -O3 -o uuidgen examples/uuid_generator.c src/tempest_v3.c -I.
 * Usage:   ./uuidgen [count]
 *
 * Output:
 *   $ ./uuidgen 3
 *   a1b2c3d4-e5f6-4789-ab12-cd34ef567890
 *   12345678-9abc-4def-b123-4567890abcde
 *   ...
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include "src/tempest_v3.h"

static void generate_uuid(tx4_state *csprng) {
    uint8_t bytes[16];
    for (int i = 0; i < 16; i += 8) {
        uint64_t r = tx5cmul_next(csprng);
        memcpy(bytes + i, &r, 8);
    }

    /* Set version 4 and variant */
    bytes[6] = (bytes[6] & 0x0F) | 0x40;   /* version 4 */
    bytes[8] = (bytes[8] & 0x3F) | 0x80;   /* variant 10 */

    printf("%02x%02x%02x%02x-%02x%02x-%02x%02x-%02x%02x-%02x%02x%02x%02x%02x%02x\n",
           bytes[0], bytes[1], bytes[2], bytes[3],
           bytes[4], bytes[5], bytes[6], bytes[7],
           bytes[8], bytes[9], bytes[10], bytes[11],
           bytes[12], bytes[13], bytes[14], bytes[15]);
}

/* Simple entropy seeding for Windows / Unix */
static void seed_from_os(uint64_t key[4], uint64_t nonce[2]) {
#if defined(_WIN32)
    HCRYPTPROV hcp;
    if (CryptAcquireContext(&hcp, NULL, NULL, PROV_RSA_FULL, CRYPT_VERIFYCONTEXT)) {
        CryptGenRandom(hcp, 32, (BYTE*)key);
        CryptGenRandom(hcp, 16, (BYTE*)nonce);
        CryptReleaseContext(hcp, 0);
    }
#else
    FILE *fp = fopen("/dev/urandom", "rb");
    if (fp) {
        if (fread(key, 1, 32, fp) < 32) { /* fallback */ }
        if (fread(nonce, 1, 16, fp) < 16) { /* fallback */ }
        fclose(fp);
    }
#endif
    /* Always mix in time for extra entropy */
    uint64_t t = (uint64_t)time(NULL);
    for (int i = 0; i < 4; i++) key[i] ^= t ^ ((uint64_t)&key + i);
    for (int i = 0; i < 2; i++) nonce[i] ^= t ^ ((uint64_t)&nonce + i + 4);
}

int main(int argc, char **argv) {
    int count = (argc > 1) ? atoi(argv[1]) : 1;
    if (count < 1 || count > 10000) {
        fprintf(stderr, "Usage: %s [1-10000]\n", argv[0]);
        return 1;
    }

    uint64_t key[4], nonce[2];
    seed_from_os(key, nonce);

    tx4_state csprng;
    tx5cmul_init(&csprng, key, nonce);

    for (int i = 0; i < count; i++)
        generate_uuid(&csprng);

    return 0;
}

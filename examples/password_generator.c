/* password_generator.c — Generate strong random passwords using Tempest v3
 *
 * Compile: gcc -O3 -o passgen examples/password_generator.c src/tempest_v3.c -I.
 * Usage:   ./passgen [length] [count]
 *
 * Example:
 *   $ ./passgen 20 5
 *   Xk7#mP2$vL9@nR4!qW8%
 *   aB3$xK9!mN2#pR7@vL5^
 *   ...
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#ifdef _WIN32
#include <windows.h>
#include <wincrypt.h>
#endif
#include "src/tempest_v3.h"

/* Character sets */
static const char UPPER[] = "ABCDEFGHJKLMNPQRSTUVWXYZ";       /* no I,O (ambiguous) */
static const char LOWER[] = "abcdefghjkmnpqrstuvwxyz";         /* no i,l,o */
static const char DIGITS[] = "23456789";                        /* no 0,1 */
static const char SYMBOLS[] = "!@#$%^&*()-_=+[]{};:,.<>?";

static void generate_passwords(tx4_state *csprng, int length, int count) {
    /* Build full charset */
    char charset[256];
    snprintf(charset, sizeof(charset), "%s%s%s%s", UPPER, LOWER, DIGITS, SYMBOLS);
    int cs_len = strlen(charset);

    for (int i = 0; i < count; i++) {
        char pwd[128];
        /* Ensure at least one char from each set */
        pwd[0] = UPPER[tx5cmul_next(csprng) % (sizeof(UPPER) - 1)];
        pwd[1] = LOWER[tx5cmul_next(csprng) % (sizeof(LOWER) - 1)];
        pwd[2] = DIGITS[tx5cmul_next(csprng) % (sizeof(DIGITS) - 1)];
        pwd[3] = SYMBOLS[tx5cmul_next(csprng) % (sizeof(SYMBOLS) - 1)];

        /* Fill rest from full charset */
        for (int j = 4; j < length; j++)
            pwd[j] = charset[tx5cmul_next(csprng) % cs_len];

        /* Shuffle using Fisher-Yates */
        for (int j = length - 1; j > 0; j--) {
            uint64_t k = tx5cmul_next(csprng) % (uint64_t)(j + 1);
            char tmp = pwd[j]; pwd[j] = pwd[k]; pwd[k] = tmp;
        }
        pwd[length] = '\0';
        printf("%s\n", pwd);
    }
}

int main(int argc, char **argv) {
    int length = (argc > 1) ? atoi(argv[1]) : 16;
    int count  = (argc > 2) ? atoi(argv[2]) : 10;

    if (length < 8) { fprintf(stderr, "Minimum password length: 8\n"); return 1; }
    if (length > 127) { fprintf(stderr, "Maximum password length: 127\n"); return 1; }

    /* Seed CSPRNG from OS entropy */
    tx4_state csprng;
#if defined(_WIN32) || defined(_WIN64)
    uint64_t key[4], nonce[2];
    HCRYPTPROV hcp;
    if (CryptAcquireContext(&hcp, NULL, NULL, PROV_RSA_FULL, 0)) {
        CryptGenRandom(hcp, sizeof(key), (BYTE*)key);
        CryptGenRandom(hcp, sizeof(nonce), (BYTE*)nonce);
        CryptReleaseContext(hcp, 0);
    }
#else
    uint64_t key[4], nonce[2];
    FILE *fp = fopen("/dev/urandom", "rb");
    if (fp) { fread(key, 1, 32, fp); fread(nonce, 1, 16, fp); fclose(fp); }
    else {
        /* Fallback: mix time + pid (weak but avoids UB).
           Note: ~30 bits entropy — NOT cryptographically secure.
           Ensure /dev/urandom is available in production. */
        uint64_t t = (uint64_t)time(NULL) ^ (uint64_t)getpid();
        key[0] = t; key[1] = t ^ 0x9E3779B97F4A7C15ULL;
        key[2] = t ^ 0x6A09E667F3BCC908ULL; key[3] = t ^ 0xBB67AE8584CAA73BULL;
        nonce[0] = t ^ 0x3243F6A8885A308DULL; nonce[1] = t ^ 0xB7E151628AED2A6BULL;
    }
#endif

    tx5cmul_init(&csprng, key, nonce);
    generate_passwords(&csprng, length, count);
    return 0;
}

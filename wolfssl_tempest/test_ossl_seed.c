/* test_ossl_seed.c — KAT + OpenSSL API test for the Tempest
 * SEED-SOURCE provider.
 *
 * Build (WSL): gcc -O2 -o test_ossl_seed test_ossl_seed.c \
 *              tempest_ossl_seed.c ../code/tempest_v3.c \
 *              -lcrypto -ldl -pthread
 * Run: ./test_ossl_seed
 *
 * KAT path: instantiate() with 48-byte additional input =
 * key[1,2,3,4] || nonce[5,6]; generate() must emit the published
 * 5-block KAT stream through the OpenSSL EVP_RAND API.
 */
#include <openssl/core_names.h>
#include <openssl/evp.h>
#include <openssl/err.h>
#include <openssl/provider.h>
#include <stdio.h>
#define DBG(msg) do { fprintf(stderr, "[dbg] %s\n", msg); } while (0)
#include <stdint.h>
#include <string.h>

static const uint64_t kat_want[5] = {
    0x6BBE30BB1D12DDD0ULL, 0xB9167FE6CCEC68D9ULL,
    0xCF6F7BA5C6AED360ULL, 0xA53C77D6D081BEC3ULL,
    0x7F5A13D9CBF1CD84ULL};

static int u64_put(unsigned char *buf, uint64_t v) {
    for (int i = 0; i < 8; i++) buf[i] = (unsigned char)(v >> (8 * i));
    return 8;
}

int main(void) {
    OSSL_PROVIDER *prov = OSSL_PROVIDER_load(NULL, "tempest_ossl_seed");
    if (prov == NULL) {
        fprintf(stderr, "provider load failed (set OPENSSL_MODULES=.)\n");
        return 1;
    }
    printf("provider loaded: tempest_ossl_seed\n");

    DBG("before fetch");
    EVP_RAND *rand = EVP_RAND_fetch(NULL, "tempest", NULL);
    DBG("after fetch");
    if (rand == NULL) {
        fprintf(stderr, "EVP_RAND_fetch(tempest-seed) failed\n");
        ERR_print_errors_fp(stderr);
        return 1;
    }
    DBG("before ctx_new");
    EVP_RAND_CTX *ctx = EVP_RAND_CTX_new(rand, NULL);  /* no parent */
    DBG("after ctx_new");
    if (ctx == NULL) { fprintf(stderr, "ctx new failed\n"); return 1; }

    /* KAT: deterministic seed via additional input. */
    unsigned char adin[48];
    u64_put(adin, 1); u64_put(adin + 8, 2);
    u64_put(adin + 16, 3); u64_put(adin + 24, 4);
    u64_put(adin + 32, 5); u64_put(adin + 40, 6);

    DBG("before instantiate");
    if (!EVP_RAND_instantiate(ctx, 128, 0, adin, sizeof(adin), NULL)) {
        fprintf(stderr, "instantiate failed\n");
        return 1;
    }

    unsigned char out[40];
    DBG("before generate");
    /* OpenSSL 3.5: EVP_RAND_generate returns int (1 = success). */
    if (!EVP_RAND_generate(ctx, out, sizeof(out), 128, 0, NULL, 0)) {
        fprintf(stderr, "generate failed\n");
        ERR_print_errors_fp(stderr);
        return 1;
    }
    DBG("after generate");

    int ok = 1;
    for (int i = 0; i < 5; i++) {
        uint64_t v;
        memcpy(&v, out + 8 * i, 8);
        if (v != kat_want[i]) {
            printf("KAT word %d FAIL: got %016llx want %016llx\n",
                   i + 1, (unsigned long long)v,
                   (unsigned long long)kat_want[i]);
            ok = 0;
        }
    }
    printf("KAT through EVP_RAND API: %s\n", ok ? "5/5 PASS" : "FAIL");

    /* Distribution sanity through the OpenSSL API. */
    unsigned char big[256];
    if (!EVP_RAND_generate(ctx, big, sizeof(big), 128, 0, NULL, 0)) {
        fprintf(stderr, "second generate failed\n");
        return 1;
    }
    unsigned long long acc = 0;
    for (size_t i = 0; i < sizeof(big); i++) acc += big[i];
    printf("256-byte block byte-mean: %.3f (expect ~127.5)\n",
           (double)acc / sizeof(big));

    /* State query. */
    char state[64] = {0};
    OSSL_PARAM params[] = {
        OSSL_PARAM_utf8_string(OSSL_RAND_PARAM_STATE, state, sizeof(state)),
        OSSL_PARAM_END
    };
    EVP_RAND_CTX_get_params(ctx, params);
    printf("RAND state: %s\n", state);

    EVP_RAND_CTX_free(ctx);
    EVP_RAND_free(rand);
    OSSL_PROVIDER_unload(prov);
    printf("provider test: %s\n", ok ? "PASS" : "FAIL");
    return ok ? 0 : 1;
}

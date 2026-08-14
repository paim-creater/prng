/* tempest_ossl_seed.c — OpenSSL 3.x provider: Tempest v3 as a
 * SEED-SOURCE RAND algorithm.
 *
 * This is the official third-party extension point of OpenSSL 3.x:
 * a provider registering an OSSL_FUNC_rand dispatch table. The seed
 * source sits OUTSIDE the FIPS boundary and feeds entropy to the
 * DRBG stack (the same role the built-in "seed_src" plays) — a
 * legitimate integration point, unlike replacing a TLS library's
 * trust-root RNG (entropy-source semantics: reseed, prediction
 * resistance), which is why this works where those integrations do
 * not.
 *
 * Semantics: on instantiate(), 48 bytes of entropy are taken from
 * the parent RAND (the OS) — 32 bytes key + 16 bytes nonce — and
 * used to seed Tempest v3 (KAT-verified C reference). generate()
 * then emits the Tempest stream as seed material.
 *
 * Build (WSL): gcc -fPIC -shared -O2 -o tempest_ossl_seed.so \
 *              tempest_ossl_seed.c ../code/tempest_v3.c
 * Test:  ./test_ossl_seed        (KAT + OpenSSL API test)
 * Load:  openssl rand -provider-path . -provider tempest_ossl_seed 16
 */
#include <openssl/core.h>
#include <openssl/core_dispatch.h>
#include <openssl/core_names.h>
#include <openssl/rand.h>
#include <openssl/evp.h>
#include <openssl/err.h>
#include <string.h>
#include <stdint.h>
#include "../code/tempest_v3.h"

#define TEMPEST_SEED_LEN 48  /* 32 key + 16 nonce */
#define TEMPEST_MAX_REQUEST (1UL << 30)  /* max bytes per generate */

typedef struct {
    void *provctx;
    EVP_RAND_CTX *parent;
    const OSSL_DISPATCH *parent_calls;
    unsigned char seed[TEMPEST_SEED_LEN];
    size_t seed_len;
    tempest_state ts;
    int seeded;
    int strength;
} tempest_seed_ctx;

/* --------------------------------------------------------------
 * RAND dispatch
 * -------------------------------------------------------------- */

static void *tempest_seed_newctx(void *provctx, void *parent,
                                 const OSSL_DISPATCH *parent_calls) {
    tempest_seed_ctx *ctx = OPENSSL_zalloc(sizeof(*ctx));
    if (ctx == NULL) return NULL;
    ctx->provctx = provctx;
    ctx->parent = parent;
    ctx->parent_calls = parent_calls;
    ctx->seeded = 0;
    return ctx;
}

static void tempest_seed_freectx(void *vctx) {
    tempest_seed_ctx *ctx = vctx;
    if (ctx == NULL) return;
    OPENSSL_clear_free(ctx, sizeof(*ctx));
}

static int tempest_seed_instantiate(void *vctx, unsigned int strength,
                                    int prediction_resistance,
                                    const unsigned char *adin,
                                    size_t adin_len,
                                    const OSSL_PARAM params[]) {
    tempest_seed_ctx *ctx = vctx;
    if (ctx == NULL) return 0;
    ctx->strength = (int)strength;

    if (adin_len == TEMPEST_SEED_LEN) {
        /* Deterministic seeding (test/KAT path): the additional
         * input carries the 48-byte key||nonce verbatim. */
        memcpy(ctx->seed, adin, TEMPEST_SEED_LEN);
        ctx->seed_len = TEMPEST_SEED_LEN;
    } else if (ctx->parent_calls != NULL
               && OSSL_FUNC_rand_get_seed(ctx->parent_calls) != NULL) {
        /* Normal path: take 48 bytes of entropy from the parent
         * RAND (the OS). */
        OSSL_FUNC_rand_get_seed_fn *parent_get_seed =
            (OSSL_FUNC_rand_get_seed_fn *)
                OSSL_FUNC_rand_get_seed(ctx->parent_calls);
        unsigned char *seed_ptr = NULL;
        size_t seed_len = parent_get_seed(ctx->parent, &seed_ptr, strength,
                                          TEMPEST_SEED_LEN, TEMPEST_SEED_LEN,
                                          prediction_resistance, adin,
                                          adin_len);
        if (seed_len < TEMPEST_SEED_LEN || seed_ptr == NULL) {
            return 0;
        }
        memcpy(ctx->seed, seed_ptr, TEMPEST_SEED_LEN);
        ctx->seed_len = TEMPEST_SEED_LEN;
    } else {
        /* No parent and no deterministic seed: refuse (a seed source
         * without entropy is a dead key — the exact class this
         * project's framework detects). */
        return 0;
    }

    if (ctx->seed_len < TEMPEST_SEED_LEN) return 0;

    {
        uint64_t key[4], nonce[2];
        memcpy(key, ctx->seed, 32);
        memcpy(nonce, ctx->seed + 32, 16);
        tempest_init(&ctx->ts, key, nonce);
    }
    ctx->seeded = 1;
    return 1;
}

static int tempest_seed_uninstantiate(void *vctx) {
    tempest_seed_ctx *ctx = vctx;
    if (ctx == NULL) return 0;
    OPENSSL_cleanse(&ctx->ts, sizeof(ctx->ts));
    OPENSSL_cleanse(ctx->seed, sizeof(ctx->seed));
    ctx->seed_len = 0;
    ctx->seeded = 0;
    return 1;
}

static size_t tempest_seed_generate(void *vctx, unsigned char *out,
                                    size_t outlen,
                                    unsigned int strength,
                                    int prediction_resistance,
                                    const unsigned char *adin,
                                    size_t adin_len) {
    tempest_seed_ctx *ctx = vctx;
    if (ctx == NULL || !ctx->seeded) return 0;
    if (strength > (unsigned int)ctx->strength) return 0;
    if (out == NULL || outlen == 0) return 0;
    /* The Tempest stream IS the seed material. One word per round
     * (the tempest_u64 path, matching the published KAT stream). */
    size_t i = 0;
    for (; i + 8 <= outlen; i += 8) {
        uint64_t w = tempest_u64(&ctx->ts);
        memcpy(out + i, &w, 8);
    }
    if (i < outlen) {
        uint64_t w = tempest_u64(&ctx->ts);
        memcpy(out + i, &w, outlen - i);
    }
    return outlen;
}

/* seed sources produce no nonces */
static size_t tempest_seed_nonce(void *vctx, unsigned char *out,
                                 size_t outlen, int strength,
                                 const void *adin, size_t adin_len) {
    return 0;
}

static int tempest_seed_get_seed(void *vctx, unsigned char **out,
                                 size_t *outlen, size_t entropy,
                                 size_t min_len, size_t max_len,
                                 const unsigned char *adin,
                                 size_t adin_len) {
    tempest_seed_ctx *ctx = vctx;
    if (ctx == NULL || !ctx->seeded) return 0;
    if (entropy > 0) return 0;  /* we cannot supply entropy on demand */
    if (max_len > TEMPEST_SEED_LEN) return 0;
    *out = ctx->seed;
    *outlen = max_len;
    return 1;
}

static void tempest_seed_clear_seed(void *vctx, unsigned char *out,
                                    size_t outlen) {
    tempest_seed_ctx *ctx = vctx;
    if (ctx == NULL || out == NULL) return;
    OPENSSL_cleanse(out, outlen);
    if (out == ctx->seed) ctx->seed_len = 0;
}

static int tempest_seed_verify_zeroization(void *vctx) {
    return 1;  /* state is cleansed on free/uninstantiate */
}

static int tempest_seed_get_params(OSSL_PARAM params[]) {
    /* No provider-level RAND params in the OpenSSL 3.5 API. */
    return 1;
}

static int tempest_seed_get_ctx_params(void *vctx, OSSL_PARAM params[]) {
    tempest_seed_ctx *ctx = vctx;
    OSSL_PARAM *p;

    if (ctx == NULL) return 0;
    p = OSSL_PARAM_locate(params, OSSL_RAND_PARAM_STATE);
    if (p != NULL) {
        const char *state = ctx->seeded ? "ready" : "empty";
        if (!OSSL_PARAM_set_utf8_string(p, state)) return 0;
    }
    p = OSSL_PARAM_locate(params, OSSL_RAND_PARAM_STRENGTH);
    if (p != NULL && !OSSL_PARAM_set_int(p, ctx->strength)) return 0;
    p = OSSL_PARAM_locate(params, OSSL_RAND_PARAM_MAX_REQUEST);
    if (p != NULL && !OSSL_PARAM_set_size_t(p, TEMPEST_MAX_REQUEST))
        return 0;
    return 1;
}

static const OSSL_PARAM *tempest_seed_gettable_ctx_params(void *vctx,
                                                          void *provctx) {
    static const OSSL_PARAM params[] = {
        OSSL_PARAM_utf8_string(OSSL_RAND_PARAM_STATE, NULL, 0),
        OSSL_PARAM_int(OSSL_RAND_PARAM_STRENGTH, NULL),
        OSSL_PARAM_size_t(OSSL_RAND_PARAM_MAX_REQUEST, NULL),
        OSSL_PARAM_END
    };
    return params;
}

static const OSSL_PARAM *tempest_seed_settable_ctx_params(void *vctx,
                                                          void *provctx) {
    static const OSSL_PARAM params[] = { OSSL_PARAM_END };
    return params;
}

static int tempest_seed_enable_locking(void *vctx) { return 1; }
static int tempest_seed_lock(void *vctx) { return 1; }
static void tempest_seed_unlock(void *vctx) {}

/* --------------------------------------------------------------
 * Provider dispatch
 * -------------------------------------------------------------- */

static const OSSL_DISPATCH tempest_seed_rand_functions[] = {
    { OSSL_FUNC_RAND_NEWCTX, (void (*)(void))tempest_seed_newctx },
    { OSSL_FUNC_RAND_FREECTX, (void (*)(void))tempest_seed_freectx },
    { OSSL_FUNC_RAND_INSTANTIATE, (void (*)(void))tempest_seed_instantiate },
    { OSSL_FUNC_RAND_UNINSTANTIATE, (void (*)(void))tempest_seed_uninstantiate },
    { OSSL_FUNC_RAND_GENERATE, (void (*)(void))tempest_seed_generate },
    { OSSL_FUNC_RAND_NONCE, (void (*)(void))tempest_seed_nonce },
    { OSSL_FUNC_RAND_GET_SEED, (void (*)(void))tempest_seed_get_seed },
    { OSSL_FUNC_RAND_CLEAR_SEED, (void (*)(void))tempest_seed_clear_seed },
    { OSSL_FUNC_RAND_VERIFY_ZEROIZATION, (void (*)(void))tempest_seed_verify_zeroization },
    { OSSL_FUNC_RAND_GET_PARAMS, (void (*)(void))tempest_seed_get_params },
    { OSSL_FUNC_RAND_GET_CTX_PARAMS, (void (*)(void))tempest_seed_get_ctx_params },
    { OSSL_FUNC_RAND_GETTABLE_CTX_PARAMS, (void (*)(void))tempest_seed_gettable_ctx_params },
    { OSSL_FUNC_RAND_SETTABLE_CTX_PARAMS, (void (*)(void))tempest_seed_settable_ctx_params },
    { OSSL_FUNC_RAND_ENABLE_LOCKING, (void (*)(void))tempest_seed_enable_locking },
    { OSSL_FUNC_RAND_LOCK, (void (*)(void))tempest_seed_lock },
    { OSSL_FUNC_RAND_UNLOCK, (void (*)(void))tempest_seed_unlock },
    { 0, NULL }
};

static const OSSL_ALGORITHM tempest_seed_algorithms[] = {
    { "tempest", NULL, tempest_seed_rand_functions,
      "Tempest v3 SEED-SOURCE (KAT-verified, 2^128)" },
    { NULL, NULL, NULL, NULL }
};

static const OSSL_PARAM tempest_seed_param_types[] = {
    OSSL_PARAM_DEFN(OSSL_PROV_PARAM_NAME, OSSL_PARAM_UTF8_PTR, NULL, 0),
    OSSL_PARAM_DEFN(OSSL_PROV_PARAM_VERSION, OSSL_PARAM_UTF8_PTR, NULL, 0),
    OSSL_PARAM_END
};

static const OSSL_PARAM *tempest_seed_gettable_params(void *provctx) {
    return tempest_seed_param_types;
}

static int tempest_seed_prov_get_params(void *provctx, OSSL_PARAM params[]) {
    OSSL_PARAM *p = OSSL_PARAM_locate(params, OSSL_PROV_PARAM_NAME);
    if (p != NULL && !OSSL_PARAM_set_utf8_ptr(p, "tempest_ossl_seed")) return 0;
    p = OSSL_PARAM_locate(params, OSSL_PROV_PARAM_VERSION);
    if (p != NULL && !OSSL_PARAM_set_utf8_ptr(p, "1.0")) return 0;
    return 1;
}

static void *tempest_seed_prov_ctx_new(void) {
    return OPENSSL_zalloc(1);  /* no provider state needed */
}

static void tempest_seed_prov_ctx_free(void *provctx) {
    OPENSSL_free(provctx);
}

static const OSSL_ALGORITHM *tempest_seed_query_operation(void *provctx,
                                                          int operation_id,
                                                          int *no_cache) {
    *no_cache = 0;
    if (operation_id == OSSL_OP_RAND)
        return tempest_seed_algorithms;
    return NULL;
}

static const OSSL_DISPATCH tempest_seed_provider_functions[] = {
    { OSSL_FUNC_PROVIDER_GETTABLE_PARAMS, (void (*)(void))tempest_seed_gettable_params },
    { OSSL_FUNC_PROVIDER_GET_PARAMS, (void (*)(void))tempest_seed_prov_get_params },
    { OSSL_FUNC_PROVIDER_QUERY_OPERATION, (void (*)(void))tempest_seed_query_operation },
    { OSSL_FUNC_PROVIDER_TEARDOWN, (void (*)(void))tempest_seed_prov_ctx_free },
    { 0, NULL }
};

int OSSL_provider_init(const OSSL_CORE_HANDLE *handle,
                       const OSSL_DISPATCH *in,
                       const OSSL_DISPATCH **out,
                       void **provctx) {
    *provctx = tempest_seed_prov_ctx_new();
    *out = tempest_seed_provider_functions;
    return 1;
}

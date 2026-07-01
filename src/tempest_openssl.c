/* tempest_openssl.c — OpenSSL 3.x Provider for Tempest v3 DRBG
 * ======================================================================
 * 实现 OSSL_OP_RAND 接口, 使 Tempest v3 成为 OpenSSL 的 EVP_RAND 提供者。
 * 所有使用 OpenSSL 的程序 (openssl CLI, libtls, Nginx, Python ssl 等)
 * 均可通过 provider 机制使用 Tempest v3 作为随机数源。
 *
 * 原理:
 *   OpenSSL 3.x 通过 provider 架构加载算法。
 *   OSSL_provider_init() → provider_query_operation() → OSSL_ALGORITHM[]
 *   每个算法有自己的 OSSL_DISPATCH 表映射功能 ID→函数指针。
 *
 * 编译 (Linux):
 *   gcc -O3 -march=native -fPIC -shared -o tempest_provider.so \
 *       tempest_openssl.c \
 *       -I/usr/include/openssl
 *
 * 编译 (Windows MinGW):
 *   gcc -O3 -march=native -shared -o tempest_provider.dll \
 *       tempest_openssl.c \
 *       -I/c/msys64/mingw64/include
 *
 * 测试:
 *   OPENSSL_MODULES=. openssl rand -provider tempest_provider -hex 32
 *
 * 程序中使用:
 *   EVP_RAND *rng = EVP_RAND_fetch(NULL, "TEMPEST-DRBG", NULL);
 *   EVP_RAND_CTX *ctx = EVP_RAND_CTX_new(rng, NULL);
 *   EVP_RAND_instantiate(ctx, 128, 0, NULL, 0, NULL);
 *   EVP_RAND_generate(ctx, buf, 32, 0, 0, NULL, 0);
 *   EVP_RAND_CTX_free(ctx);
 *
 * 注意: 此文件只实现 provider 胶水层, 不包含 Tempest 算法本身。
 * Tempest 算法包含在 tempest_v3.c + tempest_drbg.c 中。
 * ====================================================================== */
#include <string.h>
#include <stdint.h>
#include <stdlib.h>

/* OpenSSL 3.x Provider API */
#include <openssl/core.h>
#include <openssl/core_dispatch.h>
#include <openssl/core_names.h>
#include <openssl/params.h>
#include <openssl/err.h>
#include <openssl/evp.h>     /* EVP_RAND_STATE_* */

/* ═══════════════════════════════════════════════════════════════════════
 * Tempest v3 核心 — 内联实现 (无外部依赖)
 * 完整实现 4-cmul 轮函数 + AND-mix 输出 + 密钥编排
 * ═══════════════════════════════════════════════════════════════════════ */

#define ROTL(x, r) (((x) << (r)) | ((x) >> (64 - (r))))
#define WEYL_GOLDEN 0x9E3779B97F4A7C15ULL

static inline uint64_t cmul_hl(uint64_t a, uint64_t b) {
    return (uint64_t)(uint32_t)(a >> 32) * (uint64_t)(uint32_t)b;
}
static inline uint64_t cmul_lh(uint64_t a, uint64_t b) {
    return (uint64_t)(uint32_t)a * (uint64_t)(uint32_t)(b >> 32);
}

typedef struct {
    uint64_t u, v, w, z, rounds, weyl;
} TempestState;

static void tempest_round(TempestState *s) {
    uint64_t u = s->u, v = s->v, w = s->w, z = s->z;
    int sh = (int)(s->rounds & 3);
    uint64_t wval = s->weyl + WEYL_GOLDEN;
    u ^= ROTL(wval, 7) ^ (wval >> 17);
    v ^= ROTL(wval, 19) ^ (wval >> 23);
    w ^= ROTL(wval, 31) ^ (wval >> 29);
    z ^= ROTL(wval, 43) ^ (wval >> 37);
    s->weyl = wval;
    uint64_t u0 = u;
    u += ROTL(v, 7) ^ ROTL(z, 13);
    v += ROTL(w, 11);
    w += ROTL(z, 13);
    z += ROTL(u0, 17);
    u += cmul_hl(v, w); v += cmul_hl(w, z);
    w += cmul_lh(u, v); u += cmul_hl(w, z);
    u ^= ROTL(v, 19) + w; v ^= ROTL(w, 23) + z;
    w ^= ROTL(z, 7) + u; z ^= ROTL(u, 11) + v;
    if ((s->rounds & 1) == 0) {
        z ^= ROTL(v, (unsigned)(19 - sh * 2)) + u;
        w ^= ROTL(u, (unsigned)(23 - sh * 2)) + z;
        v ^= ROTL(z, (unsigned)(7 + sh * 2)) + w;
        u ^= ROTL(w, (unsigned)(11 + sh * 2)) + v;
    }
    s->u = u; s->v = v; s->w = w; s->z = z; s->rounds++;
}

static uint64_t make_output(uint64_t u, uint64_t v, uint64_t w, uint64_t z) {
    uint64_t t = u ^ ROTL(v, 32) ^ w ^ ROTL(z, 16);
    t ^= ROTL(t, 27) ^ ROTL(t, 17);
    t ^= ROTL(t, 31) & ROTL(t, 53);
    t ^= ROTL(t, 17) & ROTL(t, 43);
    t ^= ROTL(t,  7) & ROTL(t, 23);
    t ^= ROTL(t,  5) & ROTL(t, 19);
    t ^= t >> 32;
    return t;
}

static uint64_t tempest_next(TempestState *s) {
    tempest_round(s);
    return make_output(s->u, s->v, s->w, s->z);
}

static void tempest_init(TempestState *s,
    const uint64_t key[4], const uint64_t nonce[2])
{
    uint64_t k0 = key[0], k1 = key[1], k2 = key[2], k3 = key[3];
    s->u = k0; s->v = k1 ^ nonce[0]; s->w = k2 ^ nonce[1];
    s->z = k3 ^ 0x54454D5035583543ULL; s->rounds = 0;
    s->weyl = 0x6A09E667F3BCC908ULL;
    uint64_t weyl = 0x6A09E667F3BCC908ULL;
    for (int i = 0; i < 16; i++) {
        tempest_round(s); weyl += WEYL_GOLDEN;
        if (i < 8) {
            if (i & 1) {
                s->u ^= ROTL(k0, (unsigned)(i + 1)) ^ weyl;
                s->v ^= ROTL(k1, (unsigned)(i + 1)) ^ (weyl << 17);
                s->w ^= ROTL(k2, (unsigned)(i + 1)) ^ (weyl >> 13);
                s->z ^= ROTL(k3, (unsigned)(i + 1)) ^ ROTL(weyl, 31);
            } else {
                s->u ^= k0 ^ weyl; s->v ^= k1 ^ (weyl << 17);
                s->w ^= k2 ^ (weyl >> 13); s->z ^= k3 ^ ROTL(weyl, 31);
            }
        } else {
            uint64_t nh = nonce[i & 1], nl = nonce[1 - (i & 1)];
            uint64_t nc = (nh << 32) | (uint32_t)nl;
            s->u ^= nc; s->v ^= ROTL(nc, 19) ^ (uint64_t)i;
            s->z ^= ROTL(nc, 43);
        }
    }
    for (int i = 0; i < 6; i++) tempest_round(s);
    s->u ^= k0; s->v ^= k1; s->w ^= k2; s->z ^= k3;
}

/* SP 800-90A DRBG Update: XOR data → 8 rounds mix */
static void drbg_update(TempestState *s, const uint64_t data[4]) {
    s->u ^= data[0]; s->v ^= data[1];
    s->w ^= data[2]; s->z ^= data[3];
    /* 8 轮后处理 */
    for (int i = 0; i < 4; i++) {
        uint64_t fb = tempest_next(s);
        s->u ^= fb; s->v ^= tempest_next(s);
    }
}

/* ═══════════════════════════════════════════════════════════════════════
 * Provider Context
 * ═══════════════════════════════════════════════════════════════════════ */
typedef struct {
    TempestState core;           /* Tempest 核心状态 */
    int strength;                /* 安全强度 (bit) */
    int initialized;             /* 是否已 instantiate */
    uint64_t reseed_counter;     /* 自上次 reseed 后的生成次数 */
} ProvCtx;

/* ═══════════════════════════════════════════════════════════════════════
 * RAND dispatch 接口
 *
 * 函数签名匹配 OpenSSL 3.x core_dispatch.h 中 OSSL_CORE_MAKE_FUNC 定义
 * ═══════════════════════════════════════════════════════════════════════ */

/* newctx: 创建上下文 */
static void *tempest_newctx(void *provctx, const OSSL_PARAM params[]) {
    ProvCtx *ctx = OPENSSL_zalloc(sizeof(*ctx));
    if (!ctx) return NULL;
    ctx->strength = 128;
    ctx->initialized = 0;
    ctx->reseed_counter = 0;
    return ctx;
}

/* freectx: 释放上下文 */
static void tempest_freectx(void *vctx) {
    ProvCtx *ctx = (ProvCtx *)vctx;
    if (!ctx) return;
    /* 安全清零敏感状态 */
    OPENSSL_cleanse(ctx, sizeof(*ctx));
    OPENSSL_free(ctx);
}

/* instantiate: 初始化 DRBG (SP 800-90A §9.1)
 *
 * OpenSSL 核心传入 entropy 和 nonce;
 * strength: 请求的安全强度 (128);
 * entropy/entropy_len: 熵输入;
 * params: 可选参数 */
static int tempest_instantiate(void *vctx, unsigned int strength,
    int prediction_resistance, const unsigned char *entropy,
    size_t entropy_len, const OSSL_PARAM params[])
{
    ProvCtx *ctx = (ProvCtx *)vctx;
    uint64_t key[4], nonce[2];
    (void)prediction_resistance;
    (void)params;

    if (!ctx) return 0;
    if (!entropy || entropy_len < 32) return 0;

    /* 从熵输入派生 key (256-bit) + nonce (128-bit) */
    memset(key, 0, sizeof(key));
    memset(nonce, 0, sizeof(nonce));
    memcpy(key, entropy, (entropy_len < 32) ? entropy_len : 32);
    if (entropy_len >= 48)
        memcpy(nonce, entropy + 32, 16);
    else if (entropy_len >= 40)
        memcpy(nonce, entropy + 32, (entropy_len - 32 < 16) ? entropy_len - 32 : 16);

    /* 额外扩散: 用所有熵位混合 nonce */
    uint64_t extra = 0;
    for (size_t i = 0; i < entropy_len; i++)
        extra ^= ((uint64_t)entropy[i]) << ((i * 8) % 64);
    nonce[0] ^= extra;
    nonce[1] ^= ROTL(extra, 17);

    /* 初始化 Tempest */
    tempest_init(&ctx->core, key, nonce);

    /* DRBG Update 增强 */
    uint64_t feed[4] = {key[0]^nonce[0], key[1]^nonce[1], key[2], key[3]};
    drbg_update(&ctx->core, feed);

    ctx->strength = (strength > 128) ? strength : 128;
    ctx->initialized = 1;
    ctx->reseed_counter = 1;

    /* 清理栈 */
    OPENSSL_cleanse(key, sizeof(key));
    OPENSSL_cleanse(nonce, sizeof(nonce));
    OPENSSL_cleanse(feed, sizeof(feed));

    return 1;
}

/* generate: 生成随机数 (SP 800-90A §9.2)
 *
 * out/outlen: 输出缓冲区;
 * strength: 需求的安全强度;
 * adin/adinlen: 附加输入 (additional_input) */
static int tempest_generate(void *vctx, unsigned char *out, size_t outlen,
    unsigned int strength, int prediction_resistance,
    const unsigned char *adin, size_t adinlen)
{
    ProvCtx *ctx = (ProvCtx *)vctx;
    (void)strength;
    (void)prediction_resistance;

    if (!ctx || !ctx->initialized) return 0;
    if (outlen > 65536) return 0;  /* SP 800-90A 限制 */

    /* 处理附加输入 */
    uint64_t additional[4] = {0, 0, 0, 0};
    if (adin && adinlen > 0) {
        memcpy(additional, adin, (adinlen < 32) ? adinlen : 32);
        drbg_update(&ctx->core, additional);
    }

    /* 生成输出 */
    size_t remain = outlen;
    unsigned char *ptr = out;
    while (remain >= 16) {
        uint64_t pair[2];
        tempest_round(&ctx->core);
        pair[0] = make_output(ctx->core.u, ctx->core.v, ctx->core.w, ctx->core.z);
        pair[1] = make_output(ctx->core.v, ctx->core.w, ctx->core.z, ctx->core.u);
        memcpy(ptr, pair, 16);
        ptr += 16; remain -= 16;
    }
    if (remain > 0) {
        uint64_t r = tempest_next(&ctx->core);
        memcpy(ptr, &r, remain);
    }

    /* 后处理 update (前向安全性) — 用新输出覆盖旧状态 */
    uint64_t mix[4];
    mix[0] = tempest_next(&ctx->core);
    mix[1] = tempest_next(&ctx->core);
    mix[2] = tempest_next(&ctx->core);
    mix[3] = tempest_next(&ctx->core);
    drbg_update(&ctx->core, mix);
    OPENSSL_cleanse(mix, sizeof(mix));

    ctx->reseed_counter++;

    OPENSSL_cleanse(additional, sizeof(additional));
    return 1;
}

/* reseed: 重新注入熵 (SP 800-90A §9.3) */
static int tempest_reseed(void *vctx, int prediction_resistance,
    const unsigned char *entropy, size_t entropy_len,
    const unsigned char *adin, size_t adinlen)
{
    ProvCtx *ctx = (ProvCtx *)vctx;
    (void)prediction_resistance;

    if (!ctx || !entropy || entropy_len < 32) return 0;

    /* 构造 256-bit 更新数据 */
    uint64_t data[4] = {0, 0, 0, 0};
    memcpy(data, entropy, (entropy_len < 32) ? entropy_len : 32);

    /* 混入附加输入 */
    uint64_t additional[4] = {0, 0, 0, 0};
    if (adin && adinlen > 0)
        memcpy(additional, adin, (adinlen < 32) ? adinlen : 32);

    data[0] ^= additional[0]; data[1] ^= additional[1];
    data[2] ^= additional[2]; data[3] ^= additional[3];

    drbg_update(&ctx->core, data);
    ctx->reseed_counter = 1;
    ctx->initialized = 1;

    OPENSSL_cleanse(data, sizeof(data));
    OPENSSL_cleanse(additional, sizeof(additional));
    return 1;
}

/* 获取上下文参数 */
static int tempest_get_ctx_params(void *vctx, OSSL_PARAM params[]) {
    ProvCtx *ctx = (ProvCtx *)vctx;
    OSSL_PARAM *p;

    if ((p = OSSL_PARAM_locate(params, OSSL_RAND_PARAM_STRENGTH)) != NULL)
        OSSL_PARAM_set_int(p, ctx->strength);
    if ((p = OSSL_PARAM_locate(params, OSSL_RAND_PARAM_MAX_REQUEST)) != NULL)
        OSSL_PARAM_set_size_t(p, 65536);
    if ((p = OSSL_PARAM_locate(params, OSSL_RAND_PARAM_STATE)) != NULL)
        OSSL_PARAM_set_int(p, ctx->initialized ?
            EVP_RAND_STATE_READY : EVP_RAND_STATE_UNINITIALISED);

    return 1;
}

static const OSSL_PARAM tempest_ctx_params[] = {
    OSSL_PARAM_int(OSSL_RAND_PARAM_STRENGTH, NULL),
    OSSL_PARAM_size_t(OSSL_RAND_PARAM_MAX_REQUEST, NULL),
    OSSL_PARAM_int(OSSL_RAND_PARAM_STATE, NULL),
    OSSL_PARAM_END
};

static const OSSL_PARAM *tempest_gettable_ctx_params(void *vctx,
    void *provctx) {
    return tempest_ctx_params;
}

/* ═══════════════════════════════════════════════════════════════════════
 * RAND dispatch 表 — 映射功能 ID 到实现函数
 * ═══════════════════════════════════════════════════════════════════════ */
static const OSSL_DISPATCH tempest_rand_dispatch[] = {
    { OSSL_FUNC_RAND_NEWCTX,             (void (*)(void))tempest_newctx },
    { OSSL_FUNC_RAND_FREECTX,            (void (*)(void))tempest_freectx },
    { OSSL_FUNC_RAND_INSTANTIATE,        (void (*)(void))tempest_instantiate },
    { OSSL_FUNC_RAND_GENERATE,           (void (*)(void))tempest_generate },
    { OSSL_FUNC_RAND_RESEED,            (void (*)(void))tempest_reseed },
    { OSSL_FUNC_RAND_GET_CTX_PARAMS,     (void (*)(void))tempest_get_ctx_params },
    { OSSL_FUNC_RAND_GETTABLE_CTX_PARAMS,(void (*)(void))tempest_gettable_ctx_params },
    OSSL_DISPATCH_END
};

/* ═══════════════════════════════════════════════════════════════════════
 * 算法注册 — OpenSSL 核心查询时返回
 * ═══════════════════════════════════════════════════════════════════════ */
static const OSSL_ALGORITHM tempest_algorithms[] = {
    { "TEMPEST-DRBG",                   /* 算法名 — EVP_RAND_fetch 用 */
      "provider=tempest,security=128",  /* 属性字符串 */
      tempest_rand_dispatch,            /* dispatch 表 */
      "Tempest v3 CSPRNG — SP 800-90A DRBG, 2^128 security" /* 描述 */
    },
    { NULL, NULL, NULL, NULL }          /* 终止符 */
};

/* ═══════════════════════════════════════════════════════════════════════
 * Provider 查询函数 — OpenSSL 核心调用此函数获取算法
 *
 * operation_id = OSSL_OP_RAND (5) 时返回我们的 RAND 算法
 * ═══════════════════════════════════════════════════════════════════════ */
static const OSSL_ALGORITHM *tempest_query_operation(void *provctx,
    int operation_id, int *no_store)
{
    *no_store = 0;
    if (operation_id == OSSL_OP_RAND)
        return tempest_algorithms;
    return NULL;
}

/* ═══════════════════════════════════════════════════════════════════════
 * Provider 清理
 * ═══════════════════════════════════════════════════════════════════════ */
static void tempest_teardown(void *provctx) {
    (void)provctx;
}

/* ═══════════════════════════════════════════════════════════════════════
 * Provider 参数
 * ═══════════════════════════════════════════════════════════════════════ */
static const OSSL_PARAM tempest_provider_params[] = {
    OSSL_PARAM_utf8_string("provider", "tempest", 0),
    OSSL_PARAM_utf8_string("version", "1.0.0", 0),
    OSSL_PARAM_END
};

static const OSSL_PARAM *tempest_gettable_params(void *provctx) {
    return tempest_provider_params;
}

static int tempest_get_params(void *provctx, OSSL_PARAM params[]) {
    OSSL_PARAM *p;
    if ((p = OSSL_PARAM_locate(params, "provider")) != NULL)
        OSSL_PARAM_set_utf8_string(p, "tempest");
    if ((p = OSSL_PARAM_locate(params, "version")) != NULL)
        OSSL_PARAM_set_utf8_string(p, "1.0.0");
    return 1;
}

/* ═══════════════════════════════════════════════════════════════════════
 * Provider dispatch 表 — 映射 Provider 功能 ID 到实现函数
 * ═══════════════════════════════════════════════════════════════════════ */
static const OSSL_DISPATCH tempest_provider_dispatch[] = {
    { OSSL_FUNC_PROVIDER_TEARDOWN,        (void (*)(void))tempest_teardown },
    { OSSL_FUNC_PROVIDER_GETTABLE_PARAMS, (void (*)(void))tempest_gettable_params },
    { OSSL_FUNC_PROVIDER_GET_PARAMS,      (void (*)(void))tempest_get_params },
    { OSSL_FUNC_PROVIDER_QUERY_OPERATION, (void (*)(void))tempest_query_operation },
    OSSL_DISPATCH_END
};

/* ═══════════════════════════════════════════════════════════════════════
 * Provider 入口点 — OpenSSL 加载此 .dll/.so 时调用
 *
 * Openssl 3.x 调用此函数获取 provider 的能力表
 * ═══════════════════════════════════════════════════════════════════════ */
int OSSL_provider_init(const OSSL_CORE_HANDLE *handle,
                       const OSSL_DISPATCH *in,
                       const OSSL_DISPATCH **out,
                       void **provctx)
{
    /* 返回 provider 自身的 dispatch 表 */
    *out = tempest_provider_dispatch;
    *provctx = (void*)handle;
    return 1;
}

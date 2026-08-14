/* tempest_wolfssl_patch.c — Reference integration of Tempest v3 as
 * the RNG for wolfSSL via the official crypto-callback mechanism.
 *
 * This is the path recommended by the wolfSSL maintainer in
 * wolfSSL/wolfssl#10802 ("use the crypto callbacks to intercept the
 * RNG calls and service with their preferred option"). It does NOT
 * modify wolfSSL: the library's own crypto-callback dispatch
 * (wc_CryptoCb_RandomBlock, triggered by rng->devId in
 * wc_RNG_GenerateBlock) routes every RNG request to our callback,
 * which services it with the KAT-verified Tempest v3 stream.
 *
 * Security note: the callback replaces wolfSSL's entropy-based RNG,
 * so the caller is responsible for seeding Tempest with true
 * randomness (a real key/nonce, e.g. from wolfSSL's own RNG, once at
 * startup) and for the security of the resulting construction. This
 * is exactly the trust model wolfSSL's crypto callbacks are designed
 * for: the application opts in and owns the consequence.
 *
 * Build & test (WSL, wolfSSL 5.9.1 built with --enable-cryptocb):
 *   cd wolfssl_tempest
 *   gcc -I$HOME/wolfssl-5.9.1 -I.. -O2 -o test_wolfssl_cb \
 *       test_wolfssl_cb.c tempest_wolfssl_patch.c ../code/tempest_v3.c \
 *       $HOME/wolfssl-5.9.1/src/.libs/libwolfssl.a -lpthread -lm
 *   ./test_wolfssl_cb
 */
#include <wolfssl/options.h>
#include <wolfssl/wolfcrypt/cryptocb.h>
#include <wolfssl/wolfcrypt/random.h>
#include <wolfssl/wolfcrypt/error-crypt.h>
#include <string.h>
#include <stdint.h>
#include "../code/tempest_v3.h"

/* One Tempest state per process; seed it once with real entropy. */
static tempest_state g_tempest_state;

/* Seed Tempest from wolfSSL's own (entropy-based) RNG: the cleanest
 * way to obtain key material without introducing a second entropy
 * source. 32 bytes key + 16 bytes nonce. */
int tempest_wolfssl_seed_from_wolfssl(void)
{
    WC_RNG sys;
    byte seed[48];
    int ret;

    ret = wc_InitRng(&sys);
    if (ret != 0)
        return ret;
    ret = wc_RNG_GenerateBlock(&sys, seed, sizeof(seed));
    wc_FreeRng(&sys);
    if (ret != 0)
        return ret;

    {
        uint64_t key[4], nonce[2];
        memcpy(key, seed, 32);
        memcpy(nonce, seed + 32, 16);
        tempest_init(&g_tempest_state, key, nonce);
    }
    return 0;
}

/* Seed Tempest deterministically (tests / reproducible simulations).
 * NOT for production use. */
void tempest_wolfssl_seed_deterministic(uint64_t seed)
{
    tx5cmul_seed(&g_tempest_state, seed);
}

/* The crypto callback: every wolfSSL RNG request is serviced by
 * Tempest. Non-RNG requests fall through to wolfSSL (return
 * CRYPTOCB_UNAVAILABLE). Return 0 on success. */
int tempest_wolfssl_crypto_cb(int devId, wc_CryptoInfo* info, void* ctx)
{
    (void)devId;
    (void)ctx;

    if (info->algo_type == WC_ALGO_TYPE_RNG) {
        if (info->rng.out == NULL || info->rng.sz == 0)
            return BAD_FUNC_ARG;
        tempest_bytes(&g_tempest_state, info->rng.out, info->rng.sz);
        return 0;                    /* serviced: wolfSSL uses our output */
    }
    return CRYPTOCB_UNAVAILABLE;     /* other algorithms: wolfSSL internal */
}

/* Register the callback on a device id; returns the devId to pass to
 * wc_InitRng_ex (or wolfSSL_CTX_SetDevId for TLS contexts). */
int tempest_wolfssl_register(int devId)
{
    return wc_CryptoCb_RegisterDevice(devId, tempest_wolfssl_crypto_cb, NULL);
}

void tempest_wolfssl_unregister(int devId)
{
    wc_CryptoCb_UnRegisterDevice(devId);
}

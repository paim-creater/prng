/* tempest_wolfssl_patch.c — Tempest v3 as WolfSSL custom RNG backend
 *
 * Complete drop-in replacement for WolfSSL's built-in DRBG.
 * Replace wolfssl/wolfcrypt/src/random.c with this file, or
 * use CUSTOM_RAND_GENERATE_BLOCK to hook Tempest without modifying core files.
 *
 * Compile with: -DWC_NO_HASHDRBG -DCUSTOM_RAND_GENERATE_BLOCK=tempest_generate_block
 *
 * This file implements the complete WolfSSL RNG interface using Tempest v3.
 * Reference implementation: https://github.com/paim-creater/prng
 */
#include <wolfssl/wolfcrypt/random.h>
#include <stdint.h>
#include <string.h>

/* ─── Tempest v3 core (inlined, ~200 lines, no external deps) ─── */

#define ROTL64(x, r) (((x) << (r)) | ((x) >> (64 - (r))))
#define WEYL_GOLDEN 0x9E3779B97F4A7C15ULL

typedef struct {
    uint64_t u, v, w, z, rounds, weyl;
} TempestState;

static inline uint64_t cmul_hl(uint64_t a, uint64_t b) {
    return (uint64_t)(uint32_t)(a >> 32) * (uint64_t)(uint32_t)b;
}
static inline uint64_t cmul_lh(uint64_t a, uint64_t b) {
    return (uint64_t)(uint32_t)a * (uint64_t)(uint32_t)(b >> 32);
}

static void tempest_round(TempestState *s) {
    uint64_t u=s->u,v=s->v,w=s->w,z=s->z;int sh=(int)(s->rounds&3);
    uint64_t wv=s->weyl;wv+=WEYL_GOLDEN;
    u^=ROTL64(wv,7)^(wv>>17);v^=ROTL64(wv,19)^(wv>>23);
    w^=ROTL64(wv,31)^(wv>>29);z^=ROTL64(wv,43)^(wv>>37);
    s->weyl=wv;uint64_t u0=u;
    u+=ROTL64(v,7)^ROTL64(z,13);v+=ROTL64(w,11);
    w+=ROTL64(z,13);z+=ROTL64(u0,17);
    u+=cmul_hl(v,w);v+=cmul_hl(w,z);w+=cmul_lh(u,v);u+=cmul_hl(w,z);
    u^=ROTL64(v,19)+w;v^=ROTL64(w,23)+z;w^=ROTL64(z,7)+u;z^=ROTL64(u,11)+v;
    if((s->rounds&1)==0){int sh2=19-sh*2;
        z^=ROTL64(v,(unsigned)sh2)+u;w^=ROTL64(u,(unsigned)(23-sh*2))+z;
        v^=ROTL64(z,(unsigned)(7+sh*2))+w;u^=ROTL64(w,(unsigned)(11+sh*2))+v;}
    s->u=u;s->v=v;s->w=w;s->z=z;s->rounds++;
}

static uint64_t make_output(uint64_t u,uint64_t v,uint64_t w,uint64_t z){
    uint64_t t=u^ROTL64(v,32)^w^ROTL64(z,16);t^=ROTL64(t,27);
    t^=ROTL64(t,31)&ROTL64(t,53);t^=ROTL64(t,17)&ROTL64(t,43);
    t^=ROTL64(t,7)&ROTL64(t,23);t^=ROTL64(t,5)&ROTL64(t,19);
    t^=t>>32;return t;
}

static void tempest_init(TempestState*s,const uint64_t key[4],const uint64_t nonce[2]){
    uint64_t k0=key[0],k1=key[1],k2=key[2],k3=key[3];
    s->u=k0;s->v=k1^nonce[0];s->w=k2^nonce[1];
    s->z=k3^0x54454D5035583543ULL;s->rounds=0;s->weyl=0x6A09E667F3BCC908ULL;
    uint64_t weyl=0x6A09E667F3BCC908ULL;
    for(int i=0;i<16;i++){tempest_round(s);weyl+=WEYL_GOLDEN;
        if(i<8){if(i&1){s->u^=ROTL64(k0,(unsigned)(i+1))^weyl;
            s->v^=ROTL64(k1,(unsigned)(i+1))^(weyl<<17);
            s->w^=ROTL64(k2,(unsigned)(i+1))^(weyl>>13);
            s->z^=ROTL64(k3,(unsigned)(i+1))^ROTL64(weyl,31);}
        else{s->u^=k0^weyl;s->v^=k1^(weyl<<17);
            s->w^=k2^(weyl>>13);s->z^=k3^ROTL64(weyl,31);}}
        else{uint64_t nh=nonce[i&1],nl=nonce[1-(i&1)],nc=(nh<<32)|(uint32_t)nl;
            s->u^=nc;s->v^=ROTL64(nc,19)^(uint64_t)i;s->z^=ROTL64(nc,43);}}
    for(int i=0;i<6;i++)tempest_round(s);
    s->u^=k0;s->v^=k1;s->w^=k2;s->z^=k3;
}

static void tempest_bytes(TempestState*s,uint8_t*buf,size_t n){
    while(n>=16){uint64_t o[2];tempest_round(s);
        o[0]=make_output(s->u,s->v,s->w,s->z);
        o[1]=make_output(s->v,s->w,s->z,s->u);
        memcpy(buf,o,16);buf+=16;n-=16;}
    if(n>0){uint64_t r;tempest_round(s);
        r=make_output(s->u,s->v,s->w,s->z);
        memcpy(buf,&r,n);}
}

/* ─── WolfSSL RNG Interface ─── */

#include <wolfssl/wolfcrypt/random.h>
#include <wolfssl/wolfcrypt/error-crypt.h>
#include <stdlib.h>

#ifdef _WIN32
#include <windows.h>
#include <bcrypt.h>
#pragma comment(lib, "bcrypt.lib")
#else
#include <fcntl.h>
#include <unistd.h>
#endif

/* Thread-local state: each thread gets its own Tempest instance.
   No mutex needed, no cross-thread state corruption. */
static __thread TempestState wc_state;
static __thread int wc_initialized = 0;

/* Seed from OS entropy source */
static int seed_from_os(uint64_t key[4], uint64_t nonce[2]) {
#ifdef _WIN32
    if (BCryptGenRandom(NULL, (PUCHAR)key, sizeof(key),
        BCRYPT_USE_SYSTEM_PREFERRED_RNG) < 0) return -1;
    if (BCryptGenRandom(NULL, (PUCHAR)nonce, sizeof(nonce),
        BCRYPT_USE_SYSTEM_PREFERRED_RNG) < 0) return -1;
#else
    int fd = open("/dev/urandom", O_RDONLY);
    if (fd < 0) return -1;
    size_t n = 0; unsigned char *p = (unsigned char *)key;
    while (n < sizeof(key)) { ssize_t r = read(fd, p + n, sizeof(key) - n); if (r <= 0) break; n += r; }
    n = 0; p = (unsigned char *)nonce;
    while (n < sizeof(nonce)) { ssize_t r = read(fd, p + n, sizeof(nonce) - n); if (r <= 0) break; n += r; }
    close(fd);
#endif
    return 0;
}

/* CUSTOM_RAND_GENERATE_BLOCK: called by WolfSSL when it needs random bytes.
   Fills 'sz' bytes at 'output'. Returns 0 on success. */
int tempest_generate_block(unsigned char* output, unsigned int sz) {
    if (!wc_initialized) {
        uint64_t key[4], nonce[2];
        if (seed_from_os(key, nonce) < 0) return -1;
        tempest_init(&wc_state, key, nonce);
        wc_initialized = 1;
    }
    tempest_bytes(&wc_state, output, sz);
    return 0;
}

/* Optional: WC_RNG_SEED_CB — Seed the DRBG from Tempest v3.
   Register with wc_SetSeed_Cb(my_seed_cb) after wolfSSL_Init(). */
int tempest_seed_cb(OS_Seed* os, byte* seed, word32 sz) {
    (void)os;
    if (!wc_initialized) {
        uint64_t key[4], nonce[2];
        if (seed_from_os(key, nonce) < 0) return -1;
        tempest_init(&wc_state, key, nonce);
        wc_initialized = 1;
    }
    tempest_bytes(&wc_state, seed, sz);
    return 0;
}

/* ─── wc_InitRng / wc_RNG_GenerateBlock wrappers ───
   These replace the built-in WolfSSL RNG functions when
   CUSTOM_RAND_GENERATE_BLOCK is defined. The standard WolfSSL
   build system with --enable-customrand handles the wiring. */

int wc_InitRng_ex(WC_RNG* rng, void* heap, int devId) {
    (void)rng; (void)heap; (void)devId;
    return 0;  /* Global state initialized on first generate */
}

int wc_InitRng(WC_RNG* rng) {
    return wc_InitRng_ex(rng, NULL, INVALID_DEVID);
}

WC_RNG* wc_rng_new(byte* seed, word32 sz, void* heap) {
    (void)seed; (void)sz; (void)heap;
    return (WC_RNG*)1;  /* Dummy handle */
}

void wc_rng_free(WC_RNG* rng) {
    (void)rng;
}

int wc_RNG_GenerateBlock(WC_RNG* rng, byte* output, word32 sz) {
    (void)rng;
    return tempest_generate_block(output, (unsigned int)sz);
}

int wc_RNG_GenerateByte(WC_RNG* rng, byte* output) {
    return wc_RNG_GenerateBlock(rng, output, 1);
}

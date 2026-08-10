/* tempest_v3.c — Tian Yuezhou's design */
#include "tempest_v3.h"
#include <string.h>

#if defined(__GNUC__) || defined(__clang__)
#define ALWAYS_INLINE __attribute__((always_inline)) static inline
#else
#define ALWAYS_INLINE static inline
#endif

#define WEYL_GOLDEN 0x9E3779B97F4A7C15ULL
#define K_U 0x9E3779B97F4A7C15ULL
#define K_V 0x3C6EF372FE94F82AULL
#define K_W 0x5A8279998F1BBD27ULL
#define K_Z 0x6ED9EBA1F97F3B4CULL

ALWAYS_INLINE uint64_t rotl(uint64_t x, int r) {
    return (x << r) | (x >> (64 - r));
}

ALWAYS_INLINE uint64_t andmix4(uint64_t t) {
    uint64_t a, b;
    a = rotl(t, 31); b = rotl(t, 53); t ^= a & b;
    a = rotl(t, 17); b = rotl(t, 43); t ^= a & b;
    a = rotl(t,  7); b = rotl(t, 23); t ^= a & b;
    a = rotl(t,  5); b = rotl(t, 19); t ^= a & b;
    return t;
}

static void enhanced_round(tx4_state *s) {
    uint64_t u = s->u, v = s->v, w = s->w, z = s->z;
    uint64_t u0 = u, v0 = v, w0 = w, z0 = z;

    /* Phase A: GF(2) nonlinear diffusion (reads from snapshot) */
    u = u0 ^ rotl(v0,5) ^ rotl(w0,17) ^ (rotl(v0,5) & rotl(z0,25)) ^ K_U;
    v = v0 ^ rotl(w0,11) ^ rotl(z0,23) ^ (rotl(w0,11) & rotl(u0,29)) ^ K_V;
    w = w0 ^ rotl(z0,13) ^ rotl(u0,31) ^ (rotl(u0,9) & rotl(v0,15)) ^ K_W;
    z = z0 ^ rotl(u0,17) ^ rotl(v0,7) ^ (rotl(v0,27) & rotl(w0,21)) ^ K_Z;

    /* Phase A(lin): snapshot ANDs covering (u,z) and (w,z) for linear resistance */
    u ^= (rotl(z0, 23) & rotl(w0, 53));
    z ^= (rotl(u0, 5) & rotl(z0, 25));

    /* Phase B: GF(2) round key — pure {AND,XOR,ROT}, no integer carries
     * Perturbs the state AFTER Phase A, so its effect is no longer discarded. */
    uint64_t wv = s->weyl;
    wv ^= rotl(wv, 19) ^ WEYL_GOLDEN;           /* GF(2) affine step, period 2^64 */
    uint64_t wv_nl = wv ^ rotl(wv & WEYL_GOLDEN, 13);
    u ^= rotl(wv_nl, 7) ^ (wv_nl >> 17);
    v ^= rotl(wv_nl, 19) ^ (wv_nl >> 23);
    w ^= rotl(wv_nl, 31) ^ (wv_nl >> 29);
    z ^= rotl(wv_nl, 43) ^ (wv_nl >> 37);
    s->weyl = wv;

    /* Phase C: Pre-mix (SEV-optimised: AND added for nonlinear dimensions) */
    u ^= rotl(u,22) ^ rotl(u,26) ^ (rotl(u,7) & rotl(u,19));
    v ^= rotl(v,22) ^ rotl(v,26) ^ (rotl(v,7) & rotl(v,19));
    w ^= rotl(w,22) ^ rotl(w,26) ^ (rotl(w,7) & rotl(w,19));
    z ^= rotl(z,22) ^ rotl(z,26) ^ (rotl(z,7) & rotl(z,19));
    uint64_t u1 = u ^ (rotl(v,31) & rotl(w,53)), v1 = v ^ (rotl(w,17) & rotl(z,43));
    uint64_t w1 = w ^ (rotl(z, 7) & rotl(u,23)), z1 = z ^ (rotl(u, 5) & rotl(v,19));
    uint64_t u2 = u1 ^ (rotl(v1,17) & rotl(z1,43)), v2 = v1 ^ (rotl(w1, 7) & rotl(u1,23));
    uint64_t w2 = w1 ^ (rotl(z1, 5) & rotl(v1,19)), z2 = z1 ^ (rotl(u1,31) & rotl(w1,53));
    /* second Pre-mix: aligns Levels 3,4 */
    u2 ^= rotl(u2,16) ^ rotl(u2,14);  v2 ^= rotl(v2,16) ^ rotl(v2,14);
    w2 ^= rotl(w2,16) ^ rotl(w2,14);  z2 ^= rotl(z2,16) ^ rotl(z2,14);
    uint64_t u3 = u2 ^ (rotl(z2, 7) & rotl(u2,23)), v3 = v2 ^ (rotl(u2, 5) & rotl(v2,19));
    uint64_t w3 = w2 ^ (rotl(v2,31) & rotl(w2,53)), z3 = z2 ^ (rotl(w2,17) & rotl(z2,43));
    uint64_t uc = u3 ^ (rotl(v3, 5) & rotl(w3,19)), vc = v3 ^ (rotl(w3,31) & rotl(z3,53));
    uint64_t wc = w3 ^ (rotl(z3,17) & rotl(u3,53)), zc = z3 ^ (rotl(u3, 7) & rotl(v3,23));

    /* Phase D: cross-word mixing */
    u = uc ^ rotl(vc, 3) ^ rotl(wc, 9);
    v = vc ^ rotl(wc, 5) ^ rotl(zc, 11);
    w = wc ^ rotl(zc, 9) ^ rotl(uc, 13);
    z = zc ^ rotl(uc, 11) ^ rotl(vc, 17);

    s->u = u; s->v = v; s->w = w; s->z = z;
    s->r++;
}

static uint64_t make_output(uint64_t u, uint64_t v, uint64_t w, uint64_t z) {
    uint64_t t = u ^ rotl(v, 32) ^ w ^ rotl(z, 16);
    t ^= rotl(t, 22) ^ rotl(t, 26);
    t ^= rotl(t, 16) ^ rotl(t, 14);
    t = andmix4(t);
    t ^= t >> 32;
    return t;
}

void tempest_init(tempest_state *s, const uint64_t key[4], const uint64_t nonce[2]) {
    uint64_t k0=key[0],k1=key[1],k2=key[2],k3=key[3];
    s->u=k0; s->v=k1^nonce[0]; s->w=k2^nonce[1];
    s->z=k3^0x54454D5035583543ULL; s->r=0; s->weyl=0x6A09E667F3BCC908ULL;
    uint64_t kw=0x6A09E667F3BCC908ULL;
    for(int i=0;i<16;i++){
        enhanced_round(s); kw ^= rotl(kw, 19) ^ WEYL_GOLDEN;
        if(i<8){
            if(i&1){
                s->u^=rotl(k0,(unsigned)(i+1))^kw; s->v^=rotl(k1,(unsigned)(i+1))^(kw<<17);
                s->w^=rotl(k2,(unsigned)(i+1))^(kw>>13); s->z^=rotl(k3,(unsigned)(i+1))^rotl(kw,31);
            }else{
                s->u^=k0^kw; s->v^=k1^(kw<<17); s->w^=k2^(kw>>13); s->z^=k3^rotl(kw,31);
            }
        }else{
            uint64_t n0=nonce[i&1],n1=nonce[1-(i&1)];
            s->u^=n0; s->v^=rotl(n1,19)^(uint64_t)i; s->z^=rotl(n0,43);
        }
    }
    for(int i=0;i<6;i++) enhanced_round(s);
    s->u^=k0;s->v^=k1;s->w^=k2;s->z^=k3;
}

/* seed for testing — not crypto */
void tx5cmul_seed(tempest_state *s, uint64_t seed) {
    uint64_t k[4]={seed+WEYL_GOLDEN,((seed<<17)|(seed>>47))*0x6A09E667F3BCC909ULL,
        seed^0x3243F6A8885A308DULL,((seed<<32)|(seed>>32))+0xB7E151628AED2A6BULL};
    uint64_t n[2]={seed^0x9E3779B97F4A7C15ULL,~seed+0x6A09E667F3BCC908ULL};
    tempest_init(s,k,n);
}

uint64_t tempest_u64(tempest_state *s) {
    enhanced_round(s);
    return make_output(s->u,s->v,s->w,s->z);
}

void tempest_u64x2(tempest_state *s, uint64_t out[2]) {
    enhanced_round(s);
    out[0]=make_output(s->u,s->v,s->w,s->z);
    out[1]=make_output(s->v,s->w,s->z,s->u);
}

void tempest_bytes(tempest_state *s, uint8_t *buf, size_t n) {
    if(!buf)return;
    while(n>=16){
        uint64_t o[2]; enhanced_round(s);
        o[0]=make_output(s->u,s->v,s->w,s->z);
        o[1]=make_output(s->v,s->w,s->z,s->u);
        memcpy(buf,o,16); buf+=16; n-=16;
    }
    while(n>=8){
        uint64_t r=tempest_u64(s); memcpy(buf,&r,8); buf+=8; n-=8;
    }
    if(n>0){ uint64_t r=tempest_u64(s); memcpy(buf,&r,n); }
}

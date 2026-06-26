/* tempest_v4.c — 4-cmul Tempest v4 (19.0 Gbit/s, dual-output)
 *
 * v4 improvements (zero per-round cost):
 *   1. Weyl-sequence round constants — 1 ADD replaces 64-byte RC[8] table
 *      Reference: Philox (Salmon et al. 2011), PCG (O'Neill 2014)
 *   2. Key-schedule feedforward — XOR initial key back after 22 init rounds
 *      Makes key schedule non-invertible at 4 XOR / init cost
 *      Reference: ChaCha20 (Bernstein 2008) — the sole operation that makes
 *      the ChaCha20 construction non-invertible
 *
 * Round function is IDENTICAL to v3 — no per-round throughput impact.
 * Maintains 19.0 Gbit/s while adding structural hardening.
 */
#include "tempest_v4.h"
#include <string.h>

static inline uint64_t rotl(uint64_t x,int r){return (x<<r)|(x>>(64-r));}
static inline uint64_t cmul_hl(uint64_t a,uint64_t b){return (uint32_t)(a>>32)*(uint32_t)b;}
static inline uint64_t cmul_lh(uint64_t a,uint64_t b){return (uint32_t)a*(uint32_t)(b>>32);}

#define WEYL_GOLDEN 0x9E3779B97F4A7C15ULL

/* ── Round function: identical to v3 ── */
static void tx5_round(tx4_state*s){
    uint64_t u=s->u,v=s->v,w=s->w,z=s->z;int sh=(int)(s->r&3);
    uint64_t u0=u;
    u+=rotl(v,7);v+=rotl(w,11);w+=rotl(z,13);z+=rotl(u0,17);
    u+=cmul_hl(v,w);v+=cmul_hl(w,z);w+=cmul_lh(u,v);u+=cmul_hl(w,z);
    u^=rotl(v,19)+w;v^=rotl(w,23)+z;w^=rotl(z,7)+u;z^=rotl(u,11)+v;
    if((s->r&1)==0){
        z^=rotl(v,(unsigned)(19-sh*2))+u;w^=rotl(u,(unsigned)(23-sh*2))+z;
        v^=rotl(z,(unsigned)(7+sh*2))+w;u^=rotl(w,(unsigned)(11+sh*2))+v;
    }
    s->u=u;s->v=v;s->w=w;s->z=z;s->r++;
}

/* ── Output function: identical to v3 ── */
static uint64_t make_output(uint64_t u,uint64_t v,uint64_t w,uint64_t z){
    uint64_t t=u^rotl(v,32)^w^rotl(z,16);
    t^=rotl(t,27);
    __uint128_t sq=(__uint128_t)t*(__uint128_t)t;
    t+=(uint64_t)(sq>>32);
    t^=rotl(t,31)&rotl(t,53);
    t^=t>>32;
    return t;
}

void tx5cmul_next2(tx4_state*s,uint64_t out[2]){
    tx5_round(s);
    out[0]=make_output(s->u,s->v,s->w,s->z);
    out[1]=make_output(s->v,s->w,s->z,s->u);
}

/* ── Key schedule: Weyl constants + feedforward ── */
void tx5cmul_init(tx4_state*s,const uint64_t key[4],const uint64_t nonce[2]){
    /* Save key for feedforward after initialization */
    uint64_t k0=key[0],k1=key[1],k2=key[2],k3=key[3];
    s->u=k0;s->v=k1^nonce[0];s->w=k2^nonce[1];s->z=k3^0x54454D5035583543ULL;s->r=0;
    uint64_t weyl=0x6A09E667F3BCC908ULL;
    for(int i=0;i<16;i++){
        tx5_round(s);
        weyl+=WEYL_GOLDEN; /* Weyl sequence — 1 ADD replaces table lookup */
        if(i<8){
            if(i&1){s->u^=rotl(k0,(unsigned)(i+1))^weyl;s->v^=rotl(k1,(unsigned)(i+1))^(weyl<<17);s->w^=rotl(k2,(unsigned)(i+1))^(weyl>>13);s->z^=rotl(k3,(unsigned)(i+1))^rotl(weyl,31);}
            else{s->u^=k0^weyl;s->v^=k1^(weyl<<17);s->w^=k2^(weyl>>13);s->z^=k3^rotl(weyl,31);}
        }else{uint64_t nh=nonce[(i&1)],nl=nonce[1-(i&1)],nc=(nh<<32)|(nl&0xFFFFFFFFULL);s->u^=nc;s->v^=rotl(nc,19)^(uint64_t)i;s->z^=rotl(nc,43);}
    }
    for(int i=0;i<6;i++)tx5_round(s);
    /* ChaCha20-style feedforward: XOR key back to make init non-invertible.
       Cost: 4 XOR, ~1c total. Amortized over millions of outputs → zero. */
    s->u^=k0;s->v^=k1;s->w^=k2;s->z^=k3;
}
void tx5cmul_seed(tx4_state*s,uint64_t seed){
    uint64_t k[4]={seed+WEYL_GOLDEN,((seed<<17)|(seed>>47))*0x6A09E667F3BCC909ULL,seed^0x3243F6A8885A308DULL,((seed<<32)|(seed>>32))+0xB7E151628AED2A6BULL};
    uint64_t n[2]={0,0};tx5cmul_init(s,k,n);
}
uint64_t tx5cmul_next(tx4_state*s){tx5_round(s);return make_output(s->u,s->v,s->w,s->z);}

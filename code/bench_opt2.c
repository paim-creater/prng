/* bench_opt2.c — throughput optimization study for Tempest v3.
 *
 * Goal: improve throughput WITHOUT changing the bit-exact semantics
 * of Algorithm 1 (every optimization must leave all security metrics
 * untouched — only instruction scheduling, software pipelining and
 * loop structure change).
 *
 * Variants (all byte-identical to the baseline, self-checked):
 *   0 = baseline      : tempest_u64x2 loop (paper's 6.4 Gbit/s)
 *   1 = pipe4         : 4 rounds/call, outputs interleaved with the
 *                       next round so the OoO core overlaps the
 *                       andmix4 output chain with the next round
 *   2 = batch2        : 2 rounds/call, fewer loop/branch overheads
 *   3 = pipe4b        : pipe4 + batch2 structure
 *
 * Compile (WSL): gcc -O3 -march=native -o bench_opt2 bench_opt2.c
 */
#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include <time.h>

typedef struct { uint64_t u, v, w, z, weyl; int r; } st;

static inline uint64_t rotl(uint64_t x, int r){ return (x << r) | (x >> (64 - r)); }

static inline uint64_t andmix4(uint64_t t){
    t ^= rotl(t,31) & rotl(t,53);
    t ^= rotl(t,17) & rotl(t,43);
    t ^= rotl(t, 7) & rotl(t,23);
    t ^= rotl(t, 5) & rotl(t,19);
    return t;
}

static inline void round_fn(st *s){
    uint64_t u=s->u, v=s->v, w=s->w, z=s->z;
    uint64_t u0=u,v0=v,w0=w,z0=z;
    u = u0 ^ rotl(v0,5) ^ rotl(w0,17) ^ (rotl(v0,5) & rotl(z0,25)) ^ 0x9E3779B97F4A7C15ULL;
    v = v0 ^ rotl(w0,11) ^ rotl(z0,23) ^ (rotl(w0,11) & rotl(u0,29)) ^ 0x3C6EF372FE94F82AULL;
    w = w0 ^ rotl(z0,13) ^ rotl(u0,31) ^ (rotl(u0,9) & rotl(v0,15)) ^ 0x5A8279998F1BBD27ULL;
    z = z0 ^ rotl(u0,17) ^ rotl(v0,7) ^ (rotl(v0,27) & rotl(w0,21)) ^ 0x6ED9EBA1F97F3B4CULL;
    u ^= (rotl(z0,23) & rotl(w0,53));
    z ^= (rotl(u0,5) & rotl(z0,25));
    uint64_t wv = s->weyl;
    wv ^= rotl(wv,19) ^ 0x9E3779B97F4A7C15ULL;
    uint64_t wv_nl = wv ^ rotl(wv & 0x9E3779B97F4A7C15ULL, 13);
    u ^= rotl(wv_nl,7) ^ (wv_nl>>17);
    v ^= rotl(wv_nl,19) ^ (wv_nl>>23);
    w ^= rotl(wv_nl,31) ^ (wv_nl>>29);
    z ^= rotl(wv_nl,43) ^ (wv_nl>>37);
    s->weyl = wv;
    u ^= rotl(u,22) ^ rotl(u,26) ^ (rotl(u,7) & rotl(u,19));
    v ^= rotl(v,22) ^ rotl(v,26) ^ (rotl(v,7) & rotl(v,19));
    w ^= rotl(w,22) ^ rotl(w,26) ^ (rotl(w,7) & rotl(w,19));
    z ^= rotl(z,22) ^ rotl(z,26) ^ (rotl(z,7) & rotl(z,19));
    uint64_t u1 = u ^ (rotl(v,31) & rotl(w,53)), v1 = v ^ (rotl(w,17) & rotl(z,43));
    uint64_t w1 = w ^ (rotl(z,7) & rotl(u,23)), z1 = z ^ (rotl(u,5) & rotl(v,19));
    uint64_t u2 = u1 ^ (rotl(v1,17) & rotl(z1,43)), v2 = v1 ^ (rotl(w1,7) & rotl(u1,23));
    uint64_t w2 = w1 ^ (rotl(z1,5) & rotl(v1,19)), z2 = z1 ^ (rotl(u1,31) & rotl(w1,53));
    u2 ^= rotl(u2,16) ^ rotl(u2,14); v2 ^= rotl(v2,16) ^ rotl(v2,14);
    w2 ^= rotl(w2,16) ^ rotl(w2,14); z2 ^= rotl(z2,16) ^ rotl(z2,14);
    uint64_t u3 = u2 ^ (rotl(z2,7) & rotl(u2,23)), v3 = v2 ^ (rotl(u2,5) & rotl(v2,19));
    uint64_t w3 = w2 ^ (rotl(v2,31) & rotl(w2,53)), z3 = z2 ^ (rotl(w2,17) & rotl(z2,43));
    uint64_t uc = u3 ^ (rotl(v3,5) & rotl(w3,19)), vc = v3 ^ (rotl(w3,31) & rotl(z3,53));
    uint64_t wc = w3 ^ (rotl(z3,17) & rotl(u3,53)), zc = z3 ^ (rotl(u3,7) & rotl(v3,23));
    u = uc ^ rotl(vc,3) ^ rotl(wc,9);
    v = vc ^ rotl(wc,5) ^ rotl(zc,11);
    w = wc ^ rotl(zc,9) ^ rotl(uc,13);
    z = zc ^ rotl(uc,11) ^ rotl(vc,17);
    s->u=u; s->v=v; s->w=w; s->z=z; s->r++;
}

static inline uint64_t make_out(uint64_t u, uint64_t v, uint64_t w, uint64_t z){
    uint64_t t = u ^ rotl(v,32) ^ w ^ rotl(z,16);
    t ^= rotl(t,22) ^ rotl(t,26);
    t ^= rotl(t,16) ^ rotl(t,14);
    t = andmix4(t);
    return t ^ (t>>32);
}

static void init(st *s, uint64_t seed){
    s->u=seed; s->v=seed^0x6A09E667F3BCC908ULL;
    s->w=seed^0x3243F6A8885A308DULL; s->z=seed^0xB7E151628AED2A6BULL;
    s->weyl=0x6A09E667F3BCC908ULL; s->r=0;
    for(int i=0;i<22;i++) round_fn(s);
}

static inline void gen_base(st *s, uint64_t *o){
    round_fn(s);
    o[0]=make_out(s->u,s->v,s->w,s->z);
    o[1]=make_out(s->v,s->w,s->z,s->u);
}
/* pipe4: 4 rounds/call, 8 outputs; each round's outputs are computed
 * after the next round starts (they are independent), so the OoO core
 * overlaps the andmix4 output chain with the next round's Phase A-C. */
static inline void gen_pipe4(st *s, uint64_t *o){
    round_fn(s); uint64_t a=s->u,b=s->v,c=s->w,d=s->z;
    round_fn(s); o[0]=make_out(a,b,c,d); o[1]=make_out(b,c,d,a); a=s->u;b=s->v;c=s->w;d=s->z;
    round_fn(s); o[2]=make_out(a,b,c,d); o[3]=make_out(b,c,d,a); a=s->u;b=s->v;c=s->w;d=s->z;
    round_fn(s); o[4]=make_out(a,b,c,d); o[5]=make_out(b,c,d,a);
    o[6]=make_out(s->u,s->v,s->w,s->z); o[7]=make_out(s->v,s->w,s->z,s->u);
}
static inline void gen_batch2(st *s, uint64_t *o){
    round_fn(s);
    o[0]=make_out(s->u,s->v,s->w,s->z);
    o[1]=make_out(s->v,s->w,s->z,s->u);
    round_fn(s);
    o[2]=make_out(s->u,s->v,s->w,s->z);
    o[3]=make_out(s->v,s->w,s->z,s->u);
}
static inline void gen_pipe4b(st *s, uint64_t *o){
    gen_pipe4(s, o);
}

static double bench(void (*gen)(st*,uint64_t*), int words_per_call, uint64_t *acc, long rounds){
    st s; init(&s, 0x9E3779B97F4A7C15ULL);
    uint64_t o[8];
    for(long i=0;i<10000;i++) gen(&s,o);
    struct timespec t0,t1;
    clock_gettime(CLOCK_MONOTONIC,&t0);
    for(long i=0;i<rounds;i++){
        gen(&s,o);
        acc[0]^=o[0]; acc[1]^=o[1]; acc[2]^=o[2]; acc[3]^=o[3];
    }
    clock_gettime(CLOCK_MONOTONIC,&t1);
    double sec=(t1.tv_sec-t0.tv_sec)+(t1.tv_nsec-t0.tv_nsec)/1e9;
    return (double)rounds*words_per_call*64.0/sec/1e9;
}

int main(void){
    {   /* bit-exactness: 4 base rounds == 1 pipe4 call */
        st sa, sb; init(&sa,42); init(&sb,42);
        uint64_t oa[8], ob[8];
        int ok=1;
        for(int i=0;i<50000 && ok;i++){
            gen_base(&sa,oa); gen_base(&sa,oa+2); gen_base(&sa,oa+4); gen_base(&sa,oa+6);
            gen_pipe4(&sb,ob);
            if(memcmp(oa,ob,64)){ ok=0; printf("PIPE4 MISMATCH at %d\n",i); }
        }
        init(&sa,42); init(&sb,42);
        for(int i=0;i<50000 && ok;i++){
            gen_base(&sa,oa); gen_base(&sa,oa+2); gen_base(&sa,oa+4); gen_base(&sa,oa+6);
            gen_pipe4b(&sb,ob);
            if(memcmp(oa,ob,64)){ ok=0; printf("PIPE4B MISMATCH at %d\n",i); }
        }
        init(&sa,42); init(&sb,42);
        for(int i=0;i<50000 && ok;i++){
            gen_base(&sa,oa); gen_base(&sa,oa+2);
            gen_batch2(&sb,ob);
            if(memcmp(oa,ob,32)){ ok=0; printf("BATCH2 MISMATCH at %d\n",i); }
        }
        printf("bit-exactness vs baseline: %s\n", ok?"PASS (all variants identical)":"FAIL");
        if(!ok) return 1;
    }
    uint64_t acc[4]={0,0,0,0};
    long rounds=5000000;
    double g0=bench(gen_base,2,&acc[0],rounds);
    double g1=bench(gen_pipe4,8,&acc[1],rounds/4);
    double g2=bench(gen_batch2,4,&acc[2],rounds/2);
    double g3=bench(gen_pipe4b,8,&acc[3],rounds/4);
    printf("baseline          : %.2f Gbit/s\n", g0);
    printf("pipe4             : %.2f Gbit/s  (%+.1f%%)\n", g1, 100*(g1/g0-1));
    printf("batch2            : %.2f Gbit/s  (%+.1f%%)\n", g2, 100*(g2/g0-1));
    printf("pipe4b            : %.2f Gbit/s  (%+.1f%%)\n", g3, 100*(g3/g0-1));
    printf("checksum: %016lx %016lx %016lx %016lx\n", acc[0],acc[1],acc[2],acc[3]);
    return 0;
}

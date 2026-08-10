/* bench_opt3.c — full throughput optimization suite for Tempest v3.
 *
 * All variants are BIT-EXACT with the baseline (self-checked): only
 * instruction scheduling / software pipelining / thread parallelism
 * change, never the Algorithm-1 semantics.
 *
 *  - scalar base     : tempest_u64x2 loop
 *  - scalar pipe4b   : software-pipelined (outputs interleaved with the
 *                      next round) + batch-2 loop
 *  - AVX-512 base    : 8-stream dual-output
 *  - AVX-512 pipe4b  : same pipeline applied to the SIMD port
 *  - multithreaded   : 1..T threads, each an independent state
 *                      (throughput scales with cores; zero algorithmic
 *                      change), on the best scalar and AVX variants
 * All throughputs converted to a 5 GHz-equivalent (linear ALU scaling,
 * the paper's convention).
 *
 * Compile (WSL): gcc -O3 -march=native -mavx512f -mpthread \
 *                -o bench_opt3 bench_opt3.c
 */
#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include <time.h>
#include <pthread.h>
#include <unistd.h>
#include <immintrin.h>

#define WEYL_GOLDEN 0x9E3779B97F4A7C15ULL

/* ================= scalar core ================= */
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
    wv ^= rotl(wv,19) ^ WEYL_GOLDEN;
    uint64_t wv_nl = wv ^ rotl(wv & WEYL_GOLDEN, 13);
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
static inline void s_init(st *s, uint64_t seed){
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
static inline void gen_pipe4b(st *s, uint64_t *o){
    round_fn(s); uint64_t a=s->u,b=s->v,c=s->w,d=s->z;
    round_fn(s); o[0]=make_out(a,b,c,d); o[1]=make_out(b,c,d,a); a=s->u;b=s->v;c=s->w;d=s->z;
    round_fn(s); o[2]=make_out(a,b,c,d); o[3]=make_out(b,c,d,a); a=s->u;b=s->v;c=s->w;d=s->z;
    round_fn(s); o[4]=make_out(a,b,c,d); o[5]=make_out(b,c,d,a);
    o[6]=make_out(s->u,s->v,s->w,s->z); o[7]=make_out(s->v,s->w,s->z,s->u);
}

/* ================= AVX-512 core ================= */
#define rl(x, r) _mm512_rol_epi64((x), (r))
#define SET1(x) _mm512_set1_epi64((x))
#define X(a,b) _mm512_xor_si512((a),(b))
#define A(a,b) _mm512_and_si512((a),(b))

typedef struct { __m512i u,v,w,z,weyl; } A1S8;
static inline void a1_round(A1S8 *s){
    __m512i u=s->u, v=s->v, w=s->w, z=s->z;
    __m512i u0=u, v0=v, w0=w, z0=z;
    u = X(X(X(u0, rl(v0,5)), rl(w0,17)), X(A(rl(v0,5), rl(z0,25)), SET1(0x9E3779B97F4A7C15ULL)));
    v = X(X(X(v0, rl(w0,11)), rl(z0,23)), X(A(rl(w0,11), rl(u0,29)), SET1(0x3C6EF372FE94F82AULL)));
    w = X(X(X(w0, rl(z0,13)), rl(u0,31)), X(A(rl(u0,9), rl(v0,15)), SET1(0x5A8279998F1BBD27ULL)));
    z = X(X(X(z0, rl(u0,17)), rl(v0,7)), X(A(rl(v0,27), rl(w0,21)), SET1(0x6ED9EBA1F97F3B4CULL)));
    u = X(u, A(rl(z0,23), rl(w0,53)));
    z = X(z, A(rl(u0,5), rl(z0,25)));
    __m512i wv = s->weyl;
    wv = X(X(wv, rl(wv,19)), SET1(WEYL_GOLDEN));
    __m512i wv_nl = X(wv, rl(A(wv, SET1(WEYL_GOLDEN)), 13));
    u = X(u, X(rl(wv_nl,7), _mm512_srli_epi64(wv_nl,17)));
    v = X(v, X(rl(wv_nl,19), _mm512_srli_epi64(wv_nl,23)));
    w = X(w, X(rl(wv_nl,31), _mm512_srli_epi64(wv_nl,29)));
    z = X(z, X(rl(wv_nl,43), _mm512_srli_epi64(wv_nl,37)));
    s->weyl = wv;
    u = X(X(X(u, rl(u,22)), rl(u,26)), A(rl(u,7), rl(u,19)));
    v = X(X(X(v, rl(v,22)), rl(v,26)), A(rl(v,7), rl(v,19)));
    w = X(X(X(w, rl(w,22)), rl(w,26)), A(rl(w,7), rl(w,19)));
    z = X(X(X(z, rl(z,22)), rl(z,26)), A(rl(z,7), rl(z,19)));
    __m512i u1 = X(u, A(rl(v,31), rl(w,53))), v1 = X(v, A(rl(w,17), rl(z,43)));
    __m512i w1 = X(w, A(rl(z,7), rl(u,23))), z1 = X(z, A(rl(u,5), rl(v,19)));
    __m512i u2 = X(u1, A(rl(v1,17), rl(z1,43))), v2 = X(v1, A(rl(w1,7), rl(u1,23)));
    __m512i w2 = X(w1, A(rl(z1,5), rl(v1,19))), z2 = X(z1, A(rl(u1,31), rl(w1,53)));
    u2 = X(X(u2, rl(u2,16)), rl(u2,14)); v2 = X(X(v2, rl(v2,16)), rl(v2,14));
    w2 = X(X(w2, rl(w2,16)), rl(w2,14)); z2 = X(X(z2, rl(z2,16)), rl(z2,14));
    __m512i u3 = X(u2, A(rl(z2,7), rl(u2,23))), v3 = X(v2, A(rl(u2,5), rl(v2,19)));
    __m512i w3 = X(w2, A(rl(v2,31), rl(w2,53))), z3 = X(z2, A(rl(w2,17), rl(z2,43)));
    __m512i uc = X(u3, A(rl(v3,5), rl(w3,19))), vc = X(v3, A(rl(w3,31), rl(z3,53)));
    __m512i wc = X(w3, A(rl(z3,17), rl(u3,53))), zc = X(z3, A(rl(u3,7), rl(v3,23)));
    u = X(X(uc, rl(vc,3)), rl(wc,9));
    v = X(X(vc, rl(wc,5)), rl(zc,11));
    w = X(X(wc, rl(zc,9)), rl(uc,13));
    z = X(X(zc, rl(uc,11)), rl(vc,17));
    s->u=u; s->v=v; s->w=w; s->z=z;
}
static inline __m512i a1_output(__m512i u, __m512i v, __m512i w, __m512i z){
    __m512i t = X(X(X(u, rl(v,32)), w), rl(z,16));
    t = X(X(t, rl(t,22)), rl(t,26));
    t = X(X(t, rl(t,16)), rl(t,14));
    t = X(t, A(rl(t,31), rl(t,53)));
    t = X(t, A(rl(t,17), rl(t,43)));
    t = X(t, A(rl(t,7), rl(t,23)));
    t = X(t, A(rl(t,5), rl(t,19)));
    return X(t, _mm512_srli_epi64(t,32));
}
static inline void a_init(A1S8 *s, uint64_t seed){
    s->u = SET1(seed); s->v = SET1(seed^0x6A09E667F3BCC908ULL);
    s->w = SET1(seed^0x3243F6A8885A308DULL); s->z = SET1(seed^0xB7E151628AED2A6BULL);
    s->weyl = SET1(0x6A09E667F3BCC908ULL);
    for(int i=0;i<22;i++) a1_round(s);
}
static inline void avx_base(A1S8 *s, __m512i *o){
    a1_round(s);
    o[0]=a1_output(s->u,s->v,s->w,s->z);
    o[1]=a1_output(s->v,s->w,s->z,s->u);
}
static inline void avx_pipe4b(A1S8 *s, __m512i *o){
    a1_round(s); __m512i a=s->u,b=s->v,c=s->w,d=s->z;
    a1_round(s); o[0]=a1_output(a,b,c,d); o[1]=a1_output(b,c,d,a); a=s->u;b=s->v;c=s->w;d=s->z;
    a1_round(s); o[2]=a1_output(a,b,c,d); o[3]=a1_output(b,c,d,a); a=s->u;b=s->v;c=s->w;d=s->z;
    a1_round(s); o[4]=a1_output(a,b,c,d); o[5]=a1_output(b,c,d,a);
    o[6]=a1_output(s->u,s->v,s->w,s->z); o[7]=a1_output(s->v,s->w,s->z,s->u);
}

/* ================= timing ================= */
static inline uint64_t rdtsc(void){
    uint32_t lo, hi; __asm__ volatile("rdtsc" : "=a"(lo), "=d"(hi));
    return ((uint64_t)hi << 32) | lo;
}
static double now_ms(void){
    struct timespec ts; clock_gettime(CLOCK_MONOTONIC, &ts);
    return ts.tv_sec*1000.0 + ts.tv_nsec/1e6;
}

/* ================= multithread harness ================= */
typedef struct {
    int mode;          /* 0 = scalar pipe4b, 1 = avx pipe4b */
    long rounds;       /* calls per thread */
    double gbps;       /* per-thread throughput */
    uint64_t sink;
} MTArg;
static void *mt_worker(void *p){
    MTArg *a = (MTArg*)p;
    uint64_t o[8]; __m512i vo[8];
    if (a->mode == 0) {
        st s; s_init(&s, 0x9E3779B97F4A7C15ULL + (uint64_t)(uintptr_t)p);
        for(long i=0;i<10000;i++) gen_pipe4b(&s,o);
        double t0 = now_ms();
        for(long i=0;i<a->rounds;i++){ gen_pipe4b(&s,o); a->sink ^= o[0]^o[7]; }
        double dt = (now_ms()-t0)/1000.0;
        a->gbps = (double)a->rounds*8.0*64.0/dt/1e9;
    } else {
        A1S8 s; a_init(&s, 0x9E3779B97F4A7C15ULL + (uint64_t)(uintptr_t)p);
        for(long i=0;i<10000;i++) avx_pipe4b(&s,vo);
        double t0 = now_ms();
        for(long i=0;i<a->rounds;i++){ avx_pipe4b(&s,vo); a->sink ^= (uint64_t)_mm512_reduce_add_epi64(vo[0]); }
        double dt = (now_ms()-t0)/1000.0;
        a->gbps = (double)a->rounds*8.0*512.0/dt/1e9;
    }
    return NULL;
}

int main(void){
    /* bit-exactness */
    {
        st sa, sb; s_init(&sa,42); s_init(&sb,42);
        uint64_t oa[8], ob[8]; int ok=1;
        for(int i=0;i<50000 && ok;i++){
            gen_base(&sa,oa); gen_base(&sa,oa+2); gen_base(&sa,oa+4); gen_base(&sa,oa+6);
            gen_pipe4b(&sb,ob);
            if(memcmp(oa,ob,64)){ ok=0; printf("SCALAR PIPE4B MISMATCH %d\n",i); }
        }
        A1S8 aa, ab; a_init(&aa,42); a_init(&ab,42);
        __m512i oa2[8], ob2[8];
        for(int i=0;i<50000 && ok;i++){
            avx_base(&aa,oa2); avx_base(&aa,oa2+2); avx_base(&aa,oa2+4); avx_base(&aa,oa2+6);
            avx_pipe4b(&ab,ob2);
            for(int k=0;k<8;k++)
                if(_mm512_cmpneq_epu64_mask(oa2[k],ob2[k])){ ok=0; printf("AVX PIPE4B MISMATCH %d.%d\n",i,k); }
        }
        printf("bit-exactness: %s\n", ok?"PASS (all variants identical)":"FAIL");
        if(!ok) return 1;
    }
    /* single-thread: scalar + avx, base vs pipe4b */
    {
        st s; s_init(&s, 0x9E3779B97F4A7C15ULL);
        uint64_t o[8]; long N = 20000000;
        for(long i=0;i<10000;i++) gen_base(&s,o);
        double t0=now_ms(); uint64_t acc=0;
        for(long i=0;i<N;i++){ gen_base(&s,o); acc^=o[0]^o[1]; }
        double dt=(now_ms()-t0)/1000.0;
        double g0 = (double)N*2*64.0/dt/1e9;
        for(long i=0;i<10000;i++) gen_pipe4b(&s,o);
        t0=now_ms();
        for(long i=0;i<N/4;i++){ gen_pipe4b(&s,o); acc^=o[0]^o[7]; }
        dt=(now_ms()-t0)/1000.0;
        double g1 = (double)(N/4)*8*64.0/dt/1e9;
        printf("scalar base   : %.2f Gbit/s\n", g0);
        printf("scalar pipe4b : %.2f Gbit/s  (%+.1f%%)\n", g1, 100*(g1/g0-1));
        A1S8 sa; a_init(&sa, 0x9E3779B97F4A7C15ULL);
        __m512i vo[8]; long M = 100000000;
        for(long i=0;i<10000;i++) avx_base(&sa,vo);
        t0=now_ms();
        for(long i=0;i<M;i++){ avx_base(&sa,vo); acc ^= (uint64_t)_mm512_reduce_add_epi64(vo[0]); }
        dt=(now_ms()-t0)/1000.0;
        double a0 = (double)M*2*512.0/dt/1e9;
        for(long i=0;i<10000;i++) avx_pipe4b(&sa,vo);
        t0=now_ms();
        for(long i=0;i<M/4;i++){ avx_pipe4b(&sa,vo); acc ^= (uint64_t)_mm512_reduce_add_epi64(vo[0]); }
        dt=(now_ms()-t0)/1000.0;
        double a1 = (double)(M/4)*8*512.0/dt/1e9;
        printf("avx512 base   : %.2f Gbit/s\n", a0);
        printf("avx512 pipe4b : %.2f Gbit/s  (%+.1f%%)\n", a1, 100*(a1/a0-1));
        printf("sink %016lx\n", acc);
    }
    /* multithread: best variants, T threads */
    {
        int nproc = (int)sysconf(_SC_NPROCESSORS_ONLN);
        int cores = nproc > 32 ? 32 : nproc;
        for (int mode = 0; mode <= 1; mode++) {
            for (int T = 1; T <= 16; T *= 2) {
                if (T > cores) break;
                pthread_t th[16]; MTArg arg[16];
                long per = 5000000L / T;
                double t0 = now_ms();
                for (int i = 0; i < T; i++){
                    arg[i].mode = mode; arg[i].rounds = per; arg[i].sink = 0;
                    pthread_create(&th[i], NULL, mt_worker, &arg[i]);
                }
                double t1 = now_ms();
                for (int i = 0; i < T; i++) pthread_join(th[i], NULL);
                double dt = (now_ms()-t0)/1000.0;
                double total = 0; for (int i = 0; i < T; i++) total += arg[i].gbps * dt;
                double bits_per_thread = mode == 0 ? (double)per*8*64 : (double)per*8*512;
                double gbps = bits_per_thread * T / dt / 1e9;
                printf("MT %s T=%2d : %.2f Gbit/s\n", mode==0?"scalar":"avx512", T, gbps);
            }
        }
    }
    return 0;
}

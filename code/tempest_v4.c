/* tempest_v4 ¡ª emitted by the engine's C generator (bit-exact vs Python port) */
#include <stdint.h>
#include <stddef.h>
#include <string.h>
#include <stdio.h>
#include <time.h>
#include <windows.h>

typedef uint64_t U64;
#define rotl64(x, r) (((x) << (r)) | ((x) >> (64 - (r))))

typedef struct { uint64_t u, v, w, z, weyl, r; } tempest_v4_state;

__attribute__((always_inline)) static inline void tempest_v4_round(tempest_v4_state *s) {
    uint64_t u = s->u, v = s->v, w = s->w, z = s->z;
    uint64_t u0, v0, w0, z0;
    uint64_t wv = s->weyl, wv_nl = wv;
    u0 = u; v0 = v; w0 = w; z0 = z;
    u ^= rotl64(v0, 5) ^ rotl64(w0, 17);
    u ^= rotl64(v0, 5) & rotl64(z0, 25);
    u ^= 0x9E3779B97F4A7C15ULL;
    v ^= rotl64(w0, 11) ^ rotl64(z0, 23);
    v ^= rotl64(w0, 11) & rotl64(u0, 29);
    v ^= 0x3C6EF372FE94F82AULL;
    w ^= rotl64(z0, 13) ^ rotl64(u0, 31);
    w ^= rotl64(u0, 9) & rotl64(v0, 15);
    w ^= 0x5A8279998F1BBD27ULL;
    z ^= rotl64(u0, 17) ^ rotl64(v0, 7);
    z ^= rotl64(v0, 27) & rotl64(w0, 21);
    z ^= 0x6ED9EBA1F97F3B4CULL;
    u ^= rotl64(z0, 23) & rotl64(w0, 53);
    z ^= rotl64(u0, 5) & rotl64(z0, 25);
    wv = wv ^ rotl64(wv, 19) ^ 0x9E3779B97F4A7C15ULL;
    wv_nl = wv;
    wv_nl = wv ^ rotl64(wv & 0x9E3779B97F4A7C15ULL, 13);
    u ^= rotl64(wv_nl, 7) ^ (wv_nl >> 17);
    v ^= rotl64(wv_nl, 19) ^ (wv_nl >> 23);
    w ^= rotl64(wv_nl, 31) ^ (wv_nl >> 29);
    z ^= rotl64(wv_nl, 43) ^ (wv_nl >> 37);
    u ^= rotl64(u, 22) ^ rotl64(u, 26) ^ (rotl64(u, 13) & rotl64(u, 41));
    v ^= rotl64(v, 22) ^ rotl64(v, 26) ^ (rotl64(v, 7) & rotl64(v, 19));
    w ^= rotl64(w, 22) ^ rotl64(w, 26) ^ (rotl64(w, 55) & rotl64(w, 11));
    z ^= rotl64(z, 22) ^ rotl64(z, 26) ^ (rotl64(z, 63) & rotl64(z, 7));
    u0 = u; v0 = v; w0 = w; z0 = z;
    u ^= rotl64(v0, 31) & rotl64(w0, 53);
    v ^= rotl64(w0, 17) & rotl64(z0, 43);
    w ^= rotl64(z0, 7) & rotl64(u0, 23);
    z ^= rotl64(u0, 5) & rotl64(v0, 19);
    u0 = u; v0 = v; w0 = w; z0 = z;
    u ^= rotl64(v0, 17) & rotl64(z0, 43);
    v ^= rotl64(w0, 7) & rotl64(u0, 23);
    w ^= rotl64(z0, 5) & rotl64(v0, 19);
    z ^= rotl64(u0, 31) & rotl64(w0, 53);
    u ^= rotl64(u, 46) ^ rotl64(u, 2);
    v ^= rotl64(v, 22) ^ rotl64(v, 26);
    w ^= rotl64(w, 23) ^ rotl64(w, 13);
    z ^= rotl64(z, 24) ^ rotl64(z, 27);
    u0 = u; v0 = v; w0 = w; z0 = z;
    u ^= rotl64(z0, 7) & rotl64(u0, 23);
    v ^= rotl64(u0, 55) & rotl64(v0, 19);
    w ^= rotl64(v0, 31) & rotl64(w0, 53);
    z ^= rotl64(w0, 17) & rotl64(z0, 43);
    u0 = u; v0 = v; w0 = w; z0 = z;
    u ^= rotl64(v0, 5) & rotl64(w0, 19);
    v ^= rotl64(w0, 31) & rotl64(z0, 53);
    w ^= rotl64(z0, 17) & rotl64(u0, 53);
    z ^= rotl64(u0, 7) & rotl64(v0, 23);
    u0 = u; v0 = v; w0 = w; z0 = z;
    u ^= rotl64(v0, 3) ^ rotl64(w0, 9);
    v ^= rotl64(w0, 5) ^ rotl64(z0, 11);
    w ^= rotl64(z0, 9) ^ rotl64(u0, 13);
    z ^= rotl64(u0, 11) ^ rotl64(v0, 17);
    s->u = u; s->v = v; s->w = w; s->z = z;
    s->weyl = wv; s->r++;
}

__attribute__((always_inline)) static inline uint64_t tempest_v4_output(uint64_t u, uint64_t v, uint64_t w, uint64_t z) {
    uint64_t t = u ^ rotl64(v, 32) ^ w ^ rotl64(z, 16);
    t ^= rotl64(t, 22) ^ rotl64(t, 26);
    t ^= rotl64(t, 16) ^ rotl64(t, 14);
    t ^= rotl64(t, 31) & rotl64(t, 53);
    t ^= rotl64(t, 17) & rotl64(t, 43);
    t ^= rotl64(t, 7) & rotl64(t, 23);
    t ^= rotl64(t, 5) & rotl64(t, 19);
    return t ^ (t >> 32);
}

static void tempest_v4_init(tempest_v4_state *s, const uint64_t key[4], const uint64_t nonce[2]) {
    uint64_t k0=key[0],k1=key[1],k2=key[2],k3=key[3];
    s->u=k0; s->v=k1^nonce[0]; s->w=k2^nonce[1];
    s->z=k3^0x54454D5035583543ULL; s->r=0; s->weyl=0x6A09E667F3BCC908ULL;
    uint64_t kw=0x6A09E667F3BCC908ULL;
    for(int i=0;i<16;i++){
        tempest_v4_round(s); kw ^= rotl64(kw, 19) ^ 0x9E3779B97F4A7C15ULL;
        if(i<8){
            if(i&1){
                s->u^=rotl64(k0,(unsigned)(i+1))^kw; s->v^=rotl64(k1,(unsigned)(i+1))^(kw<<17);
                s->w^=rotl64(k2,(unsigned)(i+1))^(kw>>13); s->z^=rotl64(k3,(unsigned)(i+1))^rotl64(kw,31);
            }else{
                s->u^=k0^kw; s->v^=k1^(kw<<17); s->w^=k2^(kw>>13); s->z^=k3^rotl64(kw,31);
            }
        }else{
            uint64_t n0=nonce[i&1],n1=nonce[1-(i&1)];
            s->u^=n0; s->v^=rotl64(n1,19)^(uint64_t)i; s->z^=rotl64(n0,43);
        }
    }
    for(int i=0;i<6;i++) tempest_v4_round(s);
    s->u^=k0;s->v^=k1;s->w^=k2;s->z^=k3;
}

__attribute__((always_inline)) static inline uint64_t tempest_v4_next(tempest_v4_state *s) {
    tempest_v4_round(s);
    return tempest_v4_output(s->u, s->v, s->w, s->z);
}

/* --- KAT --- */
static const uint64_t tempest_v4_kat[5] = {
0x14F5A292449ABBF8ULL, 0x04580C9D90D6FF4DULL, 0x1D07512E7F406B59ULL, 0x0EF62983F027F2FBULL, 0x52A4534064935CB8ULL
};

int main() {
    tempest_v4_state s;
    uint64_t key[4] = {1, 2, 3, 4}, nonce[2] = {5, 6};
    tempest_v4_init(&s, key, nonce);
    int ok = 1;
    for (int i = 0; i < 5; i++) {
        uint64_t got = tempest_v4_next(&s);
        if (got != tempest_v4_kat[i]) { printf("KAT %d FAIL: got %016llX want %016llX\n", i,
            (unsigned long long)got, (unsigned long long)tempest_v4_kat[i]); ok = 0; }
    }
    printf("KAT: %s\n", ok ? "PASS" : "FAIL");

        /* benchmark: 3 conditions, register accumulator, volatile write once */
    tempest_v4_init(&s, key, nonce);
    LARGE_INTEGER f, a, b;
    QueryPerformanceFrequency(&f);
    volatile uint64_t sink = 0;
    uint64_t acc = 0;
    const int N = 1 << 20;

    /* (1) raw round function, 128 bits of state per round */
    QueryPerformanceCounter(&a);
    for (int i = 0; i < N; i++) {
        tempest_v4_round(&s);
        acc ^= s.u ^ s.v ^ s.w ^ s.z;
    }
    QueryPerformanceCounter(&b);
    sink ^= acc;
    printf("round-only : %.2f Gbit/s (128 bits/round)\n",
        (double)(N * 128) / ((double)(b.QuadPart - a.QuadPart) / f.QuadPart) / 1e9);

    /* (2) true dual output: ONE round, TWO outputs (128 bits/round) */
    tempest_v4_init(&s, key, nonce);
    QueryPerformanceCounter(&a);
    for (int i = 0; i < N; i++) {
        tempest_v4_round(&s);
        acc ^= tempest_v4_output(s.u, s.v, s.w, s.z);
        acc ^= tempest_v4_output(s.v, s.w, s.z, s.u);
    }
    QueryPerformanceCounter(&b);
    sink ^= acc;
    printf("dual-output: %.2f Gbit/s (128 bits/round)\n",
        (double)(N * 128) / ((double)(b.QuadPart - a.QuadPart) / f.QuadPart) / 1e9);

    /* (3) single output, 64 bits/round */
    tempest_v4_init(&s, key, nonce);
    QueryPerformanceCounter(&a);
    for (int i = 0; i < N; i++) {
        tempest_v4_round(&s);
        acc ^= tempest_v4_output(s.u, s.v, s.w, s.z);
    }
    QueryPerformanceCounter(&b);
    sink ^= acc;
    printf("single-out : %.2f Gbit/s (64 bits/round)\n",
        (double)(N * 64) / ((double)(b.QuadPart - a.QuadPart) / f.QuadPart) / 1e9);
    printf("sink=%llu\n", (unsigned long long)sink);
    return ok ? 0 : 1;
}

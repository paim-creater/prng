/* walk_recheck.c — re-test swalk_RandomWalk1 (the second BigCrush
 * "*****", p=2.8e-4) on fresh seeds, to decide structure vs noise.
 * BigCrush's parameters: N=1, n=1e8, r=0, s=5, L0=50, L1=50.
 * Compile (WSL): gcc -O3 -I/usr/include/testu01 -o walk_recheck
 *               walk_recheck.c -ltestu01 -ltestu01mylib -lm
 */
#include "unif01.h"
#include "swalk.h"
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>

static uint64_t uu, vv, ww, zz;

static inline uint64_t rotl(uint64_t x, int r){ return (x << r) | (x >> (64 - r)); }

static inline uint64_t andmix4(uint64_t t){
    t ^= rotl(t, 31) & rotl(t, 53);
    t ^= rotl(t, 17) & rotl(t, 43);
    t ^= rotl(t,  7) & rotl(t, 23);
    t ^= rotl(t,  5) & rotl(t, 19);
    return t;
}

static void round_fixed(void){
    uint64_t u = uu, v = vv, w = ww, z = zz;
    uint64_t u0 = u, v0 = v, w0 = w, z0 = z;
    u = u0 ^ rotl(v0, 5) ^ rotl(w0, 13);
    v = v0 ^ rotl(w0, 11) ^ rotl(z0, 19);
    w = w0 ^ rotl(z0, 23) ^ rotl(u0, 9);
    z = z0 ^ rotl(u0, 17) ^ rotl(v0, 27);
    u ^= rotl(u, 22) ^ rotl(u, 26); u = andmix4(u);
    v ^= rotl(v, 22) ^ rotl(v, 26); v = andmix4(v);
    w ^= rotl(w, 22) ^ rotl(w, 26); w = andmix4(w);
    z ^= rotl(z, 22) ^ rotl(z, 26); z = andmix4(z);
    uu = u; vv = v; ww = w; zz = z;
}

static uint64_t next_u64(void){
    uint64_t t = uu ^ rotl(vv, 32) ^ ww ^ rotl(zz, 16);
    t ^= rotl(t, 27) ^ rotl(t, 17);
    t = andmix4(t);
    t ^= t >> 32;
    round_fixed();
    return t;
}

static double gU01(void *p, void *x){ (void)p; (void)x;
    return (double)(uint32_t)(next_u64() >> 32) * 2.3283064365386963E-10; }
static unsigned long gBits(void *p, void *x){ (void)p; (void)x;
    return (unsigned long)(uint32_t)(next_u64() >> 32); }
static void gW(void *j){ (void)j; printf(" v3.1 fixed\n"); }

int main(int ac, char **av){
    for (int trial = 0; trial < 3; trial++) {
        uint64_t seed = 0x9E3779B97F4A7C15ULL + (uint64_t)trial * 0x123456789ABCDEFULL;
        uu = seed; vv = seed ^ 0x6A09E667F3BCC908ULL;
        ww = seed ^ 0x3243F6A8885A308DULL; zz = seed ^ 0xB7E151628AED2A6BULL;
        for (int i = 0; i < 22; i++) round_fixed();
        unif01_Gen *g = malloc(sizeof(unif01_Gen));
        g->name = "v3.1 fixed"; g->GetU01 = &gU01; g->GetBits = &gBits;
        g->Write = &gW; g->param = NULL; g->state = NULL;
        swalk_Res *res = swalk_CreateRes();
        swalk_RandomWalk1(g, res, 1, 100000000L, 0, 5, 50, 50);
        for (int k = 0; k < res->imax; k++) {
            double pv = res->H[k]->pVal1->V[0];
            printf("trial %d H[%d]: p = %g%s\n", trial, k, pv,
                   pv < 0.001 ? "   *****" : "");
        }
        swalk_DeleteRes(res);
        free(g);
    }
    return 0;
}

/* testu01_v31_fixed.c — TestU01 harness for the v3.1 fixed generator.
 * The fixed v3.1 (Phase B: self + two rotations per word) fed to
 * TestU01 SmallCrush/Crush/BigCrush, mirroring testu01_v3.c.
 * Compile (WSL): gcc -O3 -o testu01_v31_fixed testu01_v31_fixed.c
 *               -ltestu01 -lmylib -lmyrand -lm
 */
#include "unif01.h"
#include "bbattery.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
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
    uint64_t seed = 0x9E3779B97F4A7C15ULL;
    uu = seed; vv = seed ^ 0x6A09E667F3BCC908ULL;
    ww = seed ^ 0x3243F6A8885A308DULL; zz = seed ^ 0xB7E151628AED2A6BULL;
    for (int i = 0; i < 22; i++) round_fixed();
    unif01_Gen *g = malloc(sizeof(unif01_Gen));
    g->name = "v3.1 fixed"; g->GetU01 = &gU01; g->GetBits = &gBits;
    g->Write = &gW; g->param = NULL; g->state = NULL;
    const char *b = ac > 1 ? av[1] : "small";
    if (!strcmp(b, "small"))      { printf("=== SmallCrush ===\n"); bbattery_SmallCrush(g); }
    else if (!strcmp(b, "crush")) { printf("=== Crush ===\n");     bbattery_Crush(g); }
    else if (!strcmp(b, "bigcrush")) { printf("=== BigCrush ===\n"); bbattery_BigCrush(g); }
    else { printf("Usage: %s [small|crush|bigcrush]\n", av[0]); }
    free(g);
    return 0;
}

/* bench_final.c — Inlined benchmark for cross-word AND + XOR-ROT Phase B */
#include <stdio.h>
#include <stdint.h>
#ifdef _WIN32
#include <windows.h>
static double now_ms(void) {
    LARGE_INTEGER f,c; QueryPerformanceFrequency(&f); QueryPerformanceCounter(&c);
    return (double)c.QuadPart*1000.0/(double)f.QuadPart;
}
#else
#include <sys/time.h>
static double now_ms(void) {
    struct timeval tv; gettimeofday(&tv,NULL);
    return tv.tv_sec*1000.0+tv.tv_usec/1000.0;
}
#endif

static inline uint64_t rotl(uint64_t x, int r) { return (x<<r)|(x>>(64-r)); }

static void round_func(uint64_t *up, uint64_t *vp, uint64_t *wp, uint64_t *zp, uint64_t *weyl) {
    uint64_t u=*up,v=*vp,w=*wp,z=*zp,u0=u,v0=v,w0=w,z0=z;
    uint64_t wv = *weyl + 0x9E3779B97F4A7C15ULL;
    u ^= rotl(wv,7)^(wv>>17); v ^= rotl(wv,19)^(wv>>23);
    w ^= rotl(wv,31)^(wv>>29); z ^= rotl(wv,43)^(wv>>37);
    *weyl = wv;
    u = u0 ^ rotl(v0,5)^rotl(w0,13)^rotl(z0,25);
    v = v0 ^ rotl(w0,11)^rotl(z0,19)^rotl(u0,29);
    w = w0 ^ rotl(z0,23)^rotl(u0,9)^rotl(v0,15);
    z = z0 ^ rotl(u0,17)^rotl(v0,27)^rotl(w0,21);
    u ^= rotl(u,22)^rotl(u,26); v ^= rotl(v,22)^rotl(v,26);
    w ^= rotl(w,22)^rotl(w,26); z ^= rotl(z,22)^rotl(z,26);
    uint64_t u1=u^(rotl(v,31)&rotl(w,53)),v1=v^(rotl(w,17)&rotl(z,43));
    uint64_t w1=w^(rotl(z, 7)&rotl(u,23)),z1=z^(rotl(u, 5)&rotl(v,19));
    uint64_t u2=u1^(rotl(v1,17)&rotl(z1,43)),v2=v1^(rotl(w1, 7)&rotl(u1,23));
    uint64_t w2=w1^(rotl(z1, 5)&rotl(v1,19)),z2=z1^(rotl(u1,31)&rotl(w1,53));
    uint64_t u3=u2^(rotl(z2, 7)&rotl(u2,23)),v3=v2^(rotl(u2, 5)&rotl(v2,19));
    uint64_t w3=w2^(rotl(v2,31)&rotl(w2,53)),z3=z2^(rotl(w2,17)&rotl(z2,43));
    uint64_t uc=u3^(rotl(v3, 5)&rotl(w3,19)),vc=v3^(rotl(w3,31)&rotl(z3,53));
    uint64_t wc=w3^(rotl(z3,17)&rotl(u3,53)),zc=z3^(rotl(u3, 7)&rotl(v3,23));
    *up = uc ^ rotl(vc,3)^rotl(wc,9);
    *vp = vc ^ rotl(wc,5)^rotl(zc,11);
    *wp = wc ^ rotl(zc,9)^rotl(uc,13);
    *zp = zc ^ rotl(uc,11)^rotl(vc,17);
}

static volatile uint64_t vsink = 0;

int main() {
    uint64_t u=1,v=2,w=3,z=4,weyl=0x6A09E667F3BCC908ULL;
    double t0,t1; int i;

    printf("=== Final: XOR-ROT + cross-word AND (inlined) ===\n\n");

    /* 128 bits/round × 50M */
    u=1;v=2;w=3;z=4;weyl=0x6A09E667F3BCC908ULL;
    t0 = now_ms();
    uint64_t d = 0;
    for (i=0; i<50000000; i++) {
        round_func(&u,&v,&w,&z,&weyl);
        d ^= u ^ v ^ w ^ z;
    }
    vsink = d;
    t1 = now_ms();
    double td = t1-t0, gd = (50000000.0*128)/(td*1e6);
    printf("Dual  (50M iters): %8.0f ms  %7.1f Gbit/s\n", td, gd);

    /* 64 bits/round × 100M */
    u=1;v=2;w=3;z=4;weyl=0x6A09E667F3BCC908ULL;
    t0 = now_ms();
    d = 0;
    for (i=0; i<100000000; i++) {
        round_func(&u,&v,&w,&z,&weyl);
        d ^= u ^ rotl(v,32) ^ w ^ rotl(z,16);
    }
    vsink = d;
    t1 = now_ms();
    double ts = t1-t0, gs = (100000000.0*64)/(ts*1e6);
    printf("Single (100M iters): %8.0f ms  %7.1f Gbit/s\n", ts, gs);

    printf("\nCross-word AND overhead vs original (16.4 dual): %.0f%%\n", (1-gd/16.4)*100);
    return 0;
}

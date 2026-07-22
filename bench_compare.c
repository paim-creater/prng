/* bench_compare.c — Pure Phase B throughput comparison: XOR-ROT vs MDS
   Compile: gcc -O3 -march=native -o bench_compare bench_compare.c -I.
   Run:    ./bench_compare.exe */
#include <stdio.h>
#include <stdint.h>
#ifdef _WIN32
#include <windows.h>
static double now_ms(void) {
    LARGE_INTEGER f, c;
    QueryPerformanceFrequency(&f); QueryPerformanceCounter(&c);
    return (double)c.QuadPart * 1000.0 / (double)f.QuadPart;
}
#else
#include <sys/time.h>
static double now_ms(void) {
    struct timeval tv; gettimeofday(&tv, NULL);
    return tv.tv_sec * 1000.0 + tv.tv_usec / 1000.0;
}
#endif

static inline uint64_t rotl(uint64_t x, int r) {
    return (x << r) | (x >> (64 - r));
}
static inline uint64_t xtime64(uint64_t x) {
    return (x << 1) ^ (0x1BULL & -((int64_t)(x >> 63)));
}

int main() {
    uint64_t u, v, w, z, u0, v0, w0, z0, s;
    double t0, t1;
    int i, j;
    const int N = 200000000;

    printf("=== Phase B: XOR-ROT vs MDS ===\n\n");

    /*  XOR-ROT Phase B  */
    u0 = 0x123456789ABCDEF0ULL; v0 = 0x23456789ABCDEF01ULL;
    w0 = 0x3456789ABCDEF012ULL; z0 = 0x456789ABCDEF0123ULL;
    s = 0;
    t0 = now_ms();
    for (i = 0; i < N; i++) {
        u = u0 ^ rotl(v0,5) ^ rotl(w0,13) ^ rotl(z0,25);
        v = v0 ^ rotl(w0,11) ^ rotl(z0,19) ^ rotl(u0,29);
        w = w0 ^ rotl(z0,23) ^ rotl(u0,9) ^ rotl(v0,15);
        z = z0 ^ rotl(u0,17) ^ rotl(v0,27) ^ rotl(w0,21);
        s ^= u ^ v ^ w ^ z;
        /* rotate inputs to prevent compiler folding */
        u0 += s; v0 ^= s; w0 += v0; z0 ^= w0;
    }
    t1 = now_ms();
    printf("XOR-ROT: %8.0f ms  (sum=%016llX)\n", t1-t0, (unsigned long long)s);

    /*  MDS Phase B  */
    u0 = 0x123456789ABCDEF0ULL; v0 = 0x23456789ABCDEF01ULL;
    w0 = 0x3456789ABCDEF012ULL; z0 = 0x456789ABCDEF0123ULL;
    s = 0;
    t0 = now_ms();
    for (i = 0; i < N; i++) {
        uint64_t u2 = xtime64(u0), v2 = xtime64(v0), w2 = xtime64(w0), z2 = xtime64(z0);
        u = u2 ^ v0 ^ w0 ^ z0;
        v = u0 ^ v2 ^ w0 ^ z0;
        w = u0 ^ v0 ^ w2 ^ z0;
        z = u0 ^ v0 ^ w0 ^ z2;
        s ^= u ^ v ^ w ^ z;
        u0 += s; v0 ^= s; w0 += v0; z0 ^= w0;
    }
    t1 = now_ms();
    printf("MDS:      %8.0f ms  (sum=%016llX)\n", t1-t0, (unsigned long long)s);

    return 0;
}

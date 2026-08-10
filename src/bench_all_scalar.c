/* bench_all_scalar.c — unified fair comparison: scalar ChaCha20,
 * scalar xoshiro256**, OpenSSL AES-CTR, with the same harness
 * (RDTSC frequency calibration in the same run, long loops, register
 * accumulator).  Tempest scalar/AVX-512 and ChaCha20-EVP measured
 * separately (same harness).
 * Compile: gcc -O3 -o bench_all_scalar bench_all_scalar.c -lcrypto
 */
#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include <stdlib.h>
#include <windows.h>
#include <openssl/evp.h>

static inline uint64_t rdtsc(void) {
    unsigned lo, hi;
    __asm__ volatile ("rdtsc" : "=a"(lo), "=d"(hi));
    return ((uint64_t)hi << 32) | lo;
}
static double now_ms(void) {
    LARGE_INTEGER f, c;
    QueryPerformanceFrequency(&f); QueryPerformanceCounter(&c);
    return (double)c.QuadPart * 1000.0 / (double)f.QuadPart;
}
static inline uint32_t rotl32(uint32_t x, int n) { return (x << n) | (x >> (32 - n)); }

/* ---------- scalar ChaCha20 (standard 20-round, 8x32-bit words) ---------- */
#define QR(a,b,c,d) do { a+=b; d^=a; d=rotl32(d,16); c+=d; b^=c; \
    b=rotl32(b,12); a+=b; d^=a; d=rotl32(d,8); c+=d; b^=c; b=rotl32(b,7); } while(0)
static void chacha20_block(uint32_t out[16], const uint32_t in[16]) {
    uint32_t x[16]; memcpy(x, in, 64);
    for (int i = 0; i < 10; i++) {
        QR(x[0],x[4],x[8],x[12]); QR(x[1],x[5],x[9],x[13]);
        QR(x[2],x[6],x[10],x[14]); QR(x[3],x[7],x[11],x[15]);
        QR(x[0],x[5],x[10],x[15]); QR(x[1],x[6],x[11],x[12]);
        QR(x[2],x[7],x[8],x[13]);  QR(x[3],x[4],x[9],x[14]);
    }
    for (int i = 0; i < 16; i++) out[i] = x[i] + in[i];
}
static double bench_chacha_scalar(void) {
    uint32_t state[16] = {0x61707865,0x3320646e,0x79622d32,0x6b206574,
                          1,2,3,4, 5,6,7,8, 9,10,11,12};
    uint32_t out[16]; volatile uint64_t sink = 0; uint64_t acc = 0;
    const long long N = 50000000LL;
    for (int i = 0; i < 1000000; i++) { chacha20_block(out, state); acc ^= out[0]; }
    double t0 = now_ms();
    for (long long i = 0; i < N; i++) {
        chacha20_block(out, state);
        state[12]++; if (!state[12]) state[13]++;
        acc ^= out[0] ^ out[1];
    }
    double t1 = now_ms();
    sink ^= acc;
    return (double)N * 512.0 / ((t1 - t0) / 1000.0) / 1e9; /* 512 bits/block */
}

/* ---------- scalar xoshiro256** ---------- */
static uint64_t xs_state[4];
static inline uint64_t rotl64(uint64_t x, int k) { return (x << k) | (x >> (64 - k)); }
static uint64_t xoshiro_next(void) {
    uint64_t result = rotl64(xs_state[1] * 5, 7) * 9;
    uint64_t t = xs_state[1] << 17;
    xs_state[2] ^= xs_state[0]; xs_state[3] ^= xs_state[1];
    xs_state[1] ^= xs_state[2]; xs_state[0] ^= xs_state[3];
    xs_state[2] ^= t;
    xs_state[3] = rotl64(xs_state[3], 45);
    return result;
}
static double bench_xoshiro(void) {
    xs_state[0]=1; xs_state[1]=2; xs_state[2]=3; xs_state[3]=4;
    volatile uint64_t sink = 0; uint64_t acc = 0;
    const long long N = 1000000000LL;
    for (int i = 0; i < 1000000; i++) acc ^= xoshiro_next();
    double t0 = now_ms();
    for (long long i = 0; i < N; i++) acc ^= xoshiro_next();
    double t1 = now_ms();
    sink ^= acc;
    return (double)N * 64.0 / ((t1 - t0) / 1000.0) / 1e9;
}

/* ---------- OpenSSL AES-128-CTR ---------- */
static double bench_aes_ctr(void) {
    EVP_CIPHER_CTX *ctx = EVP_CIPHER_CTX_new();
    unsigned char key[16] = {0}, iv[16] = {0};
    const size_t BLK = 1 << 16;   /* 64 KiB, cache-resident-ish */
    unsigned char *in = malloc(BLK), *out = malloc(BLK);
    memset(in, 0x5a, BLK);
    EVP_EncryptInit_ex(ctx, EVP_aes_128_ctr(), NULL, key, iv);
    long long N = 1 << 12;  /* 256 MiB */
    double t0 = now_ms();
    for (long long i = 0; i < N; i++) {
        int len = 0, flen = 0;
        EVP_EncryptUpdate(ctx, out, &len, in, (int)BLK);
        EVP_EncryptFinal_ex(ctx, out + len, &flen);
    }
    double t1 = now_ms();
    double gbps = (double)N * (double)BLK * 8.0 / ((t1 - t0) / 1000.0) / 1e9;
    EVP_CIPHER_CTX_free(ctx); free(in); free(out);
    return gbps;
}

int main(void) {
    uint64_t tsc0 = rdtsc();
    double t0 = now_ms();
    double ch = bench_chacha_scalar();
    double xs = bench_xoshiro();
    double aes = bench_aes_ctr();
    double t1 = now_ms();
    uint64_t tsc1 = rdtsc();
    double freq = (double)(tsc1 - tsc0) / ((t1 - t0) / 1000.0) / 1e9;
    double scale = 5.0 / freq;
    printf("freq=%.3f GHz\n", freq);
    printf("ChaCha20 scalar  : %7.2f Gbit/s  (->5GHz: %7.1f)\n", ch, ch*scale);
    printf("xoshiro256**     : %7.2f Gbit/s  (->5GHz: %7.1f)\n", xs, xs*scale);
    printf("AES-128-CTR EVP  : %7.2f Gbit/s  (->5GHz: %7.1f)\n", aes, aes*scale);
    return 0;
}

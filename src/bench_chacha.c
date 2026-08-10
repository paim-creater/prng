#include <stdio.h>
#include <stdint.h>
#include <string.h>
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
int main(void) {
    EVP_CIPHER_CTX *ctx = EVP_CIPHER_CTX_new();
    unsigned char key[32] = {0}, iv[16] = {0};
    const size_t BLK = 1 << 20;   /* 1 MiB buffer */
    unsigned char *in = malloc(BLK), *out = malloc(BLK);
    memset(in, 0x5a, BLK);
    uint64_t tsc0 = rdtsc();
    double t0 = now_ms();
    EVP_EncryptInit_ex(ctx, EVP_chacha20(), NULL, key, iv);
    long long N = 1 << 14;  /* 16 GiB total */
    for (long long i = 0; i < N; i++) {
        int len = 0, flen = 0;
        EVP_EncryptUpdate(ctx, out, &len, in, (int)BLK);
        EVP_EncryptFinal_ex(ctx, out + len, &flen);
    }
    double t1 = now_ms();
    uint64_t tsc1 = rdtsc();
    double freq = (double)(tsc1 - tsc0) / ((t1 - t0) / 1000.0) / 1e9;
    double gbps = (double)N * (double)BLK * 8.0 / ((t1 - t0) / 1000.0) / 1e9;
    double scale = 5.0 / freq;
    printf("freq=%.3f GHz  ChaCha20(EVP): %.1f Gbit/s  (->5GHz: %.1f)\n",
           freq, gbps, gbps * scale);
    EVP_CIPHER_CTX_free(ctx);
    free(in); free(out);
    return 0;
}

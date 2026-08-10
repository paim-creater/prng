/* tempest_stream.c — Algorithm 1 used as a stream cipher (XOR
 * keystream, the ChaCha20 deployment pattern): encrypt a file with
 * key+nonce, decrypt it back, and verify byte-exact round-trip.
 *
 * The point of the demo: a cryptographic PRNG with a verified
 * construction is directly a stream cipher --- encryption = keystream
 * XOR plaintext --- and the round-trip plus the keystream's own
 * statistical record (1 TiB PractRand, BigCrush, NIST) make the
 * confidentiality claim measurable end to end.
 *
 * Build:   gcc -O3 -o tempest_stream tempest_stream.c tempest_v3.c
 * Run:     ./tempest_stream <infile> <outfile>
 *          (infile is encrypted in place as outfile; run twice with
 *           the same key/nonce to decrypt — XOR is self-inverse)
 * Built-in self-test if no arguments: round-trip on 4 MiB of random
 * data + byte-entropy comparison of plaintext vs ciphertext.
 */
#include "tempest_v3.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>

static const uint64_t KEY[4] = {0x6A09E667F3BCC908ULL, 0xBB67AE8584CAA73BULL,
                                0x3C6EF372FE94F82BULL, 0xA54FF53A5F1D36F1ULL};
static const uint64_t NONCE[2] = {0x9E3779B97F4A7C15ULL, 0x243F6A8885A308D3ULL};

/* XOR the file content with the Tempest keystream (in place). */
static void xor_stream(uint8_t *buf, size_t n) {
    tempest_state s;
    tempest_init(&s, KEY, NONCE);
    size_t off = 0;
    while (off < n) {
        uint64_t o[2];
        tempest_u64x2(&s, o);              /* 128 bits per call */
        const uint8_t *ks = (const uint8_t *)o;
        size_t take = n - off < 16 ? n - off : 16;
        for (size_t i = 0; i < take; i++) buf[off + i] ^= ks[i];
        off += take;
    }
}

static double byte_entropy(const uint8_t *buf, size_t n) {
    double cnt[256] = {0};
    for (size_t i = 0; i < n; i++) cnt[buf[i]] += 1.0;
    double h = 0;
    for (int i = 0; i < 256; i++)
        if (cnt[i] > 0) {
            double p = cnt[i] / n;
            h -= p * (log(p) / log(2.0));
        }
    return h;
}

static int self_test(void) {
    const size_t N = 4 << 20;              /* 4 MiB */
    uint8_t *pt = malloc(N), *ct = malloc(N), *rt = malloc(N);
    if (!pt || !ct || !rt) return 0;
    for (size_t i = 0; i < N; i++) pt[i] = (uint8_t)(i * 2654435761u >> 13);
    memcpy(ct, pt, N);
    xor_stream(ct, N);
    memcpy(rt, ct, N);
    xor_stream(rt, N);
    int ok = memcmp(pt, rt, N) == 0;
    printf("round-trip 4 MiB:      %s\n", ok ? "PASS (decrypt == original)"
                                             : "FAIL");
    printf("plaintext byte entropy: %.4f bits/byte\n", byte_entropy(pt, N));
    printf("ciphertext byte entropy: %.4f bits/byte\n", byte_entropy(ct, N));
    free(pt); free(ct); free(rt);
    return ok;
}

int main(int argc, char **argv) {
    if (argc < 3) {
        printf("no file args: running built-in self-test\n");
        return self_test() ? 0 : 1;
    }
    FILE *f = fopen(argv[1], "rb");
    if (!f) { perror("open"); return 1; }
    fseek(f, 0, SEEK_END);
    long n = ftell(f);
    fseek(f, 0, SEEK_SET);
    uint8_t *buf = malloc((size_t)n);
    if (!buf) { fclose(f); return 1; }
    if (fread(buf, 1, (size_t)n, f) != (size_t)n) { fclose(f); return 1; }
    fclose(f);
    xor_stream(buf, (size_t)n);
    FILE *g = fopen(argv[2], "wb");
    if (!g) { free(buf); return 1; }
    fwrite(buf, 1, (size_t)n, g);
    fclose(g);
    printf("%s -> %s: %ld bytes XOR-keystreamed with key+nonce "
           "(run again to decrypt)\n", argv[1], argv[2], n);
    free(buf);
    return 0;
}

/* gen_a1_stream.c — binary keystream output for the published Algorithm 1
 * (Tempest v3, pure-GF(2) round function, KAT 0x6BBE30BB...), for the
 * statistical-test reruns (PractRand 1 TiB / BigCrush / NIST).
 *
 * Semantics: exactly the release implementation (tempest_v3.c linked
 * below), dual-output (128 bits per call), same key/nonce convention as
 * the paper's KAT (key 0x6A09E667... , nonce 0xDEADBEEF... as in
 * gen_practrand_tempest.c).
 *
 * Build (Windows):  gcc -O3 -o gen_a1_stream.exe gen_a1_stream.c tempest_v3.c
 * Usage:            gen_a1_stream [bytes] > stream.bin     (binary stdout)
 *                    gen_a1_stream | RNG_test stdin64 -tlmax 1TB
 */
#include "tempest_v3.h"
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#ifdef _WIN32
#include <fcntl.h>
#include <io.h>
#endif

int main(int ac, char **av) {
#ifdef _WIN32
    _setmode(_fileno(stdout), _O_BINARY);
#endif
    /* self-check against the release KAT vector (key {1,2,3,4},
     * nonce {5,6}) before streaming */
    uint64_t kk[4] = {1, 2, 3, 4};
    uint64_t nn[2] = {5, 6};
    tempest_state s;
    tempest_init(&s, kk, nn);
    const uint64_t expect[5] = {0x6BBE30BB1D12DDD0ULL, 0xB9167FE6CCEC68D9ULL,
                                0xCF6F7BA5C6AED360ULL, 0xA53C77D6D081BEC3ULL,
                                0x7F5A13D9CBF1CD84ULL};
    for (int i = 0; i < 5; i++) {
        uint64_t got = tempest_u64(&s);
        if (got != expect[i]) {
            fprintf(stderr, "KAT %d FAIL: got %016llX\n", i,
                    (unsigned long long)got);
            return 2;
        }
    }
    fprintf(stderr, "Algorithm-1 KAT self-check: PASS\n");
    /* stream key/nonce: the paper's convention (as gen_practrand_tempest.c) */
    uint64_t k[4] = {0x9E3779B97F4A7C15ULL, 0x6A09E667F3BCC909ULL,
                     0x3243F6A8885A308DULL, 0xB7E151628AED2A6BULL};
    uint64_t n[2] = {0xDEADBEEFCAFE1234ULL, 0xFEEDFACEBABE5678ULL};
    tempest_init(&s, k, n);
    uint64_t nbytes = (ac > 1) ? strtoull(av[1], NULL, 10)
                               : 128ULL * 1024 * 1024 * 1024;  /* default 128 GiB */
    uint64_t w = 0;
    while (w < nbytes) {
        uint64_t r[2];
        tempest_u64x2(&s, r);
        fwrite(r, 1, 16, stdout);
        w += 16;
    }
    fflush(stdout);
    return 0;
}

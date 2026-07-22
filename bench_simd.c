/* bench_simd.c — Tempest v3 AVX-512 SIMD vs Scalar 基准测试
 * gcc -O3 -march=native -mavx512f -o bench_simd bench_simd.c src/tempest_simd.c -lm
 */
#include "src/tempest_simd.h"
#include <stdio.h>

int main() {
    printf("Tempest v3 — AVX-512 SIMD 8-way Parallel Benchmark\n");
    printf("============================================\n\n");

    /* 验证输出正确性 */
    printf("验证 SIMD 8 路输出...\n");
    TempestSIMD8 simd;
    tempest_simd_seed(&simd, 42);
    uint64_t out[16];

    tempest_simd_next_u64x2(&simd, out);

    int all_nonzero = 1;
    for (int i = 0; i < 16; i++) if (out[i] == 0) all_nonzero = 0;

    int all_distinct = 1;
    for (int i = 0; i < 16; i++)
        for (int j = i+1; j < 16; j++)
            if (out[i] == out[j]) all_distinct = 0;

    if (all_nonzero) printf("  ✅ 所有 16 个输出非零\n");
    else printf("  ❌ 存在零输出!\n");
    if (all_distinct) printf("  ✅ 所有 16 个输出互不相同 (8 路独立流)\n");
    else printf("  ❌ 存在重复输出!\n");

    /* 打印前 8 个输出 (每流 1 个) */
    printf("\n8 路首次输出:\n");
    for (int i = 0; i < 8; i++)
        printf("  stream[%d] = 0x%016llx\n", i, (unsigned long long)out[i]);

    /* 基准测试 */
    printf("\n");
    tempest_bench_compare();

    return (all_nonzero && all_distinct) ? 0 : 1;
}

/* tempest_simd.h — AVX-512 8-way parallel Tempest v3
 * ======================================================================
 * 使用 AVX-512 SIMD 同时运行 8 个独立的 Tempest v3 实例，
 * 预计吞吐量: 25-30 Gbit/s (+50% vs 标量 17.7 Gbit/s)
 *
 * 原理：
 *   每个 AVX-512 512-bit 寄存器容纳 8× uint64。
 *   SoA (Structure of Arrays) 布局:
 *     u_reg = {u0, u1, u2, u3, u4, u5, u6, u7}
 *     v_reg = {v0, v1, v2, v3, v4, v5, v6, v7} 等
 *   所有 ADD / XOR / ROT 操作单指令完成 8 路。
 *
 * 编译: gcc -O3 -march=native -mavx512f -o bench_simd bench_simd.c tempest_simd.c -I.
 * ====================================================================== */
#ifndef TEMPEST_SIMD_H
#define TEMPEST_SIMD_H

#include <stdint.h>
#include <stddef.h>
#include <immintrin.h>

#ifdef __cplusplus
extern "C" {
#endif

/* ═══════════════════════════════════════════════════════════════════════
 * 8 路 SIMD 状态
 * 每个 __m512i 包含 8 个 uint64 (8 个独立流)
 * ═══════════════════════════════════════════════════════════════════════ */
typedef struct {
    __m512i u;         /* u0..u7 — 8 路状态字 A */
    __m512i v;         /* v0..v7 — 8 路状态字 B */
    __m512i w;         /* w0..w7 — 8 路状态字 C */
    __m512i z;         /* z0..z7 — 8 路状态字 D */
    __m512i rounds;    /* 轮数计数器 (8× uint64) */
    __m512i weyl;      /* Weyl 序列值 (8× uint64) */
} TempestSIMD8;

/* ── 8 路并行初始化 ── */

/* 从 8 组 key/nonce 初始化 */
void tempest_simd_init(TempestSIMD8 *s,
    const uint64_t keys[8][4], const uint64_t nonces[8][2]);

/* 从 1 个种子派生 8 路 (每个流用不同种子) */
void tempest_simd_seed(TempestSIMD8 *s, uint64_t base_seed);

/* ── 8 路并行生成 ── */

/* 生成 8 个 uint64 (每流 1 个) */
void tempest_simd_next_u64(TempestSIMD8 *s, uint64_t out[8]);

/* 生成 8×2 = 16 个 uint64 (每流 2 个, 双输出) */
void tempest_simd_next_u64x2(TempestSIMD8 *s, uint64_t out[16]);

/* 填充 8 路输出到缓冲区 (每路连续 n 字节) */
void tempest_simd_fill(TempestSIMD8 *s, uint8_t *buffers[8], size_t nbytes);

/* ── 单路提取 (将 8 路 SIMD 中的第 i 路输出) ── */
uint64_t tempest_simd_extract_u64(TempestSIMD8 *s, int lane);

/* ── 标量基准函数 (对比用, 与 tempest_v3.c 相同) ── */
uint64_t tempest_scalar_next(uint64_t state[4]);

void tempest_scalar_init(uint64_t state[4], const uint64_t key[4], const uint64_t nonce[2]);

/* ── 基准 —— 返回 Gbit/s ── */
double tempest_bench_simd(int64_t rounds);
double tempest_bench_scalar(int64_t rounds);
double tempest_bench_compare(void);

#ifdef __cplusplus
}
#endif

#endif /* TEMPEST_SIMD_H */

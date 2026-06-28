/* _tempest_numpy.c — Tempest v3 NumPy 加速扩展
 * ======================================================================
 * 提供两种批量填充函数, 供 Python 的 tempest_rng.py 通过 ctypes 调用。
 * 不需要 NumPy 头文件——操作裸内存, Python 端管理 numpy array。
 *
 * 函数:
 *   fill_u64(state_ptr, out, n)   — 批量生成 uint64
 *   fill_double(state_ptr, out, n) — 批量生成 float64 [0,1)
 *   fill_normal(state_ptr, out, n) — 批量生成 Box-Muller normal
 *
 * 编译:
 *   gcc -O3 -march=native -fPIC -shared -o _tempest_numpy.so _tempest_numpy.c tempest_v3.c -I.
 *   (Windows: gcc -O3 -march=native -shared -o _tempest_numpy.dll _tempest_numpy.c tempest_v3.c -I.)
 * ====================================================================== */
#include <stdint.h>
#include <string.h>
#include <math.h>
#include "tempest_v3.h"

/* ── 批量生成 uint64 ── */
void tempest_fill_u64(tx4_state *state, uint64_t *out, int n) {
    int i = 0;
    while (i + 1 < n) {
        uint64_t pair[2];
        tx5cmul_next2(state, pair);
        out[i++] = pair[0];
        out[i++] = pair[1];
    }
    if (i < n) {
        out[i] = tx5cmul_next(state);
    }
}

/* ── 批量生成 float64 [0, 1) ── */
void tempest_fill_double(tx4_state *state, double *out, int n) {
    /* 用 uint64 高 53 bit 生成 float64: IEEE 754 double 精度 53 bit */
    static const double SCALE = 1.0 / (1ULL << 53);
    int i = 0;
    while (i + 1 < n) {
        uint64_t pair[2];
        tx5cmul_next2(state, pair);
        out[i++] = (pair[0] >> 11) * SCALE;
        out[i++] = (pair[1] >> 11) * SCALE;
    }
    if (i < n) {
        uint64_t r = tx5cmul_next(state);
        out[i] = (r >> 11) * SCALE;
    }
}

/* ── 批量生成 float32 [0, 1) ── */
void tempest_fill_float(tx4_state *state, float *out, int n) {
    static const float SCALE = 1.0f / (1U << 24);
    int i = 0;
    while (i + 1 < n) {
        uint64_t pair[2];
        tx5cmul_next2(state, pair);
        out[i++] = (float)(pair[0] >> 40) * SCALE;
        out[i++] = (float)(pair[1] >> 40) * SCALE;
    }
    if (i < n) {
        uint64_t r = tx5cmul_next(state);
        out[i] = (float)(r >> 40) * SCALE;
    }
}

/* ── 批量生成正态分布 (Box-Muller, 两个输出一对) ── */
void tempest_fill_normal(tx4_state *state, double *out, int n) {
    static const double TWO_PI = 6.283185307179586476925286766559;
    static const double SCALE = 1.0 / (1ULL << 53);
    int i = 0;

    while (i + 1 < n) {
        /* 生成两个独立均匀值 */
        uint64_t pair[2];
        tx5cmul_next2(state, pair);
        double u1 = (pair[0] >> 11) * SCALE;
        double u2 = (pair[1] >> 11) * SCALE;

        /* Box-Muller 变换 */
        double r = sqrt(-2.0 * log(u1 + 1e-308));
        double theta = TWO_PI * u2;

        out[i++] = r * cos(theta);
        if (i < n) {
            out[i++] = r * sin(theta);
        }
    }
}

/* ── 重置状态 (用于 reseed / reinitialize) ── */
void tempest_reset_state(tx4_state *state, const uint64_t key[4], const uint64_t nonce[2]) {
    tx5cmul_init(state, key, nonce);
}

/* tempest_simd.c — AVX-512 8-way parallel Tempest v3 implementation
 * ======================================================================
 * 8 路 SIMD Tempest v3: 同时运行 8 个独立流，共享指令分派。
 * 理论上限 ~28 Gbit/s (芝 4 AVX-512 @ 5GHz)
 *
 * 编译: gcc -O3 -march=native -mavx512f -o bench_simd bench_simd.c tempest_simd.c -lm
 * ====================================================================== */
#include "tempest_simd.h"
#include <string.h>
#include <stdio.h>
#include <windows.h>

/* ═══════════════════════════════════════════════════════════════════════
 * AVX-512 辅助函数
 * ═══════════════════════════════════════════════════════════════════════ */

/* 8 路并行 rotl: return (x << r) | (x >> (64 - r)) */
static inline __m512i simd_rotl(__m512i x, int r) {
    return _mm512_or_si512(
        _mm512_slli_epi64(x, r),
        _mm512_srli_epi64(x, 64 - r)
    );
}

/* 8 路并行 cmul_hl: (x >> 32) * (uint32_t)y
   vpmuludq 取 op1[63:32] × op2[31:0] = x_hi × y_lo = cmul_hl(x,y) */
static inline __m512i simd_cmul_hl(__m512i x, __m512i y) {
    return _mm512_mul_epu32(x, y);
}

/* 8 路并行 cmul_lh: (uint32_t)x * (y >> 32)
   需要 x_lo × y_hi。
   vpmuludq(op1, op2) = op1_hi × op2_lo
   先将 x 左移 32 (x_lo 到高位), y 右移 32 (y_hi 到低位) */
static inline __m512i simd_cmul_lh(__m512i x, __m512i y) {
    __m512i x_shifted = _mm512_slli_epi64(x, 32);   /* x_lo 移到高位 */
    __m512i y_shifted = _mm512_srli_epi64(y, 32);   /* y_hi 移到低位 */
    return _mm512_mul_epu32(x_shifted, y_shifted);
}

/* Weyl 常数 */
#define SIMD_WEYL_GOLDEN _mm512_set1_epi64(0x9E3779B97F4A7C15ULL)
#define SIMD_WEYL_INIT   _mm512_set1_epi64(0x6A09E667F3BCC908ULL)
#define SIMD_DOMAIN_SEP  _mm512_set1_epi64(0x54454D5035583543ULL)

/* ═══════════════════════════════════════════════════════════════════════
 * 8 路并行单轮 Tempest v3
 * 所有操作在 8 个独立流上同时执行
 * ═══════════════════════════════════════════════════════════════════════ */
static void simd_round(TempestSIMD8 *s) {
    __m512i u = s->u, v = s->v, w = s->w, z = s->z;
    __m512i rnd = s->rounds;

    /* sh = rounds & 3 (每流独立) */
    __m512i sh = _mm512_and_si512(rnd, _mm512_set1_epi64(3));

    /* [Mod 3] Weyl 逐轮去相关 */
    __m512i wval = _mm512_add_epi64(s->weyl, SIMD_WEYL_GOLDEN);
    u = _mm512_xor_si512(u, _mm512_xor_si512(simd_rotl(wval, 7),  _mm512_srli_epi64(wval, 17)));
    v = _mm512_xor_si512(v, _mm512_xor_si512(simd_rotl(wval, 19), _mm512_srli_epi64(wval, 23)));
    w = _mm512_xor_si512(w, _mm512_xor_si512(simd_rotl(wval, 31), _mm512_srli_epi64(wval, 29)));
    z = _mm512_xor_si512(z, _mm512_xor_si512(simd_rotl(wval, 43), _mm512_srli_epi64(wval, 37)));
    s->weyl = wval;

    /* [Mod 1] ADD 预扩散 + z→u 反馈 (a₁ ≥ 4) */
    __m512i u0 = u;
    u = _mm512_add_epi64(u, _mm512_xor_si512(simd_rotl(v, 7), simd_rotl(z, 13)));
    v = _mm512_add_epi64(v, simd_rotl(w, 11));
    w = _mm512_add_epi64(w, simd_rotl(z, 13));
    z = _mm512_add_epi64(z, simd_rotl(u0, 17));

    /* 4-cmul Fibonacci-weave */
    u = _mm512_add_epi64(u, simd_cmul_hl(v, w));  /* cmul₁, deg=4 */
    v = _mm512_add_epi64(v, simd_cmul_hl(w, z));  /* cmul₂, deg=4 (并行) */
    w = _mm512_add_epi64(w, simd_cmul_lh(u, v));  /* cmul₃, deg=8 */
    u = _mm512_add_epi64(u, simd_cmul_hl(w, z));  /* cmul₄, deg=12 */

    /* Post-ARX */
    u = _mm512_xor_si512(u, _mm512_add_epi64(simd_rotl(v, 19), w));
    v = _mm512_xor_si512(v, _mm512_add_epi64(simd_rotl(w, 23), z));
    w = _mm512_xor_si512(w, _mm512_add_epi64(simd_rotl(z, 7),  u));
    z = _mm512_xor_si512(z, _mm512_add_epi64(simd_rotl(u, 11), v));

    /* Alternating Boomerang (every 2 rounds) — all lanes have same rounds */
    __m512i rnd_parity = _mm512_and_si512(rnd, _mm512_set1_epi64(1));
    __mmask8 even_mask = _mm512_cmpeq_epi64_mask(rnd_parity, _mm512_setzero_si512());

    /* 所有流共享同一 sh，提取 lane 0 计算旋转常数 */
    alignas(64) uint64_t rnd_buf[8];
    _mm512_store_epi64(rnd_buf, rnd);
    int sh_val = (int)(rnd_buf[0] & 3);

    __m512i r1 = simd_rotl(v, 19 - sh_val * 2);
    __m512i r2 = simd_rotl(u, 23 - sh_val * 2);
    __m512i r3 = simd_rotl(z, 7  + sh_val * 2);
    __m512i r4 = simd_rotl(w, 11 + sh_val * 2);

    __m512i bz = _mm512_xor_si512(z, _mm512_add_epi64(r1, u));
    __m512i bw = _mm512_xor_si512(w, _mm512_add_epi64(r2, z));
    __m512i bv = _mm512_xor_si512(v, _mm512_add_epi64(r3, w));
    __m512i bu = _mm512_xor_si512(u, _mm512_add_epi64(r4, v));

    z = _mm512_mask_mov_epi64(z, even_mask, bz);
    w = _mm512_mask_mov_epi64(w, even_mask, bw);
    v = _mm512_mask_mov_epi64(v, even_mask, bv);
    u = _mm512_mask_mov_epi64(u, even_mask, bu);

    s->u = u; s->v = v; s->w = w; s->z = z;
    s->rounds = _mm512_add_epi64(rnd, _mm512_set1_epi64(1));
}

/* ═══════════════════════════════════════════════════════════════════════
 * 8 路并行输出函数: 4 级 AND-mix 级联
 * ═══════════════════════════════════════════════════════════════════════ */
static __m512i simd_make_output(__m512i u, __m512i v, __m512i w, __m512i z) {
    __m512i t = _mm512_xor_si512(u, _mm512_xor_si512(
        simd_rotl(v, 32), _mm512_xor_si512(w, simd_rotl(z, 16))));
    t = _mm512_xor_si512(t, simd_rotl(t, 27));
    t = _mm512_xor_si512(t, _mm512_and_si512(simd_rotl(t, 31), simd_rotl(t, 53)));
    t = _mm512_xor_si512(t, _mm512_and_si512(simd_rotl(t, 17), simd_rotl(t, 43)));
    t = _mm512_xor_si512(t, _mm512_and_si512(simd_rotl(t,  7), simd_rotl(t, 23)));
    t = _mm512_xor_si512(t, _mm512_and_si512(simd_rotl(t,  5), simd_rotl(t, 19)));
    t = _mm512_xor_si512(t, _mm512_srli_epi64(t, 32));
    return t;
}

/* ═══════════════════════════════════════════════════════════════════════
 * 8 路双输出: 每轮 8×2 = 16 个 uint64
 * ═══════════════════════════════════════════════════════════════════════ */
static void simd_next2(TempestSIMD8 *s, __m512i *out0, __m512i *out1) {
    simd_round(s);
    *out0 = simd_make_output(s->u, s->v, s->w, s->z);
    *out1 = simd_make_output(s->v, s->w, s->z, s->u);
}

/* ═══════════════════════════════════════════════════════════════════════
 * 密钥编排 (8 路并行, 22 轮)
 * ═══════════════════════════════════════════════════════════════════════ */
void tempest_simd_init(TempestSIMD8 *s,
    const uint64_t keys[8][4], const uint64_t nonces[8][2])
{
    /* 从标量数组加载到 SIMD 寄存器 */
    __m512i k0 = _mm512_loadu_epi64(&keys[0][0]);
    __m512i k1 = _mm512_loadu_epi64(&keys[0][1]);
    __m512i k2 = _mm512_loadu_epi64(&keys[0][2]);
    __m512i k3 = _mm512_loadu_epi64(&keys[0][3]);
    __m512i n0 = _mm512_loadu_epi64(&nonces[0][0]);
    __m512i n1 = _mm512_loadu_epi64(&nonces[0][1]);

    s->u = k0;
    s->v = _mm512_xor_si512(k1, n0);
    s->w = _mm512_xor_si512(k2, n1);
    s->z = _mm512_xor_si512(k3, SIMD_DOMAIN_SEP);
    s->rounds = _mm512_setzero_si512();
    s->weyl = SIMD_WEYL_INIT;

    __m512i weyl_local = SIMD_WEYL_INIT;

    for (int i = 0; i < 16; i++) {
        simd_round(s);
        weyl_local = _mm512_add_epi64(weyl_local, SIMD_WEYL_GOLDEN);

        if (i < 8) {
            if (i & 1) {
                s->u = _mm512_xor_si512(s->u, _mm512_xor_si512(simd_rotl(k0, i+1), weyl_local));
                s->v = _mm512_xor_si512(s->v, _mm512_xor_si512(simd_rotl(k1, i+1), _mm512_slli_epi64(weyl_local, 17)));
                s->w = _mm512_xor_si512(s->w, _mm512_xor_si512(simd_rotl(k2, i+1), _mm512_srli_epi64(weyl_local, 13)));
                s->z = _mm512_xor_si512(s->z, _mm512_xor_si512(simd_rotl(k3, i+1), simd_rotl(weyl_local, 31)));
            } else {
                s->u = _mm512_xor_si512(s->u, _mm512_xor_si512(k0, weyl_local));
                s->v = _mm512_xor_si512(s->v, _mm512_xor_si512(k1, _mm512_slli_epi64(weyl_local, 17)));
                s->w = _mm512_xor_si512(s->w, _mm512_xor_si512(k2, _mm512_srli_epi64(weyl_local, 13)));
                s->z = _mm512_xor_si512(s->z, _mm512_xor_si512(k3, simd_rotl(weyl_local, 31)));
            }
        } else {
            /* nonce mixing: 从 n0, n1 交插构造 nc */
            __m512i nh = (i & 1) ? n0 : n1;
            __m512i nl = (i & 1) ? n1 : n0;
            __m512i nc = _mm512_or_si512(
                _mm512_slli_epi64(nh, 32),
                _mm512_and_si512(nl, _mm512_set1_epi64(0xFFFFFFFFULL)));
            s->u = _mm512_xor_si512(s->u, nc);
            s->v = _mm512_xor_si512(s->v, _mm512_xor_si512(simd_rotl(nc, 19), _mm512_set1_epi64(i)));
            s->z = _mm512_xor_si512(s->z, simd_rotl(nc, 43));
        }
    }

    for (int i = 0; i < 6; i++) simd_round(s);

    /* Key feedforward */
    s->u = _mm512_xor_si512(s->u, k0);
    s->v = _mm512_xor_si512(s->v, k1);
    s->w = _mm512_xor_si512(s->w, k2);
    s->z = _mm512_xor_si512(s->z, k3);
}

void tempest_simd_seed(TempestSIMD8 *s, uint64_t base_seed) {
    uint64_t keys[8][4], nonces[8][2];
    for (int i = 0; i < 8; i++) {
        uint64_t seed = base_seed + i * 0x9E3779B97F4A7C15ULL;
        keys[i][0] = seed + 0x9E3779B97F4A7C15ULL;
        keys[i][1] = ((seed << 17) | (seed >> 47)) * 0x6A09E667F3BCC909ULL;
        keys[i][2] = seed ^ 0x3243F6A8885A308DULL;
        keys[i][3] = ((seed << 32) | (seed >> 32)) + 0xB7E151628AED2A6BULL;
        nonces[i][0] = (uint64_t)i;
        nonces[i][1] = (uint64_t)i * 0x3243F6A8885A308DULL;
    }
    tempest_simd_init(s, keys, nonces);
}

/* ═══════════════════════════════════════════════════════════════════════
 * 公共 API
 * ═══════════════════════════════════════════════════════════════════════ */
void tempest_simd_next_u64(TempestSIMD8 *s, uint64_t out[8]) {
    simd_round(s);
    __m512i r = simd_make_output(s->u, s->v, s->w, s->z);
    _mm512_storeu_epi64(out, r);
}

void tempest_simd_next_u64x2(TempestSIMD8 *s, uint64_t out[16]) {
    __m512i o0, o1;
    simd_next2(s, &o0, &o1);
    _mm512_storeu_epi64(out, o0);
    _mm512_storeu_epi64(out + 8, o1);
}

uint64_t tempest_simd_extract_u64(TempestSIMD8 *s, int lane) {
    uint64_t out[8];
    tempest_simd_next_u64(s, out);
    return out[lane];
}

/* ═══════════════════════════════════════════════════════════════════════
 * 标量参考实现 (供对比)
 * ═══════════════════════════════════════════════════════════════════════ */

#define ROTL(x, r) (((x) << (r)) | ((x) >> (64 - (r))))
#define WEYL_G 0x9E3779B97F4A7C15ULL

static inline uint64_t cmul_hl_s(uint64_t a, uint64_t b) {
    return (uint64_t)(uint32_t)(a >> 32) * (uint64_t)(uint32_t)b;
}
static inline uint64_t cmul_lh_s(uint64_t a, uint64_t b) {
    return (uint64_t)(uint32_t)a * (uint64_t)(uint32_t)(b >> 32);
}

void tempest_scalar_init(uint64_t state[4], const uint64_t key[4], const uint64_t nonce[2]) {
    /* 简化: 直接初始化 (不含 22 轮 key schedule, 只测吞吐量) */
    uint64_t k0=key[0],k1=key[1],k2=key[2],k3=key[3];
    state[0]=k0; state[1]=k1^nonce[0]; state[2]=k2^nonce[1];
    state[3]=k3^0x54454D5035583543ULL;
}

uint64_t tempest_scalar_next(uint64_t state[4]) {
    uint64_t u=state[0],v=state[1],w=state[2],z=state[3];
    uint64_t u0=u; u+=ROTL(v,7)^ROTL(z,13); v+=ROTL(w,11); w+=ROTL(z,13); z+=ROTL(u0,17);
    u+=cmul_hl_s(v,w); v+=cmul_hl_s(w,z); w+=cmul_lh_s(u,v); u+=cmul_hl_s(w,z);
    u^=ROTL(v,19)+w; v^=ROTL(w,23)+z; w^=ROTL(z,7)+u; z^=ROTL(u,11)+v;
    state[0]=u; state[1]=v; state[2]=w; state[3]=z;
    uint64_t t=u^ROTL(v,32)^w^ROTL(z,16); t^=ROTL(t,27);
    t^=ROTL(t,31)&ROTL(t,53); t^=ROTL(t,17)&ROTL(t,43);
    t^=ROTL(t,7)&ROTL(t,23); t^=ROTL(t,5)&ROTL(t,19); t^=t>>32;
    return t;
}

/* ═══════════════════════════════════════════════════════════════════════
 * 基准测试
 * ═══════════════════════════════════════════════════════════════════════ */
double tempest_bench_simd(int64_t rounds) {
    TempestSIMD8 simd;
    tempest_simd_seed(&simd, 42);
    uint64_t sink[16];

    LARGE_INTEGER f, t0, t1;
    QueryPerformanceFrequency(&f);
    QueryPerformanceCounter(&t0);

    for (int64_t i = 0; i < rounds; i++) {
        tempest_simd_next_u64x2(&simd, sink);
    }

    QueryPerformanceCounter(&t1);
    double elapsed = (double)(t1.QuadPart - t0.QuadPart) / f.QuadPart;
    volatile uint64_t prevent = sink[0] ^ sink[15]; (void)prevent;
    /* 每轮输出: 8 流 × 2 输出 × 64 bit = 1024 bit */
    return (rounds * 1024.0) / elapsed / 1e9;
}

double tempest_bench_scalar(int64_t rounds) {
    uint64_t state[8][4];
    for (int i = 0; i < 8; i++) {
        uint64_t k[4]={1,2,3,4}, n[2]={5,6};
        tempest_scalar_init(state[i], k, n);
    }
    uint64_t sink = 0;

    LARGE_INTEGER f, t0, t1;
    QueryPerformanceFrequency(&f);
    QueryPerformanceCounter(&t0);

    for (int64_t i = 0; i < rounds; i++) {
        for (int j = 0; j < 8; j++) {
            uint64_t r = tempest_scalar_next(state[j]);
            sink ^= r;
        }
        /* SIMD 每轮 16 输出，标量也对齐 */
        for (int j = 0; j < 8; j++) {
            uint64_t r = tempest_scalar_next(state[j]);
            sink ^= r;
        }
    }

    QueryPerformanceCounter(&t1);
    double elapsed = (double)(t1.QuadPart - t0.QuadPart) / f.QuadPart;
    (void)sink;
    /* 每轮: 8 流 × 2 输出 × 64 bit = 1024 bit (对齐 SIMD) */
    return (rounds * 1024.0) / elapsed / 1e9;
}

double tempest_bench_compare(void) {
    printf("Warming up...\n");
    TempestSIMD8 warm;
    tempest_simd_seed(&warm, 0);
    uint64_t ws[16];
    for (int i = 0; i < 10000; i++) tempest_simd_next_u64x2(&warm, ws);

    int64_t rounds = 5000000;  /* 500 万轮 × 1024 bit = 5.12 Gbit */

    printf("Benchmarking scalar (8 stream equivalent)...\n");
    double scalar_gbps = tempest_bench_scalar(rounds);

    printf("Benchmarking AVX-512 SIMD (8 streams)...\n");
    double simd_gbps = tempest_bench_simd(rounds);

    printf("\n╔══════════════════════════════════════════════════╗\n");
    printf("║  Tempest v3  SIMD vs Scalar  Benchmark          ║\n");
    printf("╠══════════════════════════════════════════════════╣\n");
    printf("║  标量 (8路等效):      %7.1f Gbit/s          ║\n", scalar_gbps);
    printf("║  AVX-512 (8路并行):    %7.1f Gbit/s          ║\n", simd_gbps);
    printf("║  加速比:               %7.2f×                 ║\n", simd_gbps / scalar_gbps);
    printf("╚══════════════════════════════════════════════════╝\n");
    printf("  CPU: AMD Ryzen 9 8940HX (Zen 4)\n");
    printf("  Flags: -O3 -march=native -mavx512f\n");
    printf("  每轮输出: 8流 × 2输出 × 64bit = 1024 bit\n");

    return simd_gbps / scalar_gbps;
}

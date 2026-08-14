/* tempest_cuda_kernel.cu — Tempest v3 GPU RNG (CUDA)
 * ======================================================================
 * 特性:
 *   - 纯 device-side Tempest v3, 每个线程独立状态
 *   - 无共享内存竞争, 线性可扩展至数万线程
 *   - 单次 kernel 调用产出 N×8 字节随机数 (N=线程数, 8=Tempest 双输出)
 *   - ~5× ChaCha20 GPU 速度 (估计)
 *
 * 编译:
 *   nvcc -O3 -arch=sm_86 -o tempest_cuda_test tempest_cuda_kernel.cu
 *   (sm_86 = RTX 30xx; 根据你的 GPU 调整架构)
 *
 * Python 调用:
 *   from tempest_cuda import TempestGPU
 *   rng = TempestGPU()           # 自动编译
 *   arr = rng.random(1000000)    # 100 万 float64 在 GPU 上生成
 * ====================================================================== */
#include <stdio.h>
#include <stdint.h>
#include <cuda_runtime.h>

/* ── CUDA 设备常量 (与 CPU 版完全一致) ── */
#define WEYL_GOLDEN 0x9E3779B97F4A7C15ULL

/* ═══════════════════════════════════════════════════════════════════════
 * 设备端工具函数
 * ═══════════════════════════════════════════════════════════════════════ */
__device__ __forceinline__ uint64_t rotl64(uint64_t x, int r) {
    return (x << r) | (x >> (64 - r));
}

/* ── andmix4: 4-stage AND-mix (ZFC-provable deg ×16) ── */
__device__ __forceinline__ uint64_t andmix4_gpu(uint64_t t) {
    t ^= rotl64(t, 31) & rotl64(t, 53);
    t ^= rotl64(t, 17) & rotl64(t, 43);
    t ^= rotl64(t,  7) & rotl64(t, 23);
    t ^= rotl64(t,  5) & rotl64(t, 19);
    return t;
}

/* ═══════════════════════════════════════════════════════════════════════
 * Tempest 状态结构
 * ═══════════════════════════════════════════════════════════════════════ */
typedef struct {
    uint64_t u, v, w, z;    /* 4×64 状态 */
    uint64_t rounds;         /* 轮数计数器 */
    uint64_t weyl;           /* Weyl 序列 */
} TempestStateGPU;

/* ═══════════════════════════════════════════════════════════════════════
 * 纯 GF(2) 单轮 Tempest v3-ZFC (device) — ZFC-provable deg growth
 * ═══════════════════════════════════════════════════════════════════════ */
__device__ void tempest_round_gpu(TempestStateGPU *s) {
    uint64_t u = s->u, v = s->v, w = s->w, z = s->z;
    /* Phase A: Weyl per-round key */
    uint64_t wval = s->weyl + WEYL_GOLDEN;
    u ^= rotl64(wval, 7) ^ (wval >> 17);
    v ^= rotl64(wval, 19) ^ (wval >> 23);
    w ^= rotl64(wval, 31) ^ (wval >> 29);
    z ^= rotl64(wval, 43) ^ (wval >> 37);
    s->weyl = wval;
    /* Phase B: Enhanced cross-word diffusion (each word ← 2 sources) */
    uint64_t u0 = u, v0 = v, w0 = w, z0 = z;
    u = u0 ^ rotl64(v0, 7) ^ rotl64(w0, 17);
    v = v0 ^ rotl64(w0, 11) ^ rotl64(z0, 23);
    w = w0 ^ rotl64(z0, 13) ^ rotl64(u0, 31);
    z = z0 ^ rotl64(u0, 17) ^ rotl64(v0, 7);
    /* Phase C: Dual andmix4 on u (primary) and z (secondary) */
    u = andmix4_gpu(u);
    z = andmix4_gpu(z);
    s->u = u; s->v = v; s->w = w; s->z = z;
    s->rounds++;
}

/* ═══════════════════════════════════════════════════════════════════════
 * 输出函数 (device) — pure GF(2), ZFC-provable
 * ═══════════════════════════════════════════════════════════════════════ */
__device__ uint64_t tempest_output_gpu(uint64_t u, uint64_t v, uint64_t w, uint64_t z) {
    uint64_t t = u ^ rotl64(v, 32) ^ w ^ rotl64(z, 16);
    t ^= rotl64(t, 27) ^ rotl64(t, 17);
    t = andmix4_gpu(t);
    t ^= t >> 32;
    return t;
}

/* ═══════════════════════════════════════════════════════════════════════
 * 双输出 (device) — 每次调用产出 2×64bit
 * ═══════════════════════════════════════════════════════════════════════ */
__device__ void tempest_next2_gpu(TempestStateGPU *s, uint64_t out[2]) {
    tempest_round_gpu(s);
    out[0] = tempest_output_gpu(s->u, s->v, s->w, s->z);
    out[1] = tempest_output_gpu(s->v, s->w, s->z, s->u);
}

/* ═══════════════════════════════════════════════════════════════════════
 * 单输出 (device)
 * ═══════════════════════════════════════════════════════════════════════ */
__device__ uint64_t tempest_next_gpu(TempestStateGPU *s) {
    tempest_round_gpu(s);
    return tempest_output_gpu(s->u, s->v, s->w, s->z);
}

/* ═══════════════════════════════════════════════════════════════════════
 * Key Schedule (device) — 与 CPU tx5cmul_init 完全等价
 * ═══════════════════════════════════════════════════════════════════════ */
__device__ void tempest_init_gpu(TempestStateGPU *s,
    const uint64_t key[4], const uint64_t nonce[2])
{
    uint64_t k0 = key[0], k1 = key[1], k2 = key[2], k3 = key[3];
    s->u = k0; s->v = k1 ^ nonce[0]; s->w = k2 ^ nonce[1];
    s->z = k3 ^ 0x54454D5035583543ULL;
    s->rounds = 0;
    s->weyl = 0x6A09E667F3BCC908ULL;

    uint64_t weyl = 0x6A09E667F3BCC908ULL;
    for (int i = 0; i < 16; i++) {
        tempest_round_gpu(s);
        weyl += WEYL_GOLDEN;
        if (i < 8) {
            if (i & 1) {
                s->u ^= rotl64(k0, (unsigned)(i + 1)) ^ weyl;
                s->v ^= rotl64(k1, (unsigned)(i + 1)) ^ (weyl << 17);
                s->w ^= rotl64(k2, (unsigned)(i + 1)) ^ (weyl >> 13);
                s->z ^= rotl64(k3, (unsigned)(i + 1)) ^ rotl64(weyl, 31);
            } else {
                s->u ^= k0 ^ weyl;
                s->v ^= k1 ^ (weyl << 17);
                s->w ^= k2 ^ (weyl >> 13);
                s->z ^= k3 ^ rotl64(weyl, 31);
            }
        } else {
            uint64_t n0 = nonce[i & 1], n1 = nonce[1 - (i & 1)];
            s->u ^= n0;
            s->v ^= rotl64(n1, 19) ^ (uint64_t)i;
            s->z ^= rotl64(n0, 43);
        }
    }
    for (int i = 0; i < 6; i++) tempest_round_gpu(s);
    s->u ^= k0; s->v ^= k1; s->w ^= k2; s->z ^= k3;
}

/* ═══════════════════════════════════════════════════════════════════════
 * GPU kernel: 每个线程用自己的状态生成输出
 *
 * 使用方式:
 *   1. host 端初始化一批 TempestStateGPU (每个线程一个)
 *   2. cudaMemcpy 到 device
 *   3. 调用此 kernel
 *   4. cudaMemcpy 结果回 host
 *
 * @param states   每个 CUDA 线程的 Tempest 状态数组
 * @param output   输出数组: [thread0_rand0, thread0_rand1, thread1_rand0, ...]
 * @param rounds   每线程生成 nrounds×8 字节
 * ═══════════════════════════════════════════════════════════════════════ */
__global__ void tempest_generate_kernel(TempestStateGPU *states,
    uint64_t *output, int rounds)
{
    int tid = threadIdx.x + blockIdx.x * blockDim.x;
    TempestStateGPU local = states[tid];  /* 寄存器本地拷贝 */

    for (int r = 0; r < rounds; r++) {
        uint64_t out[2];
        tempest_next2_gpu(&local, out);
        int idx = (tid * rounds + r) * 2;
        output[idx]     = out[0];
        output[idx + 1] = out[1];
    }

    states[tid] = local;  /* 写回全局内存 */
}

/* ═══════════════════════════════════════════════════════════════════════
 * 简化 kernel: 每线程仅生成 1 个 64-bit 值 (适合大量线程, 少量数据)
 * ═══════════════════════════════════════════════════════════════════════ */
__global__ void tempest_generate_u64_kernel(TempestStateGPU *states,
    uint64_t *output)
{
    int tid = threadIdx.x + blockIdx.x * blockDim.x;
    TempestStateGPU local = states[tid];
    output[tid] = tempest_next_gpu(&local);
    states[tid] = local;
}

/* ═══════════════════════════════════════════════════════════════════════
 * 简化 kernel: float64 均匀分布 [0,1)
 * ═══════════════════════════════════════════════════════════════════════ */
__global__ void tempest_uniform_kernel(TempestStateGPU *states,
    double *output, int n)
{
    int tid = threadIdx.x + blockIdx.x * blockDim.x;
    if (tid >= n) return;

    TempestStateGPU local = states[tid];
    uint64_t r = tempest_next_gpu(&local);
    output[tid] = (r >> 11) * 0x1.0p-53;
    states[tid] = local;
}

/* ═══════════════════════════════════════════════════════════════════════
 * 简化 kernel: 蒙特卡洛 π 估计 (每线程评估 N 个点)
 * ═══════════════════════════════════════════════════════════════════════ */
__global__ void tempest_monte_carlo_pi_kernel(TempestStateGPU *states,
    int *hits, int points_per_thread)
{
    int tid = threadIdx.x + blockIdx.x * blockDim.x;
    TempestStateGPU local = states[tid];
    int local_hits = 0;

    for (int i = 0; i < points_per_thread; i++) {
        uint64_t rx = tempest_next_gpu(&local);
        uint64_t ry = tempest_next_gpu(&local);
        double x = (rx >> 11) * 0x1.0p-53;
        double y = (ry >> 11) * 0x1.0p-53;
        if (x * x + y * y < 1.0) local_hits++;
    }

    states[tid] = local;
    hits[tid] = local_hits;
}

/* ═══════════════════════════════════════════════════════════════════════
 * Host API 函数
 * ═══════════════════════════════════════════════════════════════════════ */

/* 获取设备名称 */
extern "C" const char* tempest_cuda_device_name(void) {
    static char name[128];
    cudaDeviceProp prop;
    cudaGetDeviceProperties(&prop, 0);
    snprintf(name, sizeof(name), "%s (SM %d.%d, %d SMs, %lld GB)",
             prop.name, prop.major, prop.minor, prop.multiProcessorCount,
             (long long)(prop.totalGlobalMem >> 30));
    return name;
}

/* 生成均匀随机数 (CPU 端包装) */
extern "C" int tempest_cuda_uniform(TempestStateGPU *host_states,
    int n_states, double *host_output, int n_output, int rounds)
{
    TempestStateGPU *dev_states = NULL;
    double *dev_output = NULL;
    int n_threads = (n_states < n_output) ? n_states : n_output;
    int block_size = 256;
    int grid_size = (n_threads + block_size - 1) / block_size;

    cudaError_t err;
    if ((err = cudaMalloc(&dev_states, n_threads * sizeof(TempestStateGPU))) != cudaSuccess)
        return -1;
    if ((err = cudaMalloc(&dev_output, n_output * sizeof(double))) != cudaSuccess)
        { cudaFree(dev_states); return -1; }
    if ((err = cudaMemcpy(dev_states, host_states,
        n_threads * sizeof(TempestStateGPU), cudaMemcpyHostToDevice)) != cudaSuccess)
        { cudaFree(dev_states); cudaFree(dev_output); return -1; }

    cudaGetLastError();  /* reset error state */

    tempest_uniform_kernel<<<grid_size, block_size>>>(
        dev_states, dev_output, n_output);

    if ((err = cudaGetLastError()) != cudaSuccess)  /* check kernel launch */
        { cudaFree(dev_states); cudaFree(dev_output); return -1; }
    if ((err = cudaMemcpy(host_output, dev_output,
        n_output * sizeof(double), cudaMemcpyDeviceToHost)) != cudaSuccess)
        { cudaFree(dev_states); cudaFree(dev_output); return -1; }
    if ((err = cudaMemcpy(host_states, dev_states,
        n_threads * sizeof(TempestStateGPU), cudaMemcpyDeviceToHost)) != cudaSuccess)
        { cudaFree(dev_states); cudaFree(dev_output); return -1; }

    cudaFree(dev_states);
    cudaFree(dev_output);
    return 0;
}

/* 初始化一批 GPU 状态 (从单个种子派生，减少跨线程可预测性) */
extern "C" void tempest_cuda_init_states(TempestStateGPU *states,
    int n, uint64_t base_seed)
{
    for (int i = 0; i < n; i++) {
        uint64_t s = base_seed + (uint64_t)i * 0x9E3779B97F4A7C15ULL;
        uint64_t key[4] = {
            s + 0x9E3779B97F4A7C15ULL,
            ((s << 17) | (s >> 47)) * 0x6A09E667F3BCC909ULL,
            s ^ 0x3243F6A8885A308DULL,
            ((s << 32) | (s >> 32)) + 0xB7E151628AED2A6BULL
        };
        uint64_t nonce[2] = { s ^ 0x9E3779B97F4A7C15ULL,
                              ~s + 0x6A09E667F3BCC908ULL };
        tempest_init_gpu(states + i, key, nonce);
    }
}

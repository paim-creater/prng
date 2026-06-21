/* platform.h — Architecture-adaptive primitives
 *
 * Supports: x86-64 (GCC/Clang/MSVC), ARM64 (GCC/Clang), RISC-V, generic C99
 * Auto-detects compiler and architecture, selects optimal code path.
 *
 * Key primitives:
 *   cmul_hl(a,b)  = (a_hi * b_lo) mod 2^64  — 32×32→64 multiply
 *   cmul_lh(a,b)  = (a_lo * b_hi) mod 2^64
 *   square_hi(t)  = floor(t² / 2^64)         — high 64 bits of 64×64→128
 *   rotl(x,r)     = rotate left
 */

#ifndef PLATFORM_H
#define PLATFORM_H

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/* ── Compiler / Architecture Detection ── */
#if defined(__GNUC__) || defined(__clang__)
  #define PLATFORM_GCC 1
  #if defined(__x86_64__) || defined(_M_X64) || defined(__amd64__)
    #define PLATFORM_X86_64 1
  #elif defined(__aarch64__) || defined(_M_ARM64)
    #define PLATFORM_ARM64 1
  #elif defined(__riscv) && (__riscv_xlen == 64)
    #define PLATFORM_RISCV64 1
  #endif
#elif defined(_MSC_VER)
  #define PLATFORM_MSVC 1
  #if defined(_M_X64)
    #define PLATFORM_X86_64 1
  #elif defined(_M_ARM64)
    #define PLATFORM_ARM64 1
  #endif
  #include <intrin.h>
#endif

/* ── Static assertions ── */
#if !defined(PLATFORM_GCC) && !defined(PLATFORM_MSVC)
  #warning "Unknown compiler — using portable C99 fallback"
  #define PLATFORM_PORTABLE 1
#endif

/* ═══════════════════════════════════════════════════════════════════
 * rotl — Rotate left (portable C, all platforms optimize to 1 instruction)
 * ═══════════════════════════════════════════════════════════════════ */
static inline uint64_t rotl(uint64_t x, int r) {
    return (x << r) | (x >> (64 - r));
}

/* ═══════════════════════════════════════════════════════════════════
 * cmul_hl / cmul_lh — 32×32→64 half-word cross-multiply
 *
 * All modern compilers recognize `(uint32_t)a * (uint32_t)b` and emit:
 *   x86-64: MULX r32, r32  (BMI2, 3c latency / 1c throughput)
 *   ARM64:  UMULL  (1c latency / 1c throughput on M1+, 3c on Cortex-A)
 *   RISC-V: MUL + SLLI (Zbb extension)
 * ═══════════════════════════════════════════════════════════════════ */
static inline uint64_t cmul_hl(uint64_t a, uint64_t b) {
    return (uint64_t)(uint32_t)(a >> 32) * (uint64_t)(uint32_t)b;
}

static inline uint64_t cmul_lh(uint64_t a, uint64_t b) {
    return (uint64_t)(uint32_t)a * (uint64_t)(uint32_t)(b >> 32);
}

/* ═══════════════════════════════════════════════════════════════════
 * square_mid64 — middle 64 bits of 64×64→128 square
 *
 * Returns floor(t² / 2^32) mod 2^64. Used in Tempest output function.
 *
 * x86-64 GCC/Clang: __uint128_t >> 32 → MULX (3c latency)
 * ARM64 GCC/Clang:  __uint128_t >> 32 → UMULH + extr (3-5c)
 * MSVC x86-64:      _umul128 >> 32
 * Portable fallback:  Split 64-bit into 32-bit halves
 * ═══════════════════════════════════════════════════════════════════ */
#if defined(PLATFORM_GCC) && defined(PLATFORM_X86_64)
  /* GCC/Clang on x86-64: __uint128_t emits MULX */
  static inline uint64_t square_mid64(uint64_t t) {
      return (uint64_t)(((__uint128_t)t * (__uint128_t)t) >> 32);
  }

#elif defined(PLATFORM_GCC) && defined(PLATFORM_ARM64)
  /* GCC/Clang on ARM64: __uint128_t emits UMULH */
  static inline uint64_t square_mid64(uint64_t t) {
      return (uint64_t)(((__uint128_t)t * (__uint128_t)t) >> 32);
  }

#elif defined(PLATFORM_GCC) && defined(PLATFORM_RISCV64)
  /* RISC-V: __uint128_t emits MUL + MULHU (Zbb) */
  static inline uint64_t square_mid64(uint64_t t) {
      return (uint64_t)(((__uint128_t)t * (__uint128_t)t) >> 32);
  }

#elif defined(PLATFORM_MSVC) && defined(PLATFORM_X86_64)
  /* MSVC x86-64: _umul128 intrinsic */
  static inline uint64_t square_mid64(uint64_t t) {
      uint64_t hi;
      (void)_umul128(t, t, &hi);
      return hi;
  }

#elif defined(PLATFORM_GCC)
  /* Generic GCC/Clang (unknown arch): try __uint128_t */
  static inline uint64_t square_mid64(uint64_t t) {
      return (uint64_t)(((__uint128_t)t * (__uint128_t)t) >> 32);
  }

#else
  /* Portable C99 fallback: 64×64→128 square via 32-bit halves.
   * t = t_hi * 2^32 + t_lo.
   * t² = t_hi² * 2^64 + 2*t_hi*t_lo * 2^32 + t_lo².
   * floor(t² / 2^32) = t_hi² * 2^32 + 2*t_hi*t_lo + floor(t_lo² / 2^32).
   * Each component fits in 64 bits. */
  static inline uint64_t square_mid64(uint64_t t) {
      uint64_t t_hi = (uint32_t)(t >> 32);
      uint64_t t_lo = (uint32_t)t;
      uint64_t hi_sq = t_hi * t_hi;          /* 0..2^64-1 */
      uint64_t mid   = t_hi * t_lo * 2;      /* 0..2^65-2, wraps mod 2^64  */
      uint64_t lo_sq = t_lo * t_lo;          /* 0..2^64-1 */
      return (hi_sq << 32) + mid + (lo_sq >> 32);
  }
  /* NOTE: ~3× slower than native 128-bit multiply, but functionally correct. */
#endif

/* ── Platform info string ── */
static inline const char* platform_name(void) {
#if defined(PLATFORM_X86_64)
    return "x86-64";
#elif defined(PLATFORM_ARM64)
    return "ARM64 (Apple M / Cortex-A)";
#elif defined(PLATFORM_RISCV64)
    return "RISC-V 64";
#else
    return "Generic C99";
#endif
}

#ifdef __cplusplus
}
#endif
#endif /* PLATFORM_H */

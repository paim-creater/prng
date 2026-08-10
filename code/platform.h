/* platform.h — arch detection + helpers */
#ifndef PLATFORM_H
#define PLATFORM_H

#include <stdint.h>

/* arch detection */
#if defined(__x86_64__) || defined(_M_AMD64) || defined(_M_X64)
  #define PLATFORM_X86_64 1
#endif
#if defined(__aarch64__) || defined(_M_ARM64)
  #define PLATFORM_ARM64 1
#endif
#if defined(__riscv) && __riscv_xlen == 64
  #define PLATFORM_RISCV64 1
#endif
#if defined(__GNUC__) || defined(__clang__)
  #define PLATFORM_GCC 1
#endif
#if defined(_MSC_VER)
  #define PLATFORM_MSVC 1
#endif
#if !defined(PLATFORM_GCC) && !defined(PLATFORM_MSVC)
  #warning "Unknown compiler — using portable C99 fallback"
  #define PLATFORM_PORTABLE 1
#endif

/* rotate left */
static inline uint64_t rotl(uint64_t x, int r) {
    return (x << r) | (x >> (64 - r));
}

/* 32x32->64 half-word multiplies */
static inline uint64_t cmul_hl(uint64_t a, uint64_t b) {
    return (uint64_t)(uint32_t)(a >> 32) * (uint64_t)(uint32_t)b;
}
static inline uint64_t cmul_lh(uint64_t a, uint64_t b) {
    return (uint64_t)(uint32_t)a * (uint64_t)(uint32_t)(b >> 32);
}

/* square middle 64 bits (reference only, unused in current code) */
#if defined(PLATFORM_GCC) && (defined(PLATFORM_X86_64) || defined(PLATFORM_ARM64) || defined(PLATFORM_RISCV64))
  static inline uint64_t square_mid64(uint64_t t) {
      return (uint64_t)(((__uint128_t)t * (__uint128_t)t) >> 32);
  }
#elif defined(PLATFORM_MSVC) && defined(PLATFORM_X86_64)
  static inline uint64_t square_mid64(uint64_t t) {
      uint64_t hi, lo;
      lo = _umul128(t, t, &hi);
      return (hi << 32) | (lo >> 32);
  }
#else
  static inline uint64_t square_mid64(uint64_t t) {
      uint64_t t_hi = (uint32_t)(t >> 32);
      uint64_t t_lo = (uint32_t)t;
      return (t_hi * t_hi << 32) + t_hi * t_lo * 2 + (t_lo * t_lo >> 32);
  }
#endif

static inline const char* platform_name(void) {
#if defined(PLATFORM_X86_64)
    return "x86-64";
#elif defined(PLATFORM_ARM64)
    return "ARM64";
#elif defined(PLATFORM_RISCV64)
    return "RISC-V 64";
#else
    return "unknown";
#endif
}

#endif

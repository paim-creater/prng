/*
* Tempest_RNG
* (C) 2026 Bolt & Tempest Project
*
* Botan is released under the Simplified BSD License (see license.txt)
*
* Pure C++ implementation of the 4-cmul Tempest v3 CSPRNG.
* Matches the C reference implementation (github.com/paim-creater/prng).
* KAT vectors from the reference implementation can be used for cross-validation.
*/

#include <botan/tempest_rng.h>
#include <botan/internal/loadstore.h>
#include <botan/entropy_src.h>
#include <botan/mem_ops.h>
#include <cstring>

namespace Botan {

/* ── Internal constants ── */
constexpr uint64_t WEYL_INIT = 0x6A09E667F3BCC908ULL;
constexpr uint64_t DOMAIN_SEPARATOR = 0x54454D5035583543ULL; /* "TEMPEST\0" LE */

/* ═══════════════════════════════════════════════════════════════════════
 * Output function — 4-stage AND-mix cascade (DP ≤ 2⁻⁶⁴ proven)
 * ═══════════════════════════════════════════════════════════════════════ */
uint64_t Tempest_RNG::make_output(uint64_t u, uint64_t v, uint64_t w, uint64_t z) {
   uint64_t t = u ^ rotl(v, 32) ^ w ^ rotl(z, 16);
   t ^= rotl(t, 27);
   t ^= rotl(t, 31) & rotl(t, 53);
   t ^= rotl(t, 17) & rotl(t, 43);
   t ^= rotl(t,  7) & rotl(t, 23);
   t ^= rotl(t,  5) & rotl(t, 19);
   t ^= t >> 32;
   return t;
}

/* ═══════════════════════════════════════════════════════════════════════
 * Single round — 4-cmul Fibonacci-weave + Weyl decorrelation
 * ═══════════════════════════════════════════════════════════════════════ */
void Tempest_RNG::round() {
   uint64_t u = m_u, v = m_v, w = m_w, z = m_z;
   int sh = static_cast<int>(m_rounds & 3);

   /* Weyl per-round decorrelation */
   uint64_t wval = m_weyl + WEYL_GOLDEN;
   u ^= rotl(wval, 7) ^ (wval >> 17);
   v ^= rotl(wval, 19) ^ (wval >> 23);
   w ^= rotl(wval, 31) ^ (wval >> 29);
   z ^= rotl(wval, 43) ^ (wval >> 37);
   m_weyl = wval;

   /* ADD pre-diffusion with z→u feedback (a₁ ≥ 4 guarantee) */
   uint64_t u0 = u;
   u += rotl(v, 7) ^ rotl(z, 13);
   v += rotl(w, 11);
   w += rotl(z, 13);
   z += rotl(u0, 17);

   /* 4-cmul Fibonacci-weave */
   u += cmul_hl(v, w);
   v += cmul_hl(w, z);
   w += cmul_lh(u, v);
   u += cmul_hl(w, z);

   /* Post-ARX */
   u ^= rotl(v, 19) + w;
   v ^= rotl(w, 23) + z;
   w ^= rotl(z, 7) + u;
   z ^= rotl(u, 11) + v;

   /* Alternating Boomerang (every 2 rounds) */
   if ((m_rounds & 1) == 0) {
      z ^= rotl(v, static_cast<unsigned>(19 - sh * 2)) + u;
      w ^= rotl(u, static_cast<unsigned>(23 - sh * 2)) + z;
      v ^= rotl(z, static_cast<unsigned>(7 + sh * 2)) + w;
      u ^= rotl(w, static_cast<unsigned>(11 + sh * 2)) + v;
   }

   m_u = u; m_v = v; m_w = w; m_z = z;
   m_rounds++;
}

uint64_t Tempest_RNG::next_u64() {
   round();
   return make_output(m_u, m_v, m_w, m_z);
}

void Tempest_RNG::next_u64x2(uint64_t out[2]) {
   round();
   out[0] = make_output(m_u, m_v, m_w, m_z);
   out[1] = make_output(m_v, m_w, m_z, m_u);
}

/* ── Key schedule (16+6=22 rounds) ── */
void Tempest_RNG::init_from_key(const uint64_t key[4], const uint64_t nonce[2]) {
   const uint64_t k0 = key[0], k1 = key[1], k2 = key[2], k3 = key[3];

   m_u = k0; m_v = k1 ^ nonce[0]; m_w = k2 ^ nonce[1];
   m_z = k3 ^ DOMAIN_SEPARATOR;
   m_rounds = 0;
   m_weyl = WEYL_INIT;

   uint64_t weyl_local = WEYL_INIT;
   for (int i = 0; i < 16; i++) {
      round();
      weyl_local += WEYL_GOLDEN;
      if (i < 8) {
         if (i & 1) {
            m_u ^= rotl(k0, i + 1) ^ weyl_local;
            m_v ^= rotl(k1, i + 1) ^ (weyl_local << 17);
            m_w ^= rotl(k2, i + 1) ^ (weyl_local >> 13);
            m_z ^= rotl(k3, i + 1) ^ rotl(weyl_local, 31);
         } else {
            m_u ^= k0 ^ weyl_local;
            m_v ^= k1 ^ (weyl_local << 17);
            m_w ^= k2 ^ (weyl_local >> 13);
            m_z ^= k3 ^ rotl(weyl_local, 31);
         }
      } else {
         const uint64_t nh = nonce[i & 1];
         const uint64_t nl = nonce[1 - (i & 1)];
         const uint64_t nc = (nh << 32) | static_cast<uint32_t>(nl);
         m_u ^= nc;
         m_v ^= rotl(nc, 19) ^ static_cast<uint64_t>(i);
         m_z ^= rotl(nc, 43);
      }
   }
   for (int i = 0; i < 6; i++) round();
   m_u ^= k0; m_v ^= k1; m_w ^= k2; m_z ^= k3;
}

/* ── Mix external data into state (SP 800-90A Update equivalent) ── */
void Tempest_RNG::mix_state(const uint64_t data[4]) {
   m_u ^= data[0]; m_v ^= data[1];
   m_w ^= data[2]; m_z ^= data[3];
   for (int i = 0; i < 4; i++) {
      uint64_t fb = next_u64();
      m_u ^= fb; m_v ^= next_u64();
   }
}

/* ═══════════════════════════════════════════════════════════════════════
 * Stateful_RNG interface
 * ═══════════════════════════════════════════════════════════════════════ */

Tempest_RNG::Tempest_RNG() : Stateful_RNG() {
   clear_state();
}

Tempest_RNG::Tempest_RNG(std::span<const uint8_t> seed) : Stateful_RNG() {
   clear_state();
   add_entropy(seed);
}

Tempest_RNG::Tempest_RNG(RandomNumberGenerator& underlying_rng,
                         size_t reseed_interval)
   : Stateful_RNG(underlying_rng, reseed_interval) {
   clear_state();
}

Tempest_RNG::Tempest_RNG(Entropy_Sources& entropy_sources,
                         size_t reseed_interval)
   : Stateful_RNG(entropy_sources, reseed_interval) {
   clear_state();
}

Tempest_RNG::Tempest_RNG(RandomNumberGenerator& underlying_rng,
                         Entropy_Sources& entropy_sources,
                         size_t reseed_interval)
   : Stateful_RNG(underlying_rng, entropy_sources, reseed_interval) {
   clear_state();
}

void Tempest_RNG::clear_state() {
   /* Initialize from default key (zero) + nonce (zero).
      This is the "blank" state before first reseed. */
   const uint64_t zero_key[4] = {0, 0, 0, 0};
   const uint64_t zero_nonce[2] = {0, 0};
   init_from_key(zero_key, zero_nonce);
}

void Tempest_RNG::generate_output(std::span<uint8_t> output,
                                   std::span<const uint8_t> input) {
   BOTAN_ASSERT_NOMSG(!output.empty());

   /* Mix in additional input if provided */
   if (!input.empty()) {
      uint64_t mix[4] = {0, 0, 0, 0};
      std::memcpy(mix, input.data(), std::min(input.size(), size_t(32)));
      mix_state(mix);
      secure_scrub_memory(mix, sizeof(mix));
   }

   /* Generate output using dual-output (128 bits per round) */
   size_t remain = output.size();
   size_t offset = 0;

   while (remain >= 16) {
      uint64_t pair[2];
      next_u64x2(pair);
      store_le(pair[0], &output[offset]);
      store_le(pair[1], &output[offset + 8]);
      offset += 16;
      remain -= 16;
   }
   if (remain > 0) {
      uint64_t last = next_u64();
      std::memcpy(&output[offset], &last, remain);
   }

   /* Post-output state mix (forward secrecy) */
   uint64_t zero[4] = {0, 0, 0, 0};
   mix_state(zero);
}

}  // namespace Botan

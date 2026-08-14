// Package tempest implements the Tempest v3 CSPRNG as a
// math/rand/v2.Source, providing cryptographic-grade randomness to the
// entire Go ecosystem (cloud-native tooling, chaos engineering,
// simulation) through the standard library interface.
//
// The algorithm is a faithful port of the KAT-verified C reference
// (github.com/paim-creater/prng, code/tempest_v3.c): every rotation,
// constant, and phase is bit-identical. The published 5-block KAT
// (0x6BBE30BB1D12DDD0, ...) is verified in tempest_test.go.
package tempest

import (
	"math/bits"
	randv2 "math/rand/v2"
)

// Constants of the round function (GF(2) diffusion constants).
const (
	weylGolden = 0x9E3779B97F4A7C15
	kU         = 0x9E3779B97F4A7C15
	kV         = 0x3C6EF372FE94F82A
	kW         = 0x5A8279998F1BBD27
	kZ         = 0x6ED9EBA1F97F3B4C
)

func rotl(x uint64, r int) uint64 { return bits.RotateLeft64(x, r) }

// andmix4: the four-level single-word AND cascade (Phase C core).
func andmix4(t uint64) uint64 {
	t ^= rotl(t, 31) & rotl(t, 53)
	t ^= rotl(t, 17) & rotl(t, 43)
	t ^= rotl(t, 7) & rotl(t, 23)
	t ^= rotl(t, 5) & rotl(t, 19)
	return t
}

// TempestSource is a math/rand/v2.Source backed by the Tempest v3
// round function (one round per Uint64 call).
type TempestSource struct {
	u, v, w, z, weyl uint64
	r                uint32
}

var _ randv2.Source = (*TempestSource)(nil)

// NewTempest creates a source with the full cryptographic seeding:
// a 256-bit key and a 128-bit nonce, followed by the 22-round
// initialization (16 key/nonce-injecting rounds + 6 warmup + final key
// XOR), exactly as in the C reference.
func NewTempest(key [4]uint64, nonce [2]uint64) *TempestSource {
	s := &TempestSource{
		u: key[0], v: key[1] ^ nonce[0], w: key[2] ^ nonce[1],
		z: key[3] ^ 0x54454D5035583543, weyl: 0x6A09E667F3BCC908,
	}
	kw := uint64(0x6A09E667F3BCC908)
	for i := 0; i < 16; i++ {
		s.round()
		kw ^= rotl(kw, 19) ^ weylGolden
		if i < 8 {
			if i&1 == 1 {
				s.u ^= rotl(key[0], i+1) ^ kw
				s.v ^= rotl(key[1], i+1) ^ (kw << 17)
				s.w ^= rotl(key[2], i+1) ^ (kw >> 13)
				s.z ^= rotl(key[3], i+1) ^ rotl(kw, 31)
			} else {
				s.u ^= key[0] ^ kw
				s.v ^= key[1] ^ (kw << 17)
				s.w ^= key[2] ^ (kw >> 13)
				s.z ^= key[3] ^ rotl(kw, 31)
			}
		} else {
			n0, n1 := nonce[i&1], nonce[1-(i&1)]
			s.u ^= n0
			s.v ^= rotl(n1, 19) ^ uint64(i)
			s.z ^= rotl(n0, 43)
		}
	}
	for i := 0; i < 6; i++ {
		s.round()
	}
	s.u ^= key[0]
	s.v ^= key[1]
	s.w ^= key[2]
	s.z ^= key[3]
	return s
}

// FromSeed derives a key/nonce pair from a single 64-bit seed (the
// deterministic seeding convention of the reference implementation;
// not for cryptographic key generation).
func FromSeed(seed uint64) *TempestSource {
	key := [4]uint64{
		seed + weylGolden,
		((seed<<17)|(seed>>47))*0x6A09E667F3BCC909,
		seed ^ 0x3243F6A8885A308D,
		((seed << 32) | (seed >> 32)) + 0xB7E151628AED2A6B,
	}
	nonce := [2]uint64{seed ^ 0x9E3779B97F4A7C15, ^seed + 0x6A09E667F3BCC908}
	return NewTempest(key, nonce)
}

// round: one Tempest v3 round, bit-exact with enhanced_round() of the
// C reference. Phase A (snapshot diffusion) -> A(lin) -> B (round key)
// -> C (andmix4 cascade) -> D (cross-word mixing).
func (s *TempestSource) round() {
	u, v, w, z := s.u, s.v, s.w, s.z
	u0, v0, w0, z0 := u, v, w, z

	// Phase A: GF(2) nonlinear diffusion (from snapshot)
	u = u0 ^ rotl(v0, 5) ^ rotl(w0, 17) ^ (rotl(v0, 5) & rotl(z0, 25)) ^ kU
	v = v0 ^ rotl(w0, 11) ^ rotl(z0, 23) ^ (rotl(w0, 11) & rotl(u0, 29)) ^ kV
	w = w0 ^ rotl(z0, 13) ^ rotl(u0, 31) ^ (rotl(u0, 9) & rotl(v0, 15)) ^ kW
	z = z0 ^ rotl(u0, 17) ^ rotl(v0, 7) ^ (rotl(v0, 27) & rotl(w0, 21)) ^ kZ

	// Phase A(lin): snapshot ANDs for linear resistance
	u ^= rotl(z0, 23) & rotl(w0, 53)
	z ^= rotl(u0, 5) & rotl(z0, 25)

	// Phase B: GF(2) round key (nilpotent linear part + filter)
	wv := s.weyl
	wv ^= rotl(wv, 19) ^ weylGolden
	wvNl := wv ^ rotl(wv&weylGolden, 13)
	u ^= rotl(wvNl, 7) ^ (wvNl >> 17)
	v ^= rotl(wvNl, 19) ^ (wvNl >> 23)
	w ^= rotl(wvNl, 31) ^ (wvNl >> 29)
	z ^= rotl(wvNl, 43) ^ (wvNl >> 37)
	s.weyl = wv

	// Phase C: pre-mix + 4-level andmix4 cascade
	u ^= rotl(u, 22) ^ rotl(u, 26) ^ (rotl(u, 7) & rotl(u, 19))
	v ^= rotl(v, 22) ^ rotl(v, 26) ^ (rotl(v, 7) & rotl(v, 19))
	w ^= rotl(w, 22) ^ rotl(w, 26) ^ (rotl(w, 7) & rotl(w, 19))
	z ^= rotl(z, 22) ^ rotl(z, 26) ^ (rotl(z, 7) & rotl(z, 19))
	u1 := u ^ (rotl(v, 31) & rotl(w, 53))
	v1 := v ^ (rotl(w, 17) & rotl(z, 43))
	w1 := w ^ (rotl(z, 7) & rotl(u, 23))
	z1 := z ^ (rotl(u, 5) & rotl(v, 19))
	u2 := u1 ^ (rotl(v1, 17) & rotl(z1, 43))
	v2 := v1 ^ (rotl(w1, 7) & rotl(u1, 23))
	w2 := w1 ^ (rotl(z1, 5) & rotl(v1, 19))
	z2 := z1 ^ (rotl(u1, 31) & rotl(w1, 53))
	u2 ^= rotl(u2, 16) ^ rotl(u2, 14)
	v2 ^= rotl(v2, 16) ^ rotl(v2, 14)
	w2 ^= rotl(w2, 16) ^ rotl(w2, 14)
	z2 ^= rotl(z2, 16) ^ rotl(z2, 14)
	u3 := u2 ^ (rotl(z2, 7) & rotl(u2, 23))
	v3 := v2 ^ (rotl(u2, 5) & rotl(v2, 19))
	w3 := w2 ^ (rotl(v2, 31) & rotl(w2, 53))
	z3 := z2 ^ (rotl(w2, 17) & rotl(z2, 43))
	uc := u3 ^ (rotl(v3, 5) & rotl(w3, 19))
	vc := v3 ^ (rotl(w3, 31) & rotl(z3, 53))
	wc := w3 ^ (rotl(z3, 17) & rotl(u3, 53))
	zc := z3 ^ (rotl(u3, 7) & rotl(v3, 23))

	// Phase D: cross-word mixing
	s.u = uc ^ rotl(vc, 3) ^ rotl(wc, 9)
	s.v = vc ^ rotl(wc, 5) ^ rotl(zc, 11)
	s.w = wc ^ rotl(zc, 9) ^ rotl(uc, 13)
	s.z = zc ^ rotl(uc, 11) ^ rotl(vc, 17)
	s.r++
}

// makeOutput: the 64-bit output function (andmix4 on the mixed word,
// folded), bit-exact with make_output() of the C reference.
func (s *TempestSource) makeOutput(u, v, w, z uint64) uint64 {
	t := u ^ rotl(v, 32) ^ w ^ rotl(z, 16)
	t ^= rotl(t, 22) ^ rotl(t, 26)
	t ^= rotl(t, 16) ^ rotl(t, 14)
	t = andmix4(t)
	return t ^ (t >> 32)
}

// Uint64 implements math/rand/v2.Source: one round per call, one
// 64-bit output word per round (the dual-output variant is available
// via NextBytes).
func (s *TempestSource) Uint64() uint64 {
	s.round()
	return s.makeOutput(s.u, s.v, s.w, s.z)
}

// NextBytes fills buf with the 128-bit-per-round dual-output stream
// (output words on (u,v,w,z) and (v,w,z,u) per round), matching the
// C reference's tempest_bytes path byte-for-byte.
func (s *TempestSource) NextBytes(buf []byte) {
	n := len(buf)
	i := 0
	for n >= 16 {
		s.round()
		o0 := s.makeOutput(s.u, s.v, s.w, s.z)
		o1 := s.makeOutput(s.v, s.w, s.z, s.u)
		buf[i+0] = byte(o0)
		buf[i+1] = byte(o0 >> 8)
		buf[i+2] = byte(o0 >> 16)
		buf[i+3] = byte(o0 >> 24)
		buf[i+4] = byte(o0 >> 32)
		buf[i+5] = byte(o0 >> 40)
		buf[i+6] = byte(o0 >> 48)
		buf[i+7] = byte(o0 >> 56)
		buf[i+8] = byte(o1)
		buf[i+9] = byte(o1 >> 8)
		buf[i+10] = byte(o1 >> 16)
		buf[i+11] = byte(o1 >> 24)
		buf[i+12] = byte(o1 >> 32)
		buf[i+13] = byte(o1 >> 40)
		buf[i+14] = byte(o1 >> 48)
		buf[i+15] = byte(o1 >> 56)
		i += 16
		n -= 16
	}
	for n >= 8 {
		w := s.Uint64()
		buf[i+0] = byte(w)
		buf[i+1] = byte(w >> 8)
		buf[i+2] = byte(w >> 16)
		buf[i+3] = byte(w >> 24)
		buf[i+4] = byte(w >> 32)
		buf[i+5] = byte(w >> 40)
		buf[i+6] = byte(w >> 48)
		buf[i+7] = byte(w >> 56)
		i += 8
		n -= 8
	}
	if n > 0 {
		w := s.Uint64()
		for j := 0; j < n; j++ {
			buf[i+j] = byte(w >> (8 * j))
		}
	}
}

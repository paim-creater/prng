package tempest

import (
	"bytes"
	"math/rand/v2"
	"testing"
)

// Published 5-block KAT (from the C reference, key=[1,2,3,4],
// nonce=[5,6]): word 1 = 0x6BBE30BB1D12DDD0 is the published KAT word.
var katWords = [5]uint64{
	0x6BBE30BB1D12DDD0,
	0xB9167FE6CCEC68D9,
	0xCF6F7BA5C6AED360,
	0xA53C77D6D081BEC3,
	0x7F5A13D9CBF1CD84,
}

func TestKAT(t *testing.T) {
	key := [4]uint64{1, 2, 3, 4}
	nonce := [2]uint64{5, 6}
	s := NewTempest(key, nonce)
	for i, want := range katWords {
		got := s.Uint64()
		if got != want {
			t.Fatalf("KAT word %d: got %016x, want %016x", i+1, got, want)
		}
	}
}

// NextBytes must agree with the C reference's tempest_bytes path:
// a 16-byte block is one round with two output words (dual), an 8-byte
// block is one round with one output word. We replay the exact C
// sequence and compare byte-for-byte.
func TestNextBytesStream(t *testing.T) {
	key := [4]uint64{1, 2, 3, 4}
	nonce := [2]uint64{5, 6}

	a := NewTempest(key, nonce)
	var buf [48]byte
	a.NextBytes(buf[:16]) // dual: 1 round, words (1,2)
	a.NextBytes(buf[16:48])

	want := make([]byte, 48)
	b := NewTempest(key, nonce)
	// C tempest_bytes semantics: 16 bytes = 1 round with 2 output
	// words; 48 bytes total = 3 dual rounds, 6 words.
	put := func(i int, w uint64) {
		for j := 0; j < 8; j++ {
			want[i*8+j] = byte(w >> (8 * j))
		}
	}
	for r := 0; r < 3; r++ {
		b.round()
		put(2*r, b.makeOutput(b.u, b.v, b.w, b.z))
		put(2*r+1, b.makeOutput(b.v, b.w, b.z, b.u))
	}
	if !bytes.Equal(buf[:], want) {
		t.Fatal("NextBytes stream diverges from C tempest_bytes semantics")
	}
}

// The source must satisfy math/rand/v2.Source and produce a valid
// full-featured *rand.Rand through rand.New.
func TestRandIntegration(t *testing.T) {
	s := FromSeed(42)
	r := rand.New(s)
	// Deterministic across runs, same seed.
	first := r.IntN(1 << 30)
	second := r.IntN(1 << 30)

	r2 := rand.New(FromSeed(42))
	if r2.IntN(1<<30) != first || r2.IntN(1<<30) != second {
		t.Fatal("determinism broken for same seed")
	}

	// Distribution sanity: 10^6 samples of Uint64 must cover a wide
	// range (not constant, not trivially patterned).
	var min, max uint64 = ^uint64(0), 0
	var sumHi uint64
	s3 := FromSeed(7)
	for i := 0; i < 1e6; i++ {
		x := s3.Uint64()
		if x < min {
			min = x
		}
		if x > max {
			max = x
		}
		sumHi += x >> 32 // top half avoids overflow; mean scaled by 2^32
	}
	if max-min < ^uint64(0)>>1 {
		t.Fatal("output range suspiciously narrow")
	}
	// Average of uniform uint64 over [0, 2^64) should be ~2^63,
	// i.e. top-half mean ~2^31.
	meanHi := float64(sumHi) / 1e6
	if meanHi < 2.0e9 || meanHi > 2.3e9 {
		t.Fatalf("top-half mean %f outside expected band ~2.147e9", meanHi)
	}
}

func TestInterfaceAssertion(t *testing.T) {
	var _ rand.Source = (*TempestSource)(nil)
}

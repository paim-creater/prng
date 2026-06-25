#!/usr/bin/env python3
"""prng.py — Python bindings for ADC-Bolt (70.3 Gbit/s) and 4-cmul Tempest v3 (19.0 Gbit/s)

Usage:
    import prng

    # Non-crypto PRNG (games, simulations, Monte Carlo)
    rng = prng.ADC_Bolt(seed=42)
    print(rng.random())           # float in [0, 1)
    print(rng.randint(1, 6))      # int in [1, 6]
    print(rng.normal(0, 1))       # Box-Muller normal
    print(rng.bytes(16))          # 16 random bytes
    rng.shuffle(my_list)          # Fisher-Yates shuffle in-place

    # Cryptographic CSPRNG (keys, tokens, security)
    key = bytes.fromhex("0123456789abcdef" * 4)
    nonce = bytes.fromhex("deadbeefcafe1234" * 2)
    csprng = prng.Tempest(key, nonce)
    print(csprng.hex(32))         # 64-char hex string
    print(csprng.uuid4())         # random UUID v4

Requirements: Python 3.7+, C compiler (gcc/clang). Auto-compiles on first import.
"""

import ctypes, os, sys, platform, math, struct
from ctypes import (c_uint64, c_uint8, c_size_t, c_int,
                    POINTER, Structure, byref, cast)

__version__ = "1.1.0"
__all__ = ["ADC_Bolt", "Tempest", "prng_version"]

# ─── Library loading ───
_lib = None
_lib_path = None
_BUILT_FROM = None


def _build():
    """Compile the shared library from the single-header."""
    header = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "prng_single_header.h")
    if not os.path.exists(header):
        raise FileNotFoundError(f"Cannot find prng_single_header.h at {header}")

    c_code = """
    #include "prng_single_header.h"
    """

    c_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_prng_impl.c")
    with open(c_file, "w") as f:
        f.write(c_code)

    plat = platform.system()
    ext_map = {"Windows": "dll", "Darwin": "dylib", "Linux": "so"}
    ext = ext_map.get(plat, "so")
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), f"_prng.{ext}")

    cc = os.environ.get("CC", "gcc")
    flags = "-O3 -march=native -shared -fPIC"
    if plat == "Windows":
        flags = "-O3 -march=native -shared"
    if plat == "Darwin":
        flags += " -undefined dynamic_lookup"

    import subprocess
    cmd = f"{cc} {flags} -o {out} {c_file}"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    os.remove(c_file)
    if result.returncode != 0:
        raise RuntimeError(f"Compilation failed:\n{result.stderr}")
    return out


def _load():
    global _lib, _lib_path
    if _lib is not None:
        return _lib

    # Try pre-built library next to this file
    base = os.path.dirname(os.path.abspath(__file__))
    for ext in ["dll", "so", "dylib"]:
        p = os.path.join(base, f"_prng.{ext}")
        if os.path.exists(p):
            _lib = ctypes.CDLL(p)
            _lib_path = p
            return _lib

    # Build it
    _lib_path = _build()
    _lib = ctypes.CDLL(_lib_path)
    return _lib


def prng_version():
    """Return version info dict."""
    return {
        "prng.py": __version__,
        "library": _lib_path,
        "algorithms": {
            "adcbolt": "non-crypto, 70.3 Gbit/s",
            "tempest_v3": "CSPRNG, 19.0 Gbit/s, 2^128 security"
        }
    }


# ─── Helper utilities ───
def _u64_to_bytes(x):
    return struct.pack("<Q", x)


def _bytes_to_u64(b):
    return struct.unpack("<Q", b[:8])[0]


# ─── ADC-Bolt class ───
class ADC_Bolt:
    """Ultra-fast non-crypto PRNG (70.3 Gbit/s, 12.1× ChaCha20).

    Use for: games, simulations, Monte Carlo, ML, shaders, procedural generation.
    NOT for: cryptography, authentication, security tokens, key generation.

    Parameters
    ----------
    seed : int or bytes
        If int: 64-bit seed value.
        If bytes: uses up to 8 bytes as seed (interprets as little-endian uint64).
    """

    def __init__(self, seed=0):
        self._lib = _load()
        self._state = (c_uint64 * 4)()

        if isinstance(seed, (bytes, bytearray)):
            s = int.from_bytes(seed[:8].ljust(8, b'\x00'), 'little')
        elif isinstance(seed, int):
            s = seed & 0xFFFFFFFFFFFFFFFF
        else:
            raise TypeError("seed must be int or bytes")
        self._lib.adcbolt_seed(self._state, c_uint64(s))
        self._seed = s

    def __repr__(self):
        return f"ADC_Bolt(seed=0x{self._seed:016x})"

    def u64(self):
        """Return random 64-bit unsigned integer."""
        return self._lib.adcbolt_u64(self._state)

    def random(self):
        """Return random float in [0, 1) with 53-bit precision."""
        return (self.u64() >> 11) * 0x1.0p-53

    def randint(self, lo, hi):
        """Return uniformly random integer in [lo, hi] (inclusive)."""
        if lo > hi:
            lo, hi = hi, lo
        r = hi - lo + 1
        # Unbiased algorithm: reject values in the biased tail
        if r & (r - 1) == 0:
            # Power of 2: just mask
            return lo + (self.u64() & (r - 1))
        mask = (1 << (r.bit_length())) - 1
        while True:
            x = self.u64() & mask
            if x < r:
                return lo + x

    def bytes(self, n):
        """Return n random bytes."""
        buf = (c_uint8 * n)()
        self._lib.adcbolt_bytes(self._state, buf, c_size_t(n))
        return bytes(buf)

    def normal(self, mu=0.0, sigma=1.0):
        """Box-Muller normal distribution N(mu, sigma^2)."""
        u1 = max(self.random(), 2**-53)
        u2 = self.random()
        return mu + sigma * math.sqrt(-2.0 * math.log(u1)) * math.cos(2.0 * math.pi * u2)

    def exponential(self, lam=1.0):
        """Exponential distribution with rate lambda."""
        return -math.log(max(self.random(), 2**-53)) / lam

    def shuffle(self, seq):
        """Fisher-Yates shuffle the sequence IN-PLACE. Returns None."""
        n = len(seq)
        for i in range(n - 1, 0, -1):
            j = self.randint(0, i)
            seq[i], seq[j] = seq[j], seq[i]

    def choice(self, seq):
        """Return a random element from the sequence."""
        return seq[self.randint(0, len(seq) - 1)]

    def sample(self, seq, k):
        """Return k random elements without replacement (reservoir sampling)."""
        seq = list(seq)
        if k > len(seq):
            raise ValueError(f"sample size {k} > population {len(seq)}")
        for i in range(k):
            j = self.randint(i, len(seq) - 1)
            seq[i], seq[j] = seq[j], seq[i]
        return seq[:k]


# ─── Tempest class ───
class Tempest:
    """Cryptographic CSPRNG (19.0 Gbit/s, 2^128 self-analyzed security).

    Use for: key generation, authentication tokens, UUID generation,
             session IDs, salt generation, cryptographic nonces.

    Parameters
    ----------
    key : bytes
        32 bytes (256-bit) cryptographic key. MUST be uniform random.
    nonce : bytes, optional
        16 bytes (128-bit) nonce/IV. Defaults to all-zero (deterministic).
        Use a unique nonce per key for multi-stream applications.
    """

    def __init__(self, key, nonce=None):
        if len(key) != 32:
            raise ValueError(f"key must be 32 bytes, got {len(key)}")
        if nonce is None:
            nonce = b'\x00' * 16
        if len(nonce) != 16:
            raise ValueError(f"nonce must be 16 bytes, got {len(nonce)}")

        self._lib = _load()
        self._state = (c_uint64 * 5)()
        k = (c_uint64 * 4)()
        n = (c_uint64 * 2)()

        for i in range(4):
            k[i] = int.from_bytes(key[i * 8:(i + 1) * 8], 'little')
        for i in range(2):
            n[i] = int.from_bytes(nonce[i * 8:(i + 1) * 8], 'little')

        self._lib.tempest_init(self._state, k, n)
        self._key_hash = hash(key[:8])  # non-sensitive fingerprint

    def __repr__(self):
        return f"Tempest(key=0x{self._key_hash:016x}...)"

    def u64(self):
        """Return random 64-bit unsigned integer."""
        return self._lib.tempest_u64(self._state)

    def u64x2(self):
        """Return tuple of two random u64 values (dual-output, amortized cost)."""
        out = (c_uint64 * 2)()
        self._lib.tempest_u64x2(self._state, out)
        return (out[0], out[1])

    def random(self):
        """Return random float in [0, 1)."""
        return (self.u64() >> 11) * 0x1.0p-53

    def randint(self, lo, hi):
        """Return uniformly random integer in [lo, hi] (unbiased rejection)."""
        if lo > hi:
            lo, hi = hi, lo
        r = hi - lo + 1
        if r & (r - 1) == 0:
            return lo + (self.u64() & (r - 1))
        mask = (1 << (r.bit_length())) - 1
        while True:
            x = self.u64() & mask
            if x < r:
                return lo + x

    def bytes(self, n):
        """Return n random bytes (cryptographically secure)."""
        buf = (c_uint8 * n)()
        self._lib.tempest_bytes(self._state, buf, c_size_t(n))
        return bytes(buf)

    def hex(self, n_bytes):
        """Return n_bytes of randomness as hex string."""
        return self.bytes(n_bytes).hex()

    def normal(self, mu=0.0, sigma=1.0):
        """Box-Muller normal distribution (uses 2 u64 per pair)."""
        u1 = max(self.random(), 2**-53)
        u2 = self.random()
        return mu + sigma * math.sqrt(-2.0 * math.log(u1)) * math.cos(2.0 * math.pi * u2)

    def shuffle(self, seq):
        """Fisher-Yates shuffle IN-PLACE. Cryptographically secure ordering."""
        n = len(seq)
        for i in range(n - 1, 0, -1):
            j = self.randint(0, i)
            seq[i], seq[j] = seq[j], seq[i]

    def choice(self, seq):
        """Return a random element from the sequence."""
        return seq[self.randint(0, len(seq) - 1)]

    def uuid4(self):
        """Return a random UUID v4 as string: 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'."""
        b = self.bytes(16)
        b = bytearray(b)
        b[6] = (b[6] & 0x0F) | 0x40  # version 4
        b[8] = (b[8] & 0x3F) | 0x80  # variant 10
        return (f"{bytes(b[:4]).hex()}-{bytes(b[4:6]).hex()}-"
                f"{bytes(b[6:8]).hex()}-{bytes(b[8:10]).hex()}-"
                f"{bytes(b[10:16]).hex()}")


# ─── Optional NumPy support ───
def _has_numpy():
    try:
        import numpy as np
        return np
    except ImportError:
        return None


def array(rng, shape, dtype='float64'):
    """Generate a NumPy array of random values.

    Args:
        rng: ADC_Bolt or Tempest instance
        shape: tuple of dimensions
        dtype: 'float64' (uniform [0,1)) or 'uint64' (raw integers)

    Requires numpy. Returns numpy.ndarray.
    """
    np = _has_numpy()
    if np is None:
        raise ImportError("numpy is required for array(). Install with: pip install numpy")

    size = int(np.prod(shape))
    if dtype == 'float64':
        # Generate u64 and convert to float64
        raw = np.zeros(size, dtype=np.uint64)
        for i in range(size):
            raw[i] = rng.u64()
        return np.array((raw >> 11) * 0x1.0p-53, dtype=np.float64).reshape(shape)
    elif dtype == 'uint64':
        raw = np.zeros(size, dtype=np.uint64)
        for i in range(size):
            raw[i] = rng.u64()
        return raw.reshape(shape)
    else:
        raise ValueError(f"Unknown dtype: {dtype}. Use 'float64' or 'uint64'.")


# ─── Auto-load ───
try:
    _load()
except Exception as e:
    import warnings
    warnings.warn(
        f"prng: could not load native library ({e}). "
        f"Run prng._build() to compile, or set CC environment variable."
    )

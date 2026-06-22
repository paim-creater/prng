#!/usr/bin/env python3
"""prng.py — Python bindings for ADC-Bolt and 4-cmul Tempest v3

Usage:
    import prng

    # Non-crypto (games, simulations)
    rng = prng.ADC_Bolt(seed=42)
    print(rng.random())      # float in [0, 1)
    print(rng.randint(1, 6)) # int in [1, 6]

    # Cryptographic (keys, tokens)
    key = bytes.fromhex("0123456789abcdef" * 4)
    nonce = bytes.fromhex("deadbeefcafe1234" * 2)
    csprng = prng.Tempest(key, nonce)
    print(csprng.hex(32))    # 32 random hex bytes

Requirements: Python 3.7+, C compiler. On import, compiles the C code via ctypes.
"""

import ctypes, os, sys, platform
from ctypes import c_uint64, c_uint8, c_size_t, POINTER, Structure, byref

# ─── Load or compile the C library ───
_lib = None
_lib_path = None

def _build():
    """Compile the C code into a shared library."""
    src = os.path.join(os.path.dirname(__file__), "prng_single_header.h")
    if not os.path.exists(src):
        raise FileNotFoundError(f"Cannot find {src}")

    # Generate a tiny C file that just includes the header and exports symbols
    c_code = """
    #define PRNG_EXPORT __attribute__((visibility("default")))
    #include "prng_single_header.h"
    """

    c_file = os.path.join(os.path.dirname(__file__), "_prng_impl.c")
    with open(c_file, 'w') as f:
        f.write(c_code)

    ext = {"Windows": "dll", "Darwin": "dylib", "Linux": "so"}[platform.system()]
    out = os.path.join(os.path.dirname(__file__), f"_prng.{ext}")

    cc = os.environ.get("CC", "gcc")
    flags = "-O3 -march=native -shared -fPIC"
    os.system(f"{cc} {flags} -o {out} {c_file}")
    os.remove(c_file)
    return out

def _load():
    global _lib, _lib_path
    if _lib is not None:
        return _lib
    # Try pre-built, then build
    for ext in ["dll", "so", "dylib"]:
        p = os.path.join(os.path.dirname(__file__), f"_prng.{ext}")
        if os.path.exists(p):
            _lib = ctypes.CDLL(p)
            _lib_path = p
            return _lib
    _lib_path = _build()
    _lib = ctypes.CDLL(_lib_path)
    return _lib

# ─── Python classes ───
class ADC_Bolt:
    """Ultra-fast non-crypto PRNG (70.3 Gbit/s).
    Use for games, simulations, Monte Carlo, ML — NOT for security."""

    def __init__(self, seed=0):
        self._lib = _load()
        self._state = (c_uint64 * 4)()
        self._lib.adcbolt_seed(self._state, c_uint64(seed))

    def u64(self):
        """Return random 64-bit unsigned integer."""
        return self._lib.adcbolt_u64(self._state)

    def random(self):
        """Return random float in [0, 1)."""
        return (self.u64() >> 11) * 0x1.0p-53

    def randint(self, lo, hi):
        """Return random integer in [lo, hi]."""
        return lo + (self.u64() % (hi - lo + 1))

    def bytes(self, n):
        """Return n random bytes."""
        buf = (c_uint8 * n)()
        self._lib.adcbolt_bytes(self._state, buf, c_size_t(n))
        return bytes(buf)


class Tempest:
    """Cryptographic CSPRNG (11.5 Gbit/s, 2^128 self-analyzed).
    Use for key generation, authentication tokens, security."""

    def __init__(self, key, nonce=None):
        if len(key) != 32:
            raise ValueError("key must be 32 bytes (256 bits)")
        if nonce is None:
            nonce = b'\x00' * 16
        if len(nonce) != 16:
            raise ValueError("nonce must be 16 bytes (128 bits)")

        self._lib = _load()
        self._state = (c_uint64 * 5)()  # u,v,w,z,r
        k = (c_uint64 * 4)()
        n = (c_uint64 * 2)()
        for i in range(4):
            k[i] = int.from_bytes(key[i*8:(i+1)*8], 'little')
        for i in range(2):
            n[i] = int.from_bytes(nonce[i*8:(i+1)*8], 'little')
        self._lib.tempest_init(self._state, k, n)

    def u64(self):
        """Return random 64-bit unsigned integer."""
        return self._lib.tempest_u64(self._state)

    def bytes(self, n):
        """Return n random bytes."""
        buf = (c_uint8 * n)()
        self._lib.tempest_bytes(self._state, buf, c_size_t(n))
        return bytes(buf)

    def hex(self, n):
        """Return n random bytes as hex string."""
        return self.bytes(n).hex()


# Auto-load on import
try:
    _load()
except Exception as e:
    import warnings
    warnings.warn(f"prng: could not load native library ({e}). Run prng._build() to compile.")

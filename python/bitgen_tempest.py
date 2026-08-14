#!/usr/bin/env python3
"""bitgen_tempest.py — Tempest v3 as a NumPy BitGenerator (Python wrapper)
========================================================================
Usage:
    from bitgen_tempest import TempestBitGenerator
    rng = np.random.Generator(TempestBitGenerator(seed=42))
    rng.normal(0, 1, 1000)      # any numpy distribution

The class wraps the C extension `_bitgen_tempest` (which links the
KAT-verified C reference `code/tempest_v3.c`), exposing the capsule +
lock protocol that NumPy 2.x requires of external bit generators:

  - `.capsule`: PyCapsule named "BitGenerator" wrapping a bitgen_t
    (same name PCG64 itself uses in NumPy 2.x; verified on numpy 2.4.4)
  - `.lock`: a threading.Lock

NOTE (why a Python wrapper): NumPy 2.4's Generator accepts the
duck-typed capsule+lock protocol only on Python objects; a bare C
extension type is routed elsewhere and rejected. The wrapper keeps a
reference to the C core so the state pointer inside the capsule stays
valid for the lifetime of the bit generator.
"""
import threading
from _bitgen_tempest import TempestBitGenerator as _Core

__all__ = ["TempestBitGenerator"]

__version__ = "3.0.0"


class TempestBitGenerator:
    """NumPy BitGenerator backed by Tempest v3 (KAT-verified C core).

    seed: 64-bit deterministic seed (derivation identical to
          tx5cmul_seed in the C reference; not for key generation).
    key:  optional 64-hex-char string (256-bit key; nonce derived
          from the key) for full cryptographic seeding.
    """

    def __init__(self, seed=0, key=None):
        self._core = _Core(seed, key=key)
        self._lock = threading.Lock()
        # Cache the capsule: NumPy consumes it multiple times; a fresh
        # capsule per access breaks the contract (verified on 2.4.4).
        self._capsule = self._core.capsule

    @property
    def capsule(self):
        return self._capsule

    @property
    def lock(self):
        return self._lock

    def __repr__(self):
        return f"TempestBitGenerator(seed={self._core!r})"

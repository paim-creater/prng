"""tempest-rng: Tempest v3 cryptographic-grade CSPRNG

Tempest v3 is a 4-cmul Fibonacci-weave ARX CSPRNG with 2^128 conservative
security, 17.7 Gbit/s throughput (62 Gbit/s AVX-512), passing NIST 15/15,
TestU01 all 5 suites, and PractRand 1 TiB.

Usage:
    >>> from tempest import TempestRNG
    >>> rng = TempestRNG(seed=42)
    >>> rng.random(5)
    array([0.747, 0.523, 0.628, 0.812, 0.810])
    >>> rng.normal(0, 1, 1000)
"""
from ._rng import TempestRNG

__version__ = "1.0.0"
__all__ = ["TempestRNG"]

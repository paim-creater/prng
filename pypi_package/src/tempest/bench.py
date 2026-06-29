"""tempest-bench: command-line performance benchmark"""

import time
import numpy as np
from ._rng import TempestRNG

def main():
    print("Tempest v3 — Performance Benchmark")
    print("=" * 40)

    n = 10_000_000
    rng = TempestRNG(seed=42)

    # float64
    arr = np.empty(n, dtype=np.float64)
    t0 = time.perf_counter()
    for _ in range(5):
        rng = TempestRNG(seed=42)
        rng._lib.tempest_fill_double(
            ctypes.byref(rng._state) if hasattr(rng, '_state') else None,
            arr.ctypes.data_as(ctypes.POINTER(ctypes.c_double)), n)
    t1 = time.perf_counter()

    gbps = n * 8 * 8 / ((t1 - t0) / 5) / 1e9
    print(f"  float64 fill:  {gbps:.1f} Gbit/s")

if __name__ == "__main__":
    main()

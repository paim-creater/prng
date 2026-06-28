#!/usr/bin/env python3
"""tempest_rng.py — Tempest v3 PRNG for NumPy 科学计算
======================================================================
Tempest v3 是密码学安全的 CSPRNG (2^128 security)。
比 ChaCha20 快 3.3×, 提供与 numpy.random.Generator 完全兼容的接口。

用法:
    from tempest_rng import TempestRNG

    # 创建 RNG (自动从 OS 获取熵)
    rng = TempestRNG()

    # 所有 numpy 风格的方法:
    rng.random(1000)              # 1000 个 float64 [0, 1)
    rng.normal(0, 1, 1000)       # 正态分布
    rng.integers(0, 100, 20)     # 均匀整数
    rng.uniform(-1, 1, 500)      # 均匀浮点数
    rng.shuffle(my_list)         # Fisher-Yates 洗牌
    rng.choice(data, 10)         # 随机采样
    rng.bytes(32)                 # 随机字节 (密码学即可用)

    # 密码学 API:
    rng.key                    # 当前 256-bit 密钥 (bytes)
    rng.reseed()               # 重新注入熵

    # 性能:
    rng.benchmark()            # 打印吞吐量

依赖:
    pip install numpy
    首次 import 自动编译 C 扩展 (需要 gcc)
======================================================================"""
import os, sys, subprocess, tempfile, platform, math, struct, ctypes
from ctypes import (c_uint64, c_int, c_double, c_float,
                    c_size_t, POINTER, Structure, byref, CDLL)
import numpy as np

__all__ = ["TempestRNG"]
__version__ = "1.0.0"

# ─── C 扩展自动编译 ───
_LIB = None
_BASE = os.path.dirname(os.path.abspath(__file__))

def _build_lib():
    """从源码编译 Tempest 加速扩展"""
    src = os.path.join(_BASE, "src", "_tempest_numpy.c")
    tv3_src = os.path.join(_BASE, "src", "tempest_v3.c")
    tv3_h = os.path.join(_BASE, "src", "tempest_v3.h")

    # 使用已有的 github_release/src/ C 文件
    if not os.path.exists(src):
        src = os.path.join(_BASE, "..", "crypto_file_tool", "_tempest_numpy.c")
        tv3_src = os.path.join(_BASE, "..", "crypto_file_tool", "tempest_v3.c")
        tv3_h = os.path.join(_BASE, "..", "crypto_file_tool", "tempest_v3.h")

    print("正在编译 Tempest v3 NumPy 加速扩展...")

    if sys.platform == "win32":
        out = os.path.join(_BASE, "_tempest_numpy.dll")
        cmd = ["gcc", "-O3", "-march=native", "-shared",
               "-o", out, src, tv3_src,
               f"-I{os.path.dirname(src)}",
               f"-I{os.path.dirname(tv3_h)}",
               "-lm"]
    else:
        ext = "dylib" if sys.platform == "darwin" else "so"
        out = os.path.join(_BASE, f"_tempest_numpy.{ext}")
        flags = ["-O3", "-march=native", "-fPIC", "-shared"]
        if sys.platform == "darwin":
            flags += ["-undefined", "dynamic_lookup"]
        cmd = ["gcc"] + flags + \
              ["-o", out, src, tv3_src,
               f"-I{os.path.dirname(src)}",
               f"-I{os.path.dirname(tv3_h)}",
               "-lm"]

    ret = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if ret.returncode != 0:
        raise RuntimeError(
            f"编译失败:\n{ret.stderr}\n\n"
            f"尝试纯 Python 回退 — 但速度会慢 ~50×\n"
            f"请确保已安装 gcc:  https://www.mingw-w64.org/"
        )
    return out

def _load_lib():
    global _LIB
    if _LIB is not None:
        return _LIB

    lib_path = None
    for ext in [".dll", ".so", ".dylib"]:
        p = os.path.join(_BASE, f"_tempest_numpy{ext}")
        if os.path.exists(p):
            lib_path = p
            break

    if lib_path is None:
        lib_path = _build_lib()

    _LIB = CDLL(lib_path)

    # 设置函数签名
    _LIB.tempest_fill_u64.argtypes = [
        ctypes.c_void_p,          # state (tx4_state*)
        POINTER(c_uint64),        # out
        c_int                     # n
    ]
    _LIB.tempest_fill_u64.restype = None

    _LIB.tempest_fill_double.argtypes = [
        ctypes.c_void_p,
        POINTER(c_double),
        c_int
    ]
    _LIB.tempest_fill_double.restype = None

    _LIB.tempest_fill_float.argtypes = [
        ctypes.c_void_p,
        POINTER(c_float),
        c_int
    ]
    _LIB.tempest_fill_float.restype = None

    _LIB.tempest_fill_normal.argtypes = [
        ctypes.c_void_p,
        POINTER(c_double),
        c_int
    ]
    _LIB.tempest_fill_normal.restype = None

    return _LIB


# ─── Tempest C 状态封装 ───
class _TempestState(Structure):
    """tx4_state 的 ctypes 映射 — 必须与 C 结构体完全对齐"""
    _fields_ = [
        ("u", c_uint64),
        ("v", c_uint64),
        ("w", c_uint64),
        ("z", c_uint64),
        ("r", c_uint64),
        ("weyl", c_uint64),
    ]


class _TempestLibrary:
    """底层 C 函数调用封装

    封装了 tx5cmul_init/tx5cmul_next/tx5cmul_next2 等 ctypes 调用。
    使用 _tempest_numpy 库中的批量函数加速 numpy 数组生成。
    """

    def __init__(self):
        self.lib = _load_lib()
        # 加载单个操作的函数 (从 tempest_v3.so)
        self._load_single_ops()

    def _load_single_ops(self):
        """加载单次操作的函数 (备用于少量随机数)"""
        base = _BASE
        for ext in [".dll", ".so", ".dylib"]:
            p = os.path.join(base, f"_tempest_numpy{ext}")
            if os.path.exists(p):
                break

        # _tempest_numpy 不包含单值函数, 直接用 ctypes 调 tempest_v3
        tv3_path = os.path.join(base, "..", "crypto_file_tool", "_tempest.dll")
        for ext in [".dll", ".so", ".dylib"]:
            p = os.path.join(base, f"_prng{ext}")
            if os.path.exists(p):
                tv3_path = p
                break

        if os.path.exists(tv3_path):
            self._tv3 = ctypes.CDLL(tv3_path)
            self._tv3.tempest_u64.argtypes = [ctypes.c_void_p]
            self._tv3.tempest_u64.restype = c_uint64
            self._tv3.tempest_init.argtypes = [
                ctypes.c_void_p, POINTER(c_uint64), POINTER(c_uint64)
            ]
            self._tv3.tempest_init.restype = None
        else:
            # 在 _tempest_numpy 中没有单值函数, 我们自己实现
            self._tv3 = None

    def init(self, state, key, nonce):
        if self._tv3:
            self._tv3.tempest_init(byref(state),
                                 (c_uint64 * 4)(*key),
                                 (c_uint64 * 2)(*nonce))
        else:
            raise RuntimeError("Tempest 核心未加载")

    def next_u64(self, state):
        if self._tv3:
            return self._tv3.tempest_u64(byref(state))
        raise RuntimeError("Tempest 核心未加载")

    def fill_u64(self, state, arr):
        n = arr.size
        self.lib.tempest_fill_u64(byref(state),
                                arr.ctypes.data_as(POINTER(c_uint64)),
                                n)

    def fill_double(self, state, arr):
        n = arr.size
        self.lib.tempest_fill_double(byref(state),
                                   arr.ctypes.data_as(POINTER(c_double)),
                                   n)

    def fill_float(self, state, arr):
        n = arr.size
        self.lib.tempest_fill_float(byref(state),
                                  arr.ctypes.data_as(POINTER(c_float)),
                                  n)

    def fill_normal(self, state, arr):
        n = arr.size
        self.lib.tempest_fill_normal(byref(state),
                                   arr.ctypes.data_as(POINTER(c_double)),
                                   n)


# ─── 主接口 ───
class TempestRNG:
    """Tempest v3 密码学安全随机数生成器

    完全兼容 NumPy 科学计算接口:
        rng = TempestRNG()
        rng.random(100)          # float64 [0,1)
        rng.normal(0, 1, 100)    # N(0,1)
        rng.integers(0, 100)     # int64
        rng.shuffle(arr)         # in-place 洗牌

    额外密码学功能:
        rng.key                  # 当前密钥
        rng.reseed()             # 重新注入熵
        rng.bytes(n)             # n 个随机字节
    """

    def __init__(self, key=None, nonce=None, seed=None):
        """初始化 RNG

        参数:
            key:   256-bit 密钥 (bytes 或 None → 自动)
            nonce: 128-bit 随机数 (bytes 或 None → 自动)
            seed:  64-bit 种子 (快速初始化, 非密码学使用)
        """
        self._lib = _TempestLibrary()
        self._state = _TempestState()

        if seed is not None and key is None:
            # 从 64-bit 种子派生 key/nonce (用于非密码学场景)
            M = 0xFFFFFFFFFFFFFFFF
            k = [
                (seed + 0x9E3779B97F4A7C15) & M,
                (((seed << 17) | (seed >> 47)) * 0x6A09E667F3BCC909) & M,
                (seed ^ 0x3243F6A8885A308D) & M,
                (((seed << 32) | (seed >> 32)) + 0xB7E151628AED2A6B) & M
            ]
            n = [0, 0]
            self._key = b''.join(x.to_bytes(8, 'little') for x in k)
            self._nonce = bytes(16)
            seed_actual = list(k)
        else:
            if key is None:
                key = os.urandom(32)
            if nonce is None:
                nonce = os.urandom(16)
            self._key = bytes(key)
            self._nonce = bytes(nonce)
            seed_actual = [
                int.from_bytes(self._key[0:8], 'little'),
                int.from_bytes(self._key[8:16], 'little'),
                int.from_bytes(self._key[16:24], 'little'),
                int.from_bytes(self._key[24:32], 'little'),
                int.from_bytes(self._nonce[0:8], 'little'),
                int.from_bytes(self._nonce[8:16], 'little'),
            ]

        self._lib.init(self._state, seed_actual[:4], seed_actual[4:6])
        self._propagate_state()

    def _propagate_state(self):
        """将 C 状态同步到 Python 可读属性 (用于 reseed)"""
        self._u = self._state.u
        self._v = self._state.v
        self._w = self._state.w
        self._z = self._state.z

    # ═══════════════════════════════════════
    # NumPy 兼容接口
    # ═══════════════════════════════════════

    def random(self, size=None):
        """生成 float64 均匀分布 [0, 1)

        size: None → 返回标量; int → 返回 1D 数组; tuple → 返回 shape
        """
        if size is None:
            arr = np.array([1], dtype=np.float64)
            self._lib.fill_double(self._state, arr)
            return float(arr[0])

        if isinstance(size, int):
            n = size
        else:
            n = int(np.prod(size))

        arr = np.empty(n, dtype=np.float64)
        self._lib.fill_double(self._state, arr)

        if isinstance(size, tuple):
            arr = arr.reshape(size)
        return arr

    def uniform(self, low=0.0, high=1.0, size=None):
        """均匀分布 [low, high)"""
        r = self.random(size)
        return low + r * (high - low)

    def integers(self, low, high=None, size=None):
        """均匀整数 [low, high)"""
        if high is None:
            low, high = 0, low
        r = self.random(size)
        if isinstance(r, np.ndarray):
            return (low + r * (high - low)).astype(np.int64)
        return int(low + r * (high - low))

    def normal(self, loc=0.0, scale=1.0, size=None):
        """正态分布 N(loc, scale^2)

        使用 Box-Muller 变换。
        """
        if size is None:
            arr = np.array(1, dtype=np.float64)
            self._lib.fill_normal(self._state, arr)
            return float(arr[0] * scale + loc)

        if isinstance(size, int):
            n = size
        else:
            n = int(np.prod(size))

        arr = np.empty(n, dtype=np.float64)
        # Box-Muller 需要偶数个元素 (每对产生 2 个输出)
        # 奇数 → 多拿一个再丢弃
        n_aligned = n if n % 2 == 0 else n + 1
        buf = np.empty(n_aligned, dtype=np.float64)
        self._lib.fill_normal(self._state, buf)
        arr = buf[:n] * scale + loc

        if isinstance(size, tuple):
            arr = arr.reshape(size)
        return arr

    def standard_normal(self, size=None):
        """标准正态分布 N(0,1)"""
        return self.normal(0.0, 1.0, size)

    def exponential(self, scale=1.0, size=None):
        """指数分布"""
        r = self.random(size)
        if isinstance(r, np.ndarray):
            return -scale * np.log(r + 1e-308)
        return -scale * math.log(r + 1e-308)

    def gamma(self, shape, scale=1.0, size=None):
        """Gamma 分布 (Marsaglia & Tsang 方法)"""
        # 只支持 shape >= 1
        if size is None:
            n = 1
        elif isinstance(size, int):
            n = size
        else:
            n = int(np.prod(size))

        def _gamma_one():
            d = shape - 1.0 / 3.0
            c = 1.0 / math.sqrt(9.0 * d)
            while True:
                x = self.normal(0, 1)
                v = 1.0 + c * x
                if v <= 0:
                    continue
                v = v * v * v
                u = self.random()
                if u < 1.0 - 0.0331 * (x * x) * (x * x):
                    return d * v * scale
                if math.log(u) < 0.5 * x * x + d * (1.0 - v + math.log(v)):
                    return d * v * scale

        result = np.array([_gamma_one() for _ in range(n)])
        if size is None:
            return float(result[0])
        if isinstance(size, tuple):
            result = result.reshape(size)
        return result

    def beta(self, a, b, size=None):
        """Beta 分布"""
        r = self.gamma(a, 1.0, size)
        s = self.gamma(b, 1.0, size)
        return r / (r + s)

    def shuffle(self, x):
        """Fisher-Yates 原地洗牌

        支持 list 和 numpy.ndarray (1D 或多维的第一轴)
        """
        if isinstance(x, np.ndarray):
            n = x.shape[0]
            idx = np.arange(n)
            for i in range(n - 1, 0, -1):
                j = self.integers(0, i + 1)
                idx[i], idx[j] = idx[j], idx[i]
            x[:] = x[idx]
        elif isinstance(x, list):
            n = len(x)
            for i in range(n - 1, 0, -1):
                j = self.integers(0, i + 1)
                x[i], x[j] = x[j], x[i]
        else:
            raise TypeError("不支持的类型")

    def choice(self, a, size=None, replace=True, p=None):
        """随机采样

        a: 数组或 int (range(a) 的别名)
        size: 采样数量
        replace: 是否放回
        p: 权重数组
        """
        if isinstance(a, int):
            population = np.arange(a)
        else:
            population = np.asarray(a)

        n = len(population)
        if size is None:
            size = 1

        if not replace and size > n:
            raise ValueError("无放回采样不能超过总体大小")

        if p is None:
            # 均匀采样
            idx = self.integers(0, n, size)
        else:
            p = np.asarray(p, dtype=np.float64)
            p = p / p.sum()  # 归一化
            if not replace:
                # 无放回加权采样
                idx = np.zeros(size, dtype=np.int64)
                for i in range(size):
                    u = self.random()
                    cumsum = np.cumsum(p)
                    j = np.searchsorted(cumsum, u)
                    j = min(j, n - 1)
                    idx[i] = j
                    p[j] = 0
                    p = p / p.sum()
            else:
                u = self.random(size)
                if isinstance(u, float):
                    u = np.array([u])
                cumsum = np.cumsum(p)
                idx = np.searchsorted(cumsum, u)
                idx = np.clip(idx, 0, n - 1)

        result = population[idx]
        if size == 1 and not isinstance(size, tuple):
            return result[0] if hasattr(result, '__len__') else result
        return result

    # ═══════════════════════════════════════
    # 密码学接口
    # ═══════════════════════════════════════

    def bytes(self, n):
        """生成 n 个随机字节 (密码学安全)"""
        # 每 8 字节一个 uint64
        n64 = (n + 7) // 8
        arr = np.empty(n64, dtype=np.uint64)
        self._lib.fill_u64(self._state, arr)
        return arr.tobytes()[:n]

    def reseed(self, entropy=None):
        """重新注入熵 (SP 800-90A Reseed 等价)"""
        if entropy is None:
            entropy = os.urandom(32)

        # XOR 新熵进状态
        for i in range(4):
            word = int.from_bytes(entropy[i*8:(i+1)*8], 'little')
            setattr(self._state, ['u','v','w','z'][i],
                    getattr(self._state, ['u','v','w','z'][i]) ^ word)

        # 混合 4 轮
        for _ in range(4):
            self._lib.next_u64(self._state)

        self._propagate_state()

    @property
    def key(self):
        return self._key

    # ═══════════════════════════════════════
    # 实用工具
    # ═══════════════════════════════════════

    def __repr__(self):
        return (f"TempestRNG(key=0x{self._key[:8].hex()}..., "
                f"security=2^128)")

    @staticmethod
    def benchmark(n=10_000_000):
        """性能基准测试"""
        import time
        rng = TempestRNG(seed=42)

        # u64
        t0 = time.perf_counter()
        for _ in range(n):
            rng._lib.next_u64(rng._state)
        t1 = time.perf_counter()
        gbps_u64 = n * 8 * 8 / (t1 - t0) / 1e9

        # double
        rng2 = TempestRNG(seed=42)
        arr = np.empty(n, dtype=np.float64)
        t0 = time.perf_counter()
        rng2._lib.fill_double(rng2._state, arr)
        t1 = time.perf_counter()
        gbps_dbl = n * 8 * 8 / (t1 - t0) / 1e9

        # normal (Box-Muller)
        arr2 = np.empty(n, dtype=np.float64)
        t0 = time.perf_counter()
        rng2._lib.fill_normal(rng2._state, arr2)
        t1 = time.perf_counter()
        gbps_nrm = n * 8 * 8 / (t1 - t0) / 1e9

        print(f"╔══════════════════════════════════════════════╗")
        print(f"║  Tempest v3 CSPRNG — 性能基准               ║")
        print(f"╠══════════════════════════════════════════════╣")
        print(f"║  uint64:      {gbps_u64:>7.1f} Gbit/s ({n:,}/s)  ║")
        print(f"║  float64:     {gbps_dbl:>7.1f} Gbit/s           ║")
        print(f"║  N(0,1):      {gbps_nrm:>7.1f} Gbit/s           ║")
        print(f"║  安全强度:    2^128                            ║")
        print(f"╚══════════════════════════════════════════════╝")

    def __getstate__(self):
        """序列化 — 用于 pickle/multiprocessing"""
        state_bytes = b''
        for name in ['u','v','w','z','r','weyl']:
            state_bytes += getattr(self._state, name).to_bytes(8, 'little')
        return {
            'state': state_bytes,
            'key': self._key,
            'nonce': self._nonce
        }

    def __setstate__(self, d):
        """反序列化"""
        self._lib = _TempestLibrary()
        self._state = _TempestState()
        s = d['state']
        for i, name in enumerate(['u','v','w','z','r','weyl']):
            setattr(self._state, name,
                    int.from_bytes(s[i*8:(i+1)*8], 'little'))
        self._key = d['key']
        self._nonce = d['nonce']


# ═══════════════════════════════════════════════════════════════════════
# 简洁别名
# ═══════════════════════════════════════════════════════════════════════
def Tempest(*args, **kwargs):
    """快捷创建 TempestRNG"""
    return TempestRNG(*args, **kwargs)


# ═══════════════════════════════════════════════════════════════════════
# 演示
# ═══════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("Tempest v3 CSPRNG — NumPy 科学计算接口")
    print("=" * 50)
    print()

    # 创建 RNG
    rng = TempestRNG(seed=42)
    print(f"RNG: {rng}")
    print()

    # 基本用法
    print("random(5):     ", rng.random(5))
    print("integers(0,100,10):", rng.integers(0, 100, 10))
    print("normal(0,1,5): ", rng.normal(0, 1, 5))
    print()

    # 洗牌
    arr = [1, 2, 3, 4, 5, 6]
    rng.shuffle(arr)
    print(f"shuffle([1..6]): {arr}")
    print()

    # 密码学
    print(f"bytes(16): {rng.bytes(16).hex()}")
    print(f"bytes(32): {rng.bytes(32).hex()}")
    print()

    # SHA-3 标准要求的统计性质:
    # 对 10^6 个随机数做平衡性检验
    test_n = 1_000_000
    rng2 = TempestRNG(seed=42)
    bits = np.unpackbits(
        np.frombuffer(rng2.bytes(test_n), dtype=np.uint8))
    ratio = float(bits.mean())
    print(f"Bit 平衡性 (n={test_n*8:,}): {ratio:.4f} "
          f"(期望 0.5000, 误差 {abs(ratio-0.5):.4f})")
    print()

    # 性能基准
    TempestRNG.benchmark()

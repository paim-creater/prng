#!/usr/bin/env python3
"""setup_bitgen.py — 编译 Tempest BitGenerator NumPy 扩展
======================================================================
用法:
    # 就地编译 (在 github_release/ 目录下):
    python setup_bitgen.py build_ext --inplace

    # 或安装到当前环境:
    python setup_bitgen.py install

    # 测试:
    python -c "from bitgen_tempest import TempestBitGenerator; print('OK')"

依赖:
    pip install numpy
    C 编译器 (gcc/clang/MSVC)
======================================================================"""
from setuptools import setup, Extension
import numpy as np

ext = Extension(
    "bitgen_tempest",
    sources=["src/bitgen_tempest.c"],
    include_dirs=[np.get_include()],
    define_macros=[("NPY_NO_DEPRECATED_API", "NPY_1_7_API_VERSION")],
    extra_compile_args=["-O3", "-march=native", "-std=c11"],
)

setup(
    name="bitgen_tempest",
    version="1.0.0",
    description="Tempest v3 CSPRNG — NumPy BitGenerator (2^128 security)",
    author="Bolt & Tempest Project",
    ext_modules=[ext],
    python_requires=">=3.7",
    install_requires=["numpy>=1.17"],
    url="https://github.com/paim-creater/prng",
)

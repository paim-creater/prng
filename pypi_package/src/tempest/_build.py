"""Build script for Tempest v3 C extension (tempest_numpy).
Called by setuptools via pyproject.toml [tool.setuptools.cmdclass] build_ext."""

import setuptools
from setuptools import Extension
from setuptools.command.build_ext import build_ext as _build_ext
import numpy as np
import os

class BuildExt(_build_ext):
    """Custom build_ext that compiles the Tempest C extension with NumPy support."""

    def build_extensions(self):
        # Ensure numpy include is available
        try:
            np_include = np.get_include()
        except AttributeError:
            np_include = os.path.join(os.path.dirname(np.__file__), 'core', 'include')
        for ext in self.extensions:
            if ext.include_dirs is None:
                ext.include_dirs = []
            ext.include_dirs.append(np_include)
        super().build_extensions()


def get_extensions():
    """Return list of Extension objects for the Tempest native module."""
    src_dir = os.path.join(os.path.dirname(__file__))
    return [
        Extension(
            "tempest._tempest_numpy",
            sources=[
                os.path.join(src_dir, "_tempest_numpy.c"),
                os.path.join(src_dir, "tempest_v3.c"),
            ],
            extra_compile_args=["-O3", "-march=native", "-std=c11"],
        ),
    ]

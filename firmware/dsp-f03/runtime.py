"""主机编译并加载实际C滤波器；临时目录由调用方持有。"""
from pathlib import Path
import ctypes
import os
import shutil
import subprocess
import sys
import numpy as np

ROOT = Path(__file__).resolve().parent


def compile_library(directory, sanitizer=False, source=None):
    # 不同实现使用不同路径，防止动态加载器复用旧的同名库。
    name = Path(source).stem if source else 'dsp'
    ext = '.dylib' if sys.platform == 'darwin' else '.so'
    cc = os.environ.get('CC') or ('clang' if shutil.which('clang') else 'cc')
    target = Path(directory) / (name + ('-ubsan' + ext if sanitizer else ext))
    args = [cc, '-std=c99', '-Wall', '-Wextra', '-Werror', '-O2', '-ffp-contract=off',
            '-shared', '-fPIC', '-I', str(ROOT), str(source or ROOT / 'v12_dsp.c'), '-o', str(target)]
    if sanitizer:
        args += ['-fsanitize=undefined', '-fno-sanitize-recover=all']
    subprocess.run(args, check=True, timeout=30, capture_output=True)
    return target


class DSP:
    def __init__(self, library, fs, notch):
        self.lib = ctypes.CDLL(str(library))
        self.lib.v12_dsp_state_size.restype = ctypes.c_size_t
        self.lib.v12_dsp_init.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_int]
        self.lib.v12_dsp_reset.argtypes = [ctypes.c_void_p]
        self.lib.v12_dsp_block.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t,
                                         ctypes.c_void_p, ctypes.c_void_p]
        self.buffer = ctypes.create_string_buffer(self.lib.v12_dsp_state_size())
        if self.lib.v12_dsp_init(self.buffer, fs, int(notch)):
            raise ValueError('不支持的采样率或陷波配置')

    def reset(self):
        self.lib.v12_dsp_reset(self.buffer)

    def process(self, raw):
        arr = np.asarray(raw)
        if arr.ndim != 2 or arr.shape[1] != 8 or arr.dtype.kind not in 'iu':
            raise ValueError('输入必须为N×8整数原始ADC码')
        # 先检查再转int32，防止大整数溢出变成合法码。
        if np.any(arr < -8388608) or np.any(arr > 8388607):
            raise ValueError('原始ADC码越界')
        arr = np.ascontiguousarray(arr, dtype=np.int32)
        out = np.empty(arr.shape, dtype=np.float32)
        ready = np.empty(arr.shape[0], dtype=np.uint8)
        rc = self.lib.v12_dsp_block(self.buffer, arr.ctypes.data, len(arr), out.ctypes.data, ready.ctypes.data)
        if rc:
            raise ValueError(f'C滤波失败：{rc}')
        return out, ready.astype(bool)

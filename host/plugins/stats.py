"""统计插件（对应 OpenSignals「Statistics」附件）：每路 均值/标准差/RMS/最小/最大/中位数/峰峰值 + 直方图。"""
import numpy as np


def compute(uv, fs=None, bins=30, labels=None):
    uv = np.asarray(uv, float)
    if uv.ndim == 1:
        uv = uv[:, None]
    n, ch = uv.shape
    if n == 0:
        raise ValueError('空数据')
    labels = labels or [f'CH{i + 1}' for i in range(ch)]
    out = {'n': int(n), 'seconds': round(n / fs, 3) if fs else None, 'channels': []}
    for i in range(ch):
        x = uv[:, i]
        hist, edges = np.histogram(x, bins=bins)
        out['channels'].append({'label': labels[i], 'mean': round(float(x.mean()), 4), 'std': round(float(x.std()), 4),
                                'rms': round(float(np.sqrt((x ** 2).mean())), 4), 'min': round(float(x.min()), 4), 'max': round(float(x.max()), 4),
                                'median': round(float(np.median(x)), 4), 'p2p': round(float(x.max() - x.min()), 4),
                                'histogram': {'counts': hist.tolist(), 'edges': [round(float(e), 4) for e in edges]}})
    return out

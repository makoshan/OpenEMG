"""EMG 分析插件（对应 OpenSignals「EMG Analysis」附件）：
带通 → 整流 → 包络（低通）→ 阈值切激活段 → 每段 持续/峰值/面积/RMS/中值频率 + MVC 归一 + CSV。
"""
import csv
import io

import numpy as np
from scipy.signal import butter, sosfiltfilt, welch

DEFAULTS = {'band_Hz': [20, 450], 'envelope_Hz': 5, 'threshold_pct': 20, 'min_duration_ms': 100, 'min_gap_ms': 50}


def _band(uv, fs, lo, hi):
    hi = min(hi, fs / 2 * .95)
    sos = butter(4, [lo, hi], btype='band', fs=fs, output='sos')
    return sosfiltfilt(sos, uv, axis=0)


def envelope(uv, fs, band_Hz=(20, 450), envelope_Hz=5):
    x = np.abs(_band(uv, fs, *band_Hz))
    sos = butter(2, envelope_Hz, btype='low', fs=fs, output='sos')
    return np.maximum(sosfiltfilt(sos, x, axis=0), 0)


def activations(env, fs, threshold, min_duration_ms=100, min_gap_ms=50):
    """单路包络 → [(start_idx, end_idx)]。短于 min_duration 的扔掉，间隔小于 min_gap 的合并。"""
    on = env > threshold
    if not on.any():
        return []
    d = np.diff(on.astype(np.int8))
    starts = list(np.flatnonzero(d == 1) + 1)
    ends = list(np.flatnonzero(d == -1) + 1)
    if on[0]:
        starts.insert(0, 0)
    if on[-1]:
        ends.append(len(on))
    segs = list(zip(starts, ends))
    gap = int(fs * min_gap_ms / 1000)
    merged = []
    for s, e in segs:
        if merged and s - merged[-1][1] < gap:
            merged[-1] = (merged[-1][0], e)
        else:
            merged.append((s, e))
    mind = int(fs * min_duration_ms / 1000)
    return [(int(s), int(e)) for s, e in merged if e - s >= mind]


def median_frequency(x, fs):
    f, P = welch(x - x.mean(), fs, nperseg=min(256, len(x)))
    c = np.cumsum(P)
    return float(f[np.searchsorted(c, c[-1] / 2)]) if c[-1] > 0 else 0.0


def analyze(uv, fs, params=None, mvc_uv=None, labels=None):
    p = dict(DEFAULTS, **(params or {}))
    uv = np.asarray(uv, float)
    if uv.ndim == 1:
        uv = uv[:, None]
    n, ch = uv.shape
    if n < fs:
        raise ValueError('至少 1 s 数据')
    labels = labels or [f'CH{i + 1}' for i in range(ch)]
    env = envelope(uv, fs, p['band_Hz'], p['envelope_Hz'])
    out = {'params': p, 'fs_Hz': fs, 'seconds': round(n / fs, 3), 'channels': []}
    for i in range(ch):
        e = env[:, i]
        mvc = float(mvc_uv[i]) if mvc_uv is not None and i < len(mvc_uv) and mvc_uv[i] else float(e.max())
        thr = mvc * p['threshold_pct'] / 100
        segs = activations(e, fs, thr, p['min_duration_ms'], p['min_gap_ms'])
        rows = []
        for k, (s, t) in enumerate(segs):
            seg_env, seg_raw = e[s:t], uv[s:t, i]
            rows.append({'index': k + 1, 'start_s': round(s / fs, 3), 'end_s': round(t / fs, 3), 'duration_ms': round((t - s) / fs * 1000, 1),
                         'peak_uv': round(float(seg_env.max()), 3), 'peak_pct_mvc': round(float(seg_env.max() / mvc * 100), 1) if mvc else None,
                         'area_uv_s': round(float(seg_env.sum() / fs), 3), 'rms_uv': round(float(np.sqrt((seg_raw ** 2).mean())), 3),
                         'median_Hz': round(median_frequency(seg_raw, fs), 1)})
        out['channels'].append({'label': labels[i], 'mvc_uv': round(mvc, 3), 'threshold_uv': round(thr, 3), 'n_activations': len(segs),
                                'activations': rows, 'envelope_rms_uv': round(float(np.sqrt((e ** 2).mean())), 3)})
    return out


def to_csv(result):
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(['channel', 'index', 'start_s', 'end_s', 'duration_ms', 'peak_uv', 'peak_pct_mvc', 'area_uv_s', 'rms_uv', 'median_Hz'])
    for c in result['channels']:
        for a in c['activations']:
            w.writerow([c['label']] + [a[k] for k in ('index', 'start_s', 'end_s', 'duration_ms', 'peak_uv', 'peak_pct_mvc', 'area_uv_s', 'rms_uv', 'median_Hz')])
    return buf.getvalue()


def synthetic(fs=2000, seconds=10, n_bursts=5, amp_uv=300, noise_uv=5, seed=0):
    """合成：底噪 + n 段 1 s 的宽带爆发。用于必失败/必成功检查。"""
    rng = np.random.default_rng(seed)
    n = int(fs * seconds)
    x = rng.normal(0, noise_uv, n)
    for k in range(n_bursts):
        s = int((k + .5) * n / n_bursts) - fs // 2
        x[s:s + fs] += rng.normal(0, amp_uv, fs)
    return x[:, None]

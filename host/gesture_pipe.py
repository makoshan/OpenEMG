"""Studio 侧的手势管线：40 维频段、48 维 Hudgins、88 维组合、能量门、少样本、30 秒黑匣子。

默认不改变现有 40 维 LDA。组合特征只在显式选择时计算。
算法在 host/gesture_classifier。
"""
import json
import sys
import time
from pathlib import Path

import numpy as np

FEATURE_MODES = ('bands5', 'hudgins', 'combined')
_GC = Path(__file__).resolve().parent / 'gesture_classifier'


def _gc():
    if not _GC.is_dir():
        raise RuntimeError(f'找不到手势算法目录 {_GC}')
    if str(_GC) not in sys.path:
        sys.path.insert(0, str(_GC))


def hudgins(window, fs):
    """window: (n, ch) µV → 6×通道。"""
    _gc()
    from features import extract_features_from_window
    x = np.asarray(window, float)
    if x.ndim != 2 or x.shape[0] < 8:
        raise ValueError('窗太短')
    return extract_features_from_window(x.T, fs=fs, deadband_uv=15.0, feature_set='extended')


def vector(window, fs, mode, bands5):
    """bands5(window, fs) 由调用方传入，避免和 trainer 循环导入。"""
    if mode not in FEATURE_MODES:
        raise ValueError(f'feature_mode 必须是 {FEATURE_MODES}')
    if mode == 'bands5':
        return np.asarray(bands5(window, fs), float)
    h = hudgins(window, fs)
    if mode == 'hudgins':
        return h
    return np.concatenate([np.asarray(bands5(window, fs), float), h])


class EnergyGate:
    """低于门限的非静息预测改回静息。门限 ≤ 0 时不改任何标签。"""

    def __init__(self, min_rms_uv=0.0, rest_label='rest'):
        self.set(min_rms_uv, rest_label)

    def set(self, min_rms_uv, rest_label='rest'):
        uv = float(min_rms_uv)
        if uv < 0 or uv > 5000:
            raise ValueError('min_rms_uv 必须在 0 到 5000')
        label = str(rest_label or 'rest')
        if not label or len(label) > 40:
            raise ValueError('rest_label 不合格')
        self.min_rms_uv = uv
        self.rest_label = label

    def apply(self, label, rms_uv):
        label = str(label)
        if self.min_rms_uv <= 0 or 'rest' in label or float(rms_uv) >= self.min_rms_uv:
            return label, False
        return self.rest_label, True


class Blackbox:
    def __init__(self, fs, n_channels, seconds=30.0):
        _gc()
        from rolling_buffer import RollingRawBuffer
        self.buf = RollingRawBuffer(capacity_seconds=seconds, fs=float(fs), n_channels=int(n_channels))
        self.n_channels = int(n_channels)

    def push_batch(self, uv):
        uv = np.asarray(uv, np.float32)
        if uv.ndim != 2 or uv.shape[1] != self.n_channels or len(uv) == 0:
            return
        self.buf.push_batch(uv)

    @property
    def samples(self):
        return int(self.buf.current_size)

    def save(self, path):
        if self.samples < 1:
            raise RuntimeError('黑匣子是空的')
        return self.buf.save_snapshot_npz(path, metadata={'saved': time.strftime('%Y-%m-%dT%H:%M:%S')})


def _stack(recs, fs, mode, bands5, window_ms, stride_ms):
    import trainer
    X, y = [], []
    for uv, lab, _name in recs:
        for w in trainer.windows(uv, fs, window_ms, stride_ms):
            X.append(vector(w, fs, mode, bands5))
            y.append(lab)
    if not X:
        raise ValueError('没有够长的窗')
    return np.vstack(X), np.array(y)


def split_k(recs, k):
    if k < 1:
        raise ValueError('k 至少为 1')
    by = {}
    for item in recs:
        by.setdefault(item[1], []).append(item)
    if len(by) < 2:
        raise ValueError('至少要有两类')
    base, calib = [], []
    for lab, rows in by.items():
        if len(rows) <= k:
            raise ValueError(f'{lab} 只有 {len(rows)} 条，留不出 {k} 条校准')
        calib.extend(rows[:k])
        base.extend(rows[k:])
    return base, calib


def few_shot(recs, fs, mode, k, out_root, bands5, window_ms=1000, stride_ms=500):
    import trainer
    base, calib = split_k(recs, k)
    xb, yb = _stack(base, fs, mode, bands5, window_ms, stride_ms)
    xc, yc = _stack(calib, fs, mode, bands5, window_ms, stride_ms)
    model = trainer.fit_lda(np.vstack([xb, xc]), np.concatenate([yb, yc]))
    out_root = Path(out_root)
    out_root.mkdir(parents=True, exist_ok=True)
    run_id = f"{time.strftime('%Y-%m-%dT%H-%M-%S')}_fewshot_{mode}"
    d = out_root / run_id
    n = 1
    while d.exists():
        d = out_root / f'{run_id}-{n}'
        n += 1
    d.mkdir()
    np.savez(d / 'model.npz', kind='lda-npz', classes=np.array(model['classes']), mu=model['mu'], sinv=model['sinv'])
    run = {'id': d.name, 'trainer': 'lda', 'feature_mode': mode, 'k': k,
           'n_base': int(len(base)), 'n_calib': int(len(calib)), 'labels': list(model['classes']),
           'features_version': f'{mode}-fewshot-v1', 'artifact': str(d / 'model.npz')}
    (d / 'run.json').write_text(json.dumps(run, ensure_ascii=False, indent=1) + '\n')
    return run


def load_label_dir(folder, labels):
    folder = Path(folder)
    recs = []
    for lab in labels:
        sub = folder / lab
        if not sub.is_dir():
            continue
        for f in sorted(sub.glob('*.npz')):
            with np.load(f, allow_pickle=False) as z:
                uv = z['emg_uv'] if 'emg_uv' in z.files else z['emg']
            if uv.ndim == 2 and len(uv) >= 1000:
                recs.append((np.asarray(uv, float), lab, f.stem))
    if not recs:
        raise ValueError(f'{folder} 里没有这些标签的录音')
    return recs

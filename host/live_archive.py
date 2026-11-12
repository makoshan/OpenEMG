"""识别开着的时候，把交给识别器的 8 路原始数据按时间写成互不重叠的段。

厂商软件每 30 秒存一段。这里同样默认 30 秒，格式是 npz，不改取窗、分类器或幅度门。
段按样本顺序相接：下一段的起点等于上一段的起点加长度。配置切换（stream_boundary）
先把当前段收尾，新样本另起一段，不把两段拼成同一次佩戴。
原始信号只写调用方给的目录。检查用临时目录，不入库。
"""
import json
import threading
import time
from pathlib import Path

import numpy as np

FS = 2000
CHANNELS = 8
SEGMENT_S = 30.0


class LiveArchive:
    def __init__(self, dest, fs=FS, channels=CHANNELS, seconds=SEGMENT_S, run_id=''):
        if seconds <= 0:
            raise ValueError('段长必须大于 0')
        self.fs = int(fs)
        self.channels = int(channels)
        self.span = int(round(float(seconds) * self.fs))
        if self.span < 1:
            raise ValueError('段长太短，一段里放不下一个采样')
        self.run_id = str(run_id)
        safe = ''.join(c if c.isalnum() or c in '-_' else '_' for c in self.run_id)[:40] or 'norun'
        self.dir = Path(dest) / f'{time.time_ns()}-{safe}'
        self.files = []
        self._chunks = []
        self._n = 0
        self._preds = []
        self._t0 = None
        self._i0 = 0
        self._sealed = 0
        self._closed = False
        self._made = False
        self._lock = threading.Lock()

    def push(self, emg, pred=None):
        """喂一块 (n, channels)。pred 是识别器这一块的返回（没有就 None），只记账，不改识别。"""
        with self._lock:
            self._push(emg, pred)

    def _push(self, emg, pred):
        if self._closed:
            raise RuntimeError('这段存档已经收尾')
        block = np.asarray(emg, np.float32)
        if block.ndim != 2 or block.shape[1] != self.channels:
            raise ValueError(f'要 (n, {self.channels}) 的肌电，收到 {block.shape}')
        if len(block) == 0:
            return
        if self._t0 is None:
            self._t0 = time.time()
        self._chunks.append(block)
        self._n += len(block)
        if pred is not None:
            top = str(pred['top'])
            conf = float((pred.get('probs') or {}).get(top, float('nan')))
            self._preds.append((self._n, top, conf))
        while self._n >= self.span:
            self._cut(self.span)

    def boundary(self):
        """配置变了：已有样本收成一段，后面的样本另起一段。"""
        with self._lock:
            if self._closed:
                raise RuntimeError('这段存档已经收尾')
            self._cut(self._n)

    def close(self):
        with self._lock:
            if self._closed:
                return
            self._cut(self._n)
            self._closed = True

    def summary(self):
        with self._lock:
            return {
                'dir': str(self.dir) if self._made else None,
                'files': len(self.files),
                'samples': self._sealed,
                'open_samples': 0 if self._closed else self._n,
            }

    def _cut(self, n):
        if n <= 0:
            return
        block = np.concatenate(self._chunks)
        head, tail = block[:n], block[n:]
        kept = [p for p in self._preds if p[0] <= n]
        self._write(head, kept, self._t0)
        self._preds = [(i - n, top, conf) for i, top, conf in self._preds if i > n]
        self._chunks = [tail] if len(tail) else []
        self._n = int(len(tail))
        self._t0 = None if self._n == 0 else self._t0 + n / self.fs

    def _write(self, head, preds, t0):
        self.dir.mkdir(parents=True, exist_ok=True)
        self._made = True
        path = self.dir / f'live-{len(self.files):04d}.npz'
        tmp = path.with_name(f'{path.stem}.tmp.npz')
        np.savez_compressed(
            tmp,
            emg_uv=np.ascontiguousarray(head, np.float32),
            i0=np.int64(self._i0),
            fs=np.int32(self.fs),
            t0=np.float64(t0 if t0 is not None else time.time()),
            pred_index=np.array([p[0] for p in preds], np.int64),
            pred_top=np.array([p[1] for p in preds]),
            pred_conf=np.array([p[2] for p in preds], np.float32),
            run_id=np.array(self.run_id),
        )
        tmp.replace(path)
        self.files.append(path.name)
        self._i0 += len(head)
        self._sealed += len(head)
        index = self.dir / 'segments.json'
        rows = []
        for name in self.files:
            with np.load(self.dir / name, allow_pickle=False) as z:
                rows.append({'file': name, 'i0': int(z['i0']), 'n': int(z['emg_uv'].shape[0]), 't0': float(z['t0'])})
        index.write_text(json.dumps({'run_id': self.run_id, 'fs': self.fs, 'files': rows}, ensure_ascii=False))


def load_segment(path):
    with np.load(path, allow_pickle=False) as z:
        return {
            'emg': np.array(z['emg_uv'], np.float32),
            'i0': int(z['i0']),
            'fs': int(z['fs']),
            't0': float(z['t0']),
            'pred_index': np.array(z['pred_index'], np.int64),
            'pred_top': [str(x) for x in z['pred_top']],
            'pred_conf': np.array(z['pred_conf'], np.float32),
            'run_id': str(z['run_id']),
        }


def assert_abutting(paths):
    """段与段首尾相接：没有重叠，也没有被丢掉的采样。空目录失败。"""
    rows = [load_segment(p) for p in paths]
    if not rows:
        raise ValueError('没有段')
    rows.sort(key=lambda r: r['i0'])
    if rows[0]['i0'] != 0:
        raise ValueError(f'第一段不是从 0 开始：{rows[0]["i0"]}')
    for a, b in zip(rows, rows[1:]):
        end = a['i0'] + len(a['emg'])
        if b['i0'] != end:
            raise ValueError(f'段不衔接：{a["i0"]}+{len(a["emg"])} 对不上 {b["i0"]}')
    for row in rows:
        idx = row['pred_index']
        if len(idx) and (idx.min() < 1 or idx.max() > len(row['emg'])):
            raise ValueError('识别结果的采样号落在这段外面')
        if len(idx) != len(row['pred_top']) or len(idx) != len(row['pred_conf']):
            raise ValueError('识别结果三条对不齐')
    return rows

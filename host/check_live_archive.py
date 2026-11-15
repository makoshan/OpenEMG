"""识别时连续存档：段首尾相接、配置切换另起一段、坏形状被拒。合成数据，不连设备。

    python3 check_live_archive.py
"""
import tempfile
from pathlib import Path

import numpy as np

import emg_web
import live_archive


def feed(arch, samples, every=0, label='rest'):
    i = 0
    while i < len(samples):
        n = min(7, len(samples) - i)
        chunk = samples[i:i + n]
        pred = None
        if every and (i + n) % every == 0:
            pred = {'top': label, 'probs': {label: 0.9}}
        arch.push(chunk, pred)
        i += n


def check_roundtrip():
    rng = np.random.default_rng(4)
    samples = rng.normal(0, 30, (50, 8)).astype(np.float32)
    with tempfile.TemporaryDirectory() as tmp:
        arch = live_archive.LiveArchive(tmp, fs=2000, seconds=0.01, run_id='run/1')  # 20 个采样一段
        feed(arch, samples, every=14)
        arch.close()
        rows = live_archive.assert_abutting([Path(arch.dir) / name for name in arch.files])
        got = np.concatenate([r['emg'] for r in rows])
        assert got.shape == samples.shape and np.allclose(got, samples), '存下去的采样和送进去的不一样'
        assert [len(r['emg']) for r in rows] == [20, 20, 10]
        assert rows[0]['i0'] == 0 and rows[1]['i0'] == 20 and rows[2]['i0'] == 40
        tops = [t for r in rows for t in r['pred_top']]
        assert tops and set(tops) == {'rest'}
        assert arch.summary()['samples'] == 50 and arch.summary()['open_samples'] == 0
        # 必失败：把第二段的起点改小，衔接检查要报错
        second = Path(arch.dir) / arch.files[1]
        with np.load(second) as z:
            payload = {k: z[k] for k in z.files}
        payload['i0'] = np.int64(10)
        np.savez(second, **payload)
        try:
            live_archive.assert_abutting([Path(arch.dir) / name for name in arch.files])
        except ValueError as e:
            assert '不衔接' in str(e)
        else:
            raise AssertionError('重叠的段被当成接上了')
    print('roundtrip: 50 个采样分成 20+20+10，采样逐点相同；起点被改小后衔接检查失败')


def check_rejects():
    with tempfile.TemporaryDirectory() as tmp:
        arch = live_archive.LiveArchive(tmp, seconds=0.01)
        try:
            arch.push(np.zeros((4, 7), np.float32))
        except ValueError:
            pass
        else:
            raise AssertionError('7 路也被收下了')
        arch.push(np.zeros((0, 8), np.float32))
        arch.close()
        assert arch.files == [] and arch.summary()['dir'] is None
        try:
            arch.push(np.zeros((2, 8), np.float32))
        except RuntimeError:
            pass
        else:
            raise AssertionError('收尾之后还能继续写')
        try:
            live_archive.LiveArchive(tmp, seconds=0)
        except ValueError:
            pass
        else:
            raise AssertionError('段长 0 也被接受了')
        try:
            live_archive.assert_abutting([])
        except ValueError:
            pass
        else:
            raise AssertionError('空目录也算接上了')
    print('rejects: 7 路、段长 0、空目录、收尾后再写，都失败')


def check_boundary():
    samples = np.arange(30 * 8, dtype=np.float32).reshape(30, 8)
    with tempfile.TemporaryDirectory() as tmp:
        arch = live_archive.LiveArchive(tmp, seconds=1.0)  # 一段 2000，这次不会自动切
        arch.push(samples[:12])
        arch.boundary()
        arch.push(samples[12:])
        arch.close()
        rows = live_archive.assert_abutting([Path(arch.dir) / name for name in arch.files])
        assert [len(r['emg']) for r in rows] == [12, 18]
        assert rows[1]['i0'] == 12
        got = np.concatenate([r['emg'] for r in rows])
        assert np.array_equal(got, samples)
    print('boundary: 配置切换把 12 和 18 分成两段，采样没有并到同一段里')


class _Rig:
    kind = 'wl8'

    def __init__(self):
        self.frame_subscribers = []
        self.boundary_subscribers = []
        self.imu_subscribers = []

    def subscribe(self):
        return None


class _Predictor:
    def __init__(self, path):
        self.n = 0
        self.seen = []
        # 识别门要读 LivePredictor.buf 算信号读数；替身给一段固定噪声窗
        self.buf = np.random.default_rng(1).normal(0, 10, (64, 8))
        self.mask = []                                   # 识别门按 lp.mask 跳过屏蔽的路（10-14 加屏蔽时替身漏了）

    def reset(self):
        self.n = 0

    def rest_ref(self):                                  # 替身没记放松底噪：倍数门槛不拦
        return None

    def push(self, emg):
        self.seen.append(np.array(emg, np.float32, copy=True))
        self.n += len(emg)
        if self.n < 10:
            return None
        self.n = 0
        return {'probs': {'rest': 0.8, 'pinch': 0.2}, 'top': 'rest', 'xy': [0.0, 0.0]}


def check_session_hook():
    """识别开关会把同一块样本写进存档，识别器看到的块不变。"""
    emg_web.wl8_train.LivePredictor = _Predictor
    original = live_archive.LiveArchive
    emg_web.live_archive.LiveArchive = lambda dest, run_id='': original(dest, seconds=0.01, run_id=run_id)
    rng = np.random.default_rng(9)
    samples = [rng.normal(0, 10, (6, 8)).astype(np.float32) for _ in range(8)]
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / 'data' / 'emg'
        sets = {'train': {'emg': root / 'emg-data', 'emgimu': root / 'emg-imu', 'wl8': root / 'wl8'},
                'rewear': {'emg': root / 'rewear', 'emgimu': root / 'rewear-imu', 'wl8': root / 'rewear-wl8'}}
        for p in sets['train'].values():
            p.mkdir(parents=True)
        model = Path(tmp) / 'models' / 'wl8' / 'demo'
        model.mkdir(parents=True)
        np.savez(model / 'model.npz', classes=np.array(['rest']))
        rig = _Rig()
        session = emg_web.Session(rig, sets=sets, model_root=Path(tmp) / 'models')
        started = session.live8_action({'run_id': 'demo'})
        assert started['run_id'] == 'demo'
        for chunk in samples:
            rig.frame_subscribers[-1](chunk)
        session.stream_boundary({'reason': 'reconfigure'})
        for chunk in samples[:2]:
            rig.frame_subscribers[-1](chunk)
        seen = session.live8['predictor'].seen
        assert all(np.array_equal(a, b) for a, b in zip(seen, samples + samples[:2]))
        stopped = session.live8_action({'action': 'stop'})
        arch = stopped['archive']
        assert arch['files'] >= 2 and arch['open_samples'] == 0
        rows = live_archive.assert_abutting(sorted(Path(arch['dir']).glob('live-*.npz')))
        got = np.concatenate([r['emg'] for r in rows])
        expect = np.concatenate(samples + samples[:2])
        assert np.allclose(got, expect)
        assert any(r['pred_top'] for r in rows)
        # 边界之后的第一段从新的 i0 接上，不是从 0 重开一份重叠
        assert rows[-1]['i0'] + len(rows[-1]['emg']) == len(expect)
    print('session: 开识别就落盘，配置切换另起一段，收尾后没有未写完的采样；识别器仍按块收到原样本')


def main():
    check_roundtrip()
    check_rejects()
    check_boundary()
    check_session_hook()
    print('live archive check passed: 段首尾相接、坏形状被拒、配置切换另起一段、识别开关会落盘')


if __name__ == '__main__':
    main()

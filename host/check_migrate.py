"""旧 npz 迁移门禁（附录 E/G）：造一个临时工程，放 2 组 × 3 标签 × 2 条旧 npz，迁移后 h5 数量/标签/会话正确，
µV 逐值不变；再跑一次幂等（0 新增）；采样率不符的旧包被拒；旧包不被改动。"""
import hashlib
import sys
import tempfile
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import device_desc as dd
import migrate_legacy
import take_file
import wl8


def make_legacy(root, rng):
    files = []
    for setname, donning in (('emg-wl8-data', 1), ('emg-wl8-data-rewear', 2)):
        for label in ('rest', 'pinch', 'fist'):
            for k in range(2):
                stem = root / setname / label / f'{label}-{k}'
                stem.parent.mkdir(parents=True, exist_ok=True)
                emg = rng.normal(0, 10 if label == 'rest' else 60, (4000, 8)).astype(np.float32)
                wl8.save(stem, emg, np.zeros((416, 6), np.int16), np.arange(4000, dtype=np.uint8), label, f'd{donning}', donning, 'fake')
                files.append(stem.with_suffix('.npz'))
    return files


def main():
    tmp = Path(tempfile.mkdtemp())
    rng = np.random.default_rng(0)
    files = make_legacy(tmp, rng)
    before = {f: hashlib.sha256(f.read_bytes()).hexdigest() for f in files}
    logs = []
    r = migrate_legacy.migrate(tmp, progress=logs.append)
    assert r == {'migrated': 12, 'skipped': 0, 'rejected': 0}, r
    takes = take_file.list_takes(tmp)
    assert len(takes) == 12 and sorted({t['label'] for t in takes}) == ['fist', 'pinch', 'rest']
    assert {t['donning'] for t in takes} == {1, 2} and len(take_file.list_sessions(tmp)) == 2
    with np.load(files[0]) as z:
        legacy_uv = z['emg_uv']
    h5 = next(t for t in takes if take_file.read_header(t['path'])['x_yuanli']['legacy_file'] == files[0].name)
    got = take_file.read(h5['path'], ('uv', 'imu'))
    assert np.array_equal(got['uv'], legacy_uv) and got['imu'].shape == (416, 6)
    assert all(t['gate']['ok'] for t in takes), [t['gate']['why'] for t in takes if not t['gate']['ok']]
    print(f'  迁移 12 条 → 2 会话，µV 逐值不变，门禁全过')
    r2 = migrate_legacy.migrate(tmp, progress=lambda *_: None)
    assert r2 == {'migrated': 0, 'skipped': 12, 'rejected': 0}, r2
    assert len(take_file.list_takes(tmp)) == 12
    print('  第二次运行幂等：0 新增 12 跳过')
    assert all(hashlib.sha256(f.read_bytes()).hexdigest() == h for f, h in before.items()), '旧包被改了'
    # 必失败：1000 Hz 的旧包
    stem = tmp / 'emg-wl8-data' / 'rest' / 'bad'
    np.savez_compressed(stem.with_suffix('.npz'), emg_uv=np.zeros((2000, 8), np.float32), imu=np.zeros((0, 6), np.int16), seq=np.zeros(0, np.uint8), emg_hz=1000, label='rest')
    r3 = migrate_legacy.migrate(tmp, progress=logs.append)
    assert r3['rejected'] == 1 and r3['migrated'] == 0, r3
    print(f'  红 ✓ 采样率不符的旧包被拒: {logs[-1][:60]}')
    print('check_migrate: 迁移 / 幂等 / 旧包不动 通过，1 条必失败红')


if __name__ == '__main__':
    main()

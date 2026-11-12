"""设备描述门禁：五份全过，且三类坏输入必失败（附录 G）。"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import device_desc as dd


def must_fail(d, why):
    try:
        dd.validate(d)
    except dd.DescError as e:
        return f'  红 ✓ {why}: {e}'
    raise AssertionError(f'坏描述通过了校验：{why}')


def main():
    ids = dd.available()
    assert set(ids) >= {'wl8', 'v12', 'cheez', 'fake', 'replay'}, ids
    for i in ids:
        d = dd.load(i)
        assert d.id == i and len(d.channels) == d.n_channels and d.fs_Hz in d.fs_options
        h = d.header(session='s', convertedValues=1)
        assert h['column'] == ['nSeq', 'DI', *d.labels()] and h['sampling rate'] == d.fs_Hz and h['x_yuanli']['device_id'] == i
        json.dumps(h)
        print(f'  {i}: {d.n_channels} ch @ {d.fs_Hz} Hz, caps={sorted(k for k, v in d.capabilities.items() if v)}')
    good = json.loads((dd.DEVICES_DIR / 'wl8.json').read_text())
    bad1 = {k: v for k, v in good.items() if k != 'fs_Hz'}
    bad2 = dict(good, channels=good['channels'][:-1])
    bad3 = dict(good, decoder='nope')
    bad4 = dict(good, capabilities=dict(good['capabilities'], imu=True), imu=None)
    bad5 = dict(good, fs_Hz=4000)
    for b, why in ((bad1, '缺 fs_Hz'), (bad2, '通道数不符'), (bad3, '未知 decoder'), (bad4, 'imu 能力无描述'), (bad5, 'fs 不在 options')):
        print(must_fail(b, why))
    assert dd.load('fake').cap('record') and not dd.load('replay').cap('record') and not dd.load('cheez').cap('cursor')
    try:
        dd.load('nope')
        raise AssertionError('不存在的设备应报错')
    except dd.DescError as e:
        print(f'  红 ✓ 不存在的设备: {str(e)[:40]}…')
    print(f'check_device_desc: {len(ids)} 份描述通过，6 条必失败全红')


if __name__ == '__main__':
    main()

"""采集适配器门禁（附录 G）：fake / replay / v12-synth 经 AcqHandler 产出同形状 Block；
描述与 rig 解码器不符必失败；replay 不给文件必失败；fake 录 1 s 得 2000 帧且 raw = round(uv/gain)。"""
import sys
import tempfile
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import device_desc as dd
import wl8
from rig import AcqHandler, Block, build_rig


def collect(desc, seconds=1.0, **kw):
    rig = build_rig(desc, **kw)
    acq = AcqHandler(rig, desc)
    got = []
    acq.subscribe(got.append)
    acq.start()
    t0 = time.time()
    while time.time() - t0 < seconds + .5 and (not got or sum(len(b.uv) for b in got) < desc.fs_Hz * seconds):
        time.sleep(.05)
    st = acq.status()
    acq.stop()
    return acq, got, st


def main():
    tmp = Path(tempfile.mkdtemp())
    shapes = {}
    for did, kw in (('fake', {}), ('v12', {})):
        desc = dd.load(did)
        acq, got, st = collect(desc, **kw)
        assert got, f'{did} 没有数据'
        b = got[0]
        assert isinstance(b, Block) and b.uv.ndim == 2 and b.uv.shape[1] == desc.n_channels and b.raw.dtype == np.int32 and b.seq.dtype == np.uint32
        assert b.uv.dtype == np.float32 and len(b.raw) == len(b.uv) == len(b.seq)
        gain = np.array(desc.gains())
        assert np.array_equal(b.raw, np.round(b.uv / gain).astype(np.int32)), f'{did} raw≠round(uv/gain)'
        assert st['state'] == 'acquiring' and st['samples'] >= desc.fs_Hz
        seqs = np.concatenate([x.seq for x in got])
        assert np.array_equal(seqs, np.arange(len(seqs), dtype=np.uint32)), f'{did} 样本序号不连续'
        shapes[did] = (b.uv.shape[1], b.raw.dtype, b.seq.dtype)
        print(f'  {did}: {len(got)} 块 {st["samples"]} 帧 dropped={st["dropped"]} state={st["state"]}')
    # replay：先用 fake 录一段存 npz，再回放，形状一致
    desc = dd.load('fake')
    acq, got, st = collect(desc, seconds=1.0)
    uv = np.concatenate([x.uv for x in got])[:2000]
    stem = tmp / 'rest' / 'take'
    stem.parent.mkdir()
    wl8.save(stem, uv, np.zeros((208, 6), np.int16), np.arange(2000, dtype=np.uint8), 'rest', 's', 1, 'fake')
    rd = dd.load('replay')
    acq, got, st = collect(rd, seconds=.5, replay=stem.with_suffix('.npz'))
    assert got and got[0].uv.shape[1] == 8 and got[0].raw.dtype == np.int32 and got[0].seq.dtype == np.uint32
    assert not rd.cap('record')
    print(f'  replay: {len(got)} 块 {st["samples"]} 帧，与 fake/v12 同形状')
    assert len({(v[1], v[2]) for v in shapes.values()}) == 1
    # 录 1 s
    desc = dd.load('fake')
    rig = build_rig(desc)
    acq = AcqHandler(rig, desc)
    acq.start()
    rec = acq.record(1.0)
    rec.mark('go', 'key')
    assert rec.wait(5), '录制 1 s 超时'
    arr = rec.arrays()
    acq.stop()
    assert len(arr['uv']) == 2000 and len(arr['raw']) == 2000 and len(arr['seq']) == 2000, len(arr['uv'])
    assert arr['events'] and arr['events'][0][1] == 'go'
    print(f'  record 1 s → {len(arr["uv"])} 帧，imu {None if arr["imu"] is None else len(arr["imu"])} 行，事件 {arr["events"]}')
    # 必失败
    bad = dd.validate({**dd.load('fake').to_json(), 'id': 'bad', 'decoder': 'cheez', 'n_channels': 1, 'channels': dd.load('cheez').channels, 'fs_Hz': 1000, 'fs_options': [1000]})
    try:
        AcqHandler(build_rig(dd.load('fake')), bad)
        raise AssertionError('描述与 rig 解码器不符却通过了')
    except (ValueError, dd.DescError) as e:
        print(f'  红 ✓ 描述/解码器不符: {str(e)[:50]}')
    try:
        build_rig(dd.load('replay'))
        raise AssertionError('replay 不给文件却建成了')
    except ValueError as e:
        print(f'  红 ✓ replay 缺文件: {e}')
    try:
        AcqHandler(build_rig(dd.load('replay'), replay=stem.with_suffix('.npz')), dd.load('replay')).record(1.0)
        raise AssertionError('replay 不可录却开了录制')
    except PermissionError as e:
        print(f'  红 ✓ replay 不可录: {str(e)[:50]}')
    print('check_rig_adapter: fake / v12 / replay 同形状 Block；录制 1 s = 2000 帧；3 条必失败全红')


if __name__ == '__main__':
    main()

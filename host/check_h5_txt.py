"""段文件门禁（附录 G）：fake 录 1 s → .h5 → .txt 往返逐值相同；头部 JSON 能按 OpenSignals 读法解析；
缺 'sampling rate' 的头必失败；列数与数据不符必失败；门禁对饱和/缺帧数据必红。"""
import json
import sys
import tempfile
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import device_desc as dd
import gates
import osig_txt
import take_file
from rig import AcqHandler, build_rig


def opensignals_style_read(path):
    """照 OpenSignals 官方 python-samples 的读法：第 1 行魔数，第 2 行 '# ' + JSON，第 3 行 EndOfHeader，之后 tab 数字。"""
    lines = Path(path).read_text().splitlines()
    assert lines[0] == osig_txt.MAGIC, lines[0]
    hdr = json.loads(lines[1][2:])
    assert lines[2] == osig_txt.END
    key = next(iter(hdr))
    h = hdr[key]
    data = np.array([[float(v) for v in ln.split('\t')] for ln in lines[3:] if ln.strip()])
    assert data.shape[1] == len(h['column']), (data.shape, h['column'])
    assert data[:, 0].tolist() == list(range(len(data))), 'nSeq 应 0..n-1'
    return h, data


def main():
    tmp = Path(tempfile.mkdtemp())
    desc = dd.load('fake')
    acq = AcqHandler(build_rig(desc), desc)
    acq.start()
    rec = acq.record(1.0)
    rec.mark('cue', 'ui')
    assert rec.wait(5)
    arr = rec.arrays()
    acq.stop()
    meta, d = take_file.new_session(tmp, desc, subject='S01', donning=1, placement='前臂')
    p, gate = take_file.write(d, desc, arr, 'fist', session_meta=meta, seconds=1.0, dropped=acq.dropped)
    assert gate['ok'] and gate['frames'] == 2000, gate
    hdr = take_file.read_header(p)
    for k in ('sampling rate', 'column', 'resolution', 'device', 'x_yuanli', 'date', 'time'):
        assert k in hdr, k
    assert hdr['x_yuanli']['device_id'] == 'fake' and hdr['x_yuanli']['take_label'] == 'fist' and hdr['x_yuanli']['donning'] == 1
    back = take_file.read(p, ('uv', 'raw', 'seq', 'imu'))
    assert back['uv'].shape == (2000, 8) and back['raw'].dtype == np.int32 and back['seq'].dtype == np.uint32 and back['imu'] is not None
    assert take_file.events(p) == [(0.0, 'cue', 'ui')]
    part = take_file.read(p, ('uv',), frm=100, to=300)['uv']
    assert part.shape == (200, 8) and np.array_equal(part, back['uv'][100:300])
    print(f'  h5 {p.name}: uv{back["uv"].shape} raw int32 seq uint32 imu{back["imu"].shape} 事件 1 条，区间读 OK')
    # 往返 .txt（µV 与 raw 各一次）
    t1 = take_file.export_txt(p, tmp / 'a.txt', converted=True)
    h1, d1 = opensignals_style_read(t1)
    assert h1['convertedValues'] == 1 and h1['sampling rate'] == 2000 and h1['column'][2:] == desc.labels()
    assert np.allclose(d1[:, 2:], back['uv'], atol=5e-4), np.abs(d1[:, 2:] - back['uv']).max()
    t0 = take_file.export_txt(p, tmp / 'b.txt', converted=False)
    h0, d0 = opensignals_style_read(t0)
    assert h0['convertedValues'] == 0 and np.array_equal(d0[:, 2:].astype(np.int64), back['raw'].astype(np.int64)), 'raw 往返不逐值相同'
    h2, data2, di2 = osig_txt.read(t0)
    assert np.array_equal(data2.astype(np.int64), back['raw'].astype(np.int64)) and h2 == h0
    # 同一份头：txt 第二行的 JSON 与 h5 attrs['header'] 除 convertedValues 外相同
    assert {k: v for k, v in h1.items() if k != 'convertedValues'} == {k: v for k, v in hdr.items() if k != 'convertedValues'}
    print(f'  txt µV {d1.shape} / raw {d0.shape} 往返逐值相同；头 JSON 与 h5 同一份')
    # 会话清单
    ss, tk = take_file.list_sessions(tmp), take_file.list_takes(tmp)
    assert len(ss) == 1 and ss[0]['n_takes'] == 1 and tk[0]['label'] == 'fist' and tk[0]['gate']['ok']
    # 必失败
    try:
        osig_txt.write(tmp / 'bad.txt', {k: v for k, v in hdr.items() if k != 'sampling rate'}, back['uv'])
        raise AssertionError('缺 sampling rate 的头写成功了')
    except ValueError as e:
        print(f'  红 ✓ 缺 sampling rate: {e}')
    try:
        osig_txt.write(tmp / 'bad2.txt', hdr, back['uv'][:, :5])
        raise AssertionError('列数不符写成功了')
    except ValueError as e:
        print(f'  红 ✓ 列数不符: {e}')
    rail = np.full((2000, 8), desc.limits['rail_uV'], np.float32)
    g = gates.check(desc, rail, seconds=1.0)
    assert not g['ok'] and 'rail' in g['why'].lower() or '饱和' in g['why'], g
    print(f'  红 ✓ 饱和段门禁: {g["why"]}')
    g = gates.check(desc, back['uv'][:1500], seconds=1.0)
    assert not g['ok'], g
    print(f'  红 ✓ 缺帧段门禁: {g["why"]}')
    g = gates.check(desc, back['uv'], seconds=1.0, dropped=50)
    assert not g['ok'], g
    print(f'  红 ✓ 丢块段门禁: {g["why"]}')
    print('check_h5_txt: h5 ↔ txt 往返通过，OpenSignals 读法解析通过，5 条必失败全红')


if __name__ == '__main__':
    main()

"""18 通道腕带端到端（不接实物）：假串口按 2000 帧/秒出 41 字节帧 → build_rig(wl18) 自动找口（排除 8 通道接收器、试读认帧）
→ 采集服务 /api/emg/record 录两条 → 工程 data/emg/emg-wl18-data 里是 n×18、元数据写内置滤波；8 通道目录不被写。

    host/.venv-emg/bin/python host/check_wl18_web.py
"""
import json
import sys
import tempfile
import threading
import time
import urllib.request
from pathlib import Path

import numpy as np
import serial
from serial.tools import list_ports

sys.path.insert(0, str(Path(__file__).resolve().parent))
import device_desc
import emg_web
import wl18
from rig import build_rig

opened = []


class FakeSerial:
    """只有 usbmodemWL18 会出数据；按真实速率放字节，像手环一样一直发。"""
    def __init__(self, device, baud, timeout=None, exclusive=False):
        assert baud == wl18.BAUD, baud
        self.device, self.port, self.dtr, self.rts = device, device, True, True
        if device is not None: self.open()                                 # 和 pyserial 一样：给了口就立刻开

    def open(self):
        self.device = self.port
        opened.append((self.device, self.dtr, self.rts))
        self.t0, self.pos, self.s, self.buf = time.monotonic(), 0, 0, bytearray()
        self.rng = np.random.default_rng(len(opened))

    def __enter__(self): return self
    def __exit__(self, *a): self.close()
    def close(self): pass

    def _fill(self):
        due = int((time.monotonic() - self.t0) * 2000)
        while self.s < due * 1.1 and self.device.endswith('WL18'):          # 每 10 帧 EMG 插 1 帧 IMU
            k = self.s
            self.buf += wl18.emg_frame(k & 0xFF, self.rng.integers(-300, 300, wl18.N_CH) * 7.5) if k % 11 else wl18.imu_frame(k & 0xFF, (0, 0, 0, 0, 0, 16393))
            self.s += 1

    @property
    def in_waiting(self):
        self._fill(); return len(self.buf)

    def read(self, n=1):
        if not self.in_waiting: time.sleep(.005); self._fill()
        out = bytes(self.buf[:n]); del self.buf[:n]; return out


class Port:
    def __init__(self, device, vid, pid=0): self.device, self.vid, self.pid, self.serial_number = device, vid, pid, None


serial.Serial = FakeSerial
list_ports.comports = lambda: [Port('/dev/cu.SLAB_USBtoUART', 0x10C4), Port('/dev/cu.debug-console', None), Port('/dev/cu.usbmodemXIAO', 0x2886, 0x8045), Port('/dev/cu.usbmodemNEW', 0x5555), Port('/dev/cu.usbmodemWL18', 0x1234)]


def call(port, path, body=None):
    req = urllib.request.Request(f'http://127.0.0.1:{port}{path}', data=json.dumps(body).encode() if body is not None else None,
                                 headers={'Content-Type': 'application/json', 'X-Mako-Collector': '1', 'X-Mako-Project': 'p18'}, method='POST' if body is not None else 'GET')
    with urllib.request.urlopen(req, timeout=10) as r: return r.status, json.loads(r.read())


desc = device_desc.load('wl18')
rig = build_rig(desc)
assert type(rig) is wl18.Wl18Rig and rig.link_state() == 'waiting-band', rig.link_state()     # 有候选口、还没开
with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    sets = {k: {kind: root / 'data' / 'emg' / p.name for kind, p in v.items()} for k, v in emg_web.SETS.items()}
    session = emg_web.Session(rig, sets, model_root=root / 'models', project={'id': 'p18', 'name': 'p18'}, desc=desc)
    srv = emg_web.server_for(session, 0); port = srv.server_port
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    assert call(port, '/api/emg/record', {'label': 'rest', 'count': 2, 'countdown': 0, 'seconds': 1})[0] == 202
    for _ in range(400):
        st = call(port, '/api/emg/state')[1]
        if not st.get('busy'): break
        time.sleep(.05)
    rs = st['rig']
    assert rs['kind'] == 'wl18' and rs['link'] == 'streaming' and rs['port'] == '/dev/cu.usbmodemWL18' and rs['banner'].startswith('WaveleTech 18ch'), rs
    names = [d for d, *_ in opened]
    assert not {'/dev/cu.SLAB_USBtoUART', '/dev/cu.debug-console', '/dev/cu.usbmodemXIAO'} & set(names), ('8 通道接收器 / 无厂商号 / 已知别的设备不该被打开', opened)
    assert opened[0] == ('/dev/cu.usbmodemNEW', False, False) and opened[1] == ('/dev/cu.usbmodemWL18', False, False), ('试读前要关 DTR/RTS', opened)
    files = sorted((root / 'data' / 'emg' / 'emg-wl18-data' / 'rest').glob('*.npz'))
    assert len(files) == 2, (files, st.get('log'))
    for f in files:
        with np.load(f) as z: assert z['emg_uv'].shape[1] == 18 and len(z['emg_uv']) >= 2000 and z['emg_uv'].dtype == np.float32, z['emg_uv'].shape
        m = json.loads(f.with_suffix('.json').read_text())
        assert m['sensor'] == 'WaveleTech 18ch wired 2k' and m['builtin_filter'] is True and len(m['emg_uv_rms']) == 18, m
        assert 150 < max(m['emg_uv_rms']) < 200, m['emg_uv_rms']                 # ±300 µV 均匀分布 RMS ≈ 173
    assert not (root / 'data' / 'emg' / 'emg-wl8-data').exists(), '18 通道样本不能进 8 通道目录'
    for bad in (lambda: session.wl8_train_start(), lambda: session.live8_action({'action': 'start'})):    # 必须失败：训练 / 实时识别还按 8 路写
        try: bad()
        except ValueError as e: assert '8 路' in str(e)
        else: raise AssertionError('18 通道进了 8 路训练 / 识别')
    assert st['counts']['train'] == {'rest': 2}, st['counts']
    srv.shutdown(); rig.streaming = False
print('wl18 web check passed: 自动找口（跳过 CP210x / 无厂商号 / XIAO，试读关 DTR/RTS，不出帧的口不选）、HTTP 录 2 条 n×18 到 emg-wl18-data、元数据带内置滤波')

"""唯理 18 通道 EMG 腕带（有线 USB 虚拟串口，2 Mbps）串口解析与录制。

协议来自 vendor/waveletech/唯理-18通道EMG腕带-硬件说明书v1.5.pdf，官方上位机的做法（说明书 PDF 和 exe 在本机 vendor/waveletech/，不入库）。
接线：主机两个 Type-C，一个只充电、一个只通信（USB CDC）；说明书不推荐边充边采。
帧格式（帧头、类型、共用包序号和 8 通道版一样，见 wl8.py）：
  内置滤波打开（开机默认）：41 字节 = D2 D2 D2 + AA/BB + 序号 + 36 字节载荷；AA：18 路 × int16 大端，读数 ÷ 7.5 = µV。
  内置滤波关闭（发 SetFilterEN-0）：59 字节，载荷 54 字节；AA：18 路 × int24 大端，读数 ÷ 60 = µV。
  BB 两种帧长都一样：温度(0.01 ℃) + gyro xyz + acc xyz（int16）+ 电压 mV + 电量 % + 8 字节毫秒时间戳，其余补 0。
同步：照官方上位机，当前位置和往后一帧（41 或 59 字节）处都要是 D2 D2 D2 AA/BB 才认一帧，比只看 3 字节帧头更不容易错同步。
代价：最后一帧要等下一帧到了才能确认（延迟 0.5 ms）。

    python3 wl18.py --check                  # 说明书截图里的真实字节 + 合成字节流，秒级
    python3 wl18.py --seconds 5 [--port X]   # 录 5 秒到 emg-wl18-raw/<时间>.npz，打印丢包/采样率
"""
import argparse
import json
import math
import struct
import time
from pathlib import Path

import numpy as np

import wl8

SYNC, EMG, IMU = wl8.SYNC, wl8.EMG, wl8.IMU
N_CH, BAUD, EMG_HZ = 18, 2_000_000, 2000
BYTES_PER_CH = {41: 2, 59: 3}                      # 帧长 → 每路字节数（滤波开 / 关）
UV_PER_COUNT = {41: 1 / 7.5, 59: 1 / 60}
RAIL_UV = {41: (1 << 15) / 7.5 * .98, 59: (1 << 23) / 60 * .98}     # 满量程的 98% 算饱和
GYRO_SCALE = .07 * math.pi / 180                   # 70 mdps/LSB（±2000 dps 默认量程）→ rad/s
ACC_SCALE = .061e-3 * 9.80665                      # 0.061 mg/LSB（±2 g 默认量程）→ m/s²


def _head(buf, k):
    return buf[k:k + 3] == SYNC and k + 3 < len(buf) and buf[k + 3] in (EMG, IMU)


def decode(buf, kinds=False, sizes=False):
    """bytes → (emg float32 (n,18) µV, imu int16 (m,6), seq uint8 (n+m,) 到达顺序的共用序号, [kinds], [sizes], 没拼完的尾巴)。
    kinds=True 在尾巴前插入每帧类型；sizes=True 再插入每帧帧长（41 = 内置滤波开，59 = 关）。"""
    emg, imu, seq_all, kind_all, size_all = [], [], [], [], []
    i, n = 0, len(buf)
    while True:
        j = buf.find(SYNC, i)
        if j < 0 or j + 4 > n:
            break
        if buf[j + 3] not in (EMG, IMU):
            i = j + 1; continue
        # 先看 41 再看 59；看不了（字节没到）就停下，等下一块
        if j + 45 > n:
            break
        if _head(buf, j + 41):
            size = 41
        elif j + 63 > n:
            break
        elif _head(buf, j + 59):
            size = 59
        else:
            i = j + 1; continue
        kind, payload, w = buf[j + 3], buf[j + 5:j + size], BYTES_PER_CH[size]
        if kind == EMG:
            emg.append([int.from_bytes(payload[k:k + w], 'big', signed=True) * UV_PER_COUNT[size] for k in range(0, N_CH * w, w)])
        else:
            imu.append(struct.unpack('>6h', payload[2:14]))
        seq_all.append(buf[j + 4]); kind_all.append(kind); size_all.append(size)
        i = j + size
    tail = buf[i:] if (j := buf.find(SYNC, i)) < 0 else buf[j:]
    out = [np.array(emg, np.float32).reshape(-1, N_CH), np.array(imu, np.int16).reshape(-1, 6), np.array(seq_all, np.uint8)]
    if kinds: out.append(np.array(kind_all, np.uint8))
    if sizes: out.append(np.array(size_all, np.uint16))
    return (*out, tail)


def frame(kind, seq, payload):
    return SYNC + bytes([kind, seq]) + payload


def emg_frame(seq, counts, size=41):
    w = BYTES_PER_CH[size]
    return frame(EMG, seq, b''.join(int(v).to_bytes(w, 'big', signed=True) for v in counts))


def imu_frame(seq, six, size=41, battery=100):
    body = struct.pack('>h6hHB', 2530, *six, 4000, battery)          # 温度 25.30 ℃、电压 4000 mV
    return frame(IMU, seq, body + bytes(size - 5 - len(body)))


def find_port(explicit=None, ports=None, probe=True):
    """说明书没给 USB 厂商号，只能逐个试：排除 8 通道版的 CP210x / CH343 接收器，剩下有厂商号的口里，
    以 2 Mbps 读 0.3 秒、能解出 20 帧以上的就是。probe=False 只看有没有候选口（状态轮询用，不去开别人的口）。"""
    # ponytail: 逐口试读；拿到实物的 USB 厂商号后改成按厂商号过滤，不再打开别的设备
    if ports is None:
        from serial.tools import list_ports
        ports = list_ports.comports()
    if explicit:
        hits = [p for p in ports if p.device == explicit]
    else:
        hits = [p for p in ports if p.vid is not None and not any(p.vid == v and pid in (None, p.pid) for v, pid in (*wl8.RECEIVERS, *NOT_WL18))]
        if probe:
            hits = [p for p in hits if _probe(p.device)]
    if not hits:
        raise wl8.NoReceiver('没找到唯理 18 通道腕带：用随附的 Type-C 数据线插手环的通信口（不是充电口），开机后再试；或用 --serial 指定')
    return hits[0]


# 本仓已知的别的设备：单通道 Cheez 板的 CH340、Seeed XIAO（R01 台架 / V12），不去试开
NOT_WL18 = ((0x1A86, 0x7523), (0x2886, None))


def _probe(device, seconds=.3):
    import serial
    try:
        conn = serial.Serial(None, BAUD, timeout=.05, exclusive=True)
        conn.port, conn.dtr, conn.rts = device, False, False             # 先关 DTR/RTS 再开口：带自动复位电路的板子不会被试读弄重启
        conn.open()
        with conn:
            got, t0 = b'', time.monotonic()
            while time.monotonic() - t0 < seconds:
                got += conn.read(4096)
    except (serial.SerialException, OSError):
        return False
    return len(decode(got)[2]) >= 20


class Wl18Rig(wl8.Wl8Rig):
    """和 Wl8Rig 同一条读线程 / 订阅 / take 链路，只换解码、串口参数和饱和阈值。"""
    kind = 'wl18'
    n_ch, baud, sensor = N_CH, BAUD, 'WaveleTech 18ch wired 2k'
    gyro_scale, acc_scale = GYRO_SCALE, ACC_SCALE
    scans_ports = True
    frame_len = 41                                                          # 最近一帧的帧长：41 = 内置滤波开（开机默认）

    @staticmethod
    def find(explicit=None, ports=None, probe=True):
        return find_port(explicit, ports, probe)

    def _receiver_present(self):
        try:
            self.find(self.port_hint, self._port_snapshot(), probe=False)
            return True
        except wl8.NoReceiver:
            return False

    def decode(self, buf, kinds=False):
        *out, size, tail = decode(buf, kinds=kinds, sizes=True)
        if len(size): self.frame_len = int(size[-1])
        return (*out, tail)

    @property
    def rail_uv(self):
        return RAIL_UV[self.frame_len]

    def meta(self):
        return dict(super().meta(), builtin_filter=self.frame_len == 41)


def record(seconds, port=None, out=Path('emg-wl18-raw'), label=''):
    import serial
    dev = find_port(port)
    chunks = []
    with serial.Serial(dev.device, BAUD, timeout=.2, exclusive=True) as conn:
        conn.read(4096)                                                     # 同 wl8.record：不 reset_input_buffer，丢第一块
        t0 = time.monotonic()
        while time.monotonic() - t0 < seconds:
            if b := conn.read(4096):
                chunks.append(b)
    elapsed = time.monotonic() - t0
    emg, imu, seq, size, _ = decode(b''.join(chunks), sizes=True)
    report = wl8.stats(emg, imu, seq, elapsed)
    report['frame_len'] = sorted({int(v) for v in size})
    out.mkdir(exist_ok=True)
    stem = out / time.strftime('%Y%m%d-%H%M%S')
    np.savez_compressed(stem.with_suffix('.npz'), emg_uv=emg, imu=imu, seq=seq, emg_hz=EMG_HZ, gyro_scale=GYRO_SCALE, acc_scale=ACC_SCALE, label=label)
    stem.with_suffix('.json').write_text(json.dumps(dict(sensor=Wl18Rig.sensor, port=dev.device, label=label,
                                                          recordedAt=time.strftime('%Y-%m-%dT%H:%M:%S'), **report), indent=2) + '\n')
    return stem, report


# 说明书 v1.5 第 6 页串口助手截图（滤波开，静止）：序号 59、5A、5B，5A 是 BB 包
MANUAL_41 = """D2 D2 D2 AA 59 35 CB EE 1E EA 46 E0 8F F0 56 EA FB 38 7F 28 3C D2 FF 14 1C 1F 80 58 50 0A CF 3A BA 08 2E 03 2E 8C 32 19 63
D2 D2 D2 BB 5A 01 6E 00 00 FF FC FF FD 05 99 2F B4 29 7C 13 89 64 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
D2 D2 D2 AA 5B 3E 76 F1 83 EB 85 E3 A3 F2 6F F1 9B 2F 78 27 F0 D4 4C 15 3F 20 C8 6A 1A 06 54 3B 9B 05 2C F7 FD 6B C5 E1 9E"""


def check():
    import queue
    import threading
    # 1. 说明书真实字节：序号连续、手环静止时 |a| ≈ 1 g、第 1 路 0x35CB ÷ 7.5。最后一帧没有下一帧头确认，留在尾巴里
    raw = bytes.fromhex(MANUAL_41.replace('\n', ' '))
    emg, imu, seq, tail = decode(raw + raw[:4])
    assert emg.shape == (2, 18) and imu.shape == (1, 6) and seq.tolist() == [0x59, 0x5A, 0x5B] and tail == raw[:4], (emg.shape, imu.shape, seq, tail)
    assert abs(emg[0, 0] - 0x35CB / 7.5) < 1e-3 and abs(emg[0, 1] - (0xEE1E - 65536) / 7.5) < 1e-3
    g = float(np.linalg.norm(imu[0, 3:].astype(np.float64)) * ACC_SCALE)
    assert 9.6 < g < 10.0 and tuple(imu[0, :3]) == (0, -4, -3), (g, imu[0])
    assert len(decode(raw)[0]) == 1, '最后一帧没有下一帧头，不该被认'
    # 2. 合成：两种帧长各 1 秒，中间切换（模拟发 SetFilterEN-0）；开头有垃圾，序号跨过 255
    rng = np.random.default_rng(0)
    t41, t59 = rng.integers(-32768, 32768, (2000, N_CH)), rng.integers(-(1 << 23), 1 << 23, (2000, N_CH))
    stream, s = bytearray(b'\x00\xd2\xd2\xd2'), 0
    for size, truth in ((41, t41), (59, t59)):
        for k, row in enumerate(truth):
            stream += emg_frame(s & 0xFF, row, size); s += 1
            if k % 10 == 0:
                stream += imu_frame(s & 0xFF, (1, -2, 3, -4, 5, -6), size); s += 1
    stream = bytes(stream) + emg_frame(s & 0xFF, np.zeros(N_CH, int))           # 收尾帧：让最后一帧真帧能被确认
    emg, imu, seq, kinds, size, tail = decode(stream, kinds=True, sizes=True)
    want = np.vstack([t41 / 7.5, t59 / 60]).astype(np.float32)
    assert emg.shape == (4000, N_CH) and np.allclose(emg, want, rtol=0, atol=1e-3), 'int16/int24 解码错'
    assert imu.shape == (400, 6) and tuple(imu[0]) == (1, -2, 3, -4, 5, -6) and wl8.dropped(seq) == 0
    assert set(size[:2200].tolist()) == {41} and set(size[2200:].tolist()) == {59}, '帧长切换处认错'
    assert len(tail) == 41
    # 3. 必须失败：丢 3 帧 → 丢包 3；载荷里伪造一个帧头 → 双帧头确认挡住，不多出帧
    fr = [stream[4 + 41 * i:4 + 41 * (i + 1)] for i in range(300)]
    assert wl8.dropped(decode(b''.join(fr[:100] + fr[103:]))[2]) == 3
    fake = bytearray(fr[0]); fake[10:14] = SYNC + bytes([EMG])                 # 第 1 帧载荷中间藏一个 D2 D2 D2 AA，从它前面开始读
    e5, _, q5, _ = decode(bytes(fake[6:]) + b''.join(fr[1:50]))
    assert len(q5) == 48 and q5[0] == fr[1][4], ('伪帧头被当成帧', len(q5))
    bad = bytearray(b''.join(fr[:50])); bad[41 + 3] = 0xCC                      # 第 2 帧类型字节坏：第 1、2 帧都丢（第 1 帧没了确认），其余照解
    assert len(decode(bytes(bad))[2]) == 47
    # 4. Wl18Rig 走 Wl8Rig 的同一条 _feed / take：小块喂、take 存 n×18、元数据写帧长与内置滤波
    rig = Wl18Rig(); got = []
    rig.frame_subscribers.append(got.append)
    for i in range(0, len(stream), 97): rig._feed(stream[i:i + 97])
    assert np.vstack(got).shape == (4000, N_CH) and rig.frame_len == 59 and rig.rail_uv == RAIL_UV[59]

    class Dev: device = 'fake-wl18'
    class Conn:                                                             # 按 2000 帧/秒放字节，像真串口
        def __init__(c, data): c.data, c.pos, c.t0 = data, 0, time.monotonic()
        @property
        def in_waiting(c): return max(0, min(len(c.data), int((time.monotonic() - c.t0) * 2200 * 41)) - c.pos)
        def read(c, n):
            if not c.in_waiting: time.sleep(.005)
            b = c.data[c.pos:c.pos + n]; c.pos += len(b); return b
    one, s = bytearray(), 0
    for k, row in enumerate(rng.integers(-300, 300, (2400, N_CH)) * 7.5):    # 1.2 秒、±300 µV
        one += emg_frame(s & 0xFF, row); s += 1
        if k % 10 == 0: one += imu_frame(s & 0xFF, (0, 0, 0, 0, 0, 16393)); s += 1
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        rig = Wl18Rig(); rig.conn, rig.device, rig.streaming = Conn(bytes(one)), Dev(), True
        threading.Thread(target=rig._pump, daemon=True).start()
        time.sleep(.05)
        r = rig.take('rest', None, Path(tmp), 'check', 1, seconds=1)
        rig.streaming = False
        f = next((Path(tmp) / 'rest').glob('*.npz'))
        with np.load(f) as z: assert z['emg_uv'].shape[1] == N_CH and z['emg_uv'].dtype == np.float32 and float(z['gyro_scale']) == GYRO_SCALE
        m = json.loads(f.with_suffix('.json').read_text())
        assert m['sensor'] == Wl18Rig.sensor and m['builtin_filter'] is True and len(m['emg_uv_rms']) == N_CH, m
        assert 2000 <= r['frames'] <= 2400, r                                # take 收 span + 0.1 秒
        # 必须失败：饱和阈值跟帧长走；41 帧下 5000 µV（超过 16 位满量程 4369）算饱和
        try: wl8.validate(np.full((2000, N_CH), 5000.), np.arange(2000) % 256, 1, rig.rail_uv)
        except ValueError as e: assert '饱和' in str(e)
        else: raise AssertionError('41 帧饱和没拦住')
    # 5. 找口：排除 8 通道接收器；不试读时只要有候选口就算在
    class P:
        def __init__(p, dev, vid, pid=0): p.device, p.vid, p.pid = dev, vid, pid
    ports = [P('/dev/cu.SLAB', 0x10C4), P('/dev/cu.wch', 0x1A86, 0x55D3), P('/dev/cu.Bluetooth', None), P('/dev/cu.usbmodem1', 0x1234)]
    assert find_port(ports=ports, probe=False).device == '/dev/cu.usbmodem1'
    try: find_port(ports=ports[:3], probe=False)
    except wl8.NoReceiver: pass
    else: raise AssertionError('只有 8 通道接收器时不该当成 18 通道')
    print('wl18 check passed: 说明书 3 帧（|a|=%.2f m/s²）、41/59 各 2000 帧与中途切换、伪帧头被挡、丢包 3、take 存 n×18 与元数据' % g)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--check', action='store_true'); p.add_argument('--seconds', type=float, default=5)
    p.add_argument('--port'); p.add_argument('--label', default='')
    a = p.parse_args()
    if a.check:
        check()
    else:
        stem, report = record(a.seconds, a.port, label=a.label)
        print(stem, json.dumps(report, ensure_ascii=False))

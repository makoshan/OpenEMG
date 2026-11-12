"""唯理 8 通道 EMG 腕带（有线 2 kSPS 版）串口解析与录制。

帧格式来自商品说明书（卖家 2026-09-24 确认没有别的文档；8 通道版没有内置滤波）。
接线（卖家 2026-09-29）：黑色主机上的 Type-C 只充电；通信走主机引出的灰白线的白色头，接收芯片是 CP2102 或 CH343。
绿灯闪 = 连接成功。先充 30 min，别用快充。基线和工频要自己去除（18 通道版才内置滤波）。
佩戴（卖家「佩戴方式」图）：右手，戴在手腕紧贴手掌根处（不是前臂中段），主机在手背侧；电源开关和指示灯朝小指一侧、朝手肘方向。
表带内侧 8 根金属棒、每根两端各一个触点（看起来是 8 对双极电极）；参考/偏置电极在哪，卖家还没回答。
防工频：采集时笔记本拔掉电源适配器；白线别拖在桌面/地上、别碰其他电器、动作时别扯到，悬空或贴在身上。
帧格式：
921600 8N1，每包 29 字节 = 头 D2 D2 D2 + 类型 (AA=EMG / BB=IMU) + 包序号 (0x00–0xFF 循环) + 24 字节载荷。
AA 载荷：8 通道 × 3 字节有符号 24 bit 大端，单位 µV。
BB 载荷：2 字节未说明 + gr_x gr_y gr_z acc_x acc_y acc_z 各 int16 大端，其余补 0；×0.0012 = rad/s，×0.0005978 = m/s²。
AA、BB 共用一个包序号（2026-09-29 卖家 XCOM 截图：8B AA、8C BB、8D AA…），丢包只能按到达顺序的合并序号算。

    python3 wl8.py --check                      # 合成字节流，秒级
    python3 wl8.py --seconds 5                  # 录 5 秒到 emg-wl8-raw/<时间>.npz，打印丢包/采样率
"""
import argparse
import json
import os
import struct
import time
from pathlib import Path

import numpy as np

FRAME, SYNC = 29, b'\xd2\xd2\xd2'
EMG, IMU = 0xAA, 0xBB
BAUD, EMG_HZ = 921600, 2000
GYRO_SCALE, ACC_SCALE = .0012, .0005978          # counts -> rad/s, m/s^2 (说明书)
RECEIVERS = ((0x10C4, None), (0x1A86, 0x55D3))   # 说明书写 CP2102；2026-09-29 实到的接收器是 CH343（单通道板是 CH340 0x7523，不冲突）
LINK_FRESH_S = 1.0                                 # 最近 1 秒内有帧才算 streaming；更久没帧是 waiting-band
REWEAR_GAP_S = 30.0                                # 断流这么久后再出数据，当作手环可能摘下重戴过：link_since 刷新，App 识别页据此提醒先重新校准（2026-10-16 道指剑认成破邪印）


class NoReceiver(RuntimeError):
    """找不到接收器串口。数据流用它的 code 回 503，而不是把连接掐掉。"""
    code = 'no-receiver'


def decode(buf, kinds=False):
    """bytes -> (emg int32 (n,8) µV, imu int16 (m,6), seq uint8 (n+m,) shared counter in arrival order, leftover bytes).
    kinds=True inserts, before the leftover, the packet type (0xAA / 0xBB) of every frame in arrival order.
    Resyncs on the 3-byte header; a bad type byte skips one byte and searches again."""
    emg, imu, seq_all, kind_all = [], [], [], []
    i, n = 0, len(buf)
    while True:
        j = buf.find(SYNC, i)
        if j < 0 or j + FRAME > n:
            break
        kind, seq, payload = buf[j + 3], buf[j + 4], buf[j + 5:j + FRAME]
        if kind == EMG:
            emg.append([int.from_bytes(payload[k:k + 3], 'big', signed=True) for k in range(0, 24, 3)])
        elif kind == IMU:
            imu.append(struct.unpack('>6h', payload[2:14]))
        else:
            i = j + 1; continue
        seq_all.append(seq); kind_all.append(kind)
        i = j + FRAME
    tail = buf[i:] if (j := buf.find(SYNC, i)) < 0 else buf[j:]
    out = (np.array(emg, np.int32).reshape(-1, 8), np.array(imu, np.int16).reshape(-1, 6), np.array(seq_all, np.uint8))
    return (*out, np.array(kind_all, np.uint8), tail) if kinds else (*out, tail)


def dropped(seq):
    """Packets lost according to a uint8 rolling counter (0 when every step is +1)."""
    if len(seq) < 2:
        return 0
    return int(((np.diff(seq.astype(np.int16)) - 1) % 256).sum())


def ac_rms(emg):
    # 先减每路均值再算 RMS：电极直流偏置有几十 mV，不减掉显示的就是偏置而不是肌电幅度。
    x = emg.astype(np.float64)
    return np.sqrt(((x - x.mean(0)) ** 2).mean(0))


def stats(emg, imu, seq, seconds):
    return dict(emg_frames=int(len(emg)), imu_frames=int(len(imu)), seconds=round(seconds, 3),
                emg_hz=round(len(emg) / seconds, 1) if seconds else None,
                imu_hz=round(len(imu) / seconds, 1) if seconds else None,
                dropped=dropped(seq),
                emg_uv_rms=[round(float(v), 1) for v in ac_rms(emg)] if len(emg) else None)


def find_port(explicit=None, ports=None):
    if ports is None:
        from serial.tools import list_ports
        ports = list_ports.comports()
    hits = [p for p in ports if p.device == explicit] if explicit else [p for p in ports if any(p.vid == v and pid in (None, p.pid) for v, pid in RECEIVERS)]
    if not hits:
        raise NoReceiver('没找到唯理接收器串口（CP210x 或 CH343 0x55D3）；插上接收器，或用 --port 指定')
    return hits[0]


def record(seconds, port=None, out=Path('emg-wl8-raw'), label=''):
    import serial
    dev = find_port(port)
    chunks, t0 = [], None
    # AGENTS.md rule 5: never reset_input_buffer(); read and discard the first chunk instead.
    with serial.Serial(dev.device, BAUD, timeout=.2, exclusive=True) as conn:
        conn.read(4096)
        t0 = time.monotonic()
        while time.monotonic() - t0 < seconds:
            b = conn.read(4096)
            if b:
                chunks.append(b)
    elapsed = time.monotonic() - t0
    emg, imu, seq, _ = decode(b''.join(chunks))
    report = stats(emg, imu, seq, elapsed)
    out.mkdir(exist_ok=True)
    stem = out / time.strftime('%Y%m%d-%H%M%S')
    np.savez_compressed(stem.with_suffix('.npz'), emg_uv=emg, imu=imu, seq=seq,
                        emg_hz=EMG_HZ, gyro_scale=GYRO_SCALE, acc_scale=ACC_SCALE, label=label)
    stem.with_suffix('.json').write_text(json.dumps(dict(sensor='WaveleTech 8ch wired 2k', port=dev.device, label=label,
                                                          recordedAt=time.strftime('%Y-%m-%dT%H:%M:%S'), **report), indent=2) + '\n')
    return stem, report


def _frame(kind, seq, payload):
    return SYNC + bytes([kind, seq]) + payload


# First six rows of the seller's XCOM capture (2026-09-29, wristband at rest): seq 8B..90 with one BB at 8C.
XCOM_ROWS = """D2 D2 D2 AA 8B FF FD 05 FF FC 6F FF FC D8 FF FC 52 FF FC DC FF FB 55 FF FE 4A FF FE 17
D2 D2 D2 BB 8C 02 68 00 01 FF FD 00 02 CC 18 F6 5D 25 07 00 00 00 00 00 00 00 00 00 00
D2 D2 D2 AA 8D FF FD 22 FF FC A0 FF FC D7 FF FC 45 FF FC C6 FF FB 3E FF FE 48 FF FE 1D
D2 D2 D2 AA 8E FF FD 40 FF FC DC FF FC EC FF FC 40 FF FC BA FF FB 34 FF FE 5F FF FE 4F
D2 D2 D2 AA 8F FF FD 66 FF FD 2C FF FD 1C FF FC 50 FF FC C1 FF FB 58 FF FE BB FF FE D7
D2 D2 D2 AA 90 FF FD 85 FF FD 8D FF FD 8C FF FC A8 FF FD 23 FF FC 24 FF FE EA 00 00 D5"""


def read_available(conn):
    """有多少读多少：in_waiting 有数据就全取，没有就阻塞等 1 字节（受 timeout 限制）。
    以前 read(4096) 要攒满 4096 字节才返回，约 64 ms 一批，光标每秒只更新约 16 次（2026-10-03 实测 SSE 包间隔中位 64 ms）。"""
    return conn.read(max(1, conn.in_waiting))


def check():
    # Real bytes: shared counter has no gap; a wristband at rest reads ~9.8 m/s² (the old 2-byte-early IMU offset gave 8.1).
    emg, imu, seq, tail = decode(bytes.fromhex(XCOM_ROWS.replace('\n', ' ')))
    assert emg.shape == (5, 8) and imu.shape == (1, 6) and tail == b''
    assert dropped(seq) == 0, 'AA/BB share one counter'
    assert tuple(emg[0]) == (-763, -913, -808, -942, -804, -1195, -438, -489), emg[0]
    g = float(np.linalg.norm(imu[0, 3:].astype(np.float64)) * ACC_SCALE)
    assert 9.6 < g < 10.0 and tuple(imu[0, :3]) == (1, -3, 2), (g, imu[0])
    rng = np.random.default_rng(0)
    # 2000 EMG frames (1 s) with a known ramp, IMU after every 10th; the shared counter rolls past 255.
    truth = rng.integers(-8_000_000, 8_000_000, (2000, 8))           # 24-bit signed range
    stream, s = b'', 0
    for k, row in enumerate(truth):
        stream += _frame(EMG, s & 0xFF, b''.join(int(v).to_bytes(3, 'big', signed=True) for v in row)); s += 1
        if k % 10 == 0:
            stream += _frame(IMU, s & 0xFF, bytes(2) + struct.pack('>6h', 1, -2, 3, -4, 5, -6) + bytes(10)); s += 1
    emg, imu, seq, tail = decode(b'\x00\x17' + stream)              # leading garbage before the first sync
    assert emg.shape == (2000, 8) and (emg == truth).all(), 'signed 24-bit decode wrong'
    # 小块读取：同一段字节按 1–200 字节的随机碎片经 read_available + _feed 送进去，结果必须和整段一次解码一样
    class _Conn:
        def __init__(s, data): s.data, s.pos = data, 0
        @property
        def in_waiting(s): return min(len(s.data) - s.pos, int(rng.integers(0, 200)))
        def read(s, n): b = s.data[s.pos:s.pos + n]; s.pos += len(b); return b
    rig = Wl8Rig.__new__(Wl8Rig); rig.buf, rig.capturing, rig.frames, rig.t_ms, rig.page_buf = b'', None, [], 0, np.zeros((0, 8), np.int32); rig.link_since = rig.last_frame_wall = None
    page = queue.Queue(); rig.subscribers = [page]
    rig.chunk_subscribers, got_e, got_i, reads = [], [], [], 0
    rig.frame_subscribers, rig.imu_subscribers = [got_e.append], [got_i.append]
    conn = _Conn(b'\x00\x17' + stream)
    while conn.pos < len(conn.data): rig._feed(read_available(conn)); reads += 1
    ce, ci = np.vstack(got_e), np.vstack(got_i)
    assert ce.shape == (2000, 8) and (ce == truth).all() and ci.shape == (200, 6) and rig.buf == b'', ('碎片读取解码不一致', ce.shape, ci.shape, len(rig.buf))
    assert reads > len(conn.data) // 200, ('没按小块读', reads)
    lines = [page.get_nowait() for _ in range(page.qsize())]
    assert lines == page_lines(truth, 0) and rig.t_ms == 1000, ('页面文本行在小块读取下丢了或错位', len(lines), len(page_lines(truth, 0)), rig.t_ms)
    cut = _Conn(stream[:-7]); rig.buf, rig.page_buf = b'', np.zeros((0, 8), np.int32); got_e.clear()   # 末尾半帧：留在缓冲里，不丢不错
    while cut.pos < len(cut.data): rig._feed(read_available(cut))
    assert len(rig.buf) == 29 - 7 and np.vstack(got_e).shape[0] in (1999, 2000), (len(rig.buf), np.vstack(got_e).shape)
    assert imu.shape == (200, 6) and tuple(imu[0]) == (1, -2, 3, -4, 5, -6)
    assert dropped(seq) == 0 and tail == b''
    # Must fail: drop frames 100..102 -> 3 lost; corrupt one type byte -> that frame skipped, rest still decoded.
    frames = [stream[i:i + FRAME] for i in range(0, len(stream), FRAME)]
    _, _, seq2, _ = decode(b''.join(frames[:100] + frames[103:]))
    assert dropped(seq2) == 3, dropped(seq2)
    bad = bytearray(stream); bad[3] = 0xCC
    e3, _, _, _ = decode(bytes(bad))
    assert len(e3) == 1999 and (e3[0] == truth[1]).all(), 'corrupt frame not skipped cleanly'
    # A frame cut in half at the end must come back as leftover, not as a wrong sample.
    e4, _, _, tail4 = decode(stream[:FRAME * 5 + 10])
    assert len(e4) == 4 and len(tail4) == 10          # first 5 frames = 1 EMG + 1 IMU + 3 EMG
    # A read holding only BB frames must still reach IMU subscribers (the old _feed returned early without EMG).
    rig, got = Wl8Rig(), []
    rig.imu_subscribers.append(lambda m: got.append(len(m)))
    rig._feed(_frame(IMU, 7, bytes(2) + struct.pack('>6h', 0, 0, 0, 0, 0, 16410) + bytes(10)) * 3)
    assert got == [3], f'BB-only chunk lost: {got}'
    # kinds=True keeps arrival order of packet types: the XCOM rows are AA BB AA AA AA AA.
    *_, k, _ = decode(bytes.fromhex(XCOM_ROWS.replace('\n', ' ')), kinds=True)
    assert k.tolist() == [EMG, IMU, EMG, EMG, EMG, EMG], k
    rig2, got2 = Wl8Rig(), []
    rig2.chunk_subscribers.append(lambda e, m, q, kk, t: got2.append((len(e), len(m), len(q), kk.tolist(), t > 0)))
    rig2._feed(bytes.fromhex(XCOM_ROWS.replace('\n', ' ')))
    assert got2 == [(5, 1, 6, [EMG, IMU, EMG, EMG, EMG, EMG], True)], got2
    # 回放：真实字节录音 → 重新编码 → 同一条 _feed 链路，数据一致；回放拒绝录制
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        f = Path(tmp) / 'r.npz'; e0 = rng.integers(-500, 500, (400, 8)); m0 = rng.integers(-9, 9, (40, 6))
        np.savez(f, emg_uv=e0, imu=m0)
        rr, got3 = ReplayWl8Rig(f, loop=False), []
        rr.frame_subscribers.append(got3.append); rr._feed(rr.stream)
        back = np.concatenate(got3); assert back.shape == (400, 8) and (back == e0).all(), 'replay changed the data'
        assert rr.status()['replay'] == 'r.npz' and rr.banner.startswith('回放')
        try: rr.take('rest', None, None, None, 1)
        except ValueError: pass
        else: raise AssertionError('回放模式居然能录制')
    assert clip_seconds(1) == 1 and clip_seconds(5) == 5
    for bad in (0, 6, True, 2.5):
        try: clip_seconds(bad)
        except ValueError: continue
        raise AssertionError(f'坏时长没被拒绝 {bad!r}')
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        short = FakeWl8Rig().take('finger_rest', 'high', root, 'check', 1, seconds=1)
        full = FakeWl8Rig().take('rest', 'high', root, 'check', 1)
        assert 1900 <= short['frames'] <= 2100, short
        assert full['frames'] >= 3800, full
        assert [json.loads(f.read_text())['seconds'] for f in (root / 'finger_rest').glob('*.json')] == [1], '元数据单次时长没写成实际的 1 秒'
        FakeWl8Rig().take('pinch', 'high', root, 'check', 1, seconds=1, strap_hole=4)
        assert [json.loads(f.read_text())['strap_hole'] for f in (root / 'pinch').glob('*.json')] == [4], '织带孔位没写进元数据'
        assert [json.loads(f.read_text())['strap_hole'] for f in (root / 'rest').glob('*.json')] == [None], '没填织带孔位时应记为 null'
        FakeWl8Rig().take('fist', 'high', root, 'check', 1, seconds=1, cable_dir='palm', ch0_site='ulnar')
        assert [(m['cable_dir'], m['ch0_site']) for m in (json.loads(f.read_text()) for f in (root / 'fist').glob('*.json'))] == [('palm', 'ulnar')], '戴法没写进元数据'
        assert [(m['cable_dir'], m['ch0_site']) for m in (json.loads(f.read_text()) for f in (root / 'rest').glob('*.json'))] == [(None, None)], '没填戴法时应记为 null'
    print('wl8 check passed: XCOM capture (shared seq, |a|=%.2f m/s²), 2000 EMG + 200 IMU frames, 小块读取与整段解码一致、页面文本行和时间戳不丢、末尾半帧留缓冲, 3 dropped detected, '
          'corrupt frame skipped, partial tail kept' % g)


# ------------------------------------------------------------- collector rig ----
# emg_web.py drives this like Rig/FakeRig: kind, status(), take(), subscribe()/unsubscribe().
# The wristband streams unconditionally, so one reader thread runs from open() on; a take is
# "the next SECONDS seconds of frames", and the PULSE page gets channel 0 re-scaled to the
# 12-bit / 1 kHz line format it already parses ('S t worn v0..v9').
import queue
import threading

SECONDS = 2
FINGER_LABELS = (
    'finger_rest', 'finger_all', 'finger_thumb', 'finger_index', 'finger_middle', 'finger_little',
    'finger_index_middle', 'finger_index_little', 'finger_thumb_index_middle', 'finger_middle_ring_little',
    'finger_index_middle_ring_little', 'finger_pinch_index', 'finger_pinch_middle', 'finger_pinch_ring',
    'finger_pinch_little', 'finger_middle_ring', 'finger_index_middle_ring',
)  # 可选手指组：放松 + 说明书图包里的 16 个动作。不替换上面的演示档。
WRIST_LABELS = ('wrist_flex', 'wrist_ext', 'wrist_radial', 'wrist_ulnar', 'wrist_pron', 'wrist_supi', 'daily_type', 'daily_cup')
# 手腕误触测试：只录不训，见 research/WRIST_FALSE_TRIGGER_CHECKLIST.md
LABELS = ('rest', 'left', 'right', 'click', 'pinch', 'rub', 'fist', 'loose') + FINGER_LABELS + WRIST_LABELS   # left/right/click 持续做 2 s（对标唯理演示：屈腕 / 伸腕 / 捏合）；


def clip_seconds(value):
    """单次录制时长。缺省仍走 SECONDS。布尔值在 Python 里也是 int，必须单独拒绝。"""
    if isinstance(value, bool) or not isinstance(value, int) or value < 1 or value > 5:
        raise ValueError('单次时长必须是 1 到 5 秒')
    return value
# pinch/rub/fist 与单通道同一套：2 s 内先放松、做一次（捏合一次 / 连搓三下 / 握拳一次）、结束前松开；loose = 表带松一格
RAIL_UV = (1 << 23) * .98
PAGE_UV_PER_COUNT = 2000 / 2048                                     # ±2 mV maps to the page's 0..4095


def validate(emg, seq, seconds, rail_uv=RAIL_UV):
    """Same role as usb_emg.validate: raise ValueError on a take we must not train on."""
    lost = dropped(seq)
    if lost:
        raise ValueError(f'丢包 {lost}')
    if len(emg) < EMG_HZ * seconds * .95:
        raise ValueError(f'只收到 {len(emg)} 帧（应 {EMG_HZ * seconds}）')
    railed = float((np.abs(emg) >= rail_uv).mean())
    if railed > .01:
        raise ValueError(f'饱和 {railed:.1%}')
    return railed


# 戴法（2026-10-21）：线缆朝向、CH1（下标 ch0）电极对准的体表位置；只记进元数据，训练和识别不读。
CABLE_DIRS = ('elbow', 'palm')
CH0_SITES = ('ulnar', 'radial', 'palmar', 'dorsal')


def save(stem, emg, imu, seq, label, session, donning, port, seconds=SECONDS, strap_hole=None, cable_dir=None, ch0_site=None, rig_meta=None):
    m = rig_meta or Wl8Rig.meta(Wl8Rig)                                 # 设备相关的那几项（传感器名、IMU 换算，wl18 多一个内置滤波）
    np.savez_compressed(stem.with_suffix('.npz'), emg_uv=emg, imu=imu, seq=seq,
                        emg_hz=EMG_HZ, gyro_scale=m['gyro_scale'], acc_scale=m['acc_scale'], label=label)
    stem.with_suffix('.json').write_text(json.dumps(dict({k: v for k, v in m.items() if not k.endswith('_scale')}, port=port, label=label, session=session,
                                                          donning=int(donning), seconds=seconds, strap_hole=strap_hole, cable_dir=cable_dir, ch0_site=ch0_site, recordedAt=time.strftime('%Y-%m-%dT%H:%M:%S'),
                                                          emg_uv_rms=[round(float(v), 1) for v in ac_rms(emg)]),
                                                     ensure_ascii=False, indent=2) + '\n')


def page_lines(emg, t_ms):
    """2 kHz × 8 ch -> the page's 1 kHz single-channel lines (channel 0, pairs averaged)."""
    ch = emg[:len(emg) // 2 * 2, 0].astype(np.float64).reshape(-1, 2).mean(1)
    v = np.clip(np.round(2048 + ch / PAGE_UV_PER_COUNT), 0, 4095).astype(int)
    return [f'S {t_ms + i} 10 ' + ' '.join(map(str, v[i:i + 10])) for i in range(0, len(v) - len(v) % 10, 10)]


class Wl8Rig:
    kind = 'wl8'
    # 换设备只改这几项（wl18.Wl18Rig）：通道数、波特率、解码、找口、饱和阈值、元数据
    n_ch, baud, sensor = 8, BAUD, 'WaveleTech 8ch wired 2k'
    gyro_scale, acc_scale, rail_uv = GYRO_SCALE, ACC_SCALE, RAIL_UV
    decode = staticmethod(decode)
    find = staticmethod(find_port)
    scans_ports = False

    def meta(self):
        return dict(sensor=self.sensor, gyro_scale=self.gyro_scale, acc_scale=self.acc_scale)

    def __init__(self, port=None):
        self.port_hint, self.conn, self.device, self.banner = port, None, None, ''
        self.lock, self.subscribers, self.streaming = threading.Lock(), [], False
        self.buf, self.frames, self.t_ms, self.capturing = b'', [], 0, None
        self.page_buf = np.zeros((0, self.n_ch), np.int32)                  # 不满 20 行（= 一行页面文本）的肌电留到下一块
        self.boundary_subscribers = []  # 配置/断连边界在下一块数据前同步送达。
        self.frame_subscribers = []                                         # callables fed every decoded (n,8) µV chunk (emg_live)
        self.imu_subscribers = []                                           # callables fed every decoded (m,6) int16 IMU chunk (wl8_cursor)
        self.chunk_subscribers = []                                         # callables(emg, imu, seq, kinds, host_ns) per read (wl8_ab)
        self.last_frame_at, self.drop_why, self._ports = None, '', None     # _ports：测试注入的串口列表；None 才去列真口
        self.link_since = self.last_frame_wall = None                       # link_since：这一段连续出数据从什么时候开始（epoch 秒）：开口 / 服务重启 / 断流 ≥ REWEAR_GAP_S 后的第一帧刷新

    def open(self):
        if self.conn:
            return
        import serial
        self.device = self.find(self.port_hint, self._port_snapshot())
        self.conn = serial.Serial(self.device.device, self.baud, timeout=.2, exclusive=True)
        self.drop_why = ''
        self.last_frame_at = self.last_frame_wall = None                    # 重开口后的第一帧也刷新 link_since（拔线重插算一次重连）
        self.banner = f'{self.sensor.rsplit(" wired", 1)[0]} @ {self.device.device}'
        self.streaming = True
        threading.Thread(target=self._pump, daemon=True).start()

    def _port_snapshot(self):
        listed = getattr(self, '_ports', None)
        return None if listed is None else listed()

    def _receiver_present(self):
        try:
            self.find(self.port_hint, self._port_snapshot())
            return True
        except NoReceiver:
            return False

    def link_state(self):
        now = time.monotonic()
        fresh = self.last_frame_at is not None and now - self.last_frame_at <= LINK_FRESH_S
        if self.conn:
            return 'streaming' if fresh else 'waiting-band'
        if type(self) is not Wl8Rig and not self.scans_ports:              # 假手环 / 回放 / 测试子类自己报，不去扫这台电脑的串口；真设备子类（wl18）设 scans_ports
            return 'streaming' if fresh or self.streaming else 'waiting-band'
        if self._receiver_present():
            return 'waiting-band'
        if self.drop_why:
            return 'dropped'
        return 'no-receiver'

    def status(self):
        link = self.link_state()
        out = {'port': self.device.device if self.device else None, 'kind': self.kind, 'banner': self.banner, 'streaming': self.streaming, 'link': link, 'link_since': self.link_since}
        if link == 'dropped' and self.drop_why:
            out['link_detail'] = self.drop_why
        return out

    def _drop(self, why):
        try: self.conn.close()
        except Exception: pass
        self.conn = self.device = None; self.streaming = False; self.drop_why = str(why); self.banner = f'断开：{why}'

    def _pump(self):
        while self.streaming:
            try:
                raw = read_available(self.conn)
            except Exception as e:
                self._drop(e); return
            if not raw:
                continue
            self._feed(raw)

    def _feed(self, raw):
        emg, imu, seq, kinds, self.buf = self.decode(self.buf + raw, kinds=True)
        if len(seq):
            wall = time.time()                                              # 断流间隔用墙钟：macOS 的 monotonic 在合盖睡眠时不走，睡一夜醒来会把隔夜算成几秒（复核建议）
            if self.last_frame_wall is None or wall - self.last_frame_wall >= REWEAR_GAP_S:
                self.link_since = wall
            self.last_frame_wall = wall
            self.last_frame_at = time.monotonic()
            host_ns = time.monotonic_ns()
            for fn in list(self.chunk_subscribers):
                try: fn(emg, imu, seq, kinds, host_ns)
                except Exception as e: print('chunk subscriber:', e, flush=True)
        if len(imu):                                                        # a read can hold only BB frames: still deliver them
            for fn in list(self.imu_subscribers):
                try: fn(imu)
                except Exception as e: print('imu subscriber:', e, flush=True)
        if self.capturing is not None and len(seq):                         # 只有 BB 帧的一块也要收：漏了它的序号，take 会误报丢包
            self.capturing.append((emg, imu, seq))
        if not len(emg):
            return
        for fn in list(self.frame_subscribers):
            try: fn(emg)
            except Exception as e: print('frame subscriber:', e, flush=True)
        # 页面文本每 20 行肌电出一行；小块读取时大多数块不满 20 行，余数要留着拼，不能截掉（时间戳同理）
        self.page_buf = np.vstack([self.page_buf, emg]); k = len(self.page_buf) // 20 * 20
        if not k: return
        for line in page_lines(self.page_buf[:k], self.t_ms):
            for q in list(self.subscribers):
                try: q.put_nowait(line)
                except queue.Full: pass
        self.t_ms += k * 1000 // EMG_HZ; self.page_buf = self.page_buf[k:]

    def take(self, label, wear, dest, session, donning, cancelled=None, seconds=None, **meta):
        span = SECONDS if seconds is None else clip_seconds(seconds)
        with self.lock:
            self.open()
            self.capturing = []
            time.sleep(span + .1)
            parts, self.capturing = self.capturing, None
        if not self.streaming:
            raise ValueError(self.banner)
        emg = np.concatenate([p[0] for p in parts]) if parts else np.zeros((0, self.n_ch), np.int32)
        imu = np.concatenate([p[1] for p in parts]) if parts else np.zeros((0, 6), np.int16)
        seq = np.concatenate([p[2] for p in parts]) if parts else np.zeros(0, np.uint8)
        railed = validate(emg, seq, span, self.rail_uv)
        # 校准中用户停下，当前条不能进训练集；普通采集默认不传此回调。
        if cancelled and cancelled(): raise ValueError('校准已停止，当前条未保存')
        folder = dest / label; folder.mkdir(parents=True, exist_ok=True)
        stem = folder / f'{label}-{time.strftime("%Y%m%dT%H%M%S")}-{int(time.time() * 1000) % 1000:03d}'
        save(stem, emg, imu, seq, label, session, donning, self.device.device, seconds=span, rig_meta=self.meta(), **meta)
        rms = ac_rms(emg)
        return {'frames': int(len(emg)), 'railed': railed, 'rms_uv_max': float(rms.max()), 'rms_uv_min': float(rms.min())}

    def subscribe(self):
        q = queue.Queue(maxsize=2000); self.subscribers.append(q)
        try:
            with self.lock:
                self.open()
        except Exception:
            if q in self.subscribers: self.subscribers.remove(q)
            raise
        return q

    def unsubscribe(self, q):
        if q in self.subscribers:
            self.subscribers.remove(q)


def _synth_frames(label, rng, seconds=SECONDS, seq0=0):
    """Bytes as the wristband would send them: each gesture lights its own channels (µV RMS)."""
    known = {'rest': np.full(8, 8.), 'middle': np.array([60, 40, 8, 8, 8, 8, 20, 8.]), 'thumb_up': np.array([8, 8, 55, 35, 8, 8, 8, 8.]),
             'thumb_down': np.array([8, 8, 8, 8, 50, 30, 8, 8.]), 'fist': np.full(8, 45.), 'loose': np.full(8, 300.),
             'left': np.array([8, 8, 8, 8, 8, 40, 60, 50.]), 'right': np.array([50, 40, 8, 8, 8, 8, 8, 8.]), 'click': np.array([8, 8, 45, 35, 8, 8, 8, 8.]),
             'pinch': np.array([8, 30, 45, 8, 8, 8, 8, 8.]), 'rub': np.array([8, 8, 8, 30, 40, 8, 8, 8.])}
    gain = known.get(label)
    if gain is None:
        slot = sum(ord(ch) for ch in label) % 8
        gain = np.full(8, 12.)
        gain[slot] = 80.
        gain[(slot + 3) % 8] = 45.
    n = int(EMG_HZ * seconds)
    uv = rng.normal(0, 1, (n, 8)) * gain
    if label == 'loose':
        uv[:, 0] = RAIL_UV * 1.01                                       # a peeled electrode pins the rail
    out, s = b'', seq0                                                  # one counter for AA and BB, like the device
    for k, row in enumerate(np.round(uv).astype(int)):
        out += _frame(EMG, s & 0xFF, b''.join(int(v).to_bytes(3, 'big', signed=True) for v in row)); s += 1
        if k % 10 == 0:
            out += _frame(IMU, s & 0xFF, bytes(2) + struct.pack('>6h', 0, 0, 0, 0, 0, 16410) + bytes(10)); s += 1
    return out, s & 0xFF


class FakeWl8Rig(Wl8Rig):
    """--fake --wl8: synthetic frames pushed through the real decode/validate/save path.
    realtime=True（命令行 --fake）：一条录 2 秒、边录边出流，和真腕带一样；测试默认 False，瞬间完成。"""
    def __init__(self, seed=1, realtime=False, link_mode=None):
        super().__init__()
        self.realtime = realtime
        self.link_mode = link_mode if link_mode is not None else os.environ.get('YUANLI_LINK', '')
        if self.link_mode not in ('', 'no-receiver', 'waiting-band'):
            raise ValueError(f'未知 YUANLI_LINK：{self.link_mode}')
        self.rng, self.seq = np.random.default_rng(seed), 0
        self.banner, self.next_label = 'WaveleTech 8ch FAKE', 'rest'

        class Dev: device, serial_number = 'fake', 'FAKE'
        if self.link_mode == 'no-receiver':
            self.conn, self.streaming, self.device = None, False, None
            self._ports = lambda: []
        else:
            self.conn, self.streaming, self.device = True, True, Dev()

    def open(self): pass

    def link_state(self):
        if self.link_mode == 'no-receiver': return 'no-receiver'
        if self.link_mode == 'waiting-band': return 'waiting-band'
        return 'streaming' if self.streaming else 'waiting-band'

    def take(self, label, wear, dest, session, donning, cancelled=None, seconds=None, **meta):
        span = SECONDS if seconds is None else clip_seconds(seconds)
        raw, self.seq = _synth_frames(label, self.rng, seconds=span, seq0=self.seq)
        step = len(raw) // 20 + 1 if self.realtime else 4096                # 实时：20 片 × 0.1 s = 2 s，页面能看到 NOW 阶段和幅度
        with self.lock:
            self.capturing = []
            for i in range(0, len(raw), step):
                self._feed(raw[i:i + step])
                if self.realtime: time.sleep(span / 20)
            parts, self.capturing = self.capturing, None
        emg = np.concatenate([p[0] for p in parts]); imu = np.concatenate([p[1] for p in parts])
        seq = np.concatenate([p[2] for p in parts])
        railed = validate(emg, seq, span)
        # 校准中用户停下，当前条不能进训练集；普通采集默认不传此回调。
        if cancelled and cancelled(): raise ValueError('校准已停止，当前条未保存')
        folder = dest / label; folder.mkdir(parents=True, exist_ok=True)
        save(folder / f'{label}-{time.time_ns()}', emg, imu, seq, label, session, donning, 'fake', seconds=span, **meta)
        rms = ac_rms(emg)
        return {'frames': int(len(emg)), 'railed': railed, 'rms_uv_max': float(rms.max()), 'rms_uv_min': float(rms.min())}

    def subscribe(self):
        if self.link_mode == 'no-receiver':
            raise NoReceiver('没找到唯理接收器串口（CP210x 或 CH343 0x55D3）；插上接收器，或用 --port 指定')
        q = queue.Queue(maxsize=2000); self.subscribers.append(q)
        if self.link_mode == 'waiting-band':
            return q                                                        # 口开着，但不喂帧：页面应停在「等手环」
        if getattr(self, 'pumping', False):
            return q                                                        # one clock for all pages: two pumps would double-feed the detector
        self.pumping = True
        def pump():
            k = 0
            while self.subscribers:
                # Every fourth second carries a 0.4 s gesture burst so the live detector has something to find.
                if k % 4 == 3:                                                  # first burst at 3 s, after the detector's calibration
                    label = str(self.rng.choice(['left', 'right', 'click']))
                    burst, self.seq = _synth_frames(label, self.rng, seconds=.4, seq0=self.seq)
                    tail, self.seq = _synth_frames('rest', self.rng, seconds=.6, seq0=self.seq)
                    raw = burst + tail; self.last_fake_label = label
                else:
                    raw, self.seq = _synth_frames('rest', self.rng, seconds=1, seq0=self.seq)
                # 真腕带是连续出数，这里每秒的数据切成 10 份、每 0.1 s 喂一份；一次喂 1 s 会让页面「在线」每秒闪一次
                step = max(1, len(raw) // 10)
                for i in range(0, len(raw), step):
                    if self.capturing is None:
                        self._feed(raw[i:i + step])
                    time.sleep(.1)
                k += 1
            self.pumping = False
        threading.Thread(target=pump, daemon=True).start()
        return q


class ReplayWl8Rig(Wl8Rig):
    """--replay：把一段真实录音按原速重新编码成串口字节，走同一条解码 / 订阅链路，循环播放。
    只给演示兜底用：横幅常驻"回放"，并且拒绝录制（回放数据不能进训练集）。"""
    def __init__(self, path, loop=True):
        super().__init__()
        self.path, self.loop = Path(path), loop
        with np.load(self.path, allow_pickle=False) as z:
            emg = np.round(np.asarray(z['emg_uv'], float)).astype(np.int64)
            imu = np.asarray(z['imu'], np.int64) if 'imu' in z.files else np.zeros((0, 6), np.int64)
            kinds = np.asarray(z['kinds']) if 'kinds' in z.files else None
        if kinds is None or len(kinds) != len(emg) + len(imu):                # 老文件没有包类型：IMU 均匀插在 EMG 之间
            every = max(1, len(emg) // max(1, len(imu))) if len(imu) else 0
            kinds = np.array([k for i in range(len(emg)) for k in ([EMG, IMU] if every and i % every == every - 1 and i // every < len(imu) else [EMG])])
        out, ie, ii = bytearray(), 0, 0
        for n, k in enumerate(kinds):
            if k == EMG and ie < len(emg):
                out += _frame(EMG, n & 0xFF, b''.join(int(v).to_bytes(3, 'big', signed=True) for v in np.clip(emg[ie], -2**23, 2**23 - 1))); ie += 1
            elif k == IMU and ii < len(imu):
                out += _frame(IMU, n & 0xFF, bytes(2) + struct.pack('>6h', *[int(v) for v in imu[ii]]) + bytes(10)); ii += 1
        self.stream, self.seconds = bytes(out), max(len(emg) / EMG_HZ, .1)
        self.banner, self.replay = f'回放 · {self.path.name}', self.path.name

        class Dev: device, serial_number = f'replay:{self.path.name}', 'REPLAY'
        self.device = Dev()

    def open(self):
        if self.streaming: return
        self.streaming = True
        threading.Thread(target=self._play, daemon=True).start()

    def _play(self):
        step = FRAME * 64; per = self.seconds * step / len(self.stream)     # 每块 64 帧，按原速推
        while self.streaming:
            t0 = time.monotonic()
            for i in range(0, len(self.stream), step):
                if not self.streaming: return
                self._feed(self.stream[i:i + step])
                time.sleep(max(0., t0 + (i + step) / len(self.stream) * self.seconds - time.monotonic()))
            if not self.loop: self.streaming = False

    def status(self):
        return dict(super().status(), replay=self.replay)

    def take(self, *a, **k):
        raise ValueError('回放模式不能录制训练数据')


# ------------------------------------------------------------- channel sweep ----
def load(folder):
    """[(label, emg_uv (n,8))] in time order, from <folder>/<label>/*.npz."""
    out = []
    for path in sorted(Path(folder).glob('*/*.npz'), key=lambda p: p.name.split('-', 1)[1]):
        with np.load(path, allow_pickle=False) as z:
            out.append((path.parent.name, z['emg_uv']))
    return out


def _xy(records, channels):
    import emg_channels
    return np.stack([emg_channels.features(e[:, channels].astype(np.float64)) for _, e in records]), [l for l, _ in records]


def _split(records):
    """Per class in time order: first 70% train, last 30% test (same rule as emg_channels)."""
    tr, te = [], []
    for label in sorted({l for l, _ in records}):
        rs = [r for r in records if r[0] == label]; cut = int(len(rs) * .7)
        tr += rs[:cut]; te += rs[cut:]
    return tr, te


def _score(train, test, channels):
    import emg_model
    X, y = _xy(train, channels)
    if len(set(y)) < 2:
        return None
    model = emg_model._fit_generic(X, y)
    Xt, yt = _xy([r for r in test if r[0] in model['classes']], channels)
    if not len(yt):
        return None
    return emg_model._report(yt, emg_model.predict(model, Xt), sorted(set(yt)))


def sweep(train_root, rewear_root=None, sizes=(1, 2, 4, 8)):
    """Which electrodes, how many, and the G2 number: balanced accuracy on a rewear set for the
    best 4 chosen on the train set alone (never on the rewear set)."""
    from itertools import combinations
    records = [r for r in load(train_root) if r[0] != 'loose']
    tr, te = _split(records)
    best = {}
    for k in sizes:
        scored = [(c, _score(tr, te, list(c))) for c in combinations(range(8), k)]
        scored = [(c, s['balanced']) for c, s in scored if s]
        if scored:
            c, b = max(scored, key=lambda v: v[1]); best[k] = {'channels': list(c), 'balanced': b}
    out = {'takes': len(records), 'classes': sorted({l for l, _ in records}), 'best': best}
    if 4 in best:
        out['within_session_4ch'] = _score(tr, te, best[4]['channels'])
    rewear = [r for r in load(rewear_root) if r[0] != 'loose'] if rewear_root and Path(rewear_root).exists() else []
    if rewear and 4 in best:
        rep = _score(records, rewear, best[4]['channels'])
        out['rewear_4ch'] = rep
        # Every TRAIN class must be re-recorded >= 5 times: the report only knows the classes the rewear set has.
        counts = {k: sum(1 for l, _ in rewear if l == k) for k in out['classes']}
        out['g2_passed'] = bool(rep and rep['balanced'] >= .85 and all(v >= 5 for v in counts.values()))
    else:
        out['g2_passed'] = False
    sizes_txt = ' / '.join(f'{k}ch {v["balanced"]:.2f}' for k, v in best.items())
    out['message'] = (f'同次佩戴内：{sizes_txt}；最佳 4 电极 {best.get(4, {}).get("channels")}'
                      + (f'；摘下重戴 4ch {out["rewear_4ch"]["balanced"]:.2f}（≥0.85 {"过" if out["g2_passed"] else "不过"}）' if out.get('rewear_4ch') else '；rewear 集未录'))
    return out


def check_sweep():
    import tempfile
    rng = np.random.default_rng(5)
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        for which, n in (('train', 12), ('rewear', 6)):
            for label in ('rest', 'left', 'right', 'click'):
                for i in range(n):
                    raw, _ = _synth_frames(label, rng)
                    emg, imu, seq, _ = decode(raw)
                    folder = root / which / label; folder.mkdir(parents=True, exist_ok=True)
                    save(folder / f'{label}-{i:04d}', emg, imu, seq, label, 'check', 1, 'fake')
        r = sweep(root / 'train', root / 'rewear')
        assert r['best'][8]['balanced'] > .9 and r['best'][4]['balanced'] > .8, r['best']
        assert r['best'][1]['balanced'] < r['best'][4]['balanced'], 'one channel should not match four'
        assert r['g2_passed'], r['message']
        # Must fail: a rewear set missing two classes cannot pass G2 even if what is there is perfect.
        import shutil
        shutil.rmtree(root / 'rewear' / 'click'); shutil.rmtree(root / 'rewear' / 'right')
        assert not sweep(root / 'train', root / 'rewear')['g2_passed'], 'incomplete rewear passed'
        # Must fail: shuffled labels fall to chance.
        recs = load(root / 'train'); labels = rng.permutation([l for l, _ in recs])
        tr, te = _split([(l, e) for l, (_, e) in zip(labels, recs)])
        assert _score(tr, te, [0, 1, 2, 3])['balanced'] < .4
    # 直流偏置不能改变 RMS；只剩偏置时 RMS 为 0。
    x = rng.normal(0, 50, (4000, 8))
    assert np.allclose(ac_rms(x - 40000), ac_rms(x)) and ac_rms(np.full((10, 8), -40000.0)).max() == 0
    # validate must reject a peeled (railed) take and a lossy one.
    raw, _ = _synth_frames('loose', rng); emg, _, seq, _ = decode(raw)
    try: validate(emg, seq, SECONDS)
    except ValueError as e: assert '饱和' in str(e)
    else: raise AssertionError('railed take accepted')
    raw, _ = _synth_frames('rest', rng); frames = [raw[i:i + FRAME] for i in range(0, len(raw), FRAME)]
    emg, _, seq, _ = decode(b''.join(frames[:50] + frames[52:]))
    try: validate(emg, seq, SECONDS)
    except ValueError as e: assert '丢包' in str(e)
    else: raise AssertionError('lossy take accepted')
    print('wl8 sweep check passed:', r['message'])


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--check', action='store_true'); p.add_argument('--seconds', type=float, default=5)
    p.add_argument('--port'); p.add_argument('--label', default='')
    a = p.parse_args()
    if a.check:
        check(); check_sweep()
    else:
        stem, report = record(a.seconds, a.port, label=a.label)
        print(stem, json.dumps(report, ensure_ascii=False))

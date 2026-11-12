"""AcqHandler：把现有各家 Rig 的订阅链路翻译成统一的数据块，并提供统一的录制。

统一块 Block：
    device_id   描述 id
    uv          float32 (n, ch)   物理量 µV（按描述 offset/gain 由 raw 算，或 rig 已给 µV）
    raw         int32   (n, ch)   原始码值（rig 给不出时由 uv 反推：round(uv/gain + offset)）
    seq         uint32  (n,)      设备序号
    t_host_ns   int               这一块到达主机的单调时钟
    imu         int16   (m, 6) 或 None
    di          uint8   (n, k) 或 None

状态四态：found（有描述、未 open）/ enabled（open 成功、未出流）/ acquiring（出流中）/ lost（断开）。
重连一律新开段（segment += 1），不拼接——AGENTS 铁律。
"""
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent.parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import device_desc  # noqa: E402
import v12  # noqa: E402
import wl8  # noqa: E402
import wl18  # noqa: E402

# Cheez 的 Rig / FakeRig 定义在 emg_web.py 里，而 emg_web 会导入本模块：只能在函数内按需导入（循环依赖）。


@dataclass
class Block:
    device_id: str
    uv: np.ndarray
    raw: np.ndarray
    seq: np.ndarray
    t_host_ns: int
    imu: np.ndarray | None = None
    di: np.ndarray | None = None
    segment: int = 0


def build_rig(desc, serial=None, replay=None, realtime=False, seed=1):
    """按描述挑现有 Rig。描述决定类；命令行只补地址。"""
    kind = desc.transport.get('kind')
    if kind == 'fake':
        return wl8.FakeWl8Rig(seed=seed, realtime=realtime) if desc.decoder == 'wl8' else _cheez_fake(realtime)
    if kind == 'replay':
        path = replay or desc.transport.get('match', {}).get('path')
        if not path:
            raise device_desc.DescError('replay 需要 --replay <npz>')
        return wl8.ReplayWl8Rig(path)
    if desc.decoder == 'wl8':
        return wl8.Wl8Rig(serial)
    if desc.decoder == 'wl18':
        return wl18.Wl18Rig(serial)
    if desc.decoder == 'v12':
        if kind == 'ble' and not desc.cap('record'):
            return v12.SynthV12Rig(seed=seed)          # BLE 桥接未接通前只能合成（描述里 record=false）
        return v12.V12Rig(allow_real=True)
    if desc.decoder == 'cheez':
        import emg_web  # 循环依赖，见文件头
        return emg_web.Rig(serial)
    raise device_desc.DescError(f'不会造 {desc.id} 的 rig')


def _cheez_fake(realtime):
    import emg_web  # 循环依赖，见文件头
    return emg_web.FakeRig(realtime=realtime)


RIG_DECODER = {'Wl8Rig': 'wl8', 'FakeWl8Rig': 'wl8', 'ReplayWl8Rig': 'wl8', 'Wl18Rig': 'wl18', 'V12Rig': 'v12', 'SynthV12Rig': 'v12', 'Rig': 'cheez', 'FakeRig': 'cheez'}
RIG_CHANNELS = {'wl8': 8, 'wl18': 18, 'v12': 8, 'cheez': 1}


def check_pair(rig, desc):
    """rig 与描述必须说同一种解码器、同样的通道数；不符就拒绝，不猜。"""
    dec = RIG_DECODER.get(type(rig).__name__)
    if dec is None:
        raise ValueError(f'未知 rig 类型 {type(rig).__name__}')
    if dec != desc.decoder:
        raise ValueError(f'描述 {desc.id} 的 decoder={desc.decoder}，但 rig 是 {type(rig).__name__}（{dec}）')
    if desc.n_channels != RIG_CHANNELS[dec]:
        raise ValueError(f'{dec} 出 {RIG_CHANNELS[dec]} 路，描述 {desc.id} 写了 {desc.n_channels} 路')


class AcqHandler:
    def __init__(self, rig, desc):
        check_pair(rig, desc)
        self.rig, self.desc = rig, desc
        self.lock = threading.Lock()
        self.subscribers = []
        self.segment, self.n_blocks, self.n_samples, self.dropped = 0, 0, 0, 0
        self.last_seq = None
        self.state = 'found'
        self._recorder = None
        self._clock = None
        self.gain = np.asarray(desc.gains(), np.float64)
        self.offset = np.asarray(desc.offsets(), np.float64)
        self._hooked = False

    # ------------------------------------------------------------------ 生命周期
    def open(self):
        with self.lock:
            if self.state in ('enabled', 'acquiring'):
                return self.status()
            self.rig.open()
            self._hook()
            self.state = 'enabled'
            return self.status()

    def start(self):
        self.open()
        # 连续流的 rig（Wl8 家族、V12 合成）open 即出流；Cheez 走 take()，这里只标状态
        if type(self.rig).__name__ == 'FakeWl8Rig' and self._clock is None:
            self._clock = self.rig.subscribe()          # 假手环的泵在有订阅者时才转；stop() 退订
        return self.status()

    def stop(self):
        with self.lock:
            if self._recorder:
                self._recorder.stop()
            if self._clock is not None:
                self.rig.unsubscribe(self._clock)
                self._clock = None
            if hasattr(self.rig, 'streaming') and type(self.rig).__name__ in ('ReplayWl8Rig', 'SynthV12Rig'):
                self.rig.streaming = False
            self.state = 'enabled' if getattr(self.rig, 'conn', None) or getattr(self.rig, 'streaming', False) else 'found'
            return self.status()

    def status(self):
        st = {}
        try:
            st = self.rig.status() or {}
        except Exception as e:  # 老 rig 的 status 可能在未 open 时抛
            st = {'error': str(e)}
        if st.get('banner', '').startswith('断开'):
            self.state = 'lost'
        return {
            'device_id': self.desc.id, 'name': self.desc.name, 'state': self.state,
            'fs_Hz': self.desc.fs_Hz, 'n_channels': self.desc.n_channels, 'labels': self.desc.labels(),
            'capabilities': self.desc.capabilities, 'segment': self.segment, 'samples': self.n_samples, 'dropped': self.dropped,
            'battery': None, 'rig': st,
        }

    # ------------------------------------------------------------------ 订阅
    def subscribe(self, fn):
        self.subscribers.append(fn)
        return lambda: self.subscribers.remove(fn) if fn in self.subscribers else None

    def _hook(self):
        if self._hooked:
            return
        r = self.rig
        if hasattr(r, 'chunk_subscribers'):            # Wl8 家族与 V12：一次 read 一块
            r.chunk_subscribers.append(self._on_chunk)
            if hasattr(r, 'boundary_subscribers'):
                r.boundary_subscribers.append(self._on_boundary)
            self._hooked = True
        else:                                           # Cheez：没有连续块；录制走 rig.take，实时流由 emg_web 现有路径负责
            self._hooked = True

    def _on_boundary(self, event):
        self.segment += 1
        self.last_seq = None
        self.state = 'lost' if 'lost' in str(event).lower() or '断' in str(event) else self.state

    def _on_chunk(self, emg, imu, seq, kinds, host_ns):
        if not len(seq) and not len(emg):
            return
        uv = np.asarray(emg, np.float32).reshape(-1, self.desc.n_channels) if len(emg) else np.zeros((0, self.desc.n_channels), np.float32)
        raw = np.round(uv / self.gain + self.offset).astype(np.int32)
        # rig 给的 seq 是 EMG+IMU 共用的 uint8 滚动计数（到达顺序）：丢帧按它算，样本序号另起 uint32 连续计数
        shared = np.asarray(seq, np.uint8)
        if len(shared):
            chain = shared if self.last_seq is None else np.concatenate([[self.last_seq], shared]).astype(np.uint8)
            self.dropped += wl8.dropped(chain)
            self.last_seq = int(shared[-1])
        seq = np.arange(self.n_samples, self.n_samples + len(uv), dtype=np.uint32)
        self.n_blocks += 1
        self.n_samples += len(uv)
        self.state = 'acquiring'
        b = Block(self.desc.id, uv, raw, seq, int(host_ns), np.asarray(imu, np.int16) if imu is not None and len(imu) else None, None, self.segment)
        if self._recorder:
            self._recorder.feed(b)
        for fn in list(self.subscribers):
            try:
                fn(b)
            except Exception as e:
                print('acq subscriber:', e, flush=True)

    # ------------------------------------------------------------------ 录制
    def record(self, seconds=None):
        """开始一段录制；seconds=None 为连续，调 stop_record() 结束。返回 TakeRecorder。"""
        if not self.desc.cap('record'):
            raise PermissionError(f'{self.desc.id} 不能录制（描述 capabilities.record=false）')
        if self._recorder and not self._recorder.done:
            raise RuntimeError('已有一段在录')
        self.start()
        self._recorder = TakeRecorder(self.desc, seconds, segment=self.segment)
        return self._recorder

    def stop_record(self):
        if not self._recorder:
            raise RuntimeError('没有在录')
        r = self._recorder
        r.stop()
        self._recorder = None
        return r


class TakeRecorder:
    def __init__(self, desc, seconds, segment=0):
        self.desc, self.seconds, self.segment = desc, seconds, segment
        self.blocks, self.events, self.done = [], [], False
        self.t0_ns, self.t0_wall = None, time.time()
        self._ev = threading.Event()

    def feed(self, b):
        if self.done or b.segment != self.segment:
            return
        if self.t0_ns is None:
            self.t0_ns = b.t_host_ns
        self.blocks.append(b)
        if self.seconds is not None and sum(len(x.uv) for x in self.blocks) >= self.seconds * self.desc.fs_Hz:
            self.stop()

    def mark(self, label, source='key'):
        n = sum(len(x.uv) for x in self.blocks)
        t = n / self.desc.fs_Hz
        self.events.append((float(t), str(label), str(source)))
        return t

    def stop(self):
        self.done = True
        self._ev.set()

    def wait(self, timeout=None):
        return self._ev.wait(timeout)

    def arrays(self):
        if not self.blocks:
            z = np.zeros((0, self.desc.n_channels))
            return dict(uv=z.astype(np.float32), raw=z.astype(np.int32), seq=np.zeros(0, np.uint32), t_host_ns=np.zeros(0, np.int64), imu=None, di=None, events=self.events)
        uv = np.concatenate([b.uv for b in self.blocks])
        raw = np.concatenate([b.raw for b in self.blocks])
        seq = np.concatenate([b.seq for b in self.blocks])
        t = np.array([b.t_host_ns for b in self.blocks], np.int64)
        imus = [b.imu for b in self.blocks if b.imu is not None]
        imu = np.concatenate(imus) if imus else None
        dis = [b.di for b in self.blocks if b.di is not None]
        di = np.concatenate(dis) if dis else None
        if self.seconds is not None:
            n = int(self.seconds * self.desc.fs_Hz)
            uv, raw, seq = uv[:n], raw[:n], seq[:n]
        return dict(uv=uv, raw=raw, seq=seq, t_host_ns=t, imu=imu, di=di, events=self.events)

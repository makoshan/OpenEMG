"""V12 自研前端（ADS1298 + XIAO nRF52840，传输协议候选 v1）接进现有八通道页面的数据源。

V12 的包（16 字节头 + 每帧 27 字节 ADS 原始帧）→ 序号缺口计数 → ADC 码换算成 µV → 重新编成唯理帧，
走 wl8.Wl8Rig 同一条解码 / 订阅链路（和 ReplayWl8Rig 同一个做法），所以 stream8、页面、滤波一行不用改。

四态：已实现未验收。现在只有合成输入：V12 还没有能采样的板子、目标固件和 BLE 链路。
编解码在本仓库 firmware/offline-f01/codec.py（协议未冻结，只留一份，改了这边自动跟上）。

    python3 v12.py --check                       # 合成包，秒级；编解码文件不在就 SKIP
    python3 emg_web.py --v12-synth --port 8769   # 页面上看 V12 合成流（不能录制、不能控制光标）
"""
import argparse
from dataclasses import asdict, dataclass
import importlib.util
import json
import threading
import time
from pathlib import Path

import numpy as np

import wl8
from v12_raw import RawArchive

CODEC = Path(__file__).resolve().parent.parent / 'firmware/offline-f01/codec.py'
@dataclass(frozen=True)
class AdcProfile:
    """名义配置，不代表已读回实板寄存器或完成电压校准。"""
    vref_V: float = 4.0
    gain: int = 6
    fs_Hz: int = 2000

    def __post_init__(self):
        if isinstance(self.vref_V, bool) or self.vref_V not in (2.4, 4.0):
            raise ValueError('候选内部参考电压仅支持 2.4 V 或 4 V')
        if type(self.gain) is not int or self.gain not in (1, 2, 3, 4, 6, 8, 12):
            raise ValueError('ADS1298 增益配置无效')
        if type(self.fs_Hz) is not int or self.fs_Hz not in (2000, 4000):
            raise ValueError('候选采样率仅支持 2000 或 4000 Hz')

    @property
    def uv_per_count(self):
        # TI 数据手册 §9.4.1：LSB 权重 VREF/(2^23−1)，再折回 PGA 输入端。
        return self.vref_V * 1e6 / (self.gain * (2 ** 23 - 1))


# 对齐 F05 候选 CONFIG3=0xe0、CHnSET 增益码 000。还没有实板读回/校准证据。
F05_PROFILE = AdcProfile()
VREF_V, GAIN = F05_PROFILE.vref_V, F05_PROFILE.gain
UV_PER_COUNT = F05_PROFILE.uv_per_count
ADS_STATUS = bytes([0xC0, 0, 0])                     # 帧头 3 字节状态字：高 4 位固定 1100，导联脱落位全 0


def load_codec(path=CODEC):
    spec = importlib.util.spec_from_file_location('v12_codec', path)
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    return mod




class V12Rig(wl8.Wl8Rig):
    """喂 V12 包的八通道设备。接真实 BLE 时由桥接程序调 feed_packet；现在只有下面的合成源。"""
    def __init__(self, allow_real=False, codec=None, profile=F05_PROFILE, raw_dir=None):
        if profile.fs_Hz != wl8.EMG_HZ:
            raise ValueError('现有页面只支持 2 kHz；4 kHz 不可冒充 2 kHz 显示')
        super().__init__()
        self.profile = profile
        self.codec = codec or load_codec()
        self.archive = RawArchive(raw_dir, profile, self.codec, allow_real) if raw_dir is not None else None
        self.rx, self.seq = self.codec.Receiver(allow_real), 0
        # 状态字不对的帧（全零、错位）的采样序号。ponytail: 全部留在内存，长时间实采改成计数 + 原包归档里查。
        self.bad_status = []
        self.banner, self.replay = 'V12 协议 v1（候选）', 'V12'               # replay 非空：沿用回放的拦截，不能录训练集、不能控真光标

        class Dev: device, serial_number = 'v12', 'V12'
        self.device = Dev()

    def feed_packet(self, data, mtu=247):
        # 先存原包，坏包也留下供离线诊断；写失败就抛错，不能假装记录成功。
        if self.archive is not None:
            self.archive.write(dict(packet_hex=bytes(data).hex(), mtu=mtu))
        before = self.rx.missing_samples
        p = self.rx.receive(data, mtu)                                       # 坏包、乱序、未开会话都在这里抛 ValueError，不往下游送
        if p.flags & self.codec.RECONFIGURE:
            # 配置改变后丢弃未满显示块，避免两段信号拼进同一窗口；原包归档保留边界标志。
            self.buf = b''
            self.page_buf = np.zeros((0, 8), np.int32)
            for callback in list(self.boundary_subscribers):
                callback(dict(self.rx.boundaries[-1]))
        self.seq += self.rx.missing_samples - before                         # 丢了几个采样，唯理序号就跳几个，下游丢包统计照常能看见
        counts = np.array([self.codec.decode_frame(f)[1] for f in p.frames], np.float64)
        # 页面用整数 µV；诊断文件保留完整 ADC 码/状态字/序号/时间戳，不受这里的舍入影响。
        uv = np.clip(np.round(counts * self.profile.uv_per_count), -2 ** 23, 2 ** 23 - 1).astype(int)
        out = bytearray()
        for i, (f, row) in enumerate(zip(p.frames, uv)):
            if f[0] >> 4 != ADS_STATUS[0] >> 4:
                # 状态字高 4 位不是 1100：全零读或错位，不是采样。不送下游、不补值，序号照跳，页面按丢样显示。
                self.bad_status.append(p.sequence + i); self.seq += 1
                continue
            out += wl8._frame(wl8.EMG, self.seq & 0xFF, b''.join(int(v).to_bytes(3, 'big', signed=True) for v in row)); self.seq += 1
        self._feed(bytes(out))

    def disconnect(self):
        if self.archive is not None:
            self.archive.write({'disconnect': True})
        boundary = dict(reason='disconnect', previous_timestamp_us=self.rx.last_timestamp, next_timestamp_us=None, missing_samples=None)
        self.rx.disconnect()
        for callback in list(self.boundary_subscribers): callback(boundary)
        self.buf = b''
        self.page_buf = np.zeros((0, 8), np.int32)

    def close_capture(self):
        if self.archive is not None:
            self.archive.close()
            self.archive = None

    def open(self): self.streaming = True

    def status(self):
        rx = self.rx
        return dict(super().status(), replay=self.replay, v12={'accepted_samples': rx.accepted_samples, 'missing_samples': rx.missing_samples,
                                                                'malformed': rx.malformed, 'reordered': rx.reordered, 'sessions': rx.sessions,
                                                                'bad_status_frames': len(self.bad_status),
                                                                'configuration_boundaries': list(rx.boundaries),
                                                                'adc_profile': asdict(self.profile), 'calibration_verified': False,
                                                                'raw_capture': self.archive is not None})

    def take(self, *a, **k):
        raise ValueError('V12 合成/候选协议数据不能录制训练数据')


def synth_packets(codec, uv, seq0=0, t0_us=1, profile=F05_PROFILE):
    """把 (n,8) µV 编成 V12 包（每包 8 帧，带合成标志；seq0 为 0 时首包开新会话）。"""
    counts = np.round(np.asarray(uv, np.float64) / profile.uv_per_count).astype(int)
    for i in range(0, len(counts), codec.MAX_FRAMES):
        frames = tuple(ADS_STATUS + b''.join(int(v).to_bytes(3, 'big', signed=True) for v in row) for row in counts[i:i + codec.MAX_FRAMES])
        seq = seq0 + i
        flags = codec.SYNTHETIC | (codec.SESSION_START if seq == 0 else 0)
        yield codec.encode(codec.Packet(seq, t0_us + seq * 1_000_000 // profile.fs_Hz, flags, frames))


class SynthV12Rig(V12Rig):
    """--v12-synth：合成肌电（1 秒放松 / 1 秒握拳交替）经 V12 编码器出包，再走 V12Rig。横幅常驻「合成」。"""
    def __init__(self, seed=1):
        super().__init__()
        self.rng, self.banner = np.random.default_rng(seed), 'V12 协议 v1 FAKE · 合成数据，非实物'   # 页面靠横幅里的 FAKE 显示「模拟台架 · 非实物数据」

    def open(self):
        if self.streaming: return
        self.streaming = True
        threading.Thread(target=self._play, daemon=True).start()

    def _play(self):
        block, n, t0 = 64, 0, time.monotonic()                               # 每 32 ms 出 64 个采样
        while self.streaming:
            gain = 45. if (n // wl8.EMG_HZ) % 2 else 8.
            for pkt in synth_packets(self.codec, self.rng.normal(0, gain, (block, 8)), seq0=n):
                self.feed_packet(pkt)
            n += block
            time.sleep(max(0., t0 + n / wl8.EMG_HZ - time.monotonic()))


# 交付包（ADS1298_ESP32C3 固件 v1 串口/TCP 帧）：55 FF + 27 字节 ADS 原帧 + 前 29 字节累加和低 8 位。
# 07-17 那份采集按交接文档 §12.4 是 EMG_Init：2000 SPS、增益 1、内部 4 V 基准；没有寄存器读回证据。
V1_PROFILE = AdcProfile(vref_V=4.0, gain=1, fs_Hz=2000)


def read_ads_v1(path):
    """返回 [27 字节帧或 None]：帧头错位直接报错（文件坏了），校验和不对的帧记 None（按传输丢样处理）。"""
    d = Path(path).read_bytes()
    if not d or len(d) % 30:
        raise ValueError(f'{path}: 长度 {len(d)} 不是 30 字节帧的整数倍')
    frames = []
    for k in range(0, len(d), 30):
        f = d[k:k + 30]
        if f[:2] != b'\x55\xff':
            raise ValueError(f'{path}: 第 {k // 30} 帧帧头不是 55 FF')
        frames.append(f[2:29] if sum(f[:29]) & 0xFF == f[29] else None)
    if frames[0] is None:
        raise ValueError(f'{path}: 第 0 帧校验和不对，没法开会话')   # ponytail: 少见，真遇到再从第一个好帧起算
    return frames


def v1_packets(codec, frames, fs_Hz):
    """把 read_ads_v1 的帧按文件里的帧号当采样序号编成 V12 包；None 处断开，接收端按缺口计数。
    文件没有时间戳，用标称周期补（不是测得的采样时刻）。"""
    run = []
    for k, f in enumerate(frames + [None]):
        if f is not None and len(run) < codec.MAX_FRAMES and (not run or run[-1][0] == k - 1):
            run.append((k, f)); continue
        if run:
            seq = run[0][0]
            yield codec.encode(codec.Packet(seq, 1 + seq * 1_000_000 // fs_Hz, codec.SESSION_START if seq == 0 else 0,
                                            tuple(x for _, x in run)))
        run = [(k, f)] if f is not None else []


def replay_v1(path, profile=V1_PROFILE, codec=None):
    """交付包原始数据走 V12Rig 整条链：数好帧 / 状态字坏帧 / 校验和坏帧，三者之和必须等于总帧数。"""
    codec = codec or load_codec()
    frames = read_ads_v1(path)
    rig, got, seqs = V12Rig(allow_real=True, codec=codec, profile=profile), [], []   # 别人板子的真数据：显式放行实测来源，只回放不录制
    rig.frame_subscribers.append(got.append); rig.chunk_subscribers.append(lambda emg, imu, seq, kinds, ns: seqs.append(seq))
    for pkt in v1_packets(codec, frames, profile.fs_Hz):
        rig.feed_packet(pkt)
    emg = np.concatenate(got) if got else np.zeros((0, 8), int)
    bad_sum = [k for k, f in enumerate(frames) if f is None]

    def kind(f):
        if f == bytes(27): return 'zero'
        if any(f[j] >> 4 == 0xC and f[j + 1] == 0 and f[j + 2] == 0 for j in range(1, 25)): return 'shifted'
        return 'other'
    bad = [dict(frame=k, kind=kind(frames[k]), status=frames[k][:3].hex()) for k in rig.bad_status]
    v = rig.status()['v12']
    report = dict(source=str(path), total_frames=len(frames), good_frames=len(emg),
                  bad_status_frames=len(bad), bad_checksum_frames=len(bad_sum),
                  bad_status_kinds={k: sum(b['kind'] == k for b in bad) for k in ('zero', 'shifted', 'other')},
                  # 前面补一个虚拟的 −1 号，开头就坏的帧也算进缺口；结尾坏帧下游看不见缺口，只在 bad_status 里
                  receiver_missing=v['missing_samples'], page_dropped=wl8.dropped(np.concatenate([[255]] + seqs)) if seqs else 0,
                  adc_profile=asdict(profile), profile_source='交接文档 §12.4，未读回寄存器',
                  timestamps='标称周期补的，文件里没有', seconds_if_nominal=round(len(frames) / profile.fs_Hz, 3))
    # 守恒：每一帧要么进了页面，要么被标成坏帧，不能凭空多或少
    report['balanced'] = (report['good_frames'] + report['bad_status_frames'] + report['bad_checksum_frames'] == len(frames)
                          and report['receiver_missing'] == len(bad_sum)
                          and report['page_dropped'] == len(bad) + len(bad_sum))
    return report, bad, bad_sum, emg


def check():
    if not CODEC.exists():
        print(f'SKIP: v12 —— 找不到编解码 {CODEC}'); return
    codec = load_codec()
    rng = np.random.default_rng(0)
    truth = np.round(rng.normal(0, 60, (64, 8))).astype(int); truth[0] = [0, 1, -1, 5000, -5000, 187500, -187500, 7]
    pkts = list(synth_packets(codec, truth))
    assert len(pkts) == 8 and all(len(p) == 16 + 8 * 27 for p in pkts)

    # 1) 换算：整数 µV 进、整数 µV 出，逐样本相等；状态里的计数对得上
    rig, got, seqs = V12Rig(codec=codec), [], []
    rig.frame_subscribers.append(got.append); rig.chunk_subscribers.append(lambda emg, imu, seq, kinds, ns: seqs.append(seq))
    for p in pkts: rig.feed_packet(p)
    assert np.array_equal(np.concatenate(got), truth), 'µV 往返不一致'
    assert {k: rig.status()['v12'][k] for k in ('accepted_samples', 'missing_samples', 'malformed', 'reordered', 'sessions')} == {
        'accepted_samples': 64, 'missing_samples': 0, 'malformed': 0, 'reordered': 0, 'sessions': 1}
    assert wl8.dropped(np.concatenate(seqs)) == 0
    # 独立满量程判据，避免合成编码/解码用了同一错误系数仍然往返通过。
    assert round((2 ** 23 - 1) * UV_PER_COUNT) == 666667

    # 2) 丢一个包：缺 8 个采样，V12 计数和唯理序号两边都看得见，样本不补造
    rig, got, seqs = V12Rig(codec=codec), [], []
    rig.frame_subscribers.append(got.append); rig.chunk_subscribers.append(lambda emg, imu, seq, kinds, ns: seqs.append(seq))
    for i, p in enumerate(pkts):
        if i != 3: rig.feed_packet(p)
    assert rig.status()['v12']['missing_samples'] == 8 and wl8.dropped(np.concatenate(seqs)) == 8
    assert np.array_equal(np.concatenate(got), np.delete(truth, slice(24, 32), 0))

    # 3) 必须被拒的输入：截断包、未开会话的首包、非合成来源、录制
    def refused(fn):
        try: fn()
        except ValueError: return True
        return False
    rig, got = V12Rig(codec=codec), []
    rig.frame_subscribers.append(got.append)
    assert refused(lambda: rig.feed_packet(pkts[0][:-1])) and rig.status()['v12']['malformed'] == 1
    assert refused(lambda: rig.feed_packet(pkts[1])), '没有会话起始包也收了'
    real = bytearray(pkts[0]); real[3] &= ~codec.SYNTHETIC
    assert refused(lambda: rig.feed_packet(bytes(real))), '默认不该接收实测来源'
    assert not got, '被拒的包不该有样本流到下游'
    assert refused(lambda: rig.take('rest', 1, Path('.'), 's', 1))

    # 3b) 状态字坏帧（全零读、错位）不能当 0 µV 信号进页面：不送下游、位置记下、序号照跳
    bad_truth = truth[:8].copy()
    frames = [ADS_STATUS + b''.join(int(v).to_bytes(3, 'big', signed=True) for v in np.round(row / UV_PER_COUNT).astype(int)) for row in bad_truth]
    frames[2] = bytes(27)                                   # 全零读
    frames[5] = frames[5][1:] + b'\x00'                     # 左移一个字节：状态字高 4 位变了
    rig, got, seqs = V12Rig(codec=codec), [], []
    rig.frame_subscribers.append(got.append); rig.chunk_subscribers.append(lambda emg, imu, seq, kinds, ns: seqs.append(seq))
    rig.feed_packet(codec.encode(codec.Packet(0, 1, codec.SYNTHETIC | codec.SESSION_START, tuple(frames))))
    assert rig.bad_status == [2, 5] and rig.status()['v12']['bad_status_frames'] == 2, rig.bad_status
    assert np.array_equal(np.concatenate(got), np.delete(bad_truth, [2, 5], 0)), '坏帧混进了下游'
    assert wl8.dropped(np.concatenate(seqs)) == 2

    # 3c) 交付包 v1 文件：好帧 / 状态字坏 / 校验和坏三类守恒；帧头错位整份拒收
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        raw = bytearray()
        for k in range(20):
            f = bytes(27) if k == 5 else ADS_STATUS + b''.join(int(v).to_bytes(3, 'big', signed=True) for v in truth[k])
            fr = b'\x55\xff' + f
            raw += fr + bytes([(sum(fr) + (1 if k == 9 else 0)) & 0xFF])     # 第 9 帧校验和故意错
        p = Path(tmp) / 'v1.bin'; p.write_bytes(bytes(raw))
        report, bad, bad_sum, emg = replay_v1(p, codec=codec)
        assert (report['good_frames'], report['bad_status_frames'], report['bad_checksum_frames']) == (18, 1, 1), report
        assert bad == [dict(frame=5, kind='zero', status='000000')] and bad_sum == [9] and report['balanced'], report
        assert report['receiver_missing'] == 1 and report['page_dropped'] == 2
        raw[30] = 0x54; p.write_bytes(bytes(raw))
        assert refused(lambda: replay_v1(p, codec=codec)), '帧头错位也收了'

    # 4) 端到端：采集服务的 stream8 真推出 2 kHz、8 列的 µV 包；状态里标着 V12，录制被拒
    import json, tempfile, urllib.request
    import emg_web
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        sets = {k: {kind: root / p.name for kind, p in v.items()} for k, v in emg_web.SETS.items()}
        rig = SynthV12Rig()
        srv = emg_web.server_for(emg_web.Session(rig, sets, model_root=root / 'models'), 0)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        base = f'http://127.0.0.1:{srv.server_port}'
        rows = 0
        with urllib.request.urlopen(base + '/api/emg/stream8?project=', timeout=10) as r:
            kind = 'emg'
            for line in r:
                if line.startswith(b'event:'): kind = line[6:].strip().decode()
                elif line.startswith(b'data:'):
                    if kind == 'emg':
                        pkt = json.loads(line[5:])
                        assert pkt['hz'] == 2000 and pkt['unit'] == 'uV' and all(len(s) == 8 for s in pkt['samples'])
                        rows += len(pkt['samples'])
                    kind = 'emg'
                if rows >= 2000: break
        req = urllib.request.Request(base + '/api/emg/state', headers={'X-Mako-Collector': '1', 'X-Mako-Project': ''})
        state = json.loads(urllib.request.urlopen(req, timeout=10).read())
        assert state['wl8']['replay'] == 'V12' and 'FAKE' in state['rig']['banner'], state['rig']    # 没有 FAKE 页面就不标「非实物」
        assert rig.status()['v12']['missing_samples'] == 0 and rig.status()['v12']['accepted_samples'] >= 2000
        rig.streaming = False; srv.shutdown(); srv.server_close()
    print('PASS: v12 —— 协议包 → µV 往返一致，丢包两边可见，坏包/实测来源/录制被拒，stream8 推出 2 kHz × 8 路')
    from check_v12_capture import check_capture
    check_capture()


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--check', action='store_true')
    p.add_argument('--capture-synth', type=Path, help='把合成原包保存到新的诊断目录，不连接设备')
    p.add_argument('--seconds', type=int, default=1, choices=range(1, 61))
    p.add_argument('--replay-v1', type=Path, help='回放交付包 ADS1298_ESP32C3 的 v1 .bin，报告好帧/坏帧')
    p.add_argument('--out', type=Path, help='--replay-v1 的报告目录（新建）：report.json + bad_frames.csv')
    args = p.parse_args()
    if sum(map(bool, (args.check, args.capture_synth, args.replay_v1))) > 1: p.error('--check / --capture-synth / --replay-v1 只能选一个')
    if args.check: check()
    elif args.replay_v1:
        report, bad, bad_sum, _ = replay_v1(args.replay_v1)
        print(json.dumps(report, ensure_ascii=False, indent=1))
        if args.out:
            args.out.mkdir(parents=True, exist_ok=False)
            (args.out / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=1) + '\n')
            rows = [(b['frame'], b['kind'], b['status']) for b in bad] + [(k, 'checksum', '') for k in bad_sum]
            (args.out / 'bad_frames.csv').write_text('frame,kind,status\n' + ''.join(f'{a},{b},{c}\n' for a, b, c in sorted(rows)))
            print(f'报告：{args.out}')
        raise SystemExit(0 if report['balanced'] else 1)
    elif args.capture_synth:
        rig = V12Rig(raw_dir=args.capture_synth)
        try:
            for packet in synth_packets(rig.codec, np.random.default_rng(1).normal(0, 8, (args.seconds * 2000, 8))):
                rig.feed_packet(packet)
            rig.disconnect()
        finally:
            rig.close_capture()
        print(f'已保存合成诊断记录：{args.capture_synth}；非实物数据')
    else: p.error('使用 --check 或 --capture-synth；看页面用 emg_web.py --v12-synth')

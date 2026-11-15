"""ab-control-v1：连续录制"抓放"训练数据（主方案 项目设计规范 第 4 节 A/B，
界面视觉稿 firmware/research/2026-09-30-ab-control-ui-mock.html，Mako 已确认；条件检查只提醒、不拦）。

每一步连续保存：原始 EMG（2 kHz × 8）、IMU（6 轴）、合并包序号和包类型（AA/BB）、每个读取块的主机接收时间，
以及每条口令的主机时间和当时的 EMG / IMU 样本位置。口令时间不是动作真值，训练时边界不确定的窗口要排除。

    python3 wl8_ab.py --check       # 假手环 + 加速日程，走完录制 / 暂停 / 作废 / 停止 / 条件检查
"""
import json
import subprocess
import sys
import threading
import time
from pathlib import Path

import numpy as np
from scipy.signal import butter, filtfilt, iirnotch, sosfiltfilt

import wl8

PROTOCOL = 'ab-control-v1'
FS = wl8.EMG_HZ
DAILY = ['转转手腕', '伸手拿个东西再放回', '轻轻握拳再放开', '搓搓手指', '调整一下坐姿和手臂', '随意放松地动一动', '看看手机再放下', '自然放松']
STEPS = {
    'rehearsal': dict(title='预演 5 次', hint='不入训练集：确认口令、倒计时、波形和保存都正常', cycles=5, hold=(2, 4)),
    'rest60': dict(title='静止放松 60 s', hint='自然呼吸，可以轻微调整，不用僵住', single=('rest', 60)),
    'hold20': dict(title='捏合保持 ×20', hint='10 次轻力、10 次中等力，随机；力度舒服就行', cycles=20, hold=(2, 4), force=True),
    'holdaim10': dict(title='捏合 + 转腕 ×10', hint='捏住以后慢慢左右 / 上下转手腕，像在瞄准', cycles=10, hold=(3, 4), aim=True),
    'daily120': dict(title='日常动作 120 s', hint='跟着提示做普通动作，这些是"不该触发"的干扰样本', daily=120),
}
ORDER = list(STEPS)
PURPOSES = {'dev': '开发数据', 'rehearsal': '预演（不入训练集）', 'accept': '独立验收（冻结后）'}


def schedule(step, rng):
    """一步的分段：[{phase, dur, cycle, cycles, force, text}]；第一段是 3 s 准备。"""
    cfg, segs = STEPS[step], [dict(phase='prepare', dur=3, cycle=0, cycles=0, text='准备')]
    if 'single' in cfg:
        phase, dur = cfg['single']; segs.append(dict(phase=phase, dur=dur, cycle=0, cycles=0, text='放松，手别动'))
    elif 'daily' in cfg:
        n = cfg['daily'] // 15
        for i in range(n): segs.append(dict(phase='daily', dur=15, cycle=i + 1, cycles=n, text=DAILY[i % len(DAILY)]))
    else:
        n = cfg['cycles']; forces = (['light', 'medium'] * (n // 2 + 1))[:n] if cfg.get('force') else [None] * n
        if cfg.get('force'): rng.shuffle(forces)
        for i in range(n):
            hold = round(float(rng.uniform(*cfg['hold'])), 1)
            word = {'light': '轻轻捏住', 'medium': '中等力捏住', None: '捏住'}[forces[i]] + ('，慢慢转手腕瞄准' if cfg.get('aim') else '，保持')
            segs += [dict(phase='rest', dur=2, cycle=i + 1, cycles=n, force=forces[i], text='放松'),
                     dict(phase='hold', dur=hold, cycle=i + 1, cycles=n, force=forces[i], text=word, aim=bool(cfg.get('aim'))),
                     dict(phase='release', dur=2, cycle=i + 1, cycles=n, force=forces[i], text='松开')]
    return segs


class Recorder:
    """在采集服务里跑一步 ab-control-v1。time_scale < 1 只用于自检（把日程缩短）。"""
    def __init__(self, rig, root, voice=True, time_scale=1.0):
        self.rig, self.root, self.voice, self.scale = rig, Path(root), voice, time_scale
        self.lock = threading.Lock()
        self.active, self.flags, self.progress, self.last_saved = False, {}, {}, None

    # ---------------------------------------------------------------- 状态 ----
    def done(self, hand, donning):
        """这只手、这次佩戴，每一步已经保存了几次（不含作废前的"停止"）。"""
        out = {s: dict(files=0, cycles=0, voided=0) for s in ORDER}
        for f in (self.root / hand / f'wear-{donning}').glob('*.json'):
            try: m = json.loads(f.read_text())
            except Exception: continue
            s = m.get('step')
            if s in out:
                out[s]['files'] += 1; out[s]['cycles'] += m.get('completed_cycles', 0); out[s]['voided'] += len(m.get('voided_cycles', []))
        return out

    def state(self, hand=None, donning=None):
        with self.lock:
            st = dict(protocol=PROTOCOL, active=self.active, paused=bool(self.flags.get('paused')), progress=dict(self.progress),
                      steps=[dict(key=k, title=v['title'], hint=v['hint']) for k, v in STEPS.items()], purposes=PURPOSES,
                      last_saved=self.last_saved)
        if hand and donning: st['done'] = self.done(hand, donning)
        return st

    def control(self, action):
        with self.lock:
            if not self.active: raise ValueError('当前没有在录的步骤')
            if action == 'pause': self.flags['paused'] = True
            elif action == 'resume': self.flags['paused'] = False
            elif action == 'stop': self.flags['stop'] = True
            elif action == 'void': self.flags['void'] = True
            else: raise ValueError(f'未知操作 {action}')

    def _say(self, text):
        if self.voice and sys.platform == 'darwin':
            try: subprocess.Popen(['say', '-v', 'Tingting', text])
            except OSError: pass

    # ---------------------------------------------------------------- 录制 ----
    def run(self, step, meta, seed=None):
        """阻塞直到这一步结束；返回保存的 npz 路径。meta: hand / donning / purpose / conditions / placement。"""
        if step not in STEPS: raise ValueError(f'未知步骤 {step}')
        if getattr(self.rig, 'replay', None): raise ValueError('回放模式不能录制训练数据')
        hand, donning = meta.get('hand', 'left'), int(meta.get('donning', 1))
        if hand not in ('left', 'right') or donning < 1: raise ValueError('手别或佩戴次数不对')
        rng = np.random.default_rng(seed if seed is not None else time.time_ns() % 2**32)
        segs = schedule(step, rng)
        chunks, cues = [], []
        counts = dict(emg=0, imu=0)
        def on_chunk(emg, imu, seq, kinds, host_ns):
            chunks.append((emg, imu, seq, kinds, host_ns)); counts['emg'] += len(emg); counts['imu'] += len(imu)
        def cue(phase, seg=None, **extra):
            cues.append(dict(host_ns=time.monotonic_ns(), emg_index=counts['emg'], imu_index=counts['imu'], phase=phase,
                             cycle=(seg or {}).get('cycle', 0), force=(seg or {}).get('force'), **extra))
        with self.lock:
            if self.active: raise RuntimeError('已经有一步在录')
            self.active, self.flags = True, {}
        self.rig.chunk_subscribers.append(on_chunk)
        q = self.rig.subscribe()                                            # 打开串口 / 让假手环开始推流
        stopped, voided, completed = False, [], 0
        try:
            total = sum(s['dur'] for s in segs) * self.scale; spent = 0.
            for seg in segs:
                dur = seg['dur'] * self.scale; t_seg = time.monotonic(); paused_for = 0.
                cue(seg['phase'], seg, text=seg['text']); self._say(seg['text'])
                while True:
                    if self.flags.get('stop'): stopped = True; break
                    if self.flags.pop('void', False):
                        c = seg['cycle'] if seg['phase'] in ('hold', 'release') or not completed else completed
                        if c and c not in voided: voided.append(c); cue('void', seg, voided_cycle=c)
                    if self.flags.get('paused'):
                        cue('pause', seg); p0 = time.monotonic()
                        while self.flags.get('paused') and not self.flags.get('stop'): time.sleep(.05)
                        paused_for += time.monotonic() - p0; cue('resume', seg)
                    el = time.monotonic() - t_seg - paused_for
                    with self.lock:
                        self.progress = dict(step=step, title=STEPS[step]['title'], phase=seg['phase'], text=seg['text'], force=seg.get('force'),
                                             aim=seg.get('aim', False), cycle=seg['cycle'], cycles=seg['cycles'], phase_dur=seg['dur'],
                                             phase_elapsed=round(el / self.scale, 2), step_remaining=round(max(0., total - spent - el) / self.scale, 1),
                                             completed=completed, voided=list(voided),
                                             cycle_plan=[dict(phase=s['phase'], dur=s['dur']) for s in segs if s['cycle'] == seg['cycle'] and seg['cycle']])
                    if el >= dur: break
                    time.sleep(.02)
                if stopped: break
                spent += dur
                if seg['phase'] == 'release' or (seg['phase'] == 'daily' and seg['cycle']): completed = seg['cycle']
                if seg['phase'] == 'rest' and 'single' in STEPS[step]: completed = 1
            cue('end'); self._say('这一步停止了' if stopped else '这一步完成')
        finally:
            self.rig.chunk_subscribers.remove(on_chunk); self.rig.unsubscribe(q)
            with self.lock: self.active, self.progress = False, {}
        return self._save(step, meta, hand, donning, chunks, cues, segs, stopped, voided, completed)

    def _save(self, step, meta, hand, donning, chunks, cues, segs, stopped, voided, completed):
        fs = int(getattr(self.rig, 'fs_Hz', FS))
        n_ch = int(getattr(self.rig, 'n_channels', 8))
        gyro_scale = float(getattr(self.rig, 'gyro_scale', wl8.GYRO_SCALE))
        acc_scale = float(getattr(self.rig, 'acc_scale', wl8.ACC_SCALE))
        cat = lambda i, shape, dt: np.concatenate([c[i] for c in chunks]) if chunks else np.zeros(shape, dt)
        emg, imu, seq, kinds = cat(0, (0, n_ch), np.int32), cat(1, (0, 6), np.int16), cat(2, (0,), np.uint8), cat(3, (0,), np.uint8)
        chunk_ns = np.array([c[4] for c in chunks], np.int64)
        chunk_n = np.array([[len(c[0]), len(c[1]), len(c[2])] for c in chunks], np.int32).reshape(-1, 3)
        folder = self.root / hand / f'wear-{donning}'; folder.mkdir(parents=True, exist_ok=True)
        stem = folder / f'{step}-{time.strftime("%Y%m%d-%H%M%S")}'
        np.savez_compressed(stem.with_suffix('.npz'), emg_uv=emg, imu=imu, seq=seq, kinds=kinds, chunk_host_ns=chunk_ns, chunk_counts=chunk_n,
                            emg_hz=fs, gyro_scale=gyro_scale, acc_scale=acc_scale)
        info = dict(protocol=PROTOCOL, step=step, hand=hand, donning=donning, purpose=meta.get('purpose', 'dev'),
                    placement=meta.get('placement', ''), strap_hole=meta.get('strap_hole'), conditions=meta.get('conditions'), banner=getattr(self.rig, 'banner', ''),
                    recorded_at=time.strftime('%Y-%m-%dT%H:%M:%S'), stopped=stopped, completed_cycles=completed, voided_cycles=voided,
                    emg_samples=int(len(emg)), imu_samples=int(len(imu)), dropped=wl8.dropped(seq), cues=cues, schedule=segs,
                    note='口令时间不是动作真值；边界不确定的窗口在训练时排除。chunk_host_ns 是每个读取块到达主机的单调时钟。')
        stem.with_suffix('.json').write_text(json.dumps(info, ensure_ascii=False, indent=1, default=str))
        with self.lock: self.last_saved = dict(path=str(stem.with_suffix('.npz')), step=step, stopped=stopped, completed=completed,
                                               voided=voided, emg_samples=int(len(emg)), dropped=info['dropped'])
        return stem.with_suffix('.npz')

    # ---------------------------------------------------------------- 条件 ----
    def conditions(self, seconds=5.0):
        """测几秒：工频、放松底噪、IMU、供电（自适应 2/8/16/18 路与 1000/2000 Hz）。只给提醒，不拦。"""
        fs = int(getattr(self.rig, 'fs_Hz', FS))
        n_ch = int(getattr(self.rig, 'n_channels', 8))
        acc_scale = float(getattr(self.rig, 'acc_scale', wl8.ACC_SCALE))
        gyro_scale = float(getattr(self.rig, 'gyro_scale', wl8.GYRO_SCALE))
        got = []
        sub = lambda e, m, s, k, t: got.append((e, m))
        self.rig.chunk_subscribers.append(sub); q = self.rig.subscribe()
        try: time.sleep(seconds)                                         # 真实时长，不随自检的日程加速缩短
        finally: self.rig.chunk_subscribers.remove(sub); self.rig.unsubscribe(q)
        emg = np.concatenate([g[0] for g in got]).astype(float) if got else np.zeros((0, n_ch))
        imu = np.concatenate([g[1] for g in got]).astype(float) if got else np.zeros((0, 6))
        out, warn = dict(emg_samples=int(len(emg)), imu_samples=int(len(imu))), []
        win = max(1, fs // 4)                                            # 250 ms 分窗（2 kHz 为 500 点，1 kHz 为 250 点）
        if len(emg) >= fs and len(emg) >= win and emg.ndim == 2 and emg.shape[1] in VALID_CHANNELS:
            hp = sosfiltfilt(butter(4, 20, 'hp', fs=fs, output='sos'), emg, axis=0)
            mains = sosfiltfilt(butter(4, [45, 55], 'bp', fs=fs, output='sos'), hp, axis=0)
            y = hp.copy()
            for k in range(1, 20):
                f0 = 50 * k
                if f0 >= fs / 2:
                    break
                b, a = iirnotch(f0, 30, fs); y = filtfilt(b, a, y, axis=0)
            n_win = len(y) // win
            w = np.sqrt((y[:n_win * win].reshape(n_win, win, emg.shape[1]) ** 2).mean(1))
            out.update(mains_mv=round(float(np.median(np.sqrt((mains ** 2).mean(0)))) / 1000, 2), noise_uv=round(float(np.median(w)), 1),
                       noise_per_channel=np.median(w, 0).round(1).tolist())
            out.update(signal_readout(emg, fs))
            if out['mains_mv'] > 2: warn.append(f"工频 {out['mains_mv']} mV 偏大：离开插线板 / 充电器，触点补水")
            if out['noise_uv'] > 150: warn.append(f"放松底噪 {out['noise_uv']} µV 偏高：前臂搁稳、手放松，或补水")
        else: warn.append('没收到足够的肌电数据：检查手环是否开机、接收器是否插好')
        if len(imu):
            acc = np.linalg.norm(imu[:, 3:] * acc_scale, axis=1)
            out.update(acc_g=round(float(acc.mean()), 2), gyro_rad_s=round(float(np.abs(imu[:, :3] * gyro_scale).mean()), 3))
            if not 8.5 < out['acc_g'] < 11: warn.append(f"IMU 重力 {out['acc_g']} m/s² 不对：检查接收器")
        else: warn.append('没收到 IMU 数据')
        try:
            batt = subprocess.run(['pmset', '-g', 'batt'], capture_output=True, text=True, timeout=3).stdout
            out['power'] = 'battery' if 'Battery Power' in batt else 'ac' if 'AC Power' in batt else 'unknown'
            if out['power'] == 'ac': warn.append('Mac 接着充电器：厂商要求用电池，拔掉充电器、扩展坞和外接显示器')
        except Exception: out['power'] = 'unknown'
        out['warnings'] = warn
        return out


VALID_CHANNELS = (2, 8, 16, 18)


def signal_readout(emg, fs=FS):
    """5 秒、2/8/16/18 路、单位 µV 的三个只读数。样本不够、路数不对或含非数时返回空，不拿 0 冒充测过。

    基线：原始中位，µV。
    时域峰峰值：20 Hz 高通后的最大减最小，µV。
    频域：20–450 Hz、去掉 50 Hz 倍频之后的 RMS，dB 相对 1 µV。
    这是我们自己的算法，不是唯理软件里那三根柱子。
    """
    x = np.asarray(emg, float)
    if x.ndim != 2 or x.shape[1] not in VALID_CHANNELS or len(x) < fs or not np.isfinite(x).all():
        return {}
    hp = sosfiltfilt(butter(4, 20, 'hp', fs=fs, output='sos'), x, axis=0)
    band = sosfiltfilt(butter(4, [20, min(450, fs / 2 - 1)], 'bp', fs=fs, output='sos'), x, axis=0)
    y = band
    for k in range(1, 9):
        f0 = 50 * k
        if f0 >= fs / 2:
            break
        b, a = iirnotch(f0, 30, fs)
        y = filtfilt(b, a, y, axis=0)
    rms = np.maximum(np.sqrt((y ** 2).mean(0)), 1e-6)
    return dict(
        baseline_uv=np.round(np.median(x, 0), 1).tolist(),
        vpp_uv=np.round(hp.max(0) - hp.min(0), 1).tolist(),
        spectral_db=np.round(20 * np.log10(rms), 1).tolist(),
    )


# ---------------------------------------------------------------- 自检 ----
def check():
    import tempfile
    rng = np.random.default_rng(0)
    s = schedule('hold20', rng)
    holds = [x for x in s if x['phase'] == 'hold']
    assert len(holds) == 20 and sorted({x['force'] for x in holds}) == ['light', 'medium'] and sum(x['force'] == 'light' for x in holds) == 10
    assert all(2 <= x['dur'] <= 4 for x in holds) and s[0]['phase'] == 'prepare'
    assert [x['phase'] for x in schedule('rest60', rng)] == ['prepare', 'rest'] and len(schedule('daily120', rng)) == 9
    t = np.arange(2 * FS) / FS
    tone = lambda hz: np.tile((100 * np.sin(2 * np.pi * hz * t))[:, None], (1, 8))
    keep, kill = signal_readout(tone(80)), signal_readout(tone(50))
    assert 180 < keep['vpp_uv'][0] < 260 and abs(keep['baseline_uv'][0]) < 1, keep
    assert abs(keep['spectral_db'][0] - 37) < 1.5 and kill['spectral_db'][0] < keep['spectral_db'][0] - 12, (keep, kill)
    flat = signal_readout(np.full((2 * FS, 8), 80.0))
    assert flat['baseline_uv'] == [80.0] * 8 and flat['vpp_uv'][0] < 1, flat
    assert signal_readout(np.zeros((FS - 1, 8))) == {} and signal_readout(np.zeros((2 * FS, 7))) == {}
    assert signal_readout(np.full((2 * FS, 8), np.nan)) == {}
    with tempfile.TemporaryDirectory() as tmp:
        rig = wl8.FakeWl8Rig(); rec = Recorder(rig, tmp, voice=False, time_scale=.1)
        # 1) 完整录一步 rest60（加速到 6 s），文件带原始数组、包类型、口令
        path = rec.run('rest60', dict(hand='left', donning=1, purpose='dev', strap_hole=5))
        z = np.load(path); m = json.loads(path.with_suffix('.json').read_text())
        assert m['strap_hole'] == 5, '织带孔位没写进抓放元数据'
        assert len(z['emg_uv']) > 0 and len(z['imu']) > 0 and len(z['seq']) == len(z['kinds']) == len(z['emg_uv']) + len(z['imu'])
        assert set(np.unique(z['kinds'])) == {wl8.EMG, wl8.IMU} and z['chunk_counts'][:, 0].sum() == len(z['emg_uv'])
        assert [c['phase'] for c in m['cues']] == ['prepare', 'rest', 'end'] and not m['stopped'] and m['completed_cycles'] == 1
        assert m['cues'][1]['emg_index'] <= m['cues'][2]['emg_index'] and m['protocol'] == PROTOCOL
        # 2) 捏合保持：录到第 2 次时作废当前一次、暂停再继续、然后停止 —— 都要记进元数据
        def drive():
            while not rec.active: time.sleep(.01)
            while rec.progress.get('cycle', 0) < 2: time.sleep(.01)
            rec.control('void'); time.sleep(.05); rec.control('pause'); time.sleep(.2); rec.control('resume'); time.sleep(.1); rec.control('stop')
        threading.Thread(target=drive, daemon=True).start()
        path2 = rec.run('hold20', dict(hand='left', donning=1, purpose='dev'), seed=1)
        m2 = json.loads(path2.with_suffix('.json').read_text()); phases = [c['phase'] for c in m2['cues']]
        assert m2['strap_hole'] is None, '没填织带孔位时应记为 null'
        assert m2['stopped'] and m2['voided_cycles'] == [1] and 'pause' in phases and 'resume' in phases and 'void' in phases, (m2['voided_cycles'], phases)
        assert not rec.active and rec.progress == {}
        try: rec.control('stop')
        except ValueError: pass
        else: raise AssertionError('没在录时的控制应该报错')
        # 3) 统计本次佩戴已完成的步骤；手别不对要拒绝
        d = rec.done('left', 1); assert d['rest60']['files'] == 1 and d['hold20']['files'] == 1 and d['hold20']['voided'] == 1
        try: rec.run('rest60', dict(hand='middle', donning=1))
        except ValueError: pass
        else: raise AssertionError('错误手别被接受')
        # 4) 条件检查：假手环没有工频，IMU 重力约 9.8，返回提醒列表
        c = rec.conditions(seconds=2.5)
        assert c['emg_samples'] > 0 and 'mains_mv' in c and isinstance(c['warnings'], list) and c['power'] in ('battery', 'ac', 'unknown'), c
        for key in ('baseline_uv', 'vpp_uv', 'spectral_db', 'noise_per_channel'):
            assert len(c[key]) == 8 and all(np.isfinite(c[key])), c[key]
        # 5) C08B 2ch / 16ch @ 1000 Hz 条件检查与 IMU 量程对齐（含奇数个 250 ms 窗不崩溃、无假重力告警）
        import c08b_stream
        for n_ch in (2, 16):
            crig = c08b_stream.SynthC08BRig(n_channels=n_ch, fs_Hz=1000, seed=7)
            crec = Recorder(crig, tmp, voice=False)
            cc = crec.conditions(seconds=1.25)  # 1250 点 = 5 个 250 ms 奇数窗，覆盖旧版 2ch ValueError 坑
            crig.streaming = False
            assert cc['emg_samples'] >= 1000 and 9.5 < cc['acc_g'] < 10.1, (n_ch, cc)
            assert not any('IMU 重力' in w for w in cc['warnings']), (n_ch, cc['warnings'])
            for key in ('baseline_uv', 'vpp_uv', 'spectral_db', 'noise_per_channel'):
                assert len(cc[key]) == n_ch and all(np.isfinite(cc[key])), (n_ch, key, cc[key])
    print('wl8_ab check passed: 日程（20 次轻中力各半、2–4 s）、连续录制含包类型与口令、作废 / 暂停 / 继续 / 停止记账、佩戴统计、手别校验、2/8/16ch 条件检查')


if __name__ == '__main__':
    if '--check' in sys.argv: check()
    else: print(__doc__)

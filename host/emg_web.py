"""Tonight's EMG collection + test site. One process owns the serial port; the page drives it.

    python3 emg_web.py                 # http://127.0.0.1:8767  (Chrome/Edge for the live pane)
    python3 check_emg_web.py           # the same server on a fake rig, no hardware

Why a server and not Web Serial in the page: recording takes must go through usb_emg.validate
and land as the .npz that pipeline.py trains on, and only one program may hold the port. So the
board is opened once here; the pages get a live copy of the `s` stream over SSE (/api/emg/stream)
and ask this process to record, gate, train, evaluate and write the evidence file.
"""
import argparse
import json
import os
import queue
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import numpy as np

import usb_emg
import emg_rehearsal
import usb_emg_imu
import wl8
import wl8_ab
import calibration_voice
import wl8_cursor
import wl8_actions
import wl8_ctrl
import wl8_train
import live_archive
import validation_recording
import emg_live
import device_desc
import studio_api
from rig import build_rig

HERE = Path(__file__).resolve().parent
SETS = {'train': {'emg': HERE / 'emg-data', 'emgimu': HERE / 'emg-imu-data', 'wl8': HERE / 'emg-wl8-data', 'wl18': HERE / 'emg-wl18-data'},
        'rewear': {'emg': HERE / 'emg-data-rewear', 'emgimu': HERE / 'emg-imu-data-rewear', 'wl8': HERE / 'emg-wl8-data-rewear', 'wl18': HERE / 'emg-wl18-data-rewear'}}
GESTURES = ('rest', 'pinch', 'rub', 'snap', 'fist')
# 单通道动作组：'five' = 原五类（旧目录不变）；其余组名、类别来自 App 的 emg8-profiles.json（与八通道同一份清单），主进程按清单放行
import re
_GROUP, _LABEL = re.compile(r'[a-z0-9][a-z0-9-]{0,39}'), re.compile(r'[a-z0-9_]{1,40}')
def single_group(group, labels=None):
    """(组名, 类别)：组名空或 'five' 是原五类；别的组必须给类别。"""
    group = group or 'five'
    if not _GROUP.fullmatch(group): raise ValueError('动作组名不合法')
    if group == 'five': return group, GESTURES
    labels = tuple(labels or ())
    if not 2 <= len(labels) <= 20 or len(set(labels)) != len(labels) or not all(_LABEL.fullmatch(l) for l in labels):
        raise ValueError('动作组类别不合法')
    return group, labels

def class_fingerprints(manifest, labels=GESTURES):
    groups = {label: [] for label in labels}
    for row in manifest or []:
        parts = str(row.get('file', '')).split('/')
        if len(parts) >= 2 and parts[1] in groups and row.get('sha256'):
            groups[parts[1]].append(str(row['sha256'])[:8])
    return {label: ''.join(sorted(items)) for label, items in groups.items()}


def same_wear_files(archive):
    """Validation takes moved out because they were recorded without re-wearing (archive/*same-wear*/README.json)."""
    files = set()
    for readme in sorted(Path(archive).glob('*same-wear*/README.json')):
        files |= {f for f in json.loads(readme.read_text()).get('files', []) if f.endswith('.npz')}
    return files


def rewear_score(report, same_wear):
    """Balanced recall over classes whose validation really was re-worn; same-wear classes are named, not scored."""
    validation = report.get('validation') or {}
    excluded = sorted({str(row.get('file', '')).split('/')[1] for row in report.get('manifest') or []
                       if row.get('file') in same_wear}, key=lambda label: GESTURES.index(label) if label in GESTURES else 99)
    kept = [label for label in validation.get('labels', []) if label not in excluded]
    if not excluded or not kept: return {'excluded': excluded, 'score': validation.get('balanced_accuracy')}
    return {'excluded': excluded, 'score': sum(validation['recall'][label] for label in kept) / len(kept)}
TIERS = ('rest', 'light', 'hard', 'loose', 'punch')
LABELS = {'emg': TIERS, 'emgimu': TIERS, 'wl8': wl8.LABELS, 'wl18': wl8.LABELS}   # 18 通道单独存 emg-wl18-data，不和 8 路样本混      # what the page's record buttons say, per rig


def rewear_passed(report, floor=None):
    """Cross-wear passes on BALANCED recall with every trained class re-recorded >= MIN_TAKES times.
    Raw accuracy lets one easy class carry a rewear set that is missing the others."""
    if not report:
        return False
    if floor is None:
        from emg_model import MIN_TAKES as floor
    return all(sum(report['confusion'][k].values()) >= floor for k in report['recall']) and report['balanced'] >= .8


class Rig:
    """The board. `kind` is which firmware answered: emg (usb_emg) or emgimu (usb_emg_imu)."""
    def __init__(self, port=None):
        self.port_hint, self.conn, self.device, self.kind, self.banner = port, None, None, None, ''
        self.lock, self.streaming, self.subscribers = threading.Lock(), False, []
        self.pump = None

    def open(self):
        if self.conn:
            return
        import serial
        from serial.tools import list_ports
        candidates = [p for p in list_ports.comports() if (p.device == self.port_hint if self.port_hint else p.vid in usb_emg.RIG_VIDS)]
        for c in candidates:
            for kind, banner in (('emg', usb_emg.BANNER), ('emgimu', usb_emg_imu.BANNER)):
                try:
                    conn = serial.Serial(c.device, 115200, timeout=.2, write_timeout=2, exclusive=True)
                    time.sleep(2); usb_emg._drain(conn); conn.write(b'?')
                    self.banner = usb_emg.read_header(conn, timeout=3, prefix=banner)
                    self.conn, self.device, self.kind = conn, c, kind
                    self._sync_stream()
                    return
                except (OSError, ValueError, TimeoutError, RuntimeError):
                    try: conn.close()
                    except Exception: pass
        raise RuntimeError('没找到跑 emg_usb / emg_imu_usb 固件的板子：先 bench_flash_uf2.py 刷进去')

    def _sync_stream(self):
        # The board keeps its toggle state when the host service restarts.
        deadline = time.monotonic() + .6
        while time.monotonic() < deadline:
            if self.conn.readline().startswith(b'S '):
                self.conn.write(b's')
                time.sleep(.05)
                usb_emg._drain(self.conn)
                break
        self.streaming = False

    def status(self):
        return {'port': self.device.device if self.device else None, 'kind': self.kind, 'banner': self.banner, 'streaming': self.streaming}

    def take(self, label, wear, dest, session, donning, on_started=None, prep_host_ns=None, cue=None, review_smr=False):
        with self.lock:
            self.open()
            try:
                if self.kind == 'emg' and 'R=preview-record' in self.banner:
                    # Leave the device streaming until R; hand over the sole reader at a frame boundary.
                    self.streaming = False
                    if self.pump: self.pump.join()
                else:
                    self._stream(False)
            except Exception as e:
                self._drop(e); self.open()
            folder = dest / label; folder.mkdir(parents=True, exist_ok=True)
            stem = folder / f'{label}-{time.strftime("%Y%m%dT%H%M%S")}-{int(time.time() * 1000) % 1000:03d}'
            try:
                if self.kind == 'emgimu':
                    h, counts, frames, railed = usb_emg_imu.read_take(self.conn, wear)
                    usb_emg_imu.save(stem, counts, frames, h, label, self.device.serial_number, session, donning)
                    d = usb_emg_imu.lead({'emg': counts, 'imu': frames, 'worn': h['worn'], 't0_ms': h['t0_ms']})
                    return {'worn': h['worn'], 'railed': railed, 'imu_frames': h['n_imu'], 'max_gap_us': h['max_gap_us'], 'lead_ms': d}
                extra = {'prep_host_ns': prep_host_ns, 'cue': cue}
                if on_started: extra['on_started'] = on_started
                if review_smr: extra['review_smr'] = True
                if 'V=stream-record' in self.banner:
                    counts, worn, railed, timing = usb_emg.read_take(self.conn, wear, self._publish, True,
                        lambda: self._stream(True) if self.subscribers else None, **extra)
                else:
                    counts, worn, railed, timing = usb_emg.read_take(
                        self.conn, wear, self._publish if 'R=preview-record' in self.banner else None, **extra)
                usb_emg.save(stem, counts, worn, label, self.device.serial_number, session=session, donning=donning, timing=timing)
                rms = float(usb_emg.emg_features((counts, worn))[0]) * 1000
                return {'worn': worn, 'railed': railed, 'rms_mv': rms, 'quality_warnings': timing.get('quality_warnings', []), **usb_emg.timing_for_log(timing)}
            except usb_emg.RejectedTake as e:
                rejected = dest.parent / 'rejected' / dest.name / label
                rejected.mkdir(parents=True, exist_ok=True)
                target = rejected / stem.name
                target.with_suffix('.bin').write_bytes(e.payload)
                target.with_suffix('.json').write_text(json.dumps(dict(
                    status='rejected', reason=str(e), header=e.header, label=label,
                    split=dest.name, session=session, donning=donning, wear=wear,
                    deviceSerial=self.device.serial_number, recordedAt=time.strftime('%Y-%m-%dT%H:%M:%S'),
                    **(getattr(e, 'timing', None) or {})
                ), ensure_ascii=False, indent=2))
                e.saved_path = str(target.with_suffix('.bin'))
                raise
            finally:
                if self.subscribers: self._stream(True)

    def _stream(self, on):
        if on == self.streaming:
            return
        self.conn.write(b's'); self.streaming = on
        if on:
            self.pump = threading.Thread(target=self._pump, daemon=True)
            self.pump.start()
        else:
            if self.pump: self.pump.join()  # finish the pending read before recording owns the port
            time.sleep(.05); usb_emg._drain(self.conn)

    def _drop(self, why):
        """USB unplugged or the board reset: forget the handle so the next open() finds the board
        again under whatever name it re-enumerates as (usbmodem101 -> usbmodem1101 on a replug)."""
        try: self.conn.close()
        except Exception: pass
        self.conn = self.device = self.kind = None; self.streaming = False; self.banner = f'断开：{why}'

    def _pump(self):
        while self.streaming:
            try:
                line = self.conn.readline().decode('ascii', errors='replace').strip()
            except Exception as e:                 # serial.SerialException / OSError on unplug
                self._drop(e); return
            if not line:
                continue
            self._publish(line)

    def _publish(self, line):
        for q in list(self.subscribers):
            try: q.put_nowait(line)
            except queue.Full: pass

    def subscribe(self):
        q = queue.Queue(maxsize=2000); self.subscribers.append(q)
        with self.lock:
            self.open()
            try:
                self._stream(True)
            except Exception as e:                 # stale handle from before a replug
                self._drop(e); self.open(); self._stream(True)
        return q

    def unsubscribe(self, q):
        if q in self.subscribers:
            self.subscribers.remove(q)
        if not self.subscribers:
            with self.lock:
                if self.conn: self._stream(False)


class FakeRig:
    """--fake: answers like emg_usb from usb_emg._synth so the page can be walked through with
    no board (tonight's dry run, demos, check_emg_web). 'loose' takes come back half-peeled and
    get dropped by the same validate() the real rig uses."""
    kind, banner = 'emg', 'MAKO DAILY 1.usb-emg; USB-EMG-1; FAKE'
    def __init__(self, realtime=False):
        self.realtime = realtime
        import zlib; self.zlib = zlib
        self.rng = np.random.default_rng(1); self.streaming = False; self.subscribers = []; self.lock = threading.Lock(); self.conn = True; self.t = 0
    def open(self): pass
    def status(self): return {'port': 'fake', 'kind': self.kind, 'banner': self.banner, 'streaming': self.streaming}
    def take(self, label, wear, dest, session, donning, on_started=None, prep_host_ns=None, cue=None, review_smr=False):
        ack = getattr(self, 'fixed_ack', None) or time.time_ns()
        if on_started: on_started({'recording_ack_host_ns': ack, 'command_sent_host_ns': ack})
        hold = getattr(self, 'hold_after_cue', None)
        if hold is not None and not hold.wait(2):
            raise RuntimeError('提示回执没有在这条录制结束前到达')
        kind = {'rest': 'rest', 'light': 'light', 'hard': 'hard', 'loose': 'rest', 'punch': 'hard', 'pinch': 'light', 'rub': 'light', 'snap': 'hard', 'fist': 'hard'}.get(label, 'rest' if label.endswith('_rest') else 'light')   # 别的动作组：假台架只分放松 / 用力
        counts = usb_emg._synth(kind, self.rng); worn = 600 if label == 'loose' else 1000
        header = f'EMG {usb_emg.EMG_HZ} {usb_emg.EMG_COUNT} {self.zlib.crc32(counts.tobytes()):x} {worn} 1005 0'
        warnings = [] if review_smr else None
        worn, railed = usb_emg.validate(header, counts.tobytes(), wear, quality_warnings=warnings)
        if self.realtime: time.sleep(max(0, 2 - (time.time_ns() - ack) / 1e9))
        timing = {'max_gap_us': 1005, 'late': 0, 'command_sent_host_ns': ack, 'recording_ack_host_ns': ack}
        if review_smr: timing.update(quality_warnings=warnings, quality_status='review_required' if warnings else 'capture_checks_passed', training_eligible=False)
        timing.update(usb_emg.align_capture(timing, prep_host_ns, cue, []))
        folder = dest / label; folder.mkdir(parents=True, exist_ok=True)
        usb_emg.save(folder / f'{label}-{time.time_ns()}', counts, worn, label, 'FAKE', session=session, donning=donning, timing=timing)
        return {'worn': worn, 'railed': railed, 'quality_warnings': warnings or [], 'rms_mv': float(usb_emg.emg_features((counts, worn))[0]) * 1000, **usb_emg.timing_for_log(timing)}
    def subscribe(self):
        q = queue.Queue(maxsize=2000); self.subscribers.append(q); self.streaming = True
        def pump():
            while self.streaming and q in self.subscribers:
                v = np.clip(np.round(2048 + self.rng.normal(0, 4, 10)), 0, 4095).astype(int)
                try: q.put_nowait(f'S {self.t} 10 ' + ' '.join(map(str, v)))
                except queue.Full: pass
                self.t += 10; time.sleep(.01)
        threading.Thread(target=pump, daemon=True).start()
        return q
    def unsubscribe(self, q):
        if q in self.subscribers: self.subscribers.remove(q)
        self.streaming = bool(self.subscribers)


def task_for(sets):
    """pipeline's emg task, but loading/training/evaluating against THESE roots -- the default
    task is bound to firmware/emg-data, and a --fake or test session must never touch that."""
    import pipeline, emg_model
    base = pipeline._emg_task()
    train_root, rewear_root = sets['train']['emg'], sets['rewear']['emg']
    def load(splits=None): return usb_emg.load(train_root), []
    def do_train(output): return emg_model.train(load()[0], emg_model.LABELS, Path(output))
    def do_evaluate(model_dir): return emg_model.evaluate(Path(model_dir), rewear=rewear_root)
    return pipeline.Task(**{**base.__dict__, 'data': train_root, 'load': load, 'train': do_train, 'evaluate': do_evaluate})


def strap_hole_ok(v):
    """织带孔位：None（不记）或 1–20 的整数；只记进元数据，不参与训练和识别。"""
    if v is not None and (type(v) is not int or not 1 <= v <= 20): raise ValueError('织带孔位必须是 1 到 20 的整数')
    return v


def wear_ok(cable_dir, ch0_site):
    """戴法：None（未记）或固定选项之一；只记进元数据，不参与训练和识别。"""
    if cable_dir is not None and cable_dir not in wl8.CABLE_DIRS: raise ValueError('线缆朝向只能是 elbow / palm')
    if ch0_site is not None and ch0_site not in wl8.CH0_SITES: raise ValueError('CH1 电极位置只能是 ulnar / radial / palmar / dorsal')
    return {k: v for k, v in (('cable_dir', cable_dir), ('ch0_site', ch0_site)) if v is not None}


class Session:
    """What the page shows: counts on disk, the job in flight, the last results.
    model_root: where trained runs go (None = pipeline's gesture-models/)."""
    # 单通道五类实时识别（live1_action）；锁防双击开出两个识别线程。放类上：部分检查不经 __init__ 造 Session
    live1, live1_lock = None, threading.Lock()
    def __init__(self, rig, sets=SETS, model_root=None, model=None, channels=None, project=None, desc=None):
        self.rig, self.sets, self.model_root, self.lock = rig, sets, model_root, threading.Lock()
        self.project = project
        self.desc = desc or device_desc.for_rig(rig)      # 设备描述：能力判断都看它，不再问 rig.kind
        self.studio = None                                # __main__ 挂 studio_api.Studio
        self.busy, self.progress, self.log, self.results = None, {}, [], {}
        self.stop_requested = False                      # 页面点「停下这一批」：当前这条录完（或倒数中）就停
        self.issue = None
        self.issue_file = self.gesture_sets()['train'].parent / 'review-status.json'
        if self.issue_file.exists():
            self.issue = json.loads(self.issue_file.read_text())
        self.live, self.events = None, []
        self._open_cue = None
        self.pred_subscribers, self.live8, self.wl8_job = [], None, {}      # 八通道：实时识别订阅、识别器、训练任务状态
        self.ab = wl8_ab.Recorder(rig, self.gesture_sets()['train'].parent.parent / 'ab-control-v1') if self.desc.cap('ab') else None
        self.validation = validation_recording.ValidationRecording(rig, (self.wl8_root() if self.project else HERE / 'v12-captures') / 'validation-local', lambda: None if not self.live8 else dict({k: self.live8[k] for k in ('run_id', 'threshold_uv', 'sensitivity', 'min_prob')}, threshold_x=self.live8.get('threshold_x'), mask=list(self.live8['predictor'].mask)), self.wl8_models()) if hasattr(rig, 'chunk_subscribers') else None
        self.ctrl = wl8_ctrl.CtrlSerial()                                  # 控制串口：识别结果发给外设（经典 5 步）
        self.ai = wl8_actions.AiPending()                                   # AI 确认钩子的当前请求（App AI 授权卡读）
        self.cursor = wl8_cursor.Controller(rig, self.gesture_sets()['train'].parent.parent / 'cursor') if self.desc.cap('cursor') else None
        if hasattr(rig, "boundary_subscribers"): rig.boundary_subscribers.append(self.stream_boundary)
        if model:
            classify, model_channels = emg_live.cnn_classifier(model)
            # The npz remembers the channels it was trained on. For a Meta-pretrained net those are Meta's 16
            # electrode indices, so the wristband mapping must be given explicitly (--channels a,b,c,d).
            channels = channels or model_channels
            if any(c >= 8 for c in channels):
                raise ValueError(f'模型通道 {model_channels} 不是腕带的 0–7：用 --channels 指定腕带上对应的 4 个电极')
            self.watch(classify, channels)

    # ---------------------------------------------------------------- 多通道（2 / 8 / 16 路）：连续录制 / 训练 / 实时识别 ----
    def wl8_root(self):
        return next(iter(self.sets['train'].values())).parent            # 工程的 data/emg

    def wl8_folder_prefix(self):
        # 8 通道保持原有 emg-wl8-data 目录；2 通道与 16 通道按设备 id 隔离，避免不同通道数的矩阵混装
        return 'emg-wl8-data' if self.desc.n_channels == 8 else f'emg-{self.desc.id}-data'

    def wl8_models(self):
        sub = 'wl8' if self.desc.n_channels == 8 else self.desc.id
        return (self.model_root or HERE / 'gesture-models') / sub

    def ab_action(self, body):
        action = body.get('action')
        if action == 'conditions':
            if not (self.ab or (self.multi and hasattr(self.rig, 'chunk_subscribers'))):
                raise ValueError('当前设备不支持多通道信号条件检查')
            if self.busy: raise RuntimeError(f'正在 {self.busy}，等它完')
            probe = self.ab or wl8_ab.Recorder(self.rig, self.gesture_sets()['train'].parent.parent / 'ab-control-v1')
            return probe.conditions(float(body.get('seconds', 5)))
        if self.ab is None or not self.desc.cap('ab') or not self.desc.cap('record'):
            raise ValueError(f'{self.desc.name} 未开放 ab-control-v1 录制（安全锁关闭或非对应模式）')
        if action == 'start':
            step = body.get('step'); meta = {k: body.get(k) for k in ('hand', 'donning', 'purpose', 'placement', 'conditions')}
            meta['strap_hole'] = strap_hole_ok(body.get('strap_hole'))
            if step not in wl8_ab.STEPS: raise ValueError('未知步骤')
            if getattr(self.rig, 'replay', None): raise ValueError('回放模式不能录制训练数据')
            self.start(f'抓放 · {wl8_ab.STEPS[step]["title"]}', lambda: self.say(f'已保存 {self.ab.run(step, meta).name}'))
            return {'ok': True}
        self.ab.control(action); return {'ok': True}

    def wl8_train_start(self, labels=None):
        if self.desc.n_channels < 2: raise ValueError(f'{self.desc.name} 请使用单通道训练入口')
        if not self.desc.cap('train') or self.desc.n_channels not in (2, 8, 16):
            raise ValueError(f'{self.desc.name} 还不能训练和实时识别：当前仅开放 2 / 8 路及 C08B 16 路')
        labels = [l for l in (labels or wl8_train.DEFAULT_LABELS) if l in wl8.LABELS]
        job = self.wl8_job = {'running': True, 'events': [], 'run_id': None, 'error': None, 'labels': labels}
        folder = self.wl8_folder_prefix()
        expected_ch = self.desc.n_channels
        def run():
            try:
                r, m = wl8_train.train(self.wl8_root(), labels, progress=lambda e: job['events'].append(e),
                                       data_folder=folder, n_channels=expected_ch)
                d = wl8_train.save(r, m, self.wl8_models()); job['run_id'] = d.name; self.say(f'{expected_ch} 通道训练完成：{d.name}')
            except Exception as e: job['error'] = str(e); raise
            finally: job['running'] = False
        self.start(f'训练 {expected_ch} 通道模型', run)

    def wl8_runs(self):
        out = []
        for f in sorted(self.wl8_models().glob('*/run.json'), reverse=True)[:20]:
            r = json.loads(f.read_text()); out.append({k: r.get(k) for k in ('id', 'created', 'labels', 'same_wear', 'rewear', 'rewear_source', 'shuffled', 'counts', 'n_channels', 'fs_Hz')})
        return out

    def wl8_run(self, rid):
        f = self.wl8_models() / Path(rid).name / 'run.json'
        if not f.exists(): raise ValueError('没有这次训练')
        return json.loads(f.read_text())

    def stream_boundary(self, event):
        """同步回调：先清窗口再允许新配置样本进入预测。已写下的原始段在这里收尾，不和后面的样本拼成一段。"""
        if self.live8:
            self.live8['predictor'].reset(); self.live8['last'] = None
            arch = self.live8.get('archive')
            if arch is not None:
                try: arch.boundary()
                except Exception as e: print('live archive:', e, flush=True)
        if self.live: self.live.reset()
        self.events = []

    def _live_gate(self, body, previous=None):
        threshold = body.get('threshold_uv', 0 if previous is None else previous[0])
        sensitivity = body.get('sensitivity', 5 if previous is None else previous[1])
        return wl8_train.gate_settings(threshold, sensitivity)[:2]

    @staticmethod
    def _live_times(body):
        """幅度门槛按倍数（× 这个人的放松底噪）；没给或给 null 就是按绝对微伏。"""
        return None if body.get('threshold_x') is None else wl8_train.times_setting(body['threshold_x'])

    @staticmethod
    def _live_mask(mask, max_ch=8):
        """要屏蔽的路：1–max_ch 的整数列表，最多 max_ch-1 路（至少留一路）。"""
        max_skip = max(0, int(max_ch) - 1)
        if not isinstance(mask, list) or len(mask) > max_skip or any(isinstance(l, bool) or not isinstance(l, int) or not 1 <= l <= max_ch for l in mask):
            raise ValueError(f'屏蔽的路必须是 1 到 {max_ch} 的整数列表，最多 {max_skip} 路')
        return mask

    def _stop_live8(self):
        if self.validation and self.validation.active: self.validation.stop('实时识别停止')
        if not self.live8:
            return None
        try: self.rig.frame_subscribers.remove(self.live8['fn'])
        except ValueError: pass
        arch = self.live8.get('archive')
        summary = None
        if arch is not None:
            arch.close()
            summary = arch.summary()
        self.live8 = None
        return summary

    def live8_action(self, body):
        action = body.get('action') or 'start'
        if action == 'stop':
            return {'ok': True, 'archive': self._stop_live8()}
        if self.desc.n_channels < 2: raise ValueError(f'{self.desc.name} 请使用单通道实时识别入口')
        if not self.desc.cap('train') or self.desc.n_channels not in (2, 8, 16):
            raise ValueError(f'{self.desc.name} 还不能训练和实时识别：当前仅开放 2 / 8 路及 C08B 16 路')
        max_ch = self.desc.n_channels
        if action == 'tune':
            if self.validation and self.validation.active: raise ValueError('连续验证期间请保持识别设置不变')
            if not self.live8: raise ValueError('实时识别未开启')
            threshold, sensitivity = self._live_gate(body, (self.live8['threshold_uv'], self.live8['sensitivity']))
            mask = self._live_mask(body['mask'], max_ch) if 'mask' in body else None   # 先校验完再改，坏 mask 不留半截门槛
            min_prob = wl8_train.min_prob_setting(body['min_prob']) if 'min_prob' in body else self.live8['min_prob']
            times = self._live_times(body) if 'threshold_x' in body else self.live8['threshold_x']
            self.live8['threshold_uv'], self.live8['sensitivity'], self.live8['min_prob'], self.live8['threshold_x'] = threshold, sensitivity, min_prob, times
            if mask is not None: self.live8['predictor'].set_mask(mask)
            return {'ok': True, 'threshold_uv': threshold, 'sensitivity': sensitivity, 'min_prob': min_prob, 'threshold_x': times, 'mask': self.live8['predictor'].mask}
        if action != 'start': raise ValueError('未知实时识别操作')
        rid = Path(body.get('run_id') or (self.wl8_runs() or [{}])[0].get('id') or '').name
        path = self.wl8_models() / rid / 'model.npz'
        if not rid or not path.exists(): raise ValueError(f'还没有训练好的 {max_ch} 通道模型')
        threshold, sensitivity = self._live_gate(body)
        min_prob = wl8_train.min_prob_setting(body.get('min_prob', 0))
        times = self._live_times(body)
        self._stop_live8()
        lp = wl8_train.LivePredictor(path)
        arch = live_archive.LiveArchive(self.wl8_root() / 'live-raw', run_id=rid)
        def fn(emg):
            infer_started = validation_recording.ms()
            r = lp.push(emg)
            if r and self.live8:
                facts = wl8_train.signal_facts(lp.buf, fs=getattr(lp, 'fs', wl8_train.FS), skip=lp.mask)
                r = wl8_train.apply_recognition_gate(r, facts, self.live8['threshold_uv'], self.live8['sensitivity'], self.live8['min_prob'], self.live8['threshold_x'], lp.rest_ref())
                r['t'] = time.time(); r['mask'] = list(lp.mask); self.live8['last'] = r
                if self.validation: self.validation.prediction(r, len(lp.buf), infer_started)
                if not (self.validation and self.validation.id and not self.validation.finalized): self.ctrl.feed(r)
                for cb in list(self.pred_subscribers):
                    try: cb(r)
                    except Exception: pass
            try: arch.push(emg, r)
            except Exception as e: print('live archive:', e, flush=True)
        self.live8 = {'run_id': rid, 'fn': fn, 'last': None, 'predictor': lp, 'archive': arch, 'threshold_uv': threshold, 'sensitivity': sensitivity, 'min_prob': min_prob, 'threshold_x': times}
        self.ctrl.reset()
        self.rig.frame_subscribers.append(fn); self.rig.subscribe()
        return {'ok': True, 'run_id': rid, 'threshold_uv': threshold, 'sensitivity': sensitivity, 'min_prob': min_prob, 'threshold_x': times, 'rest_ref_uv': lp.rest_ref()}

    def ctrl_action(self, body):
        """控制串口：open（port、baud）/ close / test。不许和手环数据口是同一个。"""
        action = body.get('action')
        if action == 'open':
            if body.get('port') and body.get('port') == getattr(getattr(self.rig, 'device', None), 'device', None):
                raise ValueError('控制串口不能选手环的数据串口')
            return self.ctrl.open(body.get('port'), body.get('baud', 115200))
        if action == 'close': self.ctrl.close(); return self.ctrl.state()
        if action == 'test': return self.ctrl.test()
        raise ValueError('未知控制串口操作')

    def wl8_state(self):
        if not self.multi and self.ab is None: return None
        return {'ab': self.ab.state() if self.ab else None, 'train': {k: v for k, v in self.wl8_job.items() if k != 'events'} | {'events': self.wl8_job.get('events', [])[-40:]},
                'live': None if not self.live8 else {
                    'run_id': self.live8.get('run_id'), 'last': self.live8['last'],
                    'archive': None if self.live8.get('archive') is None else self.live8['archive'].summary()},
                'replay': getattr(self.rig, 'replay', None), 'cursor': self.cursor.state() if self.cursor else None, 'ai': self.ai.state(), 'ctrl': self.ctrl.state()}

    def watch(self, classify, channels):
        """Live events off the wristband stream: onset -> one CNN call -> event (emg_live)."""
        self.live = emg_live.Detector(classify, channels)
        def on_frames(emg):
            n = self.live.n_infer
            emitted = self.live.feed(emg)
            if self.live.n_infer > n:                                       # one onset per chunk in practice; log the latest verdict
                ev = self.live.inferences[-1]
                self.say(f'起爆 @ {ev["t_ms"]} ms → {ev["label"]} ({ev["conf"]:.2f}){"" if ev["emitted"] else "，不发"}')
            self.events += emitted; del self.events[:-50]
        self.rig.frame_subscribers.append(on_frames)

    @property
    def multi(self):
        """多路腕带类（2 / 8 / 16 通道连续块流、wl8_train 路径、无单路 pipeline 任务）。没经 __init__ 的 Session 按 rig 推描述。"""
        desc = getattr(self, 'desc', None) or device_desc.for_rig(self.rig)
        return desc.n_channels >= 2 and desc.cap('realtime')

    def gesture_sets(self, group='five'):
        # 原五类沿用 emg-gesture-data；别的动作组各占一个目录，数据不混
        base = next(iter(self.sets['train'].values())).parent
        root = base / ('emg-gesture-data' if group in (None, 'five') else f'emg-gesture-data-{group}')
        return {split: root / split for split in ('train', 'validation', 'test')}

    def single_models(self, group='five'):
        root = Path(self.model_root or HERE / 'gesture-models')
        return root / ('five-gestures' if group in (None, 'five') else f'single-{group}')

    def rehearsal_root(self):
        return self.gesture_sets()['train'].parent.parent / 'emg-rehearsal-v3'

    def rehearsal_start(self, body):
        with self.lock:
            if self.busy: raise ValueError('录制中，请等待结束')
            return emg_rehearsal.start(self.rehearsal_root(), body.get('participant'),
                                       body.get('placement'), body.get('battery_confirmed'))

    def diagnostic_root(self):
        return self.gesture_sets()['train'].parent.parent / 'emg-diagnostic-v1'

    def diagnostic_state(self):
        root = self.diagnostic_root()
        marker = root / 'session.json'
        meta = json.loads(marker.read_text()) if marker.exists() else {}
        return {**meta, 'counts': {f'wear-{i}': {label: len(list((root / f'wear-{i}' / label).glob('*.npz')))
                for label in ('rest', 'pinch', 'rub')} for i in range(1, 4)}}

    def diagnostic_action(self, action, donning=0):
        with self.lock:
            if self.busy: raise ValueError('录制中，请等待结束')
            state = self.diagnostic_state()
            if action == 'start':
                if state.get('id'): return state
                import uuid
                meta = {'id': str(uuid.uuid4()), 'protocol': 'diagnostic-v1', 'confirmed': []}
            elif action == 'wear':
                if not state.get('id') or donning not in (1, 2, 3): raise ValueError('诊断佩戴编号无效')
                if donning > 1 and not all(n >= 5 for n in state['counts'][f'wear-{donning-1}'].values()):
                    raise ValueError('请先完成上一次佩戴的三种动作')
                meta = {k: v for k, v in state.items() if k != 'counts'}
                meta['confirmed'] = sorted(set(meta['confirmed'] + [donning]))
            else: raise ValueError('未知诊断操作')
            root = self.diagnostic_root(); root.mkdir(parents=True, exist_ok=True)
            temp = root / 'session.tmp'; temp.write_text(json.dumps(meta, ensure_ascii=False, indent=2))
            temp.replace(root / 'session.json')
            return self.diagnostic_state()

    def factor_check_root(self):
        return self.gesture_sets()['train'].parent.parent / 'emg-factor-check-v1'

    def factor_check_state(self):
        root = self.factor_check_root()
        marker = root / 'session.json'
        meta = json.loads(marker.read_text()) if marker.exists() else {}
        counts = {'wear-1': {label: len(list((root / 'wear-1' / label).glob('*.npz'))) for label in ('rest', 'pinch', 'rub')}}
        return {**meta, 'counts': counts}

    def factor_check_action(self, action, donning=0, factor=''):
        with self.lock:
            if self.busy: raise ValueError('录制中，请等待结束')
            state = self.factor_check_state()
            if action == 'start':
                if state.get('id'): return state
                text = factor.strip() if isinstance(factor, str) else ''
                if not text or len(text) > 80 or any(c in text for c in '\n\r'):
                    raise ValueError('先写明这一轮只改变的一个条件')
                import uuid
                meta = {'id': str(uuid.uuid4()), 'protocol': 'factor-check-v1', 'factor': text, 'confirmed': []}
            elif action == 'wear':
                if not state.get('id') or donning != 1: raise ValueError('这一次只在同一佩戴里录')
                meta = {k: v for k, v in state.items() if k != 'counts'}
                meta['confirmed'] = [1]
            else:
                raise ValueError('未知对照操作')
            root = self.factor_check_root()
            root.mkdir(parents=True, exist_ok=True)
            temp = root / 'session.tmp'
            temp.write_text(json.dumps(meta, ensure_ascii=False, indent=2))
            temp.replace(root / 'session.json')
            return self.factor_check_state()

    def gesture_counts(self, group='five', labels=GESTURES):
        return {split: {label: len(list((root / label).glob('*.npz'))) for label in labels}
                for split, root in self.gesture_sets(group).items()}

    def counts(self):
        kind = self.rig.kind or 'emg'
        if self.multi and (self.desc.n_channels != 8 or kind not in self.sets.get('train', {})):
            base = self.wl8_root()
            prefix = self.wl8_folder_prefix()
            return {'train': {p.name: len(list(p.glob('*.npz'))) for p in sorted((base / prefix).glob('*')) if p.is_dir()},
                    'rewear': {p.name: len(list(p.glob('*.npz'))) for p in sorted((base / f'{prefix}-rewear').glob('*')) if p.is_dir()}}
        return {name: {p.name: len(list(p.glob('*.npz'))) for p in sorted(paths[kind].glob('*')) if p.is_dir()}
                for name, paths in self.sets.items()}

    def state(self, include_training=True, group=None, labels=None):
        group, labels = single_group(group, labels)
        try: rig = dict(self.rig.status())
        except Exception as e: rig = {'error': str(e)}
        rig.setdefault('n_channels', self.desc.n_channels)
        rig.setdefault('fs_Hz', self.desc.fs_Hz)
        rig.setdefault('device_id', self.desc.id)
        rig.setdefault('device_name', self.desc.name)
        tier_key = 'wl8' if self.multi else (self.rig.kind or 'emg')
        return {'project': self.project, 'rig': rig, 'counts': self.counts(), 'gesture_counts': self.gesture_counts(group, labels), 'gesture_group': group, 'diagnostic': self.diagnostic_state(), 'factor_check': self.factor_check_state(), 'rehearsal': emg_rehearsal.state(self.rehearsal_root()), 'busy': self.busy, 'progress': self.progress, 'capture_issue': self.issue, 'gesture_training': self.gesture_training(group, labels) if include_training else None,
                'log': self.log[-40:], 'results': self.results, 'tiers': LABELS.get(tier_key, TIERS),
                'events': self.events[-10:], 'live': None if not self.live else ('ready' if self.live.ready else 'calibrating'),
                'wl8': self.wl8_state(), 'live1': self.live1 and {'run_id': self.live1['run_id'], 'last': self.live1['last']}}

    def set_issue(self, issue):
        self.issue = issue
        self.issue_file.parent.mkdir(parents=True, exist_ok=True)
        self.issue_file.write_text(json.dumps(issue, ensure_ascii=False, indent=2))

    def say(self, text):
        self.log.append(f'{time.strftime("%H:%M:%S")} {text}')

    def start(self, name, fn):
        with self.lock:
            if self.busy:
                raise RuntimeError(f'正在 {self.busy}，等它完')
            self.busy = name
        def run():
            try: fn()
            except Exception as e: self.say(f'{name} 出错：{e}')
            finally: self.busy = None
        threading.Thread(target=run, daemon=True).start()

    def record(self, label, count, which, session, donning, wear, countdown=3, task='effort', calibration=False, seconds=None, group=None, strap_hole=None, cable_dir=None, ch0_site=None):
        if task not in ('effort', 'gestures', 'diagnostic', 'factor-check', 'rehearsal'): raise ValueError('未知采集任务')
        with self.live1_lock: self._stop_live1()                         # 录制要独占串口，单通道识别先停
        if not 1 <= count <= 100 or not 0 <= countdown <= 10: raise ValueError('录制数量或倒计时超出范围')
        span = None if seconds is None else wl8.clip_seconds(seconds)
        if span is not None and not isinstance(self.rig, wl8.Wl8Rig): raise ValueError('单次时长只用于八通道腕带')
        take_extra = {} if span is None else {'seconds': span}
        # 织带孔位只记进每条录音的元数据，供以后拿底噪对照松紧；不参与训练和识别。
        if strap_hole_ok(strap_hole) is not None:
            if not isinstance(self.rig, wl8.Wl8Rig): raise ValueError('织带孔位只用于八通道腕带')
            take_extra['strap_hole'] = strap_hole
        if how := wear_ok(cable_dir, ch0_site):                          # 别叫 wear：那是单通道的松紧档（high/low/off）形参
            if not isinstance(self.rig, wl8.Wl8Rig): raise ValueError('戴法只用于八通道腕带')
            take_extra.update(how)
        kind = self.rig.kind or (self.rig.open() or self.rig.kind)
        if task == 'rehearsal':
            if kind != 'emg': raise ValueError('预演仅支持当前 Cheez 单通道')
            dest, d = emg_rehearsal.destination(self.rehearsal_root(), label, count, which)
            donning = 1
            session = f"single-action-v3; stage=rehearsal; session_id={d['id']}/wear-1; rub=single-slide; {d['participant']}; {d['placement']}"
        elif task == 'diagnostic':
            d = self.diagnostic_state()
            if kind != 'emg' or not d.get('id') or which not in d['counts'] or label not in ('rest', 'pinch', 'rub'):
                raise ValueError('未知诊断采集条件')
            donning = int(which[-1])
            if donning not in d['confirmed']: raise ValueError('请先确认本次重新佩戴')
            if count != 1 or d['counts'][which][label] >= 5: raise ValueError('诊断每次录一条，每种动作最多五条')
            dest = self.diagnostic_root() / which
            session = f"diagnostic-v1; session_id={d['id']}/wear-{donning}; rub=three-rubs; {session}"
        elif task == 'factor-check':
            d = self.factor_check_state()
            if kind != 'emg' or not d.get('id') or which != 'wear-1' or label not in ('rest', 'pinch', 'rub'):
                raise ValueError('未知对照条件')
            if 1 not in d.get('confirmed', []): raise ValueError('请先确认这一次佩戴')
            if count != 1 or d['counts']['wear-1'][label] >= 5: raise ValueError('每次录一条，放松、捏合和搓动各最多五条')
            dest = self.factor_check_root() / 'wear-1'
            session = f"factor-check-v1; session_id={d['id']}/wear-1; factor={d.get('factor', '')}; same-donning; comfortable pinch, not a fist; rub=three-rubs; {session}"
        elif task == 'gestures':
            if kind != 'emg': raise ValueError('当前手势采集仅支持单通道 EMG')
            group = group or 'five'
            if not _GROUP.fullmatch(group) or (label not in GESTURES if group == 'five' else not _LABEL.fullmatch(label)) or which not in self.gesture_sets(group):
                raise ValueError('未知手势或数据集')
            dest = self.gesture_sets(group)[which]
            session = f'gesture-v1; group={group}; 2s raw; relax-action-release; {session}'
        else:
            if label not in LABELS.get(kind, TIERS): raise ValueError(f'未知档位 {label}')
            dest = self.sets[which][kind]
        if type(calibration) is not bool or calibration and (not self.multi or label not in calibration_voice.NAMES or task != 'effort' or countdown < 3):
            raise ValueError('校准口令仅支持八通道校准，放松倒数至少三秒')
        retry = task in ('gestures', 'diagnostic', 'factor-check', 'rehearsal') and self.issue is not None and self.issue.get('label') == label and self.issue.get('split') == which
        if retry: count = 1
        bounded = task in ('gestures', 'diagnostic', 'factor-check', 'rehearsal')
        budget_file = dest / f'capture-budget-{donning}.json'
        def read_budget():
            return json.loads(budget_file.read_text()) if budget_file.exists() else {'failures': 0, 'label': None, 'consecutive': 0}
        def save_budget(budget):
            budget_file.parent.mkdir(parents=True, exist_ok=True)
            temp = budget_file.with_suffix('.tmp')
            temp.write_text(json.dumps(budget, ensure_ascii=False))
            temp.replace(budget_file)
        def job():
            budget = read_budget() if bounded else {}
            if bounded and budget['failures'] >= 5:
                self.set_issue(dict(label=label, split=which, reason='本次佩戴已达 5 次失败上限；已结束试录，请检查后建立新的佩戴会话', stopped=True, limit_reached=True))
                return

            kept = attempted = 0
            self.stop_requested = False
            consecutive = budget.get('consecutive', 0) if budget.get('label') == label else 0
            for i in range(count):
                voice = None
                if calibration:
                    self.progress = {'label': label, 'take': i + 1, 'count': count, 'phase': '放松提示'}
                    voice = calibration_voice.CalibrationVoice(lambda: self.stop_requested)
                    try: voice.prepare(label)
                    except Exception:
                        voice.close(); self.progress = {}; raise
                for r in range(countdown, 0, -1):
                    if self.stop_requested: break
                    self.progress = {'label': label, 'take': i + 1, 'count': count, 'phase': f'{r}'}; time.sleep(1)
                if self.stop_requested:
                    if voice: voice.close()
                    self.say(f'{label}：已按要求停下这一批'); break
                attempted = i + 1
                self.progress = {'label': label, 'take': i + 1, 'count': count, 'phase': '准备录制'}
                cue = {}
                prep_ns = time.time_ns()
                def started(timing):
                    ack = timing['recording_ack_host_ns']
                    cue['ack_host_ns'] = ack
                    cue['pushed_host_ns'] = time.time_ns()
                    # String: the nanosecond clock does not survive a browser JSON number.
                    self.progress = {'label': label, 'take': i + 1, 'count': count, 'phase': 'NOW',
                                     'recording_ack_host_ns': str(ack)}
                    line = 'CUE ' + json.dumps(self.progress)
                    for q in list(self.rig.subscribers):
                        try: q.put_nowait(line)
                        except queue.Full: pass
                try:
                    if isinstance(self.rig, (Rig, FakeRig)) and kind == 'emg':
                        self._open_cue = cue
                        try:
                            info = self.rig.take(label, wear, dest, session, donning, on_started=started,
                                                 prep_host_ns=prep_ns, cue=cue, review_smr=task in ('diagnostic', 'factor-check', 'rehearsal'))
                        finally:
                            self._open_cue = None
                    else:
                        # 口令和动作窗同时起（不等播完）：NOW 对齐真正采样起点，用户听到「开始」动作就落在窗内。
                        if voice: voice.cue('rest' if label == 'mouse_rest' else 'go', wait=False)
                        if self.stop_requested: raise ValueError('校准已停止，未开始录制')
                        self.progress['phase'] = 'NOW'
                        info = self.rig.take(label, wear, dest, session, donning, cancelled=lambda: self.stop_requested, **take_extra) if calibration else self.rig.take(label, wear, dest, session, donning, **take_extra)
                        if voice:
                            # 文件已经保存；结束口令失败只提醒，不谎报数据没收下。
                            try: voice.cue('release')
                            except (ValueError, OSError) as e: self.say(f'结束口令未播放：{e}；本条已保存')
                except ValueError as e:
                    consecutive += 1
                    if bounded:
                        budget.update(failures=budget['failures'] + 1, label=label, consecutive=consecutive)
                        save_budget(budget)
                    limit_reached = bounded and budget['failures'] >= 5
                    if task in ('gestures', 'diagnostic', 'factor-check', 'rehearsal'):
                        self.set_issue(dict(label=label, split=which, reason=str(e),
                            rejected=consecutive, stopped=retry or consecutive >= 2 or limit_reached,
                            limit_reached=limit_reached, failures=budget['failures'],
                            saved_path=getattr(e, 'saved_path', None)))
                    self.say(f'{label} #{i + 1} 未收下：{e}')
                    if str(e).startswith('只收到 0 帧'):          # 一帧都没有 = 数据源断了，后面几条只会白录
                        self.say(f'{label}：没有收到任何数据，已停下这一批；检查手环连接后重试')
                        break
                    if task in ('gestures', 'diagnostic', 'factor-check', 'rehearsal') and (retry or consecutive >= 2 or limit_reached):
                        self.say('已暂停：先检查原因，下一次仅试录 1 条')
                        break
                    continue
                finally:
                    if voice: voice.close()
                consecutive = 0
                if bounded:
                    budget.update(label=label, consecutive=0)
                    save_budget(budget)
                if task in ('gestures', 'diagnostic', 'factor-check', 'rehearsal'): self.set_issue(None)
                if info.get('quality_warnings'):
                    self.say(('对照' if task == 'factor-check' else '诊断') + '已保存，待检查（未加入训练）：' + '；'.join(info['quality_warnings']))
                kept += 1; self.say(f'{label} #{i + 1} 收下 ' + ' '.join(f'{k}={v:.1f}' if isinstance(v, float) else f'{k}={v}' for k, v in info.items()))
                if getattr(self, 'studio', None) and self.multi:                 # 同一条同步落一份 .h5（studio sessions/），旧 .npz 不动
                    try:
                        r = self.studio.ingest_legacy(dest / label)
                        if r and not r[1]['ok']: self.say(f'  .h5 门禁：{r[1]["why"]}（旧流程已收下，仅新流程标红）')
                    except Exception as e: self.say(f'  .h5 同步失败（不影响录制）：{e}')
            self.progress = {}
            self.say(f'{label}：尝试 {attempted} 条，收下 {kept} 条进 {dest.name}/')
        self.start(f'录 {label}', job)

    def gesture_training(self, group='five', labels=GESTURES):
        root = self.single_models(group)
        runs, same_wear = [], same_wear_files(self.gesture_sets()['train'].parent.parent / 'archive')
        for p in sorted(root.glob('*/report.json'), reverse=True):
            r = json.loads(p.read_text())
            runs.append({k: v for k, v in r.items() if k not in ('manifest', 'test_manifest')} | {
                'id': p.parent.name, 'samples': class_fingerprints(r.get('manifest'), r.get('labels') or labels), 'rewear': rewear_score(r, same_wear)})
        frozen = (root / 'frozen.txt').read_text().strip() if (root / 'frozen.txt').exists() else None
        return {'runs': runs, 'frozen': frozen}

    def train_gestures(self, action, model='lda', run_id='', group=None, labels=None):
        import subprocess
        import uuid
        from emg_gesture_train import MODELS
        if action not in ('train', 'evaluate') or model not in MODELS:
            raise ValueError('未知训练操作或模型')
        group, labels = single_group(group, labels)
        root = self.single_models(group)
        frozen = root / 'frozen.txt'
        if action == 'train':
            if frozen.exists(): raise ValueError('模型已冻结并进入独立验收，不再使用本测试集选模型')
            run_id = time.strftime('%Y%m%d-%H%M%S') + '-' + model + '-' + uuid.uuid4().hex[:6]
        elif not run_id or run_id in ('.', '..') or Path(run_id).name != run_id or not (root / run_id / 'report.json').is_file():
            raise ValueError('模型记录不存在')
        elif frozen.exists() and frozen.read_text().strip() != run_id:
            raise ValueError('独立验收已绑定其他模型')
        runtime = Path(os.environ.get('OPENEMG_PY') or (HERE.parent / '.venv/bin/python'))
        isolate = []
        if not runtime.exists():
            # 打包 App：用自带 Python（numpy/scipy/sklearn 都在），深度模型除外。-s -E 不读用户的 site-packages / PYTHON* 变量；不用 -I（会把脚本目录也拿掉，import usb_emg 就断）
            runtime, isolate = Path(sys.executable), ['-s', '-E']
        def job():
            if action == 'evaluate':
                root.mkdir(parents=True, exist_ok=True); frozen.write_text(run_id)
            # 子进程不继承父进程的 -B，显式禁写缓存，避免改动已校验的安装包。
            args = [str(runtime), '-B', *isolate, str(HERE / 'emg_gesture_train.py'), action,
                    '--data', str(self.gesture_sets(group)['train'].parent), '--output', str(root / run_id), '--model', model, '--labels', ','.join(labels)]
            result = subprocess.run(args, capture_output=True, text=True, timeout=600)
            if result.returncode: raise RuntimeError(result.stderr[-1200:])
            self.say(('训练与验证完成' if action == 'train' else '独立验收完成') + '：' + run_id)
        self.start(f'{len(labels)} 类训练' if action == 'train' else '独立验收', job)

    # ---------------------------------------------------------------- 单通道：实时识别 ----

    def _stop_live1(self):
        # 当场退订（不等识别线程下一次醒来）：紧接着的录制要独占串口
        if self.live1: self.live1['stop'].set(); self.rig.unsubscribe(self.live1['q']); self.live1 = None

    def live1_action(self, body):
        """start：订阅单通道流，按 2 秒窗（与训练样本同长）每 250 ms 判一次，最近 3 次多数票出结果；
        结果作为 `P {json}` 行混进 /api/emg/stream，页面和波形走同一条连接。stop：停下并退订。"""
        if body.get('action') == 'stop':
            with self.live1_lock: self._stop_live1()
            return {'ok': True}
        if self.multi: raise ValueError('五类实时识别只用于 Cheez 单通道')
        if self.busy: raise ValueError(f'正在 {self.busy}，等它完再开识别')
        import pickle
        import emg_gesture_train as egt
        group, labels = single_group(body.get('group'), body.get('labels'))
        rid = Path(str(body.get('run_id') or '')).name or next((r['id'] for r in self.gesture_training(group, labels)['runs']), '')
        if rid in ('.', '..'): raise ValueError('模型记录不存在')
        folder = self.single_models(group) / rid
        if not rid or not (folder / 'report.json').is_file() or not (folder / 'model.pkl').is_file(): raise ValueError('这个动作组还没有训练好的模型')
        report = json.loads((folder / 'report.json').read_text())
        kind, names = report.get('model', 'lda'), tuple(report.get('labels') or egt.LABELS)   # 旧报告没有 labels：原五类
        if kind in egt.DEEP_MODELS: raise ValueError('实时识别只支持经典模型（lda / svm 等）')
        model = pickle.loads((folder / 'model.pkl').read_bytes())
        with self.live1_lock:
            self._stop_live1()
            q, stop = self.rig.subscribe(), threading.Event()
            live = self.live1 = {'run_id': rid, 'stop': stop, 'last': None, 'q': q}
        def run():
            buf, since, recent = np.zeros(0), 0, []
            try:
                while not stop.is_set():
                    try: line = q.get(timeout=1)
                    except queue.Empty: continue
                    f = line.split()
                    if len(f) < 4 or f[0] != 'S': continue
                    try: vals = np.asarray(f[3:], float)
                    except ValueError: continue
                    buf = np.concatenate([buf, vals])[-usb_emg.EMG_COUNT:]; since += len(vals)
                    if len(buf) < usb_emg.EMG_COUNT or since < usb_emg.EMG_HZ // 4: continue
                    since = 0
                    k = int(egt.predict(model, kind, usb_emg.clean(buf)[None])[0])
                    recent = (recent + [k])[-3:]
                    top = max(reversed(recent), key=recent.count)          # 平票（三次各不同）取最新一次
                    r = {'label': names[top], 'raw': names[k], 't': time.time()}
                    live['last'] = r
                    pkt = 'P ' + json.dumps(r)
                    for sub in list(self.rig.subscribers):
                        if sub is not q:
                            try: sub.put_nowait(pkt)
                            except queue.Full: pass
            except Exception as e:
                self.say(f'单通道识别停了：{e}')
            finally:
                self.rig.unsubscribe(q)
                if self.live1 is live: self.live1 = None
        threading.Thread(target=run, daemon=True).start()
        return {'ok': True, 'run_id': rid}

    def run(self, stage):
        import pipeline
        task = task_for(self.sets) if not self.multi else None      # the wristband has no pipeline task
        output = self.model_root and str(Path(self.model_root) / f"{time.strftime('%Y%m%d-%H%M%S')}-emg")
        def job():
            if self.multi and stage in ('gate', 'auto', 'evaluate'):
                # The wristband path has one job: which electrodes, how many, and the rewear number (G2).
                self.results['sweep'] = wl8.sweep(self.sets['train']['wl8'], self.sets['rewear']['wl8'])
            elif stage == 'gate':
                self.results['gate'] = pipeline.gate(task)
            elif stage == 'auto':
                self.results['auto'] = pipeline.auto(task, output)
            elif stage == 'evaluate':
                model = self.results.get('auto', {}).get('trained', {}).get('output')
                if not model: raise RuntimeError('先训练')
                self.results['evaluate'] = pipeline.evaluate(task, model)
            elif stage == 'lead':
                self.results['lead'] = usb_emg_imu.summarize(usb_emg_imu.load(self.sets['train']['emgimu']))
            else:
                raise ValueError(stage)
            self.say(f'{stage} 完成')
        self.start(stage, job)

    def evidence(self, folder=HERE.parent / 'evidence'):
        """Four-state, from what is on disk and what ran -- never from what the page claims."""
        c, r = self.counts(), self.results
        gate, auto, ev, lead, sweep = r.get('gate'), r.get('auto'), r.get('evaluate'), r.get('lead'), r.get('sweep')
        def state(cond_done, cond_pass, blocked=None):
            return blocked and f'阻塞（{blocked}）' or ('已实测通过' if cond_pass else '已实现未验收' if cond_done else '未实现')
        trained = bool(auto and auto.get('trained'))
        rewear = ev and ev['evaluation'].get('rewear')
        rows = [
            ('真 take 过门禁', state(bool(gate), bool(gate) and gate['separability']['status'] in ('ok', 'warn')),
             gate and gate['separability']['message']),
            ('三档训练器 + profile', state(trained, trained and (auto['trained']['metadata']['loo']['accuracy'] >= .8)),
             trained and json.dumps(auto['trained']['metadata']['profile']['cuts'], ensure_ascii=False)),
            ('跨佩戴验收', state(bool(ev), rewear_passed(rewear), None if ev else '未录 rewear'),
             ev and ev['evaluation'].get('message')),
            ('提前量', state(bool(lead), bool(lead) and lead.get('with_both_onsets', 0) >= 30), lead and lead.get('message')),
            ('腕带电极扫描 + G2 摘下重戴', state(bool(sweep), bool(sweep) and sweep.get('g2_passed')), sweep and sweep.get('message')),
        ]
        lines = [f'# EMG 采集与测试 — {time.strftime("%Y-%m-%d %H:%M")}', '',
                 f'台架：{self.rig.status()}', '',
                 '## 数据（磁盘上的 .npz 数）', json.dumps(c, ensure_ascii=False), '',
                 '## 四态', '| 项 | 状态 | 依据 |', '|---|---|---|',
                 *[f'| {n} | {s} | {d or "—"} |' for n, s, d in rows], '',
                 '## 日志', *self.log[-60:], '']
        folder.mkdir(exist_ok=True)
        path = folder / f'{time.strftime("%Y-%m-%d")}-emg-session.md'
        path.write_text('\n'.join(lines)); self.say(f'evidence → {path.name}')
        return {'path': str(path), 'rows': rows}


def server_for(session, port=8767):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_): pass
        def respond(self, code, data, ctype='application/json; charset=utf-8'):
            payload = data if isinstance(data, bytes) else json.dumps(data, ensure_ascii=False, default=str).encode()
            self.send_response(code); self.send_header('Content-Type', ctype); self.send_header('Content-Length', str(len(payload)))
            self.send_header('Cache-Control', 'no-store'); self.end_headers()
            try: self.wfile.write(payload)
            except (BrokenPipeError, ConnectionResetError): pass
        def local(self, mutation=False):
            hosts = {f'localhost:{self.server.server_port}', f'127.0.0.1:{self.server.server_port}'}
            return (self.headers.get('Host') in hosts and self.headers.get('Origin') in (None, *('http://' + h for h in hosts))
                    and (not mutation or self.headers.get('X-Mako-Collector') == '1'))
        def do_GET(self):
            if not self.local(): return self.respond(403, {'error': '仅本机'})
            from urllib.parse import urlsplit, parse_qs
            route = self.path.split('?', 1)[0]
            pages = {'/': 'emg_web.html', '/guide': 'emg_guide.html', '/pulse': 'emg_pulse.html', '/wristband': 'emg_wristband.html', '/studio': 'emg_studio.html', '/emg_demo.js': 'emg_demo.js'}
            if route == '/guide':
                from urllib.parse import urlsplit, parse_qs
                requested = parse_qs(urlsplit(self.path).query).get('project', [''])[0]
                if requested != (session.project or {}).get('id', ''):
                    return self.respond(409, '采集服务未绑定当前工程，请先切换服务对应的工程。', 'text/plain; charset=utf-8')
            if route in pages:
                ctype = 'text/javascript' if route.endswith('.js') else 'text/html; charset=utf-8'
                return self.respond(200, (HERE / pages[route]).read_bytes(), ctype)
            if route == '/api/emg/state':
                qs = parse_qs(urlsplit(self.path).query)
                try: return self.respond(200, session.state(include_training=qs.get('view') != ['capture'], group=qs.get('group', [None])[0],
                                                            labels=[l for l in qs.get('labels', [''])[0].split(',') if l]))
                except ValueError as e: return self.respond(400, {'error': str(e)})
            if route in ('/api/emg/ab', '/api/emg/wl8/runs', '/api/emg/wl8/run'):
                q = parse_qs(urlsplit(self.path).query); one = lambda k, d='': q.get(k, [d])[0]
                try:
                    if route == '/api/emg/ab':
                        if session.ab is None: return self.respond(409, {'error': '不是八通道模式'})
                        return self.respond(200, session.ab.state(one('hand', 'left'), int(one('donning', '1'))))
                    if route == '/api/emg/wl8/runs': return self.respond(200, session.wl8_runs())
                    return self.respond(200, session.wl8_run(one('id')))
                except ValueError as e: return self.respond(400, {'error': str(e)})
            if route == '/api/emg/wl8/cursor':                              # 轻量状态：App 主进程移动光标时每秒读一次当心跳
                if not session.cursor: return self.respond(409, {'error': '需要八通道手环'})
                return self.respond(200, session.cursor.state())
            if route == '/api/emg/stream8':
                requested = parse_qs(urlsplit(self.path).query).get('project', [''])[0]
                if requested != (session.project or {}).get('id', ''):
                    return self.respond(409, {'error': '工程不匹配'})
                if not session.multi:
                    return self.respond(409, {'error': '需要多通道手环'})
                frames = queue.Queue(maxsize=128)
                sample_index, dropped_frames, segment = 0, 0, 0
                stream_hz = int(getattr(session.rig, 'fs_Hz', 0) or session.desc.fs_Hz or wl8.EMG_HZ)
                def publish8(emg):
                    nonlocal sample_index, dropped_frames
                    packet = {'hz': stream_hz, 'unit': 'uV', 'segment': segment, 'sample_index': sample_index,
                              'dropped_frames': dropped_frames, 'samples': emg.tolist()}
                    sample_index += len(emg)
                    try: frames.put_nowait(packet)
                    except queue.Full: dropped_frames += len(emg)
                def publish_boundary(event):
                    nonlocal sample_index, segment
                    # 清掉待发旧段，保证边界不会被满队列丢弃；新段随后才入队。
                    while True:
                        try: frames.get_nowait()
                        except queue.Empty: break
                    segment += 1; sample_index = 0
                    frames.put_nowait(dict(event, type='boundary', segment=segment))
                if hasattr(session.rig, 'boundary_subscribers'):
                    session.rig.boundary_subscribers.append(publish_boundary)
                def publish_imu(imu):
                    try: frames.put_nowait({'type': 'imu', 'hz': 'irregular', 'samples': imu.tolist()})
                    except queue.Full: pass
                def publish_pred(r):
                    try: frames.put_nowait(dict(r, type='pred'))
                    except queue.Full: pass
                session.rig.frame_subscribers.append(publish8)
                session.rig.imu_subscribers.append(publish_imu)
                def publish_cursor(r):
                    try: frames.put_nowait(dict(r, type='cursor'))
                    except queue.Full: pass
                session.pred_subscribers.append(publish_pred)
                if session.cursor: session.cursor.subscribers.append(publish_cursor)
                def publish_studio(pkt):                                     # gate / rule / train / take 事件（studio_api）
                    try: frames.put_nowait(pkt)
                    except queue.Full: pass
                if getattr(session, 'studio', None): session.studio.event_subscribers.append(publish_studio)
                clock = None
                try:
                    try:
                        clock = session.rig.subscribe()
                    except wl8.NoReceiver as e:
                        self.respond(503, {'error': str(e), 'code': e.code})
                        return
                    self.send_response(200)
                    self.send_header('Content-Type', 'text/event-stream')
                    self.send_header('Cache-Control', 'no-store'); self.end_headers()
                    while True:
                        try: packet = frames.get(timeout=5)
                        except queue.Empty: self.wfile.write(b': keep\n\n'); self.wfile.flush(); continue
                        head = f"event: {packet['type']}\n" if packet.get('type') in ('imu', 'pred', 'cursor', 'boundary', 'gate', 'rule', 'train', 'take', 'lsl') else ''     # named events: onmessage-only pages ignore them
                        self.wfile.write((head + 'data: ' + json.dumps(packet) + '\n\n').encode()); self.wfile.flush()
                except (BrokenPipeError, ConnectionResetError, OSError): pass
                finally:
                    if hasattr(session.rig, 'boundary_subscribers'): session.rig.boundary_subscribers.remove(publish_boundary)
                    session.rig.imu_subscribers.remove(publish_imu)
                    session.pred_subscribers.remove(publish_pred)
                    if session.cursor: session.cursor.subscribers.remove(publish_cursor)
                    studio = getattr(session, 'studio', None)
                    if studio and publish_studio in studio.event_subscribers: studio.event_subscribers.remove(publish_studio)
                    session.rig.frame_subscribers.remove(publish8)
                    if clock is not None: session.rig.unsubscribe(clock)
                return
            if route == '/api/emg/stream':
                try: q = session.rig.subscribe()
                except wl8.NoReceiver as e: return self.respond(503, {'error': str(e), 'code': e.code})
                except Exception as e: return self.respond(503, {'error': str(e)})
                self.send_response(200); self.send_header('Content-Type', 'text/event-stream'); self.send_header('Cache-Control', 'no-store'); self.end_headers()
                try:
                    while True:
                        try: line = q.get(timeout=5)
                        except queue.Empty: self.wfile.write(b': keep\n\n'); self.wfile.flush(); continue
                        self.wfile.write(f'data: {line}\n\n'.encode()); self.wfile.flush()
                except (BrokenPipeError, ConnectionResetError, OSError): pass
                finally: session.rig.unsubscribe(q)
                return
            handled = session.studio and session.studio.handle('GET', route, parse_qs(urlsplit(self.path).query))    # studio_api 命名空间路由
            if handled: return self.respond(*handled)
            self.respond(404, {'error': route})
        def do_PUT(self): return self.do_POST()
        def do_POST(self):
            if not self.local(True): return self.respond(403, {'error': '仅本机，且要 X-Mako-Collector: 1'})
            if self.headers.get('X-Mako-Project', '') != (session.project or {}).get('id', ''):
                return self.respond(409, {'error': '工程不匹配，已拒绝写入；请重新打开当前工程采集页'})
            body = json.loads(self.rfile.read(int(self.headers.get('Content-Length') or 0)) or b'{}')
            handled = session.studio and session.studio.handle(self.command, self.path.split('?', 1)[0], None, body)    # studio_api 命名空间路由
            if handled: return self.respond(*handled)
            try:
                if self.path == '/api/emg/rehearsal':
                    return self.respond(200, session.rehearsal_start(body))
                if self.path == '/api/emg/diagnostic':
                    return self.respond(200, session.diagnostic_action(body.get('action'), int(body.get('donning', 0))))
                if self.path == '/api/emg/factor-check':
                    return self.respond(200, session.factor_check_action(body.get('action'), int(body.get('donning', 0)), body.get('factor', '')))
                if self.path == '/api/emg/cue-shown':
                    slot = session._open_cue
                    shown = body.get('shown_ms')
                    if slot is None:
                        return self.respond(409, {'error': '当前没有等待提示回执的录制'})
                    if isinstance(shown, bool) or not isinstance(shown, int) or shown < 1_000_000_000_000:
                        return self.respond(400, {'error': 'shown_ms 要是页面画出「做！」时的毫秒时间'})
                    if str(body.get('recording_ack_host_ns')) != str(slot.get('ack_host_ns')):
                        return self.respond(409, {'error': '提示回执与这一条对不上'})
                    phase = body.get('phase', 'action')
                    if phase not in ('relax', 'action', 'release'):
                        return self.respond(400, {'error': '未知提示阶段'})
                    slot.setdefault('phase_shown_ms', {})[phase] = shown
                    if phase == 'action': slot['shown_ms'] = shown
                    return self.respond(202, {'ok': True})
                if self.path == '/api/emg/record':
                    if body.get('action') == 'stop':
                        session.stop_requested = True
                        return self.respond(202, {'ok': True})
                    session.record(body['label'], int(body.get('count', 30)), body.get('set', 'train'), body.get('session', ''),
                                   int(body.get('donning', 1)), body.get('wear', 'high'), int(body.get('countdown', 3)), body.get('task', 'effort'), body.get('calibration', False), body.get('seconds', None), body.get('group'), body.get('strap_hole'), body.get('cable_dir'), body.get('ch0_site'))
                    return self.respond(202, {'ok': True})
                if self.path == '/api/emg/gesture-train':
                    session.train_gestures(body['action'], body.get('model', 'lda'), body.get('run_id', ''), body.get('group'), body.get('labels'))
                    return self.respond(202, {'ok': True})
                if self.path == '/api/emg/live1':
                    return self.respond(200, session.live1_action(body))
                if self.path == '/api/emg/run':
                    session.run(body['stage']); return self.respond(202, {'ok': True})
                if self.path == '/api/emg/ab':
                    return self.respond(200, session.ab_action(body))
                if self.path == '/api/emg/wl8/train':
                    session.wl8_train_start(body.get('labels')); return self.respond(202, {'ok': True})
                if self.path == '/api/emg/wl8/validation':
                    if session.validation is None: raise ValueError('需要八通道手环')
                    if body.get('action') == 'start' and session.cursor and session.cursor.mode != 'off': raise ValueError('先停止光标控制再开始连续验证')
                    return self.respond(200, session.validation.action(body))
                if self.path == '/api/emg/wl8/live':
                    return self.respond(200, session.live8_action(body))
                if self.path == '/api/emg/wl8/ctrl':
                    return self.respond(200, session.ctrl_action(body))
                if self.path == '/api/emg/wl8/cursor':
                    if not session.cursor: return self.respond(409, {'error': '需要八通道手环'})
                    if session.validation and session.validation.id and not session.validation.finalized and body.get('action') != 'stop': raise ValueError('连续验证期间不控制光标')
                    try: return self.respond(200, session.cursor.action(body))
                    except PermissionError as e: return self.respond(403, {'error': str(e)})
                if self.path == '/api/emg/wl8/ai':                           # ai_confirm.py 上报：开始等确认 / 判完
                    return self.respond(200, session.ai.update(body))
                if self.path == '/api/emg/wl8/action':                       # 手势 → 系统鼠标（App「用手势」页显式启用后才发）
                    if not session.cursor: return self.respond(409, {'error': '需要八通道手环'})
                    if session.validation and session.validation.id and not session.validation.finalized: raise ValueError('连续验证期间不操作鼠标')
                    if getattr(session.rig, 'replay', None): return self.respond(409, {'error': '回放数据不能操作鼠标'})
                    if body.get('action') in wl8_actions.ACTIONS and not session.live8:      # 识别没开就不该有手势动作（暂停 / 恢复不受限）
                        return self.respond(409, {'error': '实时识别未开启，不操作鼠标'})
                    if not hasattr(session, 'actions'): session.actions = wl8_actions.Actions()
                    try: return self.respond(200, session.actions.do(body))
                    except PermissionError as e: return self.respond(403, {'error': str(e)})
                if self.path == '/api/emg/evidence':
                    return self.respond(200, session.evidence())
            except (KeyError, ValueError, RuntimeError) as e:
                return self.respond(400, {'error': str(e)})
            self.respond(404, {'error': self.path})
    return ThreadingHTTPServer(('127.0.0.1', port), Handler)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--port', type=int, default=8767); p.add_argument('--serial', help='串口路径，默认按横幅找')
    p.add_argument('--fake', action='store_true', help='无板子：合成台架，走完整个流程'); p.add_argument('--data', help='--fake 时数据根目录（默认临时目录，不污染 emg-data）')
    p.add_argument('--project', type=Path, help='PrintThings 工程目录：数据与模型保存在该工程内')
    p.add_argument('--wl8', action='store_true', help='唯理 8 通道腕带（CP210x 串口）而不是 XIAO')
    p.add_argument('--replay', type=Path, help='八通道回放：把这段录音按原速循环推流（演示兜底；不能录制）')
    p.add_argument('--v12-synth', action='store_true', help='V12 自研前端协议的合成流（v12.py）：只看链路和页面，不能录制')
    p.add_argument('--model', help='折叠后的 CNN .npz（emg_wl8_cnn.py --save-model）：腕带流上实时出手势事件')
    p.add_argument('--channels', help='--model 用哪 4 个腕带电极（Meta 预训练的 npz 必须给）')
    p.add_argument('--device', help=f'设备描述 id（host/devices/*.json：{", ".join(device_desc.available())}）；旧开关 --fake/--wl8/--replay/--v12-synth 是它的别名')
    a = p.parse_args()
    # 设备描述决定 rig 类；命令行只补地址。旧开关映射：--fake --wl8 → fake；--fake → cheez 的假台架；--replay → replay；--v12-synth → v12；--wl8 → wl8；默认 cheez
    if a.device: desc = device_desc.load(a.device)
    elif a.v12_synth: desc = device_desc.load('v12')
    elif a.replay: desc = device_desc.load('replay')
    elif a.wl8: desc = device_desc.load('fake' if a.fake else 'wl8')
    else:
        desc = device_desc.load('cheez')
        if a.fake: desc.transport = {'kind': 'fake', 'match': {}}
    is_fake = desc.transport['kind'] == 'fake'
    if is_fake and a.project: p.error("假台架不可写入真实工程")
    chans = [int(c) for c in a.channels.split(',')] if a.channels else None
    # 八通道假手环默认瞬间完成一条（自检 / 门禁要快）；试用台设 YUANLI_FAKE_REALTIME=1 才一条录 2 秒、连续出流；Cheez 假台架一直是实时
    rig = build_rig(desc, serial=a.serial, replay=a.replay, realtime=(desc.decoder == 'cheez') or os.environ.get('YUANLI_FAKE_REALTIME') == '1')
    if is_fake:
        import tempfile
        root = Path(a.data) if a.data else Path(tempfile.mkdtemp(prefix='emg-fake-'))
        sets = {k: {kind: root / p.name for kind, p in v.items()} for k, v in SETS.items()}
        import pipeline; pipeline.REGISTRY = root / 'index.json'      # fake runs never enter the real registry
        print(f'FAKE rig ({desc.id}), data under {root}', flush=True)
        session = Session(rig, sets, model_root=root / 'models', model=a.model, channels=chans, desc=desc)
        studio_root = root / 'studio'
    else:
        sets, project, model_root = SETS, None, None
        studio_root = HERE / 'v12-captures' / 'studio'               # 原始生物信号留 host/v12-captures（gitignore）
        if a.project:
            from uuid import UUID
            root = a.project.resolve(strict=True)
            meta = json.loads((root / 'project.json').read_text())
            assert meta['format'] == 'printthings-project'
            UUID(meta['projectId'])
            project = {'id': meta['projectId'], 'name': meta['name']}
            sets = {k: {kind: root / 'data' / 'emg' / p.name for kind, p in v.items()} for k, v in SETS.items()}
            model_root = root / 'models' / 'emg'
            studio_root = root / 'data' / 'emg'
        session = Session(rig, sets, model_root=model_root, model=a.model, channels=chans, project=project, desc=desc)
    session.studio = studio_api.Studio(session, desc, studio_root)
    srv = server_for(session, a.port)
    print(f'MAKO emg collector: http://127.0.0.1:{srv.server_port}  device={desc.id}', flush=True)
    try: srv.serve_forever()
    except KeyboardInterrupt: pass
    finally: srv.server_close()

"""EMG Studio 的命名空间路由（EMG_STUDIO_V2_PLAN 附录 B.6）。`emg_web.py` 的 Handler 两行委托到 `Studio.handle()`。

    studio = Studio(session, desc, root)
    code, data = studio.handle('GET', '/api/device/state', query, body) or (None, None)

- 不用 eval；路由是显式表。路径参数一律限制在 root 之内。
- 设备热切换（select 到另一个 id）与真扫描属于 B5：这里 scan 只列描述目录，select 只接受当前设备。
- 事件（gate / rule / train / take）推给 event_subscribers，stream8 把它们转成 SSE 命名事件。
"""
import importlib.util
import json
import threading
import time
from pathlib import Path

import numpy as np

import dataset as dsmod
import device_desc
import gesture_pipe
import lsl_out
import migrate_legacy
import take_file
import trainer
from plugins import emg_analysis, rules, stats
from rig import AcqHandler

RING_SECONDS = 5
_BRINGUP_MOD = None


def _bringup_decoder():
    global _BRINGUP_MOD
    if _BRINGUP_MOD is None:
        p = Path(__file__).resolve().parent.parent / 'firmware' / 'c08b-bringup' / 'tools' / 'decode_bringup.py'
        spec = importlib.util.spec_from_file_location('c08b_decode_bringup', p)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _BRINGUP_MOD = mod
    return _BRINGUP_MOD


class Studio:
    def __init__(self, session, desc, root):
        self.session, self.desc, self.root = session, desc, Path(root)
        self.acq = AcqHandler(session.rig, desc)
        self.cur = None                                   # (meta, dir)
        self.take = None                                  # (TakeRecorder, label, started_wall)
        self.take_lock = threading.Lock()
        self.rules = rules.Engine()
        self.rules.subscribers.append(lambda ev: self._emit('rule', ev))
        self.gate = gesture_pipe.EnergyGate()
        self.blackbox = gesture_pipe.Blackbox(desc.fs_Hz, desc.n_channels)
        session.pred_subscribers.append(self._on_pred)
        self.lsl = None
        self.train_job = {'state': 'idle'}
        self.event_subscribers = []
        self.ring = np.zeros((0, desc.n_channels), np.float32)
        self.acq.subscribe(self._on_block)

    # ------------------------------------------------------------------ 内部
    def _emit(self, kind, data):
        pkt = dict(data, type=kind, device_id=self.desc.id, t=data.get('t', time.time()))
        for cb in list(self.event_subscribers):
            try:
                cb(pkt)
            except Exception:
                pass

    def _on_pred(self, pred):
        """能量门打开时，用最近 200 ms 的环缓改写后续订阅者看到的 top。门限为 0 时不改。"""
        if self.gate.min_rms_uv > 0 and len(self.ring):
            n = min(len(self.ring), max(1, int(0.2 * self.desc.fs_Hz)))
            rms = float(np.sqrt(np.mean(np.asarray(self.ring[-n:], float) ** 2)))
            label, blocked = self.gate.apply(pred.get('top', ''), rms)
            if blocked:
                pred['top'] = label
                pred['gated'] = True
                pred['rms_uv'] = rms
        self.rules.push(pred)

    def _on_block(self, b):
        keep = RING_SECONDS * self.desc.fs_Hz
        self.ring = np.concatenate([self.ring, b.uv])[-keep:]
        self.blackbox.push_batch(b.uv)
        if self.lsl:
            try:
                self.lsl.push(b)
            except Exception as e:
                self._emit('lsl', {'error': str(e)})
                self.lsl = None

    def _safe(self, rel):
        p = (self.root / rel).resolve()
        if self.root.resolve() not in p.parents:
            raise ValueError('文件必须在数据根目录内')
        if not p.exists():
            raise ValueError(f'文件不存在 {rel}')
        return p

    def _finish_take(self, rec, label):
        with self.take_lock:
            if self.take is None or self.take[0] is not rec or getattr(rec, 'finishing', False):
                return None
            rec.finishing = True                      # 只允许一个收尾者；文件写完前 recording 仍为 True
        try:
            meta, d = self.cur
            arrays = rec.arrays()
            n = len(arrays['uv'])
            path, gate = take_file.write(d, self.desc, arrays, label, session_meta=meta, seconds=rec.seconds, dropped=self.acq.dropped - rec.dropped0)
            self.cur = (json.loads((d / 'session.json').read_text()), d)
            out = {'file': str(path.relative_to(self.root)), 'label': label, 'frames': n, 'gate': gate}
            self._emit('gate', {'take': out['file'], 'ok': gate['ok'], 'why': gate['why']})
            return out
        finally:
            with self.take_lock:
                if self.take is not None and self.take[0] is rec:
                    self.take = None

    def ingest_legacy(self, folder):
        """老录制路径（Session.record → rig.take → wl8.save）每收下一条，把那条 .npz 同步转成 sessions/*-legacy_dNN/*.h5。
        老文件不动；失败只记日志，绝不影响录制。返回 (path, gate) 或 None。"""
        if self.desc.decoder != 'wl8':
            return None
        files = sorted(Path(folder).glob('*.npz'), key=lambda f: f.stat().st_mtime)
        if not files:
            return None
        f = files[-1]
        try:
            r = migrate_legacy.migrate_one(self.desc, f.parent.name, f, self.root, migrate_legacy.done_index(self.root))
        except Exception as e:
            self._emit('gate', {'take': f.name, 'ok': False, 'why': f'转 .h5 失败：{e}'})
            return None
        if r:
            path, gate = r
            self._emit('gate', {'take': str(path.relative_to(self.root)), 'ok': gate['ok'], 'why': gate['why'], 'legacy': f.name})
        return r

    # ------------------------------------------------------------------ 路由
    def handle(self, method, route, query=None, body=None):
        q = {k: v[0] if isinstance(v, list) else v for k, v in (query or {}).items()}
        body = body or {}
        fn = ROUTES.get((method, route))
        if fn is None:
            return None
        try:
            return 200, fn(self, q, body)
        except PermissionError as e:
            return 403, {'error': str(e)}
        except (ValueError, KeyError, OSError, device_desc.DescError) as e:
            return 400, {'error': str(e)}
        except RuntimeError as e:
            return 409, {'error': str(e)}

    # 设备
    def device_scan(self, q, body):
        out = []
        for i in device_desc.available():
            d = device_desc.load(i)
            out.append({'id': i, 'name': d.name, 'transport': d.transport['kind'], 'address': None,
                        'state': self.acq.state if i == self.desc.id else ('known' if d.transport['kind'] in ('fake', 'replay') else 'not_scanned')})
        return {'devices': out, 'current': self.desc.id, 'note': '真扫描（串口横幅 / BLE 广播）属于 B5；此处只列描述目录'}

    def device_select(self, q, body):
        did = body.get('id')
        if did != self.desc.id:
            if did not in device_desc.available():
                raise ValueError(f'未知设备 {did}')
            raise RuntimeError(f'热切换属于 B5：请用 --device {did} 重启采集服务')
        return {'device': self.desc.to_json(), 'state': self.acq.status()}

    def device_config_get(self, q, body):
        return self.desc.to_json()

    def device_config_put(self, q, body):
        if 'fs_Hz' in body:
            if body['fs_Hz'] not in self.desc.fs_options:
                raise ValueError(f'fs_Hz 只能是 {self.desc.fs_options}')
            if body['fs_Hz'] != self.desc.fs_Hz:
                raise RuntimeError('运行中改采样率属于 B5；重启时改描述文件')
        for ch in body.get('channels', []):
            i = int(ch['index'])
            if not 0 <= i < self.desc.n_channels:
                raise ValueError(f'通道 {i} 越界')
            if 'label' in ch:
                self.desc.channels[i]['label'] = str(ch['label'])[:24]
            if 'enabled' in ch:
                self.desc.channels[i]['enabled'] = bool(ch['enabled'])
        return self.desc.to_json()

    def device_state(self, q, body):
        st = self.acq.status()
        st['since'] = self.cur[0]['started'] if self.cur else None
        st['recording'] = bool(self.take)
        st['session'] = self.cur[0]['session'] if self.cur else None
        return st

    def device_pinout(self, q, body):
        mod = _bringup_decoder()
        did = str(q.get('device_id') or self.desc.id)
        out = dict(mod.channel_pinout(did))
        target_desc = self.desc
        if did and did != self.desc.id:
            try:
                target_desc = device_desc.load(out.get('device_id') or did)
            except Exception:
                target_desc = self.desc
        out['notes'] = target_desc.notes
        out['record_enabled'] = bool(target_desc.cap('record'))
        return out

    def device_bringup_decode(self, q, body):
        mod = _bringup_decoder()
        sample = body.get('sample')
        hex_str = mod.sample_hex(str(sample)) if sample else str(body.get('hex') or '').strip()
        if not hex_str:
            raise ValueError('请输入 BLE 0xFFFF 广播十六进制串或 97 字节报告十六进制串')
        res = mod.decode_any_hex(hex_str)
        res['input_hex'] = hex_str
        return res

    # 会话 / 段
    def session_start(self, q, body):
        if not self.desc.cap('record'):
            raise PermissionError(f'{self.desc.id} 不能录制')
        if self.cur:
            raise RuntimeError(f'会话 {self.cur[0]["session"]} 未结束')
        meta, d = take_file.new_session(self.root, self.desc, subject=body.get('subject', 'S'), donning=int(body.get('donning', 1)),
                                        hand=body.get('hand', ''), placement=body.get('placement', ''), notes=body.get('notes', ''))
        self.cur = (meta, d)
        self.acq.start()
        return {'session': meta}

    def session_stop(self, q, body):
        if not self.cur:
            raise RuntimeError('没有进行中的会话')
        if self.take:
            self.take_stop(q, body)
        meta = take_file.end_session(self.cur[1])
        self.cur = None
        self.acq.stop()                               # 与 session_start 的 acq.start() 对称；老路径的实时流不受影响
        return {'session': meta['session'], 'takes': meta['takes']}

    def take_start(self, q, body):
        if not self.cur:
            raise RuntimeError('先 /api/session/start')
        if self.take:
            raise RuntimeError('已有一段在录')
        seconds = body.get('seconds')
        seconds = float(seconds) if seconds is not None else None
        label = str(body.get('label') or 'take')
        rec = self.acq.record(seconds)
        rec.dropped0 = self.acq.dropped
        with self.take_lock:
            self.take = (rec, label, time.time())
        if seconds is not None:
            def finish():
                rec.wait(seconds + 10)
                self._finish_take(rec, label)
            threading.Thread(target=finish, daemon=True).start()
        self._emit('take', {'label': label, 'seconds': seconds, 'state': 'recording'})
        return {'take': {'label': label, 'seconds': seconds, 'segment': rec.segment}}

    def take_stop(self, q, body):
        if not self.take:
            raise RuntimeError('没有在录')
        rec, label, _ = self.take
        self.acq.stop_record() if not rec.done else None
        return self._finish_take(rec, label) or {'file': None, 'gate': None, 'note': '已由定时结束写入'}

    def take_mark(self, q, body):
        if not self.take:
            raise RuntimeError('没有在录')
        rec, _, _ = self.take
        return {'t_s': rec.mark(body.get('label', 'mark'), body.get('source', 'ui'))}

    # 文件
    def files_list(self, q, body):
        return {'sessions': take_file.list_sessions(self.root), 'takes': [dict(t, file=str(Path(t.pop('path')).relative_to(self.root))) for t in take_file.list_takes(self.root, q.get('session'))]}

    def files_open(self, q, body):
        p = self._safe(q['file'])
        frm, to = int(q.get('from', 0)), q.get('to')
        to = int(to) if to else None
        decim = max(1, int(q.get('decim', 1)))
        d = take_file.read(p, ('uv', 'di'), frm=frm, to=to)
        uv = d['uv'][::decim]
        return {'header': d['header'], 'from': frm, 'to': to, 'decim': decim, 'n': int(len(uv)), 'uv': uv.tolist(),
                'di': d['di'][::decim].tolist() if d.get('di') is not None else None, 'events': take_file.events(p)}

    def files_export_txt(self, q, body):
        p = self._safe(body['file'])
        out = take_file.export_txt(p, converted=bool(body.get('converted', True)))
        return {'path': str(out)}

    # 数据集
    def dataset_list(self, q, body):
        return {'datasets': dsmod.list_datasets(self.root)}

    def dataset_save(self, q, body):
        ds = dsmod.build(self.root, str(body['name']), body.get('label_map') or {}, body.get('session_split'), body.get('device_id'))
        p = dsmod.save(ds, self.root)
        return {'path': str(p), 'summary': ds['summary'], 'rejected': ds['rejected']}

    def dataset_validate(self, q, body):
        ds = dsmod.load(self.root, str(body.get('name') or q.get('name')))
        return {'ok': True, 'summary': ds['summary'], 'fingerprint': dsmod.fingerprint(ds)}

    # 训练
    def train_start(self, q, body):
        if self.train_job.get('state') == 'running':
            raise RuntimeError('已有训练在跑')
        ds = dsmod.load(self.root, str(body['dataset']))
        kind = body.get('trainer', 'lda')
        if kind not in trainer.TRAINERS:
            raise ValueError(f'trainer 必须是 {trainer.TRAINERS}')
        seed, epochs = int(body.get('seed', 0)), int(body.get('epochs', 40))
        feature_mode = body.get('feature_mode', 'bands5')
        self.train_job = {'state': 'running', 'trainer': kind, 'dataset': ds['name'], 'feature_mode': feature_mode, 'started': time.time(), 'progress': []}

        def progress(p):
            self.train_job['progress'].append(p)
            self._emit('train', {'run_id': self.train_job.get('run_id'), **p})

        def work():
            try:
                run = trainer.train(ds, self.root, self.desc, trainer=kind, seed=seed, out_root=self.root / 'models', progress=progress, epochs=epochs, feature_mode=feature_mode)
                self.train_job.update(state='done', run_id=run['id'], metrics=run['metrics'], note=run.get('note'))
            except Exception as e:
                self.train_job.update(state='error', error=str(e))
                self._emit('train', {'stage': 'error', 'error': str(e)})
        threading.Thread(target=work, daemon=True).start()
        return {'ok': True, 'job': {k: v for k, v in self.train_job.items() if k != 'progress'}}

    def train_runs(self, q, body):
        return {'runs': trainer.runs(self.root / 'models'), 'job': {k: v for k, v in self.train_job.items() if k != 'progress'},
                'production': trainer.production(self.root / 'models')}

    def train_freeze(self, q, body):
        return trainer.freeze(self.root / 'models', str(body['run_id']))

    def gesture_state(self, q, body):
        return {'feature_modes': list(gesture_pipe.FEATURE_MODES), 'min_rms_uv': self.gate.min_rms_uv,
                'rest_label': self.gate.rest_label, 'blackbox_samples': self.blackbox.samples,
                'blackbox_seconds': round(self.blackbox.samples / self.desc.fs_Hz, 3)}

    def gesture_gate(self, q, body):
        self.gate.set(body.get('min_rms_uv', 0), body.get('rest_label', self.gate.rest_label))
        return self.gesture_state(q, body)

    def gesture_decide(self, q, body):
        label, blocked = self.gate.apply(body['label'], body['rms_uv'])
        return {'label': label, 'blocked': blocked, 'min_rms_uv': self.gate.min_rms_uv}

    def gesture_fewshot(self, q, body):
        mode = body.get('feature_mode', 'combined')
        k = int(body.get('k', 1))
        if body.get('dataset'):
            ds = dsmod.load(self.root, str(body['dataset']))
            recs = dsmod.records(ds, self.root, 'train')
        else:
            labels = body.get('labels') or []
            if not labels:
                raise ValueError('需要 dataset 或 labels')
            recs = gesture_pipe.load_label_dir(self.root / 'emg-wl8-data', labels)
        run = gesture_pipe.few_shot(recs, self.desc.fs_Hz, mode, k, self.root / 'models', trainer.features)
        run.pop('artifact', None)
        return run

    def gesture_dump(self, q, body):
        if self.blackbox.samples < int(0.2 * self.desc.fs_Hz):
            raise RuntimeError(f'黑匣子只有 {self.blackbox.samples / self.desc.fs_Hz:.2f} s，不足 0.2 s')
        out = self.root / 'exports' / f'blackbox-{time.strftime("%Y%m%dT%H%M%S")}.npz'
        out.parent.mkdir(parents=True, exist_ok=True)
        self.blackbox.save(out)
        return {'path': str(out), 'samples': self.blackbox.samples}

    # 插件
    def plugin_stats(self, q, body):
        w = float(q.get('window_s', 1))
        n = int(w * self.desc.fs_Hz)
        if len(self.ring) < n:
            raise RuntimeError(f'缓冲只有 {len(self.ring) / self.desc.fs_Hz:.2f} s，不足 {w} s')
        return stats.compute(self.ring[-n:], self.desc.fs_Hz, labels=self.desc.labels())

    def plugin_emg_analysis(self, q, body):
        p = self._safe(body['file'])
        d = take_file.read(p, ('uv',), frm=int(body.get('from', 0)), to=body.get('to'))
        mvc = None
        if body.get('mvc_file'):
            m = take_file.read(self._safe(body['mvc_file']), ('uv',))['uv']
            env = emg_analysis.envelope(m, self.desc.fs_Hz, (body.get('params') or {}).get('band_Hz', emg_analysis.DEFAULTS['band_Hz']))
            mvc = env.max(0).tolist()
        r = emg_analysis.analyze(d['uv'], self.desc.fs_Hz, body.get('params'), mvc_uv=mvc, labels=self.desc.labels())
        out = self.root / 'exports' / f'{p.parent.name}_{p.stem}_emg_analysis.csv'
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(emg_analysis.to_csv(r))
        return dict(r, csv=str(out), file=body['file'])

    def rules_get(self, q, body):
        return {'rules': self.rules.rules, 'events': self.rules.events[-50:]}

    def rules_put(self, q, body):
        rs = body if isinstance(body, list) else body.get('rules', [])
        self.rules.set_rules(rs)
        return {'rules': self.rules.rules}

    def lsl_put(self, q, body):
        if body.get('enabled'):
            if not lsl_out.available():
                return {'ok': False, 'enabled': False, 'why': '环境没有 pylsl'}
            if not self.lsl:
                self.lsl = lsl_out.Outlet(self.desc)
            return {'ok': True, 'enabled': True, 'stream_name': self.lsl.name}
        if self.lsl:
            self.lsl.close()
            self.lsl = None
        return {'ok': True, 'enabled': False}


ROUTES = {
    ('POST', '/api/device/scan'): Studio.device_scan,
    ('POST', '/api/device/select'): Studio.device_select,
    ('GET', '/api/device/config'): Studio.device_config_get,
    ('PUT', '/api/device/config'): Studio.device_config_put,
    ('GET', '/api/device/state'): Studio.device_state,
    ('GET', '/api/device/pinout'): Studio.device_pinout,
    ('POST', '/api/device/bringup_decode'): Studio.device_bringup_decode,
    ('POST', '/api/session/start'): Studio.session_start,
    ('POST', '/api/session/stop'): Studio.session_stop,
    ('POST', '/api/take/start'): Studio.take_start,
    ('POST', '/api/take/stop'): Studio.take_stop,
    ('POST', '/api/take/mark'): Studio.take_mark,
    ('GET', '/api/files/list'): Studio.files_list,
    ('GET', '/api/files/open'): Studio.files_open,
    ('POST', '/api/files/export_txt'): Studio.files_export_txt,
    ('GET', '/api/dataset/list'): Studio.dataset_list,
    ('PUT', '/api/dataset/save'): Studio.dataset_save,
    ('POST', '/api/dataset/validate'): Studio.dataset_validate,
    ('POST', '/api/train/start'): Studio.train_start,
    ('GET', '/api/train/runs'): Studio.train_runs,
    ('POST', '/api/train/freeze'): Studio.train_freeze,
    ('GET', '/api/gesture/state'): Studio.gesture_state,
    ('PUT', '/api/gesture/gate'): Studio.gesture_gate,
    ('POST', '/api/gesture/decide'): Studio.gesture_decide,
    ('POST', '/api/gesture/fewshot'): Studio.gesture_fewshot,
    ('POST', '/api/gesture/blackbox/dump'): Studio.gesture_dump,
    ('GET', '/api/plugin/stats'): Studio.plugin_stats,
    ('POST', '/api/plugin/emg_analysis'): Studio.plugin_emg_analysis,
    ('GET', '/api/rules'): Studio.rules_get,
    ('PUT', '/api/rules'): Studio.rules_put,
    ('PUT', '/api/lsl'): Studio.lsl_put,
}

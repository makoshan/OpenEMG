"""专训短窗与运动校准；保留旧模型的一秒特征，不混用动作练习标签。"""
from pathlib import Path
import json
from zipfile import BadZipFile
from zlib import error as CompressionError
import numpy as np
from scipy.signal import welch, butter, sosfiltfilt


def install(trainer, profiles, wl8):
    gap_epoch = [0]
    original_feed = wl8.Wl8Rig._feed
    def feed(rig, raw):
        _, _, seq, _ = rig.decode(rig.buf + raw)                       # 用 rig 自己的解码：wl18 是 41/59 字节帧，拿 29 字节解会误报丢包
        if len(seq):
            last = getattr(rig, '_pt_last_sequence', None)
            lost = wl8.dropped(seq) + (((int(seq[0]) - last - 1) % 256) if last is not None else 0)
            rig._pt_last_sequence = int(seq[-1])
            if lost: gap_epoch[0] += 1
        return original_feed(rig, raw)
    wl8.Wl8Rig._feed = feed
    original_load, original_live = trainer.load, trainer.LivePredictor
    sets = [set(p['labels']) for p in profiles.values() if p.get('protocol')]
    by_labels = {frozenset(p['labels']): p for p in profiles.values() if p.get('protocol')}
    sos = butter(4, [20, 450], 'bandpass', fs=trainer.FS, output='sos')

    def features(e):
        e = np.asarray(e, float)
        f, power = welch(e - e.mean(0), trainer.FS, nperseg=400, axis=0)
        ok = f >= 20
        for k in range(1, 20):
            ok &= np.abs(f - 50 * k) > 4
        return np.array([np.log(power[ok & (f >= lo) & (f < hi)].mean(0) + 1e-9) for lo, hi in trainer.BANDS]).ravel()

    # 校准组的放松条剔除（相对规则，沿用 host 普通训练「放松底噪 > 放松中位数 × 1.5」的思路，但校准每类只有 3 条，用下四分位 × 3）：
    # 2026-10-10 一条别的会话写进真实工程的放松样本 8 路 3–12 万 µV 混进第 10 次佩戴训练集。全工程 575 条按绝对幅度没有缺口
    #（真实样本最高一路 2.4 万、中位 2.4 万），所以不设绝对 µV 阈值；只在同一次佩戴的放松条内部比。
    # 线 = max(下四分位 × 3, 1000 µV)：真实 49 条放松（第 5–11 次）只按 ×3 会剔 37%，加 1000 µV 下限剔 22%、目标垃圾（1.3–4.4 万）全中（复核 P2）
    REST_FACTOR, REST_FLOOR_UV = 3., 1000.
    def rest_outliers(rms_by_file):
        """{文件: 八路中位 RMS} → 要剔除的文件列表：> max(下四分位 × REST_FACTOR, REST_FLOOR_UV)。"""
        if len(rms_by_file) < 2: return []
        cut = max(REST_FACTOR * float(np.percentile(list(rms_by_file.values()), 25)), REST_FLOOR_UV)
        return [f for f, r in rms_by_file.items() if r > cut]
    trainer.REST_FACTOR, trainer.REST_FLOOR_UV, trainer.rest_outliers = REST_FACTOR, REST_FLOOR_UV, rest_outliers

    def donning_of(f):
        try:
            m = json.loads(f.with_suffix('.json').read_text()); return m.get('donning') if isinstance(m, dict) else None
        except (OSError, ValueError): return None

    def window(e, half, align):
        """每条独立录制只取一个短窗，邻近窗不分到训练和验证两边。
        校准组对准动作：20–450 Hz 滤波后 0.2 s 平滑能量最大处（2026-10-07 第 5/6 次佩戴：正中 0.2 s 留一 52%，对准 0.4 s 68–85%）。"""
        mid = len(e) // 2
        if align and len(e) > 2 * half:
            env = np.convolve((sosfiltfilt(sos, e, axis=0) ** 2).sum(1), np.ones(400) / 400, 'same')
            mid = half + int(np.argmax(env[half:len(e) - half]))
        return e[mid - half:mid + half]

    def load(root, labels, since=None):
        if set(labels) not in sets:
            return original_load(root, labels, since)
        p = by_labels[frozenset(labels)]; half = int(p.get('windowMs', 200)) // 2 * trainer.FS // 1000
        calibrate = bool(p.get('calibrate'))
        files = [(label, f) for label in labels for f in sorted((Path(root) / label).glob('*.npz')) if not (since and f.stat().st_mtime < since)]
        if calibrate:
            # 每次佩戴校准：只用编号最大（= 这次）的佩戴训练；重戴目录不参与，分数只报同次佩戴留一。
            if Path(root).name.endswith('-rewear'): return []
            wears = [d for _, f in files if type(d := donning_of(f)) is int]
            if not wears: return []                               # 一个带佩戴编号的都没有：什么都不训，别把无编号文件全选进来
            current = max(wears)
            files = [(l, f) for l, f in files if donning_of(f) == current]
        out = []
        for label, f in files:
            with np.load(f, allow_pickle=False) as z:
                e = z['emg_uv'].astype(float)
            if len(e) < 2 * half: continue                        # 比窗口还短的样本跳过，负索引会回绕
            x = features(window(e, half, calibrate))
            rms_ch = np.std(e, axis=0)
            out.append((label, x, dict(file=f.name, mtime=f.stat().st_mtime, rms=float(np.median(rms_ch)), rms_ch=rms_ch, ptp=trainer.ptp_windows(e), donning=donning_of(f))))
        if calibrate:
            rests = [l for l in labels if p['gestures'].get(l, {}).get('kind') == 'rest']
            bad = set(rest_outliers({f'{l}/{m["file"]}': m['rms'] for l, _, m in out if l in rests}))   # 和 emg8-server 的训练包装同一规则、同一输入
            out = [r for r in out if f'{r[0]}/{r[2]["file"]}' not in bad]
        return out

    class ShortLive(original_live):
        POOL_STEPS = 8

        def __init__(self, path, *args, **kwargs):
            with np.load(path, allow_pickle=False) as z:
                ms = int(z['window_ms']) if 'window_ms' in z else 1000
                short = bool(z['short']) if 'short' in z else ms < 1000     # 旧模型没有 short 标志：沿用「不足 1 s 即短窗」
            self.shadow = None; self.shadow_error = 'not_trained'; self.shadow_pending = []
            self.shadow_epoch = 0
            self.short = short
            self.gap_epoch = gap_epoch[0]
            self.pool = []; self.rest_streak = 0
            super().__init__(path, window_s=ms / 1000 if self.short else 1., step_s=.05 if self.short else .1)
            self.pool_steps = 8 if self.win < 1000 else 3
            sidecar = Path(path).with_name('adaptive-intent.json')
            if sidecar.exists():
                try:
                    import adaptive_intent, hashlib
                    data = adaptive_intent.load(sidecar)
                    if data.get('legacy_sha256') != hashlib.sha256(Path(path).read_bytes()).hexdigest():raise ValueError('模型配对不符')
                    if set(data['classes']) != set(self.m['classes']):raise ValueError('类别不符')
                    self.shadow = adaptive_intent.Stream(data); self.shadow_error = ''
                except Exception as e: self.shadow_error = type(e).__name__

        def reset(self):
            super().reset()
            if self.shadow is not None: self.shadow.reset()
            self.shadow_pending = []; self.shadow_epoch += 1
            self.pool = []; self.rest_streak = 0

        def set_mask(self, lanes):
            super().set_mask(lanes)
            # 候选当前要求八路完整；屏蔽路后不偷偷复用原八路模型。
            if self.shadow is not None:self.shadow.reset()
            self.shadow_pending = []; self.shadow_epoch += 1
            self.pool = []; self.rest_streak = 0

        def shadow_result(self, emg):
            if self.shadow is None:return dict(mode='shadow', status=self.shadow_error, events=[])
            if self.mask:return dict(mode='shadow', status='masked_channels_unsupported', events=[])
            try:
                ticks = self.shadow.push(emg)
                self.shadow_pending.extend(dict(t, epoch=self.shadow_epoch) for t in ticks)
                return dict(mode='shadow', status='active', ticks=self.shadow_pending,
                            events=[t for t in self.shadow_pending if t['event']], donning=self.shadow.model.data['donning'],
                            sample_cursor=self.shadow.samples, epoch=self.shadow_epoch)
            except Exception as e:
                self.shadow.reset(); self.shadow_pending=[]; self.shadow_epoch+=1
                return dict(mode='shadow', status=type(e).__name__, events=[])

        def push(self, emg):
            if not self.short:
                return super().push(emg)
            if self.gap_epoch != gap_epoch[0]:
                self.gap_epoch = gap_epoch[0]; self.reset()
                return dict(probs={}, top='', xy=[0, 0])
            e = np.asarray(emg, float)
            if e.ndim != 2 or e.shape[1] != 8 or not np.isfinite(e).all():
                self.reset()
                return None
            shadow = self.shadow_result(e)
            self.buf = np.concatenate([self.buf, e])[-self.win:]
            self.since += len(e)
            if len(self.buf) < self.win or self.since < self.step:
                return None
            self.since = 0
            x = features(self.buf)[None]
            _, p = trainer.scores(self.m, x)
            p_out = p[0]
            xy = (x @ self.W)[0]
            self.shadow_pending = []
            extra = {}
            if getattr(self, 'rest_rms', None) is not None:
                keep_ch = [i for i in range(8) if i + 1 not in getattr(self, 'mask', ())]
                if keep_ch:
                    rms_w = np.std(self.buf[:, keep_ch], axis=0)
                    snr_db = float(20.0 * np.log10(np.percentile(rms_w / np.maximum(self.rest_rms[keep_ch], 1e-6), 75) + 1e-9))
                else:
                    snr_db = 0.0
                score_wt = float(np.clip((snr_db + 3.0) / 20.0, 0.1, 1.0))
                rest_cls = next((c for c in self.m['classes'] if 'rest' in c), None)
                raw_top = self.m['classes'][int(p[0].argmax())]
                if raw_top == rest_cls and snr_db < 1.5:
                    self.rest_streak += 1
                    if self.rest_streak >= 2:
                        self.pool.clear()
                else:
                    self.rest_streak = 0
                wt = float(p[0].max()) * score_wt
                self.pool.append((p[0], wt))
                if len(self.pool) > getattr(self, 'pool_steps', self.POOL_STEPS):
                    self.pool.pop(0)
                w_sum = sum(wk for _, wk in self.pool)
                p_out = sum(pk * wk for pk, wk in self.pool) / max(w_sum, 1e-12)
                p_cal = trainer.calibrated_probs(self.m, x, getattr(self, 'temp', 1.0))[0]
                extra = dict(noul=round(float(p_cal.max()), 3), score=round(score_wt, 3), snr_db=round(snr_db, 2))
            return dict(adaptive_intent=shadow, probs={c: round(float(v), 3) for c, v in zip(self.m['classes'], p_out)},
                        top=self.m['classes'][int(p_out.argmax())], xy=[float(v) for v in xy], **extra)

    trainer.load, trainer.LivePredictor = load, ShortLive
    trainer.meta_features = features


def calibrate(root, since=None):
    """按实际佩戴学习两方向的陀螺仪向量；编号混用、缺 IMU、方向不一致都不放行。"""
    pairs = [('motion_cw', 'motion_ccw'), ('motion_up', 'motion_down'), ('motion_left', 'motion_right')]
    vectors, wears, bias_samples = {}, set(), []
    try:
        base_files = [(label, f, json.loads(f.with_suffix('.json').read_text())) for label in ['motion_rest', 'motion_hold', 'motion_other'] for f in (root / 'emg-wl8-data' / label).glob('*.npz') if not since or f.stat().st_mtime >= since]
        if not base_files or any(not isinstance(m, dict) or type(m.get('donning')) is not int or not 1 <= m['donning'] <= 20 for _, _, m in base_files):
            raise ValueError('基础数据缺少有效佩戴编号')
        current_wear = max(m['donning'] for _, _, m in base_files)
        if any(sum(1 for l, _, m in base_files if l == label and m['donning'] == current_wear) < 5 for label in ['motion_rest', 'motion_hold', 'motion_other']):
            raise ValueError('当前佩戴的三个基础状态各需 5 条；旧数据会保留')
        for label in ['motion_rest', 'motion_hold', 'motion_other']:
            for f in (root / 'emg-wl8-data' / label).glob('*.npz'):
                if since and f.stat().st_mtime < since: continue
                wear = json.loads(f.with_suffix('.json').read_text())['donning']
                if wear != current_wear: continue
                if type(wear) is not int: raise ValueError('佩戴编号无效')
                wears.add(wear)
                if label == 'motion_rest':
                    with np.load(f, allow_pickle=False) as z:
                        imu = z['imu']; scale = float(z['gyro_scale'])
                    if imu.dtype.kind not in 'fiu' or imu.ndim != 2 or imu.shape[1] != 6 or len(imu) < 20 or not np.isfinite(imu).all() or not np.isfinite(scale) or abs(scale - .0012) > 1e-9:
                        raise ValueError('放松基线缺少有效陀螺仪数据')
                    bias_samples.append(imu[:, :3] * scale)
        if len(wears) != 1 or not bias_samples:
            raise ValueError('运动校准需要同一次佩戴的基础数据与陀螺仪基线')
        donning = next(iter(wears))
        bias = np.median(np.concatenate(bias_samples), axis=0)
        quiet_limit = max(.15, float(np.percentile(np.linalg.norm(np.concatenate(bias_samples) - bias, axis=1), 99)) * 3)
        for label in sum(([a, b] for a, b in pairs), []):
            rows = []
            for f in sorted((root / 'emg-wl8-data' / label).glob('*.npz')):
                if since and f.stat().st_mtime < since: continue
                m = json.loads(f.with_suffix('.json').read_text())
                if isinstance(m, dict) and type(m.get('donning')) is int and m['donning'] < donning: continue
                if not isinstance(m, dict) or type(m.get('donning')) is not int or m.get('donning') != donning:
                    raise ValueError('校准与基础模型佩戴编号不同，请按当前佩戴重新采集')
                with np.load(f, allow_pickle=False) as z:
                    imu = z['imu']; scale = float(z['gyro_scale'])
                if imu.dtype.kind not in 'fiu' or imu.ndim != 2 or imu.shape[1] != 6 or len(imu) < 20 or not np.isfinite(imu).all() or not np.isfinite(scale) or abs(scale - .0012) > 1e-9:
                    raise ValueError('运动样本缺少有效陀螺仪数据')
                gyro = imu[:, :3] * scale - bias
                speed = np.linalg.norm(gyro, axis=1)
                if np.sum(speed > quiet_limit) < 4: raise ValueError('运动幅度不足，请小幅但明确地转动')
                # 取累计转角离起点最远的那一刻：捏住时手腕的小抖动、松开后的复位都盖不过主动作。
                # 旧做法取「第一次超阈值的一段」，2026-10-05 实录里取到的是捏住抖动，六向全成 +x。
                angle = np.cumsum(gyro, axis=0) * (float(m.get('seconds') or 2) / len(gyro))
                v = angle[int(np.argmax(np.linalg.norm(angle, axis=1)))]
                if np.linalg.norm(v) < .05: raise ValueError('未检测到单向运动，请转到位停住再松开复位')
                rows.append(v / np.linalg.norm(v))
            if len(rows) < 3: raise ValueError('六个运动方向各需至少 3 条校准样本')
            v = np.mean(rows, axis=0)
            if np.linalg.norm(v) < .8: raise ValueError('同一方向动作不一致，请检查动作后重录')
            vectors[label] = (v / np.linalg.norm(v)).tolist()
        for a, b in pairs:
            if np.dot(vectors[a], vectors[b]) > -.7:
                raise ValueError('相反方向没有分开，请检查顺逆时针和上下左右')
        axes = [np.array(vectors[a]) for a, _ in pairs]
        # 转腕、上下摆、左右摆要能分开，避免同一个运动同时映射到不同动作。
        if any(abs(np.dot(a, b)) > .8 for i, a in enumerate(axes) for b in axes[i + 1:]):
            raise ValueError('运动轴太接近，请分别转腕、上下摆和左右摆')
        return dict(status='calibrated', donning=donning, bias=bias.tolist(), vectors=vectors, reason='方向已校准；组合动作与重戴效果尚未实测')
    except (ValueError, OSError, KeyError, EOFError, TypeError, AttributeError, BadZipFile, CompressionError) as e:
        return dict(status='unverified', reason=str(e))


def sequence_trials(root, model, trainer, since=None):
    """基础模型之外的独立组合录制，用相同短窗出时间序列；界面共用时序解码器核验。"""
    cases = ['meta_index_tap', 'meta_middle_tap', 'meta_middle_double', 'meta_middle_long', 'meta_side_double']
    out = []
    # 与 install 的短窗特征保持完全同口径；直接复用 load 时注册的函数。
    for label in cases:
        for f in sorted((root / 'emg-wl8-data' / label).glob('*.npz')):
            if since and f.stat().st_mtime < since: continue
            try:
                with np.load(f, allow_pickle=False) as z:
                    e = z['emg_uv']
                    if 'seq' not in z: raise ValueError('组合样本缺少序号，丢帧未核对，请重录')
                    seq = z['seq']
                    if seq.ndim != 1 or seq.dtype.kind not in 'iu' or len(seq) < len(e) or np.any(seq < 0) or np.any(seq > 255) or np.any((np.diff(seq.astype(np.int16)) - 1) % 256):
                        raise ValueError('组合样本有序号缺口，不能检验时序，请重录')
                    if 'emg_hz' in z and int(z['emg_hz']) != 2000: raise ValueError('组合样本采样率不符，请重录')
                meta = json.loads(f.with_suffix('.json').read_text())
                if not isinstance(meta, dict) or type(meta.get('donning')) is not int or not 1 <= meta['donning'] <= 20 or e.dtype.kind not in 'fiu' or e.ndim != 2 or e.shape[1] != 8 or len(e) < 2000 or not np.isfinite(e).all():
                    raise ValueError('组合样本无效，请检查后重录')
                if meta.get('dropped', 0) != 0: raise ValueError('组合样本存在丢帧，不能检验时序')
                ticks = []
                for end in range(400, len(e) + 1, 100):
                    x = trainer.meta_features(e[end - 400:end])[None]
                    if not np.isfinite(x).all(): raise ValueError('组合样本短窗数值无效')
                    _, probs = trainer.scores(model, x)
                    if not np.isfinite(probs).all(): raise ValueError('组合样本概率无效')
                    i = int(probs[0].argmax())
                    ticks.append(dict(top=model['classes'][i], confidence=float(probs[0,i]), ms=1000 + end / 2))
                out.append(dict(label=label, file=f.name, donning=meta['donning'], ticks=ticks))
            except (ValueError, OSError, KeyError, TypeError, AttributeError, BadZipFile, EOFError, CompressionError) as err:
                out.append(dict(label=label, file=f.name, error=str(err), ticks=[]))
    return out

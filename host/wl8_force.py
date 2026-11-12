"""指尖力回归小实验，阶段 0：Mac 触控板当力的真值，唯理 8 路肌电估单指按压力。

方案和门的定义见 design/finger-force-20261107/PLAN.md。门的阈值录前定、录后不改。
腕带和触控板接同一台 Mac，时间都用这台机的 monotonic 时钟，不需要甩腕对时。
原始数据只放 host/v12-captures/force-<日期>/，不上传、不入库。

    .venv-emg/bin/python wl8_force.py --check                  # 合成数据，正反都要成立，不碰硬件
    .venv-emg/bin/python wl8_force.py --probe                  # 只测触控板：轻中重各按 5 秒，看读数是否单调
    .venv-emg/bin/python wl8_force.py --record --wear A        # 录一次佩戴，约 16 分钟；先退出 OpenEMG、拔电源
    .venv-emg/bin/python wl8_force.py --recover <某次>.spool    # 录制时边读边落盘；进程崩了用它重建 npz
    .venv-emg/bin/python wl8_force.py --eval A.npz B.npz --out report.json
"""
import argparse
import ctypes
import json
import os
import re
import subprocess
import sys
import tempfile
import threading
import time
import warnings
from pathlib import Path

import numpy as np
from sklearn.linear_model import Ridge
from sklearn.metrics import average_precision_score

import wl8
import wl8_train

FINGERS = ('拇指', '食指', '中指', '无名指', '小指')
AMP = dict(light=.35, mid=.65, heavy=1., go=1.)            # 只给合成数据用；实测以触控板读数为准
WIN, STEP = 512, .05                                       # 256 ms 窗（2 kHz），50 ms 步长
HALF_S = WIN / 2 / wl8.EMG_HZ
LAGS = np.round(np.arange(-.3, .301, .05), 2)              # 正数 = 肌电领先力
ALPHA = 100.                                               # 岭回归强度，录前定好，不按结果调
CONTACT = .25                                              # 读数超过该手指 p95 的 25% 算在按
CAL_S = 60.                                                # 重戴校准总时长，五根手指平摊
MIN_BATTERY = 30
ARRAYS = ('emg_uv', 'imu', 'seq', 'emg_t', 'imu_t', 'touch', 'clock_resid_ms')
CAPTURES = Path(__file__).parent / 'v12-captures'
# 录前定好的门，见 PLAN.md；录后不改
G1_R2, G1_OVER_IMU, G1_PRESS, G1_SHIFT, G1_AIR, G2_R2, G3_AP = .50, .20, .20, .05, .25, .30, .60
LAG_OK = (0., .2)


def schedule(seed=0, head_s=15., block_s=60., rest_s=20., air_s=20., air_rest_s=10., jitter=.5, rounds=2):
    """整段流程。按、松的时长随机：节拍固定时，平移量一旦是周期的整数倍，标签平移对照就失效（--check 有这条反例）。"""
    rng = np.random.default_rng(seed)
    segs, t = [], 0.
    for kind in ('noise_off', 'noise_on'):
        segs.append(dict(kind=kind, finger=-1, round=-1, say_at=t, t0=t, t1=t + head_s, cues=[]))
        t += head_s

    def block(kind, finger, rnd, dur, rest):
        nonlocal t
        t0, levels = t + rest, ('go',) if kind == 'air' else ('light', 'mid', 'heavy')
        say_at = t + min(1., rest / 2)                     # 晚一点报下一块，别和「休息」叠在一起
        c, cues = t0, []
        while True:
            on, off = rng.uniform(2 - jitter, 2 + jitter, 2)
            if c + on > t0 + dur: break
            cues.append([round(c, 3), round(c + on, 3), levels[len(cues) % len(levels)]])
            c += on + off
        segs.append(dict(kind=kind, finger=finger, round=rnd, say_at=say_at, t0=t0, t1=t0 + dur, cues=cues))
        t = t0 + dur

    for rnd in range(rounds):                              # 同一手指的两块隔开，疲劳不集中在一块
        for f in range(5): block('press', f, rnd, block_s, rest_s)
    for f in range(5): block('air', f, -1, air_s, air_rest_s)
    return segs


def voice_lines():
    lines = dict(light='轻按', mid='中按', heavy='重按', go='动', rel='松', rest='休息', done='这一段录完了',
                 noise_off='手离开电脑，放松', noise_on='手放在触控板旁边，放松')
    for i, name in enumerate(FINGERS):
        lines[f'press{i}'] = f'下一块，{name}'
        lines[f'air{i}'] = f'下一块，{name}空按，不要碰触控板'
    return lines


def cue_list(segs):
    out = []
    for s in segs:
        out.append((s['say_at'], s['kind'] if s['finger'] < 0 else f"{s['kind']}{s['finger']}"))
        out += [x for on, off, level in s['cues'] for x in ((on, level), (off, 'rel'))]
        if s['finger'] >= 0: out.append((s['t1'], 'rest'))
    return sorted(out + [(segs[-1]['t1'] + .5, 'done')])


def power_ok(text):
    """只认电池供电且电量够。接电源既引入工频，也让人体多一条到市电的路。"""
    m = re.search(r'(\d+)%', text)
    return "'Battery Power'" in text and bool(m) and int(m[1]) >= MIN_BATTERY


class Pad:
    """内置触控板。结构体布局来自 OpenMultitouchSupport，私有框架不保证跨系统版本，所以 --probe 要先过。"""
    def __init__(self):
        class P(ctypes.Structure): _fields_ = [('x', ctypes.c_float), ('y', ctypes.c_float)]
        class V(ctypes.Structure): _fields_ = [('pos', P), ('vel', P)]
        class Touch(ctypes.Structure):
            _fields_ = [('frame', ctypes.c_int), ('timestamp', ctypes.c_double), ('id', ctypes.c_int), ('state', ctypes.c_int),
                        ('finger', ctypes.c_int), ('hand', ctypes.c_int), ('norm', V), ('total', ctypes.c_float),
                        ('pressure', ctypes.c_float), ('angle', ctypes.c_float), ('major', ctypes.c_float), ('minor', ctypes.c_float),
                        ('abs', V), ('f14', ctypes.c_int), ('f15', ctypes.c_int), ('density', ctypes.c_float)]
        assert ctypes.sizeof(Touch) == 96
        self.mt = ctypes.CDLL('/System/Library/PrivateFrameworks/MultitouchSupport.framework/MultitouchSupport')
        self.mt.MTDeviceCreateDefault.restype = ctypes.c_void_p
        self.mt.MTDeviceStart.argtypes = [ctypes.c_void_p, ctypes.c_int]
        self.mt.MTDeviceStop.argtypes = [ctypes.c_void_p]
        kind = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_void_p, ctypes.POINTER(Touch), ctypes.c_int, ctypes.c_double, ctypes.c_int)
        self.mt.MTRegisterContactFrameCallback.argtypes = [ctypes.c_void_p, kind]
        self.rows = []

        def frame(_dev, touches, n, _ts, _frame):
            on = [touches[i] for i in range(n) if touches[i].state in (3, 4)]   # 3 刚接触、4 接触中；悬停和离开不算
            self.rows.append((time.monotonic(), len(on), sum(x.pressure for x in on), sum(x.total for x in on)))
            return 0
        self.callback = kind(frame)                        # 留住引用，否则回调被回收后崩溃
        self.device = self.mt.MTDeviceCreateDefault()
        if not self.device: raise RuntimeError('打不开触控板')
        self.mt.MTRegisterContactFrameCallback(self.device, self.callback)

    def start(self):
        if self.mt.MTDeviceStart(self.device, 0): raise RuntimeError('触控板启动失败')

    def stop(self):
        self.mt.MTDeviceStop(self.device)


def play(segs, voice, t0, stop):
    for at, key in cue_list(segs):
        while not stop.is_set() and time.monotonic() - t0 < at: time.sleep(.01)
        if stop.is_set(): return
        voice.cue(key, wait=False)


def capture(conn, pad, meta, spool, voice=None, tail_s=1.):
    """边读边落盘：串口字节、到达时刻、触控板帧都进 spool。进程被杀或解码出错，spool 还在，--recover 能重建。"""
    segs = meta['segs']
    spool.mkdir(parents=True)
    (spool / 'meta.json').write_text(json.dumps(meta, ensure_ascii=False))
    stop = threading.Event()
    conn.read(4096)                                        # wl8.record 的做法：丢第一块，不调 reset_input_buffer
    t0 = time.monotonic()
    end = t0 + segs[-1]['t1'] + tail_s
    pad.start()
    if voice: threading.Thread(target=play, args=(segs, voice, t0, stop), daemon=True).start()
    complete, last, done = False, 0., 0
    with open(spool / 'raw.bin', 'wb') as raw, open(spool / 'arrive.txt', 'w') as log, open(spool / 'touch.txt', 'w') as frames:
        def flush_touch():
            nonlocal done
            new = pad.rows[done:]
            done += len(new)
            frames.writelines(f'{t - t0:.6f} {n} {f} {c}\n' for t, n, f, c in new)
            frames.flush()
        try:
            while time.monotonic() < end:
                b = conn.read(4096)
                if b:
                    last = time.monotonic() - t0
                    raw.write(b); raw.flush()
                    log.write(f'{len(b)} {last:.6f}\n'); log.flush()
                flush_touch()
            complete = last >= segs[-1]['t1']              # 静默断流读不到字节，也算不完整
        except (KeyboardInterrupt, OSError) as e:          # 白线被扯、USB 掉线、睡眠走 OSError；已录部分都在 spool 里
            print(f'录制中断（{type(e).__name__}），已录部分在 {spool}')
        finally:
            stop.set(); pad.stop(); flush_touch()
    (spool / 'end.json').write_text(json.dumps(dict(complete=complete)))


def lines(path, cols):
    """读 spool 的文本列。掉电时末行可能只写了一半，列数不对的行丢掉。"""
    return np.array([r for r in (x.split() for x in path.read_text().splitlines()) if len(r) == cols], float).reshape(-1, cols)


def pack(spool):
    """spool → 一次佩戴。串口样本的时间用「累计字节 → 到达时刻」拟合，单块到达抖动不进时间轴。"""
    emg, imu, seq, kinds, _ = wl8.decode((spool / 'raw.bin').read_bytes(), kinds=True)
    sizes, arrive = lines(spool / 'arrive.txt', 2).T
    sent = np.cumsum(sizes)
    slope, zero = np.polyfit(sent, arrive, 1)
    # 每帧字节用总量平均：有坏帧时按固定 29 字节累加，末端会错开（1e-4 坏帧率到 980 秒偏 124 ms）
    frame_t = zero + slope * sent[-1] / len(kinds) * (np.arange(len(kinds)) + 1)
    touch = lines(spool / 'touch.txt', 4)
    end = spool / 'end.json'                               # 进程被杀时没有这个文件
    complete = end.is_file() and json.loads(end.read_text())['complete']
    return dict(emg_uv=emg, imu=imu, seq=seq, emg_t=frame_t[kinds == wl8.EMG], imu_t=frame_t[kinds == wl8.IMU], touch=touch,
                clock_resid_ms=np.array(float(np.percentile(np.abs(arrive - (zero + slope * sent)), 99)) * 1e3),
                meta={**json.loads((spool / 'meta.json').read_text()), 'complete': bool(complete), 'seconds': float(arrive[-1])})


def save(s, path):
    np.savez_compressed(path, **{k: s[k] for k in ARRAYS}, meta=json.dumps(s['meta'], ensure_ascii=False))
    return path


def load(path):
    z = np.load(path)
    return {**{k: z[k] for k in ARRAYS}, 'meta': json.loads(str(z['meta']))}


def force_at(s, times):
    """times 时刻的读数：取最近一帧；超过 0.1 秒没新帧算没按（没有接触时回调不再来帧）。"""
    t, p = s['touch'][:, 0], s['touch'][:, 2]
    if not len(t): return np.zeros(len(times))
    i = np.searchsorted(t, times, side='right') - 1
    return np.where((i >= 0) & (times - t[np.maximum(i, 0)] <= .1), p[np.maximum(i, 0)], 0.)


def phase(tc, seg):
    """1 = 该按，0 = 该松，-1 = 刚换口令的 0.3 秒内和块尾，不计入空按对照。"""
    out = np.full(len(tc), -1)
    cues = seg['cues']
    for i, (on, off, _) in enumerate(cues):
        nxt = cues[i + 1][0] if i + 1 < len(cues) else seg['t1']
        out[(tc >= on + .3) & (tc <= off)] = 1
        out[(tc >= off + .3) & (tc <= nxt)] = 0
    return out


def table(s):
    """按块切窗。窗不跨块，切分就不会把相邻重叠窗分到训练和测试两边。"""
    emg, t, imu, imu_t = s['emg_uv'], s['emg_t'], s['imu'].astype(float), s['imu_t']
    multi = s['touch'][s['touch'][:, 1] >= 2, 0]
    rows = []
    for k, seg in enumerate(s['meta']['segs']):
        if seg['finger'] < 0: continue
        tc = np.arange(seg['t0'] + HALF_S, seg['t1'] - HALF_S, STEP)
        idx = np.searchsorted(t, tc)
        ok = (idx >= WIN // 2) & (idx + WIN // 2 <= len(emg))
        tc, idx = tc[ok], idx[ok]
        for c, i, ph in zip(tc, idx, phase(tc, seg)):
            j0, j1 = np.searchsorted(imu_t, (c - HALF_S, c + HALF_S))
            part = imu[j0:j1]
            rows.append((wl8_train.features(emg[i - WIN // 2:i + WIN // 2]),
                         np.r_[part.mean(0), part.std(0)] if len(part) > 1 else np.zeros(12),
                         c, c - seg['t0'], k, seg['finger'], seg['round'], seg['kind'] == 'press', ph,
                         np.searchsorted(multi, c + HALF_S) > np.searchsorted(multi, c - HALF_S)))
    cols = list(zip(*rows))
    return dict(X=np.array(cols[0]), Xi=np.array(cols[1]), tc=np.array(cols[2]), rel=np.array(cols[3]), seg=np.array(cols[4]),
                finger=np.array(cols[5]), round=np.array(cols[6]), press=np.array(cols[7]), phase=np.array(cols[8]), bad=np.array(cols[9]))


def labels(s, T, lag=0.):
    """(窗数, 5)：只有该块的手指有力，其余手指是 0，这样 R² 也考「分不分得清是哪根」。空按块全 0。"""
    Y = np.zeros((len(T['tc']), 5))
    rows = np.flatnonzero(T['press'])
    Y[rows, T['finger'][rows]] = force_at(s, T['tc'][rows] + lag)
    return Y


def fit(X, Y, w=None):
    mu, sd = X.mean(0), X.std(0) + 1e-9
    model = Ridge(alpha=ALPHA).fit((X - mu) / sd, Y, sample_weight=w)
    return lambda Z: model.predict((Z - mu) / sd)


def r2(Y, P):
    if len(Y) < 2: return -1.                              # 没有窗不能算过
    return float(np.mean(1 - ((Y - P) ** 2).sum(0) / (((Y - Y.mean(0)) ** 2).sum(0) + 1e-12)))


def own_r2(Y, P, finger):
    """每根手指只在自己那块里算 R²，再平均。"""
    return float(np.mean([r2(Y[finger == f][:, [f]], P[finger == f][:, [f]]) for f in range(5)]))


def press_r2(Y, P, finger):
    """只看按着的窗：考得出轻中重，不是只认按没按。力分三档时，开关量就能解释大部分方差，其它 R² 拦不住。"""
    rows = [(finger == f) & (Y[:, f] > CONTACT) for f in range(5)]
    return float(np.mean([r2(Y[m][:, [f]], P[m][:, [f]]) for f, m in enumerate(rows)]))


def pr_auc(Y, P):
    return float(np.mean([average_precision_score(Y[:, f] > CONTACT, P[:, f]) for f in range(5)]))


def scale_of(Y, T, rows):
    """每根手指自己那几块里的 p95，当作这根手指的满量程。"""
    own = [Y[rows & (T['finger'] == f), f] for f in range(5)]
    return np.array([max(np.percentile(y, 95), 1e-9) if len(y) else 1. for y in own])


def roll_labels(Y, T, rows):
    """每块内把标签循环平移半块（60 秒的块就是 30 秒）。"""
    out = Y.copy()
    for k in np.unique(T['seg'][rows]):
        m = rows & (T['seg'] == k)
        out[m] = np.roll(Y[m], m.sum() // 2, axis=0)
    return out


def air_ratio(T, predict, test_rows):
    """空按时模型的输出起伏 ÷ 真按时的起伏。空按块不进训练，所以这是一道没见过的考题。"""
    P = predict(T['X'])
    swing = lambda rows, f: abs(P[rows & (T['phase'] == 1), f].mean() - P[rows & (T['phase'] == 0), f].mean())
    air = np.array([swing((T['finger'] == f) & ~T['press'], f) for f in range(5)])
    real = np.array([swing((T['finger'] == f) & test_rows, f) for f in range(5)])
    return float(air.mean() / (real.mean() + 1e-12))


def folds(T):
    """第一轮训第二轮测，再交换。第二触点的窗不用，空按块不进训练。"""
    use = T['press'] & ~T['bad']
    return [(use & (T['round'] == tr), use & (T['round'] == 1 - tr)) for tr in (0, 1)]


def within(s, T):
    """同佩戴：两折取平均。"""
    Y0 = labels(s, T)
    out = []
    for a, b in folds(T):
        sc = scale_of(Y0, T, a)
        Y = Y0 / sc
        emg = fit(T['X'][a], Y[a])
        P = emg(T['X'][b])
        # 平移对照：训练和测试的标签都在块内错开，只看本手指那块。全块 R² 不能用：
        # 「这块是哪根手指」的块级信息平移后还在，好数据也会有 0.2 左右（--check 实测）。
        Ys = roll_labels(Y, T, a | b)
        Pi = fit(T['Xi'][a], Y[a])(T['Xi'][b])
        fb = T['finger'][b]
        out.append(dict(emg_r2=r2(Y[b], P), own_block_r2=own_r2(Y[b], P, fb), press_r2=press_r2(Y[b], P, fb),
                        imu_r2=r2(Y[b], Pi), imu_own_r2=own_r2(Y[b], Pi, fb),
                        shift_r2=own_r2(Ys[b], fit(T['X'][a], Ys[a])(T['X'][b]), fb),
                        air_ratio=air_ratio(T, emg, b), pr_auc=pr_auc(Y[b], P), contact_rate=float((Y[b] > CONTACT).mean())))
    return {k: float(np.mean([f[k] for f in out])) for k in out[0]}


def lag_scan(s, T):
    """只用来查对时，不参与选参数。窗的时刻取窗中心。"""
    a, b = folds(T)[0]
    sc = scale_of(labels(s, T), T, a)
    curve = []
    for lag in LAGS:
        Y = labels(s, T, lag) / sc
        curve.append(r2(Y[b], fit(T['X'][a], Y[a])(T['X'][b])))
    lag = float(LAGS[int(np.argmax(curve))])
    return dict(lag_s=lag, curve=[round(c, 3) for c in curve], ok=bool(LAG_OK[0] <= lag <= LAG_OK[1]))


def rewear_rows(A, B):
    """佩戴 A 全部；佩戴 B 第一轮每根手指头 12 秒校准；测 B 第二轮。"""
    use = B['press'] & ~B['bad']
    return A['press'] & ~A['bad'], use & (B['round'] == 0) & (B['rel'] < CAL_S / 5), use & (B['round'] == 1)


def rewear(sa, A, sb, B):
    """各自用自己的均值方差归一，校准和 A 总权重相等。a_only 不校准，单列：G2 过不代表 A 的模型能迁移。"""
    Ya, Yb = labels(sa, A), labels(sb, B)
    a, cal, te = rewear_rows(A, B)
    sc = scale_of(Ya, A, a)
    Ya, Yb = Ya / sc, Yb / sc
    za = (A['X'] - A['X'][a].mean(0)) / (A['X'][a].std(0) + 1e-9)
    zb = (B['X'] - B['X'][cal].mean(0)) / (B['X'][cal].std(0) + 1e-9)
    w = np.r_[np.ones(a.sum()), np.full(cal.sum(), a.sum() / max(cal.sum(), 1))]
    both = lambda P: min(r2(Yb[te], P), own_r2(Yb[te], P, B['finger'][te]))
    return dict(a_plus_cal=both(fit(np.vstack([za[a], zb[cal]]), np.vstack([Ya[a], Yb[cal]]), w)(zb[te])),
                cal_only=both(fit(zb[cal], Yb[cal])(zb[te])),
                a_only=both(fit(A['X'][a], Ya[a])(B['X'][te])))


def cue_peaks(s, segs, f):
    """这根手指每条按压口令期间的最大读数和档位。多看 0.5 秒：人听到「轻按」要反应，不能算漏按。"""
    cues = [c for g in segs if g['kind'] == 'press' and g['finger'] == f for c in g['cues']]
    return [(level, float(force_at(s, np.arange(on, off + .5, .02)).max())) for on, off, level in cues]


def rms_swing(s, seg):
    """一块里「该按」和「该松」的肌电 RMS 之比，只报告。1 附近说明人没动。"""
    i0, i1 = np.searchsorted(s['emg_t'], (seg['t0'], seg['t1']))
    t, e = s['emg_t'][i0:i1], s['emg_uv'][i0:i1]
    ph = np.zeros(len(t), bool)
    for on, off, _ in seg['cues']: ph[np.searchsorted(t, on):np.searchsorted(t, off)] = True
    return float(np.median(wl8.ac_rms(e[ph])) / (np.median(wl8.ac_rms(e[~ph])) + 1e-9))


def quality(s, T):
    segs, meta = s['meta']['segs'], s['meta']
    air = ~T['press']
    peaks = [cue_peaks(s, segs, f) for f in range(5)]
    level = lambda ps, k: float(np.median([v for lv, v in ps if lv == k and v > 0] or [0.]))
    noise = {g['kind']: float(np.median(wl8.ac_rms(s['emg_uv'][(s['emg_t'] >= g['t0']) & (s['emg_t'] <= g['t1'])])))
             for g in segs if g['finger'] < 0}
    swing = lambda kind: round(float(np.median([rms_swing(s, g) for g in segs if g['kind'] == kind])), 2)
    hz = len(s['emg_t']) / meta['seconds']
    q = dict(complete=bool(meta['complete']), site=meta.get('site'), emg_hz=round(hz, 1), lost_rate=wl8.dropped(s['seq']) / max(len(s['seq']), 1),
             railed_rate=float((np.abs(s['emg_uv']) >= wl8.RAIL_UV).mean()), clock_resid_p99_ms=round(float(s['clock_resid_ms']), 1),
             second_touch_rate=float(T['bad'][T['press']].mean()),
             air_touch_rate=float((force_at(s, T['tc'][air]) > 0).mean()),         # 按时间算：触控板空闲时不来帧
             press_hit_rate=[float(np.mean([v > 0 for _, v in ps])) for ps in peaks],
             heavy_over_light=[round(level(ps, 'heavy') / max(level(ps, 'light'), 1e-9), 2) for ps in peaks],
             noise_uv=noise, emg_swing=dict(press=swing('press'), air=swing('air')))
    q['ok'] = quality_ok(q)
    return q


def quality_ok(q):
    return bool(q['complete'] and abs(q['emg_hz'] - wl8.EMG_HZ) <= 20 and q['lost_rate'] <= .01 and q['railed_rate'] <= .001
                and q['clock_resid_p99_ms'] <= 50 and q['second_touch_rate'] <= .1 and q['air_touch_rate'] <= .05
                and min(q['press_hit_rate']) >= .8 and min(q['heavy_over_light']) >= 1.5)


def gates(m, g):
    """全块 R² 考分不分得清手指，本手指 R² 考跟不跟得上力，只靠一个都会虚高，所以取较小的。IMU 同口径相减。
    两种校准都是能上线的做法，取较好的：10-14 实验里历史佩戴常帮倒忙，不该因合并方式差而判重戴不行。"""
    score = min(m['emg_r2'], m['own_block_r2'])
    margin = min(m['emg_r2'] - m['imu_r2'], m['own_block_r2'] - m['imu_own_r2'])
    g1 = score >= G1_R2 and margin >= G1_OVER_IMU and m['press_r2'] >= G1_PRESS and m['shift_r2'] <= G1_SHIFT and m['air_ratio'] <= G1_AIR
    return bool(g1), bool(max(g['a_plus_cal'], g['cal_only']) >= G2_R2), bool(m['pr_auc'] >= G3_AP)


def evaluate(sa, sb):
    A, B = table(sa), table(sb)
    wa, wb = within(sa, A), within(sb, B)
    m = {k: (wa[k] + wb[k]) / 2 for k in wa}
    g = rewear(sa, A, sb, B)
    align = dict(A=lag_scan(sa, A), B=lag_scan(sb, B))
    q = dict(A=quality(sa, A), B=quality(sb, B))
    g1, g2, g3 = gates(m, g)
    valid = q['A']['ok'] and q['B']['ok'] and align['A']['ok'] and align['B']['ok']
    verdict = ('判不了：数据或对时不合格，先修再说' if not valid else '三门全过，进阶段 1' if g1 and g2 and g3 else
               'G1 不过：腕带上移到前臂重录一次' if not g1 else 'G2 不过：60 秒校准不够，用现有数据加长校准再算' if not g2 else 'G3 不过：看接触判断错在哪')
    return dict(valid=bool(valid), G1=g1, G2=g2, G3=g3, verdict=verdict, mean=m, A=wa, B=wb, rewear=g, align=align, quality=q)


def show(rep):
    m, g = rep['mean'], rep['rewear']
    print(f"G1 同佩戴  {'过' if rep['G1'] else '不过'}：全块 R² {m['emg_r2']:.3f}，本手指 {m['own_block_r2']:.3f}（门 {G1_R2}），按压段内 {m['press_r2']:.3f}（门 {G1_PRESS}），"
          f"只用 IMU {m['imu_r2']:.3f} / {m['imu_own_r2']:.3f}，标签平移 {m['shift_r2']:.3f}，空按比 {m['air_ratio']:.3f}（门 {G1_AIR}）")
    print(f"G2 重戴    {'过' if rep['G2'] else '不过'}：A＋校准 {g['a_plus_cal']:.3f}，只用校准 {g['cal_only']:.3f}（门 {G2_R2}，取较好的）；不校准 {g['a_only']:.3f}（只报告）")
    print(f"G3 接触    {'过' if rep['G3'] else '不过'}：PR-AUC {m['pr_auc']:.3f}（门 {G3_AP}，正例占 {m['contact_rate']:.2f}）")
    print(f"对时：肌电领先 A {rep['align']['A']['lag_s']*1e3:.0f} ms、B {rep['align']['B']['lag_s']*1e3:.0f} ms（应在 0–200）")
    for k in 'AB': print(f"数据 {k}：{json.dumps(rep['quality'][k], ensure_ascii=False)}")
    print('结论：' + rep['verdict'])


def probe(args):
    pad = Pad()
    voice = open_voice(dict(light='轻按', mid='中按', heavy='重按', rel='松'))
    pad.start()
    stages = []
    for key in ('light', 'mid', 'heavy'):
        voice.cue(key, wait=False)
        t0 = time.monotonic(); time.sleep(args.hold)
        p = np.array([r[2] for r in pad.rows if r[0] >= t0 + 1 and r[1] == 1])
        stages.append(float(np.median(p)) if len(p) else 0.)
        voice.cue('rel', wait=False); time.sleep(2)
    pad.stop()
    voice.close()
    t = np.array([r[0] for r in pad.rows])
    rate = len(t) / max(t[-1] - t[0], 1e-6) if len(t) > 1 else 0.
    ok = 0 < stages[0] < stages[1] < stages[2]
    print(f'帧率 {rate:.0f} Hz，轻中重读数中位 {stages}，最大 {max((r[2] for r in pad.rows), default=0):.0f}，单调：{ok}')
    return 0 if ok else 1


def open_voice(lines):
    from calibration_voice import CalibrationVoice
    voice = CalibrationVoice(lambda: False)
    voice.files = {k: voice._audio(v) for k, v in lines.items()}   # 复用缓存和合成，口令是这里自己的
    return voice


def rebuild(spool):
    print('解码中…')
    s = pack(spool)
    path = save(s, spool.with_suffix('.npz'))
    print(f'已存 {path}')
    print(json.dumps(quality(s, table(s)), ensure_ascii=False) if s['meta']['complete'] else '录制不完整，这份不能进 --eval')
    return 0


def record(args):
    import serial
    text = subprocess.run(['pmset', '-g', 'ps'], capture_output=True, text=True).stdout
    if not power_ok(text):
        print(f'拒绝录制：要用电池供电且电量 ≥ {MIN_BATTERY}%。现在：{text.splitlines()[:2]}'); return 1
    try:
        dev = wl8.find_port(args.port)
    except wl8.NoReceiver as e:
        print(f'拒绝录制：{e}'); return 1
    now = time.strftime('%Y%m%d'), time.strftime('%H%M%S')
    spool = CAPTURES / f'force-{now[0]}' / f'{args.wear}-{now[1]}.spool'
    meta = dict(segs=schedule(seed=args.seed), wear=args.wear, site=args.site, seed=args.seed, port=dev.device, recordedAt=time.strftime('%Y-%m-%dT%H:%M:%S'))
    voice = open_voice(voice_lines())                      # 先合成好口令，合成时串口没人读
    subprocess.Popen(['caffeinate', '-i', '-d', '-w', str(os.getpid())])   # 录制期间不睡眠，进程退出自动解除
    try:
        with serial.Serial(dev.device, wl8.BAUD, timeout=.2, exclusive=True) as conn:
            conn.read(4096)
            t0, got = time.monotonic(), b''
            while time.monotonic() - t0 < 1: got += conn.read(4096)
            hz = len(wl8.decode(got)[0]) / (time.monotonic() - t0)
            if hz < 1900:
                print(f'拒绝录制：肌电只有 {hz:.0f} Hz，确认腕带开机、绿灯闪'); return 1
            print(f"开始。全程约 {meta['segs'][-1]['t1'] / 60:.0f} 分钟。光标停在这个终端窗口的空白处，只用轻到中等的力，按痛就停，Ctrl-C 中止。")
            print(f'原始数据边录边写到 {spool}，出错时用 --recover 重建。')
            capture(conn, Pad(), meta, spool, voice)
    finally:
        voice.close()
    return rebuild(spool)


def synth(seed=0, person=7, block_s=20., emg_real=True, imu_real=False, air=.1, lead=.1, jitter=.5, second=0., clock_off=0.,
          graded=True, late=0., air_touch=0.):
    """合成一次佩戴。肌电包络由「手指 × 电极」矩阵决定，力比肌电晚 lead 秒；同一 person 的矩阵相同，佩戴间只有小改动。
    graded=False：肌电只有开关，不随力分档。late：按下比口令晚多少秒。air_touch：第一块空按里碰板多少秒。"""
    rng = np.random.default_rng(seed)
    segs = schedule(seed, head_s=3., block_s=block_s, rest_s=1., air_s=8., air_rest_s=1., jitter=jitter)
    fs, T = wl8.EMG_HZ, segs[-1]['t1'] + .5
    n = int(T * fs)

    def activity(plan, air_gain):
        a, f = np.zeros((n, 5)), np.zeros((n, 5))
        for g in plan:
            if g['finger'] < 0: continue
            for on, off, level in g['cues']:
                i, j = int((on + late) * fs), int(off * fs)
                amp = AMP[level] * rng.uniform(.9, 1.1)
                a[i:j, g['finger']] = (amp if graded else 1.) * (1 if g['kind'] == 'press' else air_gain)
                if g['kind'] == 'press': f[i:j, g['finger']] = amp * 100
        return a, f

    act, force = activity(segs, air)
    force = np.roll(force, int(lead * fs), axis=0)
    M = np.random.default_rng(person).uniform(0, 1, (5, 8)) ** 3
    M = M * rng.uniform(.9, 1.1, M.shape)
    drive = act if emg_real else activity(schedule(seed + 999, head_s=3., block_s=block_s, rest_s=1., air_s=8., air_rest_s=1.), air)[0]
    emg = (rng.normal(size=(n, 8)) * np.sqrt(.02 + (drive @ M) ** 2) * 200).astype(np.int32)
    m = n // 20
    imu = rng.normal(size=(m, 6)) * 20
    if imu_real: imu[:, :5] += force[::20][:m] * 5
    t = np.arange(n) / fs + clock_off
    tt = np.arange(0, T, 1 / 94)
    p = force.sum(1)[np.minimum((tt * fs).astype(int), n - 1)]
    if air_touch:
        g = next(x for x in segs if x['kind'] == 'air')
        p[(tt >= g['t0'] + 1) & (tt < g['t0'] + 1 + air_touch)] = 20.
    cnt = (p > 0).astype(float)
    cnt[(rng.uniform(size=len(tt)) < second) & (p > 0)] = 2
    keep = (p > 0) | np.r_[False, p[:-1] > 0]              # 和真机一样：没接触时不来帧，抬手时来一帧 0
    return dict(emg_uv=emg, imu=imu.astype(np.int16), seq=(np.arange(n + m) % 256).astype(np.uint8), emg_t=t, imu_t=np.arange(m) / (fs / 20),
                touch=np.c_[tt, cnt, p, p][keep], clock_resid_ms=np.array(3.), meta=dict(segs=segs, complete=True, seconds=float(n / fs)))


class FakeConn:
    """按真实节奏吐 29 字节帧：每 20 帧肌电插 1 帧 IMU。stall_at 之后不再出字节，die_at 之后抛 OSError（线被扯）。"""
    def __init__(self, stall_at=None, die_at=None): self.i, self.at, self.stall_at, self.die_at = 0, time.monotonic(), stall_at, die_at

    def read(self, _size):
        time.sleep(.01)
        now = time.monotonic() - self.at
        if self.die_at is not None and now > self.die_at: raise OSError('device disconnected')
        if self.stall_at is not None and now > self.stall_at: return b''
        out = b''
        while self.i < now * wl8.EMG_HZ * 21 / 20:
            kind = wl8.IMU if self.i % 21 == 20 else wl8.EMG
            out += wl8.SYNC + bytes([kind, self.i % 256]) + (b'\x00\x00\x07' * 8 if kind == wl8.EMG else bytes(24))
            self.i += 1
        return out


class FakePad:
    def __init__(self): self.rows = []
    def start(self): self.rows += [(time.monotonic() + .01 * i, 1, 50., 1.) for i in range(100)]
    def stop(self): pass


def check():
    # 流程本身：随机时长，真按和空按都齐；语音口令一条不缺，换块时不和「休息」撞车
    segs = schedule()
    assert sum(g['kind'] == 'press' for g in segs) == 10 and sum(g['kind'] == 'air' for g in segs) == 5
    assert 840 < segs[-1]['t1'] < 1100, segs[-1]['t1']
    ons = [c[1] - c[0] for g in segs for c in g['cues']]
    assert np.std(ons) > .1 and min(ons) >= 1.5 and max(ons) <= 2.5
    assert {k for _, k in cue_list(segs)} <= set(voice_lines())
    said = [t for t, k in cue_list(segs) if k.startswith(('press', 'air'))]
    assert not set(said) & {t for t, k in cue_list(segs) if k == 'rest'}

    # 供电闸：会被拦的输入都要拦住
    assert power_ok("Now drawing from 'Battery Power'\n -InternalBattery-0 (id=1)\t80%; discharging")
    assert not power_ok("Now drawing from 'AC Power'\n -InternalBattery-0 (id=1)\t80%; charging")
    assert not power_ok("Now drawing from 'Battery Power'\n -InternalBattery-0 (id=1)\t12%; discharging")
    assert not power_ok('')

    # 录制链路：假串口真节奏。正常、断线、静默断流、进程被杀，数据都要留在 spool 里
    meta = dict(segs=[dict(kind='press', finger=0, round=0, say_at=0., t0=0., t1=1., cues=[])], wear='A')
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        capture(FakeConn(), FakePad(), meta, tmp / 'ok', tail_s=.2)
        s = pack(tmp / 'ok')
        hz = len(s['emg_t']) / (s['emg_t'][-1] - s['emg_t'][0])
        assert abs(hz - wl8.EMG_HZ) < 40 and np.all(np.diff(s['emg_t']) > 0) and s['emg_uv'][5, 0] == 7, hz
        assert s['touch'].shape == (100, 4) and float(s['clock_resid_ms']) < 50 and s['meta']['complete'], s['clock_resid_ms']
        back = load(save(s, tmp / 'ok.npz'))
        assert np.array_equal(back['emg_uv'], s['emg_uv']) and back['meta']['complete'] is True and back['meta']['wear'] == 'A'
        for name, kw in (('die', dict(die_at=.4)), ('stall', dict(stall_at=.4))):
            capture(FakeConn(**kw), FakePad(), meta, tmp / name, tail_s=.2)
            part = pack(tmp / name)
            assert not part['meta']['complete'] and len(part['emg_t']) > 400, name
        with open(tmp / 'ok' / 'arrive.txt', 'a') as f: f.write('4096')   # 掉电截断的半行
        (tmp / 'ok' / 'end.json').unlink()
        assert not pack(tmp / 'ok')['meta']['complete']    # 进程被杀：没有 end.json，也能重建，但不算完整

    # 坏帧不让时间轴错位：字节比帧多时，末帧时刻仍要接近到达时刻
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        (tmp / 'raw.bin').write_bytes(b''.join(wl8.SYNC + bytes([wl8.EMG, i % 256]) + bytes(24) + (b'\x55' * 29 if i % 10 == 0 else b'') for i in range(2000)))
        (tmp / 'arrive.txt').write_text(''.join(f'{(2000 * 29 + 200 * 29) // 10} {(k + 1) / 10}\n' for k in range(10)))
        (tmp / 'touch.txt').write_text('')
        (tmp / 'meta.json').write_text('{}')
        assert abs(pack(tmp)['emg_t'][-1] - 1.) < .01

    # 力的读数：超时算没按
    assert list(force_at(dict(touch=np.array([[0., 1, 5, 0], [.05, 0, 0, 0]])), np.array([.02, .06]))) == [5., 0.]
    assert list(force_at(dict(touch=np.array([[0., 1, 5, 0]])), np.array([.05, .5]))) == [5., 0.]

    # 门和合格线：每个条件单独翻一次，都要变红
    m0 = dict(emg_r2=.8, own_block_r2=.8, press_r2=.5, imu_r2=0., imu_own_r2=0., shift_r2=0., air_ratio=.1, pr_auc=.9)
    g0 = dict(a_plus_cal=.5, cal_only=.1)
    assert gates(m0, g0) == (True, True, True)
    for k, v in dict(emg_r2=.4, own_block_r2=.4, press_r2=.1, imu_r2=.7, imu_own_r2=.7, shift_r2=.1, air_ratio=.3).items():
        assert not gates({**m0, k: v}, g0)[0], k
    assert gates(m0, dict(a_plus_cal=.1, cal_only=.5))[1] and not gates(m0, dict(a_plus_cal=.2, cal_only=.2))[1]
    assert not gates({**m0, 'pr_auc': .5}, g0)[2]
    q0 = dict(complete=True, emg_hz=2000., lost_rate=0., railed_rate=0., clock_resid_p99_ms=3., second_touch_rate=0., air_touch_rate=0.,
              press_hit_rate=[1.] * 5, heavy_over_light=[2.] * 5)
    assert quality_ok(q0)
    for k, v in dict(complete=False, emg_hz=1900., lost_rate=.02, railed_rate=.01, clock_resid_p99_ms=60., second_touch_rate=.2, air_touch_rate=.1,
                     press_hit_rate=[1., 1., .7, 1., 1.], heavy_over_light=[2., 1.2, 2., 2., 2.]).items():
        assert not quality_ok({**q0, k: v}), k

    # 切分：训练和测试不相交，校准和测试不相交，第二触点的窗不用
    S1, S2 = synth(1, second=.02), synth(2, second=.02)
    T1, T2 = table(S1), table(S2)
    assert T1['bad'].any()
    for a, b in folds(T1):
        assert a.any() and b.any() and not (a & b).any() and not set(T1['seg'][a]) & set(T1['seg'][b])
        assert not T1['bad'][a | b].any() and T1['press'][a | b].all()
    a, cal, te = rewear_rows(T1, T2)
    assert cal.any() and te.any() and not set(T2['seg'][cal]) & set(T2['seg'][te]) and T2['rel'][cal].max() < CAL_S / 5

    assert r2(np.zeros((0, 1)), np.zeros((0, 1))) == -1.   # 没有窗不能算过
    # 校准不许看测试窗：B 第二轮增益突变 30 倍，只看校准窗的归一化对不上，分数必须掉下来
    jump = synth(2)
    for g in jump['meta']['segs']:
        if g['round'] == 1: jump['emg_uv'][(jump['emg_t'] >= g['t0']) & (jump['emg_t'] <= g['t1'])] *= 30
    leak = rewear(S1, T1, jump, table(jump))
    assert leak['a_plus_cal'] < G2_R2, ('归一化看了测试窗', leak)

    # 分析：好数据全过；每种假象各来一份，必须被对应的门拦住
    good = evaluate(synth(1), synth(2))
    assert good['valid'] and good['G1'] and good['G2'] and good['G3'], good['verdict'] + json.dumps(good['mean'])
    base_lag = good['align']['A']['lag_s']
    assert abs(base_lag - .1) <= .05, good['align']['A']

    bad = evaluate(synth(1, emg_real=False), synth(2, emg_real=False))
    assert not bad['G1'] and bad['mean']['own_block_r2'] < .2, ('肌电无关力', bad['mean'])
    bad = evaluate(synth(1, imu_real=True), synth(2, imu_real=True))
    assert not bad['G1'] and bad['mean']['emg_r2'] >= G1_R2 and bad['mean']['imu_r2'] > bad['mean']['emg_r2'] - G1_OVER_IMU, ('运动也能猜出力', bad['mean'])
    bad = evaluate(synth(1, air=1.), synth(2, air=1.))
    assert not bad['G1'] and bad['mean']['air_ratio'] > G1_AIR, ('认的是动作', bad['mean'])
    bad = evaluate(synth(1, graded=False), synth(2, graded=False))
    assert not bad['G1'] and bad['mean']['press_r2'] < G1_PRESS <= good['mean']['press_r2'], ('只认按没按', bad['mean'])
    bad = evaluate(synth(1), synth(2, person=8))
    assert bad['rewear']['a_only'] < .1 < bad['rewear']['cal_only'], ('电极全换：不校准该垮，校准该救回来', bad['rewear'])
    bad = evaluate(synth(1), synth(2, emg_real=False))
    assert not bad['G2'], ('重戴后信号没了', bad['rewear'])
    moved = evaluate(synth(1, clock_off=.1), synth(2, clock_off=.1))
    assert abs(moved['align']['A']['lag_s'] - (base_lag - .1)) <= .05, ('错开 100 ms 要被找回', moved['align']['A'])
    moved = evaluate(synth(1, clock_off=-.3), synth(2, clock_off=-.3))
    assert not moved['align']['A']['ok'] and not moved['valid'], ('对时错了要判不了', moved['align']['A'])
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')                    # 这份数据有手指整块作废，sklearn 会提示没有正例
        bad = evaluate(synth(1, second=.5), synth(2, second=.5))
    assert not bad['valid'] and bad['quality']['A']['second_touch_rate'] > .1, bad['quality']['A']
    # 固定 4 秒节拍、半块正好两个周期：平移后标签还对得上，这道对照必须红。这也是口令要用随机时长的理由
    still = evaluate(synth(1, jitter=0., block_s=16.256), synth(2, jitter=0., block_s=16.256))
    assert still['mean']['shift_r2'] > G1_SHIFT and not still['G1'], ('节拍对上平移', still['mean'])

    # 合格线不能误伤：按得晚 0.7 秒、空按误触 0.2 秒都不算废；空按一直碰板才算
    s = synth(1, late=.7)
    assert quality(s, table(s))['ok'], quality(s, table(s))
    s = synth(1, air_touch=.2)
    assert quality(s, table(s))['ok'], quality(s, table(s))
    s = synth(1, air_touch=7.)
    assert not quality(s, table(s))['ok']
    print(f"ok: wl8_force 正反检查通过（好数据 R² {min(good['mean']['emg_r2'], good['mean']['own_block_r2']):.2f}，按压段内 {good['mean']['press_r2']:.2f}，领先 {base_lag*1e3:.0f} ms）")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--probe', action='store_true')
    ap.add_argument('--hold', type=float, default=5., help='--probe 每档按多久')
    ap.add_argument('--record', action='store_true')
    ap.add_argument('--wear', default='A', choices=('A', 'B'))
    ap.add_argument('--site', default='wrist', choices=('wrist', 'forearm'))
    ap.add_argument('--seed', type=int, default=None, help='口令时长的随机种子，默认按时间取')
    ap.add_argument('--port')
    ap.add_argument('--recover', metavar='SPOOL')
    ap.add_argument('--eval', nargs=2, metavar=('A.npz', 'B.npz'))
    ap.add_argument('--out')
    a = ap.parse_args()
    if a.check: return check()
    if a.probe: return probe(a)
    if a.record:
        a.seed = int(time.time()) if a.seed is None else a.seed
        return record(a)
    if a.recover: return rebuild(Path(a.recover))
    if a.eval:
        sa, sb = load(a.eval[0]), load(a.eval[1])
        if (sa['meta'].get('wear'), sa['meta'].get('recordedAt')) == (sb['meta'].get('wear'), sb['meta'].get('recordedAt')) or sa['meta'].get('site') != sb['meta'].get('site'):
            print('拒绝评估：两份要是同一部位的两次不同佩戴'); return 1
        rep = evaluate(sa, sb)
        show(rep)
        if a.out: Path(a.out).write_text(json.dumps(rep, ensure_ascii=False, indent=2) + '\n')
        return 0
    ap.print_help()


if __name__ == '__main__':
    sys.exit(main())

"""用唯理八通道手环控制光标（v1）。按主方案（docs/superpowers/plans/2026-09-30-emg-imu-angry-birds.md 第 8 节）分阶段：
  --stage move（默认）：只用 IMU，转手腕移动光标，不看肌电；
  --stage drag：再加肌电，捏合保持 = 按住左键，松开 = 松开左键。第一版不映射单击（--click 才开，默认关）。

数据来自采集服务 emg_web.py --wl8 的 /api/emg/stream8（肌电 + `event: imu`），不另开串口。
每次佩戴先做 30 秒语音引导校准（放松 → 捏住 ×3 → 手腕左右 → 手腕上下），阈值和轴向都从校准推，不写死。

    python3 wl8_cursor.py --check              # 合成数据自检，不碰光标
    python3 wl8_cursor.py                      # 校准后只打印事件（演练，不动光标）
    python3 wl8_cursor.py --enable             # 阶段一：真正移动光标；Ctrl-C 停止
    python3 wl8_cursor.py --enable --stage drag   # 阶段二：加捏合抓放
    python3 wl8_cursor.py --enable --calib emg-wl8-raw/cursor-calib-XXXX.json   # 复用本次佩戴的校准

安全：默认不发任何鼠标事件；断流超过 0.3 s 自动松开左键并停住光标；Ctrl-C 同样先松开再退出。
"""
import argparse
import collections
import json
import queue
import subprocess
import sys
import threading
import time
import urllib.parse
import urllib.request
from pathlib import Path

import numpy as np
from scipy.signal import butter, iirnotch, sosfilt, tf2sos

import wl8

FS = 2000
SERVICE = 'http://127.0.0.1:8767'
ON, OFF, CONFIRM = .6, .3, 3            # 捏合分数的开 / 关阈值（迟滞）和连续确认次数（每次约 50 ms）
CLICK_S = .3                            # 捏住短于这个时长算单击，更长算按住
STALL_S = .3                            # 断流超过这个时长：松开左键、停住光标
DEADZONE, GAIN, VMAX = .12, 700., 2500.  # rad/s 死区（真实静止 std 0.015–0.03，手慢动 0.1–0.3）；px/s 每 rad/s；最大速度 px/s
IMU_HZ, TAU = 222, .06                  # IMU 实际约 222 Hz；速度低通时间常数 60 ms
ACCEL = 1.                              # 指针加速：有效增益 = GAIN ×（1 + ACCEL × 超出死区的 rad/s），慢动作准、快动作远
SNAP = .35                              # 直线辅助：次方向不到主方向 35% 当串扰压掉，35%–70% 渐变，超过 70% 照常斜走
REACT_S = 1.2                           # 估主方向时每段开头跳过的时间：实测动作比口令晚 1–1.5 s，段首常混着上一段的尾巴
FIRST_S = .3                            # 判"第一下"方向只跳这么多：有人一听口令就动，跳太多会把回摆当成第一下
ART_UV = 5000                            # 滤波后超过 5 mV 当电极接触伪迹（真实表面肌电很少过几 mV；2026-10-02 实测接触差时 1–11% 的时间有）
ART_RELEASE_S = 1.                      # 按住时伪迹连续超过 1 s：看不清还捏没捏，松开（宁可丢一次拖拽，也不卡着左键）
STILL_RAD, STILL_S = .25, .3            # 前臂角速度低于这个且已持续 0.3 s 才允许新按下：实测动前臂的肌电是捏合的 2–10 倍，幅度阈值分不开
SLOW_RAD = .25                          # A1 平滑只压慢速段：时间常数 = TAU / (1 + 角速度 / SLOW_RAD)；静止 60 ms 去抖，1 rad/s 约 12 ms，快动作不再背 60 ms 延迟
SOFT_FLOOR = .03                        # A3 软死区：低于这个当噪声归零；底线到 2×死区−底线之间二次过渡（连续、斜率连续），之后与硬死区同斜率
REZERO_RAD, REZERO_S, REZERO_TAU = .05, 1., 2.   # A3 零点修正：低通后角速度 < 0.05 rad/s 持续 1 s 才当静止，零点以 2 s 时间常数跟过去；有意慢移 0.1–0.3 rad/s 不会被吃掉
HP_HZ = 20                               # 肌电高通；100 Hz 在旧数据上误触更少但未经独立验证，见 evidence 3.25


class Envelope:
    """因果的 20 Hz 高通 + 50 Hz 1–9 次陷波，再取最近 100 ms 的 RMS（每路一个值）。"""
    def __init__(self, n=8, win_s=.1):
        parts = [butter(4, HP_HZ, 'hp', fs=FS, output='sos')]
        parts += [tf2sos(*iirnotch(50 * k, 30, FS)) for k in range(1, 10)]
        self.sos = np.vstack(parts); self.zi = np.zeros((len(self.sos), 2, n))
        self.win = int(win_s * FS); self.sq = np.zeros((0, n))

    def push(self, x):
        """返回最近窗口的 RMS；伪迹样本先削到 ART_UV，self.peak 记下窗口里每路的最大绝对值（> ART_UV 就是有伪迹）。"""
        y, self.zi = sosfilt(self.sos, np.asarray(x, float), axis=0, zi=self.zi)
        self.ab = np.concatenate([getattr(self, 'ab', np.zeros((0, y.shape[1]))), np.abs(y)])[-self.win:]
        self.peak = self.ab.max(0)
        self.sq = np.concatenate([self.sq, np.clip(y, -ART_UV, ART_UV) ** 2])[-self.win:]
        return np.sqrt(self.sq.mean(0))


def gyro_axes(gyro_rest, gyro_lr, gyro_ud):
    """gyro_*: (T,3) rad/s。左右段方差最大的轴 = x，上下段剩下两轴里最大的 = y；方向看口令里"先往右 / 先往上"的第一下。
    另给 proj（2×3）：两段动作各自在三轴里的主方向组成矩阵再求伪逆，前臂动作不正对传感器轴时把左右、上下解开。"""
    # 零点取"放平"段里最静的 1 秒：那段里常混着提前或迟到的动作（2026-10-02 实测）
    n = min(len(gyro_rest), IMU_HZ)
    starts = range(0, len(gyro_rest) - n + 1, max(1, n // 4))
    quiet = min(starts, key=lambda i: float(gyro_rest[i:i + n].var(0).sum()))
    bias = np.median(gyro_rest[quiet:quiet + n], 0)
    # 动起来的门槛随静止噪声走，最低 0.15 rad/s（≈ 9°/s）：挥手幅度只有二三十度，慢慢挥会低于原来的 0.36
    # 上限 0.3：放松那段手没完全静止时，门槛不能跟着涨到比真实动作还高（实测出现过 0.69）
    gate = min(.3, max(.15, 6 * float(np.std(gyro_rest - bias, 0).max())))
    def axis(seg, name, taken=None):
        v = seg - bias; var = v.var(0)
        if taken is not None: var[taken] = -1
        a = int(np.argmax(var)); moving = np.flatnonzero(np.abs(v[:, a]) > gate)
        if not len(moving):
            peak = np.abs(v).max(0)
            if taken is not None and peak[taken] > gate:
                raise ValueError(f'「{name}」的动作大多落在了左右那一轴（{peak[taken]:.2f} rad/s，其余 {np.delete(peak, taken).max():.2f}）：'
                                 '左右是手掌朝下像雨刷挥，上下是手肘不动整条前臂抬放，两个别混，重做校准')
            raise ValueError(f'「{name}」那段没检测到动作：最快只有 {peak[a]:.2f} rad/s（门槛 {gate:.2f}），动作再大、再快一点，重做校准')
        first = v[moving[0]:moving[0] + 80].sum(0)                    # 第一下动作（三轴）
        return a, 1 if first[a] > 0 else -1, first
    xa, xs, xf = axis(gyro_lr, '左右'); ya, ys, yf = axis(gyro_ud, '上下', taken=xa)
    main = lambda v: np.linalg.eigh(v.T @ v)[1][:, -1]                  # 来回动作的主方向（单位向量）
    skip = int((REACT_S - FIRST_S) * IMU_HZ)
    trim = lambda seg: seg[skip:] if len(seg) > 2 * skip else seg
    xd, yd = main(trim(gyro_lr) - bias), main(trim(gyro_ud) - bias)
    if abs(xd @ yd) > .8: raise ValueError('左右和上下两个动作在手环上几乎是同一个方向：左右挥手、上下抬前臂分清楚，重做校准')
    P = np.linalg.pinv(np.column_stack([xd, yd]))
    if P[0] @ xf < 0: P[0] *= -1                                         # 第一下往右 → 左右量为正
    if P[1] @ yf > 0: P[1] *= -1                                         # 第一下往上 → 上下量为负（屏幕 y 向下为正）
    return dict(gyro_bias=bias.tolist(), x_axis=xa, x_sign=xs, y_axis=ya, y_sign=-ys, proj=P.round(4).tolist())


def calibrate(rest_env, pinch_env, gyro_rest, gyro_lr, gyro_ud, k=3):
    """rest_env/pinch_env: (T,8) 包络；gyro_*: (T,3) rad/s。返回校准字典；信号太弱就报错。"""
    rest = np.median(rest_env, 0)
    pinch = np.percentile(pinch_env, 75, 0)                  # 捏住段里偏高的部分，避开起落过渡
    ratio = pinch / np.maximum(rest, 1e-6)
    chans = [int(c) for c in np.argsort(ratio)[::-1][:k]]
    if ratio[chans[0]] < 1.5:
        raise ValueError(f'捏合信号太弱：最好的一路只有放松的 {ratio[chans[0]]:.1f} 倍（需要 ≥ 1.5），检查佩戴、补水后重做校准')
    return dict(rest=rest.tolist(), pinch=pinch.tolist(), channels=chans, ratio=ratio.round(2).tolist(), **gyro_axes(gyro_rest, gyro_lr, gyro_ud))


def pinch_calibrate(rest_env, move_env, pinch_env, k=3, gap_env=None):
    """(T,8) 包络三段：放松 / 不捏只动前臂 / 捏住（都已剔掉伪迹窗）。按"捏住 vs 放松"选通道、定按下 / 松开阈值。
    动前臂的肌电实测是捏合的 2–10 倍（2026-10-02），幅度阈值分不开，所以不拿它定阈值：新按下要求前臂静止（STILL_*），
    动前臂那段只算出来给界面看。gap_env（两次捏之间的"松开"）也当放松用：实测接触差时动过之后基线整体抬高，
    只跟开头的放松比会把"抬高的基线"当成捏合，校准假成功、按下后再也松不开（2026-10-02 离线回放）。"""
    neg = rest_env if gap_env is None or not len(gap_env) else np.vstack([rest_env, gap_env])
    rest = np.median(neg, 0); pinch = np.percentile(pinch_env, 75, 0)
    ratio = np.median(pinch_env, 0) / np.maximum(rest, 1e-6)
    chans = [int(c) for c in np.argsort(ratio)[::-1] if ratio[c] >= 1.5][:k]
    if not chans:
        raise ValueError(f'捏合信号太弱：最好的一路捏住时只有放松的 {ratio.max():.1f} 倍（需要 ≥ 1.5），捏紧一点、电极沾湿后重做')
    cal = dict(rest=rest.tolist(), pinch=pinch.tolist(), channels=chans, ratio=ratio.round(2).tolist())
    lo = float(np.percentile([pinch_score(e, cal) for e in neg], 95))
    hi = float(np.percentile([pinch_score(e, cal) for e in pinch_env], 25))
    if hi - lo < .2:
        raise ValueError(f'捏住和放松分不开（放松时 {lo:.2f}，捏住时 {hi:.2f}，至少要差 0.2）：捏紧一点、保持住，重做')
    mv = float(np.percentile([pinch_score(e, cal) for e in move_env], 90)) if len(move_env) else None
    return dict(cal, move90=np.percentile(move_env, 90, 0).round(2).tolist() if len(move_env) else None,
                on=round(lo + .6 * (hi - lo), 3), off=round(lo + .25 * (hi - lo), 3), rest_p95=round(lo, 3), pinch_p25=round(hi, 3),
                move_p90=None if mv is None else round(mv, 3))


def fist_score(env, f):
    """握拳分数：0 = 放松，1 = 校准时的握拳水平；取握拳时升高的所有路（握拳是多路一起大幅升高，捏合只有几路）。"""
    c = f['channels']; r = np.array(f['rest'])[c]; p = np.array(f['fist'])[c]
    return float(np.mean(np.log(np.maximum(np.asarray(env, float)[c], 1e-6) / r) / np.log(p / r)))


def fist_calibrate(rest_env, fist_env, gap_env=None, pcal=None):
    """握拳离合（像把鼠标提起来）：握住时光标冻结。阈值必须高过放松、捏住、动前臂三者：
    低于捏住，捏一下就冻结；低于动前臂，松拳后边动边还冻着（松开线以下才解除）。分不开就报错，不硬上。"""
    neg = rest_env if gap_env is None or not len(gap_env) else np.vstack([rest_env, gap_env])
    rest = np.median(neg, 0); fist = np.percentile(fist_env, 75, 0)
    ratio = np.median(fist_env, 0) / np.maximum(rest, 1e-6)
    chans = [int(c) for c in np.flatnonzero(ratio >= 1.5)]
    if len(chans) < 4:
        raise ValueError(f'握拳信号太弱：只有 {len(chans)} 路升到放松的 1.5 倍以上（需要 ≥ 4 路），握紧一点后重做')
    f = dict(rest=rest.tolist(), fist=fist.tolist(), channels=chans, ratio=ratio.round(2).tolist())
    others = {'放松': float(np.percentile([fist_score(e, f) for e in neg], 95))}
    if pcal and pcal.get('pinch'): others['捏住'] = fist_score(pcal['pinch'], f)
    if pcal and pcal.get('move90'): others['动前臂'] = fist_score(pcal['move90'], f)
    lo, hi = max(others.values()), float(np.percentile([fist_score(e, f) for e in fist_env], 25))
    if hi - lo < .2:
        top = max(others, key=others.get)
        raise ValueError(f'握拳和{top}分不开（{top} {others[top]:.2f}，握拳 {hi:.2f}，至少要差 0.2）：握紧一点、保持住，重做')
    return dict(f, on=round(lo + .6 * (hi - lo), 3), off=round(lo + .25 * (hi - lo), 3), fist_p25=round(hi, 3),
                others={k: round(v, 3) for k, v in others.items()})


def pinch_score(env, cal):
    """0 = 放松水平，1 = 校准时的捏住水平（取最灵敏的几路平均，按 log 比例）。"""
    c = cal['channels']; r = np.array(cal['rest'])[c]; p = np.array(cal['pinch'])[c]
    return float(np.mean(np.log(np.maximum(env[c], 1e-6) / r) / np.log(p / r)))


class Clicker:
    """捏合分数 → 按下 / 松开 / 单击。迟滞 + 连续确认防抖；短捏算单击，长捏算按住。"""
    def __init__(self, click=False, on=ON, off=OFF):
        self.state, self.hi, self.lo, self.t_on, self.click, self.on, self.off = 'idle', 0, 0, 0., click, on, off

    def update(self, score, t, can_press=True):
        """can_press=False（前臂在动）时不开始新的按下、等待中的作废；已经按住的不受影响，拖拽照常。"""
        self.hi = self.hi + 1 if score > self.on else 0
        self.lo = self.lo + 1 if score < self.off else 0
        if self.state == 'idle' and self.hi >= CONFIRM and can_press:
            self.state, self.t_on = 'pending', t
        elif self.state == 'pending':
            if not can_press: self.state = 'idle'; return []
            if self.lo >= CONFIRM: self.state = 'idle'; return ['click'] if self.click else []
            if t - self.t_on >= CLICK_S and score > self.on: self.state = 'held'; return ['down']   # 到 0.3 s 时还得明确捏着：包络拖尾不算
        elif self.state == 'held' and self.lo >= CONFIRM:
            self.state = 'idle'; return ['up']
        return []

    def release(self):
        """断流 / 退出时调用：按着就补一个松开。"""
        was = self.state == 'held'; self.state, self.hi, self.lo = 'idle', 0, 0
        return ['up'] if was else []


class Aim:
    """陀螺仪角速度 → 光标速度：低通 → 投影成左右 / 上下 → 直线辅助 → 圆形死区 → 指针加速 → 限速。
    每个 IMU 样本都过一遍低通，结果与数据怎么分块无关。旧校准（没有 proj）退回按单轴取。"""
    def __init__(self, cal, gain=GAIN, deadzone=DEADZONE, accel=ACCEL, adaptive=True, soft=True, rezero=True):
        self.cal, self.gain, self.deadzone, self.accel, self.w = cal, gain, deadzone, accel, np.zeros(3)
        self.adaptive, self.soft, self.rezero = adaptive, soft, rezero            # A1 / A3 三个开关，可逐项对照
        self.bias, self.quiet = np.array(cal['gyro_bias'], float), 0.           # 零点修正只改这份，不写回校准文件

    def velocity(self, gyro, dt=1 / IMU_HZ):
        c = self.cal; r = np.asarray(gyro, float) - self.bias
        tau = TAU / (1 + np.linalg.norm(r) / SLOW_RAD) if self.adaptive else TAU
        self.w += (1 - np.exp(-dt / tau)) * (r - self.w)
        w = self.w
        if self.rezero:
            self.quiet = self.quiet + dt if np.linalg.norm(w) < REZERO_RAD else 0.
            if self.quiet >= REZERO_S: self.bias += dt / REZERO_TAU * w
        p = np.asarray(c['proj']) @ w if 'proj' in c else np.array([c['x_sign'] * w[c['x_axis']], c['y_sign'] * w[c['y_axis']]])
        a = np.abs(p); i = int(np.argmax(a))
        p[1 - i] *= np.clip((a[1 - i] / max(a[i], 1e-9) - SNAP) / SNAP, 0, 1)
        s, d = float(np.hypot(*p)), self.deadzone; f = min(SOFT_FLOOR, d / 2)
        u = (0. if s <= f else (s - f) ** 2 / (4 * (d - f)) if s < 2 * d - f else s - d) if self.soft else s - d
        if u <= 0: return np.zeros(2)
        return p / s * min(VMAX, self.gain * u * (1 + self.accel * u))

    def step(self, rows):
        """一块 IMU（rad/s，(n,3)）→ 这块时间里光标该走的 (dx, dy) 与最后的速度。"""
        d, v = np.zeros(2), np.zeros(2)
        for g in rows: v = self.velocity(g); d += v / IMU_HZ
        return d, v


class Mouse:
    """Quartz 鼠标输出；enable=False 时只记录不发送。"""
    def __init__(self, enable):
        self.enable, self.log, self.down_now = enable, [], False
        if enable:
            import Quartz; self.Q = Quartz
            from ApplicationServices import AXIsProcessTrusted
            if not AXIsProcessTrusted(): raise PermissionError('未授予辅助功能权限：系统设置 → 隐私与安全性 → 辅助功能，勾选运行采集服务 / 本脚本的宿主（终端或 App）')

    def _post(self, kind, pos, button=None):
        e = self.Q.CGEventCreateMouseEvent(None, kind, pos, self.Q.kCGMouseButtonLeft if button is None else button); self.Q.CGEventPost(self.Q.kCGHIDEventTap, e)

    def pos(self):
        if not self.enable: return (0., 0.)
        p = self.Q.CGEventGetLocation(self.Q.CGEventCreate(None)); return (p.x, p.y)

    def act(self, what, dx=0., dy=0.):
        self.log.append(what if what not in ('move', 'scroll') else (what, round(dx, 1), round(dy, 1)))
        if what == 'down': self.down_now = True
        if what == 'up': self.down_now = False
        if not self.enable: return
        Q, (x, y) = self.Q, self.pos()
        if what == 'move':
            b = Q.CGDisplayBounds(Q.CGMainDisplayID())
            x = min(max(x + dx, 0), b.size.width - 1); y = min(max(y + dy, 0), b.size.height - 1)
            self._post(Q.kCGEventLeftMouseDragged if self.down_now else Q.kCGEventMouseMoved, (x, y))
        elif what == 'down': self._post(Q.kCGEventLeftMouseDown, (x, y))
        elif what == 'up': self._post(Q.kCGEventLeftMouseUp, (x, y))
        elif what == 'click':                                                   # 松开 30 ms 后补，不在采集线程里睡
            self._post(Q.kCGEventLeftMouseDown, (x, y)); threading.Timer(.03, self._post, args=(Q.kCGEventLeftMouseUp, (x, y))).start()
        elif what == 'right_click':                                             # 手势「中指捏」用（wl8_actions.py）
            self._post(Q.kCGEventRightMouseDown, (x, y), Q.kCGMouseButtonRight)
            threading.Timer(.03, self._post, args=(Q.kCGEventRightMouseUp, (x, y), Q.kCGMouseButtonRight)).start()
        elif what == 'scroll':                                                  # 手势「拇指滑动」用：dy 为行数，正 = 内容向上（往下翻）
            e = Q.CGEventCreateScrollWheelEvent(None, Q.kCGScrollEventUnitLine, 1, -int(round(dy))); Q.CGEventPost(Q.kCGHIDEventTap, e)


# ------------------------------------------------------------------ 实时 ----
def stream(q):
    """后台线程：读 SSE，把 ('emg', array) / ('imu', array) 放进队列。"""
    st = json.load(urllib.request.urlopen(SERVICE + '/api/emg/state', timeout=3))
    if (st.get('rig') or {}).get('kind') != 'wl8': q.put(('error', '采集服务不是八通道模式（emg_web.py --wl8）')); return
    url = SERVICE + '/api/emg/stream8?project=' + urllib.parse.quote((st.get('project') or {}).get('id', ''))
    try:
        with urllib.request.urlopen(url, timeout=5) as r:
            kind = 'emg'
            for line in r:
                if line.startswith(b'event:'): kind = line[6:].strip().decode()
                elif line.startswith(b'data:'):
                    if kind == 'boundary':
                        while True:
                            try: q.get_nowait()
                            except queue.Empty: break
                        q.put_nowait(('error', '采集边界已改变，请重新校准')); return
                    if kind in ('emg', 'imu'): q.put((kind, np.array(json.loads(line[5:])['samples'], float)))
                    kind = 'emg'
    except Exception as e:
        q.put(('error', f'数据流中断：{e}'))


MUTE = False
def say(text):
    print('口令：', text, flush=True)
    if not MUTE: subprocess.Popen(['say', '-v', 'Tingting', text])


def run_calibration(q, hand, stage):
    """语音引导 30 秒；按口令时间切段收集包络和陀螺仪。"""
    env, steps, rec = Envelope(), [], {k: [] for k in ('rest', 'pinch', 'grest', 'lr', 'ud')}
    plan = [(0, 5, '放松，手别动', 'rest'), (5, 3, '捏住，保持', 'pinch'), (8, 2, '松开', None), (10, 3, '捏住，保持', 'pinch'),
            (13, 2, '松开', None), (16, 3, '捏住，保持', 'pinch'), (19, 2, '松开', None),
            (21, 5, '手掌朝下左右挥手，先往右', 'lr'), (26, 5, '手肘不动，整条前臂上下抬，先往上', 'ud')]
    if stage == 'move':                                  # 阶段一不需要捏合段
        plan = [(0, 5, '放松，手别动', 'rest'), (5, 5, '手掌朝下左右挥手，先往右', 'lr'), (10, 5, '手肘不动，整条前臂上下抬，先往上', 'ud')]
    end = plan[-1][0] + plan[-1][1] + 1
    say('开始校准'); time.sleep(1.5); t0 = time.monotonic(); said = set()
    while (t := time.monotonic() - t0) < end:
        for start, dur, text, key in plan:
            if t >= start and start not in said: said.add(start); say(text)
        cur = next((key for start, dur, text, key in plan if start + FIRST_S <= t < start + dur), None)
        try: kind, x = q.get(timeout=1)
        except queue.Empty: continue
        if kind == 'error': sys.exit(x)
        if kind == 'emg':
            e = env.push(x)
            if cur in ('rest', 'pinch'): rec[cur].append(e)
        elif kind == 'imu':
            g = x[:, :3] * wl8.GYRO_SCALE
            if cur == 'rest': rec['grest'].append(g)
            elif cur in ('lr', 'ud'): rec[cur].append(g)
    need = ('rest', 'grest', 'lr', 'ud') + (('pinch',) if stage == 'drag' else ())
    for k in need:
        if not rec[k]: sys.exit(f'校准段「{k}」没有收到数据：检查手环是否在推流')
    pinch = np.array(rec['pinch']) if stage == 'drag' else np.array(rec['rest']) * 3      # 阶段一不用肌电，占位
    cal = calibrate(np.array(rec['rest']), pinch, np.vstack(rec['grest']), np.vstack(rec['lr']), np.vstack(rec['ud']))
    cal.update(hand=hand, stage=stage, created=time.strftime('%Y-%m-%dT%H:%M:%S'))
    path = Path('emg-wl8-raw') / f'cursor-calib-{time.strftime("%Y%m%d-%H%M%S")}.json'
    path.parent.mkdir(exist_ok=True); path.write_text(json.dumps(cal, ensure_ascii=False, indent=1))
    say('校准完成'); print('校准：', path, '| 最灵敏几路', [c + 1 for c in cal['channels']], '| 捏合/放松倍数', cal['ratio'],
                        f"| x 用陀螺第 {cal['x_axis']} 轴，y 用第 {cal['y_axis']} 轴")
    return cal


def run(cal, mouse, stage='move', click=False):
    q = queue.Queue(maxsize=512); threading.Thread(target=stream, args=(q,), daemon=True).start()
    env, clk, aim = Envelope(), Clicker(click), Aim(cal)
    last, stalled, n = time.monotonic(), False, 0
    print(f'运行中 · 阶段 {stage}' + ('（真实光标）' if mouse.enable else '（演练，只打印移动量）') + '，Ctrl-C 停止', flush=True)
    try:
        while True:
            try: kind, x = q.get(timeout=.05)
            except queue.Empty: kind, x = None, None
            now = time.monotonic()
            if kind == 'error': print(x); break
            if kind is None:
                if not stalled and now - last > STALL_S:
                    stalled = True; ups = clk.release(); [mouse.act(a) for a in ups]
                    print('断流：停住光标' + ('，已松开左键' if ups else ''), flush=True)
                continue
            last, stalled = now, False
            if kind == 'emg' and stage == 'drag':
                for a in clk.update(pinch_score(env.push(x), cal), now):
                    mouse.act(a); print(time.strftime('%H:%M:%S'), a, flush=True)
            elif kind == 'imu' and clk.state != 'pending':          # 刚捏上的那一下先停住光标，单击更准
                d, _ = aim.step(x[:, :3] * wl8.GYRO_SCALE)
                if d.any(): mouse.act('move', *d)
            n += 1
    except KeyboardInterrupt:
        pass
    finally:
        [mouse.act(a) for a in clk.release()]; print('已停止（左键已松开）')


# ------------------------------------------------------------ 采集服务里用 ----
class Controller:
    """App「④ 控制」页背后的光标控制器。挂在采集服务的手环 IMU / 肌电上，不另开串口。
    阶段一 move：只移动。阶段二 drag：捏住保持 = 按下左键，松开 = 松开左键，中间转手腕就是拖拽；短捏不点击。
    off → 校准（15 s）→ 演练（只算不发，默认）→ 显式 enable 才动真光标；drag 另要捏合校准（22 s）。
    断流、看门狗、停止、演练、重新校准：先补一个松开左键，再回演练（主方案 8.4）。"""
    # 手环戴在前臂上，只感知前臂的转动：只弯手腕时前臂几乎不动、测不到，所以上下要整条前臂抬（手肘当支点）
    PLAN = ((0, 5, '放松，手别动', 'rest'), (5, 5, '手掌朝下左右挥手，先往右', 'lr'), (10, 5, '手肘不动，整条前臂上下抬，先往上', 'ud'))
    PINCH_PLAN = ((0, 4, '手放松，别动', 'rest'), (4, 5, '不捏，前臂左右上下随便动', 'move'), (9, 5, '捏住，保持', 'pinch'), (14, 4, '松开', 'gap'),
                  (18, 5, '捏住，保持', 'pinch'), (23, 4, '松开', 'gap'), (27, 5, '捏住，保持', 'pinch'))
    DRIFT_WAIT_S = 3.
    FIST_PLAN = ((0, 4, '手放松，别动', 'rest'), (4, 4, '握拳，用力保持', 'fist'), (8, 4, '松开', 'gap'),
                 (12, 4, '握拳，用力保持', 'fist'), (16, 4, '松开', 'gap'), (20, 4, '握拳，用力保持', 'fist'))
    LEAD, DRIFT_S, PUB_S, WATCH_S = 2.6, 10, .05, 3.     # WATCH_S：移动中这么久没人来读状态（App 挂了 / 关了）就回演练
    SAY_LEAD_S = 1.2                                     # say 起播约慢 1.2 s（2026-10-02 实测）：口令提前这么多发，听到时正好是段落开始；
                                                         # LEAD 从 1.5 加到 2.6，让「开始校准」念完再接第一段口令，不叠在一起
    EMG_STEP, PINCH_REACT_S = 50, 2.2                    # 每 50 个肌电样本（25 ms）算一次捏合分数；每段开头 2.2 s 不算：
                                                         # 实测口令到动作稳定慢约 2 s（say 起播 1.2 s + 念完 + 反应，2026-10-02 分通道对照）

    def __init__(self, rig, root, mouse=None, clock=time.monotonic, voice=True):
        self.rig, self.root, self.clock, self.voice, self.mouse = rig, Path(root), clock, voice, mouse
        self.lock, self.subscribers, self.sub = threading.RLock(), [], None
        self.mode, self.note, self.cal, self.aim, self.calib, self.drift, self.cal_path = 'off', '', None, None, None, None, None
        self.gain, self.deadzone, self.last, self.pub, self.v, self.moves, self.seen = GAIN, DEADZONE, 0., 0., np.zeros(2), 0, 0.
        self.accel = ACCEL
        self.opts = {'adaptive': True, 'soft': True, 'rezero': True, 'click': True}    # A1 自适应平滑 / A3 软死区、零点修正 / A2 短捏单击
        self.gaps, self.procs, self.clicks = collections.deque(maxlen=1000), collections.deque(maxlen=1000), 0   # IMU 块到达间隔、回调处理时间（s）
        self.watch_id = 0
        self.pcal, self.pcal_path, self.env, self.ebuf, self.score, self.last_emg = None, None, Envelope(), [], 0., 0.
        self.clk, self.events, self.drags, self.moving_until, self.artifacts, self.art_block, self.art_since = Clicker(), [], 0, 0., 0, False, 0.
        self.fcal, self.fcal_path, self.fclk, self.fscore, self.clutch = None, None, Clicker(), 0., False   # 握拳离合
        rig.imu_subscribers.append(self.feed)
        rig.frame_subscribers.append(self.feed_emg)
        if hasattr(rig, 'boundary_subscribers'): rig.boundary_subscribers.append(self.stream_boundary)

    def stream_boundary(self, event):
        """配置变化使幅度校准失效：松开动作并停用，重新校准后再启用。"""
        with self.lock:
            self._release()
            self.mode = 'off'; self.note = '采集配置改变，窗口已清空，请重新校准'
            self.env = Envelope(); self.ebuf = []; self.score = 0.
            self.pcal = self.fcal = self.calib = self.aim = None
            self.clk = Clicker(self.opts['click']); self.fclk = Clicker()
            self.cal = None; self.drift = None; self.v = np.zeros(2)
            self.fscore = 0.; self.clutch = False; self.art_block = False; self.art_since = 0.
            self.last = self.last_emg = 0.

    def _release(self):
        """按着就补一个松开；状态机清零。所有退出拖拽的路径都先走这里。"""
        self.watch_id += 1
        if self.mouse is not None and self.mouse.down_now:
            self.mouse.act('up'); self.events.append((round(self.clock(), 3), 'up', self.drags))
        self.clk = Clicker(self.opts['click'], self.pcal['on'], self.pcal['off']) if self.pcal else Clicker(self.opts['click'])

    def _check_live(self, now, gap=0.):
        """任一数据回调或页面心跳都能退出失效控制；不能等待已经停流的传感器来检查。"""
        with self.lock:
            if self.mode not in ('move', 'drag'): return
            why = ('信号暂停过' if gap > STALL_S else
                   'IMU断流' if now - self.last > STALL_S else
                   '肌电断流' if self.mode == 'drag' and now - self.last_emg > STALL_S else
                   f'App {self.WATCH_S:.0f} 秒没刷新状态' if now - self.seen > self.WATCH_S else None)
            if why:
                self._release(); self.mode, self.note = 'log', why + '，已松开左键、回到演练；确认正常后重新启用'

    def _watch_live(self, watch_id):
        with self.lock:
            if watch_id != self.watch_id or self.mode not in ('move', 'drag'): return
            self._check_live(self.clock())
            if self.mode in ('move', 'drag'):
                timer = threading.Timer(.1, self._watch_live, args=(watch_id,))
                timer.daemon = True; timer.start()

    def _say(self, text):
        if self.voice: subprocess.Popen(['say', '-v', 'Tingting', text])

    def action(self, body):
        a = body.get('action')
        with self.lock:
            if a in ('stop', 'log', 'calibrate', 'calibrate_pinch', 'calibrate_fist'):
                self._release(); self.clutch = False; self.fclk = Clicker(on=self.fcal['on'], off=self.fcal['off']) if self.fcal else Clicker()
            if a == 'stop':
                self.mode, self.note, self.calib, self.drift = 'off', '已停止', None, None
                if self.sub is not None: self.rig.unsubscribe(self.sub); self.sub = None
                return self.state()
            if a == 'config':
                self.gain = float(np.clip(float(body.get('gain', self.gain)), 100, 2000))
                self.deadzone = float(np.clip(float(body.get('deadzone', self.deadzone)), .03, .4))
                self.accel = float(np.clip(float(body.get('accel', self.accel)), 0, 3))
                for k in self.opts:
                    if k in body: self.opts[k] = bool(body[k])
                self.clk.click = self.opts['click']
                if self.aim:
                    self.aim.gain, self.aim.deadzone, self.aim.accel = self.gain, self.deadzone, self.accel
                    self.aim.adaptive, self.aim.soft, self.aim.rezero = (self.opts[k] for k in ('adaptive', 'soft', 'rezero'))
                    if not self.aim.rezero: self.aim.bias, self.aim.quiet = np.array(self.cal['gyro_bias'], float), 0.   # 关掉就回到校准零点，对照才干净
                return self.state()
            if self.sub is None: self.sub = self.rig.subscribe()
            if a == 'calibrate':
                self.mode, self.note, self.drift = 'calibrating', '', None
                self.calib = {'kind': 'imu', 'plan': self.PLAN, 't0': self.clock() + self.LEAD, 'said': set(), 'rec': {k: [] for k in ('rest', 'lr', 'ud')}}
                self._say('开始校准'); return self.state()
            if a == 'calibrate_fist':
                if self.pcal is None: raise ValueError('先做捏合校准：握拳要和捏合、动前臂比着定阈值')
                self.mode, self.note, self.drift = 'calibrating', '', None
                self.calib = {'kind': 'fist', 'plan': self.FIST_PLAN, 't0': self.clock() + self.LEAD, 'said': set(), 'rec': {k: [] for k in ('rest', 'fist', 'gap')}}
                self._say('开始握拳校准'); return self.state()
            if a == 'calibrate_pinch':
                self.mode, self.note, self.drift = 'calibrating', '', None
                self.calib = {'kind': 'pinch', 'plan': self.PINCH_PLAN, 't0': self.clock() + self.LEAD, 'said': set(), 'rec': {k: [] for k in ('rest', 'move', 'pinch', 'gap')}}
                self._say('开始捏合校准'); return self.state()
            if self.cal is None: raise ValueError('先校准：每次戴上都要做一次（15 秒）')
            if a == 'log':
                self.mode, self.note = 'log', '演练：只计算，光标不会动'; return self.state()
            if a == 'flip':                                   # 方向由"第一下"推，起手前的反向小动作会让它判反：留一个人工翻转
                k = 'x_sign' if body.get('axis') == 'x' else 'y_sign'
                self.cal[k] *= -1
                if 'proj' in self.cal: self.cal['proj'][0 if k == 'x_sign' else 1] = [-x for x in self.cal['proj'][0 if k == 'x_sign' else 1]]
                self.cal['flipped'] = self.cal.get('flipped', []) + [k]     # Aim 拿的是同一个字典，立即生效
                if self.cal_path: self.cal_path.write_text(json.dumps(self.cal, ensure_ascii=False, indent=1))
                self.note = ('左右' if k == 'x_sign' else '上下') + '方向已翻转'; return self.state()
            if a == 'enable':
                stage = 'drag' if body.get('stage') == 'drag' else 'move'
                if getattr(self.rig, 'replay', None): raise ValueError('回放数据不能控制真光标：只能演练')
                if self.clock() - self.last > STALL_S: raise ValueError('手环 IMU 没有数据：检查接收器和手环')
                if stage == 'drag' and self.pcal is None: raise ValueError('先做捏合校准（32 秒）')
                if stage == 'drag' and self.clock() - self.last_emg > STALL_S: raise ValueError('手环肌电没有数据：检查接收器和手环')
                if self.mouse is None: self.mouse = Mouse(True)          # 没有辅助功能权限会抛 PermissionError
                self._release()                                          # 从干净的松开状态开始，免得先收到一个没有按下的松开
                self.mode, self.seen = stage, self.clock()
                self._watch_live(self.watch_id)
                self.note = (('捏合中：短捏 = 单击，' if self.opts['click'] else '捏合中：') + '捏住保持 = 按下拖拽') if stage == 'drag' else '移动光标中（只移动，不点击）'
                return self.state()
            if a == 'drift':
                if self.mode not in ('log', 'move', 'drag'): raise ValueError('先校准，再在演练或移动状态下测漂移')
                # 先倒数 DRIFT_WAIT_S 再测：点按钮那一下手还在动，以前直接算进漂移（2026-10-02 一次测出 336.8 点）
                self.drift = {'t0': self.clock() + self.DRIFT_WAIT_S, 'd': [0., 0.], 'max': 0., 'done': False, 'peak_w': 0., 'said': False}
                self._say('三秒后测漂移，手放稳'); return self.state()
        raise ValueError(f'未知操作：{a}')

    def feed(self, imu):
        """rig 的 IMU 订阅：imu 是 (n,6) 原始计数。"""
        now, t_in = self.clock(), time.perf_counter(); g = np.asarray(imu, float)[:, :3] * wl8.GYRO_SCALE
        with self.lock:
            gap, self.last = now - self.last, now
            if self.mode == 'calibrating':
                return self._calibrate(now, g) if self.calib['kind'] == 'imu' else None
            if self.mode not in ('log', 'move', 'drag'): return
            self._check_live(now, gap)
            d, self.v = self.aim.step(g)
            if np.linalg.norm(self.aim.w) > STILL_RAD: self.moving_until = now + STILL_S    # 前臂在动：这段时间内不许新按下
            frozen = (self.mode == 'drag' and self.clk.state == 'pending'    # 刚捏上那一下先停住光标，按下的位置才准
                      or self.clutch or self.fclk.state == 'pending')          # 握拳离合：光标冻结（握上那 0.3 s 也先停住）
            if self.mode in ('move', 'drag') and d.any() and not frozen:
                self.mouse.act('move', *d); self.moves += 1
                if self.mouse.down_now: self.drags += 1
            if gap < 5: self.gaps.append(gap)                               # 主机侧更新间隔；暂停 / 重启那一下不算
            self.procs.append(time.perf_counter() - t_in)
            if self.drift and not self.drift['done']:
                dr = self.drift
                if not dr['said'] and now >= dr['t0'] - self.SAY_LEAD_S: dr['said'] = True; self._say('开始')
                if now >= dr['t0']:                                        # 倒数期间不算
                    dd = dr['d']; dd[0] += d[0]; dd[1] += d[1]; dr['max'] = max(dr['max'], float(np.hypot(*dd)))
                    dr['peak_w'] = max(dr['peak_w'], float(np.linalg.norm(self.aim.w)))   # 记下前臂动作：超过死区就不是零点漂移
                    if now - dr['t0'] >= self.DRIFT_S: dr['done'] = True; self._say('结束')
            if now - self.pub >= self.PUB_S:
                self.pub = now; tick = {'mode': self.mode, 'vx': round(float(self.v[0])), 'vy': round(float(self.v[1])),
                                        'score': round(self.score, 2), 'button': self._button(), 'clutch': self.clutch}
                for cb in list(self.subscribers):
                    try: cb(tick)
                    except Exception: pass

    def _button(self):
        return 'down' if self.mouse is not None and self.mouse.down_now else 'pending' if self.clk.state == 'pending' else 'up'

    def feed_emg(self, emg):
        """rig 的肌电订阅：(n,8) µV。每 EMG_STEP 个样本算一次包络和捏合分数；只有拖拽模式才真的按 / 松左键。"""
        now = self.clock()
        with self.lock:
            gap, self.last_emg = now - self.last_emg, now             # 没捏合校准也记数据心跳
            self._check_live(now, gap if self.mode == 'drag' else 0.)
            if self.pcal is None and not (self.calib and self.calib['kind'] in ('pinch', 'fist')): return
            self.ebuf.append(np.asarray(emg, float)); x = np.vstack(self.ebuf)
            k = len(x) // self.EMG_STEP * self.EMG_STEP; self.ebuf = [x[k:]] if k < len(x) else []
            for i in range(0, k, self.EMG_STEP):
                e = self.env.push(x[i:i + self.EMG_STEP])
                art = bool((self.env.peak > ART_UV).any())
                if self.calib and self.calib['kind'] in ('pinch', 'fist'): self._calibrate_emg(now, e, art); continue
                if not self.pcal: continue
                if (self.env.peak[self.pcal['channels']] > ART_UV).any():    # 电极接触伪迹：这一拍不改按键状态，
                    self.artifacts += 1; self.art_block = True                       # 之后滤波器还在振铃：分数回落到松开线以下才许新按下（振铃长短随伪迹大小变，定时等不可靠）
                    self.art_since = self.art_since or now
                    if self.mouse is not None and self.mouse.down_now and now - self.art_since > ART_RELEASE_S:
                        self._release(); self.note = f'电极接触伪迹超过 {ART_RELEASE_S:.0f} 秒，已松开左键（看不清你还捏没捏）'
                    continue
                self.art_since = 0.
                self.score = pinch_score(e, self.pcal)
                if self.score < self.pcal['off']: self.art_block = False
                fisty = False
                if self.fcal:                                                  # 握拳离合；握拳那一下捏合分数也会冲高，先判握拳
                    self.fscore = fist_score(e, self.fcal); fisty = self.fscore > self.fcal['off']
                    for act in self.fclk.update(self.fscore, now):
                        if act == 'down': self.clutch = True
                        if act == 'up': self.clutch = False; self.art_block = True     # 松拳的过渡段像捏合：捏合分数落回松开线以下才许新按下
                ok = now >= self.moving_until and not self.art_block and not self.clutch and not fisty
                for act in self.clk.update(self.score, now, can_press=ok):
                    if self.mode == 'drag' and act in ('down', 'up') and (act == 'down') != self.mouse.down_now:
                        self.mouse.act(act); self.events.append((round(now, 3), act, self.drags))
                    if self.mode == 'drag' and act == 'click' and not self.mouse.down_now:     # 短捏：松开那一刻发，不等第二击
                        self.mouse.act('click'); self.clicks += 1
                self.events = self.events[-100:]
                if self.events and self.events[0][1] == 'up': self.events = self.events[1:]     # 截断后别以松开开头

    def _calibrate_emg(self, now, e, art=False):
        """捏合 / 握拳两种肌电校准共用：按口令切段、剔伪迹，到点算阈值。"""
        c = self.calib; t = now - c['t0']; plan = c['plan']; end = plan[-1][0] + plan[-1][1]
        for start, dur, text, key in plan:
            if t >= start - self.SAY_LEAD_S and start not in c['said']: c['said'].add(start); self._say(text)
            if key in c['rec'] and start + self.PINCH_REACT_S <= t < start + dur:
                c.setdefault('n', {}).setdefault(key, [0, 0])[art] += 1
                if not art: c['rec'][key].append(e)                     # 伪迹窗不进校准
        if t < end: return
        r = c['rec']; n = c.get('n', {}); self.calib = None
        try:
            bad = {k: v[1] / max(1, sum(v)) for k, v in n.items()}
            if any(bad.get(k, 0) > .3 for k in ('rest', 'pinch', 'gap', 'fist')):
                raise ValueError('电极接触不好：放松或捏住时有 ' + '、'.join(f'{k} {v:.0%}' for k, v in bad.items()) + ' 的时间是伪迹，电极沾湿、表带收紧后重做')
            if c['kind'] == 'fist':
                if not r['rest'] or not r['fist']: raise ValueError('校准时没收到肌电数据：检查手环是否在推流')
                fcal = fist_calibrate(np.array(r['rest']), np.array(r['fist']), np.array(r['gap']).reshape(-1, 8), self.pcal)
                fcal['created'] = time.strftime('%Y-%m-%dT%H:%M:%S'); self.root.mkdir(parents=True, exist_ok=True)
                self.fcal_path = self.root / f'fist-calib-{time.strftime("%Y%m%d-%H%M%S")}.json'
                self.fcal_path.write_text(json.dumps(fcal, ensure_ascii=False, indent=1))
                self.fcal, self.fclk, self.clutch = fcal, Clicker(on=fcal['on'], off=fcal['off']), False
                self.mode, self.note = ('log' if self.cal else 'off'), '握拳校准完成：握拳光标冻结，松拳接着动'; self._say('握拳校准完成'); return
            if not r['rest'] or not r['pinch']: raise ValueError('校准时没收到肌电数据：检查手环是否在推流')
            pcal = pinch_calibrate(np.array(r['rest']), np.array(r['move']).reshape(-1, 8), np.array(r['pinch']), gap_env=np.array(r['gap']).reshape(-1, 8))
        except ValueError as err:
            self.mode, self.note = ('log' if self.cal else 'off'), str(err); self._say('握拳校准失败' if c['kind'] == 'fist' else '捏合校准失败'); return
        pcal['created'] = time.strftime('%Y-%m-%dT%H:%M:%S')
        self.root.mkdir(parents=True, exist_ok=True)
        self.pcal_path = self.root / f'pinch-calib-{time.strftime("%Y%m%d-%H%M%S")}.json'
        self.pcal_path.write_text(json.dumps(pcal, ensure_ascii=False, indent=1))
        self.pcal = pcal; self._release()
        self.mode, self.note = ('log' if self.cal else 'off'), '捏合校准完成：演练中，捏一下看按钮灯会不会亮'; self._say('捏合校准完成')

    def _calibrate(self, now, g):
        c = self.calib; t = now - c['t0']; end = self.PLAN[-1][0] + self.PLAN[-1][1]
        for start, dur, text, key in self.PLAN:
            if t >= start - self.SAY_LEAD_S and start not in c['said']: c['said'].add(start); self._say(text)
            if start + FIRST_S <= t < start + dur: c['rec'][key].append(g)  # 主方向的反应时间在 gyro_axes 里再跳
        if t < end: return
        r = c['rec']; self.calib = None
        try:
            if not all(r.values()): raise ValueError('校准时没收到 IMU 数据：检查手环是否在推流')
            cal = gyro_axes(*(np.vstack(r[k]) for k in ('rest', 'lr', 'ud')))
        except ValueError as e:
            self.mode, self.note = 'off', str(e); self._say('校准失败'); return
        cal.update(stage='move', created=time.strftime('%Y-%m-%dT%H:%M:%S'))
        self.root.mkdir(parents=True, exist_ok=True)
        self.cal_path = self.root / f'cursor-calib-{time.strftime("%Y%m%d-%H%M%S")}.json'
        self.cal_path.write_text(json.dumps(cal, ensure_ascii=False, indent=1))
        self.cal, self.aim = cal, Aim(cal, self.gain, self.deadzone, self.accel, *(self.opts[k] for k in ('adaptive', 'soft', 'rezero')))
        self.mode, self.note = 'log', '校准完成：演练中，光标不会动'; self._say('校准完成')

    def state(self):
        now, c = self.clock(), self.calib
        self._check_live(now)
        self.seen = now                                                    # 检查旧心跳后再续期
        cue = None
        if c:
            plan = c['plan']; t = now - c['t0']; i = max([k for k, p in enumerate(plan) if t >= p[0]], default=-1)
            cue = {'kind': c['kind'], 't': round(t, 2), 'total': plan[-1][0] + plan[-1][1], 'step': i, 'text': plan[i][2] if i >= 0 else '准备',
                   'plan': [{'start': p[0], 'dur': p[1], 'text': p[2], 'key': p[3]} for p in plan]}
        try: from ApplicationServices import AXIsProcessTrusted; trusted = bool(AXIsProcessTrusted())
        except Exception: trusted = None
        cal = {k: self.cal[k] for k in ('x_axis', 'x_sign', 'y_axis', 'y_sign', 'created')} if self.cal else None
        dr = self.drift
        drift = None if not dr else {'max_px': round(dr['max'], 1), 'done': dr['done'], 'wait_s': round(max(0., dr['t0'] - now), 1),
                                     'left_s': round(max(0., self.DRIFT_S - max(0., now - dr['t0'])), 1),
                                     'peak_w': round(dr['peak_w'], 3), 'moved': dr['peak_w'] > self.deadzone}
        ms = lambda xs, q: round(float(np.percentile(xs, q)) * 1000, 1) if xs else None
        upd = {'p50': ms(self.gaps, 50), 'p95': ms(self.gaps, 95), 'max': ms(self.gaps, 100), 'long': sum(x > .1 for x in self.gaps), 'n': len(self.gaps),
               'proc_p95': ms(self.procs, 95)}
        return {'mode': self.mode, 'note': self.note, 'opts': dict(self.opts), 'update_ms': upd, 'clicks': self.clicks,
                'bias_shift': round(float(np.linalg.norm(self.aim.bias - self.cal['gyro_bias'])), 4) if self.aim else None, 'calib': cue, 'cal': cal, 'gain': self.gain, 'deadzone': self.deadzone, 'accel': self.accel,
                'drift': drift, 'imu_age_ms': round((now - self.last) * 1000) if self.last else None, 'trusted': trusted,
                'replay': bool(getattr(self.rig, 'replay', None)), 'moves': self.moves, 'v': [round(float(x)) for x in self.v],
                'pcal': {k: self.pcal.get(k) for k in ('channels', 'on', 'off', 'rest_p95', 'pinch_p25', 'move_p90', 'created')} if self.pcal else None,
                'still': now >= self.moving_until, 'artifacts': self.artifacts,
                'fcal': {k: self.fcal.get(k) for k in ('channels', 'on', 'off', 'fist_p25', 'others', 'created')} if self.fcal else None,
                'fist_score': round(self.fscore, 2), 'clutch': self.clutch,
                'score': round(self.score, 2), 'button': self._button(), 'emg_age_ms': round((now - self.last_emg) * 1000) if self.last_emg else None,
                'events': {'down': sum(e[1] == 'down' for e in self.events), 'up': sum(e[1] == 'up' for e in self.events),
                           'paired': all(e[1] == ('down', 'up')[i % 2] for i, e in enumerate(self.events)), 'last': self.events[-6:]}}


# ------------------------------------------------------------------ 自检 ----
def check():
    rng = np.random.default_rng(0)
    # 1) 包络：50 Hz 大工频被陷波压住，宽带"肌电"爆发才抬高包络
    t = np.arange(FS) / FS
    mains = 20000 * np.sin(2 * np.pi * 50 * t)[:, None] * np.ones(8)
    e1 = Envelope(); [e1.push(mains[i:i + 64]) for i in range(0, FS, 64)]; quiet = e1.push(mains[:64])
    e2 = Envelope(); burst = rng.normal(0, 300, (FS, 8)); [e2.push(burst[i:i + 64]) for i in range(0, FS, 64)]; loud = e2.push(burst[:64])
    assert quiet.max() < .01 * 20000 / np.sqrt(2) and loud.min() > 150, (quiet.max(), loud.min())   # 工频至少压 40 dB
    # 2) 校准：ch2–ch4 对捏合敏感；左右转在陀螺第 2 轴（先往右 = 正），上下在第 0 轴（先往上 = 负）
    rest = rng.normal(60, 5, (100, 8)); pin = rest.copy(); pin[:, 1:4] *= 3
    g0 = rng.normal(0, .01, (300, 3)); lr = g0.copy(); lr[:, 2] = np.sin(np.linspace(0, 6 * np.pi, 300)) * 1.5
    ud = g0.copy(); ud[:, 0] = -np.sin(np.linspace(0, 6 * np.pi, 300)) * 1.5
    cal = calibrate(rest, pin, g0, lr, ud)
    assert sorted(cal['channels']) == [1, 2, 3] and (cal['x_axis'], cal['x_sign'], cal['y_axis'], cal['y_sign']) == (2, 1, 0, 1), cal
    try: calibrate(rest, rest * 1.1, g0, lr, ud)
    except ValueError: pass
    else: raise AssertionError('捏合太弱的校准被接受了')
    # 3) 状态机：长捏 = 按下 + 松开，短捏 = 单击；分数在两阈值之间来回抖不触发（迟滞）；断流时补松开
    def run_scores(scores, click=True):
        c, out = Clicker(click), []
        for i, s in enumerate(scores): out += c.update(s, i * .05)
        return out, c
    assert run_scores([0] * 10 + [1] * 20 + [0] * 10)[0] == ['down', 'up']
    assert run_scores([0] * 10 + [1] * 4 + [0] * 10)[0] == ['click']
    assert run_scores([0] * 10 + [1] * 4 + [0] * 10, click=False)[0] == [], '单击关闭时短捏仍产生了事件'
    assert run_scores([.45, .55, .62, .58, .35, .5] * 20)[0] == [], '阈值附近抖动触发了点击'
    assert run_scores([.9, .1] * 30)[0] == [], '单帧跳变触发了点击（缺少连续确认）'
    _, c = run_scores([1] * 20); assert c.state == 'held' and c.release() == ['up'] and c.state == 'idle'
    # 4) 瞄准：死区内不动；超过死区按方向移动；限速
    aim = Aim(cal)
    for _ in range(20): v0 = aim.velocity([.015, 0, -.015])                     # 软死区底线以下：噪声归零
    assert not v0.any(), v0
    hard = Aim(cal, soft=False)
    for _ in range(20): v0 = hard.velocity([.05, 0, -.05])
    assert not v0.any(), v0
    for _ in range(20): v1 = aim.velocity([0, 0, 1.0])
    assert v1[0] > 0 and v1[1] == 0, v1
    for _ in range(20): v2 = aim.velocity([-20, 0, 20])
    assert abs(np.hypot(*v2) - VMAX) < 1, v2
    # 4b) 解耦 + 直线辅助 + 加速：上下动作带 45% 漏到左右轴，解耦后光标只上下走；小斜向被压掉、真斜向保留；加速是非线性的
    t3 = np.linspace(0, 6 * np.pi, 600); r0 = rng.normal(0, .01, (300, 3))
    lr3 = np.c_[1.5 * np.sin(t3), np.zeros(600), np.zeros(600)]
    ud3 = np.c_[-.45 * 1.5 * np.sin(t3), -1.5 * np.sin(t3), np.zeros(600)]       # 先往上 = 轴 1 为负，且带着轴 0
    c3 = gyro_axes(r0, lr3, ud3); a3 = Aim(c3, accel=0)
    for _ in range(60): v3 = a3.velocity([-.45 * .8, -.8, 0])                   # 纯"往上"
    assert v3[1] < 0 and abs(v3[0]) < 1e-6, ('上下动作串到了左右', v3)
    old3 = Aim({k: c3[k] for k in c3 if k != 'proj'}, accel=0)
    for _ in range(60): o3 = old3.velocity([-.45 * .8, -.8, 0])
    assert abs(o3[0]) > 50, '对照：不解耦时应该看得到横向串扰（否则这条检查测不出东西）'
    a4 = Aim(c3, accel=0)
    for _ in range(60): sm = a4.velocity(np.array([.8, 0, 0]) + np.array([-.45, -1, 0]) * .2)   # 右挥带一点上下
    assert sm[0] > 0 and sm[1] == 0, ('小斜向没被直线辅助压掉', sm)
    a5 = Aim(c3, accel=0)
    for _ in range(60): dg = a5.velocity(np.array([.8, 0, 0]) + np.array([-.45, -1, 0]) * .8)    # 真斜着走
    assert dg[0] > 0 and dg[1] < 0, ('斜向被误压', dg)
    sp = lambda acc, w: np.hypot(*[Aim(c3, accel=acc).velocity([w, 0, 0], dt=10) for _ in range(1)][0])
    assert sp(1, 1.12) / sp(1, .32) > sp(0, 1.12) / sp(0, .32) * 1.5, '加速没让快动作比例更大'
    # 4d) A1 / A3：每项拿关掉的版本当必失败对照
    def run_aim(a, w, seconds):                                                 # 恒定角速度 w 跑 seconds 秒 → 位移 px、每样本速度
        vs = np.array([a.velocity(w) for _ in range(int(seconds * IMU_HZ))]); return np.abs(vs.sum(0) / IMU_HZ).sum(), vs
    slow = [0, 0, .1]                                                           # 有意慢移 0.1 rad/s（低于硬死区 0.12）
    assert run_aim(Aim(cal, accel=0, soft=False), slow, 2)[0] == 0, '对照：硬死区应吞掉 0.1 rad/s 慢移'
    assert run_aim(Aim(cal, accel=0), slow, 2)[0] > 10, '软死区下慢移没起步'
    sv = lambda x: np.hypot(*Aim(cal, accel=0, adaptive=False, rezero=False).velocity([0, 0, x], dt=10))
    e2 = 2 * DEADZONE - SOFT_FLOOR; assert abs(sv(e2 - 1e-6) - sv(e2 + 1e-6)) < .01 and all(np.diff([sv(x) for x in np.linspace(0, .5, 60)]) >= 0), '软死区不连续或不单调'
    step = lambda ad: int(np.argmax(np.hypot(*run_aim(Aim(cal, accel=0, adaptive=ad, rezero=False), [0, 0, 1.], .5)[1].T) > .9 * GAIN * (1 - DEADZONE))) / IMU_HZ
    assert step(True) < .035 and step(False) > .1, ('自适应平滑：1 rad/s 阶跃到 90% 的时间', step(True), step(False))
    # 陀螺零点漂了 0.045 rad/s（低于静止判据 0.05），死区调到 0.06
    drift = lambda rz: run_aim(Aim({**cal, 'gyro_bias': [0, 0, 0]}, deadzone=.06, rezero=rz), [0, 0, .045], 10)[0]
    assert drift(True) < 5 and drift(False) > 10, ('零点修正：10 s 静止漂移', drift(True), drift(False))
    eat = lambda rz: run_aim(Aim(cal, accel=0, rezero=rz), [0, 0, .12], 5)[0]
    assert eat(True) > .98 * eat(False), ('零点修正把有意慢移吃掉了', eat(True), eat(False))
    # 4c) 反应慢 1.3 s 的人：方向仍按口令后的第一下判对
    def lag_seg(axis_i, sign, lag):
        x = np.zeros((int(4.7 * IMU_HZ), 3)); k = int(lag * IMU_HZ)
        x[k:, axis_i] = sign * 1.2 * np.sin(np.linspace(0, 8 * np.pi, len(x) - k)); return x
    c4 = gyro_axes(r0, lag_seg(2, 1, 1.0), lag_seg(0, -1, 1.0))
    assert (c4['x_axis'], c4['x_sign'], c4['y_axis'], c4['y_sign']) == (2, 1, 0, 1), c4
    a6 = Aim(c4)
    for _ in range(60): v6 = a6.velocity([0, 0, .8])
    assert v6[0] > 0, ('慢半拍的人左右判反了', v6)
    # 5) 演练鼠标只记录、不发事件
    m = Mouse(False); m.act('down'); m.act('move', 3, 4); m.act('up'); m.act('scroll', 0, 3); assert m.log == ['down', ('move', 3, 4), 'up', ('scroll', 0, 3)] and not m.down_now
    # 6) 控制器：校准口令按时间切段 → 演练不发事件 → 启用才移动；断流回演练；回放拒绝启用；没转手腕校准失败
    class FakeRig:
        def __init__(self, replay=None): self.imu_subscribers, self.frame_subscribers, self.replay, self.subs = [], [], replay, 0
        def subscribe(self): self.subs += 1; return object()
        def unsubscribe(self, q): self.subs -= 1
    import tempfile
    def drive(ctl, clock, seconds, gyro):                    # gyro(t) -> rad/s 三轴；每 45 ms 送一块 10 个样本
        for _ in range(int(seconds / .045)):
            clock[0] += .045; tt = clock[0]
            ctl.feed(np.array([list(np.asarray(gyro(tt)) / wl8.GYRO_SCALE) + [0, 0, 0]] * 10))
    def wrist(t0):                                          # 按口令：静止 → 右先 z 轴来回 → 上先 x 轴来回（上 = 负）
        def g(t):
            t -= t0
            if 5.3 < t < 10: return [0, 0, 1.2 * np.sin(2 * np.pi * (t - 5.3) / 1.5)]
            if 10.3 < t < 15: return [-1.2 * np.sin(2 * np.pi * (t - 10.3) / 1.5), 0, 0]
            return [0, 0, 0]
        return g
    with tempfile.TemporaryDirectory() as d:
        clock, m = [100.], Mouse(False); rig = FakeRig()
        ctl = Controller(rig, d, mouse=m, clock=lambda: clock[0], voice=False)
        try: ctl.action({'action': 'enable'})
        except ValueError: pass
        else: raise AssertionError('没校准就能启用')
        ctl.action({'action': 'calibrate'}); t0 = clock[0] + Controller.LEAD
        drive(ctl, clock, Controller.LEAD + Controller.PLAN[-1][0] + Controller.PLAN[-1][1] + 1, wrist(t0))
        st = ctl.state(); assert st['mode'] == 'log' and (st['cal']['x_axis'], st['cal']['x_sign'], st['cal']['y_axis'], st['cal']['y_sign']) == (2, 1, 0, 1), st
        assert list(Path(d).glob('cursor-calib-*.json')), '校准没落盘'
        drive(ctl, clock, 1, lambda t: [0, 0, 1.0]); assert not m.log and ctl.state()['v'][0] > 0, '演练发了鼠标事件或速度方向错'
        ctl.action({'action': 'flip', 'axis': 'x'}); drive(ctl, clock, 1, lambda t: [0, 0, 1.0]); assert ctl.state()['v'][0] < 0, '左右翻转没生效'
        ctl.action({'action': 'flip', 'axis': 'x'}); drive(ctl, clock, 1, lambda t: [0, 0, 1.0]); assert ctl.state()['v'][0] > 0
        assert json.loads(ctl.cal_path.read_text())['flipped'] == ['x_sign', 'x_sign'], '翻转没写回校准文件'
        ctl.action({'action': 'enable'}); drive(ctl, clock, 1, lambda t: [0, 0, 1.0])
        drive(ctl, clock, 3.5, lambda t: [0, 0, 0]); assert ctl.mode == 'log' and '没刷新' in ctl.note, '没人看状态时还在移动'
        ctl.action({'action': 'enable'}); drive(ctl, clock, 1, lambda t: [0, 0, 1.0])
        assert m.log and all(e[0] == 'move' and e[1] >= 0 for e in m.log) and sum(e[1] > 0 for e in m.log) > len(m.log) / 2, m.log[:3]   # 软死区：手停后低通尾巴有 < 0.05 点的微移
        clock[0] += 1; n = len(m.log); drive(ctl, clock, .5, lambda t: [0, 0, 1.0])
        assert ctl.mode == 'log' and len(m.log) == n, '断流后没回演练 / 还在发移动'
        drive(ctl, clock, 1, lambda t: [0, 0, 0])                               # 先静下来：低通还在衰减时开测会算进上一段动作
        ctl.action({'action': 'drift'}); drive(ctl, clock, 1, lambda t: [0, 0, 1.0])                  # 倒数里手还在动：不该算进去
        drive(ctl, clock, Controller.DRIFT_WAIT_S - 1 + 10.2, lambda t: [.02, 0, -.02])
        dr = ctl.state()['drift']; assert dr['done'] and dr['max_px'] == 0 and not dr['moved'], ('倒数期间的动作被算进了漂移', dr)
        ctl.action({'action': 'drift'}); drive(ctl, clock, Controller.DRIFT_WAIT_S + 10.2, lambda t: [0, 0, .2])      # 必失败对照：慢慢漂的手腕要被量出来
        dr = ctl.state()['drift']; assert dr['max_px'] > 10 and dr['moved'], ('慢动作没被量出来或没标成"有动作"', dr)
        ctl.action({'action': 'stop'}); assert ctl.mode == 'off' and rig.subs == 0
        ctl.action({'action': 'calibrate'}); drive(ctl, clock, Controller.LEAD + Controller.PLAN[-1][0] + Controller.PLAN[-1][1] + 1, lambda t: [0, 0, 0])
        assert ctl.mode == 'off' and '没检测到' in ctl.note, ctl.note
        try: gyro_axes(np.zeros((50, 3)), np.c_[np.zeros(300), np.zeros(300), np.sin(np.linspace(0, 20, 300))], np.c_[np.zeros(300), np.zeros(300), np.sin(np.linspace(0, 20, 300))])
        except ValueError as e: assert '左右那一轴' in str(e), e
        else: raise AssertionError('上下和左右落在同一轴却校准通过了')
        rp = Controller(FakeRig('x.npz'), d, mouse=Mouse(False), clock=lambda: clock[0], voice=False); rp.cal, rp.aim = ctl.cal, ctl.aim
        rp.last = clock[0]
        try: rp.action({'action': 'enable'})
        except ValueError: pass
        else: raise AssertionError('回放数据启用了真光标')
    # 7) 阶段二：捏合校准 → 捏住拖拽。照 2026-10-02 实测：动前臂的肌电（各路 150 µV）比捏住（CH2–4 80 µV）还大
    LV = {'rest': [8] * 8, 'move': [150] * 8, 'pinch': [15, 80, 80, 80, 15, 15, 15, 15], 'both': [150, 160, 160, 160, 150, 150, 150, 150]}
    def drive2(ctl, clock, seconds, gyro, level, poll=True):  # 每 45 ms：10 个 IMU 样本 + 90 个肌电样本；poll = App 在读状态
        for _ in range(int(seconds / .045)):
            clock[0] += .045; tt = clock[0]
            ctl.feed(np.array([list(np.asarray(gyro(tt)) / wl8.GYRO_SCALE) + [0, 0, 0]] * 10))
            ctl.feed_emg(rng.normal(0, 1, (90, 8)) * np.asarray(level(tt), float))
            if poll: ctl.state()
    still = lambda t: [0, 0, 0]
    with tempfile.TemporaryDirectory() as d:
        clock, m = [500.], Mouse(False); rig = FakeRig()
        ctl = Controller(rig, d, mouse=m, clock=lambda: clock[0], voice=False)
        cal_x = {'gyro_bias': [0, 0, 0], 'x_axis': 2, 'x_sign': 1, 'y_axis': 0, 'y_sign': 1, 'created': 'check'}
        ctl.cal, ctl.aim, ctl.last = cal_x, Aim(cal_x, accel=0), clock[0]
        ctl.mode = 'log'
        try: ctl.action({'action': 'enable', 'stage': 'drag'})
        except ValueError as e: assert '捏合校准' in str(e)
        else: raise AssertionError('没做捏合校准就能拖拽')
        clock[0] += 60; ctl.feed_emg(np.zeros((90, 8)))     # 捏合校准失败 / 还没做时肌电照样在流，面板不能显示断流
        assert ctl.state()['emg_age_ms'] == 0, ('没捏合校准时肌电心跳不更新', ctl.state()['emg_age_ms'])
        ctl.action({'action': 'calibrate_pinch'}); t0 = clock[0] + Controller.LEAD
        def follow(t):                                     # 跟口令慢 2 s（实测）
            t -= t0 + 2.
            for start, dur, _, key in Controller.PINCH_PLAN:
                if start <= t < start + dur: return LV['pinch' if key == 'pinch' else 'move' if key == 'move' else 'rest']
            return LV['rest']
        drive2(ctl, clock, Controller.LEAD + Controller.PINCH_PLAN[-1][0] + Controller.PINCH_PLAN[-1][1] + 1, still, follow)
        pc = ctl.state()['pcal']; assert pc and set(pc['channels']) <= {1, 2, 3} and pc['rest_p95'] < pc['off'] < pc['on'] < pc['pinch_p25'], (ctl.note, pc)
        assert pc['move_p90'] > pc['on'], '这条检查要模拟"动前臂比捏住还大"，否则测不到静止门控'
        assert list(Path(d).glob('pinch-calib-*.json')), '捏合校准没落盘'
        ctl.action({'action': 'enable', 'stage': 'drag'}); m.log.clear()
        drive2(ctl, clock, 1, still, lambda t: LV['rest'])
        drive2(ctl, clock, 1.5, lambda t: [0, 0, 1.0], lambda t: LV['move'])          # 只动前臂（肌电比捏住还大）：不能按下
        drive2(ctl, clock, 1, lambda t: [0, 0, 1.0], lambda t: LV['both'])            # 边动边捏：也不能开始按下
        assert 'down' not in m.log, ('前臂在动时按下了', m.log[:5])
        drive2(ctl, clock, .5, still, lambda t: LV['rest'])                           # 停住
        n0 = len(m.log); drive2(ctl, clock, .8, still, lambda t: LV['pinch'])         # 静止时捏住 → 按下
        assert 'down' in m.log[n0:], ('静止捏住没按下', ctl.state()['score'], ctl.state()['pcal'])
        drive2(ctl, clock, 1.5, lambda t: [0, 0, 1.0], lambda t: LV['both'])          # 捏着转前臂 = 拖拽，不能中途松开
        assert 'up' not in m.log[n0:], '拖拽中途松开了'
        drive2(ctl, clock, .5, still, lambda t: LV['pinch'])                          # 停住
        drive2(ctl, clock, 1, still, lambda t: LV['rest'])                            # 松开
        seq = [e if isinstance(e, str) else 'move' for e in m.log[n0:]]
        i_d, i_u = seq.index('down'), seq.index('up')
        assert seq.count('down') == 1 and seq.count('up') == 1 and i_d < i_u and 'move' in seq[i_d:i_u], seq
        st = ctl.state(); assert st['events']['paired'] and st['events']['down'] == st['events']['up'] == 1 and ctl.drags > 0, st['events']
        a0 = ctl.artifacts; spikes = lambda t: np.where(np.arange(8) < 4, 30000., 8.)   # 静止时电极抖：20–30 mV 伪迹不能按下
        drive2(ctl, clock, 1, still, spikes); drive2(ctl, clock, 2, still, lambda t: LV['rest'])   # 80 mV 级伪迹后陷波振铃约 1.2 s   # 伪迹 + 之后的振铃都不能按下
        assert ctl.state()['events']['down'] == 1, '伪迹或振铃触发了按下'
        drive2(ctl, clock, .8, still, lambda t: LV['pinch']); assert m.down_now, '没按下，测不到伪迹松开'
        drive2(ctl, clock, 1.6, still, spikes); assert not m.down_now and '伪迹' in ctl.note, ('按住时持续伪迹没松开', ctl.note)
        drive2(ctl, clock, 1, still, lambda t: LV['rest']); a0 = ctl.artifacts - 1
        ev = ctl.state()['events']; assert ev['down'] == ev['up'] == 2 and ev['paired'] and ctl.artifacts > a0, ('伪迹段之后按键不对', ev)
        nd, nc = ctl.state()['events']['down'], ctl.clicks
        drive2(ctl, clock, .1, still, lambda t: [8] * 8)                              # A2 短捏（< 0.3 s）= 单击，不按下
        drive2(ctl, clock, .15, still, lambda t: LV['pinch']); drive2(ctl, clock, .6, still, lambda t: LV['rest'])
        assert ctl.state()['events']['down'] == nd and ctl.clicks == nc + 1 and m.log[-1] == 'click', ('短捏没单击或触发了按下', ctl.clicks - nc, m.log[-5:])
        ctl.action({'action': 'config', 'click': False}); assert ctl.state()['opts']['click'] is False
        drive2(ctl, clock, .15, still, lambda t: LV['pinch']); drive2(ctl, clock, .6, still, lambda t: LV['rest'])
        assert ctl.clicks == nc + 1, '单击关掉后短捏还在点'
        ctl.action({'action': 'config', 'click': True})
        drive2(ctl, clock, .5, lambda t: [0, 0, 1.0], lambda t: LV['rest']); drive2(ctl, clock, .1, lambda t: [0, 0, 1.0], lambda t: LV['pinch'])
        drive2(ctl, clock, .6, still, lambda t: LV['rest']); assert ctl.clicks == nc + 1, '边移动边短捏点了击（应该要先静止）'
        u = ctl.state()['update_ms']; assert abs(u['p50'] - 45) < 1 and u['proc_p95'] < 20, ('更新间隔统计不对', u)
        ctl.action({'action': 'config', 'soft': False, 'adaptive': False, 'rezero': False})
        assert not (ctl.aim.soft or ctl.aim.adaptive or ctl.aim.rezero) and ctl.state()['bias_shift'] == 0, '开关没传到 Aim'
        ctl.action({'action': 'config', 'soft': True, 'adaptive': True, 'rezero': True})
        # 按着的时候出事：断流 / 看门狗 / 演练按钮，都要补一个松开
        for how in ('stall', 'watch', 'log', 'emg_only', 'no_stream', 'no_callbacks'):
            ctl.action({'action': 'enable', 'stage': 'drag'}); drive2(ctl, clock, 1, still, lambda t: LV['pinch'])
            assert m.down_now, (how, '没按下去，测不到松开')
            if how == 'stall': clock[0] += 1; drive2(ctl, clock, .1, still, lambda t: LV['pinch'])
            if how == 'watch': drive2(ctl, clock, 3.5, still, lambda t: LV['pinch'], poll=False)
            if how == 'log': ctl.action({'action': 'log'})
            if how == 'emg_only': clock[0] += 1; ctl.feed_emg(rng.normal(0, 1, (90, 8)) * LV['pinch'])
            if how == 'no_stream': clock[0] += 1; ctl.state()
            if how == 'no_callbacks': clock[0] += 1; time.sleep(.3)
            assert not m.down_now and ctl.mode == 'log' and m.log[-1] == 'up' or (not m.down_now and ctl.mode == 'log'), (how, ctl.mode, m.log[-3:])
            assert ctl.state()['events']['paired'], (how, ctl.state()['events'])
            drive2(ctl, clock, .5, still, lambda t: LV['rest'])
        # 显式重新启用可续页面心跳；仅IMU移动不依赖肌电。
        drive2(ctl, clock, ctl.WATCH_S + .5, still, lambda t: LV['rest'], poll=False)
        assert ctl.action({'action': 'enable', 'stage': 'drag'})['mode'] == 'drag', '显式启用仍被旧页面心跳拦住'
        ctl.action({'action': 'log'}); ctl.pcal = None; ctl.last_emg = 0.
        assert ctl.action({'action': 'enable', 'stage': 'move'})['mode'] == 'move'
        drive(ctl, clock, 1., still)
        assert ctl.mode == 'move', '仅IMU移动被肌电缺失中止'
        ctl.action({'action': 'log'})
    r8 = lambda lv: np.abs(rng.normal(lv, lv * .1, (60, 8)))
    try: pinch_calibrate(r8(100.), r8(500.), r8(200.), gap_env=r8(200.))          # 动过之后基线整体抬到 200：捏住和松开一样
    except ValueError: pass
    else: raise AssertionError('松开和捏住一样大（只是基线抬高）还校准通过了')
    try: pinch_calibrate(r8(8.), r8(30.), r8(9.))
    except ValueError as e: assert '太弱' in str(e) or '分不开' in str(e), e
    else: raise AssertionError('捏住和放松一样大还校准通过了')
    print('wl8_cursor check passed: 陷波压工频、校准选通道和轴向、弱信号拒绝、长捏/短捏/迟滞/断流松开、死区与限速、解耦去串扰（含不解耦对照）、直线辅助与斜向保留、指针加速、反应慢 1.3 s 方向不反、演练不发事件；阶段二：捏合校准选对通道且阈值在放松和捏住之间、动前臂（肌电比捏住还大）和边动边捏都不按下、静止捏住才按下、捏着转前臂不中途松开、恰好一按一松、电极伪迹和之后的振铃不按下、短捏 = 单击（松开时发、可关、边动边捏不点）、软死区让慢移起步且连续单调（硬死区对照）、自适应平滑 1 rad/s 阶跃到 90% < 35 ms（固定 60 ms 对照 > 100 ms）、零点修正压住漂移（关掉对照 > 10 点）且不吃有意慢移、更新间隔统计、开关传到 Aim、断流/看门狗/演练时补松开、IMU停而EMG继续退出、两路停而页面刷新退出、两路与页面都停时后台退出、显式重新启用可续心跳、仅IMU移动不依赖肌电、捏不出信号时校准失败、基线抬高的假校准失败、按住时伪迹超 1 秒松开；控制器校准切段/演练不发/翻转方向/启用才动/没人看状态回演练/断流回演练/测漂移（先倒数、倒数里的动作不算、有动作单独标出）/回放拒绝/没转手腕失败')


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--check', action='store_true'); ap.add_argument('--enable', action='store_true', help='真正控制光标')
    ap.add_argument('--calib', help='复用已有校准文件（同一次佩戴）'); ap.add_argument('--hand', default='left')
    ap.add_argument('--service', default=SERVICE, help='采集服务地址（自测时指向假手环服务）'); ap.add_argument('--mute', action='store_true', help='不念口令')
    ap.add_argument('--stage', choices=('move', 'drag'), default='move'); ap.add_argument('--click', action='store_true', help='短捏 = 单击（默认关）')
    a = ap.parse_args()
    if a.check: check(); sys.exit()
    SERVICE, MUTE = a.service, a.mute
    try: mouse = Mouse(a.enable)
    except PermissionError as e: sys.exit(str(e))
    if a.calib: cal = json.loads(Path(a.calib).read_text())
    else:
        q = queue.Queue(maxsize=512); threading.Thread(target=stream, args=(q,), daemon=True).start(); cal = run_calibration(q, a.hand, a.stage)
    run(cal, mouse, a.stage, a.click)

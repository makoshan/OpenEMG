"""肌电手势控 Microduck：读采集服务的实时识别（ai_* 六类），翻成 Pollen 官方 UDP 手柄包（DKPD）发给鸭子的 netpadd。
上滑 = 一直往前走；下滑 = 停；左 / 右滑 = 转 TURN_S 秒；唤起 = 按一下 B（鞠躬：ground_pick 槽放 Spark 训的 bow 策略，Mako 11-03 定）；放松 = 保持。
不用 Start：策略已接管时按 Start 会 robot.init 回零，仿真鸭当场摔倒（Mircoduck/evidence/2026-11-03-m1-netpad）。
类别用服务端过了识别门的 top（峰峰值不够 / 不够确定时它改回放松，probs 不改），概率只拿来比 TH。
手环断流（STALE_S 没新样本）就忘掉在走、照常发摇杆归零的空包：鸭子原地停下待命，数据回来直接能用。
不再停发：停发 1 s 后 netpadd 会让鸭子坐下，而唤起改成鞠躬后没有手势能按 A 站起（坐着时 robotd 拒绝鞠躬；
数据回来补按 A 也不行，它正坐到一半时 A 被吞掉，11-03 仿真实测）。桥本身挂了才停发，那时 netpadd 照旧停下并坐下。
数据来源同 ai_confirm.find_service：真手环服务或 gesture_sim.py 都行；仿真和真机只差 --duck 地址。
Run: python3 host/duck_bridge.py [--duck 127.0.0.1:4210]
     python3 host/duck_bridge.py --check   # 自检：状态机 + gesture_sim → 桥 → 本机假 netpadd，逐包解码核对
"""
import http.client
import json
import random
import socket
import struct
import sys
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import ai_confirm

HZ = 30                     # 官方建议整包 30 Hz 重发
TH = .8                     # top 那类概率到这个数才算
N_FIRE = 3                  # 连续 3 个新样本（真服务 100 ms 推理一次，约 300 ms）才触发，单帧跳变不算
STALE_S = .35               # 这么久没有新样本 = 手环断流，改发空包；真服务能容忍连丢 2 次推理
TURN_S = 1.0                # 左 / 右滑转多久；满舵约 57°/s
TAP_S = .17                 # B 键按住多久再松开（5 帧；netpadd 按下沿触发，连发只算一次）
FULL, B = 32767, 1 << 1     # B = bit 1，默认绑 ground_pick（槽里放鞠躬）；A = bit 0 是坐 / 站，不用；Start 是 bit 6，别用
NAMES = {'ai_up': '上滑 → 前进', 'ai_down': '下滑 → 停', 'ai_left': '左滑 → 左转', 'ai_right': '右滑 → 右转', 'ai_summon': '唤起 → 鞠躬（B）'}


class Bridge:
    """纯状态机：喂 (t, probs, top) 样本和当前时间，pad() 返回这一拍要发的 (ly, rx, buttons)；一次数据都没来过时 None = 不发。"""
    def __init__(self):
        self.last_t, self.last_new = None, None
        self.run, self.turn, self.turn_until, self.tap_until = 0, 0, 0., 0.
        self.cand, self.count, self.fired, self.quiet = None, 0, None, 0

    def expired(self, now):
        """断流了吗；断了就忘掉在走 / 在转 / 在按，数据回来后从停着开始。feed 之前先问，免得卡顿后的新样本把空档盖掉。"""
        if self.last_new is not None and now - self.last_new <= STALE_S: return False
        self.run, self.turn_until, self.tap_until = 0, 0., 0.
        return True

    def feed(self, sample, now):
        self.expired(now)
        if sample and (self.last_t is None or sample[0] > self.last_t):
            self.last_t, self.last_new = sample[0], now
            t, probs, top = sample
            g = top if top in NAMES and float(probs.get(top, 0)) >= TH else None
            if g:
                if g != self.cand: self.cand, self.count = g, 0
                self.count, self.quiet = self.count + 1, 0
                if self.count >= N_FIRE and g != self.fired: self.fired = g; return self.fire(g, now)
            else:
                self.count, self.quiet = 0, self.quiet + 1     # 要「连续」N_FIRE 帧才触发；连续 N_FIRE 帧放松才重新上膛
                if self.quiet >= N_FIRE: self.cand = self.fired = None
        return None

    def fire(self, g, now):
        if g == 'ai_up': self.run = 1
        elif g == 'ai_down': self.run, self.turn_until = 0, 0.
        elif g in ('ai_left', 'ai_right'): self.turn, self.turn_until = (-1 if g == 'ai_left' else 1), now + TURN_S   # rx 正 = 右转（M1 实测）
        elif g == 'ai_summon': self.run, self.turn_until, self.tap_until = 0, 0., now + TAP_S   # 先停下再鞠躬，别带着满舵前进切策略
        return g

    def pad(self, now):
        if self.last_new is None: return None
        if self.expired(now): return (0, 0, 0)               # 断流：空包，停下不坐
        return (self.run * FULL, self.turn * FULL if now < self.turn_until else 0, B if now < self.tap_until else 0)


def samples(base):
    """取样函数：每次返回 (t, probs, top) 或 None。借 ai_confirm.live_samples 做「没开实时识别就用最新模型启动」。"""
    ai_confirm.live_samples(base)
    def one():
        last = ((json.load(urllib.request.urlopen(base + '/api/emg/state', timeout=.5)).get('wl8') or {}).get('live') or {}).get('last')
        return None if not last else (float(last['t']), dict(last.get('probs') or {}), last.get('top'))
    return one


def packet(seq, ly, rx, buttons):
    t_ms = int(time.monotonic() * 1000) % 2**32
    return b'DKPD' + struct.pack('<BBII6hH', 1, 0, seq, t_ms, 0, ly, rx, 0, 0, 0, buttons)


def run(sample, duck, seconds=None, say=print):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.IPPROTO_IP, socket.IP_TOS, 0xB8)    # 官方建议 DSCP EF
    b, seq, sending, dead, failing, end = Bridge(), random.getrandbits(32), False, False, False, seconds and time.monotonic() + seconds
    while not end or time.monotonic() < end:
        tick = time.monotonic()
        try: smp = sample()
        except (OSError, ValueError, http.client.HTTPException): smp = None   # 服务取不到 / 回包坏 / 连接半截断 = 没新样本，超时自然断流；格式变了的 KeyError 照样崩出来
        now = time.monotonic()                               # 取样可能卡住：用取样之后的时间判断断流
        was, dead = dead, sending and b.expired(now)
        if dead and not was: say('手环断流，鸭子停下待命')
        if (g := b.feed(smp, now)): say(NAMES[g])
        p = b.pad(now)
        if p is not None and not sending: sending = True; say('手环有数据，开始发包')
        if p is not None:
            seq = (seq + 1) % 2**32
            try: s.sendto(packet(seq, *p), duck); failing = False
            except OSError as e:                             # Wi-Fi 抖一下不退出；鸭子那边收不到包自己会停
                if not failing: failing = True; say(f'发包失败：{e}')
        time.sleep(max(0., 1 / HZ - (time.monotonic() - tick)))


def check():
    import threading
    import gesture_sim
    # 1. 状态机：真服务 100 ms 一个样本
    b, t = Bridge(), 0.
    def step(probs, n=1, top=None):
        nonlocal t
        fired = []
        for _ in range(n): t += .1; fired.append(b.feed((t, probs, top or max(probs, key=probs.get)), t))
        return [f for f in fired if f]
    P = gesture_sim.PROBS
    rest, up = P['rest'], P['up']
    assert b.pad(0.) is None, '没样本不该发包'
    assert step(rest, 5) == [] and b.pad(t) == (0, 0, 0)
    assert step(up, 5, top='ai_rest') == [], '服务端识别门改回放松就不算，哪怕 probs 很高'
    assert step(rest, 3) + step(up, 2) == [] and b.run == 0, '两帧不触发'
    assert step(rest, 1) + step(up, 1) + step(rest, 2) + step(up, 1) + step(rest, 2) + step(up, 1) == [], '不连续的尖峰不累计'
    step(rest, 3)
    assert step(up, 20) == ['ai_up'] and b.pad(t)[0] == FULL, '按住只触发一次'
    assert step({'ai_up': .7, 'ai_rest': .3}, 1) + step(up, 5) == [], '按住时掉一帧不重触发'
    assert step({'ai_up': .7, 'ai_rest': .3}, 5) == [], '低于门槛不算'
    assert step(P['right'], 3) == ['ai_right'] and b.pad(t)[:2] == (FULL, FULL)
    step(rest, 11); assert b.pad(t) == (FULL, 0, 0), '转 1 s 后回直行'
    assert step(P['summon'], 3) == ['ai_summon'] and b.pad(t)[2] == 2, '唤起 = B（bit 1，鞠躬），不是 A / Start'
    step(rest, 2); assert b.pad(t)[2] == 0, 'B 要松开'
    step(rest, 3); step(up, 3); assert step(P['summon'], 3) == ['ai_summon'] and b.pad(t)[:2] == (0, 0), '走着唤起：先停再鞠躬'
    assert step(P['down'], 3) == ['ai_down'] and b.pad(t) == (0, 0, 0)
    assert b.feed((t - 1, up, 'ai_up'), t + .01) is None, '旧样本不算'
    step(rest, 3); step(up, 3); step(rest, 3); assert b.run == 1
    assert b.pad(t + STALE_S + .01) == (0, 0, 0), '断流发空包：停下，不停发（停发 1 s netpadd 会让鸭子坐下）'
    step(rest, 1); assert b.pad(t) == (0, 0, 0), '数据回来不自己接着走'
    step(up, 3); t += 1.0; step(up, 1); assert b.pad(t) == (0, 0, 0), '卡顿后马上来新样本也算断过流'
    # 2. 收包工具：本机假 netpadd
    def listen(secs, sample, said):
        rx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); rx.bind(('127.0.0.1', 0)); rx.settimeout(1.5)
        threading.Thread(target=run, args=(sample, rx.getsockname(), secs, said.append), daemon=True).start()
        got = []
        try:
            while True:
                d = rx.recv(64); assert len(d) == 28 and d[:4] == b'DKPD'
                got.append((time.monotonic(),) + struct.unpack('<BBII6hH', d[4:]))
        except socket.timeout: return got
    # 2a. gesture_sim → 桥 → 假 netpadd
    sim = gesture_sim.Sim(); httpd, base = gesture_sim.serve(sim)
    try:
        threading.Timer(.4, sim.press, ('up',)).start(); threading.Timer(1.8, sim.press, ('left',)).start()
        got = listen(3.0, samples(base), [])
    finally: httpd.shutdown()
    pads = [(g[6], g[7], g[10]) for g in got]                # (ly, rx, buttons)
    assert 75 <= len(got) <= 95, f'3 s 应发约 90 包，实际 {len(got)}'
    assert all(g[1:3] == (1, 0) for g in got) and len({g[4] for g in got}) > 10, 'version 1、flags 0、t_ms 走动'
    assert all((b[3] - a[3]) % 2**32 == 1 for a, b in zip(got, got[1:])), 'seq 要逐包加 1'
    assert pads[0] == (0, 0, 0) and (FULL, 0, 0) in pads and (FULL, -FULL, 0) in pads, set(pads)
    # 2b. 采集服务卡 1 s：要报断流，恢复后不接着走
    calls = [0]
    def stuck():
        calls[0] += 1
        if calls[0] == 30: time.sleep(1.0)
        return (time.monotonic(), up, 'ai_up')
    said2 = []; got2 = listen(2.5, stuck, said2)
    gap = max(range(1, len(got2)), key=lambda i: got2[i][0] - got2[i - 1][0])
    assert got2[gap][0] - got2[gap - 1][0] > .9 and got2[gap - 1][6] == FULL, '卡之前在走'
    assert all(g[6] == 0 for g in got2[gap:]), '卡完不能接着走'
    assert '手环断流，鸭子停下待命' in said2, said2
    print(f'duck_bridge check passed: 状态机 21 项；gesture_sim → 桥 → 假 netpadd 收 {len(got)} 包，上滑前进、左滑左转、seq 连续；采集服务卡 1 s 报断流且不接着走')


if __name__ == '__main__':
    if '--check' in sys.argv: check(); sys.exit()
    host, _, port = (sys.argv[sys.argv.index('--duck') + 1] if '--duck' in sys.argv else '127.0.0.1:4210').rpartition(':')
    duck = socket.getaddrinfo(host, int(port), socket.AF_INET, socket.SOCK_DGRAM)[0][4]   # duck.local 只解析一次，免得 mDNS 拖慢 30 Hz
    base = ai_confirm.find_service()
    if not base: sys.exit('找不到采集服务：先开 OpenEMG App 的实时识别，或跑 host/gesture_sim.py')
    print(f'手势来源 {base} → 鸭子 {duck[0]}:{duck[1]}。上滑走、下滑停、左右滑转、唤起鞠躬；Ctrl-C 退出')
    try: run(samples(base), duck)
    except KeyboardInterrupt: pass

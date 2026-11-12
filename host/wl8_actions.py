"""手势 → 系统鼠标的执行端：App「用手势」页识别到一次动作后发 POST /api/emg/wl8/action，这里真的点 / 挪鼠标。
只认四个动作（左键单击、右键单击、相对移动、滚动），移动距离夹在 ±MAX_STEP 像素内、滚动夹在 ±MAX_LINES 行；两次动作至少隔 COOLDOWN_S，
防止识别抖动连点。识别与「一次动作只触发一次」在 App 端（app/v3/emg8/gesture-actions.ts），这里不重复判断。
Run: python3 wl8_actions.py --check   # 不发真鼠标，用记录模式自检
"""
import threading
import time

import wl8_cursor

ACTIONS = ('left_click', 'right_click', 'move', 'scroll')
CONTROL = ('pause', 'resume')     # AI 确认钩子用：等确认期间手势只归 AI（ai_confirm.py），最多暂停 MAX_PAUSE_S
MAX_PAUSE_S = 30
MAX_STEP = 400          # 像素；一次滑动最多挪这么远
MAX_LINES = 10          # 行；一次滚动最多翻这么多（2026-10-10 Mako 定：拇指上/下/左合成一类「拇指滑动」= 滚动）
COOLDOWN_S = .25        # 两次动作的最小间隔


class Actions:
    def __init__(self, enable=True, clock=time.monotonic):
        self.enable, self.clock, self.lock = enable, clock, threading.Lock()
        self.mouse, self.last, self.done, self.paused_until = None, -1e9, [], -1e9

    def do(self, body):
        a = body.get('action')
        if a in CONTROL:
            with self.lock:
                self.paused_until = self.clock() + min(MAX_PAUSE_S, max(0., float(body.get('seconds', 0)))) if a == 'pause' else -1e9
            return {'ok': True, 'action': a}
        if a not in ACTIONS: raise ValueError(f'未知动作 {a}')
        deliver = body.get('deliver', 'here')
        if deliver not in ('here', 'app'): raise ValueError('deliver 只能是 here / app')
        lim = MAX_LINES if a == 'scroll' else MAX_STEP
        dx, dy = (max(-lim, min(lim, float(body.get(k, 0)))) for k in ('dx', 'dy'))
        with self.lock:
            now = self.clock()
            if now < self.paused_until: return {'ok': False, 'skipped': 'AI 确认中，手势鼠标暂停'}
            if now - self.last < COOLDOWN_S: return {'ok': False, 'skipped': '太快，冷却中'}
            # PrintThings 已在自己的进程里发了鼠标事件（辅助功能权限挂在 App 上）。这里只记冷却，不再走 Quartz。
            if deliver == 'app':
                self.last = now; self.done.append(a); del self.done[:-50]
                return {'ok': True, 'action': a, 'deliver': 'app'}
            if self.mouse is None: self.mouse = wl8_cursor.Mouse(self.enable)    # 没有辅助功能权限会在这里抛 PermissionError
            if a in ('move', 'scroll'): self.mouse.act(a, dx, dy)
            else: self.mouse.act('click' if a == 'left_click' else 'right_click')
            self.last = now; self.done.append(a); del self.done[:-50]
            return {'ok': True, 'action': a}


class AiPending:
    """AI 确认钩子（ai_confirm.py）当前这一次请求，App「AI 授权」卡读它。只存内存；只会是白名单里的低风险命令。
    时间用 time.time()（同一台机器上 App 拿它算倒计时）。钩子没回报结果就按截止后 5 s 判超时拒绝。"""
    def __init__(self, clock=time.time):
        self.clock, self.lock, self.cur = clock, threading.Lock(), {'state': 'idle', 'seq': 0}

    def update(self, body):
        a = body.get('action')
        with self.lock:
            if a == 'pending':
                t, timeout = self.clock(), min(60., max(1., float(body.get('timeout', 20))))
                self.cur = {'state': 'pending', 'seq': self.cur['seq'] + 1, 'cmd': str(body.get('cmd', ''))[:200], 'started': t, 'deadline': t + timeout}
            elif a == 'done':
                if body.get('decision') not in ('allow', 'deny'): raise ValueError('decision 只能是 allow / deny')
                if self.cur['state'] != 'pending': raise ValueError('没有待确认的请求')
                self.cur = dict(self.cur, state='done', decision=body['decision'], reason=str(body.get('reason', ''))[:80],
                                ms=int(max(0, float(body.get('ms', 0)))), ended=self.clock())
            else: raise ValueError(f'未知 AI 状态 {a}')
            return self.state()

    def state(self):
        c = dict(self.cur)
        if c['state'] == 'pending' and self.clock() > c['deadline'] + 5:
            c.update(state='done', decision='deny', reason='钩子没回报结果，按超时拒绝', ms=None, ended=c['deadline'])
        return c


def check():
    t = [0.]
    s = Actions(enable=False, clock=lambda: t[0])
    assert s.do({'action': 'left_click'}) == {'ok': True, 'action': 'left_click'}
    assert s.do({'action': 'right_click'})['skipped'], '冷却期内第二次必须跳过'
    t[0] += COOLDOWN_S; assert s.do({'action': 'right_click'})['ok']
    t[0] += COOLDOWN_S; s.do({'action': 'move', 'dx': 9999, 'dy': -30})
    assert s.mouse.log[-1] == ('move', MAX_STEP, -30), s.mouse.log[-1]
    assert s.mouse.log[:2] == ['click', 'right_click'], s.mouse.log
    t[0] += COOLDOWN_S; assert s.do({'action': 'scroll', 'dy': 3}) == {'ok': True, 'action': 'scroll'}
    assert s.mouse.log[-1] == ('scroll', 0, 3), s.mouse.log[-1]
    t[0] += COOLDOWN_S; s.do({'action': 'scroll', 'dy': 999}); assert s.mouse.log[-1] == ('scroll', 0, MAX_LINES), '滚动行数没夹住'
    t[0] += COOLDOWN_S; s.do({'action': 'pause', 'seconds': 999})
    assert s.do({'action': 'left_click'})['skipped'].startswith('AI'), '暂停期间还在点鼠标'
    t[0] += MAX_PAUSE_S + .01; assert s.do({'action': 'left_click'})['ok'], '暂停最多 30 秒，过了要自动恢复'
    t[0] += COOLDOWN_S; s.do({'action': 'pause', 'seconds': 10}); s.do({'action': 'resume'}); assert s.do({'action': 'right_click'})['ok'], 'resume 后要恢复'
    t[0] += COOLDOWN_S; n = len(s.mouse.log)
    assert s.do({'action': 'move', 'dx': 12, 'dy': -3, 'deliver': 'app'}) == {'ok': True, 'action': 'move', 'deliver': 'app'}
    assert len(s.mouse.log) == n, 'App 自己发事件时采集服务不能再发一次'
    fresh = Actions(enable=True, clock=lambda: t[0])
    t[0] += COOLDOWN_S
    assert fresh.do({'action': 'left_click', 'deliver': 'app'})['deliver'] == 'app' and fresh.mouse is None, 'deliver=app 不能去加载 Quartz'
    try: fresh.do({'action': 'move', 'deliver': 'remote'})
    except ValueError: pass
    else: raise AssertionError('必须拒绝未知 deliver')
    for bad in ({'action': 'key'}, {}, {'action': 'move', 'dx': 'x'}):
        try: s.do(bad)
        except ValueError: pass
        else: raise AssertionError(f'必须拒绝 {bad}')
    t2 = [100.]; ai = AiPending(clock=lambda: t2[0])
    assert ai.state() == {'state': 'idle', 'seq': 0}
    p = ai.update({'action': 'pending', 'cmd': 'npm test' + 'x' * 500, 'timeout': 20}); assert p['state'] == 'pending' and len(p['cmd']) == 200 and p['deadline'] == 120
    t2[0] = 100.4; d = ai.update({'action': 'done', 'decision': 'allow', 'reason': '手环', 'ms': 410}); assert (d['decision'], d['ms']) == ('allow', 410)
    for bad in ({'action': 'done', 'decision': 'allow'}, {'action': 'done', 'decision': 'maybe'}, {'action': 'go'}):
        try: ai.update(bad)
        except ValueError: pass
        else: raise AssertionError(f'必须拒绝 {bad}')
    ai.update({'action': 'pending', 'cmd': 'ls', 'timeout': 20}); t2[0] += 26; s = ai.state()
    assert s['state'] == 'done' and s['decision'] == 'deny' and s['seq'] == 2, '钩子没回报，截止后要判超时拒绝'
    print('PASS: 只认四个动作、冷却防连点、移动距离夹在 ±%d、滚动夹在 ±%d 行、AI 确认时暂停（最长 %d s、可恢复）、非法动作拒绝（记录模式，不动真鼠标）；AI 待确认：截断命令、结果只认 allow/deny、没回报按超时拒绝' % (MAX_STEP, MAX_LINES, MAX_PAUSE_S))


if __name__ == '__main__':
    check()

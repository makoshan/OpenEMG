"""规则引擎：把实时识别结果 {'probs':{类:p}, 'top':类, 't':s} 变成事件。

规则：{'id','label','threshold':0.8,'hold_ms':300,'cooldown_ms':1000,'action':{'type':'key'|'osc'|'log',...}}
- 概率 ≥ threshold 连续 hold_ms 才触发；触发后 cooldown_ms 内不重复；掉到阈值下重新计时。
- 引擎只产生事件，执行动作的是订阅者（SSE / 桌面端），这里不发键盘不发网络。
"""
import time

FIELDS = ('id', 'label', 'threshold', 'hold_ms', 'cooldown_ms', 'action')


def validate(rule):
    r = dict(rule)
    for k in ('id', 'label'):
        if not r.get(k):
            raise ValueError(f'规则缺 {k}')
    r['threshold'] = float(r.get('threshold', .8))
    if not 0 < r['threshold'] <= 1:
        raise ValueError('threshold 必须在 (0,1]')
    r['hold_ms'] = int(r.get('hold_ms', 300))
    r['cooldown_ms'] = int(r.get('cooldown_ms', 1000))
    if r['hold_ms'] < 0 or r['cooldown_ms'] < 0:
        raise ValueError('hold_ms / cooldown_ms 不能为负')
    r['action'] = r.get('action') or {'type': 'log'}
    if r['action'].get('type') not in ('key', 'osc', 'log'):
        raise ValueError('action.type 必须是 key / osc / log')
    return {k: r[k] for k in FIELDS}


class Engine:
    def __init__(self, rules=()):
        self.rules = [validate(r) for r in rules]
        self.subscribers = []
        self._since = {}
        self._last_fire = {}
        self.events = []

    def set_rules(self, rules):
        self.rules = [validate(r) for r in rules]
        self._since.clear()
        self._last_fire.clear()

    def push(self, pred, now=None):
        """喂一条识别结果，返回本次触发的事件列表（同时广播给 subscribers）。"""
        now = pred.get('t', time.time()) if now is None else now
        probs = pred.get('probs') or {}
        fired = []
        for r in self.rules:
            p = float(probs.get(r['label'], 0))
            if p >= r['threshold']:
                t0 = self._since.setdefault(r['id'], now)
                held = (now - t0) * 1000
                last = self._last_fire.get(r['id'], -1e9)
                if held + 1e-6 >= r['hold_ms'] and (now - last) * 1000 + 1e-6 >= r['cooldown_ms']:
                    ev = {'rule_id': r['id'], 'label': r['label'], 'p': round(p, 3), 'held_ms': round(held), 't': now, 'action': r['action']}
                    self._last_fire[r['id']] = now
                    fired.append(ev)
            else:
                self._since.pop(r['id'], None)
        for ev in fired:
            self.events.append(ev)
            for cb in list(self.subscribers):
                try:
                    cb(ev)
                except Exception:
                    pass
        self.events = self.events[-200:]
        return fired

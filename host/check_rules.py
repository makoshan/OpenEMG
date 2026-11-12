"""规则引擎门禁（附录 G）：阈值 + 保持时间才触发；低于保持时间不触发；冷却期内不重复；
掉到阈值下重新计时；订阅者收到事件；坏规则必失败。"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from plugins import rules


def feed(eng, label, p, t_from, t_to, step=.1):
    out = []
    for i in range(int(round((t_to - t_from) / step))):
        out += eng.push({'probs': {label: p, 'rest': 1 - p}, 'top': label}, now=round(t_from + i * step, 3))
    return out


def main():
    eng = rules.Engine([{'id': 'r1', 'label': 'fist', 'threshold': .8, 'hold_ms': 300, 'cooldown_ms': 1000, 'action': {'type': 'key', 'key': 'space'}}])
    got = []
    eng.subscribers.append(got.append)
    # 0.0–0.2 s 高概率（200 ms < 300 ms 保持）→ 不触发
    assert feed(eng, 'fist', .9, 0, .2) == [] and not got
    # 掉下去再上来：0.3 s 低，0.4–1.0 s 高 → 在 0.7 s 触发一次（0.4 开始计时 + 300 ms）
    feed(eng, 'fist', .1, .2, .4)
    ev = feed(eng, 'fist', .95, .4, 1.0)
    assert len(ev) == 1 and abs(ev[0]['t'] - .7) < 1e-6 and ev[0]['action']['key'] == 'space' and ev[0]['held_ms'] >= 300, ev
    assert got == ev
    # 继续保持到 1.6 s：冷却 1000 ms 内不重复；1.7 s 再触发一次
    ev2 = feed(eng, 'fist', .95, 1.0, 1.8)
    assert len(ev2) == 1 and abs(ev2[0]['t'] - 1.7) < 1e-6, ev2
    print(f'  保持 200 ms 不触发；保持 300 ms 在 t={ev[0]["t"]} 触发；冷却 1 s 后 t={ev2[0]["t"]} 再触发')
    # 阈值边界：p=0.8 算到（≥）
    eng2 = rules.Engine([{'id': 'r', 'label': 'pinch', 'threshold': .8, 'hold_ms': 0, 'cooldown_ms': 0}])
    assert len(feed(eng2, 'pinch', .8, 0, .1)) == 1 and len(feed(eng2, 'pinch', .79, .1, .2)) == 0
    print('  阈值 ≥ 判定正确；hold_ms=0 立即触发')
    assert len(eng.events) == 2
    # 必失败
    for bad, why in (({'label': 'fist'}, '缺 id'), ({'id': 'x', 'label': 'fist', 'threshold': 1.5}, '阈值 >1'),
                     ({'id': 'x', 'label': 'fist', 'hold_ms': -1}, '负保持'), ({'id': 'x', 'label': 'fist', 'action': {'type': 'rm -rf'}}, '未知动作')):
        try:
            rules.validate(bad)
            raise AssertionError(f'{why} 通过了')
        except ValueError as e:
            print(f'  红 ✓ {why}: {e}')
    print('check_rules: 阈值 / 保持 / 冷却 / 重计时 / 订阅 通过，4 条必失败全红')


if __name__ == '__main__':
    main()

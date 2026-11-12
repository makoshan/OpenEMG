"""一次佩戴的真机测试，一条命令跑完：查接触 → 确认键校准 → 同意 / 拒绝各 3 次 → 日常动作误触 → 写证据。

对应 项目设计规范 第 3 节第 2 条（五类手势校准仍在 App 里做，不在本脚本）。
  1. 找 App 起的采集服务（端口随机，复用 ai_confirm.find_service）。
  2. 调 host/ai_confirm_calibrate.py 做本次佩戴校准；它自带接触检查（放松段 > 5 mV 尖峰超过 1% 拒存）。失败就停，不往下测。
  3. 同意 / 拒绝各 3 次，顺序打乱，语音先说这次做哪个，再走和钩子一模一样的流程（念命令 → 等手势）。
     判定：6 次全对才过；「该拒绝却放行」记危险错误，一次就不过。
  4. 误触：静止 / 转前臂 / 打字 / 打完字马上指向 / 握鼠标偶尔张手，各 2 分钟。期间暂停手势鼠标，
     用和钩子同一条规则（ai_confirm.APPROVE：食指概率 ≥ 0.85 连续 0.35 s）数「同意」被触发几次。过线：≤ 1 次 / 10 分钟（拟定）。
  5. 证据写进 evidence/<日期>-wear-session-<时分>.md / .json；只存次数和判定，不存原始肌电。
Run: python3 host/wear_session.py [--short]     # --short：误触每段 10 秒，只试流程
     python3 host/wear_session.py --check
"""
import argparse
import io
import os
import json
import random
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import ai_confirm as ac                                                          # noqa: E402

PHASES = [('静止', '手放着不动'), ('转前臂', '随便转前臂，不要捏'), ('打字', '正常打字'),
          ('打字后指向', '打一句话，再转前臂指一下，重复'), ('握鼠标', '握着鼠标正常用，偶尔张开手')]
MISFIRE_PER_10MIN = 1


def approve_events(samples):
    """数「同意」被触发了几次：和钩子同一条规则。一直按着每满 WAIT_S（20 s）再算一次：
    钩子每条命令都重新等，误识别一直在，期间来的每条命令都会被放行，只算一次会少算。"""
    lab, th, need = ac.APPROVE
    n, start, last = 0, None, None
    for t, probs in samples:
        if max((v for k, v in probs.items() if k.endswith(lab)), default=0) >= th:
            start = t if start is None else start
            if t - start >= need and (last is None or t - last >= ac.WAIT_S): n += 1; last = t
        else:
            start, last = None, None
    return n


def max_gap(samples, t0, t1):
    """这段里最长多久没有新识别结果（含开头和结尾）。手环掉线时计数是 0，不能当成没误触。"""
    ts = [t0] + [t for t, _ in samples] + [t1]
    return max(b - a for a, b in zip(ts, ts[1:]))


def score_trials(trials):
    """trials：[(期望 'allow'/'deny', 实际 'allow'/'deny'/'none')]。返回 (过没过, 危险错误次数)。危险 = 期望拒绝却放行。
    超时、没数据得到的拒绝不算识别出了中指，调用方先换成 'none'（见 gesture_of）。"""
    danger = sum(1 for want, got in trials if want == 'deny' and got == 'allow')
    return all(want == got for want, got in trials) and danger == 0, danger


def stale_reason(gaps):
    """任一段断数据超过 STALE_S（和钩子同一条线）就判阻塞：0 次可能只是没收到。"""
    stale = [k for k, g in gaps.items() if g > ac.STALE_S]
    return f'误触段手环断数据超过 {ac.STALE_S:.0f} 秒：{"、".join(stale)}，次数不可信' if stale else None


def gesture_of(decision, reason):
    """只有原因是手势本身才算认出来了；钩子在超时 / 没数据时也返回 deny。"""
    return decision if ('食指' in reason and decision == 'allow') or ('中指' in reason and decision == 'deny') else 'none'


def misfire_ok(count, minutes):
    return count <= MISFIRE_PER_10MIN * minutes / 10


def run(short=False):
    out = {'started': time.strftime('%F %T'), 'short': short}
    base = ac.find_service()
    if not base: sys.exit('没找到采集服务：先打开 PrintThings，进肌电手势页')
    r = subprocess.run([sys.executable, str(HERE / 'ai_confirm_calibrate.py')], capture_output=True, text=True,
                       env={**os.environ, 'YUANLI_SERVICE': base})                 # 校准用同一个服务；不存它最后打的 /live 返回（可能带本机路径）
    lines = (r.stdout + r.stderr).strip().splitlines()
    out['calibrate'] = {'exit': r.returncode, 'tail': [l for l in lines if l.startswith('按整次按住留一法')] + (lines[-1:] if r.returncode else [])}
    if r.returncode: return finish(out, '校准没过，见 calibrate.tail')
    sample = ac.live_samples(base)
    order = ['allow'] * 3 + ['deny'] * 3; random.Random(int(time.time())).shuffle(order)
    trials = []
    for k, want in enumerate(order, 1):
        ac.say(f'第 {k} 次，等它念完再做：{"同意，食指碰拇指" if want == "allow" else "拒绝，中指碰拇指"}'); time.sleep(.5)
        buf = io.StringIO(); t0 = time.time()
        ac.main(io.StringIO(json.dumps({'tool_name': 'Bash', 'tool_input': {'command': 'npm test'}})), buf, sample, base, on=True)
        h = json.loads(buf.getvalue())['hookSpecificOutput'] if buf.getvalue() else {}
        got = gesture_of(h.get('permissionDecision', ''), h.get('permissionDecisionReason', ''))
        trials.append((want, got)); out.setdefault('trials', []).append({'want': want, 'got': got, 'reason': h.get('permissionDecisionReason'), 's': round(time.time() - t0, 1)})
        time.sleep(2)
    out['trials_pass'], out['danger'] = score_trials(trials)
    secs = 10 if short else 120; counts, gaps = {}, {}
    try:
        for name, cue in PHASES:
            ac.hold_mouse(base, 'pause'); last_pause = time.time()                       # 念口令前先暂停：段间换姿势也不能点鼠标
            ac.say(f'{name}：{cue}'); time.sleep(1.5)                                    # 续期从发暂停算起：口令最长约 5 s，不能从 t0 算
            seen, t0 = [], time.time()
            while time.time() < t0 + secs:
                if time.time() - last_pause > 20: ac.hold_mouse(base, 'pause'); last_pause = time.time()   # 暂停 25 s，每 20 s 续一次
                s = sample()
                if s and (not seen or s[0] > seen[-1][0]): seen.append((time.time(), s[1]))   # 用本机收到的时间算断档
                time.sleep(ac.POLL_S)
            counts[name], gaps[name] = approve_events(seen), round(max_gap(seen, t0, time.time()), 1); ac.say('停'); time.sleep(1)
    finally: ac.hold_mouse(base, 'resume')
    total, minutes = sum(counts.values()), len(PHASES) * secs / 60
    out['misfire'] = {'counts': counts, 'max_gap_s': gaps, 'total': total, 'minutes': minutes, 'pass': misfire_ok(total, minutes)}
    return finish(out, stale_reason(gaps))


def finish(out, stopped):
    out['stopped'] = stopped
    passed = not stopped and out.get('trials_pass') and out.get('misfire', {}).get('pass')
    out['verdict'] = '已实测通过' if passed else ('阻塞：' + stopped if stopped else '已实测，未过线')
    stamp = time.strftime('%Y-%m-%d'); hm = time.strftime('%H%M'); ev = HERE.parent / 'evidence'
    ev.mkdir(exist_ok=True); (ev / f'{stamp}-wear-session-{hm}.json').write_text(json.dumps(out, ensure_ascii=False, indent=1))
    (ev / f'{stamp}-wear-session-{hm}.md').write_text(report(out))
    ac.say('测试结束'); print(report(out)); return out


def report(out):
    L = [f'# 佩戴测试 {out["started"]}', '', f'状态：**{out["verdict"]}**（脚本 `host/wear_session.py`{"，--short 只试流程" if out.get("short") else ""}）', '']
    if 'calibrate' in out: L.append(f'- 校准：退出 {out["calibrate"]["exit"]}，{out["calibrate"]["tail"]}')
    if 'trials' in out: L.append(f'- 同意 / 拒绝：{sum(t["want"] == t["got"] for t in out["trials"])} / {len(out["trials"])} 对，危险错误 {out.get("danger", "?")} 次（none = 超时或没数据，没认出手势）；' + '、'.join(f'{t["want"]}→{t["got"]}' for t in out['trials']))
    if 'misfire' in out: L.append(f'- 误触「同意」：{out["misfire"]["total"]} 次 / {out["misfire"]["minutes"]:.0f} 分钟（线 ≤ 1 次 / 10 分钟）；{out["misfire"]["counts"]}；最长断档 s {out["misfire"]["max_gap_s"]}')
    if out.get('stopped'): L.append(f'- 停在：{out["stopped"]}')
    return '\n'.join(L) + '\n'


def check():
    P = lambda i: {'meta_index': i, 'meta_rest': 1 - i}
    seq = lambda vals: [(k * .05, P(v)) for k, v in enumerate(vals)]
    assert approve_events(seq([0] * 10 + [.9] * 10 + [0] * 10)) == 1
    assert approve_events(seq([.9] * 80)) == 1, '按住 4 秒被算成了多次'
    assert approve_events(seq([.9] * 1200)) == 3, '按住 60 秒只算了一次（钩子期间每条命令都会放行）'
    assert max_gap([], 0, 120) == 120 and max_gap([(1, {}), (2, {})], 0, 2.5) == 1, '断档没算出来'
    assert max_gap([(k * .05, {}) for k in range(200)], 0, 10) < ac.STALE_S
    assert stale_reason({'静止': .2, '打字': 120}) and '打字' in stale_reason({'静止': .2, '打字': 120}) and stale_reason({'静止': .2}) is None, '掉线没判阻塞'
    assert gesture_of('deny', '20 秒内没等到手势') == 'none' and gesture_of('deny', '手环没有数据（超过 3 秒没更新）') == 'none', '超时的拒绝被当成认出了中指'
    assert gesture_of('deny', '手环：中指碰拇指（拒绝）') == 'deny' and gesture_of('allow', '手环：食指碰拇指（同意）') == 'allow'
    assert score_trials([('deny', 'none')]) == (False, 0)
    assert approve_events(seq(([0] * 5 + [.9] * 10) * 3)) == 3
    assert approve_events(seq([.9, .9, 0] * 30)) == 0, '断断续续被算成了同意'
    assert approve_events(seq([.8] * 50)) == 0, '低于门槛被算成了同意'
    assert approve_events([(k * .05, {'mouse_index': .95}) for k in range(10)]) == 1, '鼠标组的食指没算'
    assert score_trials([('allow', 'allow'), ('deny', 'deny')]) == (True, 0)
    assert score_trials([('allow', 'allow'), ('deny', 'allow')]) == (False, 1), '拒绝被放行没记成危险'
    assert score_trials([('allow', 'deny'), ('deny', 'deny')]) == (False, 0)
    assert misfire_ok(1, 10) and not misfire_ok(2, 10) and not misfire_ok(1, 5)
    rep = report({'started': 'x', 'verdict': '已实测，未过线', 'trials': [{'want': 'deny', 'got': 'allow'}], 'danger': 1,
                  'misfire': {'total': 2, 'minutes': 10, 'counts': {}, 'max_gap_s': {}}})
    assert '危险错误 1 次' in rep and '2 次 / 10 分钟' in rep, rep
    print('wear_session check passed: 误触计数（按住每 20 秒算一次、断续和低于门槛不算、鼠标组食指算）、断档、超时拒绝不算认出、'
          '试验评分（拒绝被放行 = 危险）、误触线、报告字段')


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--check', action='store_true'); ap.add_argument('--short', action='store_true')
    a = ap.parse_args()
    check() if a.check else run(a.short)

"""M3 真手环验收：语音念口令 → 你做手势 → duck_bridge 照常驱动仿真鸭，同时记下桥触发了什么，最后算分。
判据：6 类各 REPS 次（放松也是一类：口令窗口里不触发才算对），然后放松 2 分钟误触发 0 次。
只记事件（类别、时间），不存原始肌电。
用法：python3 trial.py [--reps 20] [--rest-s 120] [--duck 127.0.0.1:4210]
     python3 trial.py --dry --reps 2 --rest-s 5   # 用 gesture_sim --api 自动按，核对算分
"""
import json, random, subprocess, sys, threading, time, urllib.request
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[2] / 'host'   # 原力手环/host
sys.path.insert(0, str(REPO))
import ai_confirm, duck_bridge
from calibration_voice import NAMES as CUE

LABELS = ['ai_rest', 'ai_summon', 'ai_up', 'ai_down', 'ai_left', 'ai_right']
WINDOW_S, GAP_S = 3.0, 2.0          # 口令念完后 3 s 内的第一个事件算这次的答案；之后放松 2 s 再念下一个
arg = lambda k, d: type(d)(sys.argv[sys.argv.index(k) + 1]) if k in sys.argv else d
REPS, REST_S, DRY = arg('--reps', 20), arg('--rest-s', 120.0), '--dry' in sys.argv
host, _, port = arg('--duck', '127.0.0.1:4210').rpartition(':')
OUT = Path(f'./microduck/evidence/{time.strftime("%Y-%m-%d")}-m3-real-band/{"dry" if DRY else "run"}-{time.strftime("%H%M%S")}.json')

events, lock = [], threading.Lock()
def log(msg):                         # duck_bridge.run 的 say：把「上滑 → 前进」这类事件记成 (时间, 标签)
    g = next((k for k, v in duck_bridge.NAMES.items() if v == msg), None)
    with lock: events.append((time.monotonic(), g or msg))
    print(f'  [桥] {msg}', flush=True)


def speak(text):
    subprocess.run(['say', '-v', 'Tingting' if b'Tingting' in subprocess.run(['say', '-v', '?'], capture_output=True).stdout else 'Flo', text])


base = ai_confirm.find_service()
if not base: sys.exit('找不到采集服务：先开 OpenEMG App 的六类实时识别' + ('，或起 host/gesture_sim.py --api' if DRY else ''))
sample = duck_bridge.samples(base)
if not DRY:   # 实时识别没指定模型时用最新的；最新的若是结印四类，桥一次都不会触发、全判放松，所以开测前先拦住
    t0, s = time.monotonic(), None
    while not s and time.monotonic() - t0 < 5: s = sample(); time.sleep(.2)
    if not s or time.time() - s[0] > 1: sys.exit(f'实时识别没有新结果（{base}）：看手环有没有在出数据')   # 断流后 live.last 留着旧值，要看 t 新不新
    if set(LABELS) - set(s[1]): sys.exit(f'实时识别用的模型不是六类（当前类别 {sorted(s[1])}，服务 {base}）：先在 App 录「AI 选择 · 六类」并训练，再用它开实时识别')
bridge = threading.Thread(target=duck_bridge.run, args=(sample, (host, int(port))), kwargs={'say': log}, daemon=True); bridge.start()
press = lambda g: urllib.request.urlopen(urllib.request.Request(base + '/sim', data=json.dumps({'gesture': g}).encode(), method='POST'), timeout=2)

plan = LABELS * REPS; random.shuffle(plan)
trials, windows, completed = [], [], False
try:
    speak('开始测试，听口令做一次就放松'); time.sleep(GAP_S)
    for i, want in enumerate(plan, 1):
        print(f'{i}/{len(plan)} 口令：{CUE[want]}', flush=True)
        speak(CUE[want]); c = time.monotonic(); windows.append((c, c + WINDOW_S))
        if DRY and want != 'ai_rest':
            try: press(want.removeprefix('ai_'))
            except OSError: pass                 # 模拟器停了（断流反例）：照常往下走，看结果会不会作废
        time.sleep(WINDOW_S)
        with lock: got = [(t - c, g) for t, g in events if c <= t < c + WINDOW_S and g in duck_bridge.NAMES]
        trials.append({'want': want, 'got': got[0][1] if got else 'ai_rest', 'latency_s': round(got[0][0], 2) if got else None, 'extra': [g for _, g in got[1:]]})
        print(f'    → {trials[-1]["got"]}{"  ✓" if trials[-1]["got"] == want else "  ✗"}', flush=True)
        time.sleep(GAP_S)
        if not bridge.is_alive(): print('桥线程退出了，停止测试', flush=True); break
    r0 = time.monotonic(); speak(f'现在保持放松 {int(REST_S)} 秒'); time.sleep(max(0., REST_S - (time.monotonic() - r0))); r1 = time.monotonic()   # 播报那几秒也算放松
    speak('测试结束'); completed = bridge.is_alive() and len(trials) == len(plan)
except KeyboardInterrupt: r0 = r1 = None
with lock:
    rest_hits = [g for t, g in events if r0 and r0 <= t < r1 and g in duck_bridge.NAMES]
    drops = sum(1 for _, g in events if g.startswith('手环断流'))   # 中途断过流：之后的题都会被判成放松，整轮作废
    stray = [g for t, g in events if g in duck_bridge.NAMES and not (r0 and r0 <= t < r1) and not any(a <= t < b for a, b in windows)]   # 口令之间的空档里触发的

per = {l: f'{sum(t["got"] == l for t in trials if t["want"] == l)}/{sum(t["want"] == l for t in trials)}' for l in LABELS}
conf = Counter(f'{t["want"]}→{t["got"]}' for t in trials if t['got'] != t['want'])
lat = sorted(t['latency_s'] for t in trials if t['latency_s'] is not None and t['got'] == t['want'])
res = {'date': time.strftime('%Y-%m-%d %H:%M'), 'dry': DRY, 'valid': completed and not drops, 'completed': completed, 'dropouts': drops, 'reps': REPS, 'window_s': WINDOW_S, 'bridge': {'TH': duck_bridge.TH, 'N_FIRE': duck_bridge.N_FIRE},
       'accuracy': f'{sum(t["got"] == t["want"] for t in trials)}/{len(trials)}', 'per_class': per, 'confusions': dict(conf),
       'latency_median_s': lat[len(lat) // 2] if lat else None, 'extra_events': sum(len(t['extra']) for t in trials), 'stray_between_trials': stray,
       'rest': {'seconds': round(r1 - r0, 1) if r0 else None, 'false_triggers': len(rest_hits), 'which': rest_hits}, 'trials': trials}
OUT.parent.mkdir(parents=True, exist_ok=True); OUT.write_text(json.dumps(res, ensure_ascii=False, indent=2))
print(json.dumps({k: v for k, v in res.items() if k != 'trials'}, ensure_ascii=False, indent=1)); print('写入', OUT)

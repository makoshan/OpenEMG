"""手势模拟器：不戴手环也能演示和测试「手环当 AI 确认键」（host/ai_confirm.py）。
它假装成采集服务，只实现 ai_confirm 用到的接口：GET /api/emg/state 返回 rig.kind=wl8 和 wl8.live.last={t, probs, top}，POST 一律回 ok。
按 a = 食指碰拇指（同意），d = 中指碰拇指（拒绝），各按住 HOLD_S 秒；q 退出。
控鸭六类（host/duck_bridge.py 读）：e = 唤起，i / k / j / l = 上 / 下 / 左 / 右滑，概率键与真模型同名 ai_*。
运行期间把自己的地址写进 SERVICE_FILE，ai_confirm 找服务时优先用它；退出时删掉。以后换真手环，只是数据来源不同，钩子一行不改。
--api 额外开 POST /sim {"gesture": "allow"|"deny"|"summon"|"up"|"down"|"left"|"right"} 给自动测试用；默认不开，免得本机别的程序（包括 AI 自己）替你点同意。
Run: python3 host/gesture_sim.py          # 交互
     python3 host/gesture_sim.py --check  # 自检：起服务 → 模拟同意 / 拒绝 → 用 ai_confirm 的真实读取路径判定
"""
import json
import os
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

SERVICE_FILE = Path.home() / '.local/state/yuanli/service.url'
HOLD_S = 1.0                                   # 按一下 = 按住 1 秒；ai_confirm 同意要连续 0.35 s
PROBS = {'rest': {'meta_rest': .98, 'meta_index': .01, 'meta_middle': .01},
         'allow': {'meta_index': .95, 'meta_middle': .02, 'meta_rest': .03},
         'deny': {'meta_middle': .9, 'meta_index': .02, 'meta_rest': .08}}
AI = {'summon': '唤起', 'up': '上滑', 'down': '下滑', 'left': '左滑', 'right': '右滑'}   # 控鸭用；标签名同 app/src/web.tsx 的 LABELS
PROBS.update({g: {f'ai_{g}': .93, 'ai_rest': .07} for g in AI})
KEYS = {'a': ('allow', '食指碰拇指（同意）'), 'd': ('deny', '中指碰拇指（拒绝）'), 'e': ('summon', '唤起'),
        'i': ('up', '上滑'), 'k': ('down', '下滑'), 'j': ('left', '左滑'), 'l': ('right', '右滑')}


class Sim:
    def __init__(self, clock=time.time):
        self.clock, self.until, self.gesture = clock, 0., 'rest'

    def press(self, gesture):
        if gesture not in PROBS or gesture == 'rest': raise ValueError(gesture)
        self.gesture, self.until = gesture, self.clock() + HOLD_S

    def state(self):
        now = self.clock()
        g = self.gesture if now < self.until else 'rest'
        return {'rig': {'kind': 'wl8', 'simulated': True}, 'project': {'id': 'gesture-sim'},
                'wl8': {'live': {'last': {'t': now, 'probs': PROBS[g], 'top': max(PROBS[g], key=PROBS[g].get)}}}}   # top 同真服务（过识别门后的类别）


def serve(sim, api=False, port=0):
    class H(BaseHTTPRequestHandler):
        def log_message(self, *a): pass
        def reply(self, body):
            data = json.dumps(body).encode()
            self.send_response(200); self.send_header('Content-Type', 'application/json'); self.send_header('Content-Length', str(len(data)))
            self.end_headers(); self.wfile.write(data)
        def do_GET(self):
            if self.path.split('?')[0] == '/api/emg/state': self.reply(sim.state())
            else: self.send_error(404)
        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers.get('Content-Length') or 0)) or b'{}')
            if self.path == '/sim':
                if not api: return self.send_error(403)
                sim.press(body.get('gesture')); return self.reply({'ok': True})
            self.reply({'ok': True})                     # /api/emg/wl8/live、/action、/ai：模拟器不需要真做
    httpd = ThreadingHTTPServer(('127.0.0.1', port), H)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd, f'http://127.0.0.1:{httpd.server_address[1]}'


def interactive(api):
    import termios, tty
    sim = Sim(); httpd, base = serve(sim, api)
    SERVICE_FILE.parent.mkdir(parents=True, exist_ok=True); SERVICE_FILE.unlink(missing_ok=True)
    os.close(os.open(SERVICE_FILE, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)); SERVICE_FILE.write_text(base)   # ai_confirm 只认 0600
    print(f'手势模拟器在 {base}（已写入 {SERVICE_FILE}）。a = 同意，d = 拒绝；e = 唤起，i/k/j/l = 上/下/左/右滑；q = 退出')
    tty_in = sys.stdin.isatty()
    old = termios.tcgetattr(sys.stdin.fileno()) if tty_in else None
    try:
        if not tty_in: threading.Event().wait()                                 # 后台跑（自动测试配 --api）：等到被杀
        tty.setcbreak(sys.stdin.fileno())
        while (k := sys.stdin.read(1)) != 'q':
            if k in KEYS: sim.press(KEYS[k][0]); print(f'→ {KEYS[k][1]}', flush=True)
    except KeyboardInterrupt: pass
    finally:
        if old: termios.tcsetattr(sys.stdin.fileno(), termios.TCSADRAIN, old)
        httpd.shutdown()
        if SERVICE_FILE.exists() and SERVICE_FILE.read_text() == base: SERVICE_FILE.unlink()


def check():
    import urllib.request
    sys.path.insert(0, str(Path(__file__).parent))
    import ai_confirm
    sim = Sim(); httpd, base = serve(sim, api=True)
    try:
        st = json.load(urllib.request.urlopen(base + '/api/emg/state', timeout=2))
        assert st['rig']['kind'] == 'wl8' and st['wl8']['live']['last']['probs'] == PROBS['rest']
        for g in ('allow', 'deny'):
            sample = ai_confirm.live_samples(base)                   # ai_confirm 的真实读取路径
            threading.Timer(.3, lambda g=g: urllib.request.urlopen(urllib.request.Request(
                base + '/sim', data=json.dumps({'gesture': g}).encode(), method='POST'), timeout=2)).start()
            assert ai_confirm.wait_gesture(sample)[0] == g, g
        for g in AI:                                                # 控鸭六类：按下后最高的是同名 ai_ 标签
            sim.press(g); p = json.load(urllib.request.urlopen(base + '/api/emg/state', timeout=2))['wl8']['live']['last']['probs']
            assert max(p, key=p.get) == f'ai_{g}', (g, p)
        sim.until = 0
        _, closed = serve(Sim())
        try: urllib.request.urlopen(urllib.request.Request(closed + '/sim', data=b'{"gesture":"allow"}', method='POST'), timeout=2); raise AssertionError('没开 --api 也能远程点同意')
        except urllib.error.HTTPError as e: assert e.code == 403
    finally: httpd.shutdown()
    print('gesture_sim check passed: 状态接口、同意 / 拒绝经 ai_confirm 真实读取路径判定、控鸭五个手势、默认不开远程点击')


if __name__ == '__main__':
    import signal; signal.signal(signal.SIGTERM, lambda *a: (_ for _ in ()).throw(KeyboardInterrupt))   # kill 时也删地址文件
    if '--check' in sys.argv: check()
    else: interactive('--api' in sys.argv)

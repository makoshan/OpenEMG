"""连接状态门禁：空串口列表、口开着 1.5 秒没帧、喂一帧、数据流 503。

不打开真串口，不碰真设备。去掉 stream8 的 503 分支时，这里会拿到连接错误或非 503，而不是 code=no-receiver。
"""
import json
import os
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import wl8


class Hit:
    def __init__(self, device='/dev/cu.usbserial-TEST'):
        self.device, self.vid, self.pid = device, 0x10C4, 0xEA60


def free_port():
    s = socket.socket()
    s.bind(('127.0.0.1', 0))
    p = s.getsockname()[1]
    s.close()
    return p


def get(port, path, timeout=5):
    req = urllib.request.Request(f'http://127.0.0.1:{port}{path}')
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        raw = e.read()
        return e.code, (json.loads(raw.decode()) if raw else {})


class Server:
    def __init__(self, link):
        self.port = free_port()
        env = os.environ.copy()
        env['YUANLI_LINK'] = link
        self.proc = subprocess.Popen(
            [sys.executable, str(HERE / 'emg_web.py'), '--port', str(self.port), '--fake', '--wl8'],
            cwd=HERE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=env)
        self.lines = []
        self._t = threading.Thread(target=self._pump, daemon=True)
        self._t.start()
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            try:
                code, body = get(self.port, '/api/emg/state')
                if code == 200 and 'rig' in body:
                    self.state = body
                    return
            except (urllib.error.URLError, ConnectionError, OSError, json.JSONDecodeError):
                pass
            if self.proc.poll() is not None:
                raise AssertionError('服务退出：\n' + ''.join(self.lines[-30:]))
            time.sleep(0.1)
        raise AssertionError('服务未就绪：\n' + ''.join(self.lines[-30:]))

    def _pump(self):
        for ln in self.proc.stdout:
            self.lines.append(ln)

    def close(self):
        if self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(5)
            except subprocess.TimeoutExpired:
                self.proc.kill()


def rig_cases():
    try:
        wl8.find_port(ports=[])
    except wl8.NoReceiver:
        pass
    else:
        raise AssertionError('空串口列表居然找到了接收器')

    bare = wl8.Wl8Rig()
    bare._ports = lambda: []
    assert bare.status()['link'] == 'no-receiver', bare.status()
    assert bare.status()['port'] is None
    try:
        bare.subscribe()
    except wl8.NoReceiver:
        pass
    else:
        raise AssertionError('没接收器时 subscribe 应该失败')
    assert bare.subscribers == [], '失败的 subscribe 不能把队列留在订阅者里'

    plugged = wl8.Wl8Rig()
    plugged._ports = lambda: [Hit()]
    assert plugged.status()['link'] == 'waiting-band', plugged.status()

    opened = wl8.Wl8Rig()
    opened.conn = object()
    opened.device = Hit()
    opened.last_frame_at = time.monotonic() - 1.5
    assert opened.status()['link'] == 'waiting-band', opened.status()
    opened._feed(wl8._frame(wl8.EMG, 1, bytes(24)))
    assert opened.status()['link'] == 'streaming', '喂了一帧仍不是 streaming：时间戳没更新就会永远 waiting-band'
    opened.last_frame_at = time.monotonic() - 1.5
    assert opened.status()['link'] == 'waiting-band'

    fresh = wl8.Wl8Rig()                                   # 开口后 last_frame_at 是 None：第一帧记下 link_since（App 识别页据此提醒重新校准）
    fresh._ports = lambda: [Hit()]
    assert fresh.status()['link_since'] is None
    fresh._feed(wl8._frame(wl8.EMG, 1, bytes(24)))
    since = fresh.status()['link_since']
    assert since is not None and abs(since - time.time()) < 5, '开口后的第一帧要记下 link_since'
    fresh._feed(wl8._frame(wl8.EMG, 2, bytes(24)))
    assert fresh.status()['link_since'] == since, '连续出帧不能刷新 link_since'
    fresh.last_frame_wall = time.time() - wl8.REWEAR_GAP_S - 1   # 墙钟上隔了 31 秒（monotonic 不算：合盖睡眠时它不走）
    time.sleep(0.01)
    fresh._feed(wl8._frame(wl8.EMG, 3, bytes(24)))
    assert fresh.status()['link_since'] > since, '断流 ≥ REWEAR_GAP_S 后再出帧要刷新 link_since（可能摘下重戴）'

    opened._drop('读失败')
    opened._ports = lambda: []
    dropped = opened.status()
    assert dropped['link'] == 'dropped' and dropped['link_detail'] == '读失败', dropped
    assert dropped['banner'].startswith('断开：')
    opened._ports = lambda: [Hit()]
    assert opened.status()['link'] == 'waiting-band', '接收器回到列表里应离开 dropped'

    gone = wl8.FakeWl8Rig(link_mode='no-receiver')
    assert gone.status()['link'] == 'no-receiver' and gone.status()['port'] is None
    try:
        gone.subscribe()
    except wl8.NoReceiver:
        pass
    else:
        raise AssertionError('假手环无接收器模式仍订上了流')
    waiting = wl8.FakeWl8Rig(link_mode='waiting-band')
    assert waiting.status()['link'] == 'waiting-band'
    waiting.subscribe()
    assert waiting.status()['link'] == 'waiting-band', '等手环模式不能自己喂出帧'
    assert wl8.FakeWl8Rig().status()['link'] == 'streaming'


def http_cases():
    srv = Server('no-receiver')
    try:
        assert srv.state['rig']['link'] == 'no-receiver', srv.state['rig']
        for _ in range(2):
            code, body = get(srv.port, '/api/emg/stream8')
            assert code == 503 and body.get('code') == 'no-receiver', (code, body, ''.join(srv.lines[-10:]))
        legacy, legacy_body = get(srv.port, '/api/emg/stream')
        assert legacy == 503 and legacy_body.get('code') == 'no-receiver', (legacy, legacy_body)
    finally:
        srv.close()
    wait = Server('waiting-band')
    try:
        assert wait.state['rig']['link'] == 'waiting-band', wait.state['rig']
    finally:
        wait.close()


def main():
    rig_cases()
    http_cases()
    print('wl8 link：空口 no-receiver、1.5 秒没帧 waiting-band、喂帧 streaming、stream8/stream 两次 503')


if __name__ == '__main__':
    main()

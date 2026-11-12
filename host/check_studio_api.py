"""Studio 路由门禁（附录 B.6/G）：以子进程 `emg_web.py --device <id>` 起服务（覆盖命令行路径），
fake：扫描/选择/配置/状态 → 会话 → 定时段 + 连续段 + 标记 → 文件列表/区间读/导出 txt → 数据集 → 训练 → 冻结 → 统计 / EMG 分析 / 规则 / LSL；
SSE 收到 gate 与 train 事件。v12：不可录（403）。replay：别名 --replay 仍能起。--fake（Cheez 别名）：状态可读。
必失败：无头写入 403、选别的设备 409、采样率不在选项 400、文件越界 400、未知训练器 400、坏规则 400。"""
import json
import os
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import check_dataset
import device_desc as dd
import wl8


def free_port():
    s = socket.socket()
    s.bind(('127.0.0.1', 0))
    p = s.getsockname()[1]
    s.close()
    return p


def call(port, path, body=None, method=None, header=True):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(f'http://127.0.0.1:{port}{path}', data=data, method=method or ('POST' if body is not None else 'GET'),
                                 headers={'Content-Type': 'application/json', **({'X-Mako-Collector': '1'} if header else {})})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            raw = r.read()
            return r.status, (json.loads(raw) if 'json' in (r.getheader('Content-Type') or '') else raw)
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


class Server:
    def __init__(self, *args, env=None):
        self.port = free_port()
        self.proc = subprocess.Popen([sys.executable, str(HERE / 'emg_web.py'), '--port', str(self.port), *args], cwd=HERE,
                                     stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env={**os.environ, **(env or {})})
        self.lines = []
        threading.Thread(target=self._pump, daemon=True).start()
        # 进程活着就一直等到 120 秒：机器负载 100+ 时冷启动要 48 秒（2026-10-14 实测），固定 20 秒会误报；进程退了下面立刻报错
        deadline = time.monotonic() + 120
        while time.monotonic() < deadline:
            try:
                if call(self.port, '/api/device/state')[0] == 200:
                    return
            except (urllib.error.URLError, ConnectionError, OSError):
                pass
            if self.proc.poll() is not None:
                raise AssertionError('服务退出：\n' + ''.join(self.lines[-20:]))
            time.sleep(.1)
        self.proc.kill()                                # 超时时 __exit__ 不会跑，这里收掉，不留孤儿
        raise AssertionError('服务未就绪：\n' + ''.join(self.lines[-20:]))

    def _pump(self):
        for ln in self.proc.stdout:
            self.lines.append(ln)

    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.proc.terminate()
        try:
            self.proc.wait(5)
        except subprocess.TimeoutExpired:
            self.proc.kill()


def sse_collect(port, types, seconds):
    """开 stream8，收指定命名事件。"""
    got = []

    def run():
        req = urllib.request.Request(f'http://127.0.0.1:{port}/api/emg/stream8?project=')
        try:
            with urllib.request.urlopen(req, timeout=seconds + 5) as r:
                t0, ev = time.time(), None
                while time.time() - t0 < seconds:
                    ln = r.readline().decode().rstrip('\n')
                    if ln.startswith('event: '):
                        ev = ln[7:]
                    elif ln.startswith('data: ') and ev in types:
                        got.append((ev, json.loads(ln[6:])))
                        ev = None
                    elif ln == '':
                        ev = None
        except Exception as e:  # 服务关掉时读会断，正常
            got.append(('error', str(e)))
    th = threading.Thread(target=run, daemon=True)
    th.start()
    return got, th


def fake_flow(tmp):
    with Server('--device', 'fake', '--data', str(tmp)) as s:
        p = s.port
        assert 'device=fake' in ''.join(s.lines)
        # 设备
        c, scan = call(p, '/api/device/scan', {})
        assert c == 200 and {d['id'] for d in scan['devices']} >= {'fake', 'wl8', 'v12', 'cheez', 'replay'} and scan['current'] == 'fake'
        c, sel = call(p, '/api/device/select', {'id': 'fake'})
        assert c == 200 and sel['device']['id'] == 'fake'
        c, cfg = call(p, '/api/device/config')
        assert c == 200 and cfg['fs_Hz'] == 2000 and len(cfg['channels']) == 8
        c, cfg = call(p, '/api/device/config', {'channels': [{'index': 0, 'label': 'FCR'}]}, method='PUT')
        assert c == 200 and cfg['channels'][0]['label'] == 'FCR'
        c, st = call(p, '/api/device/state')
        assert c == 200 and st['device_id'] == 'fake' and st['capabilities']['record'] and st['session'] is None
        print(f'  fake: scan {len(scan["devices"])} 台 / select / config PUT / state={st["state"]}')
        # 会话 + 段
        c, r = call(p, '/api/session/start', {'subject': 'S01', 'donning': 1, 'hand': 'left', 'placement': '腕'})
        assert c == 200 and r['session']['donning'] == 1
        sse, th = sse_collect(p, ('gate', 'train', 'take', 'rule'), 20)
        time.sleep(.5)
        c, r = call(p, '/api/take/start', {'label': 'fist', 'seconds': 1})
        assert c == 200 and r['take']['seconds'] == 1
        c, r = call(p, '/api/take/mark', {'label': 'cue', 'source': 'ui'})
        assert c == 200 and 't_s' in r
        for _ in range(60):
            if not call(p, '/api/device/state')[1]['recording']:
                break
            time.sleep(.1)
        c, files = call(p, '/api/files/list')
        assert c == 200 and len(files['takes']) == 1 and files['takes'][0]['gate']['ok'] and files['takes'][0]['label'] == 'fist'
        f1 = files['takes'][0]['file']
        # 连续段 → 手动停
        c, r = call(p, '/api/take/start', {'label': 'rest'})
        assert c == 200 and r['take']['seconds'] is None
        time.sleep(1.3)
        c, r = call(p, '/api/take/stop', {})
        assert c == 200 and r['gate'] is not None and r['frames'] >= 2000, r
        # 必失败：会话里再开会话 / 停不存在的段
        assert call(p, '/api/session/start', {'subject': 'S01', 'donning': 2})[0] == 409
        assert call(p, '/api/take/stop', {})[0] == 409
        c, r = call(p, '/api/session/stop', {})
        assert c == 200 and len(r['takes']) == 2
        print(f'  会话：定时 1 s 段 + 连续段（{r["takes"][1]["seconds"]} s）→ 2 段入会话，gate 全 ok')
        # 文件
        c, o = call(p, f'/api/files/open?file={f1}&from=100&to=1100&decim=10')
        assert c == 200 and o['n'] == 100 and len(o['uv'][0]) == 8 and o['header']['x_yuanli']['take_label'] == 'fist' and o['events'][0][1] == 'cue'
        c, e = call(p, '/api/files/export_txt', {'file': f1})
        assert c == 200 and Path(e['path']).exists() and Path(e['path']).read_text().startswith('# OpenSignals Text File Format')
        assert call(p, '/api/files/open?file=../../etc/passwd')[0] == 400
        print(f'  files: open 区间抽稀 100 点 / export_txt → {Path(e["path"]).name} / 越界路径 400')
        # 多录几段凑数据集（直接写文件比走 HTTP 快）：3 会话 × 3 标签 × 5
        studio_root = Path(tmp) / 'studio'
        check_dataset.synth_project(studio_root, dd.load('fake'), sessions=3, per=5, seed=3)
        c, r = call(p, '/api/dataset/save', {'name': 'd1', 'label_map': {'rest': 'rest', 'pinch': 'pinch', 'fist': 'fist'}}, method='PUT')
        assert c == 200 and r['summary']['train']['rest'] >= 5, r
        c, r = call(p, '/api/dataset/validate', {'name': 'd1'})
        assert c == 200 and r['ok']
        c, r = call(p, '/api/dataset/list')
        assert c == 200 and r['datasets'][0]['name'] == 'd1'
        # 训练
        c, r = call(p, '/api/train/start', {'trainer': 'lda', 'dataset': 'd1', 'seed': 0})
        assert c == 200
        for _ in range(300):
            job = call(p, '/api/train/runs')[1]['job']
            if job['state'] in ('done', 'error'):
                break
            time.sleep(.1)
        assert job['state'] == 'done', job
        c, runs = call(p, '/api/train/runs')
        assert runs['runs'][0]['id'] == job['run_id'] and runs['production'] is None
        c, prod = call(p, '/api/train/freeze', {'run_id': job['run_id']})
        assert c == 200 and call(p, '/api/train/runs')[1]['production']['run_id'] == job['run_id']
        assert call(p, '/api/train/start', {'trainer': 'svm', 'dataset': 'd1'})[0] == 400
        print(f'  dataset d1 → train lda {job["metrics"]["validation"]["balanced_acc"] if job.get("metrics") and job["metrics"].get("validation") else job.get("metrics")} → freeze；未知训练器 400')
        # 插件
        c, stt = call(p, '/api/plugin/stats?window_s=1')
        assert c == 200 and len(stt['channels']) == 8 and stt['channels'][0]['label'] == 'FCR'
        c, an = call(p, '/api/plugin/emg_analysis', {'file': f1, 'params': {'threshold_pct': 20}})
        assert c == 200 and len(an['channels']) == 8 and Path(an['csv']).exists()
        c, r = call(p, '/api/rules', {'rules': [{'id': 'r1', 'label': 'fist', 'threshold': .8, 'hold_ms': 100}]}, method='PUT')
        assert c == 200 and r['rules'][0]['id'] == 'r1' and call(p, '/api/rules')[1]['rules'][0]['label'] == 'fist'
        assert call(p, '/api/rules', {'rules': [{'id': 'x', 'label': 'fist', 'threshold': 2}]}, method='PUT')[0] == 400
        c, l = call(p, '/api/lsl', {'enabled': True}, method='PUT')
        assert c == 200 and ('stream_name' in l or l['why'])
        assert call(p, '/api/lsl', {'enabled': False}, method='PUT')[1]['enabled'] is False
        print(f'  plugins: stats 8 路 / emg_analysis csv / rules PUT+GET / lsl {"开" if l.get("enabled") else "SKIP(" + l.get("why", "") + ")"}')
        # 必失败：无头写入 / 选别的设备 / 采样率不在选项
        assert call(p, '/api/session/start', {'subject': 'x'}, header=False)[0] == 403
        assert call(p, '/api/device/select', {'id': 'wl8'})[0] == 409
        assert call(p, '/api/device/select', {'id': 'nope'})[0] == 400
        assert call(p, '/api/device/config', {'fs_Hz': 4000}, method='PUT')[0] == 400
        th.join(25)
        kinds = [k for k, _ in sse]
        assert 'gate' in kinds and 'train' in kinds and 'take' in kinds, kinds
        gate_ev = next(v for k, v in sse if k == 'gate')
        assert gate_ev['ok'] and gate_ev['device_id'] == 'fake'
        print(f'  SSE stream8 收到命名事件：{sorted(set(kinds))}；无头 403 / 选别的设备 409 / fs 不在选项 400')
        # 老录制路径（App 现在用的 /api/emg/record）每收下一条同步落 .h5 到 *-legacy 会话；'loose' 是撬电极的满幅条，老流程拒收 → 不得出现 .h5。
        # 放在流关掉之后：假手环的 take 与后台泵共用一个 seq 计数器，边推流边 take 会误报丢包（真手环没有这个问题）。
        time.sleep(1.5)
        def legacy_takes():
            return [t for t in call(p, '/api/files/list')[1]['takes'] if 'legacy' in t['session']]
        for lab, expect_n in (('rest', 1), ('fist', 2), ('loose', 2)):
            c, r = call(p, '/api/emg/record', {'label': lab, 'count': 1, 'set': 'train', 'session': 's', 'donning': 7})
            assert c == 202, (c, r)
            for _ in range(200):
                if not call(p, '/api/emg/state')[1]['busy']:
                    break
                time.sleep(.05)
            tk = legacy_takes()
            assert len(tk) == expect_n, (lab, [t['label'] for t in tk], call(p, '/api/emg/state')[1]['log'][-3:])
            if lab != 'loose':
                assert tk[-1]['label'] == lab and tk[-1]['gate']['ok'] and tk[-1]['donning'] == 7, tk[-1]
        assert '未收下' in ''.join(call(p, '/api/emg/state')[1]['log'][-4:]), '满幅条应被旧流程拒收'
        print('  老 /api/emg/record：rest/fist 各同步 1 个 .h5（legacy 会话，donning=7，gate ok）；满幅 loose 旧流程拒收、不落 .h5')


def other_devices(tmp):
    with Server('--device', 'v12') as s:
        st = call(s.port, '/api/device/state')[1]
        assert st['device_id'] == 'v12' and not st['capabilities']['record']
        assert call(s.port, '/api/session/start', {'subject': 'x'})[0] == 403
        assert call(s.port, '/api/emg/state')[0] == 200
        print('  v12（合成）：state 可读，session/start 403（描述 record=false）')
    desc = dd.load('fake')
    rng = np.random.default_rng(0)
    stem = Path(tmp) / 'rest' / 'take'
    stem.parent.mkdir(parents=True, exist_ok=True)
    wl8.save(stem, rng.normal(0, 8, (4000, 8)).astype(np.float32), np.zeros((416, 6), np.int16), np.arange(4000, dtype=np.uint8), 'rest', 's', 1, 'fake')
    with Server('--replay', str(stem.with_suffix('.npz'))) as s:
        st = call(s.port, '/api/device/state')[1]
        assert st['device_id'] == 'replay' and 'device=replay' in ''.join(s.lines)
        assert call(s.port, '/api/take/start', {'label': 'x'})[0] in (403, 409)
        print('  --replay 别名：device=replay，take/start 被拒')
    with Server('--fake') as s:
        st = call(s.port, '/api/device/state')[1]
        assert st['device_id'] == 'cheez' and st['n_channels'] == 1
        assert call(s.port, '/api/emg/stream8?project=')[0] == 409          # 单路没有 8 路流
        print('  --fake 别名（Cheez 假台架）：device=cheez 1 路，stream8 409')
    with Server('--fake', '--wl8') as s:
        assert call(s.port, '/api/device/state')[1]['device_id'] == 'fake'
        print('  --fake --wl8 别名：device=fake')


def main():
    with tempfile.TemporaryDirectory() as tmp:
        fake_flow(tmp)
    with tempfile.TemporaryDirectory() as tmp:
        other_devices(tmp)
    print('check_studio_api: 24 条路由在 --device fake 跑通，SSE gate/train/take 事件到达，v12/replay/cheez 别名正确，8 条必失败全红')


if __name__ == '__main__':
    main()

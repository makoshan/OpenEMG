"""「肌电工作室」要用的采集服务接口，端到端走一遍（假手环，临时目录，不碰真实工程）：
抓放连续录制（开始 / 进度 / 保存 / 本次佩戴统计）→ 条件检查 → 手势录制 → 训练（进度事件、run.json）→
实时识别（stream8 里出现 event: pred）→ 回放模式（有数据流，但拒绝录制）。"""
import json
import tempfile
import threading
import time
import urllib.request
from pathlib import Path

import emg_web
import wl8
import wl8_cursor
import wl8_actions

H = {'X-Mako-Collector': '1', 'Content-Type': 'application/json', 'X-Mako-Project': ''}


def call(port, path, body=None):
    req = urllib.request.Request(f'http://127.0.0.1:{port}{path}', data=None if body is None else json.dumps(body).encode(), headers=H)
    try:
        with urllib.request.urlopen(req, timeout=30) as r: return r.status, json.loads(r.read() or b'{}')
    except urllib.error.HTTPError as e: return e.code, json.loads(e.read() or b'{}')


def wait_idle(port, timeout=120):
    t0 = time.time()
    while time.time() - t0 < timeout:
        s = call(port, '/api/emg/state')[1]
        if not s['busy']: return s
        time.sleep(.2)
    raise AssertionError('等待空闲超时')


def serve(rig, root):
    sets = {k: {kind: root / p.name for kind, p in v.items()} for k, v in emg_web.SETS.items()}
    session = emg_web.Session(rig, sets, model_root=root / 'models')
    srv = emg_web.server_for(session, 0); threading.Thread(target=srv.serve_forever, daemon=True).start()
    return session, srv, srv.server_port


def sse_events(port, want, seconds=8):
    """读 stream8，返回收到的各类事件计数；看到 want 就提前返回。"""
    got = {'emg': 0, 'imu': 0, 'pred': 0}; kind = 'emg'; t0 = time.time()
    with urllib.request.urlopen(f'http://127.0.0.1:{port}/api/emg/stream8?project=', timeout=10) as r:
        for line in r:
            if line.startswith(b'event:'): kind = line[6:].strip().decode()
            elif line.startswith(b'data:'): got[kind] = got.get(kind, 0) + 1; kind = 'emg'
            if got.get(want) or time.time() - t0 > seconds: break
    return got


with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    session, srv, port = serve(wl8.FakeWl8Rig(), root)
    session.ab.scale, session.ab.voice = .05, False                          # 日程加速到 1/20，不出声
    # 1) 抓放：状态、开始一步、录制中有进度、完成后本次佩戴统计 +1
    st = call(port, '/api/emg/ab?hand=left&donning=1')[1]
    assert st['protocol'] == 'ab-control-v1' and [s['key'] for s in st['steps']][:3] == ['rehearsal', 'rest60', 'hold20'] and st['done']['rest60']['files'] == 0
    assert call(port, '/api/emg/ab', {'action': 'start', 'step': 'nope'})[0] == 400
    assert call(port, '/api/emg/ab', {'action': 'start', 'step': 'rehearsal', 'hand': 'left', 'donning': 1, 'purpose': 'rehearsal', 'strap_hole': 0})[0] == 400
    assert call(port, '/api/emg/ab', {'action': 'start', 'step': 'rehearsal', 'hand': 'left', 'donning': 1, 'purpose': 'rehearsal', 'strap_hole': 4})[0] == 200
    seen = None
    for _ in range(100):
        p = call(port, '/api/emg/state')[1]['wl8']['ab']['progress']
        if p.get('phase') in ('rest', 'hold', 'release'): seen = p; break
        time.sleep(.05)
    assert seen and seen['cycles'] == 5 and seen['cycle_plan'] and 'step_remaining' in seen, seen
    s = wait_idle(port)
    assert call(port, '/api/emg/ab?hand=left&donning=1')[1]['done']['rehearsal']['files'] == 1
    saved = Path(s['wl8']['ab']['last_saved']['path']); assert saved.exists() and s['wl8']['ab']['last_saved']['emg_samples'] > 0
    assert json.loads(saved.with_suffix('.json').read_text())['strap_hole'] == 4, '抓放录音没记织带孔位'
    # 2) 条件检查（只提醒）
    c = call(port, '/api/emg/ab', {'action': 'conditions', 'seconds': 2})[1]
    assert 'warnings' in c and c['emg_samples'] > 0, c
    # 3) 手势录制 + 训练：进度事件里有学习曲线，run.json 有重戴分数和混淆矩阵
    for split, n in (('train', 8), ('rewear', 5)):
        for label in ('rest', 'pinch', 'fist'):
            assert call(port, '/api/emg/record', {'label': label, 'count': n, 'set': split, 'countdown': 0})[0] == 202; wait_idle(port)
    assert call(port, '/api/emg/wl8/train', {'labels': ['rest', 'pinch', 'fist']})[0] == 202
    s = wait_idle(port); job = s['wl8']['train']
    assert job['run_id'] and not job['error'] and any(e['stage'] == 'curve' for e in job['events']), job
    runs = call(port, '/api/emg/wl8/runs')[1]; run = call(port, f"/api/emg/wl8/run?id={runs[0]['id']}")[1]
    assert run['rewear'] is not None and run['confusion']['rows'] == ['rest', 'pinch', 'fist'] and len(run['projection']['train']) >= 24
    assert runs[0]['rewear_source'] == '重戴目录' and [e.get('source') for e in job['events'] if e['stage'] == 'rewear'] == ['重戴目录'], (runs[0], job['events'])   # 列表和进度都带来源
    assert call(port, '/api/emg/wl8/run?id=../../etc')[0] == 400
    # 织带孔位：只写进这一条录音的元数据，其余条是 null；坏值 400
    assert call(port, '/api/emg/record', {'label': 'rest', 'count': 1, 'set': 'rewear', 'countdown': 0, 'strap_hole': 6})[0] == 202; wait_idle(port)
    holes = [json.loads(f.read_text()).get('strap_hole') for f in root.rglob('rest-*.json')]
    assert holes.count(6) == 1 and holes.count(None) == len(holes) - 1 >= 13, holes
    for bad in (0, 21, True, '6', 2.5): assert call(port, '/api/emg/record', {'label': 'rest', 'count': 1, 'set': 'rewear', 'countdown': 0, 'strap_hole': bad})[0] == 400, bad
    # 戴法：同样只写这一条，其余条 null；坏值 400
    assert call(port, '/api/emg/record', {'label': 'rest', 'count': 1, 'set': 'rewear', 'countdown': 0, 'cable_dir': 'elbow', 'ch0_site': 'dorsal'})[0] == 202; wait_idle(port)
    worn = [(m.get('cable_dir'), m.get('ch0_site')) for m in (json.loads(f.read_text()) for f in root.rglob('rest-*.json'))]
    assert worn.count(('elbow', 'dorsal')) == 1 and worn.count((None, None)) == len(worn) - 1, worn
    for k, bad in (('cable_dir', 'wrist'), ('cable_dir', 1), ('cable_dir', ''), ('ch0_site', 'Ulnar'), ('ch0_site', ['ulnar']), ('ch0_site', True)):
        assert call(port, '/api/emg/record', {'label': 'rest', 'count': 1, 'set': 'rewear', 'countdown': 0, k: bad})[0] == 400, (k, bad)
    # 4) 实时识别：stream8 里出现 event: pred，状态里有最近一次结果
    assert call(port, '/api/emg/wl8/live', {'action': 'start'})[1]['run_id'] == runs[0]['id']
    ev = sse_events(port, 'pred'); assert ev['pred'] >= 1, ev
    last = call(port, '/api/emg/state')[1]['wl8']['live']['last']; assert set(last['probs']) == {'rest', 'pinch', 'fist'} and last['top'] in last['probs']
    # 屏蔽坏路：tune 带 mask → 之后的识别结果回报 mask；坏输入 400；mask [] 取消
    assert call(port, '/api/emg/wl8/live', {'action': 'tune', 'mask': [2, 7]})[1]['mask'] == [2, 7]
    t_mask = time.time()
    while time.time() - t_mask < 5 and (call(port, '/api/emg/state')[1]['wl8']['live']['last'] or {}).get('mask') != [2, 7]: time.sleep(.1)
    last = call(port, '/api/emg/state')[1]['wl8']['live']['last']; assert last['mask'] == [2, 7] and last['top'] in last['probs'], last
    for bad in ([0], [9], [1, 2, 3, 4, 5, 6, 7, 8], 'x', [True]): assert call(port, '/api/emg/wl8/live', {'action': 'tune', 'mask': bad})[0] == 400, bad
    assert call(port, '/api/emg/wl8/live', {'action': 'tune', 'mask': []})[1]['mask'] == []
    # 手势 → 鼠标：记录模式（检查不能动真鼠标），只认三个动作；识别停了就拒绝，暂停 / 恢复不受限
    session.actions = wl8_actions.Actions(enable=False)
    assert call(port, '/api/emg/wl8/action', {'action': 'left_click'})[1] == {'ok': True, 'action': 'left_click'}
    code, err = call(port, '/api/emg/wl8/action', {'action': 'key'}); assert code == 400 and '未知动作' in err['error'], err
    assert call(port, '/api/emg/wl8/live', {'action': 'stop'})[0] == 200
    code, err = call(port, '/api/emg/wl8/action', {'action': 'move', 'dx': 10}); assert code == 409 and '实时识别' in err['error'], err
    assert call(port, '/api/emg/wl8/action', {'action': 'resume'})[0] == 200
    # AI 授权卡：钩子上报的待确认 / 结果出现在 state.wl8.ai
    assert call(port, '/api/emg/wl8/ai', {'action': 'pending', 'cmd': 'npm test', 'timeout': 20})[1]['state'] == 'pending'
    assert call(port, '/api/emg/state')[1]['wl8']['ai']['cmd'] == 'npm test'
    assert call(port, '/api/emg/wl8/ai', {'action': 'done', 'decision': 'allow', 'ms': 410})[1]['decision'] == 'allow'
    code, err = call(port, '/api/emg/wl8/ai', {'action': 'done', 'decision': 'allow'}); assert code == 400, err
    srv.shutdown()
    # 5) 回放：用刚才那段抓放录音推流；状态标明回放；拒绝抓放录制和手势录制
    session2, srv2, port2 = serve(wl8.ReplayWl8Rig(saved), root / 'replay')
    ev2 = sse_events(port2, 'emg'); assert ev2['emg'] >= 1, ev2
    s2 = call(port2, '/api/emg/state')[1]; assert s2['wl8']['replay'] == saved.name and s2['rig']['banner'].startswith('回放')
    assert call(port2, '/api/emg/ab', {'action': 'start', 'step': 'rest60', 'hand': 'left', 'donning': 1})[0] == 400
    # 6) 光标控制：没校准不能启用；演练时 stream8 出 event: cursor；回放拒绝移动真光标
    assert s2['wl8']['cursor']['mode'] == 'off' and s2['wl8']['cursor']['replay'] is True
    code, err = call(port2, '/api/emg/wl8/cursor', {'action': 'enable'}); assert code == 400 and '校准' in err['error'], err
    cal = {'gyro_bias': [0, 0, 0], 'x_axis': 2, 'x_sign': 1, 'y_axis': 0, 'y_sign': 1, 'created': 'check'}
    session2.cursor.cal, session2.cursor.aim = cal, wl8_cursor.Aim(cal)                   # 校准要 15 s 真转手腕，这里直接给一份
    assert call(port2, '/api/emg/wl8/cursor', {'action': 'log'})[1]['mode'] == 'log'
    ev3 = sse_events(port2, 'cursor'); assert ev3['cursor'] >= 1, ev3
    code, err = call(port2, '/api/emg/wl8/cursor', {'action': 'enable'}); assert code == 400 and '回放' in err['error'], err
    assert call(port2, '/api/emg/wl8/cursor')[1]['mode'] == 'log'
    assert call(port2, '/api/emg/wl8/cursor', {'action': 'stop'})[1]['mode'] == 'off'
    code, err = call(port2, '/api/emg/wl8/action', {'action': 'left_click'}); assert code == 409 and '回放' in err['error'], err
    srv2.shutdown()
print('EMG studio API passed: 抓放连续录制与进度 / 佩戴统计 / 条件检查 / 训练进度与 run.json / 织带孔位写进元数据且坏值拒收 / 实时识别 pred 事件 / 回放推流且拒绝录制 / 路径穿越拒绝 / 光标：未校准拒绝、演练出 cursor 事件、回放拒绝移动；手势动作只认三个、回放拒绝')

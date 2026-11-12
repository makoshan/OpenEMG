"""The collection site end to end on a fake rig: record -> gate -> auto -> evaluate -> evidence,
plus the refusals (bad takes dropped, mutations need the header, busy is busy).
Run: python3 firmware/check_emg_web.py"""
import json
import queue
import tempfile
import threading
import time
import urllib.request
from pathlib import Path

import numpy as np

import emg_web
import usb_emg


FakeRig = emg_web.FakeRig

# Cross-wear gate: must fail on an incomplete or lopsided rewear set even when raw accuracy is high
import emg_model
full = emg_model._report(['rest'] * 6 + ['hard'] * 6, ['rest'] * 6 + ['hard'] * 6, ['rest', 'hard'])
assert emg_web.rewear_passed(full)
one_class = emg_model._report(['rest'] * 12, ['rest'] * 12, ['rest', 'hard'])
assert one_class['accuracy'] == 1 and not emg_web.rewear_passed(one_class), 'rewear with no hard takes passed'
lopsided = emg_model._report(['rest'] * 40 + ['hard'] * 5, ['rest'] * 45, ['rest', 'hard'])
assert lopsided['accuracy'] > .8 and not emg_web.rewear_passed(lopsided), 'majority class carried rewear'
assert not emg_web.rewear_passed(None)


def check_stream_recovery():
    from types import SimpleNamespace
    from unittest.mock import patch
    class Connection:
        def __init__(self): self.commands = []
        def write(self, data): self.commands.append(data)
        def readline(self):
            time.sleep(.02)
            return b'S 0 10 0 0 0 0 0 0 0 0 0 0\n'
    for kind in ('emg', 'emgimu'):
        for reject in (False, True):
            rig = emg_web.Rig()
            rig.conn = Connection()
            rig.device = SimpleNamespace(serial_number='FAKE')
            rig.kind = kind
            rig.banner = "R=preview-record"
            module = usb_emg if kind == 'emg' else emg_web.usb_emg_imu
            counts = usb_emg._synth('rest', np.random.default_rng(1))
            def read_take(*args, **kwargs):
                assert not rig.pump.is_alive(), 'stream reader stole the recording port'
                if kind == 'emg':
                    while not q.empty(): q.get_nowait()
                    args[2]('S 123 10 ' + ' '.join(['2048'] * 10))
                    assert q.get_nowait().startswith('S 123 '), 'record preview did not reach SSE queue'
                if reject: raise ValueError('test rejection')
                if kind == 'emg': return counts, 1000, 0, {}
                return {'worn': 1000, 't0_ms': 0, 'n_imu': 1, 'max_gap_us': 1000}, counts, [], 0
            with tempfile.TemporaryDirectory() as tmp, patch.object(usb_emg, '_drain'), patch.object(module, 'read_take', side_effect=read_take), patch.object(module, 'save'), patch.object(emg_web.usb_emg_imu, 'lead', return_value=None):
                q = rig.subscribe()
                q.get(timeout=1)
                try: rig.take('rest', 'high', Path(tmp), 'test', 1)
                except ValueError:
                    assert reject
                else: assert not reject
                assert rig.streaming and rig.conn.commands == ([b's', b's'] if kind == 'emg' else [b's', b's', b's'])
                while not q.empty(): q.get_nowait()
                assert q.get(timeout=1).startswith('S '), 'no fresh stream after take'
                rig.unsubscribe(q)
                assert not rig.pump.is_alive()
    print('Stream recovery: fresh frames after accepted/rejected EMG and EMG+IMU takes')

def check_stream_sync():
    from unittest.mock import patch
    class Connection:
        def __init__(self, active): self.active, self.commands = active, []
        def readline(self):
            time.sleep(.02)
            return b'S 1 10 2048\n' if self.active else b''
        def write(self, data): self.commands.append(data); self.active = not self.active
    for active in (False, True):
        rig = emg_web.Rig(); rig.conn = Connection(active)
        with patch.object(usb_emg, '_drain'): rig._sync_stream()
        assert not rig.conn.active and not rig.streaming
        assert rig.conn.commands == ([b's'] if active else [])
    print('Stream startup: preserved board toggle synchronized PASS')

check_stream_sync()
check_stream_recovery()


def call(port, path, body=None, header=True):
    req = urllib.request.Request(f'http://127.0.0.1:{port}{path}', data=json.dumps(body).encode() if body is not None else None,
                                 headers={'Content-Type': 'application/json', **({'X-Mako-Collector': '1'} if header else {})}, method='POST' if body is not None else 'GET')
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            raw = r.read(); return r.status, (json.loads(raw) if 'json' in (r.getheader('Content-Type') or '') else raw)
    except urllib.error.HTTPError as e: return e.code, json.loads(e.read())


def check_cue_receipt_lands_on_the_take():
    rig = FakeRig()
    rig.hold_after_cue = threading.Event()
    rig.fixed_ack = (time.time_ns() // 1_000_000) * 1_000_000
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        sets = {'train': {'emg': root / 'emg-data', 'emgimu': root / 'x'},
                'rewear': {'emg': root / 're', 'emgimu': root / 'y'}}
        session = emg_web.Session(rig, sets, model_root=root / 'models')
        srv = emg_web.server_for(session, 0); port = srv.server_port
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        shown = rig.fixed_ack // 1_000_000 + 250
        assert call(port, '/api/emg/cue-shown', {'shown_ms': shown, 'recording_ack_host_ns': str(rig.fixed_ack)})[0] == 409
        assert call(port, '/api/emg/record', {'label': 'rest', 'count': 1, 'countdown': 0})[0] == 202
        ack = None
        for _ in range(100):
            phase = call(port, '/api/emg/state')[1]['progress']
            if phase.get('phase') == 'NOW':
                ack = phase['recording_ack_host_ns']
                break
            time.sleep(.02)
        assert ack == str(rig.fixed_ack), ack
        assert call(port, '/api/emg/cue-shown', {'shown_ms': 10, 'recording_ack_host_ns': ack})[0] == 400
        assert call(port, '/api/emg/cue-shown', {'shown_ms': shown, 'recording_ack_host_ns': '999'})[0] == 409
        assert call(port, '/api/emg/cue-shown', {'shown_ms': shown, 'recording_ack_host_ns': ack})[0] == 202
        rig.hold_after_cue.set()
        wait_idle(port)
        saved = json.loads(next((root / 'emg-data' / 'rest').glob('*.json')).read_text())
        assert saved['cue_sample_index'] == 250, saved
        assert saved['ack_to_cue_ms'] == 250.0, saved
        assert call(port, '/api/emg/cue-shown', {'shown_ms': shown, 'recording_ack_host_ns': ack})[0] == 409
    print('Cue receipt: 做！ has host-relative sample estimate 250 and a late or mismatched receipt is refused')


def wait_idle(port):
    for _ in range(600):
        s = call(port, '/api/emg/state')[1]
        if not s['busy']: return s
        time.sleep(.05)
    raise AssertionError('server stayed busy')


check_cue_receipt_lands_on_the_take()


with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp); sets = {'train': {'emg': root / 'emg-data', 'emgimu': root / 'x'}, 'rewear': {'emg': root / 'emg-data-rewear', 'emgimu': root / 'y'}}
    session = emg_web.Session(FakeRig(), sets, model_root=root / 'models')
    srv = emg_web.server_for(session, 0); port = srv.server_port
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    # pages served, mutation without the header refused
    assert call(port, '/')[0] == 200 and call(port, '/pulse')[0] == 200 and call(port, '/guide')[0] == 200 and call(port, '/emg_demo.js')[0] == 200
    assert call(port, '/api/emg/record', {'label': 'rest', 'count': 1}, header=False)[0] == 403
    assert call(port, '/api/emg/record', {'label': 'thumb', 'count': 1})[0] == 400, 'unknown tier accepted'
    # record three tiers + loose; loose must be dropped by validate, not saved
    for label in ('rest', 'light', 'hard'):
        assert call(port, '/api/emg/record', {'label': label, 'count': 12, 'countdown': 0})[0] == 202
        assert call(port, '/api/emg/record', {'label': label, 'count': 1})[0] == 400, 'second job while busy accepted'
        wait_idle(port)
    assert call(port, '/api/emg/record', {'label': 'loose', 'count': 3, 'countdown': 0})[0] == 202
    s = wait_idle(port)
    assert s['counts']['train'] == {'hard': 12, 'light': 12, 'rest': 12}, s['counts']   # no loose/ folder with files
    sidecar = json.loads(next((root / 'emg-data' / 'rest').glob('*.json')).read_text())
    assert 'recording_ack_host_ns' in sidecar and 'cue_sample_index' not in sidecar, sidecar.keys()
    assert sum('未收下' in l and 'loose' in l for l in s['log']) == 3, s['log'][-5:]
    # rewear set is a separate root
    assert call(port, '/api/emg/record', {'label': 'rest', 'count': 6, 'set': 'rewear', 'countdown': 0})[0] == 202; wait_idle(port)
    for label in ('light', 'hard'):
        call(port, '/api/emg/record', {'label': label, 'count': 6, 'set': 'rewear', 'countdown': 0}); wait_idle(port)
    s = wait_idle(port); assert s['counts']['rewear'] == {'hard': 6, 'light': 6, 'rest': 6}, s['counts']
    # gate -> auto -> evaluate through pipeline, against THIS temp root
    import pipeline
    pipeline.REGISTRY = root / 'index.json'
    for stage in ('gate', 'auto', 'evaluate'):
        assert call(port, '/api/emg/run', {'stage': stage})[0] == 202; s = wait_idle(port)
    R = s['results']
    assert R['gate']['separability']['status'] in ('ok', 'warn'), R['gate']
    assert R['auto']['trained'] and R['auto']['trained']['metadata']['loo']['accuracy'] >= .8, R['auto']
    assert R['evaluate']['evaluation']['rewear']['accuracy'] >= .8, R['evaluate']
    # evidence: four-state from disk + results; the lead row must say 未实现, not pass
    ev = call(port, '/api/emg/evidence', {})[1]
    text = Path(ev['path']).read_text()
    assert '已实测通过' in text and '| 提前量 | 未实现' in text, text
    assert '"rest": 12' in text and 'loose' not in text.split('## 四态')[0].split('## 数据')[1], '数据段把丢弃的 loose 算进去了'
    Path(ev['path']).unlink()
    # live stream: SSE hands out what the rig pumps
    import http.client
    c = http.client.HTTPConnection('127.0.0.1', port, timeout=5); c.request('GET', '/api/emg/stream'); r = c.getresponse()
    assert r.status == 200 and r.getheader('Content-Type').startswith('text/event-stream')
    first = r.readline().decode(); assert first.startswith('data: S 0 10 '), first
    c.close(); srv.shutdown()
print('EMG web: pages, refusals, record/drop, rewear root, gate/auto/evaluate, evidence four-state and SSE passed')


# ---- the wristband path: FakeWl8Rig -> record 5 gestures + loose (dropped) -> sweep -> evidence
import wl8
with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp); sets = {'train': {'wl8': root / 'emg-wl8-data'}, 'rewear': {'wl8': root / 'emg-wl8-data-rewear'}}
    session = emg_web.Session(wl8.FakeWl8Rig(), sets, model_root=root / 'models')
    srv = emg_web.server_for(session, 0); port = srv.server_port
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    state = call(port, '/api/emg/state')[1]
    assert tuple(state['tiers']) == wl8.LABELS and state['rig']['kind'] == 'wl8', state
    assert call(port, '/api/emg/record', {'label': 'light', 'count': 1})[0] == 400, 'XIAO tier accepted on the wristband'
    for which, n in (('train', 8), ('rewear', 6)):
        for label in ('rest', 'left', 'right', 'click'):
            assert call(port, '/api/emg/record', {'label': label, 'count': n, 'set': which, 'countdown': 0})[0] == 202
            wait_idle(port)
    assert call(port, '/api/emg/record', {'label': 'loose', 'count': 2, 'countdown': 0})[0] == 202
    s = wait_idle(port)
    assert s['counts']['train'].get('loose', 0) == 0 and any('饱和' in l for l in s['log']), 'railed loose take was saved'
    assert s['counts']['train']['click'] == 8 and s['counts']['rewear']['click'] == 6
    # the live pane gets page-format lines from the wristband stream
    q = session.rig.subscribe(); line = q.get(timeout=5); session.rig.unsubscribe(q)
    f = line.split(); assert f[0] == 'S' and len(f) == 13 and all(0 <= int(v) <= 4095 for v in f[3:]), line
    assert call(port, '/api/emg/run', {'stage': 'evaluate'})[0] == 202
    s = wait_idle(port); sw = s['results']['sweep']
    assert sw['g2_passed'] and sw['best']['4']['balanced'] > .8, sw['message']   # JSON keys are strings
    ev = call(port, '/api/emg/evidence', {})[1]
    assert any(n.startswith('腕带') and st == '已实测通过' for n, st, _ in ev['rows']), ev['rows']
    # live events: an energy-pattern classifier stands in for the CNN; the fake stream carries a burst every 3rd second.
    def classify(win):
        e = (win ** 2).mean(1); return ('fist' if e.min() > 3 else 'middle' if e[0] > 3 * e[1] else 'thumb'), .9
    session.watch(classify, [0, 2, 4, 6])
    q = session.rig.subscribe(); time.sleep(9.5); session.rig.unsubscribe(q)
    s = call(port, '/api/emg/state')[1]
    assert s['live'] == 'ready' and len(s['events']) >= 1, s['events']
    assert all(e['label'] != 'rest' for e in s['events']), s['events']
    srv.shutdown()
    print('wl8 collector path passed:', sw['message'], '| live events', [e['label'] for e in s['events']])

# Same-wear validation archived on 2026-09-29 must not count as re-wear: score only the classes really re-worn.
with tempfile.TemporaryDirectory() as tmp:
    archive = Path(tmp)
    (archive / 'validation-same-wear-x').mkdir(); (archive / 'rub-redefined').mkdir()
    (archive / 'validation-same-wear-x/README.json').write_text(json.dumps({'files': ['validation/rub/a.json', 'validation/rub/a.npz']}))
    (archive / 'rub-redefined/README.json').write_text(json.dumps({'files': ['validation/snap/b.npz']}))  # other reasons are not same-wear
    same = emg_web.same_wear_files(archive)
    assert same == {'validation/rub/a.npz'}, same
    labels = ['rest', 'pinch', 'rub', 'snap', 'fist']
    report = {'manifest': [{'file': 'validation/rub/a.npz'}, {'file': 'validation/snap/b.npz'}, {'file': 'train/rub/c.npz'}],
              'validation': {'labels': labels, 'balanced_accuracy': .7, 'recall': dict(zip(labels, [.8, .8, .8, .7, .4]))}}
    score = emg_web.rewear_score(report, same)
    assert score['excluded'] == ['rub'] and abs(score['score'] - (.8 + .8 + .7 + .4) / 4) < 1e-9, score
    assert emg_web.rewear_score(report, set()) == {'excluded': [], 'score': .7}
    print('Same-wear validation: archived takes named and left out of the re-wear score PASS')

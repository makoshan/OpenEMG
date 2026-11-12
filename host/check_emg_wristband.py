"""No hardware or real project data: 8-channel SSE preserves every channel; wrong rig/project refused."""
import json
import queue
import tempfile
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path
import numpy as np
import emg_web
import wl8

class ProbeRig(wl8.Wl8Rig):
    def subscribe(self):
        q = queue.Queue(); self.subscribers.append(q)
        def push():
            time.sleep(.05)
            for fn in list(self.frame_subscribers): fn(np.arange(64).reshape(8, 8))
        threading.Thread(target=push, daemon=True).start()
        return q

with tempfile.TemporaryDirectory() as temp:
    root = Path(temp)
    sets = {split: {kind: root / split / kind for kind in ('emg', 'emgimu', 'wl8')} for split in ('train', 'rewear')}
    rig = ProbeRig()
    session = emg_web.Session(rig, sets, model_root=root / 'models', project={'id': 'probe', 'name': 'probe'})
    server = emg_web.server_for(session, 0)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f'http://127.0.0.1:{server.server_port}'
    initial_frames = list(rig.frame_subscribers)  # Session自带光标订阅；拒绝请求不得新增订阅。
    initial_boundaries = list(rig.boundary_subscribers)
    try:
        for project,kind in [('other','wl8'),('probe','emg')]:
            rig.kind=kind
            try: urllib.request.urlopen(base+'/api/emg/stream8?project='+project, timeout=2)
            except urllib.error.HTTPError as e: assert e.code == 409
            else: raise AssertionError('mismatch accepted')
            assert not rig.subscribers and rig.frame_subscribers == initial_frames
            assert rig.boundary_subscribers == initial_boundaries
        rig.kind='wl8'
        with urllib.request.urlopen(base+'/api/emg/stream8?project=probe',timeout=2) as r:
            packet=json.loads(r.readline().decode().removeprefix('data: '))
            assert packet['samples']==np.arange(64).reshape(8,8).tolist()
            assert packet['hz']==2000 and packet['unit']=='uV' and packet['sample_index']==0
            assert packet['dropped_frames']==0
            assert len(set(packet['samples'][0]))==8, 'CH1 copied to other channels'
        with urllib.request.urlopen(base+'/wristband',timeout=2) as r:
            assert '等待逐指模型' in r.read().decode()
    finally:
        server.shutdown(); server.server_close()
print('PASS: 8 distinct channels, units/rate/index, wrong project and single-channel rejection, dashboard route')

"""动作组清单 → 采集服务：App 入口（emg8-server.py install）把每个组的类别注册进 wl8.LABELS、口令名补进 calibration_voice.NAMES；
新动作组（如幽灵线 · 结印）不改 host 就能按校准流程录。原有口令不被清单覆盖。"""
import importlib.util
import json
import os
import tempfile
import time
from pathlib import Path

os.environ['YUANLI_VOICE'] = 'off'          # 不出声；口令只检查名字和流程
HERE = Path(__file__).resolve().parent
ENTRY = HERE.parent / 'app' / 'electron' / 'emg8-server.py'
spec = importlib.util.spec_from_file_location('emg8_server', ENTRY); srv = importlib.util.module_from_spec(spec); spec.loader.exec_module(srv)
srv.install(HERE)

import calibration_voice
import emg_web
import wl8

profiles = json.loads((ENTRY.parent / 'emg8-profiles.json').read_text())
for name, p in profiles.items():
    for label in p.get('captureLabels', p['labels']):
        assert label in wl8.LABELS, f'{name}/{label} 没注册成可录类别'
    for label, g in (p.get('gestures') or {}).items():
        assert calibration_voice.NAMES.get(label), f'{name}/{label} 没有口令名'
assert calibration_voice.NAMES['ai_up'] == '拇指上滑', '原有口令被清单覆盖了'
assert calibration_voice.NAMES['seal_poxie'] == profiles['ghost-seals']['gestures']['seal_poxie']['voice']

# 结印类按校准流程（calibration=True、倒数 3 秒）能录进训练集
with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp); sets = {'train': {'wl8': root / 'emg-wl8-data'}, 'rewear': {'wl8': root / 'emg-wl8-data-rewear'}}
    s = emg_web.Session(wl8.FakeWl8Rig(), sets, model_root=root / 'models')
    s.record('seal_poxie', 1, 'train', '', 1, 'high', countdown=3, calibration=True)
    for _ in range(300):
        if not s.busy: break
        time.sleep(.05)
    assert s.counts()['train'].get('seal_poxie') == 1, s.log[-5:]
# 结印组走「每次佩戴校准」训练：两次佩戴各录 3 条，只用最新一次（protocol 缺了会落回旧训练、混进旧佩戴，2026-10-14 复核抓到）
seals = profiles['ghost-seals']['labels']
with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp); sets = {'train': {'wl8': root / 'emg-wl8-data'}, 'rewear': {'wl8': root / 'emg-wl8-data-rewear'}}
    s = emg_web.Session(wl8.FakeWl8Rig(), sets, model_root=root / 'models')
    for donning in (1, 2):
        for label in seals:
            s.record(label, 3, 'train', '', donning, 'high', countdown=0)
            while s.busy: time.sleep(.05)
    import wl8_train
    rep, model = wl8_train.train(root, seals, progress=lambda *_: None)
    assert rep['validation']['status'] == 'calibration' and rep['validation']['donning'] == 2, rep['validation']
    assert all(n == 3 for n in rep['counts']['train'].values()), rep['counts']
# 没有重戴目录、训练集有两次佩戴：普通组（抓握）按佩戴编号留一次佩戴出分；拇指组规矩是没有合格重戴不出分，进度和结果都不能带重戴分
import numpy as np
rng = np.random.default_rng(5)
for name, per in (('grasp', 3), ('thumb-four', 5)):
    labels = profiles[name]['labels']
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        for donning in (1, 2):
            for k, label in enumerate(labels):
                d = root / 'emg-wl8-data' / label; d.mkdir(parents=True, exist_ok=True)
                for i in range(per):
                    gain = np.full(8, 20.); gain[k % 8] *= 1 + 3 * (k > 0)
                    np.savez(d / f'{label}-{donning}-{i}.npz', emg_uv=(rng.normal(0, 1, (4000, 8)) * gain).astype(np.float32))
                    (d / f'{label}-{donning}-{i}.json').write_text(json.dumps({'donning': donning}))
        events = []
        rep, _ = wl8_train.train(root, labels, progress=events.append)
        stages = [e['stage'] for e in events]
        if name == 'grasp':
            assert rep['rewear_source'] == '留一次佩戴' and rep['rewear'] is not None and 'rewear' in stages, (rep.get('rewear'), stages)
        else:
            assert rep['validation']['status'] == 'unverified' and rep['rewear'] is None and 'rewear_source' not in rep and 'confusion' not in rep, rep.get('rewear')
            assert 'rewear' not in stages and all(e.get('rewear') is None for e in events), events[-1]
print(f'profile voice check passed: {len(profiles)} 个动作组的类别都可录、都有口令名；结印按校准流程录下 1 条；两次佩戴只用最新一次训练；无重戴时抓握留一次佩戴出分、拇指组不出分')

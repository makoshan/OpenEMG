"""单通道五类实时识别（emg_web live1）：假台架实时流 → 2 秒窗 → 结果以 `P {json}` 混进流；录制前当场退订；没模型拒绝。"""
import json
import pickle
import queue
import tempfile
import time
from pathlib import Path

import numpy as np
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis

import emg_gesture_train as egt
import emg_web
import usb_emg

with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    sets = {'train': {'emg': root / 'emg-data', 'emgimu': root / 'x'}, 'rewear': {'emg': root / 'emg-data-rewear', 'emgimu': root / 'y'}}
    rig = emg_web.FakeRig(realtime=True)
    session = emg_web.Session(rig, sets, model_root=root / 'models')
    try:
        session.live1_action({'action': 'start'})
        raise AssertionError('没模型也开了识别')
    except ValueError as e:
        assert '还没有训练好' in str(e)
    # 随机特征拟一个 LDA，只验链路不验准确率
    rng = np.random.default_rng(0)
    x = rng.normal(0, 1, (50, 2000))
    model = LinearDiscriminantAnalysis().fit(egt.features(x), np.arange(50) % 5)
    run = session.single_models() / 'r1'; run.mkdir(parents=True)
    (run / 'model.pkl').write_bytes(pickle.dumps(model)); (run / 'report.json').write_text(json.dumps({'model': 'lda'}))

    page = rig.subscribe()                                     # 页面那一路 SSE
    assert session.live1_action({'action': 'start'})['run_id'] == 'r1'   # 不给 run_id 用最新一次
    preds, deadline = [], time.time() + 6
    while time.time() < deadline and len(preds) < 2:
        try: line = page.get(timeout=1)
        except queue.Empty: continue
        if line.startswith('P '): preds.append(json.loads(line[2:]))
    assert len(preds) >= 2 and all(p['label'] in egt.LABELS for p in preds), preds
    assert session.state()['live1']['last']['label'] in egt.LABELS
    n = len(rig.subscribers)
    session._stop_live1()
    assert len(rig.subscribers) == n - 1 and session.live1 is None, '停下要当场退订'
    rig.unsubscribe(page)
    # 别的动作组（与八通道同一份清单）：数据、模型各占目录；训练脚本按给定类别训练，识别结果用这组的类别名
    group, labels = 'ai-select', ('ai_rest', 'ai_summon', 'ai_up')
    assert session.gesture_sets(group)['train'] != session.gesture_sets()['train'] and session.single_models(group) != session.single_models()
    for split, n in (('train', 30), ('validation', 10)):
        for i, label in enumerate(labels):
            d = session.gesture_sets(group)[split] / label; d.mkdir(parents=True)
            for k in range(n):
                c = usb_emg._synth(('rest', 'light', 'hard')[i], rng)
                usb_emg.save(d / f'{label}-{k}', c, 1000, label, 'FAKE')
    out = session.single_models(group) / 'g1'
    rep = egt.train(session.gesture_sets(group)['train'].parent, out, 'lda', labels=labels)
    assert rep['labels'] == list(labels) and set(rep['validation']['recall']) == set(labels)
    assert session.state(group=group, labels=list(labels))['gesture_counts']['train'] == {l: 30 for l in labels}
    assert session.state(group=group, labels=list(labels))['gesture_training']['runs'][0]['id'] == 'g1'
    try: session.state(group='Bad/..', labels=['x', 'y']); raise AssertionError('非法组名放行了')
    except ValueError: pass
    page = rig.subscribe()
    assert session.live1_action({'action': 'start', 'group': group, 'labels': list(labels)})['run_id'] == 'g1'
    got, deadline = None, time.time() + 6
    while time.time() < deadline and not got:
        try: line = page.get(timeout=1)
        except queue.Empty: continue
        if line.startswith('P '): got = json.loads(line[2:])
    assert got and got['label'] in labels, got
    session._stop_live1(); rig.unsubscribe(page)
    print(f'live1 check passed: 假台架流出 {len(preds)} 次识别（{preds[0]["label"]}…），停下当场退订，没模型拒绝；动作组 ai-select 三类训练 → 识别出 {got["label"]}')

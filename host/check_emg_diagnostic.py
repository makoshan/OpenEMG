"""Diagnostic capture must resume and never change the training/test counts."""
import tempfile
import time
from pathlib import Path
import emg_web

with tempfile.TemporaryDirectory() as temp:
    root = Path(temp)
    sets = {k: {kind: root / p.name for kind, p in v.items()} for k,v in emg_web.SETS.items()}
    s = emg_web.Session(emg_web.FakeRig(), sets, model_root=root/'models')
    before = s.gesture_counts()
    d = s.diagnostic_action('start')
    assert s.diagnostic_action('start')['id'] == d['id']
    try: s.diagnostic_action('wear', 2)
    except ValueError: pass
    else: raise AssertionError('next wear allowed before previous completion')
    for wear in range(1,4):
        s.diagnostic_action('wear', wear)
        for n in range(5):
            for label in ('rest','pinch','rub'):
                s.record(label,1,f'wear-{wear}','fake diagnostic',wear,'high',countdown=0,task='diagnostic')
                deadline = time.monotonic()+10
                while s.busy and time.monotonic()<deadline: time.sleep(.01)
                assert not s.busy and s.diagnostic_state()['counts'][f'wear-{wear}'][label] == n+1, s.log
    assert s.gesture_counts() == before
    restored = emg_web.Session(emg_web.FakeRig(), sets, model_root=root/'models')
    assert restored.diagnostic_state() == s.diagnostic_state()
    assert sum(sum(c.values()) for c in restored.diagnostic_state()['counts'].values()) == 45
    for label,split in [('rest','wear-1'),('fist','wear-1'),('rest','../../test')]:
        try: restored.record(label,1,split,'test',1,'high',0,'diagnostic')
        except ValueError: pass
        else: raise AssertionError('invalid/over-quota recording accepted')
print('PASS: 45 separate diagnostic samples, persisted wears/resume, old data unchanged, invalid and excess writes blocked')

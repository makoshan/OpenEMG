"""Same-donning rest/pinch check must stay out of training, validation, test, and the finished diagnostic set."""
import tempfile
import time
from pathlib import Path
import emg_web

with tempfile.TemporaryDirectory() as temp:
    root = Path(temp)
    sets = {k: {kind: root / p.name for kind, p in v.items()} for k, v in emg_web.SETS.items()}
    s = emg_web.Session(emg_web.FakeRig(), sets, model_root=root / 'models')
    before = s.gesture_counts()
    d = s.pinch_check_action('start')
    assert s.pinch_check_action('start')['id'] == d['id']
    assert s.pinch_check_action('start')['protocol'] == 'pinch-check-v1'
    try:
        s.record('rest', 1, 'wear-1', 'too early', 1, 'high', countdown=0, task='pinch-check')
    except ValueError:
        pass
    else:
        raise AssertionError('recording accepted before the wear was confirmed')
    try:
        s.pinch_check_action('wear', 2)
    except ValueError:
        pass
    else:
        raise AssertionError('a second wear was accepted')
    s.pinch_check_action('wear', 1)
    for n in range(5):
        for label in ('rest', 'pinch'):
            s.record(label, 1, 'wear-1', 'same donning', 1, 'high', countdown=0, task='pinch-check')
            deadline = time.monotonic() + 10
            while s.busy and time.monotonic() < deadline:
                time.sleep(.01)
            assert not s.busy and s.pinch_check_state()['counts']['wear-1'][label] == n + 1, s.log
    assert s.gesture_counts() == before
    assert sum(sum(c.values()) for c in s.diagnostic_state()['counts'].values()) == 0
    restored = emg_web.Session(emg_web.FakeRig(), sets, model_root=root / 'models')
    assert restored.pinch_check_state()['id'] == d['id']
    assert restored.pinch_check_state()['counts']['wear-1'] == {'rest': 5, 'pinch': 5}
    for label, split in [('rub', 'wear-1'), ('rest', 'wear-2'), ('rest', 'wear-1')]:
        try:
            restored.record(label, 1, split, 'blocked', 1, 'high', 0, 'pinch-check')
        except ValueError:
            pass
        else:
            raise AssertionError(f'pinch-check {split}/{label} was accepted')
    assert restored.gesture_counts() == before
print('PASS: 10 same-donning rest/pinch samples, persisted, old sets unchanged, rub and extra writes blocked')

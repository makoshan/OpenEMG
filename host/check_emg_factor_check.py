"""One-factor rest/pinch/rub check stays out of training, validation, test, and the finished diagnostic set."""
import tempfile
import time
from pathlib import Path
import emg_web

with tempfile.TemporaryDirectory() as temp:
    root = Path(temp)
    sets = {k: {kind: root / p.name for kind, p in v.items()} for k, v in emg_web.SETS.items()}
    s = emg_web.Session(emg_web.FakeRig(), sets, model_root=root / 'models')
    before = s.gesture_counts()
    try:
        s.factor_check_action('start', factor='  ')
    except ValueError:
        pass
    else:
        raise AssertionError('blank factor was accepted')
    d = s.factor_check_action('start', factor='位置 B，接触和线缆不动')
    assert s.factor_check_action('start')['id'] == d['id']
    assert d['protocol'] == 'factor-check-v1' and d['factor'] == '位置 B，接触和线缆不动'
    try:
        s.record('rest', 1, 'wear-1', 'too early', 1, 'high', countdown=0, task='factor-check')
    except ValueError:
        pass
    else:
        raise AssertionError('recording accepted before the wear was confirmed')
    try:
        s.factor_check_action('wear', 2)
    except ValueError:
        pass
    else:
        raise AssertionError('a second wear was accepted')
    s.factor_check_action('wear', 1)
    for n in range(5):
        for label in ('rest', 'pinch', 'rub'):
            s.record(label, 1, 'wear-1', 'same donning', 1, 'high', countdown=0, task='factor-check')
            deadline = time.monotonic() + 10
            while s.busy and time.monotonic() < deadline:
                time.sleep(.01)
            assert not s.busy and s.factor_check_state()['counts']['wear-1'][label] == n + 1, s.log
    assert s.gesture_counts() == before
    assert sum(sum(c.values()) for c in s.diagnostic_state()['counts'].values()) == 0
    restored = emg_web.Session(emg_web.FakeRig(), sets, model_root=root / 'models')
    assert restored.factor_check_state()['id'] == d['id']
    assert restored.factor_check_state()['counts']['wear-1'] == {'rest': 5, 'pinch': 5, 'rub': 5}
    for label, split in [('fist', 'wear-1'), ('rest', 'wear-2'), ('rest', 'wear-1')]:
        try:
            restored.record(label, 1, split, 'blocked', 1, 'high', 0, 'factor-check')
        except ValueError:
            pass
        else:
            raise AssertionError(f'factor-check {split}/{label} was accepted')
    assert restored.gesture_counts() == before
    # 单通道松紧档原样传到 take（2026-10-21 复核：戴法校验曾把 wear 形参覆盖成 dict）
    seen = []; real = s.rig.take; s.rig.take = lambda label, wear, *a, **k: (seen.append(wear), real(label, wear, *a, **k))[1]
    s.record('rest', 1, 'train', 'wear arg', 1, 'low', countdown=0)
    deadline = time.monotonic() + 10
    while s.busy and time.monotonic() < deadline: time.sleep(.01)
    assert seen == ['low'], (seen, s.log[-3:])
print('PASS: 15 same-donning rest/pinch/rub samples, one named factor, old sets unchanged')

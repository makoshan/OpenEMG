"""Run: python3 firmware/check_emg_gesture_collection.py; never touches real data."""
import tempfile, time
from pathlib import Path
from emg_web import Session, FakeRig, GESTURES
with tempfile.TemporaryDirectory() as d:
    root = Path(d)
    sets = {'train': {'emg': root/'emg-data'}, 'rewear': {'emg': root/'emg-data-rewear'}}
    s = Session(FakeRig(), sets)
    for split in ('train', 'validation', 'test'):
        for label in GESTURES:
            s.record(label, 1, split, 'test', 1, 'high', countdown=0, task='gestures')
            deadline=time.monotonic()+5
            while s.busy and time.monotonic()<deadline: time.sleep(.01)
            assert not s.busy
            assert s.gesture_counts()[split][label] == 1, s.log
    assert s.counts() == {'train': {}, 'rewear': {}}, 'gesture data leaked into effort data'
    assert Session(FakeRig(), sets).gesture_counts() == s.gesture_counts(), 'restart lost counts'
    for label, split, task in [('light','train','gestures'),('pinch','../bad','gestures'),('pinch','train','effort')]:
        try: s.record(label,1,split,'test',1,'high',countdown=0,task=task)
        except ValueError: pass
        else: raise AssertionError('invalid collection accepted')
print('Gesture collection passed: five labels, three isolated splits, restart counts and refusals')

"""Bound failed attempts across requests, labels, and service reconstruction."""
import tempfile
from pathlib import Path
from unittest.mock import patch
import emg_web

with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    sets = {s: {'emg': root/s} for s in ('train','rewear')}
    def session():
        s = emg_web.Session(emg_web.FakeRig(), sets, model_root=root/'models')
        s.start = lambda name, job: job()
        return s
    def record(s, label='snap', count=10):
        s.record(label,count,'train','test',1,'high',countdown=0,task='gestures')
    s = session()
    with patch.object(s.rig,'take',side_effect=ValueError('signal failed')) as take:
        record(s)
        assert take.call_count == 2, 'must stop at two consecutive failures'
        assert s.issue['stopped'] and s.issue['failures']==2
    s = session()
    with patch.object(s.rig,'take',side_effect=ValueError('signal failed')) as take:
        record(s)
        assert take.call_count==1 and s.issue['failures']==3
        record(s,'rub')
        assert take.call_count==3 and s.issue['limit_reached']
    s = session()
    with patch.object(s.rig,'take',side_effect=AssertionError('budget bypass')):
        record(s,'pinch')
        assert s.issue['limit_reached']
    # A different wear/dataset has its own budget; a success is not a failure.
    with patch.object(s.rig,'take',return_value={}) as take:
        s.record('pinch',1,'validation','test',2,'high',countdown=0,task='gestures')
        assert take.call_count==1 and s.issue is None
    print('PASS: two-failure pause; persistent five-failure cap; cross-label guard; separate wear')

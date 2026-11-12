import json
import tempfile
from pathlib import Path
from unittest.mock import patch
import emg_web
import emg_rehearsal as protocol
import usb_emg

with tempfile.TemporaryDirectory() as tmp:
    root=Path(tmp)
    s=emg_web.Session(emg_web.FakeRig(),{k:{'emg':root/k} for k in ('train','rewear')},model_root=root/'models')
    s.start=lambda name,job:job()
    def rejected(fn):
        try:fn()
        except ValueError:return
        raise AssertionError('invalid action accepted')
    rejected(lambda:s.rehearsal_start({'participant':'Mako','placement':'A','battery_confirmed':False}))
    assert not s.rehearsal_root().exists()
    rejected(lambda:s.record('rest',1,'wear-1','',1,'high',0,'rehearsal'))
    meta=s.rehearsal_start({'participant':'Mako','placement':'A direction recorded','battery_confirmed':True})
    assert meta['training_eligible'] is False
    assert s.rehearsal_start({})['id']==meta['id'], 'resume must preserve original conditions'
    rejected(lambda:s.record('rub',1,'wear-1','',1,'high',0,'rehearsal'))
    with patch.object(emg_web.time,'sleep'):
        for label in protocol.LABELS:
            s.record(label,1,'wear-1','',1,'high',0,'rehearsal')
            rejected(lambda:s.record(label,1,'wear-1','',1,'high',0,'rehearsal'))
    done=protocol.state(s.rehearsal_root())
    assert done['complete'] and done['review_required'] and not done['training_eligible']
    assert all(n==0 for counts in s.gesture_counts().values() for n in counts.values())
    assert len(list(s.rehearsal_root().rglob('*.npz')))==5
    cue={'phase_shown_ms':{'relax':1700000000000,'action':1700000000400,'release':1700000001400},'shown_ms':1700000000400}
    result=usb_emg.align_capture({'recording_ack_host_ns':1700000000000000000},cue=cue)
    assert result['cue_sample_index_estimate']==400 and not result['sample_alignment_verified']
    assert result['cue_phase_shown_ms']==cue['phase_shown_ms']
print('PASS: explicit setup, resume, order, duplicate guard, five saved separately, review gate, cue phases')

# Interactive fake must leave time for the real three-phase prompt, unlike fast unit fixtures.
import threading,time
with tempfile.TemporaryDirectory() as tmp:
    cue={}
    def started(timing):
        def phases():
            cue['phase_shown_ms']={'relax':int(time.time()*1000)}
            time.sleep(.4)
            cue['shown_ms']=int(time.time()*1000)
            cue['phase_shown_ms']['action']=cue['shown_ms']
            time.sleep(1)
            cue['phase_shown_ms']['release']=int(time.time()*1000)
        threading.Thread(target=phases).start()
    t=time.monotonic()
    emg_web.FakeRig(realtime=True).take('pinch','high',Path(tmp),'fake preflight',1,on_started=started,cue=cue,review_smr=True)
    assert time.monotonic()-t>=1.9
    saved=json.loads(next(Path(tmp).rglob('*.json')).read_text())
    assert set(saved['cue_phase_shown_ms'])=={'relax','action','release'}
    assert saved['training_eligible'] is False
print('PASS: interactive fake lasts 2 s and saves three cue phases plus review metadata')

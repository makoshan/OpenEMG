import tempfile,time,json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import emg_web,usb_emg

with tempfile.TemporaryDirectory() as tmp:
 root=Path(tmp)
 rig=emg_web.Rig();rig.conn=object();rig.kind='emg';rig.device=SimpleNamespace(serial_number='TEST')
 err=usb_emg.RejectedTake('SMR rejected','EMG 1000 2000 0 1000 1003 0',b'raw')
 with patch.object(rig,'_stream'),patch.object(usb_emg,'read_take',side_effect=err):
  try:rig.take('snap','high',root/'validation','session',2)
  except usb_emg.RejectedTake:pass
 assert Path(err.saved_path).read_bytes()==b'raw'
 assert json.loads(Path(err.saved_path).with_suffix('.json').read_text())['status']=='rejected'
 assert not list((root/'validation').glob('*/*.npz'))
 class RejectRig:
  kind='emg'
  calls=0
  accept=False
  def take(self,*args):
   self.calls+=1
   if not self.accept:raise ValueError('low frequency')
   return {}
 r=RejectRig();sets={'train':{'emg':root/'effort'},'rewear':{'emg':root/'rewear'}}
 s=emg_web.Session(r,sets)
 def run(count):
  s.record('snap',count,'validation','test',2,'high',countdown=0,task='gestures')
  deadline=time.monotonic()+3
  while s.busy and time.monotonic()<deadline:time.sleep(.01)
  assert not s.busy
 run(9);assert r.calls==3 and s.issue['stopped']
 s=emg_web.Session(r,sets);assert s.issue['stopped'], 'restart lost stop reason'
 run(9);assert r.calls==4, 'retry must be one sample'
 r.accept=True;run(9);assert r.calls==5 and s.issue is None
print('PASS: rejected bytes isolated, 3 failures stop, persisted notice, one-shot retry, successful recovery')

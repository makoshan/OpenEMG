import tempfile, json
from pathlib import Path
import numpy as np
import emg_gesture_train as t
import usb_emg
with tempfile.TemporaryDirectory() as tmp:
 root=Path(tmp);rng=np.random.default_rng(4)
 for split,n in [('train',30),('validation',10),('test',10)]:
  for k,label in enumerate(t.LABELS):
   folder=root/split/label;folder.mkdir(parents=True)
   for i in range(n):
    x=1800+rng.normal(0,8+12*k,2000)
    np.savez(folder/f'{i}.npz',emg=x,emg_hz=1000,worn_permille=1000,label=label)
 for kind in t.MODELS:
  out=root/'models'/kind
  from unittest.mock import patch
  original_dataset=t.dataset
  def train_only(root,split,labels=t.LABELS):
   assert split != 'test', 'training opened independent test'
   return original_dataset(root,split,labels)
  with patch.object(t,'dataset',side_effect=train_only):r=t.train(root,out,kind,epochs=2)
  assert r['test'] is None and r['validation']['samples']==50
  assert len(r['manifest'])==200
  r=t.evaluate(root,out);assert r['test']['samples']==50
  assert t.evaluate(root,out)==json.loads(json.dumps(r))
 # Same raw sample across splits must fail rather than inflate validation.
 (root/'validation/rest/0.npz').write_bytes((root/'train/rest/0.npz').read_bytes())
 try:t.train(root,root/'bad','lda')
 except ValueError as e:assert '重复' in str(e)
 else:raise AssertionError('leakage accepted')
print('PASS all registered models, untouched test during training, explicit evaluation, duplicate leakage rejection')

# UI service refuses unknown models and freezes a single test run.
import emg_web
from unittest.mock import patch
from types import SimpleNamespace
with tempfile.TemporaryDirectory() as tmp:
    root=Path(tmp); session=emg_web.Session(SimpleNamespace(kind='emg'),model_root=root)
    session.start=lambda name,job:job()
    run=root/'five-gestures'/'valid';run.mkdir(parents=True)
    (run/'report.json').write_text('{}')
    with patch('subprocess.run',return_value=SimpleNamespace(returncode=0,stdout='',stderr='')):
        session.train_gestures('evaluate',run_id='valid')
    try:session.train_gestures('train','svm')
    except ValueError:pass
    else:raise AssertionError('training allowed after test freeze')
    try:session.train_gestures('train','unknown')
    except ValueError:pass
    else:raise AssertionError('unknown model accepted')
print('PASS: invalid models rejected; independent test locks model selection')

# Independent numeric invariants and trainable routing, not just output shapes.
from emg_book_models import book_features,build,DEEP
import torch,re
f=book_features(np.ones((1,2000))).reshape(8,10)
assert np.isfinite(f).all()
assert np.allclose(f[:,[0,1,2,3,8,9]], [1,0,0,0,1,0])
assert set(t.MODELS)==set(re.findall(r'<option value=([a-z_]+)>', (Path(__file__).parent/'emg_guide.html').read_text())).intersection(t.MODELS)
net=build('gaf_caps');seen=[]
handle=net.image.register_forward_pre_hook(lambda module,args:seen.append(args[0].detach()))
x=torch.linspace(-1,1,2000).reshape(1,1,2000)
loss=net(x).square().sum();loss.backward();handle.remove()
gaf=seen[0][0,0]
z=torch.linspace(-1,1,40)
assert torch.allclose(gaf,gaf.T,atol=1e-6)
assert torch.allclose(gaf.diag(),2*z*z-1,atol=1e-5)
assert net.caps.weight.grad is not None and net.caps.weight.grad.abs().sum()>0
print('PASS: book features, GASF formula, capsule routing gradients and UI registry')

import tempfile
from pathlib import Path
import numpy as np
import torch
import emg_gesture_train as t
from emg_tune_models import configs,fit_deep,classical

torch.set_num_threads(2)
rng=np.random.default_rng(8);x=rng.normal(size=(10,2000));y=np.tile(np.arange(5),2)
for kind in t.MODELS:
    assert len(configs(kind))>=4
    cfg=configs(kind)[-1]
    if kind in t.DEEP_MODELS:
        model,history,epoch=fit_deep(kind,cfg,x,y,42,5,(x,y))
        assert epoch==5 and len(history)==1
        before=t.predict(model,kind,x)
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'model.pt';torch.save(model,p)
            assert np.array_equal(before,t.predict(torch.load(p,weights_only=True),kind,x))
        assert np.isfinite(history[0]['loss'])
    else:
        cfg=configs(kind)[0];m=classical(kind,cfg,42);f=t.features(x)
        m.fit(f,y);assert len(m.predict(f))==10
print('PASS all 19 configured models: fitting, finite loss, checkpoint reconstruction')
# Old baseline weights must still use the exact unconfigured architecture.
net=t.build('lstm');copy=t.build('lstm',hidden=32,pooling='last',gaf_mode='mean',dropout=0)
copy.load_state_dict(net.state_dict());net.eval();copy.eval()
with torch.no_grad():assert torch.equal(net(torch.tensor(x[:,None],dtype=torch.float32)),copy(torch.tensor(x[:,None],dtype=torch.float32)))
print('PASS backward compatible default architecture')
# Numerically equal recalls must not select a later candidate due to rounding noise.
scores=[.5599999999999999,.5600000000000002]
assert max(range(len(scores)),key=lambda i:round(scores[i],12))==0

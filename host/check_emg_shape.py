"""Run with the EMG training environment; no real data or device required."""
import pickle
import numpy as np
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC
import emg_gesture_train as t
x=np.random.default_rng(4).normal(size=(10,2000));y=np.arange(10)%5
f=t.shape_features(x);g=t.shape_features(x*3)
assert f.shape==(10,44) and np.allclose(f[:,:40],g[:,:40])
assert np.isfinite(t.shape_features(np.zeros((1,2000)))).all()
m={'features':'rms-shape-v1','estimator':make_pipeline(StandardScaler(),SVC(C=10)).fit(f,y)}
assert np.array_equal(t.predict(m,'svm',x),t.predict(pickle.loads(pickle.dumps(m)),'svm',x))
a=[{'file':'train/a','sha256':'a'},{'file':'validation/b','sha256':'b'}]
assert t.dataset_id(a)==t.dataset_id(a[::-1])
assert t.dataset_id(a)!=t.dataset_id(a+[{'file':'train/c','sha256':'c'}])
print('PASS shape gain invariance, zero input, checkpoint prediction, dataset identities')

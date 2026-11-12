"""手势管线：空模型必失败、特征维度、能量门默认关闭、假服务能导出黑匣子。"""
import tempfile
from pathlib import Path

import numpy as np

import check_dataset
import check_studio_api as api
import dataset as dsmod
import device_desc
import gesture_pipe
import trainer

HERE = Path(__file__).resolve().parent


def must_fail(fn, status=None):
    try:
        fn()
    except Exception as e:
        if status is not None and getattr(e, 'code', None) not in (None, status):
            # HTTP 检查在下面单独做
            pass
        return
    raise AssertionError('本应失败')


def main():
    must_fail(lambda: trainer.fit_lda(np.zeros((0, 40)), np.array([])))
    w = np.zeros((2000, 8))
    assert trainer.features(w, 2000).shape == (40,)
    assert gesture_pipe.vector(w, 2000, 'hudgins', trainer.features).shape == (48,)
    assert gesture_pipe.vector(w, 2000, 'combined', trainer.features).shape == (88,)
    must_fail(lambda: gesture_pipe.vector(w, 2000, 'nope', trainer.features))
    gate = gesture_pipe.EnergyGate(0, 'rest')
    assert gate.apply('fist', 1) == ('fist', False)
    gate.set(200, 'mouse_rest')
    assert gate.apply('fist', 50) == ('mouse_rest', True)
    assert gate.apply('mouse_rest', 1) == ('mouse_rest', False)
    must_fail(lambda: gate.set(-1, 'rest'))
    box = gesture_pipe.Blackbox(2000, 8)
    must_fail(lambda: box.save('/tmp/empty-box.npz'))
    box.push_batch(np.zeros((400, 8)))
    with tempfile.TemporaryDirectory() as td:
        p = box.save(Path(td) / 'box.npz')
        with np.load(p) as z:
            assert 'emg_uv' in z.files
        root = Path(td)
        fs = 2000
        desc = device_desc.load('fake')
        studio = root / 'studio'
        check_dataset.synth_project(studio, desc, fs=fs, sessions=3, per=6, seed=1)
        ds = dsmod.build(studio, 'synth', {'rest': 'rest', 'pinch': 'pinch', 'fist': 'fist'})
        dsmod.save(ds, studio)
        recs = dsmod.records(ds, studio, 'train')
        run = gesture_pipe.few_shot(recs, fs, 'combined', 1, studio / 'models', trainer.features)
        with np.load(run['artifact']) as z:
            assert z['mu'].shape[1] == 88
        bands = trainer.train(ds, studio, desc, trainer='lda', seed=0, out_root=studio / 'models', feature_mode='bands5', progress=lambda *_: None)
        with np.load(bands['artifact']) as z:
            assert z['mu'].shape == (3, 40)
        must_fail(lambda: trainer.train(ds, studio, desc, trainer='cnn', seed=0, out_root=studio / 'models', feature_mode='combined'))
        with api.Server('--device', 'fake', '--data', td) as srv:
            st, state = api.call(srv.port, '/api/gesture/state')
            assert st == 200 and state['min_rms_uv'] == 0, state
            st, _ = api.call(srv.port, '/api/gesture/gate', {'min_rms_uv': -5}, 'PUT')
            assert st == 400
            st, decided = api.call(srv.port, '/api/gesture/decide', {'label': 'fist', 'rms_uv': 10}, 'POST')
            assert st == 200 and decided['blocked'] is False
            api.call(srv.port, '/api/gesture/gate', {'min_rms_uv': 200, 'rest_label': 'rest'}, 'PUT')
            st, decided = api.call(srv.port, '/api/gesture/decide', {'label': 'fist', 'rms_uv': 10}, 'POST')
            assert decided['label'] == 'rest' and decided['blocked'] is True
            st, dump = api.call(srv.port, '/api/gesture/blackbox/dump', {}, 'POST')
            assert st == 409, dump
            st, few = api.call(srv.port, '/api/gesture/fewshot', {'dataset': 'synth', 'feature_mode': 'hudgins', 'k': 1}, 'POST')
            assert st == 200 and few['feature_mode'] == 'hudgins', few
            st, bad = api.call(srv.port, '/api/gesture/fewshot', {'dataset': 'synth', 'k': 99}, 'POST')
            assert st == 400, bad
    print('手势管线检查通过')


if __name__ == '__main__':
    main()

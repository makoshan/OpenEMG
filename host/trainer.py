"""统一训练接口（EMG_STUDIO_V2_PLAN 附录 D）：

    run = train(ds, root, desc, trainer='lda', seed=0, out_root=<工程>/models/emg, progress=print)
    freeze(out_root, run['id'])

- lda：wl8_train 的 5 频段 log 功率特征（去 50 Hz 格栅）+ 收缩 LDA，推广到任意通道数与采样率。
- cnn：包 emg_wl8_cnn.run（要 torch）；没有 torch 时报 ImportError，不假装训过。
- 三集按会话划分来自数据集文件；test 集不存在时 metrics.test = None，页面显示「无独立测试」。
- 复现：同数据集（指纹）同 seed 两次 metrics 相同。
"""
import json
import time
from pathlib import Path

import numpy as np
from scipy.signal import welch

import dataset as dsmod

try:  # cnn 训练器需要 torch（EMGPY 环境）；PY 环境没有也能用 lda
    import torch
    import emg_wl8_cnn
    from emg_gni_train import Net as CnnNet
except ImportError:
    torch = emg_wl8_cnn = CnnNet = None

BANDS = [(20, 45), (55, 95), (105, 145), (155, 245), (255, 445)]
SHRINK = .5
FEATURES_VERSION = 'bands5-v1'
TRAINERS = ('lda', 'cnn')
MIN_PER_CLASS = {'lda': 5, 'cnn': 20}


def features(e, fs):
    """(n, ch) µV → ch × 5 维：每路 5 个频段的 log 平均功率；工频格（50 Hz 倍频 ±4 Hz）和 20 Hz 以下不算。
    fs=2000、8 路时与 wl8_train.features 逐值相同（频段在前、通道在后）。"""
    e = np.asarray(e, float)
    f, P = welch(e - e.mean(0), fs, nperseg=min(512, len(e)), axis=0)
    ok = f >= 20
    for k in range(1, int(fs / 2 / 50) + 1):
        ok &= np.abs(f - 50 * k) > 4
    rows = []
    for lo, hi in BANDS:
        sel = ok & (f >= lo) & (f < min(hi, fs / 2))
        rows.append(np.log(P[sel].mean(0) + 1e-9) if sel.any() else np.full(e.shape[1], np.log(1e-9)))
    return np.array(rows).ravel()


def windows(uv, fs, window_ms, stride_ms):
    w, s = int(fs * window_ms / 1000), int(fs * stride_ms / 1000)
    if len(uv) < w:
        return []
    return [uv[i:i + w] for i in range(0, len(uv) - w + 1, s)]


def fit_lda(X, y, shrink=SHRINK):
    X, y = np.asarray(X, float), np.asarray(y)
    if X.ndim != 2 or len(y) == 0 or X.shape[0] != len(y):
        raise ValueError('fit_lda 需要至少一个窗口')
    cs = sorted(set(y))
    mu = np.array([X[y == c].mean(0) for c in cs])
    C = sum(((X[y == c] - mu[i]).T @ (X[y == c] - mu[i])) for i, c in enumerate(cs)) / len(y)
    C = (1 - shrink) * C + shrink * np.eye(len(C)) * np.trace(C) / len(C)
    return dict(classes=cs, mu=mu, sinv=np.linalg.inv(C))


def predict_lda(m, X):
    d = np.array([np.einsum('ij,jk,ik->i', X - u, m['sinv'], X - u) for u in m['mu']]).T
    return np.array(m['classes'])[(-.5 * d).argmax(1)]


def balanced(yt, yp):
    cs = sorted(set(yt))
    return float(np.mean([np.mean(yp[yt == c] == c) for c in cs])) if cs else float('nan')


def confusion(yt, yp, labels):
    return {'rows': list(labels), 'matrix': [[int(((yt == a) & (yp == b)).sum()) for b in labels] for a in labels]}


def _xy(recs, fs, window_ms, stride_ms, feature_mode='bands5'):
    X, y, sess = [], [], []
    for uv, lab, s in recs:
        for w in windows(uv, fs, window_ms, stride_ms):
            if feature_mode == 'bands5':
                vec = features(w, fs)
            else:
                import gesture_pipe  # 默认 bands5 不走这里，避免和手势目录循环导入
                vec = gesture_pipe.vector(w, fs, feature_mode, features)
            X.append(vec); y.append(lab); sess.append(s)
    return np.array(X), np.array(y), sess


def _metrics(yt, yp, labels):
    return {'balanced_acc': round(balanced(yt, yp), 4), 'n': int(len(yt)),
            'per_class': {c: round(float(np.mean(yp[yt == c] == c)), 4) for c in labels if (yt == c).any()},
            'confusion': confusion(yt, yp, labels)}


def train(ds, root, desc, *, trainer='lda', seed=0, out_root, progress=print, window_ms=1000, stride_ms=500, epochs=40, min_per_class=None, feature_mode='bands5'):
    if trainer not in TRAINERS:
        raise ValueError(f'trainer 必须是 {TRAINERS}')
    if feature_mode != 'bands5':
        import gesture_pipe  # 同上：只有显式换特征才加载
        if feature_mode not in gesture_pipe.FEATURE_MODES:
            raise ValueError(f'feature_mode 必须是 {gesture_pipe.FEATURE_MODES}')
        if trainer != 'lda':
            raise ValueError('cnn 只用原始窗，不接受特征模式')
    dsmod.validate(ds, root)
    t0 = time.time()
    fs = desc.fs_Hz
    recs = {s: dsmod.records(ds, root, s) for s in dsmod.SPLITS}
    labels = sorted({lab for _, lab, _ in recs['train']})
    counts = {s: {l: sum(1 for _, lab, _ in recs[s] if lab == l) for l in labels} for s in dsmod.SPLITS}
    need = MIN_PER_CLASS[trainer] if min_per_class is None else int(min_per_class)
    short = [l for l in labels if counts['train'][l] < need]
    if short:
        raise ValueError(f"训练集每类至少 {need} 条（{trainer}），不足：{short}")
    # 独立测试集只能来自没参与训练的会话——数据集校验已保证，这里再核一次
    train_sess = {s for _, _, s in recs['train']}
    if any(s in train_sess for _, _, s in recs['test']):
        raise ValueError('test 集会话与 train 重叠')
    run = {'id': None, 'trainer': trainer, 'trainer_version': FEATURES_VERSION if trainer == 'lda' else 'emg_wl8_cnn',
           'dataset': {'name': ds['name'], 'fingerprint': dsmod.fingerprint(ds), 'gate_version': ds.get('gate_version')},
           'device_id': desc.id, 'channels_used': list(range(desc.n_channels)), 'fs_Hz': fs, 'window_ms': window_ms, 'stride_ms': stride_ms,
           'features_version': FEATURES_VERSION if feature_mode == 'bands5' else f'{feature_mode}-v1',
           'feature_mode': feature_mode, 'seed': seed, 'labels': labels, 'counts': counts,
           'started': time.strftime('%Y-%m-%dT%H:%M:%S'), 'metrics': {}}
    progress({'stage': 'data', 'counts': counts})
    if trainer == 'lda':
        X, y, _ = _xy(recs['train'], fs, window_ms, stride_ms, feature_mode)
        model = fit_lda(X, y)
        run['metrics']['train'] = _metrics(y, predict_lda(model, X), labels)
        for s in ('validation', 'test'):
            if recs[s]:
                Xs, ys, _ = _xy(recs[s], fs, window_ms, stride_ms, feature_mode)
                run['metrics'][s] = _metrics(ys, predict_lda(model, Xs), labels) if len(ys) else None
            else:
                run['metrics'][s] = None
        artifact = {'kind': 'lda-npz', 'classes': np.array(model['classes']), 'mu': model['mu'], 'sinv': model['sinv'],
                    'bands': np.array(BANDS), 'fs': fs, 'shrink': SHRINK, 'window_ms': window_ms, 'n_channels': desc.n_channels}
    else:
        artifact = _train_cnn(recs, labels, desc, run, seed, epochs, progress)
    run['ended'] = time.strftime('%Y-%m-%dT%H:%M:%S')
    run['seconds'] = round(time.time() - t0, 2)
    if run['metrics'].get('test') is None:
        run['note'] = '无独立测试：test 集为空或不是独立会话，不报测试分数'
    base = f"{time.strftime('%Y-%m-%dT%H-%M-%S')}_{trainer}_{ds['name']}"
    run['id'], k = base, 1
    while (Path(out_root) / run['id']).exists():        # 同一秒内多次训练不覆盖
        run['id'], k = f'{base}-{k}', k + 1
    d = Path(out_root) / run['id']
    d.mkdir(parents=True)
    np.savez(d / 'model.npz', **{k: v for k, v in artifact.items() if k != 'kind'}, kind=artifact['kind'])
    run['artifact'] = str(d / 'model.npz')
    (d / 'run.json').write_text(json.dumps(run, ensure_ascii=False, indent=1) + '\n')
    progress({'stage': 'done', 'id': run['id'], 'metrics': {k: (v or {}).get('balanced_acc') for k, v in run['metrics'].items()}})
    return run


def _train_cnn(recs, labels, desc, run, seed, epochs, progress):
    """包 emg_wl8_cnn：1 s 窗 → 1 kHz → 0.4 s 随机裁剪。该网络按 2000 Hz 设计，别的采样率先用 lda。"""
    if torch is None:
        raise ImportError('cnn 训练器需要 torch（EMGPY 环境）')
    if desc.fs_Hz != 2000:
        raise ValueError('cnn 训练器目前只支持 2000 Hz 设备')
    fs = desc.fs_Hz
    rng = np.random.default_rng(seed)
    torch.manual_seed(seed)
    Xtr, ytr, _ = _xy_raw(recs['train'], fs, run['window_ms'], run['stride_ms'])
    X, _ = emg_wl8_cnn.prepare([(l, x) for x, l in zip(Xtr, ytr)], run['channels_used'])
    scale = emg_wl8_cnn.scale_from(X)
    X = X / scale[None, :, None]
    model = CnnNet(len(run['channels_used']), len(labels))
    emg_wl8_cnn.fit(model, X, np.array([labels.index(v) for v in ytr]), epochs, 1e-3, None, rng)
    for s in dsmod.SPLITS:
        if not recs[s]:
            run['metrics'][s] = None
            continue
        Xs, ys, _ = _xy_raw(recs[s], fs, run['window_ms'], run['stride_ms'])
        Xs2, _ = emg_wl8_cnn.prepare([(l, x) for x, l in zip(Xs, ys)], run['channels_used'])
        pred = np.array(labels)[emg_wl8_cnn.predict(model, Xs2 / scale[None, :, None], None)]
        run['metrics'][s] = _metrics(np.array(ys), pred, labels)
        progress({'stage': s, 'balanced_acc': run['metrics'][s]['balanced_acc']})
    state = {k: v.cpu().numpy() for k, v in model.state_dict().items()}
    return {'kind': 'cnn-state', 'scale': scale, 'labels': np.array(labels), **{f'state.{k}': v for k, v in state.items()}}


def _xy_raw(recs, fs, window_ms, stride_ms):
    X, y, sess = [], [], []
    for uv, lab, s in recs:
        for w in windows(uv, fs, window_ms, stride_ms):
            X.append(w); y.append(lab); sess.append(s)
    return X, np.array(y), sess


def runs(out_root):
    out = []
    for p in sorted(Path(out_root).glob('*/run.json')):
        r = json.loads(p.read_text())
        out.append({k: r.get(k) for k in ('id', 'trainer', 'dataset', 'device_id', 'labels', 'started', 'seconds', 'note')}
                   | {'metrics': {k: (v or {}).get('balanced_acc') for k, v in r.get('metrics', {}).items()}})
    return out


def freeze(out_root, run_id):
    d = Path(out_root) / run_id
    if not (d / 'run.json').exists():
        raise ValueError(f'没有 run {run_id}')
    r = json.loads((d / 'run.json').read_text())
    prod = {'run_id': run_id, 'frozen': time.strftime('%Y-%m-%dT%H:%M:%S'), 'device_id': r['device_id'], 'labels': r['labels'],
            'artifact': r['artifact'], 'dataset': r['dataset'], 'metrics': {k: (v or {}).get('balanced_acc') for k, v in r['metrics'].items()}}
    (Path(out_root) / 'production.json').write_text(json.dumps(prod, ensure_ascii=False, indent=1) + '\n')
    return prod


def production(out_root):
    p = Path(out_root) / 'production.json'
    return json.loads(p.read_text()) if p.exists() else None

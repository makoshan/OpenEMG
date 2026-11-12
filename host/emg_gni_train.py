"""A small 1D-CNN for 4-channel wrist gestures, trained on Meta's discrete_gestures windows.

Input: windows from emg_gni_prep.py (1 kHz, 16 channels stored, float16). This keeps a channel
subset, crops a 0.4 s window around each press (random +-50 ms jitter while training), and reports
three numbers for the test users, because only the last one is what a wristband would ship:

  generic     trained on the train users, applied to unseen test users with no calibration
  own-only    trained from scratch on each test user's calibration slice only
  calibrated  the generic model fine-tuned on that same calibration slice

Calibration slice = the first CAL of each gesture's windows in time (about a minute or two of
presses), test = the last 50% of each gesture's windows. Never interleaved.

The network is ~55k parameters: small enough for int8 on the nRF52840 in the watch.

    python emg_gni_train.py --data emg-public/gni-win --channels 0,4,8,12
    python emg_gni_train.py --check          # synthetic smoke test, CPU, seconds
"""
import argparse
import json
import time
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn

CROP, PRE_IDX = 400, 100          # stored windows start 0.25 s before the press; crop starts 0.15 s before
CLASSES = ('rest', 'index_press', 'middle_press', 'thumb_click', 'thumb_down', 'thumb_in', 'thumb_out', 'thumb_up')
CAL, TEST = .2, .5


class Net(nn.Module):
    def __init__(self, ch, n=len(CLASSES)):
        super().__init__()
        blk = lambda i, o, k: nn.Sequential(nn.Conv1d(i, o, k, 2, k // 2), nn.BatchNorm1d(o), nn.ReLU())
        self.f = nn.Sequential(blk(ch, 32, 9), blk(32, 64, 7), blk(64, 64, 5), blk(64, 64, 5))
        self.head = nn.Linear(64, n)

    def forward(self, x):                     # x: (B, ch, 400)
        return self.head(self.f(x).mean(-1))


def load(folder, channels, classes=CLASSES):
    """classes: names to keep (default all); windows of other classes are dropped, labels remapped 0..k-1."""
    remap = np.full(len(CLASSES), -1); remap[[CLASSES.index(c) for c in classes]] = np.arange(len(classes))
    users = []
    for f in sorted(Path(folder).glob('*.npz')):
        z = np.load(f, allow_pickle=False)
        keep = remap[z['y']] >= 0
        X = z['X'][keep][:, :, channels].astype(np.float32)       # (n, 600, ch)
        # Per-user scale from the EARLIEST `CAL` fraction of windows only, labels unseen: what a
        # wristband can do by itself in its first minute. Never from test-time windows and never
        # from rest labels -- the earlier version did both, and a change to test data alone moved
        # calibration inputs (review 2026-09-24 reproduced it: 0.999999 -> 0.019802).
        t = z['t'][keep]
        early = np.argsort(t)[:max(1, int(len(t) * CAL))]
        scale = np.median(np.abs(X[early]), axis=(0, 1)) + 1e-6
        users.append({'name': f.stem, 'split': str(z['split']), 'X': (X / scale).transpose(0, 2, 1), 'y': remap[z['y'][keep]].astype(np.int64), 't': t})
    return users


def split_user(u):
    """Per class in time order: first CAL -> calibration, last TEST -> test."""
    cal, te = [], []
    for c in np.unique(u['y']):
        idx = np.flatnonzero(u['y'] == c); idx = idx[np.argsort(u['t'][idx])]
        cal += list(idx[:max(1, int(len(idx) * CAL))]); te += list(idx[int(len(idx) * (1 - TEST)):])
    return np.array(cal), np.array(te)


def crops(X, jitter, rng):
    if not jitter:
        return X[:, :, PRE_IDX:PRE_IDX + CROP]
    s = rng.integers(PRE_IDX - 50, PRE_IDX + 51, len(X))
    return np.stack([x[:, a:a + CROP] for x, a in zip(X, s)])


def fit(model, X, y, epochs, lr, dev, rng, Xv=None, yv=None, batch=256):
    k = model.head.out_features
    w = torch.tensor(1 / np.maximum(np.bincount(y, minlength=k), 1), dtype=torch.float32, device=dev)
    loss_f = nn.CrossEntropyLoss(weight=w / w.sum() * k)
    opt = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-3)
    sched = torch.optim.lr_scheduler.OneCycleLR(opt, lr, total_steps=epochs * max(1, -(-len(X) // batch)))
    best, best_state = -1, None
    for ep in range(epochs):
        model.train(); order = rng.permutation(len(X))
        for i in range(0, len(X), batch):
            b = order[i:i + batch]
            xb = torch.tensor(crops(X[b], True, rng), device=dev); yb = torch.tensor(y[b], device=dev)
            xb = xb * torch.exp(torch.randn(xb.shape[0], xb.shape[1], 1, device=dev) * .15)   # electrode-gain jitter
            opt.zero_grad(); loss_f(model(xb), yb).backward(); opt.step(); sched.step()
        if Xv is not None:
            acc = balanced(model, Xv, yv, dev)
            if acc > best: best, best_state = acc, {k: v.clone() for k, v in model.state_dict().items()}
    if best_state: model.load_state_dict(best_state)
    return best


@torch.no_grad()
def predict(model, X, dev):
    model.eval()
    return np.concatenate([model(torch.tensor(crops(X[i:i + 1024], False, None), device=dev)).argmax(1).cpu().numpy() for i in range(0, len(X), 1024)])


def balanced(model, X, y, dev):
    p = predict(model, X, dev)
    return float(np.mean([np.mean(p[y == c] == c) for c in np.unique(y)]))


def run(folder, channels, epochs=30, dev=None, seed=0, save=None, classes=CLASSES):
    dev = dev or ('mps' if torch.backends.mps.is_available() else 'cpu')
    rng = np.random.default_rng(seed); torch.manual_seed(seed)
    users = load(folder, channels, classes)
    tr = [u for u in users if u['split'] == 'train']; va = [u for u in users if u['split'] == 'val']; te = [u for u in users if u['split'] == 'test']
    cat = lambda us, k: np.concatenate([u[k] for u in us])
    t0 = time.time()
    generic = Net(len(channels), len(classes)).to(dev)
    best_val = fit(generic, cat(tr, 'X'), cat(tr, 'y'), epochs, 3e-3, dev, rng, cat(va, 'X') if va else None, cat(va, 'y') if va else None)
    if save:
        # Generic weights + a few test windows with their logits: emg_cnn_export.py turns these into the C header and checks parity.
        probe = te[0]['X'][:4, :, PRE_IDX:PRE_IDX + CROP].astype(np.float32)
        generic.eval()
        with torch.no_grad(): logits = generic(torch.tensor(probe, device=dev)).cpu().numpy()
        torch.save({'state': {k: v.cpu() for k, v in generic.state_dict().items()}, 'channels': channels, 'classes': list(classes),
                    'probe': probe, 'probe_logits': logits, 'probe_y': te[0]['y'][:4]}, save)
    rows = []
    for u in te:
        cal, test = split_user(u)
        Xc, yc, Xt, yt = u['X'][cal], u['y'][cal], u['X'][test], u['y'][test]
        g = balanced(generic, Xt, yt, dev)
        own = Net(len(channels), len(classes)).to(dev); fit(own, Xc, yc, 60, 3e-3, dev, rng)
        tuned = Net(len(channels), len(classes)).to(dev); tuned.load_state_dict(generic.state_dict()); fit(tuned, Xc, yc, 30, 1e-3, dev, rng)
        rows.append({'user': u['name'], 'cal_windows': int(len(cal)), 'test_windows': int(len(test)),
                     'generic': round(g, 3), 'own_only': round(balanced(own, Xt, yt, dev), 3), 'calibrated': round(balanced(tuned, Xt, yt, dev), 3)})
        print(rows[-1], flush=True)
    mean = {k: round(float(np.mean([r[k] for r in rows])), 3) for k in ('generic', 'own_only', 'calibrated')}
    return {'channels': channels, 'classes': list(classes), 'users': {'train': len(tr), 'val': len(va), 'test': len(te)}, 'val_best': round(best_val, 3),
            'params': sum(p.numel() for p in generic.parameters()), 'mean': mean, 'per_user': rows,
            'seconds': round(time.time() - t0), 'device': dev, 'chance': round(1 / len(classes), 3)}


def check():
    """Synthetic users: each gesture lights its own channel pattern with a per-user gain. The
    calibrated model must beat chance by a wide margin; shuffled training labels must not."""
    import tempfile
    rng = np.random.default_rng(3)
    pat = rng.uniform(.5, 3, (len(CLASSES), 16)); pat[0] = 0
    with tempfile.TemporaryDirectory() as tmp:
        for k, split in enumerate(['train'] * 6 + ['val'] + ['test'] * 2):
            gain = rng.uniform(.6, 1.6, 16); n = 400
            y = rng.integers(0, len(CLASSES), n).astype(np.int8)
            X = rng.normal(0, 1, (n, 600, 16))
            for i in range(n):
                X[i, 250:450] *= 1 + pat[y[i]] * gain
            np.savez(Path(tmp) / f'u{k}.npz', X=X.astype(np.float16), y=y, t=np.arange(n, dtype=float), split=split)
        r = run(tmp, [0, 4, 8, 12], epochs=6, dev='cpu')
    assert r['mean']['calibrated'] > .6 and r['mean']['generic'] > .4, r['mean']
    # Must fail: changing test-time windows only must not move a calibration window's input.
    with tempfile.TemporaryDirectory() as tmp:
        X = np.ones((10, 600, 16), np.float16); y = np.zeros(10, np.int8); t = np.arange(10, dtype=float)
        np.savez(Path(tmp) / 'u.npz', X=X, y=y, t=t, split='test'); a = load(tmp, [0])[0]['X'][0, 0, 0]
        X[5:] = 100; np.savez(Path(tmp) / 'u.npz', X=X, y=y, t=t, split='test'); b = load(tmp, [0])[0]['X'][0, 0, 0]
        assert a == b, f'test windows leaked into calibration normalisation: {a} -> {b}'
    print('train check passed', r['mean'], r['params'], 'params')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--data'); p.add_argument('--channels', default='0,4,8,12'); p.add_argument('--epochs', type=int, default=30)
    p.add_argument('--out'); p.add_argument('--check', action='store_true')
    p.add_argument('--classes', default=','.join(CLASSES), help='comma list of class names to keep, e.g. rest,index_press,thumb_click,thumb_up')
    p.add_argument('--save', help='write generic weights + probe windows (.pt) for emg_cnn_export.py')
    p.add_argument('--cal', type=float, help='calibration fraction per class (default %.2f); test stays the last 50%%' % CAL)
    a = p.parse_args()
    if a.cal:
        assert a.cal <= 1 - TEST, 'calibration would overlap the test half'
        CAL = a.cal
    if a.check or not a.data:
        check()
    else:
        r = run(a.data, [int(c) for c in a.channels.split(',')], a.epochs, save=a.save, classes=tuple(a.classes.split(',')))
        print(json.dumps(r, ensure_ascii=False, indent=2))
        if a.out: Path(a.out).write_text(json.dumps(r, ensure_ascii=False, indent=2))

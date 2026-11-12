"""Fine-tune the Meta-pretrained 4-channel CNN on wristband takes and score it on the rewear set.

This is the "预训练 → 自己硬件上微调 → 摘下重戴验收" path from the global plan, next to the LDA
electrode sweep in wl8.py. Takes are 2 s of a sustained gesture at 2 kHz x 8 ch (wl8.py); the net
wants 0.4 s x 4 ch at 1 kHz, so: pick channels, decimate 2 -> 1 kHz, crop 0.4 s windows (random
inside the take while training, the middle one when scoring), scale each channel by a label-free
median from the earliest train takes. The pretrained body keeps its weights; the head is new
because the gesture set is not Meta's (fist is not in it).

    python3 emg_wl8_cnn.py --train emg-wl8-data --rewear emg-wl8-data-rewear --channels 0,2,4,6 --init emg-public/gni_4ch_3g.pt
    python3 emg_wl8_cnn.py --check
"""
import argparse
import json
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn

import wl8
from emg_gni_train import Net, CROP

HZ_OUT = 1000
EARLY = .2


def prepare(records, channels):
    """[(label, emg_uv (4000,8))] -> X (n, ch, 2000) float32 at 1 kHz, y labels list."""
    from scipy.signal import decimate
    X = np.stack([decimate(e[:, channels].astype(np.float64), wl8.EMG_HZ // HZ_OUT, axis=0, zero_phase=True) for _, e in records]).astype(np.float32)
    return X.transpose(0, 2, 1), [l for l, _ in records]


def scale_from(X):
    """Per-channel scale from the earliest EARLY fraction of takes, labels unseen (same rule as emg_gni_train)."""
    early = X[:max(1, int(len(X) * EARLY))]
    return np.median(np.abs(early), axis=(0, 2)) + 1e-6


def crops(X, rng=None):
    n, ch, T = X.shape
    if rng is None:
        a = (T - CROP) // 2
        return X[:, :, a:a + CROP]
    starts = rng.integers(T // 10, T - CROP - T // 10, n)          # stay off the take's first/last 10%
    return np.stack([x[:, s:s + CROP] for x, s in zip(X, starts)])


def fit(model, X, y, epochs, lr, dev, rng, batch=64):
    loss_f = nn.CrossEntropyLoss(); opt = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-3)
    for _ in range(epochs):
        model.train(); order = rng.permutation(len(X))
        for i in range(0, len(X), batch):
            b = order[i:i + batch]
            xb = torch.tensor(crops(X[b], rng), device=dev) * torch.exp(torch.randn(len(b), X.shape[1], 1, device=dev) * .15)
            opt.zero_grad(); loss_f(model(xb), torch.tensor(y[b], device=dev)).backward(); opt.step()


@torch.no_grad()
def predict(model, X, dev):
    model.eval()
    return model(torch.tensor(crops(X), device=dev)).argmax(1).cpu().numpy()


def balanced(pred, y, n):
    return float(np.mean([np.mean(pred[y == c] == c) for c in range(n) if (y == c).any()]))


def run(train_root, rewear_root, channels, init=None, epochs=40, dev=None, seed=0, save_model=None):
    dev = dev or ('mps' if torch.backends.mps.is_available() else 'cpu')
    rng = np.random.default_rng(seed); torch.manual_seed(seed)
    train = [r for r in wl8.load(train_root) if r[0] != 'loose']
    rewear = [r for r in wl8.load(rewear_root) if r[0] != 'loose'] if rewear_root and Path(rewear_root).exists() else []
    classes = sorted({l for l, _ in train})
    Xtr, ytr = prepare(train, channels); ytr = np.array([classes.index(l) for l in ytr])
    scale = scale_from(Xtr); Xtr /= scale[None, :, None]
    # Time-ordered holdout inside the train session: last 30% per class, so the number is honest even before rewear is recorded.
    hold = np.zeros(len(ytr), bool)
    for c in range(len(classes)):
        idx = np.flatnonzero(ytr == c); hold[idx[int(len(idx) * .7):]] = True
    out = {'classes': classes, 'channels': channels, 'takes': len(train), 'rewear_takes': len(rewear), 'init': init and Path(init).name, 'device': dev}
    for name, pretrained in (('scratch', False), ('finetune', bool(init))):
        if name == 'finetune' and not init:
            continue
        model = Net(len(channels), len(classes)).to(dev)
        if pretrained:
            state = torch.load(init, map_location='cpu', weights_only=False)['state']
            model.load_state_dict({k: v for k, v in state.items() if not k.startswith('head.')}, strict=False)
        fit(model, Xtr[~hold], ytr[~hold], epochs, 1e-3 if pretrained else 3e-3, dev, rng)
        if save_model and (pretrained or not init):
            # Folded numpy weights + this session's channel scale: what emg_web.py --model runs live.
            from emg_cnn_export import fold, save_npz
            convs, head = fold({k: v.cpu() for k, v in model.state_dict().items()})
            save_npz(save_model, convs, head, classes, channels, scale)
        out[name] = {'holdout': round(balanced(predict(model, Xtr[hold], dev), ytr[hold], len(classes)), 3)}
        if rewear:
            Xr, yr = prepare(rewear, channels); yr = np.array([classes.index(l) if l in classes else -1 for l in yr])
            keep = yr >= 0; Xr = Xr[keep] / scale[None, :, None]; yr = yr[keep]
            out[name]['rewear'] = round(balanced(predict(model, Xr, dev), yr, len(classes)), 3)
    counts = {c: sum(1 for l, _ in rewear if l == c) for c in classes}
    best = max((v.get('rewear', -1) for k, v in out.items() if isinstance(v, dict) and 'rewear' in v), default=None)
    out['g2_passed'] = bool(best is not None and best >= .85 and all(v >= 5 for v in counts.values()))
    out['message'] = ' / '.join(f'{k}: 同次 {v["holdout"]:.2f}' + (f'，摘下重戴 {v["rewear"]:.2f}' if 'rewear' in v else '') for k, v in out.items() if isinstance(v, dict) and 'holdout' in v) \
        + ('；G2 过' if out['g2_passed'] else '；G2 不过' if rewear else '；rewear 未录')
    return out


def check():
    import tempfile
    rng = np.random.default_rng(2)
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        for which, n in (('train', 16), ('rewear', 6)):
            for label in ('rest', 'middle', 'thumb_up', 'thumb_down', 'fist'):
                for i in range(n):
                    raw, _ = wl8._synth_frames(label, rng)
                    emg, imu, seq, _ = wl8.decode(raw)
                    folder = root / which / label; folder.mkdir(parents=True, exist_ok=True)
                    wl8.save(folder / f'{label}-{i:04d}', emg, imu, seq, label, 'check', 1, 'fake')
        # A pretrained blob with random weights: the point is the loading path and the new head, not Meta's accuracy.
        torch.manual_seed(0); init = root / 'init.pt'
        torch.save({'state': Net(4, 4).state_dict()}, init)
        r = run(root / 'train', root / 'rewear', [0, 2, 4, 6], init=str(init), epochs=40, dev='cpu')
        assert r['finetune']['rewear'] > .8 and r['scratch']['rewear'] > .8 and r['g2_passed'], r['message']
        # Must fail: shuffled labels on the train side must not pass the holdout.
        recs = wl8.load(root / 'train'); labels = rng.permutation([l for l, _ in recs])
        X, y = prepare(recs, [0, 2, 4, 6]); y = np.array([['rest', 'middle', 'thumb_up', 'thumb_down', 'fist'].index(l) for l in labels])
        X /= scale_from(X)[None, :, None]
        m = Net(4, 5); fit(m, X[:56], y[:56], 15, 3e-3, 'cpu', rng)
        assert balanced(predict(m, X[56:], 'cpu'), y[56:], 5) < .45, 'shuffled labels learned something'
        # Must fail: rewear missing a class cannot pass G2.
        import shutil; shutil.rmtree(root / 'rewear' / 'fist')
        assert not run(root / 'train', root / 'rewear', [0, 2, 4, 6], init=str(init), epochs=3, dev='cpu')['g2_passed']
    print('wl8 cnn check passed:', r['message'])


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--train'); p.add_argument('--rewear'); p.add_argument('--channels', default='0,2,4,6')
    p.add_argument('--init', help='emg_gni_train.py --save 的 .pt；不给就只从头训'); p.add_argument('--epochs', type=int, default=40)
    p.add_argument('--out'); p.add_argument('--check', action='store_true'); p.add_argument('--save-model', help='折叠后的 .npz，给 emg_web.py --model 实时识别用')
    a = p.parse_args()
    if a.check or not a.train:
        check()
    else:
        r = run(a.train, a.rewear, [int(c) for c in a.channels.split(',')], a.init, a.epochs, save_model=a.save_model)
        print(json.dumps(r, ensure_ascii=False, indent=2))
        if a.out: Path(a.out).write_text(json.dumps(r, ensure_ascii=False, indent=2))

"""Real electrode shift vs our simulated ring rotation, on LibEMG's ElectrodeShift dataset (CIILData).

21 subjects, Myo 8 ch @ 200 Hz, 5 classes (close/open/rest/flexion/extension). `training/` = 5 reps
before the shift, `trial_1..4/` = 2 reps each after re-donning with a shift. Windows 200 ms / 100 ms
hop, 5 time-domain features per channel (MAV RMS WL ZC SSC; no spectral ratio at 200 Hz), the same
shrinkage LDA as emg_model. Balanced accuracy, mean over subjects.

    python3 emg_shift_public.py CIILData/ElectrodeShift --out shift.json
    python3 emg_shift_public.py --check        # synthetic must-fail
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np

FS, WIN, HOP = 200, 40, 20
SHRINKAGE = .1


def features(win):
    x = win - win.mean(0)
    d = np.diff(x, axis=0)
    thr = .1 * (np.sqrt((x ** 2).mean(0)) + 1e-12)
    zc = ((x[:-1] * x[1:] < 0) & (np.abs(d) > thr)).sum(0)
    ssc = ((d[:-1] * d[1:] < 0) & ((np.abs(d[:-1]) > thr) | (np.abs(d[1:]) > thr))).sum(0)
    return np.concatenate([np.log(np.abs(x).mean(0) + 1e-9), np.log(np.sqrt((x ** 2).mean(0)) + 1e-9),
                           np.log(np.abs(d).sum(0) + 1e-9), zc, ssc])


def features_book(win, fs=FS):
    """The textbook's fuller set (《表面肌电与人体运动识别》§3.3): the five above plus VAR, DASDV, TM3
    (time domain) and median / mean-power frequency (frequency domain). 10 numbers per channel."""
    base = features(win)
    x = win - win.mean(0)
    d = np.diff(x, axis=0)
    var = np.log(x.var(0, ddof=1) + 1e-9)
    dasdv = np.log(np.sqrt((d ** 2).mean(0)) + 1e-9)
    tm3 = np.log(np.abs((x ** 3).mean(0)) + 1e-9)
    p = np.abs(np.fft.rfft(x * np.hanning(len(x))[:, None], axis=0)) ** 2
    f = np.fft.rfftfreq(len(x), 1 / fs)
    tot = p.sum(0) + 1e-12
    mpf = (f[:, None] * p).sum(0) / tot
    mf = f[(np.cumsum(p, 0) / tot >= .5).argmax(0)]
    return np.concatenate([base, var, dasdv, tm3, mf, mpf])


FEATS = {'base': (features, 5), 'book': (features_book, 10)}
FEAT = features


def fit(X, y):
    classes = sorted(set(y)); y = np.asarray(y)
    mean, scale = X.mean(0), np.maximum(X.std(0), 1e-9)
    z = (X - mean) / scale
    groups = [z[y == k] for k in classes]
    means = np.stack([g.mean(0) for g in groups])
    within = sum(np.cov(g.T, ddof=1) * (len(g) - 1) for g in groups) / (len(y) - len(classes))
    d = X.shape[1]
    within = (1 - SHRINKAGE) * within + (SHRINKAGE * np.trace(within) / d + 1e-6) * np.eye(d)
    w = means @ np.linalg.inv(within)
    b = -.5 * np.einsum('kd,kd->k', w, means) + np.log([len(g) / len(y) for g in groups])
    return {'classes': classes, 'mean': mean, 'scale': scale, 'w': w, 'b': b}


def predict(m, X):
    z = (X - m['mean']) / m['scale']
    return np.array(m['classes'])[(z @ m['w'].T + m['b']).argmax(1)]


def balanced(y, p):
    y, p = np.asarray(y), np.asarray(p)
    return float(np.mean([np.mean(p[y == k] == k) for k in np.unique(y)]))


def load_set(folder, rotate=0):
    """(features, label, rep) for every window in one training/trial_k folder."""
    F, y, r = [], [], []
    for f in sorted(Path(folder).glob('R_*_C_*.csv')):
        rep, cls = (int(s) for s in f.stem.replace('R_', '').split('_C_'))
        x = np.loadtxt(f, delimiter=',', dtype=np.float32)
        x = np.roll(x, rotate, axis=1)                      # the band turned `rotate` electrodes
        for i in range(0, len(x) - WIN + 1, HOP):
            F.append(FEAT(x[i:i + WIN])); y.append(cls); r.append(rep)
    return np.stack(F), np.array(y), np.array(r)


def subject(root, s, rng):
    tr = load_set(root / f'subject{s}' / 'training')
    trials = [load_set(root / f'subject{s}' / f'trial_{k}') for k in range(1, 5)]
    out = {}
    # (a) no shift: leave-one-rep-out inside training
    out['same_seat_loro'] = float(np.mean([balanced(tr[1][tr[2] == k], predict(fit(tr[0][tr[2] != k], tr[1][tr[2] != k]), tr[0][tr[2] == k])) for k in range(5)]))
    m = fit(tr[0], tr[1])
    # (b) real shift, no recalibration
    out['shift_no_recal'] = float(np.mean([balanced(t[1], predict(m, t[0])) for t in trials]))
    # (c) real shift, recalibrated on one rep at the new seat, tested on the other rep
    out['shift_recal_1rep'] = float(np.mean([balanced(t[1][t[2] == 1], predict(fit(t[0][t[2] == 0], t[1][t[2] == 0]), t[0][t[2] == 1])) for t in trials]))
    # (d) real shift, old model + one new rep pooled
    out['shift_pool_1rep'] = float(np.mean([balanced(t[1][t[2] == 1], predict(fit(np.concatenate([tr[0], t[0][t[2] == 0]]), np.concatenate([tr[1], t[1][t[2] == 0]])), t[0][t[2] == 1])) for t in trials]))
    # (e) our simulation: train reps 0-2 at the old seat, test reps 3-4 with the channel ring turned k
    mt = fit(tr[0][tr[2] < 3], tr[1][tr[2] < 3])
    for k in (1, -1, 2, 4):
        te = load_set(root / f'subject{s}' / 'training', rotate=k)
        out[f'sim_rot{k:+d}_no_recal'] = balanced(te[1][te[2] >= 3], predict(mt, te[0][te[2] >= 3]))
    out['sim_rot0'] = balanced(tr[1][tr[2] >= 3], predict(mt, tr[0][tr[2] >= 3]))
    out['shuffled'] = float(np.mean([balanced(t[1], predict(fit(tr[0], rng.permutation(tr[1])), t[0])) for t in trials]))
    return out


def run(root, out=None):
    rng = np.random.default_rng(0)
    subs = sorted(int(p.name[7:]) for p in Path(root).glob('subject*'))
    per = {s: subject(Path(root), s, rng) for s in subs}
    keys = next(iter(per.values())).keys()
    summary = {k: round(float(np.mean([per[s][k] for s in subs])), 4) for k in keys}
    res = {'n_subjects': len(subs), 'mean': summary, 'per_subject': per}
    print(json.dumps(summary, indent=1))
    if out: Path(out).write_text(json.dumps(res, indent=1))
    return res


def check():
    import tempfile
    rng = np.random.default_rng(1)
    pat = rng.uniform(.5, 4, (5, 8)); pat[2] = 0
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        for s in range(2):
            gain = rng.uniform(.7, 1.4, 8)
            for folder, reps, roll in [('training', 5, 0)] + [(f'trial_{k}', 2, 2) for k in range(1, 5)]:
                d = root / f'subject{s}' / folder; d.mkdir(parents=True)
                for r in range(reps):
                    for c in range(5):
                        x = rng.normal(0, 1, (600, 8)) * (1 + pat[c] * gain)
                        np.savetxt(d / f'R_{r}_C_{c}.csv', np.roll(x, roll, 1), delimiter=',', fmt='%.3f')
        res = run(root)['mean']
    assert res['same_seat_loro'] > .9, res
    assert res['shift_no_recal'] < res['same_seat_loro'] - .3, res         # a 2-electrode shift must hurt
    assert res['shift_recal_1rep'] > res['shift_no_recal'] + .3, res       # recalibrating must recover it
    assert abs(res['sim_rot+2_no_recal'] - res['shift_no_recal']) < .15, res  # synthetic shift == rotation by 2
    assert res['shuffled'] < .35, res
    print('shift check passed')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('root', nargs='?'); p.add_argument('--out'); p.add_argument('--check', action='store_true')
    p.add_argument('--features', default='base', choices=FEATS)
    a = p.parse_args()
    FEAT = FEATS[a.features][0]
    if a.check or not a.root:
        check()
    else:
        run(a.root, a.out)

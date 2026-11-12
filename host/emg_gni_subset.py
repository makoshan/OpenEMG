"""Which 4 of Meta's 16 wrist electrodes should the band keep?

Windows from emg_gni_prep.py (1 kHz, 16 ch). Crop [100:500] (0.4 s around the press), compute
emg_channels.features once for all 16 channels (96 numbers, block order MAV/RMS/WL/ZC/SSC/HI x 16),
then score every C(16,4)=1820 subset with a within-user shrinkage LDA: per user, per class, first 70%
of windows in time train, last 30% test; balanced accuracy averaged over users.

    python emg_gni_subset.py --data emg-public/gni-win --out emg-public/gni_subset_sweep.json
    python emg_gni_subset.py --check          # synthetic must-fail: shuffled ~ chance, 4 identical <= best
"""
import argparse
import itertools
import json
import time
from pathlib import Path

import numpy as np

import emg_channels
import emg_model

emg_channels.FS = 1000                    # prep decimated 2 kHz -> 1 kHz; features() reads this for the spectral ratio
FEAT, NF = emg_channels.features, 6      # --features book swaps in the textbook's 10-per-channel set
CLASSES = ('rest', 'index_press', 'middle_press', 'thumb_click', 'thumb_down', 'thumb_in', 'thumb_out', 'thumb_up')
FIXED = [0, 4, 8, 12]
LO, HI = 100, 500


def load(folder, limit=None, seed=0):
    files = sorted(Path(folder).glob('*.npz'))
    if limit and limit < len(files):
        files = [files[i] for i in sorted(np.random.default_rng(seed).choice(len(files), limit, replace=False))]
    users = []
    for f in files:
        z = np.load(f, allow_pickle=False)
        X = z['X'][:, LO:HI].astype(np.float32)
        F = np.stack([FEAT(w) for w in X])                              # (n, NF*16)
        y, t = z['y'].astype(int), z['t']
        tr, te = [], []
        for c in np.unique(y):
            idx = np.flatnonzero(y == c); idx = idx[np.argsort(t[idx])]; cut = int(len(idx) * .7)
            tr += list(idx[:cut]); te += list(idx[cut:])
        users.append({'name': f.stem, 'F': F, 'y': y, 'tr': np.array(tr), 'te': np.array(te)})
    return users


def cols(subset):
    return np.array([f * 16 + c for f in range(NF) for c in subset])


def score(u, subset, keep=None, shuffle=None):
    """Balanced accuracy of one user on a channel subset; keep = class ids to include."""
    tr, te = u['tr'], u['te']
    if keep is not None:
        tr = tr[np.isin(u['y'][tr], keep)]; te = te[np.isin(u['y'][te], keep)]
    ytr = u['y'][tr] if shuffle is None else shuffle.permutation(u['y'][tr])
    c = cols(subset)
    model = emg_model._fit_generic(u['F'][tr][:, c], list(ytr))
    pred = np.array(emg_model.predict(model, u['F'][te][:, c]))
    yte = u['y'][te]
    return float(np.mean([np.mean(pred[yte == k] == k) for k in np.unique(yte)])), yte, pred


def mean_score(users, subset, keep=None, shuffle=None):
    return round(float(np.mean([score(u, subset, keep, shuffle)[0] for u in users])), 4)


def turn(subset, k):
    return [(c + k) % 16 for c in subset]


def rotated(u, subset, k, keep=None, aug=(0,)):
    """Train on subset, test with the whole band turned k electrodes (a re-wear that slipped round the wrist).
    aug: extra training copies of the same windows read at turned positions, same labels.
    ponytail: assumes Meta's index order is the physical ring order (15 next to 0); unverified against their docs."""
    tr, te = u['tr'], u['te']
    if keep is not None:
        tr = tr[np.isin(u['y'][tr], keep)]; te = te[np.isin(u['y'][te], keep)]
    Xtr = np.concatenate([u['F'][tr][:, cols(turn(subset, a))] for a in aug])
    model = emg_model._fit_generic(Xtr, list(u['y'][tr]) * len(aug))
    pred = np.array(emg_model.predict(model, u['F'][te][:, cols([(c + k) % 16 for c in subset])]))
    yte = u['y'][te]
    return float(np.mean([np.mean(pred[yte == c] == c) for c in np.unique(yte)]))


def rotation(users, subset, ks=range(-3, 4), keep=None, aug=(0,)):
    """No re-calibration (model from the original position) vs re-calibrated on the turned position."""
    out = {}
    for k in ks:
        out[k] = {'no_recal': round(float(np.mean([rotated(u, subset, k, keep) for u in users])), 4),
                  'recal': mean_score(users, turn(subset, k), keep)}
        if tuple(aug) != (0,):
            out[k]['aug_no_recal'] = round(float(np.mean([rotated(u, subset, k, keep, aug) for u in users])), 4)
    return out


def greedy(users, start, size):
    s = list(start)
    while len(s) < size:
        s.append(max((c for c in range(16) if c not in s), key=lambda c: mean_score(users, s + [c])))
    return s


def sweep(users):
    t0 = time.time()
    scores = {s: mean_score(users, s) for s in itertools.combinations(range(16), 4)}
    top = sorted(scores.items(), key=lambda kv: -kv[1])[:20]
    best = list(top[0][0])
    truth, pred = [], []
    for u in users:
        _, yt, p = score(u, best); truth += yt.tolist(); pred += p.tolist()
    rep = emg_model._report([CLASSES[k] for k in truth], [CLASSES[k] for k in pred], list(CLASSES))
    triples = {g: mean_score(users, best, keep=[0, *g]) for g in itertools.combinations(range(1, 8), 3)}
    g3 = max(triples, key=triples.get)
    rng = np.random.default_rng(0)
    return {'users': [u['name'] for u in users], 'n_users': len(users), 'classes': CLASSES,
            'top20': [{'subset': list(s), 'balanced': v} for s, v in top],
            'fixed_0_4_8_12': scores[tuple(FIXED)],
            'best8_greedy_from_best4': (s8 := greedy(users, best, 8), mean_score(users, s8)),
            'even8_0_2_14': mean_score(users, list(range(0, 16, 2))),
            'all16': mean_score(users, list(range(16))),
            'best4_confusion': rep['confusion'], 'best4_recall': rep['recall'],
            'best_3_gestures': {'gestures': [CLASSES[k] for k in g3], 'balanced_4class': triples[g3],
                                'all_triples_top5': [{'gestures': [CLASSES[k] for k in g], 'balanced': v}
                                                     for g, v in sorted(triples.items(), key=lambda kv: -kv[1])[:5]]},
            'must_fail': {'shuffled_labels_best4': mean_score(users, best, shuffle=rng),
                          'four_identical_ch': {'subset': [best[0]] * 4, 'balanced': mean_score(users, [best[0]] * 4)},
                          'chance_8class': round(1 / 8, 3)},
            'seconds': round(time.time() - t0)}


def check():
    import tempfile
    rng = np.random.default_rng(3)
    pat = rng.uniform(.5, 3, (8, 16)); pat[0] = 0
    with tempfile.TemporaryDirectory() as tmp:
        for k in range(3):
            gain = rng.uniform(.6, 1.6, 16); n = 240
            y = rng.integers(0, 8, n).astype(np.int8); X = rng.normal(0, 1, (n, 600, 16))
            for i in range(n):
                X[i, 250:450] *= 1 + pat[y[i]] * gain
            np.savez(Path(tmp) / f'u{k}.npz', X=X.astype(np.float16), y=y, t=np.arange(n, dtype=float), split='train')
        users = load(tmp)
    best = max(itertools.combinations(range(16), 4), key=lambda s: mean_score(users, s))
    b = mean_score(users, best)
    assert b > .8, b
    sh = mean_score(users, best, shuffle=np.random.default_rng(0))
    assert sh < .3, f'shuffled labels learned something: {sh}'
    same = mean_score(users, [best[0]] * 4)
    assert same <= b and same < mean_score(users, list(range(16))), (same, b)
    r = rotation(users, list(best), ks=(0, 8))
    assert r[0]['no_recal'] == b, (r[0], b)                    # no turn = the plain score
    assert r[8]['no_recal'] < b - .3, r                          # half a turn must break an uncalibrated model
    a = rotation(users, list(best), ks=(1,), aug=(-1, 0, 1))[1]
    assert a['aug_no_recal'] > a['no_recal'] + .1, a             # aug ignored -> equal; synthetic 0.18 -> 0.31
    print(f'subset check passed: best4 {b:.2f}, shuffled {sh:.2f}, 4x same channel {same:.2f}, '
          f'turned 8 no-recal {r[8]["no_recal"]:.2f}')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--data'); p.add_argument('--out'); p.add_argument('--users', type=int); p.add_argument('--check', action='store_true')
    p.add_argument('--rotate', help='comma subset, e.g. 3,5,7,11: accuracy when the band turns -3..+3 electrodes')
    p.add_argument('--aug', default='0', help='comma training offsets for --rotate; write --aug=-1,0,1')
    p.add_argument('--features', default='base', choices=('base', 'book'))
    p.add_argument('--keep', help='comma class names for --rotate, e.g. rest,middle_press,thumb_down,thumb_up')
    a = p.parse_args()
    if a.features == 'book':
        import emg_shift_public
        FEAT, NF = (lambda w: emg_shift_public.features_book(w, fs=1000)), 10
    if a.check or not a.data:
        check()
    elif a.rotate:
        users = load(a.data, a.users)
        s = [int(c) for c in a.rotate.split(',')]
        keep = [CLASSES.index(n) for n in a.keep.split(',')] if a.keep else None
        aug = tuple(int(x) for x in a.aug.split(','))
        r = {'subset': s, 'n_users': len(users), 'classes': a.keep or 'all8', 'aug': aug,
             'rotation': rotation(users, s, keep=keep, aug=aug)}
        print(json.dumps(r, indent=1))
        if a.out: Path(a.out).write_text(json.dumps(r, indent=1))
    else:
        users = load(a.data, a.users)
        print(f'{len(users)} users loaded', flush=True)
        r = sweep(users)
        print(json.dumps({k: v for k, v in r.items() if k != 'users'}, ensure_ascii=False, indent=1))
        if a.out: Path(a.out).write_text(json.dumps(r, ensure_ascii=False, indent=1))

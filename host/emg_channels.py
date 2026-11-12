"""How many wrist EMG channels does keyboard/mouse-style gesture control need?

Meta's generic-neuromotor-interface discrete_gestures set (16 electrodes around the wrist, 2 kHz,
CC-BY-NC research data) is recorded exactly for this: index / middle pinch, thumb click and four
thumb swipes, the gestures a wristband would map to click, right-click, enter and arrows. This keeps
1, 2, 4, 8 or all 16 channels, cuts a window around every press (plus quiet windows as 'rest'),
extracts the same kind of cheap time-domain features the watch can afford, and trains the same
shrinkage LDA the EMG task already uses. Train on the first 70% of each recording, test on the last
30% of each gesture's own windows -- never interleaved windows, which is how single-channel papers report 90%.

    python3 emg_channels.py --check                      # synthetic, no download
    python3 emg_channels.py emg-public/gni               # the 3-participant subset
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np

import emg_model

FS = 2000
PRE, POST = .15, .25                     # window around the gesture timestamp, s
CLASSES = ('index_press', 'middle_press', 'thumb_click', 'thumb_down', 'thumb_in', 'thumb_out', 'thumb_up')
SUBSETS = {1: [0], 2: [0, 8], 4: [0, 4, 8, 12], 8: list(range(0, 16, 2)), 16: list(range(16))}


def features(win):
    """win: (samples, channels) -> 6 numbers per channel. MAV, RMS, waveform length, zero crossings,
    slope-sign changes, and log power above 150 Hz over total: the Hudgins set plus one spectral
    ratio, all cheap enough for the nRF52840 in the watch."""
    x = win - win.mean(0)
    d = np.diff(x, axis=0)
    thr = .1 * (np.sqrt((x ** 2).mean(0)) + 1e-12)
    zc = ((x[:-1] * x[1:] < 0) & (np.abs(d) > thr)).sum(0)
    ssc = ((d[:-1] * d[1:] < 0) & ((np.abs(d[:-1]) > thr) | (np.abs(d[1:]) > thr))).sum(0)
    spec = np.abs(np.fft.rfft(x * np.hanning(len(x))[:, None], axis=0)) ** 2
    f = np.fft.rfftfreq(len(x), 1 / FS)
    hi = np.log((spec[f >= 150].sum(0) + 1e-12) / (spec[f >= 20].sum(0) + 1e-12))
    return np.concatenate([np.log(np.abs(x).mean(0) + 1e-9), np.log(np.sqrt((x ** 2).mean(0)) + 1e-9),
                           np.log(np.abs(d).sum(0) + 1e-9), zc, ssc, hi])


def windows(emg, times, prompts, rng, rest_per_class=None):
    """emg (N,16), times (N,), prompts: list of (name, t). Returns [(label, window)] in time order."""
    n_pre, n_post = int(PRE * FS), int(POST * FS)
    out, busy = [], []
    for name, t in prompts:
        i = int(np.searchsorted(times, t))
        busy.append(i)
        if name in CLASSES and n_pre <= i < len(emg) - n_post:
            out.append((i, name, emg[i - n_pre:i + n_post]))
    busy = np.array(sorted(busy))
    per = rest_per_class or max(1, len(out) // len(CLASSES))
    tries = 0
    while sum(1 for o in out if o[1] == 'rest') < per and tries < per * 50:
        tries += 1
        i = int(rng.integers(n_pre, len(emg) - n_post))
        if busy.size and np.min(np.abs(busy - i)) < FS:            # at least 1 s from any gesture
            continue
        out.append((i, 'rest', emg[i - n_pre:i + n_post]))
    out.sort(key=lambda o: o[0])
    return [(name, w) for _, name, w in out]


def split_score(records, channels):
    """records: [(label, window)] of one recording, time-ordered."""
    # Per class, first 70% of its windows (in time) train and the last 30% test: the thumb swipes
    # only start halfway through Meta's protocol, so one global cut would leave them untested.
    tr, te = [], []
    for label in sorted({r[0] for r in records}):
        rs = [r for r in records if r[0] == label]
        cut = int(len(rs) * .7)
        tr += rs[:cut]; te += rs[cut:]
    labels_tr = [r[0] for r in tr]
    if len(set(labels_tr)) < 2 or not te:
        return None
    X = lambda rs: np.stack([features(w[:, channels]) for _, w in rs])
    model = emg_model._fit_generic(X(tr), labels_tr)
    truth = [r[0] for r in te if r[0] in model['classes']]
    Xte = X([r for r in te if r[0] in model['classes']])
    pred = emg_model.predict(model, Xte)
    rep = emg_model._report(truth, pred, sorted(set(truth)))
    effort = emg_model._report(['rest' if t == 'rest' else 'gesture' for t in truth],
                               ['rest' if p == 'rest' else 'gesture' for p in pred], ['gesture', 'rest'])
    return {'balanced': rep['balanced'], 'effort_balanced': effort['balanced'], 'test_windows': len(truth)}


def load_recording(path):
    import h5py, pandas as pd
    with h5py.File(path, 'r') as f:
        data = f['data'][:]
    emg = np.stack([data['emg'][:, c] for c in range(16)], 1) if data['emg'].ndim == 2 else data['emg']
    prompts = pd.read_hdf(path, 'prompts')
    return emg.astype(np.float32), data['time'], list(zip(prompts['name'], prompts['time']))


def run(folder):
    files = sorted(Path(folder).rglob('*.hdf5'))
    if not files:
        sys.exit(f'{folder} 里没有 .hdf5：先下 discrete_gestures small_subset')
    rng = np.random.default_rng(0)
    per_file = []
    for path in files:
        emg, times, prompts = load_recording(path)
        recs = windows(emg, times, prompts, rng)
        row = {'file': path.name, 'windows': len(recs), 'by_channels': {}}
        for k, ch in SUBSETS.items():
            row['by_channels'][k] = split_score(recs, ch)
        per_file.append(row)
        print(path.name, {k: v and v['balanced'] for k, v in row['by_channels'].items()}, flush=True)
    summary = {}
    for k in SUBSETS:
        vals = [r['by_channels'][k] for r in per_file if r['by_channels'][k]]
        summary[k] = {'gesture8_balanced_mean': round(float(np.mean([v['balanced'] for v in vals])), 3),
                      'effort_balanced_mean': round(float(np.mean([v['effort_balanced'] for v in vals])), 3),
                      'recordings': len(vals)}
    return {'recordings': per_file, 'summary': summary, 'chance_8class': round(1 / 8, 3),
            'note': '8 类 = 7 种手势 + 放松；同一录音内前 70% 训练、后 30% 测试；收缩 LDA；每通道 6 个时域/频域特征'}


def check():
    """Synthetic 16-channel wrist: each gesture drives its own set of channels. More channels must
    separate more gestures; shuffled labels must fall to chance."""
    rng = np.random.default_rng(1)
    n = FS * 240
    emg = rng.normal(0, 1, (n, 16)).astype(np.float32)
    times = np.arange(n) / FS
    prompts, t = [], 2.
    gain = {c: np.zeros(16) for c in CLASSES}
    for k, c in enumerate(CLASSES):
        gain[c][(2 * k) % 16] = 6; gain[c][(2 * k + 1) % 16] = 4; gain[c][(2 * k + 5) % 16] = 3
    while t < 238:
        c = CLASSES[rng.integers(len(CLASSES))]
        i = int(t * FS); emg[i:i + int(.2 * FS)] *= (1 + gain[c])
        prompts.append((c, t)); prompts.append((c.replace('press', 'release'), t + .3)); t += 2.2
    recs = windows(emg, times, prompts, rng)
    s1, s16 = split_score(recs, SUBSETS[1]), split_score(recs, SUBSETS[16])
    assert s16['balanced'] > .9, s16
    assert s1['balanced'] < s16['balanced'] - .2, (s1, s16)
    shuffled = [(l, w) for (_, w), l in zip(recs, rng.permutation([r[0] for r in recs]))]
    assert split_score(shuffled, SUBSETS[16])['balanced'] < .3, 'shuffled labels learned something: leak'
    print(f'channels: 1ch {s1["balanced"]:.2f} < 16ch {s16["balanced"]:.2f}; shuffled at chance; passed')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('folder', nargs='?'); p.add_argument('--check', action='store_true')
    a = p.parse_args()
    if a.check or not a.folder:
        check()
    else:
        print(json.dumps(run(a.folder), ensure_ascii=False, indent=2))

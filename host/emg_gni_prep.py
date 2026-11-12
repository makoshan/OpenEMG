"""Stream Meta's discrete_gestures full_data.tar (33 GB) into per-user window files (~30 MB each).

The laptop has ~17 GB free, so the tar is never stored: each .hdf5 member is spooled to a temp file,
cut into windows around every gesture (plus quiet 'rest' windows), decimated 2 kHz -> 1 kHz (the rate
our own boards sample at), stored as float16 with all 16 channels (so any channel subset can be tried
later without downloading again), and the temp file is deleted.

    curl -s https://fb-ctrl-oss.s3.amazonaws.com/neuromotor-data/data/discrete_gestures/full_data.tar \
      | python emg_gni_prep.py --out emg-public/gni-win --corpus emg-public/gni/discrete_gestures_corpus.csv
    python emg_gni_prep.py --out /tmp/x --files emg-public/gni/*.hdf5     # same code on local files
"""
import argparse
import sys
import tarfile
import tempfile
from pathlib import Path

import numpy as np

FS_IN, FS_OUT = 2000, 1000
PRE, POST = .25, .35                       # stored window; training crops a jittered 0.4 s inside it
CLASSES = ('rest', 'index_press', 'middle_press', 'thumb_click', 'thumb_down', 'thumb_in', 'thumb_out', 'thumb_up')


def cut(path, rng):
    """One hdf5 recording -> (X float16 [n, 600, 16], y int8 [n], t float64 [n])."""
    import h5py
    import pandas as pd
    from scipy.signal import decimate
    with h5py.File(path, 'r') as f:
        data = f['data'][:]
    emg, times = data['emg'], data['time']
    prompts = pd.read_hdf(path, 'prompts')
    n_pre, n_post = int(PRE * FS_IN), int(POST * FS_IN)
    idx = np.searchsorted(times, prompts['time'].to_numpy())
    events = [(i, CLASSES.index(n)) for i, n in zip(idx, prompts['name']) if n in CLASSES and n_pre <= i < len(emg) - n_post]
    busy = np.sort(idx)
    n_rest = max(1, len(events) // (len(CLASSES) - 1))
    rest, tries = [], 0
    while len(rest) < n_rest and tries < n_rest * 50:
        tries += 1
        i = int(rng.integers(n_pre, len(emg) - n_post))
        if busy.size and np.abs(busy - i).min() < FS_IN:
            continue
        rest.append((i, 0))
    picks = sorted(events + rest)
    X = np.stack([decimate(emg[i - n_pre:i + n_post].astype(np.float64), 2, axis=0, zero_phase=True) for i, _ in picks])
    return X.astype(np.float16), np.array([c for _, c in picks], np.int8), times[[i for i, _ in picks]]


def save(out, name, X, y, t, split):
    np.savez(out / (Path(name).stem + '.npz'), X=X, y=y, t=t, split=split, classes=np.array(CLASSES), fs=FS_OUT, pre=PRE)


def splits(corpus):
    import csv
    if not corpus or not Path(corpus).exists():
        return {}
    return {r['dataset']: r['split'] for r in csv.DictReader(open(corpus))}


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--out', required=True); p.add_argument('--corpus'); p.add_argument('--files', nargs='*')
    a = p.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    split_of, rng = splits(a.corpus), np.random.default_rng(0)
    if a.files:
        for f in a.files:
            X, y, t = cut(f, rng); save(out, f, X, y, t, split_of.get(Path(f).name, '?'))
            print(Path(f).name, X.shape, np.bincount(y, minlength=len(CLASSES)).tolist(), flush=True)
        return
    with tarfile.open(fileobj=sys.stdin.buffer, mode='r|*') as tar:
        for m in tar:
            if not m.isfile() or not m.name.endswith('.hdf5'):
                continue
            name = Path(m.name).name
            if (out / (Path(name).stem + '.npz')).exists():
                continue                                    # a rerun skips what is done (still streams it)
            with tempfile.NamedTemporaryFile(suffix='.hdf5', dir=out) as tmp:
                src = tar.extractfile(m)
                while chunk := src.read(1 << 24):
                    tmp.write(chunk)
                tmp.flush()
                try:
                    X, y, t = cut(tmp.name, rng)
                except Exception as e:                       # one bad member must not kill a 33 GB stream
                    print(f'SKIP {name}: {e}', flush=True); continue
            save(out, name, X, y, t, split_of.get(name, '?'))
            print(name, split_of.get(name, '?'), X.shape, flush=True)


if __name__ == '__main__':
    main()

"""Line A of the EMG plan: what one channel can do, measured on someone else's data first.

NinaPro DB6 (10 subjects, 5 days x 2 sessions, 14 Delsys channels at 2 kHz, 7 grasps + rest)
is the only public set with the exact failure we care about -- electrodes taken off and put
back the next day. This keeps ONE of its channels, decimates to our 1 kHz, cuts 2 s takes the
same shape usb_emg records, and runs the same features and the same LDA. Two numbers come out
per experiment, and their gap is the point:

  within   leave-one-out inside one session          (the number papers quote)
  next_day train on day N, test on day N+1 same slot (the number the wallet gate will see)

The paper on this set (arXiv 2607.27568, all 14 channels, a CNN) reports macro-F1 0.978
within and 0.688 across days. `--channels all` runs the same script on all 14 as a sanity
anchor; nobody expects LDA on hand features to match a CNN, only to land in the same story.

    python3 emg_public.py --check                            # synthetic .mat, no download
    python3 emg_public.py db6 --subject 1 --channel 1        # emg-public/DB6_s1_*.zip must exist
    python3 emg_public.py db6 --subject 1 --channels all     # 14-channel anchor
"""
import argparse
import io
import json
import re
import tempfile
import zipfile
from pathlib import Path

import numpy as np
from scipy.io import loadmat, savemat

import emg_model
import usb_emg

HERE = Path(__file__).resolve().parent
PUBLIC = HERE / 'emg-public'
DB6_HZ = 2000
TAKE = usb_emg.EMG_COUNT * DB6_HZ // usb_emg.EMG_HZ      # 4000 samples of DB6 -> one 2 s take
# DB6 emg is in volts. Pretend it went through the Cheez front end (+-2 mV full scale into a
# 12-bit ADC centred at 1.65 V) so usb_emg's features see the same units they will on the bench.
FULL_SCALE_V = 2e-3
# DB6's seven grasps keep their NinaPro catalogue numbers (not 1..7), so name them by number.
GRASPS = lambda k: 'rest' if k == 0 else f'grasp{k}'


def to_counts(volts):
    """Volts (2 kHz) -> int16 ADC counts (1 kHz), the shape usb_emg.load hands out."""
    x = np.asarray(volts, float)[::2]           # Delsys is band-limited ~450 Hz; nothing to alias
    counts = np.round(x / FULL_SCALE_V * (usb_emg.ADC_MAX / 2)) + usb_emg.ADC_MAX / 2
    return np.clip(counts, 0, usb_emg.ADC_MAX - 1).astype('<i2')


def takes(mat, channels, rest_per_session=12):
    """One 2 s take per contiguous label run, cut from its centre. Rest runs are the gaps
    between grasps -- seven per repetition -- so they are thinned to one per repetition,
    otherwise half the set is rest and any 'accuracy' is mostly the majority prior."""
    emg, label = mat['emg'], mat['restimulus'].ravel().astype(int)
    edges = np.flatnonzero(np.diff(label)) + 1
    grasps, rests = [], []
    for start, stop in zip(np.r_[0, edges], np.r_[edges, len(label)]):
        if stop - start < TAKE:
            continue
        mid = (start + stop) // 2
        window = emg[mid - TAKE // 2: mid + TAKE // 2]
        x = tuple(to_counts(window[:, c]) for c in channels)
        (rests if label[start] == 0 else grasps).append(
            {'label': GRASPS(label[start]), 'x': x if len(channels) > 1 else (x[0], 1000)})
    keep = np.linspace(0, len(rests) - 1, min(rest_per_session, len(rests))).round().astype(int)
    return grasps + [rests[i] for i in keep]


def features_multi(x):
    """Per-channel usb_emg features, concatenated -- the 14-channel anchor's extractor."""
    return np.concatenate([usb_emg.emg_features((c, 1000)) for c in x])


def live_channels(mat):
    """DB6 pads emg[] to 16 columns; two carry nothing."""
    return [c for c in range(mat['emg'].shape[1]) if mat['emg'][:, c].std() > 0]


def session_files(subject, folder=PUBLIC):
    """{(day, time): bytes-loader} from every DB6_s{subject}_*.zip present, without extracting."""
    found = {}
    for zpath in sorted(Path(folder).glob(f'DB6_s{subject}_*.zip')):
        z = zipfile.ZipFile(zpath)
        for name in z.namelist():
            m = re.search(rf'S{subject}_D(\d)_T(\d)\.mat$', name)
            if m:
                found[(int(m[1]), int(m[2]))] = (z, name)
    return found


def load_session(entry):
    z, name = entry
    return loadmat(io.BytesIO(z.read(name)), variable_names=['emg', 'restimulus'])


def _accuracy(records, extract, train=None):
    """LOO on `records` alone, or fit `train` and score `records`."""
    vec = lambda rows: np.stack([extract(r['x']) for r in rows])
    if train is None:
        v, t = vec(records), [r['label'] for r in records]
        return emg_model._report(t, emg_model._leave_one_out_generic(v, t), sorted(set(t)))
    tv, tt = vec(train), [r['label'] for r in train]
    model = emg_model._fit_generic(tv, tt)
    truth = [r['label'] for r in records]
    return emg_model._report(truth, emg_model.predict(model, vec(records)), model['classes'])


def experiment(sessions, channels, rng=None, binary=False):
    """sessions: {(day, time): mat}. Returns within-session LOO per session, next-day transfer
    per consecutive (day, day+1) pair at the same time slot, and a shuffled-label control."""
    extract = features_multi if len(channels) > 1 else (lambda x: usb_emg.emg_features(x))
    data = {k: takes(m, channels) for k, m in sessions.items()}
    if binary:      # the wallet gate's question: is there effort at all, not which grasp
        data = {k: [dict(r, label='rest' if r['label'] == 'rest' else 'grasp') for r in v] for k, v in data.items()}
    within = {f'D{d}_T{t}': _accuracy(v, extract) for (d, t), v in sorted(data.items())}
    next_day = {}
    for (d, t), v in sorted(data.items()):
        if (d + 1, t) in data:
            next_day[f'D{d}->D{d + 1}_T{t}'] = _accuracy(data[(d + 1, t)], extract, train=v)
    first = data[min(data)]
    rng = rng or np.random.default_rng(0)
    shuffled = [dict(r, label=str(l)) for r, l in zip(first, rng.permutation([r['label'] for r in first]))]
    return {'channels': list(channels), 'takes_per_session': {f'D{d}_T{t}': len(v) for (d, t), v in sorted(data.items())},
            'within': within, 'next_day': next_day,
            'shuffled_control': _accuracy(shuffled, extract)}


def db6(subject, channels, binary=False):
    files = session_files(subject)
    if not files:
        raise SystemExit(f'{PUBLIC} 里没有 DB6_s{subject}_*.zip；先下 https://ninapro.hevs.ch/files/DB6_Preproc/DB6_s{subject}_a.zip')
    sessions = {k: load_session(v) for k, v in files.items()}
    if channels == 'all':
        channels = live_channels(sessions[min(sessions)])
    result = experiment(sessions, channels, binary=binary)
    result.update(subject=subject, binary=binary, sessions=[f'D{d}_T{t}' for d, t in sorted(files)],
                  note='within = 同 session LOO；next_day = 训练前一天、测后一天同时段；'
                       '文献 14ch CNN：0.978 / 0.688（macro-F1）')
    return result


def _synthetic_session(rng, day):
    """Fake DB6: 7 grasps + rest, 12 reps, each grasp its own band/amplitude on every channel.
    Day 2 shifts every channel's gain by a random factor -- a caricature of re-seating."""
    hz, hold, gap = DB6_HZ, 3 * DB6_HZ, 2 * DB6_HZ
    gain = rng.uniform(.6, 1.4, 14) if day > 1 else np.ones(14)
    emg, label = [], []
    for rep in range(12):
        for k in range(1, 8):
            emg.append(rng.normal(0, 2e-6, (gap, 14))); label += [0] * gap
            burst = rng.normal(0, 1, (hold, 14))
            spec = np.fft.rfft(burst, axis=0); f = np.fft.rfftfreq(hold, 1 / hz)
            spec[(f < 20 + 15 * k) | (f > 80 + 40 * k)] = 0
            burst = np.fft.irfft(spec, hold, axis=0)
            burst /= np.abs(burst).max(0) + 1e-12
            emg.append(burst * (2e-4 + 1e-4 * k) * gain + rng.normal(0, 2e-6, (hold, 14)))
            label += [k] * hold
    emg.append(rng.normal(0, 2e-6, (gap, 14))); label += [0] * gap
    return {'emg': np.vstack(emg), 'restimulus': np.array(label)[:, None]}


def check():
    rng = np.random.default_rng(20260923)
    sessions = {(1, 1): _synthetic_session(rng, 1), (2, 1): _synthetic_session(rng, 2)}
    with tempfile.TemporaryDirectory() as tmp:
        # Through a real zip + .mat round trip so session_files/load_session are exercised.
        with zipfile.ZipFile(Path(tmp) / 'DB6_s9_a.zip', 'w') as z:
            for (d, t), m in sessions.items():
                buf = io.BytesIO(); savemat(buf, m); z.writestr(f'DB6_s9_a/S9_D{d}_T{t}.mat', buf.getvalue())
        files = session_files(9, tmp)
        assert set(files) == {(1, 1), (2, 1)}, files
        loaded = {k: load_session(v) for k, v in files.items()}
    one = experiment(loaded, [3], rng)
    assert one['takes_per_session']['D1_T1'] == 12 * 7 + 12, one['takes_per_session']
    assert one['within']['D1_T1']['accuracy'] >= .9, one['within']
    assert one['shuffled_control']['accuracy'] < .3, one['shuffled_control']    # 8 balanced classes, chance 1/8
    # Must fail: the day-2 gain shift has to cost something on one channel, or "next_day"
    # is not measuring what its name says.
    assert one['next_day']['D1->D2_T1']['accuracy'] < one['within']['D1_T1']['accuracy'], one['next_day']
    all14 = experiment(loaded, list(range(14)), rng)
    assert all14['within']['D1_T1']['accuracy'] >= .9, all14['within']
    print('DB6 loader: zip/.mat round trip, take cutting, one-channel vs 14-channel, '
          'next-day drop and shuffled control passed')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--check', action='store_true')
    sub = parser.add_subparsers(dest='command')
    d = sub.add_parser('db6'); d.add_argument('--subject', type=int, default=1)
    d.add_argument('--channel', type=int, default=1, help='0-based column of the 16 in emg[]')
    d.add_argument('--channels', help='"all" for the 14-channel anchor, "each" for one row per channel')
    d.add_argument('--binary', action='store_true', help='rest vs any grasp (effort detection, 2 classes)')
    args = parser.parse_args()
    if args.check:
        check()
    elif args.command == 'db6' and args.channels == 'each':
        # Nobody documents which DB6 column sits over the flexor; ask all fourteen.
        files = session_files(args.subject)
        sessions = {k: load_session(v) for k, v in files.items()}
        live = live_channels(sessions[min(sessions)])
        print(f'live columns: {live}')
        print(f"{'ch':>3} {'within D1_T1':>13} {'D1->D2_T1':>10} {'shuffled':>9}   (balanced accuracy = mean per-class recall)")
        for c in live:
            r = experiment(sessions, [c], binary=args.binary)
            w = r['within'].get('D1_T1', {}).get('balanced', float('nan'))
            n = r['next_day'].get('D1->D2_T1', {}).get('balanced', float('nan'))
            print(f'{c:>3} {w:>13.3f} {n:>10.3f} {r["shuffled_control"]["balanced"]:>9.3f}', flush=True)
    elif args.command == 'db6':
        print(json.dumps(db6(args.subject, 'all' if args.channels == 'all' else [args.channel], args.binary), ensure_ascii=False, indent=2))
    else:
        parser.error('--check 或 db6')

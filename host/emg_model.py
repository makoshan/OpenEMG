"""Trainer and verdict for the one-channel EMG task: shrinkage LDA over usb_emg's features.

The gate (pipeline.py gate --task emg) has already said whether the classes can be told
apart on these eleven numbers; this only draws the boundary. LDA because thirty takes per
class is a handful, eleven features is nothing, and a linear boundary on named features is
a model you can read back ("fist is rms and hold_ratio") -- the same reason the board runs
a threshold detector for punches.

Two accuracies come out, and only the second one is the verdict:
  loo     leave-one-out on the recording session itself (optimistic: same electrode seat)
  rewear  emg-data-rewear/: strap off, electrodes back on, every class recorded again.
          Literature on 16-channel bands loses ~30 points here; one channel has no spatial
          redundancy to soften that, which is why it is the acceptance number.

    python3 emg_model.py --check            # synthetic, no hardware
    python3 pipeline.py auto --task emg     # gate -> train -> evaluate
"""
import argparse
import json
import tempfile
import time
from pathlib import Path

import numpy as np

import usb_emg

HERE = Path(__file__).resolve().parent
LABELS = ('rest', 'light', 'hard')     # the three tiers the phone-side gate is locked to (ADR 2026-09-23)
REWEAR = HERE / 'emg-data-rewear'
MIN_TAKES = 5           # same floor separability.report uses to call a class a class
# ponytail: fixed blend toward the identity; fit it (Ledoit-Wolf) if takes ever pass ~100/class
SHRINKAGE = .1
NAMES = tuple(usb_emg.EMG_FEATURES)


def _vectors(records, labels):
    rows = [r for r in records if r['label'] in labels]
    if not rows:
        return np.zeros((0, len(NAMES))), []
    return np.stack([usb_emg.emg_features(r['x']) for r in rows]), [r['label'] for r in rows]


def _fit_generic(vectors, truth):
    """Shrinkage LDA on any feature count; _fit is the eleven-feature name the task uses."""
    classes = sorted(set(truth))
    mean, scale = vectors.mean(0), np.maximum(vectors.std(0), 1e-9)
    z = (vectors - mean) / scale
    groups = [z[[t == k for t in truth]] for k in classes]
    means = np.stack([g.mean(0) for g in groups])
    within = sum(np.cov(g.T, ddof=1) * (len(g) - 1) for g in groups) / (len(truth) - len(classes))
    d = vectors.shape[1]
    # A dead channel (or a constant feature) leaves a zero row; the ridge keeps inv() alive
    # and the class means still carry whatever the rest of the features know.
    within = (1 - SHRINKAGE) * within + (SHRINKAGE * np.trace(within) / d + 1e-6) * np.eye(d)
    priors = np.array([len(g) / len(truth) for g in groups])
    return {'classes': classes, 'mean': mean, 'scale': scale, 'means': means,
            'precision': np.linalg.inv(within), 'log_prior': np.log(priors)}


def _fit(vectors, truth):
    assert vectors.shape[1] == len(NAMES), vectors.shape
    return _fit_generic(vectors, truth)


def _scores(model, vectors):
    z = (np.atleast_2d(vectors) - model['mean']) / model['scale']
    w = model['means'] @ model['precision']
    b = -.5 * np.einsum('kd,kd->k', w, model['means']) + model['log_prior']
    return z @ w.T + b


def predict(model, vectors):
    return [model['classes'][i] for i in _scores(model, vectors).argmax(1)]


def _leave_one_out_generic(vectors, truth):
    out = []
    for i in range(len(truth)):
        keep = [j for j in range(len(truth)) if j != i]
        out.append(predict(_fit_generic(vectors[keep], [truth[j] for j in keep]), vectors[i])[0])
    return out


_leave_one_out = _leave_one_out_generic


def _report(truth, predicted, classes):
    confusion = {a: {b: sum(t == a and p == b for t, p in zip(truth, predicted)) for b in classes}
                 for a in classes}
    recall = {k: round(confusion[k][k] / max(sum(confusion[k].values()), 1), 3) for k in classes}
    # Balanced = mean per-class recall: with 84 grasps to 12 rests, plain accuracy is
    # mostly the majority prior (a shuffled-label control scores 0.875 on it).
    return {'accuracy': round(sum(t == p for t, p in zip(truth, predicted)) / len(truth), 3),
            'balanced': round(sum(recall.values()) / len(classes), 3),
            'takes': len(truth), 'confusion': confusion, 'recall': recall}


def train(records, labels, output):
    vectors, truth = _vectors(records, labels)
    counts = {k: truth.count(k) for k in labels}
    usable = [k for k in labels if counts[k] >= MIN_TAKES]
    if len(usable) < 2:
        raise ValueError(f'训练要至少两类、每类 ≥{MIN_TAKES} 条；现在 {counts}')
    keep = [i for i, t in enumerate(truth) if t in usable]
    vectors, truth = vectors[keep], [truth[i] for i in keep]
    model = _fit(vectors, truth)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    np.savez(output / 'model.npz', classes=np.array(model['classes']),
             **{k: v for k, v in model.items() if k != 'classes'})
    meta = {'task': 'emg', 'labels': model['classes'], 'features': list(NAMES), 'takes': counts,
            'profile': profile(vectors, truth),
            'loo': _report(truth, _leave_one_out(vectors, truth), model['classes']),
            'status': 'trained', 'sensor': 'Cheez sEMG-D', 'emg_hz': usb_emg.EMG_HZ,
            'shrinkage': SHRINKAGE, 'created_at': time.strftime('%Y-%m-%dT%H:%M:%S')}
    (output / 'metadata.json').write_text(json.dumps(meta, ensure_ascii=False, indent=2) + '\n')
    return meta


def profile(vectors, truth, feature='rms'):
    """CalibrationProfile for the phone-side gate: two rms thresholds cut between adjacent tiers,
    each placed halfway between the lower tier's 95th percentile and the upper tier's 5th. The
    gap (upper 5th - lower 95th) is reported too: negative means the tiers overlap on rms alone
    and the threshold gate will misfire whatever the LDA says. This is the recipe the ADR ships;
    the LDA above is the offline check that the tiers are separable at all."""
    col = vectors[:, NAMES.index(feature)]
    order = [k for k in LABELS if k in truth]
    cuts = {}
    for lo, hi in zip(order, order[1:]):
        a = np.percentile(col[[t == lo for t in truth]], 95); b = np.percentile(col[[t == hi for t in truth]], 5)
        cuts[f'{lo}_{hi}'] = {'threshold': float((a + b) / 2), 'gap': float(b - a)}
    return {'feature': feature, 'unit': 'V rms of the 2 s take', 'tiers': order, 'cuts': cuts,
            'hysteresis': 'phone applies on/off at threshold ×1.0 / ×0.7; lead-off = off'}


def load_model(model_dir):
    with np.load(Path(model_dir) / 'model.npz', allow_pickle=False) as blob:
        model = {k: blob[k] for k in blob.files}
    model['classes'] = [str(k) for k in model['classes']]
    return model


def evaluate(model_dir, rewear=REWEAR, records=None):
    model = load_model(model_dir)
    meta = json.loads((Path(model_dir) / 'metadata.json').read_text())
    report = {'loo': meta['loo'], 'rewear': None}
    if records is None:
        records = usb_emg.load(rewear) if Path(rewear).exists() else []
    vectors, truth = _vectors(records, model['classes'])
    if not truth:
        report['message'] = (f'跨佩戴集还没录（{rewear}）：摘下、重贴、每类 ≥{MIN_TAKES} 条再录一遍——'
                             f'同佩戴 LOO {meta["loo"]["accuracy"]:.0%} 不是验收数')
        return report
    report['rewear'] = _report(truth, predict(model, vectors), model['classes'])
    report['message'] = f'同佩戴 LOO {meta["loo"]["accuracy"]:.0%} / 跨佩戴 {report["rewear"]["accuracy"]:.0%}（验收看后者）'
    return report


def check():
    rng = np.random.default_rng(20260923)
    synth = lambda kinds, n, rng: [{'label': k, 'x': (usb_emg._synth(k, rng), 1000)}
                                   for k in kinds for _ in range(n)]
    records = synth(LABELS, 12, rng)
    with tempfile.TemporaryDirectory() as tmp:
        meta = train(records, LABELS, Path(tmp) / 'm')
        assert meta['labels'] == sorted(LABELS) and meta['loo']['accuracy'] >= .9, meta['loo']
        cuts = meta['profile']['cuts']
        assert set(cuts) == {'rest_light', 'light_hard'} and all(c['gap'] > 0 for c in cuts.values()), cuts
        assert cuts['rest_light']['threshold'] < cuts['light_hard']['threshold'], cuts
        model = load_model(Path(tmp) / 'm')
        vectors, truth = _vectors(records, LABELS)
        assert predict(model, vectors) == predict(_fit(vectors, truth), vectors), '存盘后的模型和内存里的不一样'
        # A different seed is a different "wearing" only in the synth's imagination; what it
        # proves is that evaluate() reads the rewear set and scores it, not that we generalise.
        report = evaluate(Path(tmp) / 'm', records=synth(LABELS, 6, np.random.default_rng(7)))
        assert report['rewear']['accuracy'] >= .9, report
        assert evaluate(Path(tmp) / 'm', rewear=Path(tmp) / 'nowhere')['rewear'] is None
        # Must fail: one class is not a classification problem, and shuffled labels must
        # not train into anything better than chance -- otherwise LOO is leaking.
        try:
            train(synth(('hard',), 12, rng), LABELS, Path(tmp) / 'one')
        except ValueError as error:
            assert '至少两类' in str(error), error
        else:
            raise AssertionError('只有一类也训出了模型')
        shuffled = [dict(r, label=str(l)) for r, l in zip(records, rng.permutation(truth))]
        assert train(shuffled, LABELS, Path(tmp) / 'shuf')['loo']['accuracy'] < .6, '打乱标签还能训准，LOO 在泄漏'
    print('EMG trainer: fit/round-trip/rewear evaluation and both refusals passed')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--check', action='store_true', help='synthetic self-test, no hardware')
    if not parser.parse_args().check:
        parser.error('训练与验收走 pipeline.py：auto/train/evaluate --task emg')
    check()

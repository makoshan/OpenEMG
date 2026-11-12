"""Pre-training gate: can these classes be told apart at all, and is the capture drifting?

Runs on the recorded takes only -- no training, no TensorFlow, about a second on a few hundred
takes -- so it can run after every saved take instead of after an hour of training. It answers the
two questions a trained model's accuracy number does not: WHICH pair of classes is collapsing, and
WHICH physical axis would have had to separate them. `evaluate --model` still has the last word;
this is what stops you from getting there with data that was never going to work.
"""
import math

import numpy as np

import gesture_model as gm

# Axis convention (device/main.cpp, punch_detect.h): X = forearm toward the knuckles,
# Y = thumb side, Z = back of the wrist. Names are physical on purpose: the verdict has to say
# which axis to fix, not which feature index.
FEATURES = {
    'accel_peak_x': '前臂方向冲击峰值',
    'accel_peak_y': '拇指方向冲击峰值',
    'accel_peak_z': '手背方向冲击峰值',
    'gyro_rms_x': '绕前臂轴转动（手腕内外翻）',
    'gyro_rms_y': '绕拇指轴转动（上下摆）',
    'gyro_rms_z': '绕手背轴转动（左右摆）',
    'push_x': '前臂方向净冲量（推出为正）',
    'recoil_x': '回撤比（反向峰 / 正向峰）',
    'motion_seconds': '有效运动时长',
    'gravity_x': '前臂相对重力的平均朝向',
    'gravity_y': '拇指相对重力的平均朝向（握拳朝向）',
    'roll_share': '绕前臂轴占总转动的比例',
}
# Tried and rejected 2026-09-17: deepseek-flash read this file and argued roll_share is unsigned, so
# a pronate-then-supinate hook cancels itself out and a SIGNED net rotation would separate hook from
# uppercut. Measured on the 40 real takes: net deg about each axis gives d' 0.23/0.37/0.26 -- about
# 45% overlap, worse than the unsigned share's 1.51. The critique was reasonable and wrong; do not
# re-add signed net rotation without new evidence.
NAMES = tuple(FEATURES)
MOTION_DPS = 30          # same floor the collector screens takes with
# d' is a mean gap in pooled standard deviations, so the overlap it leaves is Phi(-d'/2): d'=1.5
# still leaves 23% of the two classes on top of each other, which is why a "looks separated" plot
# lies. 2.56 is the d' that gets that overlap down to 10%; below it, no threshold on that one axis
# can save the pair, and more takes of the same gesture will not move it.
WEAK_SEPARATION = 2.56
CONFUSION_BLOCK = .20    # a fifth of one class landing on the other: do not train yet
CONFUSION_WARN = .10


def features(x):
    """Twelve named physical features of one cropped take; x is (points, 6) as g and deg/s."""
    x = gm.crop(np.asarray(x, dtype=np.float32))
    accel, gyro = x[:, :3], x[:, 3:]
    gravity = accel.mean(0)
    dynamic = accel - gravity
    speed = np.linalg.norm(gyro, axis=1)
    forward = dynamic[:, 0]
    rotation = np.abs(gyro).sum(0) + 1e-6
    return np.array([
        np.abs(dynamic[:, 0]).max(), np.abs(dynamic[:, 1]).max(), np.abs(dynamic[:, 2]).max(),
        *np.sqrt((gyro**2).mean(0)),
        forward.sum() / gm.PROFILE['hz'],
        -forward.min() / max(forward.max(), 1e-6),
        float((speed > MOTION_DPS).sum()) / gm.PROFILE['hz'],
        gravity[0], gravity[1],
        rotation[0] / rotation.sum(),
    ], dtype=np.float64)


def overlap(dprime):
    """Share of the two classes that still sits on top of each other along the best single axis."""
    return .5 * math.erfc(dprime / (2 * math.sqrt(2)))


def _dprime(a, b):
    """Per-feature separation between two classes: mean gap in pooled standard deviations."""
    spread = np.sqrt((a.var(0, ddof=1) + b.var(0, ddof=1)) / 2)
    return np.abs(a.mean(0) - b.mean(0)) / np.maximum(spread, 1e-9)


def _leave_one_out(vectors, labels):
    """Nearest-neighbour label for each take, excluding itself. No model, no fitting."""
    scale = vectors.std(0)
    z = vectors / np.maximum(scale, 1e-9)
    distance = np.linalg.norm(z[:, None, :] - z[None, :, :], axis=2)
    np.fill_diagonal(distance, np.inf)
    return [labels[i] for i in distance.argmin(1)]


def report(records, minimum=5, extract=None, catalog=None):
    """records: dicts with 'label' and 'x' (as load_records returns). Cheap enough per take.
    extract/catalog swap in another sensor's named features; the gate logic is the same."""
    extract, catalog = extract or features, catalog or FEATURES
    names = tuple(catalog)
    usable = [r for r in records if r.get('x') is not None]
    labels = sorted({r['label'] for r in usable})
    classes = [k for k in labels if sum(r['label'] == k for r in usable) >= minimum]
    if len(classes) < 2:
        return {'status': 'pending', 'pairs': [], 'classes': classes,
                'message': f'每类至少 {minimum} 条才能判断可分性。'}
    rows = [r for r in usable if r['label'] in classes]
    vectors = np.stack([extract(r['x']) for r in rows])
    truth = [r['label'] for r in rows]
    predicted = _leave_one_out(vectors, truth)
    by_class = {k: vectors[[i for i, t in enumerate(truth) if t == k]] for k in classes}

    pairs = []
    for i, a in enumerate(classes):
        for b in classes[i+1:]:
            wrong = sum(t == a and p == b for t, p in zip(truth, predicted)) \
                  + sum(t == b and p == a for t, p in zip(truth, predicted))
            rate = wrong / (len(by_class[a]) + len(by_class[b]))
            separation = _dprime(by_class[a], by_class[b])
            best = int(separation.argmax())
            pairs.append({
                'classes': [a, b], 'confusion': round(rate, 3), 'confused_takes': wrong,
                'best_feature': names[best], 'best_feature_label': catalog[names[best]],
                'best_separation': round(float(separation[best]), 2),
                'best_feature_overlap': round(overlap(float(separation[best])), 3),
                'status': 'block' if rate >= CONFUSION_BLOCK else 'warn' if rate >= CONFUSION_WARN else 'ok',
            })
    pairs.sort(key=lambda p: -p['confusion'])
    worst = pairs[0]
    status = worst['status']
    accuracy = sum(t == p for t, p in zip(truth, predicted)) / len(truth)
    if status == 'ok':
        message = f'各类在这组特征上可分（最近邻自检 {accuracy:.0%}），可以进入训练。'
    else:
        a, b = worst['classes']
        weak = worst['best_separation'] < WEAK_SEPARATION
        message = (f'{a} 和 {b} 有 {worst["confused_takes"]} 条互相落到对方（{worst["confusion"]:.0%}）。'
                   f'最能分开它们的是「{worst["best_feature_label"]}」，d′ 只有 {worst["best_separation"]}，'
                   f'单看这一路还有 {worst["best_feature_overlap"]:.0%} 重叠'
                   + ('：再多录同样的动作也不会变，这两类在当前佩戴位置、当前这一路传感器上'
                      '本来就分不开。换佩戴位置、加一路别的信号，或者合并成一类——先别训。'
                      if weak else '：还有余量，先检查采集时这两类的做法是不是串了。'))
    return {'status': status, 'pairs': pairs, 'classes': classes,
            'nn_accuracy': round(accuracy, 3), 'takes': len(rows), 'message': message}


AUDIO_FEATURES = {
    'peak': '峰值（满量程占比）',
    'crest': '波峰因数（峰值 / 有效值）',
    'attack_ms': '起振时间',
    'decay_ms': '衰减到 -20 dB 的时间',
    'hf_ratio': '高频能量占比（2 kHz 以上）',
    'zcr': '过零率（频心高低）',
    'burst_count': '独立冲击次数',
    'active_ms': '有效发声时长',
}
AUDIO_RATE = 16000


def audio_features(pcm, rate=AUDIO_RATE):
    """Eight named features of one impulse take. A snap, a clap and a knock differ in attack,
    decay and spectral tilt, not in loudness, so loudness is deliberately only one of the eight."""
    x = np.asarray(pcm, dtype=np.float64)
    x = x - x.mean()
    step = max(rate // 1000, 1)                      # 1 ms envelope
    frames = x[:len(x) - len(x) % step].reshape(-1, step)
    envelope = np.abs(frames).max(1)
    peak = envelope.max()
    if peak <= 0:
        return np.zeros(len(AUDIO_FEATURES))
    rms = np.sqrt((x**2).mean()) + 1e-9
    # First difference is a one-pole high pass: its share of the energy is the spectral tilt,
    # which is what separates a snap's 2-6 kHz crack from a clap's lower, broader slap.
    difference = np.diff(x)
    hf_ratio = float((difference**2).sum() / ((x**2).sum() * 4 + 1e-9))
    loud = envelope > peak * .1
    top = int(envelope.argmax())
    rise = np.flatnonzero(envelope[:top + 1] >= peak * .1)
    after = np.flatnonzero(envelope[top:] <= peak * .1)
    burst, previous = 0, -10
    for i in np.flatnonzero(envelope > peak * .5):
        if i - previous > 30:                        # 30 ms apart counts as a second hit
            burst += 1
        previous = i
    window = x[top * step:(top + 60) * step]         # 60 ms from the peak
    zcr = float((np.diff(np.sign(window)) != 0).mean()) if len(window) > 1 else 0.
    return np.array([
        peak / 32768, peak / rms,
        float(top - rise[0]) if len(rise) else 0.,
        float(after[0]) if len(after) else float(len(envelope) - top),
        hf_ratio, zcr, float(burst), float(loud.sum()),
    ], dtype=np.float64)


def capture_drift(records):
    """The failure EI can never see: the capture firmware itself degrading between sessions."""
    sessions = {}
    for r in records:
        quality = r.get('quality') or {}
        if 'max_sample_gap_ms' not in quality:
            continue
        row = sessions.setdefault(r.get('session', '?'), {'takes': 0, 'lost': 0, 'worst_gap': 0})
        row['takes'] += 1
        row['lost'] += quality.get('lost', 0)
        row['worst_gap'] = max(row['worst_gap'], quality['max_sample_gap_ms'])
    # 52 Hz is a 19.2 ms period; the window() gate only rejects above 80 ms, so a firmware that
    # drifts to 30-40 ms passes every take one by one and still ruins the set.
    bad = {k: v for k, v in sessions.items() if v['worst_gap'] > 25 or v['lost']}
    return {'sessions': sessions, 'degraded': bad,
            'status': 'warn' if bad else 'ok',
            'message': ('采集正常：所有场次的采样间隔都在 52 Hz 名义值附近。' if not bad else
                        '这些场次的采样间隔或丢帧超出 52 Hz 名义值，问题在采集固件不在模型：'
                        + '、'.join(f'{k}（最大间隔 {v["worst_gap"]} ms，丢 {v["lost"]} 帧）' for k, v in bad.items()))}


def demo():
    rng = np.random.default_rng(0)
    def take(spin, push):
        x = rng.normal(0, .05, (gm.POINTS, 6)).astype(np.float32)
        x[:, 2] += 1
        x[80:120, 0] += push; x[120:140, 0] -= push/2; x[80:130, 3] += spin
        return x
    separable = [{'label': 'punch', 'x': take(0, 3)} for _ in range(8)] + \
                [{'label': 'twist', 'x': take(400, 0)} for _ in range(8)]
    assert report(separable)['status'] == 'ok', report(separable)['message']
    identical = [{'label': 'hook', 'x': take(200, 1)} for _ in range(8)] + \
                [{'label': 'uppercut', 'x': take(200, 1)} for _ in range(8)]
    blocked = report(identical)
    assert blocked['status'] == 'block' and '先别训' in blocked['message'], blocked
    assert report([{'label': 'hook', 'x': take(0, 1)}])['status'] == 'pending'
    drift = capture_drift([{'session': 'a', 'quality': {'max_sample_gap_ms': 20, 'lost': 0}},
                           {'session': 'b', 'quality': {'max_sample_gap_ms': 38, 'lost': 3}}])
    assert drift['status'] == 'warn' and 'b' in drift['degraded'] and 'a' not in drift['degraded']
    rate = AUDIO_RATE
    def impulse(decay_ms, tilt):
        t = np.arange(rate * 2) / rate
        noise = rng.normal(0, .02, t.size)
        onset = int(.9 * rate)
        env = np.zeros(t.size); span = np.arange(t.size - onset)
        env[onset:] = np.exp(-span / (decay_ms * rate / 1000))
        carrier = np.sin(2 * np.pi * tilt * t) * (1 + rng.normal(0, .05, t.size))
        return ((noise + 8 * env * carrier) * 3000).astype(np.int16)
    audio = [{'label': 'snap', 'x': impulse(35, 4200)} for _ in range(6)] + \
            [{'label': 'clap', 'x': impulse(180, 900)} for _ in range(6)]
    sound = report(audio, extract=audio_features, catalog=AUDIO_FEATURES)
    assert sound['status'] == 'ok', sound['message']
    same = [{'label': 'snap', 'x': impulse(35, 4200)} for _ in range(6)] + \
           [{'label': 'clap', 'x': impulse(35, 4200)} for _ in range(6)]
    assert report(same, extract=audio_features, catalog=AUDIO_FEATURES)['status'] == 'block'
    print('PASS: separable classes clear, identical classes blocked with a named axis, drift flagged, '
          'audio features separate a short bright impulse from a long dull one')


if __name__ == '__main__':
    import argparse, json
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data')
    parser.add_argument('--demo', action='store_true')
    args = parser.parse_args()
    if args.demo or not args.data:
        demo()
    else:
        records, _ = gm.load_records(args.data)
        print(json.dumps({'separability': report(records), 'capture': capture_drift(records)},
                         ensure_ascii=False, indent=2))

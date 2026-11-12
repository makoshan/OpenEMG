"""MAKO left-wrist gesture data, Keras training and independent evaluation.

Run with .venv-gesture/bin/python. No cloud upload or firmware flashing.
"""
import argparse
import asyncio
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone

import numpy as np
from bleak.exc import BleakError

ALL_LABELS = ('circle', 'up_wave', 'punch', 'other', 'uppercut', 'hook')
ALL_NAMES = ('画圈', '上挥手', '直拳', '其他动作', '上勾拳', '摆拳')
# Threshold-calibration takes for the Punch-Out control line. No model is ever trained on these --
# calibrate.py turns them into constants for punch_detect.h -- so they keep their own dataset root
# (punch-data/) and stay out of the `--labels` default, which remains the gesture class set.
# They share this file's capture contract and record validation, and nothing else.
CONTROL_LABELS = ('guard', 'duck', 'dodge_left', 'dodge_right', 'punch_high', 'punch_body')
CONTROL_NAMES = ('格挡', '下蹲', '左闪避', '右闪避', '上段拳', '身体拳')
KNOWN_LABELS = ALL_LABELS + CONTROL_LABELS
KNOWN_NAMES = ALL_NAMES + CONTROL_NAMES
LABELS, NAMES = ALL_LABELS, ALL_NAMES
# hook/uppercut/punch are not separable on the left wrist's six axes (separability.py on
# gesture-data-4s: d' 1.51, 23% overlap, "more of the same will not change it"), so a run can
# fold them into one class. The fold happens at load time only -- the take keeps its own label
# and `action` on disk, so the same dataset still trains the six-class run.
MERGE = {}


def set_labels(labels, merge=None):
    """Choose the class set for this run (train --labels/--merge, or a model's metadata)."""
    global LABELS, NAMES, MERGE
    labels = tuple(labels)
    if len(labels) < 2 or any(l not in KNOWN_LABELS for l in labels) or len(set(labels)) != len(labels):
        raise ValueError(f'labels must be distinct entries of {KNOWN_LABELS}')
    merge = dict(merge or {})
    for source, target in merge.items():
        if source not in KNOWN_LABELS or source in labels or target not in labels:
            raise ValueError(f'merge {source}->{target}: source must be a class left out of '
                             f'{labels}, target one of them')
    LABELS = labels; NAMES = tuple(KNOWN_NAMES[KNOWN_LABELS.index(l)] for l in labels); MERGE = merge
SPLITS = ('train', 'validation', 'test')
WINDOW_SECONDS = 4
CAPTURE_SECONDS = WINDOW_SECONDS + .05
REST_SECONDS = 3
POINTS = 52 * WINDOW_SECONDS
WINDOW_POINTS = 104  # 2 s classification window cut from each POINTS-row take at peak motion
PROFILE = {'hz': 52, 'accel_unit': 'g', 'gyro_unit': 'deg/s',
           'accel_range_g': 8, 'gyro_range_dps': 1000, 'points': POINTS}


def write_json(path, value, *, replace=False):
    """Durable atomic publication; existing captures are never overwritten."""
    path = Path(path)
    payload = json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent,
                                         prefix='.'+path.name, delete=False) as f:
            temporary = Path(f.name)
            f.write(payload)
            f.flush()
            os.fsync(f.fileno())
        if replace:
            os.replace(temporary, path)
        else:
            os.link(temporary, path)
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def window(samples):
    """Validate physical data before bounded interpolation; retain gravity."""
    if not isinstance(samples, list) or not POINTS-9 <= len(samples) <= POINTS+11:
        raise ValueError(f'Need {POINTS-9}..{POINTS+11} samples covering a {WINDOW_SECONDS}-second window')
    times = [0]
    lost = 0
    timing = set()
    for i, sample in enumerate(samples):
        if (not isinstance(sample,dict) or not isinstance(sample.get('axes'),list)
                or len(sample['axes'])!=6 or any(type(v) not in (int,float) for v in sample['axes'])):
            raise ValueError('Invalid six-axis values')
        for key, limit in (('seq', 65535), ('ms', 4294967295)):
            if type(sample.get(key)) is not int or not 0 <= sample[key] <= limit:
                raise ValueError('Invalid integer sequence/timestamp')
        timing.add(sample.get('timing_source'))
        if i:
            dt = (sample['ms'] - samples[i-1]['ms']) & 0xffffffff
            ds = (sample['seq'] - samples[i-1]['seq']) & 0xffff
            if not 0 < dt <= 80 or not 0 < ds <= 3:
                raise ValueError('IMU gap/reset/duplicate; repeat recording')
            lost += ds - 1
            times.append(times[-1] + dt)
    if len(timing) != 1 or not timing <= {'host_read_ms', 'fifo_nominal_52hz'}:
        raise ValueError('Missing or mixed IMU timing source')
    if not WINDOW_SECONDS*1000-100 <= times[-1] <= WINDOW_SECONDS*1000+100 or lost / (len(samples)+lost) > .02:
        raise ValueError('Duration or sample loss outside training limits')
    axes = np.asarray([s['axes'] for s in samples], dtype=np.float32)
    if axes.shape != (len(samples), 6) or not np.isfinite(axes).all():
        raise ValueError('Invalid/non-finite six-axis data')
    if (np.abs(axes[:, :3]) >= 7.80).any() or (np.abs(axes[:, 3:]) >= 1100).any():
        raise ValueError('Near sensor saturation; change hardware range and protocol before training')
    # Fixed 52 Hz grid, the same one edge_window() and the device use. linspace over the
    # take's own span stretched every gesture by its capture length (1-6%) and made the
    # Keras and Edge Impulse tensors differ for the same recording.
    target = np.arange(POINTS)*1000/PROFILE['hz']
    if times[-1] < target[-1]:
        raise ValueError('Capture too short for the fixed 52Hz window')
    result = np.stack([np.interp(target, times, axes[:, k]) for k in range(6)], axis=1)
    quality = {'samples': len(samples), 'span_ms': times[-1], 'lost': lost,
               'max_sample_gap_ms': max(np.diff(times)).item(),
               'timing_source': next(iter(timing)),
               'accel_peak_g': float(np.abs(axes[:, :3]).max()),
               'gyro_peak_dps': float(np.abs(axes[:, 3:]).max())}
    return result.astype(np.float32), quality


def crop(x):
    """Cut the WINDOW_POINTS rows with the most motion energy; the same cut is used to train,
    evaluate, predict, stream and on the device, so a 4 s take is not mostly stillness."""
    x = np.asarray(x, dtype=np.float32)
    if x.shape[0] == WINDOW_POINTS:
        return x
    if x.shape[0] < WINDOW_POINTS:
        raise ValueError('Take shorter than the classification window')
    energy = np.abs(x[:, :3] - x[:, :3].mean(0)).sum(1) + np.abs(x[:, 3:]).sum(1) / 300
    smooth = np.convolve(energy, np.ones(WINDOW_POINTS) / WINDOW_POINTS, 'valid')
    start = int(smooth.argmax())
    return x[start:start + WINDOW_POINTS]


def fingerprint(samples):
    # Same physical sequence cannot be reused by renaming or shifting timestamps.
    axes = np.asarray([s['axes'] for s in samples],dtype='<f4')
    relative = np.asarray([(s['ms']-samples[0]['ms']) & 0xffffffff for s in samples],dtype='<u4')
    return hashlib.sha256(relative.tobytes()+axes.tobytes()).hexdigest()


def edge_window(samples):
    """One quality gate for capture and exact-rate Edge Impulse export."""
    window(samples)
    target = np.arange(POINTS)*1000/PROFILE['hz']
    times = np.array([(s['ms']-samples[0]['ms']) & 0xffffffff for s in samples])
    if times[-1] < target[-1]:
        raise ValueError('Capture too short for exact 52Hz export')
    received = [s.get('received_ms') for s in samples]
    if (any(type(t) is not int for t in received)
            or any(b<a for a,b in zip(received,received[1:]))
            or not WINDOW_SECONDS*1000-300 <= received[-1]-received[0] <= WINDOW_SECONDS*1000+500):
        raise ValueError('Invalid host receive duration')
    axes = np.array([s['axes'] for s in samples])
    return np.stack([np.interp(target,times,axes[:,k]) for k in range(6)],axis=1)


def load_records(root, splits=SPLITS, *, labels=None, merge=None):
    labels = LABELS if labels is None else tuple(labels)
    merge = MERGE if merge is None else merge
    records, rejected = [], []
    sessions, hashes = {}, set()
    for path in sorted(Path(root).rglob('*.json')):
        try:
            record = json.loads(path.read_text())
            if not isinstance(record,dict):
                raise ValueError('Record must be a JSON object')
            if record.get('label')=='unlabelled' and record.get('source') in ('device_ble','device_usb') and 'split' not in record:
                continue  # Explicit doctor evidence, never training data.
            if record.get('split') not in SPLITS:
                raise ValueError('Missing or invalid dataset split')
            if record.get('split') not in splits:
                continue
            if (record.get('schema') != 1 or record.get('source') not in ('device_ble','device_usb')
                    or record.get('confirmed') is not True or record.get('hand') != 'left'
                    or record.get('profile') != PROFILE or record.get('label') not in KNOWN_LABELS):
                raise ValueError('Not a confirmed left-wrist training record with the supported profile')
            folded = merge.get(record['label'])
            if folded:
                record = dict(record, label=folded, merged_from=record['label'])
            if record['label'] not in labels:
                continue  # a valid take of a class outside this run's set; kept on disk, not used
            session = record.get('session', '')
            if not re.fullmatch(r'[A-Za-z0-9_-]{1,64}', session):
                raise ValueError('Invalid session ID')
            x, quality = window(record['samples'])
            digest = fingerprint(record['samples'])
            if digest in hashes:
                raise ValueError('Duplicate capture content')
            if session in sessions and sessions[session] != record['split']:
                raise ValueError('Session leaks across data splits')
            sessions[session] = record['split']; hashes.add(digest)
            records.append(dict(record, x=x, quality=quality, digest=digest, path=str(path)))
        except (ValueError, KeyError, TypeError, OSError) as exc:
            rejected.append({'path': str(path), 'reason': str(exc)})
    return records, rejected


def audit(root, records=None, rejected=None):
    if records is None:
        records, rejected = load_records(root)
    counts = {split: {label: sum(r['split']==split and r['label']==label for r in records)
                      for label in LABELS} for split in SPLITS}
    return {'counts': counts, 'accepted': len(records), 'rejected': rejected,
            'ready_for_training': not rejected and all(counts['train'][k]>=20 and
                counts['validation'][k]>=5 for k in LABELS)}


def tensorflow():
    os.environ.setdefault('TF_CPP_MIN_LOG_LEVEL', '2')
    os.environ.setdefault('TF_NUM_INTRAOP_THREADS', '1')
    os.environ.setdefault('TF_NUM_INTEROP_THREADS', '1')
    try:
        import tensorflow as tf
    except ImportError as exc:
        raise RuntimeError('Use firmware/.venv-gesture/bin/python; install gesture-requirements.txt') from exc
    return tf


def decide(scores, threshold=.8, margin=.2):
    values = np.asarray(scores, dtype=np.float32)
    if values.shape != (len(LABELS),) or not np.isfinite(values).all() or (values<0).any() or abs(values.sum()-1)>.001:
        raise ValueError('Invalid classifier probabilities')
    if not .5 <= threshold <= 1 or not 0 <= margin <= 1:
        raise ValueError('Invalid confidence/margin threshold')
    order = np.argsort(values)
    best, second = int(order[-1]), int(order[-2])
    label = LABELS[best] if values[best]>=threshold and values[best]-values[second]>=margin else 'unknown'
    return {'label': label, 'confidence': float(values[best]),
            'scores': {k: float(v) for k, v in zip(LABELS, values)}}


def export_header(model, mean, scale, threshold, margin, output):
    """Export the fixed Conv1D(16x9)/MaxPool4/Conv1D(32x7)/GAP/Dense net; no inference runtime."""
    def array(name, values):
        text = ','.join(f'{float(v):.9e}f' for v in np.asarray(values).ravel())
        return f'inline constexpr float {name}[] = {{{text}}};\n'
    convs = [l for l in model.layers if isinstance(l, tf_layers().Conv1D)]
    dense = [l for l in model.layers if isinstance(l, tf_layers().Dense)][-1]
    (k1, b1), (k2, b2), (wd, bd) = convs[0].get_weights(), convs[1].get_weights(), dense.get_weights()
    assert k1.shape == (9, 6, 16) and k2.shape == (7, 16, 32) and wd.shape == (32, len(LABELS)), (k1.shape, k2.shape, wd.shape)
    text = '#pragma once\n#include <cmath>\n#include <cstddef>\nnamespace mako_gesture {\n'
    text += f'inline constexpr int points={WINDOW_POINTS};\ninline constexpr int classes={len(LABELS)};\n'
    text += array('mean', mean) + array('scale', scale)
    text += array('k1', k1) + array('b1', b1) + array('k2', k2) + array('b2', b2) + array('wd', wd) + array('bd', bd)
    text += '''
// Inputs are `points` rows of the 2 s peak-motion window (same crop as the trainer):
// ax,ay,az in g; gx,gy,gz in deg/s. Caller rejects timing gaps/saturation first.
// Conv1D 16x9 (valid) -> MaxPool 4 -> Conv1D 32x7 (valid) -> global average -> Dense.
inline bool predict(const float* input, float* scores) {
  constexpr int L1 = points - 8, P1 = L1 / 4, L2 = P1 - 6;
  static float x[points * 6], h1[L1 * 16], p1[P1 * 16], h2[L2 * 32], g[32];  // ponytail: static, not stack; loop task has 4 KB
  for (int i = 0; i < points * 6; ++i) {
    if (!std::isfinite(input[i]) || std::fabs(input[i]) >= (i % 6 < 3 ? 7.80f : 1100.f)) return false;
    x[i] = (input[i] - mean[i % 6]) / scale[i % 6];
  }
  for (int t = 0; t < L1; ++t) for (int o = 0; o < 16; ++o) {
    float v = b1[o];
    for (int k = 0; k < 9; ++k) for (int c = 0; c < 6; ++c) v += x[(t + k) * 6 + c] * k1[(k * 6 + c) * 16 + o];
    h1[t * 16 + o] = v > 0 ? v : 0;
  }
  for (int t = 0; t < P1; ++t) for (int o = 0; o < 16; ++o) {
    float m = h1[(t * 4) * 16 + o];
    for (int k = 1; k < 4; ++k) m = std::fmax(m, h1[(t * 4 + k) * 16 + o]);
    p1[t * 16 + o] = m;
  }
  for (int t = 0; t < L2; ++t) for (int o = 0; o < 32; ++o) {
    float v = b2[o];
    for (int k = 0; k < 7; ++k) for (int c = 0; c < 16; ++c) v += p1[(t + k) * 16 + c] * k2[(k * 16 + c) * 32 + o];
    h2[t * 32 + o] = v > 0 ? v : 0;
  }
  for (int o = 0; o < 32; ++o) { float sum = 0; for (int t = 0; t < L2; ++t) sum += h2[t * 32 + o]; g[o] = sum / L2; }
  for (int j = 0; j < classes; ++j) { scores[j] = bd[j]; for (int i = 0; i < 32; ++i) scores[j] += g[i] * wd[i * classes + j]; }
  float top = scores[0], sum = 0;
  for (int i = 1; i < classes; ++i) if (scores[i] > top) top = scores[i];
  for (int i = 0; i < classes; ++i) { scores[i] = std::exp(scores[i] - top); sum += scores[i]; }
  for (int i = 0; i < classes; ++i) scores[i] /= sum;
  return true;
}
// 0 circle, 1 up_wave, 2 straight punch, 3 other, 4 uppercut, 5 hook, -1 unknown. Does not execute actions.
inline int classify(const float* scores) {
  int best=0,second=1;
  if(scores[second]>scores[best]){best=1;second=0;}
  for(int i=2;i<classes;++i)if(scores[i]>scores[best]){second=best;best=i;}else if(scores[i]>scores[second])second=i;
'''
    text += f'  return scores[best]>={threshold:.9e}f && scores[best]-scores[second]>={margin:.9e}f ? best : -1;\n}}\n}}\n'
    Path(output).write_text(text)


def tf_layers():
    return tensorflow().keras.layers


def verify_cpp(model, header_dir, rows, threshold, margin):
    compiler=shutil.which('clang++') or shutil.which('g++')
    if not compiler:raise RuntimeError('A C++ compiler is required to verify the exported model')
    with tempfile.TemporaryDirectory(prefix='mako-model-parity-') as temp:
        source=Path(temp)/'parity.cpp';exe=Path(temp)/'parity'
        source.write_text('#include "gesture_model_weights.h"\n#include <iostream>\n#include <iomanip>\n'
            'int main(){float x[mako_gesture::points*6],p[mako_gesture::classes];for(float &v:x)if(!(std::cin>>v))return 3;'
            'if(!mako_gesture::predict(x,p))return 2;for(float v:p)std::cout<<std::setprecision(9)<<v<<" ";'
            'std::cout<<mako_gesture::classify(p);}\n')
        subprocess.run([compiler,'-std=c++17','-O2','-I',str(Path(header_dir).resolve()),str(source),'-o',str(exe)],check=True,capture_output=True)
        worst=0.
        for row in rows:
            result=subprocess.run([str(exe)],input=' '.join(str(float(v)) for v in row.ravel()),text=True,capture_output=True,check=True)
            values=np.fromstring(result.stdout,sep=' ')
            expected=model(row[None],training=False).numpy()[0]
            if len(values)!=len(LABELS)+1:raise RuntimeError('Invalid C++ parity result')
            worst=max(worst,float(np.max(np.abs(values[:len(LABELS)]-expected))))
            label=decide(expected,threshold,margin)['label'];index=LABELS.index(label) if label in LABELS else -1
            if int(values[len(LABELS)])!=index:raise RuntimeError('C++ classification decision differs')
        if worst>1e-4:raise RuntimeError(f'C++ conversion parity failed: {worst}')
        return worst


def train(root, output, epochs=100, threshold=.8, margin=.2):
    decide([1/len(LABELS)]*len(LABELS), threshold, margin)
    if not 1 <= epochs <= 500:
        raise ValueError('epochs must be 1..500')
    records, rejected = load_records(root, ('train', 'validation'))
    if rejected:
        raise ValueError(f'Rejected data: {rejected}')
    groups = {s: [r for r in records if r['split']==s] for s in ('train','validation')}
    for split, minimum in (('train',20), ('validation',5)):
        if any(sum(r['label']==label for r in groups[split])<minimum for label in LABELS):
            raise ValueError(f'{split}: need at least {minimum} confirmed records per class')
    output = Path(output)
    if output.exists():
        raise ValueError('Model output already exists; choose a new directory')
    tf = tensorflow(); tf.keras.utils.set_random_seed(47)
    x, xv = (np.stack([crop(r['x']) for r in groups[s]]) for s in ('train','validation'))
    y, yv = (np.asarray([LABELS.index(r['label']) for r in groups[s]]) for s in ('train','validation'))
    mean = x.mean(axis=(0,1)); scale = np.maximum(x.std(axis=(0,1)), 1e-3)
    model = tf.keras.Sequential([
        tf.keras.Input(shape=(WINDOW_POINTS,6)),
        tf.keras.layers.Normalization(axis=-1, mean=mean, variance=scale**2),
        # A flattened Dense memorised 20 takes/class (100% train, 38% CV); this generalised at 78%.
        tf.keras.layers.Conv1D(16,9,activation='relu'), tf.keras.layers.MaxPool1D(4),
        tf.keras.layers.Conv1D(32,7,activation='relu'), tf.keras.layers.GlobalAveragePooling1D(),
        tf.keras.layers.Dense(len(LABELS),activation='softmax')])
    model.compile(optimizer='adam', loss='sparse_categorical_crossentropy', metrics=['accuracy'])
    # One machine-readable line per epoch so a UI can draw the curve live (PrintThings device panel).
    progress = tf.keras.callbacks.LambdaCallback(on_epoch_end=lambda e, logs: print(
        'EPOCH ' + json.dumps({'epoch': e+1, 'epochs': epochs, **{k: float(v) for k, v in (logs or {}).items()}}), flush=True))
    history = model.fit(x,y,validation_data=(xv,yv),epochs=epochs,batch_size=16,verbose=0,
        callbacks=[tf.keras.callbacks.EarlyStopping(monitor='val_loss',patience=12,restore_best_weights=True), progress])
    if not all(np.isfinite(w).all() for w in model.get_weights()):
        raise RuntimeError('Non-finite training result; no model exported')
    converter = tf.lite.TFLiteConverter.from_keras_model(model)
    binary = converter.convert()
    interpreter = tf.lite.Interpreter(model_content=binary); interpreter.allocate_tensors()
    inp, out = interpreter.get_input_details()[0], interpreter.get_output_details()[0]
    worst = 0.
    for row in xv:
        interpreter.set_tensor(inp['index'], row[None]); interpreter.invoke()
        worst = max(worst, float(np.max(np.abs(interpreter.get_tensor(out['index'])[0]-model(row[None],training=False).numpy()[0]))))
    if worst>1e-4:
        raise RuntimeError(f'TFLite conversion parity failed: {worst}')
    # Output is created only after training and conversion succeed. Metadata is the final commit marker.
    output.mkdir(parents=True)
    model.save(output/'model.keras')
    (output/'model.tflite').write_bytes(binary)
    export_header(model,mean,scale,threshold,margin,output/'gesture_model_weights.h')
    cpp_error=verify_cpp(model,output,xv,threshold,margin)
    write_json(output/'history.json',history.history)
    metadata = {'schema':1,'status':'candidate_unvalidated','labels':LABELS,'merge':MERGE,'profile':PROFILE,
                'window_points':WINDOW_POINTS,'architecture':'conv1d16x9-pool4-conv1d32x7-gap-dense',
        'hand':'left','mean':mean.tolist(),'scale':scale.tolist(),'threshold':threshold,'margin':margin,
        'training_sessions':sorted({r['session'] for r in records}),
        'training_hashes':[r['digest'] for r in records], 'tensorflow':tf.__version__,
        'keras_sha256':hashlib.sha256((output/'model.keras').read_bytes()).hexdigest(),
        'tflite_bytes':len(binary),'tflite_max_error':worst,'cpp_max_error':cpp_error,
        'created_at':datetime.now(timezone.utc).isoformat(), 'physical_acceptance':False}
    write_json(output/'metadata.json',metadata)
    return metadata


def load_model(root):
    root = Path(root)
    meta = json.loads((root/'metadata.json').read_text())
    # the model decides the class set AND the fold for evaluate/predict/live
    set_labels(meta['labels'], meta.get('merge'))
    if meta['schema']!=1 or meta['labels']!=list(LABELS) or meta['profile']!=PROFILE or meta['hand']!='left':
        raise ValueError('Unsupported model contract')
    if hashlib.sha256((root/'model.keras').read_bytes()).hexdigest()!=meta['keras_sha256']:
        raise ValueError('Model/metadata mismatch')
    decide([1/len(LABELS)]*len(LABELS),meta['threshold'],meta['margin'])
    return tensorflow().keras.models.load_model(root/'model.keras'),meta


def evaluate(root, model_dir):
    model, meta = load_model(model_dir)
    records, rejected = load_records(root, ('test',))
    if rejected:
        raise ValueError(f'Rejected test data: {rejected}')
    if any(sum(r['label']==label for r in records)<10 for label in LABELS):
        raise ValueError('Need at least 10 independent test records per class')
    if any(r['session'] in meta['training_sessions'] or r['digest'] in meta['training_hashes'] for r in records):
        raise ValueError('Test data leaked into training/validation')
    matrix = np.zeros((len(LABELS),len(LABELS)+1),dtype=int)
    for r in records:
        scores = model(crop(r['x'])[None],training=False).numpy()[0]
        label = decide(scores,meta['threshold'],meta['margin'])['label']
        matrix[LABELS.index(r['label']), LABELS.index(label) if label in LABELS else len(LABELS)] += 1
    metrics = {}
    for i,label in enumerate(LABELS):
        tp = int(matrix[i,i]); precision = tp/max(1,int(matrix[:,i].sum())); recall = tp/max(1,int(matrix[i].sum()))
        metrics[label]={'precision':precision,'recall':recall,'f1':2*precision*recall/max(1e-12,precision+recall),'support':int(matrix[i].sum())}
    actions = [i for i,k in enumerate(LABELS) if k!='other']
    background = LABELS.index('other')
    false_positive = float(matrix[background,actions].sum()/max(1,matrix[background].sum()))
    passed = all(metrics[k]['precision']>=.9 and metrics[k]['recall']>=.9 for k in LABELS if k!='other') and false_positive<=.05
    return {'rows':LABELS,'columns':(*LABELS,'unknown'),'confusion_matrix':matrix.tolist(),
        'metrics':metrics,'other_false_positive_rate':false_positive,
        'unknown_rate':float(matrix[:,-1].sum()/matrix.sum()),'window_acceptance_passed':passed,
        'continuous_stream_tested':False,'physical_acceptance':False,
        'test_hashes':[r['digest'] for r in records]}


async def raw_capture(client, seconds, countdown=False, on_phase=None, on_samples=None):
    from watch_ai import IMU, decode_sample
    samples, errors = [], []
    recording = False
    def callback(_, data):
        try:
            sample=decode_sample(data);sample['received_ms']=time.monotonic_ns()//1_000_000
            samples.append(sample)
            if recording and on_samples and len(samples)%5==0:
                on_samples(list(samples))
        except ValueError as exc:
            errors.append(str(exc))
    await client.start_notify(IMU,callback)
    try:
        if countdown:
            for n in (3,2,1):
                if on_phase:
                    on_phase('countdown', n)
                print(n,flush=True);await asyncio.sleep(1)
            samples.clear();errors.clear()
            print('\a开始',flush=True)
        else:
            # Like record's countdown, let queued subscription data drain before timing doctor.
            await asyncio.sleep(1)
            samples.clear();errors.clear()
        recording = True
        if on_phase:
            on_phase('recording', seconds)
        await asyncio.sleep(seconds)
    finally:
        await client.stop_notify(IMU)
    if errors:
        raise ValueError(f'Invalid BLE packets: {errors}')
    # Allow modest sensor clock drift; trim only samples beyond the quality ceiling.
    while len(samples) > 2 and (samples[-1]['ms']-samples[0]['ms']) & 0xffffffff > WINDOW_SECONDS*1000+100:
        samples.pop()
    return samples


async def capture_command(args):
    from bleak import BleakClient
    from ble_client import find_device
    output=Path(args.output)
    if output.exists():
        raise ValueError('Output exists; never overwrite a take')
    if args.command=='record' and not re.fullmatch(r'[A-Za-z0-9_-]{1,64}', args.session):
        raise ValueError('Use a session ID with letters/digits/_/-')
    # doctor --countdown gives a probe the same cue as record while still saving the
    # samples when quality fails; guided_session's health checks pass no flag and stay silent.
    countdown = args.command=='record' or getattr(args,'countdown',False)
    usb=getattr(args,'transport','ble')=='usb'
    from usb_imu import UsbImu
    connection=UsbImu() if usb else BleakClient(await find_device(args.address),timeout=30)
    async with connection as client:
        if args.command=='record':
            guidance='保持静止或做日常动作，持续4秒。' if args.label=='other' else '一条只做一次；听到开始后在4秒内完成。'
            print(f'左手：{NAMES[LABELS.index(args.label)]}。{guidance}',flush=True)
        elif countdown:
            print('诊断探针：听到提示音后全速做一次完整动作。结果只作未标注诊断，不进训练集。',flush=True)
        if countdown:
            await asyncio.to_thread(input,'准备好按 Enter；Ctrl+C 取消：')
        samples=await raw_capture(client,CAPTURE_SECONDS,countdown=countdown)
        record={'schema':1,'source':'device_usb' if usb else 'device_ble','label':'unlabelled','hand':'left',
                'profile':PROFILE,'address':str(client.address),'samples':samples,
                'captured_at':datetime.now(timezone.utc).isoformat()}
    try:
        _,quality=window(samples);record['quality']=quality
        edge_window(samples)
    except (ValueError,KeyError,TypeError) as exc:
        if args.command=='record':
            raise ValueError(f'Capture discarded; {exc}') from exc
        record['quality_error']=str(exc)
    if args.command=='record':
        print('\a录制结束。',flush=True)
        prompt='确认属于静止或日常动作？' if args.label=='other' else '动作正确且只做了一次？'
        answer=await asyncio.to_thread(input,prompt+'输入 y 保存，其他输入丢弃：')
        if answer.lower().strip()!='y':
            return {'saved':False,'reason':'User discarded take'}
        record.update(label=args.label,session=args.session,split=args.split,confirmed=True)
    output.parent.mkdir(parents=True,exist_ok=True);write_json(output,record)
    return {'saved':str(output),'samples':len(samples),'quality':record.get('quality'),
            'quality_error':record.get('quality_error'),'label':record['label']}


async def guided_session(args):
    """Guide one independent recording session; never upload or flash."""
    from edge_impulse import export_dataset, verify_bundle
    count = args.count if args.count is not None else {'train':40,'validation':10,'test':20}[args.split]
    if not 1 <= count <= 200:
        raise ValueError('每类目标数量必须为1到200')
    data = Path(args.data)
    records, rejected = load_records(data)
    if rejected:
        raise ValueError('已有数据未通过检查，请先处理：'+json.dumps(rejected,ensure_ascii=False))
    for record in records:
        edge_window(record['samples'])
    counts = {label:sum(r['split']==args.split and r['label']==label for r in records) for label in LABELS}
    session = args.split+'_'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f')
    output = Path(args.output) if args.output else Path(__file__).resolve().parent/'edge-impulse-data'/session
    if output.exists():
        raise ValueError('导出目录已存在，请换新目录')
    if any(n<count for n in counts.values()):
        print('左手佩戴并固定表带；保持蓝牙开启，只运行一个采集程序。',flush=True)
        if args.split != 'train':
            print('验证/测试必须另开场次，重新佩戴，并与训练场次间隔一段时间。',flush=True)
        answer = await asyncio.to_thread(input,'准备好后输入 y 开始检查；其他输入退出：')
        if answer.strip().lower() != 'y':
            return {'cancelled':True,'uploaded':False}
        for n in range(1,4):
            print(f'采样检查 {n}/3',flush=True)
            result = await capture_command(argparse.Namespace(command='doctor',address=args.address,transport=getattr(args,'transport','ble'),
                output=data/'diagnostics'/f'{session}-{n}.json'))
            if result.get('quality_error'):
                raise ValueError('采样检查失败，已停止录制：'+result['quality_error'])
        # Rotate the labels. Recording one class to target before starting the next makes
        # class perfectly correlated with time-in-session (strap creep, cable pull, sensor
        # drift), and the test split would reproduce the same confound, so evaluate()
        # could not detect it. Cannot be repaired after collection.
        discarded = 0
        while any(counts[l] < count for l in LABELS):
            label = min((l for l in LABELS if counts[l] < count), key=lambda l: counts[l])
            name = NAMES[LABELS.index(label)]
            print(f'{name}：已保存 {counts[label]}/{count}；其他动作请轮换静止、走路、拿杯等。' if label=='other'
                  else f'{name}：已保存 {counts[label]}/{count}',flush=True)
            try:
                result = await capture_command(argparse.Namespace(command='record',address=args.address,transport=getattr(args,'transport','ble'),
                    label=label,session=session,split=args.split,
                    output=data/args.split/f'{session}-{label}-{counts[label]+1:03}.json'))
            except (ValueError,BleakError,OSError) as exc:
                # A rejected window or a dropped link writes no file; re-record that take
                # instead of ending a session that already holds good data.
                print(f'本条作废，重录：{exc}',flush=True)
                result = {}
            if result.get('saved'):
                counts[label] += 1; discarded = 0
            else:
                discarded += 1
                if discarded >= 3:
                    raise ValueError('连续三条未保存，已暂停；已保存的数据保留，下次自动接着录制')
            if any(counts[l] < count for l in LABELS):
                print(f'放松休息 {REST_SECONDS} 秒，再准备下一条。',flush=True)
                await asyncio.sleep(REST_SECONDS)
    result = export_dataset(data,output)
    verify_bundle(output)
    print('本场次已导出并校验。数据尚未上传，模型尚未训练。',flush=True)
    if args.split == 'train':
        print('下一步：另开场次运行 session --split validation。',flush=True)
    elif args.split == 'validation':
        print('下一步：核对数量后将训练/验证数据导入项目1111996（动作捕捉），配置并训练。',flush=True)
    else:
        print('下一步：仅在模型参数冻结后导入测试数据，做独立评估。',flush=True)
    return {**result,'split':args.split,'session':session,'model_trained':False}


class EventGate:
    """Two agreeing windows; rearm after two background windows, not a timer alone."""
    def __init__(self):
        self.previous=None;self.streak=0;self.armed=True;self.quiet=0

    def update(self,label):
        if label in ('other','unknown'):
            self.quiet+=1;self.streak=0;self.previous=None
            if self.quiet>=2:self.armed=True
            return None
        self.quiet=0
        self.streak=self.streak+1 if label==self.previous else 1;self.previous=label
        if self.armed and self.streak>=2:
            self.armed=False;return label
        return None


async def live(args):
    from bleak import BleakClient
    from ble_client import find_device
    from watch_ai import IMU, decode_sample
    from collections import deque
    model,meta=load_model(args.model);samples=deque(maxlen=POINTS);gate=EventGate();errors=[];evaluated=0
    def callback(_,data):
        try:samples.append(decode_sample(data))
        except ValueError as exc:errors.append(str(exc));samples.clear()
    async with BleakClient(await find_device(args.address),timeout=30) as client:
        await client.start_notify(IMU,callback)
        try:
            deadline=time.monotonic()+args.seconds;last_seq=None
            while time.monotonic()<deadline:
                await asyncio.sleep(.5)
                if errors:raise ValueError(errors[0])
                if len(samples)<POINTS or samples[-1]['seq']==last_seq:continue
                last_seq=samples[-1]['seq']
                try:x,_=window(list(samples))
                except ValueError as exc:
                    samples.clear();gate=EventGate();print(json.dumps({'label':'unknown','quality_error':str(exc)}),flush=True);continue
                scores=await asyncio.to_thread(lambda:model(crop(x)[None],training=False).numpy()[0])
                result=decide(scores,meta['threshold'],meta['margin']);result['event']=gate.update(result['label'])
                evaluated+=1
                result['device_ms']=samples[-1]['ms'];print(json.dumps(result,ensure_ascii=False),flush=True)
        finally:await client.stop_notify(IMU)
    if not evaluated:raise ValueError('No valid live IMU windows; recognition not verified')
    return {'completed_seconds':args.seconds,'evaluated_windows':evaluated,'external_actions':False}


def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
    for name in ('doctor','record'):
        s=sub.add_parser(name);s.add_argument('--address');s.add_argument('--output',required=True)
        s.add_argument('--transport',choices=('ble','usb'),default='ble')
        if name=='doctor':
            s.add_argument('--countdown',action='store_true',help='按 Enter 后倒计时再采样；量程探针用')
        if name=='record':
            s.add_argument('--label',choices=LABELS,required=True);s.add_argument('--session',required=True)
            s.add_argument('--split',choices=SPLITS,required=True)
    s=sub.add_parser('session',help='自动检查、引导录制、接续进度并导出一个集合')
    s.add_argument('--split',choices=SPLITS,required=True)
    s.add_argument('--count',type=int,help='每类累计目标；默认训练40、验证10、测试20')
    s.add_argument('--data',default=str(Path(__file__).resolve().parent/'gesture-data-4s'))
    s.add_argument('--output');s.add_argument('--address')
    s.add_argument('--transport',choices=('ble','usb'),default='ble')
    s=sub.add_parser('audit');s.add_argument('--data',required=True)
    s=sub.add_parser('train');s.add_argument('--data',required=True);s.add_argument('--output',required=True)
    s.add_argument('--epochs',type=int,default=100);s.add_argument('--threshold',type=float,default=.8);s.add_argument('--margin',type=float,default=.2)
    s.add_argument('--labels',default=','.join(ALL_LABELS),help='comma-separated class set, e.g. circle,up_wave,punch,other')
    s.add_argument('--merge',default='',help='fold left-out classes into a kept one, e.g. hook=punch,uppercut=punch')
    s=sub.add_parser('evaluate');s.add_argument('--data',required=True);s.add_argument('--model',required=True);s.add_argument('--output',required=True)
    s=sub.add_parser('predict');s.add_argument('--model',required=True);s.add_argument('--record',required=True)
    s=sub.add_parser('live');s.add_argument('--model',required=True);s.add_argument('--address');s.add_argument('--seconds',type=int,default=60)
    args=p.parse_args()
    try:
        if args.command in ('doctor','record'):result=asyncio.run(capture_command(args))
        elif args.command=='session':result=asyncio.run(guided_session(args))
        elif args.command=='audit':result=audit(args.data)
        elif args.command=='train':
            set_labels(args.labels.split(','),dict(p.split('=',1) for p in args.merge.split(',') if p))
            result=train(args.data,args.output,args.epochs,args.threshold,args.margin)
        elif args.command=='evaluate':
            if Path(args.output).exists():raise ValueError('Evaluation output exists')
            result=evaluate(args.data,args.model);write_json(args.output,result)
        elif args.command=='predict':
            model,meta=load_model(args.model);record=json.loads(Path(args.record).read_text())
            if record.get('profile')!=PROFILE or record.get('hand')!='left':raise ValueError('Record/model profile mismatch')
            x,_=window(record['samples']);result=decide(model(crop(x)[None],training=False).numpy()[0],meta['threshold'],meta['margin'])
        else:
            if not 5<=args.seconds<=600:raise ValueError('live seconds must be 5..600')
            result=asyncio.run(live(args))
        print(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False))
        if args.command=='doctor' and result.get('quality_error'):return 2
        if args.command=='audit' and result['rejected']:return 2
        return 0
    except (ValueError,KeyError,TypeError,OSError,RuntimeError,BleakError,subprocess.CalledProcessError) as exc:
        p.exit(1,str(exc)+'\n')


if __name__=='__main__':
    sys.exit(main())

"""One pipeline, many tasks: gate -> train -> evaluate, driven by a task description.

Everything here already existed as a one-off per sensor. gesture_web.py called
separability.report on IMU records; usb_snap.py called the same function with its own
extractor; each knew its own labels, its own fold, its own training command. That is
fine for one task and wrong for three, and there are already two.

A Task says what differs. The stages below say what does not. Nothing in this file
imports TensorFlow, gesture_model or a sensor driver at module scope -- a task supplies
those lazily, so a future project with a different board still gets the gate and the
registry without dragging this one's dependencies along.

    python3 pipeline.py list
    python3 pipeline.py gate --task gesture
    python3 pipeline.py auto --task gesture      # gate, then train only if the gate allows
"""
import argparse
import hashlib
import json
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

import separability

# gesture_model's LABELS/MERGE are module globals; serialise every task that sets them.
_GM_LOCK = threading.Lock()

HERE = Path(__file__).resolve().parent
REGISTRY = HERE / 'gesture-models' / 'index.json'


@dataclass(frozen=True)
class Task:
    """What one sensing problem needs that another one does not."""
    name: str
    data: Path
    # load(splits) -> ([{'label', 'x', ...}], [rejected]). 'x' is whatever extract eats.
    load: Callable
    extract: Callable | None = None     # None = separability's six-axis IMU features
    catalog: dict | None = None
    labels: tuple = ()                  # the class set that gets TRAINED
    merge: dict = field(default_factory=dict)   # folded at load time; see gesture_model.MERGE
    # separability.capture_drift reads quality['max_sample_gap_ms'] and reasons about a
    # 52 Hz period, so it is the IMU capture's check, not every task's. Running it on a
    # task that stores no such quality gives an empty-set "ok" -- a false green, which is
    # worse than no check. Tasks opt in.
    drift: Callable | None = None
    train: Callable | None = None       # (output: Path) -> metadata dict
    evaluate: Callable | None = None    # (model_dir: Path) -> report dict
    note: str = ''

    def fold(self, records):
        if not self.merge:
            return records
        return [dict(r, label=self.merge.get(r['label'], r['label'])) for r in records]


# --------------------------------------------------------------------------- stages ---
def gate(task, splits=None):
    """Can these classes be told apart at all, and is the capture drifting?

    The only stage that runs on every task for free: it needs recorded takes and a
    feature extractor, never a trained model.
    """
    if task.name == 'punch':
        import calibrate
        records, rejected = task.load(splits)
        ready = calibrate.readiness(records)['ready']
        return {'task': task.name, 'takes': len(records), 'rejected': len(rejected),
                'separability': {'status': 'ok' if ready else 'pending', 'pairs': [],
                                 'message': '数量达到初版标定门槛；不代表控制可用' if ready else '六项训练数据各需 10 条'},
                'capture': task.drift(records)}
    records, rejected = task.load(splits)
    folded = task.fold(records)
    return {'task': task.name, 'takes': len(records), 'rejected': len(rejected),
            'separability': separability.report(folded, extract=task.extract, catalog=task.catalog),
            # Drift is about the capture, not the labelling, so it sees the unfolded takes.
            'capture': task.drift(records) if task.drift else
                       {'status': 'n/a', 'degraded': {}, 'message': f'{task.name} 还没有采集漂移检查。'}}


def train(task, output=None):
    if task.train is None:
        raise ValueError(f'{task.name}: 还没有训练器（数据还没采够就会是这样）')
    output = Path(output or HERE / 'gesture-models' / f"{time.strftime('%Y%m%d-%H%M%S')}-{task.name}")
    records, _ = task.load(None)
    meta = task.train(output)
    record(task, output, meta, fingerprint=dataset_fingerprint(records))
    return {'task': task.name, 'output': str(output), 'metadata': meta}


def evaluate(task, model_dir):
    if task.evaluate is None:
        raise ValueError(f'{task.name}: 还没有验收器')
    report = task.evaluate(Path(model_dir))
    record(task, Path(model_dir), None, evaluation=report)
    return {'task': task.name, 'model': str(model_dir), 'evaluation': report}


def auto(task, output=None):
    """Gate first, and stop there if it refuses -- that is the whole point of having one.

    `warn` trains: the real gesture dataset is warn today (circle/up_wave, d' 1.07), and
    refusing it would refuse everything. `block` does not, because separability.py only
    says block when no axis separates the pair and more takes cannot change it.
    """
    verdict = gate(task)
    status = verdict['separability']['status']
    if status != 'ok' and status != 'warn':
        return {**verdict, 'trained': None,
                'stopped': f"门禁 {status}：{verdict['separability']['message']}"}
    result = train(task, output)
    trained = Path(result['output'])
    evaluation = None
    if task.evaluate is not None and task.name != 'punch':
        try:
            evaluation = task.evaluate(trained)
        except (ValueError, KeyError, OSError) as exc:
            evaluation = {'skipped': str(exc)}   # usually "no test split yet", not a failure
        record(task, trained, None, evaluation=evaluation)
    return {**verdict, 'trained': result, 'evaluation': evaluation, 'stopped': None}


# -------------------------------------------------------------------------- trigger ---
# Fire when the recording STOPS, not when a take is saved. A session is ~30 takes about
# 15 s apart; training after each one burns half an hour of CPU to produce 29 models
# nobody wants, and the 30th is the only one trained on the whole session. A quiet
# window turns "after every take" into "once per session" without anyone deciding when
# a session ended.
QUIET_SECONDS = 120


def dataset_fingerprint(records):
    """Identity of the data a run was trained on. Takes carry their own content hash;
    fall back to the label list so a task without digests still dedupes."""
    marks = sorted(r.get('digest') or f"{r.get('label')}:{i}" for i, r in enumerate(records))
    return hashlib.sha256('\n'.join(marks).encode()).hexdigest()[:16]


def last_run(task):
    for run in reversed(runs()):
        if run['task'] == task.name and run.get('fingerprint'):
            return run
    return None


def should_run(task, busy=False, idle_seconds=None, records=None, gate_status=None,
               quiet_seconds=QUIET_SECONDS):
    """Pure decision, so the rule can be tested without a server or a dataset.

    `busy` covers both "capturing" and "already training": retraining while the set is
    still growing races the thing that is growing it.
    """
    if busy:
        return {'run': False, 'reason': '正在采集或训练'}
    if idle_seconds is not None and idle_seconds < quiet_seconds:
        return {'run': False, 'reason': f'刚存过数据，等安静 {quiet_seconds - int(idle_seconds)} s'}
    if records is None:
        records, _ = task.load(None)
    if not records:
        return {'run': False, 'reason': '还没有数据'}
    if gate_status is None:
        gate_status = gate(task)['separability']['status']
    if gate_status not in ('ok', 'warn'):
        return {'run': False, 'reason': f'门禁 {gate_status}'}
    mark = dataset_fingerprint(records)
    previous = last_run(task)
    if previous and previous['fingerprint'] == mark:
        return {'run': False, 'reason': f"数据没变，上次是 {previous['model']}", 'fingerprint': mark}
    return {'run': True, 'reason': '数据变了且门禁放行' if previous else '第一次训练',
            'fingerprint': mark}


def watch(task, interval=30, quiet_seconds=QUIET_SECONDS, idle=lambda: None, busy=lambda: False,
          stop=None, on_event=lambda _: None, once=False):
    """Poll the decision; run `auto` when it turns true. `idle`/`busy` come from whoever
    owns the capture -- the collector knows, this module must not guess."""
    while stop is None or not stop.is_set():
        try:
            verdict = should_run(task, busy=busy(), idle_seconds=idle(), quiet_seconds=quiet_seconds)
            on_event(verdict)
            if verdict['run']:
                on_event({'run': True, 'reason': '开始', 'result': auto(task)})
        except (ValueError, KeyError, OSError, subprocess.SubprocessError) as exc:
            on_event({'run': False, 'reason': f'自动训练出错：{exc}'})
        if once or stop is None:
            return
        stop.wait(interval)


# ------------------------------------------------------------------------- registry ---
def runs():
    return json.loads(REGISTRY.read_text()) if REGISTRY.exists() else []


def record(task, output, metadata, evaluation=None, on_device=None, fingerprint=None):
    """Append-only run log. Which model is on the board is a fact nobody was keeping:
    seven directories under gesture-models/ and no way to tell them apart."""
    REGISTRY.parent.mkdir(parents=True, exist_ok=True)
    rows = runs()
    name = Path(output).name
    entry = next((r for r in rows if r['model'] == name), None)
    if entry is None:
        entry = {'model': name, 'task': task.name, 'created_at': time.strftime('%Y-%m-%dT%H:%M:%S')}
        rows.append(entry)
    if fingerprint:
        entry['fingerprint'] = fingerprint
    if metadata:
        entry.update(labels=metadata.get('labels'), merge=metadata.get('merge'),
                     tflite_bytes=metadata.get('tflite_bytes'),
                     cpp_max_error=metadata.get('cpp_max_error'), status=metadata.get('status'))
    if evaluation is not None:
        entry['evaluation'] = evaluation
    if on_device is not None:
        for run in rows:
            if run['task'] == task.name:
                run['on_device'] = run['model'] == name
    REGISTRY.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + '\n')
    return entry


# ---------------------------------------------------------------------------- tasks ---
def _gesture_task():
    """Left-wrist six-axis gestures. hook/uppercut fold into punch: separability.py on
    gesture-data-4s gives d' 1.51 and 23% overlap, which more takes cannot shrink."""
    labels, merge = ('circle', 'up_wave', 'punch', 'other'), {'hook': 'punch', 'uppercut': 'punch'}

    def load(splits=None):
        # gesture_model keeps LABELS/MERGE as module globals, so setting them is a side
        # effect on everyone sharing the process -- gesture_web's refresh_counts reads
        # them from the HTTP threads and expects the six-class collection view. Hold the
        # lock and put them back; the subprocess protects training, this protects reads.
        import gesture_model as gm
        with _GM_LOCK:
            previous, previous_merge = gm.LABELS, dict(gm.MERGE)
            try:
                gm.set_labels(labels, merge)
                return gm.load_records(HERE / 'gesture-data-4s', splits or gm.SPLITS)
            finally:
                gm.set_labels(previous, previous_merge if previous_merge else None)

    def do_train(output):
        # Subprocess, not import: gesture_model.set_labels mutates module globals and
        # TensorFlow is a heavy, crashy guest in a long-lived process. Same reason
        # gesture_web.Collector.train shells out.
        done = subprocess.run(
            [sys.executable, str(HERE / 'gesture_model.py'), 'train',
             '--data', str(HERE / 'gesture-data-4s'), '--output', str(output),
             '--labels', ','.join(labels),
             '--merge', ','.join(f'{k}={v}' for k, v in merge.items()),
             '--threshold', '0.6', '--margin', '0.1'],
            capture_output=True, text=True, timeout=3600)
        if done.returncode:
            reason = (done.stderr or done.stdout).strip().splitlines()
            raise ValueError(reason[-1][:300] if reason else '训练失败')
        # TensorFlow prints progress on stdout, so stdout is never pure JSON.
        return json.loads((Path(output) / 'metadata.json').read_text())

    def do_evaluate(model_dir):
        # evaluate() calls load_model, which sets the labels from the model's own
        # metadata; restore afterwards for the same reason load() does.
        import gesture_model as gm
        with _GM_LOCK:
            previous, previous_merge = gm.LABELS, dict(gm.MERGE)
            try:
                return gm.evaluate(HERE / 'gesture-data-4s', model_dir)
            finally:
                gm.set_labels(previous, previous_merge if previous_merge else None)

    return Task(name='gesture', data=HERE / 'gesture-data-4s', load=load, labels=labels,
                merge=merge, drift=separability.capture_drift, train=do_train, evaluate=do_evaluate,
                note='六轴手势，52 Hz / 208 点 / 2 s 裁窗；三拳合并')


def _punch_task():
    """Control candidates fit train only; held-out test evaluation is explicitly requested."""
    labels = ('punch', 'other') + tuple(l for l in _control_labels())

    def load(splits=None):
        import calibrate
        records = calibrate.load(HERE / 'punch-data')
        return [r for r in records if splits is None or r['split'] in splits], []

    def do_train(output):
        import calibrate
        records, _ = load()
        return calibrate.save(records, output)

    def do_evaluate(output):
        import calibrate
        records, _ = load()
        return calibrate.test_report(records, output)

    return Task(name='punch', data=HERE / 'punch-data', load=load, labels=labels,
                drift=separability.capture_drift, train=do_train, evaluate=do_evaluate,
                note='单腕拳击候选阈值：train 标定，validation 复核，test 显式验收')


def _control_labels():
    import gesture_model as gm
    return gm.CONTROL_LABELS


def _snap_task():
    """Finger snap vs clap: sound and wrist jolt within +-30 ms. No trainer yet -- batch A
    (usb_snap.py --record) has not been recorded, so the gate is all there is to run."""
    def load(splits=None):
        import usb_snap
        return usb_snap.load(), []

    def extract(x):
        import usb_snap
        return usb_snap.snap_features(x)

    import usb_snap as _snap
    return Task(name='snap', data=HERE / 'snap-data', load=load, extract=extract,
                catalog=_snap.SNAP_FEATURES,
                note='16 kHz 麦 + 833 Hz 加速度的符合检测；批 A 还没录，只有门禁')


def _emg_task():
    """One dry-electrode sEMG channel on the forearm, 1 kHz. Batch A (usb_emg.py --record)
    has not been recorded; `auto` still runs the gate first and stops there if it refuses.

    The trainer is shrinkage LDA over the same eleven named features (emg_model.py): if one
    feature already separates the classes the gate says so and LDA is a threshold with
    extra steps, and if none of the eleven does, a classifier over the same eleven will
    not find what they missed. Evaluation reports two numbers and only the second one
    counts: leave-one-out on the recording, and accuracy on emg-data-rewear/ -- strap
    off, electrodes back on, recorded again.

    capture_drift stays off: it reasons about a 52 Hz IMU period and these takes store
    no max_sample_gap_ms, so running it would return an empty-set "ok" -- a false green.
    """
    def load(splits=None):
        import usb_emg
        return usb_emg.load(HERE / 'emg-data'), []

    def extract(x):
        import usb_emg
        return usb_emg.emg_features(x)

    def do_train(output):
        import emg_model
        return emg_model.train(load()[0], emg_model.LABELS, Path(output))

    def do_evaluate(model_dir):
        import emg_model
        return emg_model.evaluate(Path(model_dir))

    import usb_emg as _emg
    import emg_model as _model
    return Task(name='emg', data=HERE / 'emg-data', load=load, extract=extract,
                catalog=_emg.EMG_FEATURES, labels=_model.LABELS, train=do_train, evaluate=do_evaluate,
                note='1 kHz 单通道表面肌电 / 2 s 一条；脱落、削顶、漂移当场剔除；LDA 训练器，跨佩戴集是验收数')


def tasks():
    return {'gesture': _gesture_task(), 'punch': _punch_task(), 'snap': _snap_task(), 'emg': _emg_task()}


def resolve(name):
    available = tasks()
    if name not in available:
        raise ValueError(f'未知任务 {name!r}；已有 {sorted(available)}')
    return available[name]


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('list')
    for name in ('gate', 'train', 'auto'):
        p = sub.add_parser(name); p.add_argument('--task', required=True)
        if name != 'gate':
            p.add_argument('--output')
    p = sub.add_parser('evaluate'); p.add_argument('--task', required=True); p.add_argument('--model', required=True)
    w = sub.add_parser('watch'); w.add_argument('--task', required=True)
    w.add_argument('--interval', type=int, default=30)
    w.add_argument('--quiet-seconds', type=int, default=QUIET_SECONDS)
    w.add_argument('--once', action='store_true', help='只判一次并在该跑时跑一次，给 cron 用')
    sub.add_parser('runs')
    args = parser.parse_args()
    try:
        if args.command == 'list':
            result = [{'task': t.name, 'data': str(t.data), 'labels': list(t.labels) or None,
                       'merge': t.merge or None, 'trainer': t.train is not None,
                       'evaluator': t.evaluate is not None, 'note': t.note}
                      for t in tasks().values()]
        elif args.command == 'watch':
            import threading as _t
            stop = _t.Event()
            def show(event):
                print(json.dumps(event, ensure_ascii=False, default=str), flush=True)
            watch(resolve(args.task), interval=args.interval, quiet_seconds=args.quiet_seconds,
                  stop=None if args.once else stop, on_event=show, once=args.once)
            return
        elif args.command == 'runs':
            result = runs()
        elif args.command == 'gate':
            result = gate(resolve(args.task))
        elif args.command == 'train':
            result = train(resolve(args.task), args.output)
        elif args.command == 'evaluate':
            result = evaluate(resolve(args.task), args.model)
        else:
            result = auto(resolve(args.task), args.output)
    except (ValueError, KeyError, OSError, subprocess.SubprocessError) as exc:
        parser.exit(1, f'{exc}\n')
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))


if __name__ == '__main__':
    main()

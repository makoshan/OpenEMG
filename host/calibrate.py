"""Punch control calibration. Fit train only; validate frozen thresholds on another session.

--data punch-data --output DIR writes candidates. --evaluate DIR reads those candidates
and evaluates test only. Neither command flashes a board or claims gameplay acceptance.
"""
import argparse
import atexit
import shutil
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

import numpy as np
import gesture_model as gm

HERE = Path(__file__).resolve().parent
REQUIRED = ('duck', 'dodge_left', 'dodge_right', 'punch_high', 'punch_body', 'other')
MIN_TAKES = 10  # pilot minimum per required label, not statistical confidence
MAX_MISS = .40
PUNCHES = ('punch', 'hook', 'uppercut', 'punch_high', 'punch_body')
SIGNALS = {
    'punch': dict(constant='punchG', positive=PUNCHES,
                  negative=('other', 'duck', 'dodge_left', 'dodge_right', 'guard'),
                  column=1, above=True, max_false=.03),
    'high': dict(constant='highG', positive=('punch_high',), negative=('punch_body',),
                 column=2, above=True, max_false=.15),
    'dodge_right': dict(constant='dodgeRightG', positive=('dodge_right',),
                        negative=PUNCHES+('other','duck','dodge_left','guard'),
                        column=3, above=True, max_false=.05),
    'dodge_left': dict(constant='dodgeLeftG', positive=('dodge_left',),
                       negative=PUNCHES+('other','duck','dodge_right','guard'),
                       column=3, above=False, max_false=.05),
    'duck': dict(constant='duckG', positive=('duck',),
                 negative=PUNCHES+('other','dodge_left','dodge_right','guard'),
                 column=4, above=False, max_false=.05),
}


def load(root):
    # Validate ALL splits together, so duplicates and session leakage cannot hide across loads.
    records, rejected = gm.load_records(root, labels=gm.KNOWN_LABELS, merge={})
    if rejected:
        raise ValueError(f'{len(rejected)} 条数据未通过检查：{rejected[0]["reason"]}')
    return records


@lru_cache(maxsize=1)
def executable():
    sources = [HERE/'punch_replay.cpp', HERE/'punch_detect.h']
    digest = hashlib.sha256(b''.join(p.read_bytes() for p in sources)).hexdigest()[:16]
    folder = Path(tempfile.mkdtemp(prefix='mako-punch-replay-'))
    atexit.register(shutil.rmtree, folder, ignore_errors=True)
    binary = folder / digest
    subprocess.run(['c++', '-std=c++17', '-O2', '-I', str(HERE), str(sources[0]),
                    '-o', str(binary)], check=True, capture_output=True, timeout=30)
    return str(binary)


def replay(records, thresholds):
    """Same PunchDetector, default identity axes, original timestamps; fresh state per take.

    This checks sampled replay, not physical sample cadence or continuous-game acceptance.
    """
    packed = []
    for r in records:
        samples = r['samples']
        gm.window(samples)
        start = samples[0]['ms']
        lines = []
        for s in samples:
            a = s['axes']
            lines.append(f'{(s["ms"]-start)&0xffffffff} {a[0]} {a[1]} {a[2]} {a[4]}')
        packed.append((len(samples), '\n'.join(lines)))
    batches = [f'{float(t):.9g} {count}\n{lines}' for t in thresholds for count, lines in packed]
    if not batches:
        return np.empty((len(thresholds), 0, 5))
    out = subprocess.run([executable()], input='\n'.join(batches)+'\n', text=True,
                         capture_output=True, check=True, timeout=30)
    values = np.array([list(map(float, line.split())) for line in out.stdout.splitlines()])
    if values.shape != (len(batches), 5) or not np.isfinite(values).all():
        raise ValueError('检测器回放输出不完整')
    return values.reshape(len(thresholds), len(records), 5)


def rates(fires, positives, negatives, threshold):
    miss = int((~fires[positives]).sum()); false = int(fires[negatives].sum())
    return dict(threshold=float(threshold), miss=miss, false=false,
                miss_rate=miss/int(positives.sum()), false_rate=false/int(negatives.sum()))


def recommend(rows, budget):
    inside = [r for r in rows if r['false_rate'] <= budget]
    best = min(inside or rows, key=lambda r: (r['miss_rate'], r['false_rate']) if inside
               else (r['false_rate'], r['miss_rate']))
    return dict(best, within_budget=bool(inside), usable=bool(inside) and best['miss_rate'] <= MAX_MISS)


def measure(records, name, threshold=None):
    spec = SIGNALS[name]
    selected = [r for r in records if r['label'] in spec['positive']+spec['negative']]
    pos = np.array([r['label'] in spec['positive'] for r in selected], dtype=bool)
    neg = ~pos
    result = dict(signal=name, constant=spec['constant'], positive=int(pos.sum()),
                  negative=int(neg.sum()), max_false=spec['max_false'])
    if min(result['positive'], result['negative']) < MIN_TAKES:
        return dict(result, status='pending', message=f'正类 {pos.sum()} / 负类 {neg.sum()}；每边至少 {MIN_TAKES} 条')
    values = replay(selected, [1e6])[0, :, spec['column']]
    # Persist exactly the threshold evaluated, including decimal rounding.
    grid = [float(threshold)] if threshold is not None else np.unique(np.round(
        np.linspace(float(values.min())-.001, float(values.max())+.001, 40), 6))
    if name == 'punch':
        grid = [t for t in grid if t >= 0]
        if not grid: grid = [0.0]
        events = replay(selected, grid)[:, :, 0]
        fires = events > 0
    else:
        # ponytail: signed extreme can select rebound; use temporal features if held-out data fails.
        fires = np.array([values > t if spec['above'] else values < t for t in grid])
    rows = [rates(f, pos, neg, t) for t, f in zip(grid, fires)]
    best = recommend(rows, spec['max_false'])
    result.update(status='ok' if best['usable'] else 'unusable', recommended=best,
                  message=f'漏 {best["miss_rate"]:.0%}，负窗口误触 {best["false_rate"]:.0%}',
                  method='board_detector_replay' if name == 'punch' else 'experimental_feature',
                  physical_acceptance=False)
    if name == 'punch':
        chosen = list(grid).index(best['threshold'])
        result['extra_events'] = int(np.maximum(events[chosen, pos]-1, 0).sum())
    return result


def fit(records):
    train = [r for r in records if r['split'] == 'train']
    return [measure(train, name) for name in SIGNALS]


def evaluate(records, candidates, split='validation'):
    if split not in ('validation', 'test'):
        raise ValueError('评估只允许 validation 或 test')
    held = [r for r in records if r['split'] == split]
    return [measure(held, r['signal'], r['recommended']['threshold']) for r in candidates
            if r['status'] == 'ok']


def readiness(records):
    counts = {s: {l: sum(r['split']==s and r['label']==l for r in records) for l in REQUIRED}
              for s in gm.SPLITS}
    missing = {l: max(0, MIN_TAKES-counts['train'][l]) for l in REQUIRED}
    return dict(ready=not any(missing.values()), missing=missing, counts=counts)


def report(records):
    candidates = fit(records)
    return dict(schema=2, status='candidate_unvalidated', signals=candidates,
                validation=evaluate(records, candidates), readiness=readiness(records),
                fit_split='train', test_used=False, physical_acceptance=False,
                axis_mapping='raw X/Y/Z, signs +/+/+; physical orientation unverified',
                detector_sha256=hashlib.sha256((HERE/'punch_detect.h').read_bytes()).hexdigest())


def header(results):
    lines = ['// Candidate report only. Not a deployable firmware configuration.',
             '// high/duck/directional dodge are experimental; game integration is pending.',
             '// Replay uses default axes, fresh state per take; physical acceptance is required.']
    for r in results:
        if r['status'] == 'ok':
            lines.append(f'// {r["constant"]} = {r["recommended"]["threshold"]:.6f}; {r["message"]}')
    return '\n'.join(lines)


def save(records, output):
    if not readiness(records)['ready']:
        raise ValueError('正式标定需要六项训练数据各至少 10 条；测试集不会补足训练数量')
    result = report(records)
    if not any(r['status']=='ok' for r in result['signals']):
        raise ValueError('当前方法没有可用候选；保留原始数据，先检查轴向和动作')
    output = Path(output); output.mkdir(parents=True, exist_ok=True)
    gm.write_json(output/'calibration.json', result)
    (output/'punch_thresholds.h').write_text(header(result['signals'])+'\n')
    return result


def test_report(records, output):
    candidate = json.loads((Path(output)/'calibration.json').read_text())
    if candidate.get('schema') != 2 or candidate['detector_sha256'] != hashlib.sha256((HERE/'punch_detect.h').read_bytes()).hexdigest():
        raise ValueError('检测器版本已变或候选格式不匹配，请重新标定')
    return dict(split='test', results=evaluate(records, candidate['signals'], 'test'),
                physical_acceptance=False)


def demo():
    pos=np.array([True,True,False,False]);neg=~pos
    bad=rates(np.zeros(4,dtype=bool),pos,neg,9)
    assert not recommend([bad],.03)['usable']
    good=rates(pos,pos,neg,1)
    assert recommend([good],.03)['usable']
    assert measure([], 'punch')['status']=='pending'
    assert 'punch_high' in SIGNALS['punch']['positive']
    assert 'dodge_left' in SIGNALS['dodge_right']['negative']
    assert 'dodge_right' in SIGNALS['dodge_left']['negative']
    assert not readiness([dict(label=l,split='test') for l in REQUIRED for _ in range(10)])['ready']
    assert 'constexpr' not in header([])
    print('PASS: labels, bilateral negatives, independent splits, no silent deployable constants')


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--check',action='store_true');p.add_argument('--data')
    p.add_argument('--output');p.add_argument('--evaluate');p.add_argument('--signal',choices=tuple(SIGNALS))
    args=p.parse_args()
    if args.check or not args.data: demo()
    else:
        records=load(args.data)
        result=test_report(records,args.evaluate) if args.evaluate else save(records,args.output) if args.output else report(records)
        if args.signal:
            result={**result, 'signals':[r for r in result.get('signals',[]) if r['signal']==args.signal]}
        print(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False))

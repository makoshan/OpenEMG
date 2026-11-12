"""ZC/SSC 门槛对照：0.1×窗内 RMS（现状） vs 静息校准固定门槛，外加 MApp / AAP（Sharma 2025）。

数据：原力手环 App 自录结印（三印 + 放松，每条 2 s，共 9 次佩戴）。
留出：每次留出一整次佩戴（其下全部录制）测试，其余训练；每次佩戴最早一条 seal_rest 只做静息校准，
四臂都不拿它训练或测试。滤波用 App gate 链口径（20 Hz 四阶高通 + 50/100/150 Hz 陷波，因果）。
窗 200 ms，步长 100 ms；分类器是本仓收缩 LDA。

    host/.venv-emg/bin/python -B host/emg_threshold_ablation.py --check
    host/.venv-emg/bin/python -B host/emg_threshold_ablation.py ~/Library/Application\\ Support/原力手环/project/data/emg/emg-wl8-data
"""
import argparse
import json
from pathlib import Path

import numpy as np
from scipy.signal import butter, iirnotch, sosfilt, sosfilt_zi, tf2sos

import emg_model

FS, WIN, STEP, SKIP = 2000, 400, 200, 200          # 200 ms 窗、100 ms 步、丢前 100 ms 起步段
LABELS = ('seal_daozhi', 'seal_poxie', 'seal_rest', 'seal_wulei')
REST = 'seal_rest'
# ponytail: scipy iirnotch 的 Q 是数字带宽口径，和 signal.ts notch() 的模拟 Q 在 150 Hz 差不到 0.1 Hz，不单独复刻
SOS = np.vstack([butter(4, 20, 'highpass', fs=FS, output='sos')] +
                [tf2sos(*iirnotch(50 * k, 30, fs=FS)) for k in (1, 2, 3)])


def clean(raw):
    """因果滤波，状态按首帧直流稳态初始化（同 DisplayFilter.reset）。"""
    zi = sosfilt_zi(SOS)[:, :, None] * raw[0][None, None, :]
    return sosfilt(SOS, raw, axis=0, zi=zi)[0][SKIP:]


def calibrate(rest, k):
    """静息校准：每路差分门槛 = k×静息差分标准差；噪声带 = 静息 1%/99% 分位（论文 NM，剔离群）。"""
    return {'thr': k * np.diff(rest, axis=0).std(0), 'lo': np.percentile(rest, 1, 0), 'hi': np.percentile(rest, 99, 0)}


def features(win, cal=None, extra=False):
    """emg_channels.features 的六个量；cal 给了就用静息固定门槛，否则 0.1×窗内 RMS。extra 加 MApp、AAP。"""
    x = win - win.mean(0)
    d = np.diff(x, axis=0)
    thr = cal['thr'] if cal is not None and 'fixed' in cal else .1 * (np.sqrt((x ** 2).mean(0)) + 1e-12)
    zc = ((x[:-1] * x[1:] < 0) & (np.abs(d) > thr)).sum(0)
    ssc = ((d[:-1] * d[1:] < 0) & ((np.abs(d[:-1]) > thr) | (np.abs(d[1:]) > thr))).sum(0)
    spec = np.abs(np.fft.rfft(x * np.hanning(len(x))[:, None], axis=0)) ** 2
    f = np.fft.rfftfreq(len(x), 1 / FS)
    hi = np.log((spec[f >= 150].sum(0) + 1e-12) / (spec[f >= 20].sum(0) + 1e-12))
    out = [np.log(np.abs(x).mean(0) + 1e-9), np.log(np.sqrt((x ** 2).mean(0)) + 1e-9),
           np.log(np.abs(d).sum(0) + 1e-9), zc, ssc, hi]
    if extra:
        out.append(np.log(win.max(0) - win.min(0) + 1e-9))                  # MApp：窗内峰峰值
        out_band = (win > cal['hi']) | (win < cal['lo'])                    # AAP：从噪声带内跨到带外的次数
        out.append((out_band[1:] & ~out_band[:-1]).sum(0))
    return np.concatenate(out)


ARMS = {'A 窗内RMS门槛': (False, False), 'B 静息固定门槛': (True, False),
        'C A+MApp/AAP': (False, True), 'D B+MApp/AAP': (True, True)}


def load(folder):
    recs = []
    for label in LABELS:
        for f in sorted((Path(folder) / label).glob('*.npz')):
            meta = json.loads(f.with_suffix('.json').read_text())
            z = np.load(f)
            assert int(z['emg_hz']) == FS, f
            recs.append({'file': f.name, 'label': label, 'group': meta['donning'], 'at': meta['recordedAt'],
                         'x': clean(z['emg_uv'].astype(float))})
    return recs


def split_calibration(recs):
    """每次佩戴最早一条放松录制拿去校准，从评测集里拿掉。"""
    cal_ids = {}
    for r in sorted(recs, key=lambda r: r['at']):
        if r['label'] == REST:
            cal_ids.setdefault(r['group'], id(r))
    cal = {g: next(r['x'] for r in recs if id(r) == i) for g, i in cal_ids.items()}
    return [r for r in recs if id(r) not in cal_ids.values() and r['group'] in cal], cal


def windows(x):
    return [x[i:i + WIN] for i in range(0, len(x) - WIN + 1, STEP)]


def evaluate(recs, cal_rest, k=2.0, shuffle=None):
    """逐次佩戴留出。返回每臂 汇总 + 逐折。shuffle=rng 时打乱训练标签做阴性对照。"""
    cals = {g: calibrate(r, k) for g, r in cal_rest.items()}
    out = {}
    for arm, (fixed, extra) in ARMS.items():
        folds, pooled = [], {'truth': [], 'pred': [], 'rec_truth': [], 'rec_pred': []}
        for g in sorted(cal_rest):
            def vecs(rs):
                X, y, rid = [], [], []
                for n, r in enumerate(rs):
                    cal = dict(cals[r['group']], **({'fixed': 1} if fixed else {}))
                    for w in windows(r['x']):
                        X.append(features(w, cal, extra)); y.append(r['label']); rid.append(n)
                return np.array(X), y, rid
            tr = [r for r in recs if r['group'] != g]
            te = [r for r in recs if r['group'] == g]
            Xtr, ytr, _ = vecs(tr)
            if shuffle is not None:
                ytr = list(shuffle.permutation(ytr))
            model = emg_model._fit_generic(Xtr, ytr)
            Xte, yte, rid = vecs(te)
            pred = emg_model.predict(model, Xte)
            # 整条录制多数票：放松录制被投成某个印 = 一次误触
            rec_pred = [max(set(p), key=p.count) for p in
                        ([pr for pr, i in zip(pred, rid) if i == n] for n in range(len(te)))]
            pooled['truth'] += yte; pooled['pred'] += pred
            pooled['rec_truth'] += [r['label'] for r in te]; pooled['rec_pred'] += rec_pred
            folds.append({'group': g, **metrics(yte, pred)})
        out[arm] = {**metrics(pooled['truth'], pooled['pred']),
                    'rest_rec_false_trigger': rate(pooled['rec_truth'], pooled['rec_pred'], REST, lambda p: p != REST),
                    'rec_accuracy': round(float(np.mean([t == p for t, p in zip(pooled['rec_truth'], pooled['rec_pred'])])), 3),
                    'folds': folds}
    return out


def rate(truth, pred, cls, hit):
    sel = [p for t, p in zip(truth, pred) if t == cls]
    return round(sum(map(hit, sel)) / max(len(sel), 1), 3)


def metrics(truth, pred):
    seal = [(t, p) for t, p in zip(truth, pred) if t != REST]
    return {'balanced': emg_model._report(truth, pred, list(LABELS))['balanced'],
            'rest_false_trigger': rate(truth, pred, REST, lambda p: p != REST),     # 放松窗被判成印
            'seal_miss': round(sum(p == REST for _, p in seal) / max(len(seal), 1), 3),   # 印被判成放松
            'seal_accuracy': round(sum(t == p for t, p in seal) / max(len(seal), 1), 3),
            'windows': len(truth)}


def check():
    """合成：放松=底噪，三印各驱动不同通道。基线要远高于随机，打乱标签要回到随机附近。"""
    rng = np.random.default_rng(0)
    recs = []
    for g in range(1, 5):
        for n in range(5):
            for k, label in enumerate(LABELS):
                gain = np.ones(8)
                if label != REST:
                    gain[[k * 2, k * 2 + 1]] = 4
                recs.append({'file': f'{g}-{n}-{label}', 'label': label, 'group': g, 'at': f'{g}{n:02d}{k}',
                             'x': rng.normal(0, 1, (3600, 8)) * gain})
    ev, cal = split_calibration(recs)
    real = evaluate(ev, cal)['A 窗内RMS门槛']
    shuf = evaluate(ev, cal, shuffle=np.random.default_rng(1))['A 窗内RMS门槛']
    assert real['balanced'] > .9, real
    assert shuf['balanced'] < .4, shuf
    print(f"check: 基线 {real['balanced']:.2f}，打乱标签 {shuf['balanced']:.2f}；通过")


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('folder', nargs='?'); p.add_argument('--check', action='store_true')
    p.add_argument('--out')
    a = p.parse_args()
    if a.check or not a.folder:
        check()
    else:
        recs, cal = split_calibration(load(a.folder))
        report = {'recordings': len(recs), 'calibration_rest': len(cal),
                  'by_k': {k: evaluate(recs, cal, k) for k in (1.0, 2.0, 3.0)},
                  'shuffled_control': evaluate(recs, cal, 2.0, np.random.default_rng(1))['A 窗内RMS门槛']}
        for k, arms in report['by_k'].items():
            for arm, r in arms.items():
                print(f"k={k} {arm}: 平衡准确率 {r['balanced']}  放松误触(窗) {r['rest_false_trigger']}  "
                      f"放松误触(整条) {r['rest_rec_false_trigger']}  印准确率 {r['seal_accuracy']}  印漏判 {r['seal_miss']}")
        print('打乱标签:', report['shuffled_control']['balanced'])
        if a.out:
            Path(a.out).parent.mkdir(parents=True, exist_ok=True)
            Path(a.out).write_text(json.dumps(report, ensure_ascii=False, indent=1))

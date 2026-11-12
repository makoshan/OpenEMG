#!/usr/bin/env python3
"""对照实验：同一批录音按「条件」分组，每组各出一行：条数、底噪、动作/放松比、留一准确率、每类 3 条校准准确率。

怎么用（不改 App）：
  戴好手环后，在校准页的「佩戴位置 / 条件」框里写明这一轮【只改变的一个条件】（例如「腕部贴掌根 · 盐水」），整轮校准；
  再换下一个条件（清水 / 电极膏 / 墨水块……），再整轮校准。校准页每轮会自动把佩戴编号 +1，session 字段里带着你写的文字。
  本脚本按 (日期, 佩戴编号, session 文字) 分组，一组 = 一个条件。结果只读，不写任何录音。

  python host/compare_conditions.py --since 2026-10-12            # 今天之后的所有组
  python host/compare_conditions.py --contains 盐水 --contains 清水 --out evidence/xxx.md
  python host/compare_conditions.py --check                       # 合成数据自检（含必失败对照）

评分口径与 App 校准一致：对准动作的 0.4 s 窗（滤波能量峰前 0.15 s、后 0.25 s）、5 频段功率、收缩 LDA（wl8_train）。
这是离线近似，不是 App 服务端那份代码。数据目录默认 PrintThings 工程里的 data/emg，用 --data 改。
"""
import argparse, json, os, sys, tempfile
from collections import defaultdict
from pathlib import Path
import numpy as np
from scipy.signal import butter, sosfiltfilt

sys.path.insert(0, os.environ.get('GNI_FW', str(Path(__file__).resolve().parents[1] / 'firmware/cheez-s3')))
import wl8_train

DATA = Path(__file__).resolve().parent / 'emg-data'
SOS = butter(4, [20, 450], 'bandpass', fs=2000, output='sos')
REST_LABELS = ('rest', 'meta_rest', 'mouse_rest', 'motion_rest', 'thumb_rest')
REPEATS = 50


def window(emg):
    """滤波后对准能量峰取 [-0.15, +0.25] s（2 kHz 下 800 点）。录音不够长就取正中。"""
    e = sosfiltfilt(SOS, np.asarray(emg, float), axis=0)
    env = np.convolve((e ** 2).sum(1), np.ones(200) / 200, 'same')
    lo, hi = 300, len(e) - 500
    p = lo + int(np.argmax(env[lo:hi])) if hi > lo else len(e) // 2
    return e[max(0, p - 300):p + 500]


def load(data, prefix):
    """返回 {(日期, 佩戴编号, session): [(标签, 窗口, 录制时间)]}。"""
    groups = defaultdict(list)
    for split in ('emg-wl8-data', 'emg-wl8-data-rewear'):
        for f in sorted((data / split).glob(f'{prefix}*/*.npz')):
            meta_f = f.with_suffix('.json')
            if not meta_f.exists(): continue
            m = json.loads(meta_f.read_text())
            try: z = np.load(f, allow_pickle=False); emg = z['emg_uv']
            except Exception: continue
            if emg.ndim != 2 or emg.shape[1] != 8 or len(emg) < 1000: continue
            groups[(str(m.get('recordedAt', ''))[:10], m.get('donning'), str(m.get('session', '')))].append((f.parent.name, window(emg), str(m.get('recordedAt', ''))))
    return groups


def band_features(wins):
    from scipy.signal import welch
    out = []
    for w in wins:
        f, p = welch(w - w.mean(0), 2000, nperseg=400, axis=0); ok = f >= 20
        for k in range(1, 20): ok &= np.abs(f - 50 * k) > 4
        out.append(np.array([np.log(p[ok & (f >= lo) & (f < hi)].mean(0) + 1e-9) for lo, hi in wl8_train.BANDS]).ravel())
    return np.array(out)


def bal(yt, yp):
    return float(np.mean([np.mean(yp[yt == c] == c) for c in np.unique(yt)]))


def score_group(items, rng, repeats=REPEATS):
    labels = np.array([l for l, _, _ in items]); wins = [w for _, w, _ in items]; cls, cnt = np.unique(labels, return_counts=True)
    rest = [i for i, l in enumerate(labels) if l in REST_LABELS]; act = [i for i, l in enumerate(labels) if l not in REST_LABELS]
    noise = float(np.median([np.sqrt((wins[i] ** 2).mean(0)).max() for i in rest])) if rest else float('nan')
    ratio = float(np.median([np.sqrt((wins[i] ** 2).mean(1)).max() for i in act]) / noise) if rest and act else float('nan')
    row = dict(n=len(items), classes=len(cls), min_per_class=int(cnt.min()), noise_uv=noise, ratio=ratio, loo=None, k3=None, shuffled=None)
    if len(cls) < 3 or cnt.min() < 3: return row           # 类不全或每类不足 3 条：不出准确率
    F = band_features(wins)
    pred = np.array([wl8_train.predict(wl8_train.fit(np.delete(F, i, 0), np.delete(labels, i)), F[i:i + 1])[0] for i in range(len(labels))])
    row['loo'] = bal(labels, pred)
    if cnt.min() >= 4:
        acc, sh = [], []
        for _ in range(repeats):
            cal = np.concatenate([rng.permutation(np.flatnonzero(labels == c))[:3] for c in cls]); te = np.setdiff1d(np.arange(len(labels)), cal)
            acc.append(bal(labels[te], wl8_train.predict(wl8_train.fit(F[cal], labels[cal]), F[te])))
            sh.append(bal(labels[te], wl8_train.predict(wl8_train.fit(F[cal], rng.permutation(labels[cal])), F[te])))
        row['k3'], row['shuffled'] = float(np.mean(acc)), float(np.mean(sh))
    return row


def fmt(v, pct=False, nd=0):
    if v is None or (isinstance(v, float) and np.isnan(v)): return '—'
    return f'{v * 100:.0f}%' if pct else f'{v:.{nd}f}'


def report(groups, a):
    rng = np.random.default_rng(0); lines = ['| 日期 | 佩戴 | 条件（session 原文） | 条数 | 类数 | 底噪 µV | 动作/放松 | 留一 | 每类 3 条校准 | 打乱对照 |', '|---|---|---|---|---|---|---|---|---|---|']; rows = []
    for (day, don, sess), items in sorted(groups.items(), key=lambda kv: (kv[0][0], str(kv[0][1]), kv[0][2])):
        if a.since and day < a.since: continue
        if a.contains and not all(c in sess for c in a.contains) and not any(c in sess for c in a.contains): continue
        r = score_group(items, rng); rows.append(((day, don, sess), r))
        lines.append(f'| {day} | {don} | {sess} | {r["n"]} | {r["classes"]} | {fmt(r["noise_uv"])} | {fmt(r["ratio"], nd=1)} | {fmt(r["loo"], True)} | {fmt(r["k3"], True)} | {fmt(r["shuffled"], True)} |')
    return '\n'.join(lines), rows


def check():
    """合成两个条件：好（8 路里每类各有一路明显更响）与坏（8 路同样噪声、类间无差别）。好必须明显高于坏；打乱对照必须接近瞎猜。"""
    rng = np.random.default_rng(3)
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        for cond, good in (('条件甲 好接触', True), ('条件乙 坏接触', False)):
            don = 1 if good else 2
            for ci, lab in enumerate(['rest', 'a', 'b', 'c', 'd']):
                dest = root / 'emg-wl8-data' / f'mouse_{lab}'; dest.mkdir(parents=True, exist_ok=True)
                for j in range(6):
                    gain = np.full(8, 3.0 if good else 60.0)
                    if lab != 'rest' and good: gain[ci] = 80.0
                    emg = rng.normal(size=(4000, 8)) * gain
                    if lab != 'rest' and good: emg[1500:2300, ci % 8] *= 3
                    f = dest / f'{lab}-{don}-{j}.npz'; np.savez(f, emg_uv=emg)
                    f.with_suffix('.json').write_text(json.dumps({'donning': don, 'session': f'左手 · {cond}', 'recordedAt': '2026-10-12T10:00:00'}))
        a = argparse.Namespace(since='', contains=[]); groups = load(root, 'mouse_'); table, rows = report(groups, a)
    by = {k[2]: r for k, r in rows}; good, bad = by['左手 · 条件甲 好接触'], by['左手 · 条件乙 坏接触']
    assert good['loo'] is not None and bad['loo'] is not None, '合成数据没出准确率'
    assert good['loo'] - bad['loo'] > 0.25, f'好条件应明显高于坏条件：{good["loo"]:.2f} vs {bad["loo"]:.2f}'
    assert good['noise_uv'] < bad['noise_uv'] / 3, '底噪应能区分好坏'
    assert good['shuffled'] < good['k3'] - 0.2, f'打乱对照应接近瞎猜：{good["shuffled"]:.2f} vs {good["k3"]:.2f}'
    print(table); print('check 通过：好条件留一', fmt(good['loo'], True), '> 坏条件', fmt(bad['loo'], True), '；打乱对照', fmt(good['shuffled'], True))


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--data', default=str(DATA)); p.add_argument('--prefix', default='mouse_', help='标签前缀：mouse_ / meta_ / motion_ / thumb_')
    p.add_argument('--since', default='', help='只看这天及以后（YYYY-MM-DD）'); p.add_argument('--contains', action='append', default=[], help='session 里含该词的组（可多次）')
    p.add_argument('--out', help='结果写成 markdown'); p.add_argument('--check', action='store_true')
    a = p.parse_args()
    if a.check: check(); sys.exit(0)
    groups = load(Path(a.data), a.prefix); table, rows = report(groups, a); print(table)
    if a.out: Path(a.out).write_text('# 条件对照\n\n' + table + '\n')

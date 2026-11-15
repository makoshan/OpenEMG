"""环形卷积 + 环向旋转增强 + 权重平均，对摘下重戴有没有用。

评估环形肌电公开基准里的三条经典思路，代码在本仓从头写，不含外部代码、数据和权重：
  ring   每路电极共用同一组时间卷积，再沿电极环做首尾相接（circular）的卷积；最后按电极位置展平进分类头
  rot    训练时把八路沿环整体转一个随机分数（±0.5 路 / ±1 路），相邻两路线性插值，模拟重戴时腕带转了一点
  swa    训练后 30% 轮次每轮末存一份权重，取算术平均，再用训练数据重算 BatchNorm 统计；推理开销不变
基线 base 是现行 emg_gni_train.Net（emg_wl8_cnn.py 在用的那个，第一层直接把八路压平）。

数据与切分同 rewear_diag.py：结印四类，按（日期, 佩戴号, 左右手）分组，每类 ≥4 条的佩戴参与；
同手留一次佩戴：用同手其它佩戴训练，在留出佩戴上考试。每次佩戴用自己时间最早 20% 录音的各路中位幅度
做缩放（不看标签，同产品「首段校准」）。录音先 20 Hz 高通，再 2 kHz → 1 kHz；训练随机裁 0.4 s，
考试在录音中间 80% 均匀取 5 个 0.4 s 窗、logits 平均成一条录音的判定。指标：录音级 Macro-F1、平衡准确率。
只读本地录音，输出不含原始信号和路径。

    host/.venv-emg/bin/python -B host/research/ring_cnn_rewear.py --check
    host/.venv-emg/bin/python -B host/research/ring_cnn_rewear.py --data "$LOCAL_EMG_DATA" --out evidence/<目录>/result.json
"""
import argparse
import hashlib
import json
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from scipy.signal import butter, decimate, sosfiltfilt
from sklearn.metrics import f1_score

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from emg_gni_train import Net, CROP  # noqa: E402  现行基线网络，0.4 s × 1 kHz

FS, HZ = 2000, 1000
LABELS = ('seal_rest', 'seal_poxie', 'seal_wulei', 'seal_daozhi')
HP = butter(4, 20, 'highpass', fs=FS, output='sos')
EARLY, N_TEST_CROPS, SWA_FRAC = .2, 5, .3
# 名称 → (网络, 旋转幅度[路], 是否权重平均)
VARIANTS = {'base': ('base', 0., False), 'base_rot': ('base', .5, False), 'base_rot_swa': ('base', .5, True),
            'ring': ('ring', 0., False), 'ring_rot': ('ring', .5, False), 'ring_rot1': ('ring', 1., False),
            'ring_rot_swa': ('ring', .5, True)}


class RingConv(nn.Module):
    """电极维首尾各补一路（第 0 路左边是第 7 路），时间维普通补零；stride 只作用在时间维。"""
    def __init__(self, i, o, k):
        super().__init__()
        self.c = nn.Conv2d(i, o, (3, k), (1, 2), (0, k // 2)); self.b = nn.BatchNorm2d(o)

    def forward(self, x):                                   # x: (B, F, C, T)
        x = torch.cat([x[:, :, -1:], x, x[:, :, :1]], 2)
        return F.relu(self.b(self.c(x)))


class RingNet(nn.Module):
    def __init__(self, ch, n):
        super().__init__()
        # 每路电极共用的时间卷积：核 (1, k) 不跨电极
        self.t = nn.Sequential(nn.Conv2d(1, 16, (1, 9), (1, 2), (0, 4)), nn.BatchNorm2d(16), nn.ReLU(),
                               nn.Conv2d(16, 32, (1, 7), (1, 2), (0, 3)), nn.BatchNorm2d(32), nn.ReLU())
        self.r = nn.Sequential(RingConv(32, 48, 7), RingConv(48, 48, 5))
        self.head = nn.Linear(48 * ch, n)

    def trunk(self, x):                                     # (B, C, T) → (B, 48, C)，对电极环平移等变
        return self.r(self.t(x[:, None])).mean(-1)

    def forward(self, x):
        return self.head(self.trunk(x).flatten(1))


def make(kind, ch, n):
    return Net(ch, n) if kind == 'base' else RingNet(ch, n)


def ring_shift(x, s):
    """x (B, C, T)，s (B,) 路数（可为小数）：新第 c 路 = 原第 c−s 路，非整数时相邻两路线性插值。"""
    C = x.shape[1]; k = torch.floor(s); f = (s - k)[:, None, None]
    c = torch.arange(C, device=x.device)[None]
    g = lambda kk: torch.gather(x, 1, ((c - kk[:, None].long()) % C)[:, :, None].expand(-1, -1, x.shape[2]))
    return (1 - f) * g(k) + f * g(k + 1)


def prep(e):
    """(n, 8) µV @2 kHz → (8, n/2) float32 @1 kHz。"""
    x = sosfiltfilt(HP, np.asarray(e, float) - np.mean(e, 0), axis=0)
    return decimate(x, FS // HZ, axis=0, zero_phase=True).T.astype(np.float32)


def load(root):
    groups, manifest = defaultdict(list), []
    for label in LABELS:
        for p in sorted((root / 'emg-wl8-data' / label).glob('*.npz')):
            m = json.loads(p.with_suffix('.json').read_text())
            with np.load(p, allow_pickle=False) as z: e = z['emg_uv'].astype(float)
            if e.ndim != 2 or e.shape[1] != 8 or len(e) < 2000 or not np.isfinite(e).all(): continue
            key = (str(m.get('recordedAt', ''))[:10], m.get('donning'), str(m.get('session', '')).split('·')[0].strip())
            groups[key].append(dict(label=LABELS.index(label), t=str(m.get('recordedAt', '')), x=prep(e)))
            manifest.append(hashlib.sha256(p.read_bytes()).hexdigest())
    for rows in groups.values():                            # 每次佩戴：时间最早 20% 录音定各路缩放，不看标签
        rows.sort(key=lambda r: r['t'])
        early = rows[:max(1, int(len(rows) * EARLY))]
        sc = np.median(np.concatenate([np.abs(r['x']) for r in early], 1), 1) + 1e-6
        for r in rows: r['x'] = r['x'] / sc[:, None]
    return groups, manifest


def batch_crops(xs, rng):
    out = []
    for x in xs:
        T = x.shape[1]; s = rng.integers(T // 10, T - CROP - T // 10 + 1); out.append(x[:, s:s + CROP])
    return np.stack(out)


def test_crops(x):
    T = x.shape[1]; starts = np.linspace(T // 10, T - CROP - T // 10, N_TEST_CROPS).astype(int)
    return np.stack([x[:, s:s + CROP] for s in starts])


def recompute_bn(model, xs, rng, passes=4, batch=64):
    """权重平均后 BN 的均值方差不再对应，用训练数据重新累计（不更新权重）。"""
    bns = [m for m in model.modules() if isinstance(m, nn.modules.batchnorm._BatchNorm)]
    if not bns: return
    for m in bns: m.reset_running_stats(); m.momentum = None
    model.train()
    with torch.no_grad():
        for _ in range(passes):
            order = rng.permutation(len(xs))
            for i in range(0, len(xs), batch):
                model(torch.tensor(batch_crops([xs[j] for j in order[i:i + batch]], rng)))


def fit(kind, xs, y, rot, swa, seed, epochs=60, lr=3e-3, batch=64):
    rng = np.random.default_rng(seed); torch.manual_seed(seed)
    model = make(kind, xs[0].shape[0], len(LABELS))
    w = torch.tensor(1 / np.maximum(np.bincount(y, minlength=len(LABELS)), 1), dtype=torch.float32)
    loss_f = nn.CrossEntropyLoss(weight=w / w.sum() * len(LABELS))
    opt = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-3)
    steps = -(-len(xs) // batch)
    sched = torch.optim.lr_scheduler.OneCycleLR(opt, lr, total_steps=epochs * steps)
    snaps, start = [], int(epochs * (1 - SWA_FRAC))
    for ep in range(epochs):
        model.train(); order = rng.permutation(len(xs))
        for i in range(0, len(xs), batch):
            b = order[i:i + batch]
            xb = torch.tensor(batch_crops([xs[j] for j in b], rng))
            xb = xb * torch.exp(torch.randn(len(b), xb.shape[1], 1) * .15)        # 电极增益抖动（同现行）
            if rot: xb = ring_shift(xb, torch.empty(len(b)).uniform_(-rot, rot))
            opt.zero_grad(); loss_f(model(xb), torch.tensor(y[b])).backward(); opt.step(); sched.step()
        if swa and ep >= start: snaps.append({k: v.detach().clone() for k, v in model.state_dict().items()})
    if swa:
        avg = {k: (torch.stack([s[k].float() for s in snaps]).mean(0).to(snaps[0][k].dtype) if snaps[0][k].is_floating_point() else snaps[-1][k])
               for k in snaps[0]}
        model.load_state_dict(avg); recompute_bn(model, xs, rng)
    return model


@torch.no_grad()
def predict(model, xs):
    model.eval()
    return np.array([int(model(torch.tensor(test_crops(x))).mean(0).argmax()) for x in xs])


def score(pred, y):
    return dict(macro_f1=round(float(f1_score(y, pred, average='macro', labels=list(range(len(LABELS))), zero_division=0)), 4),
                balanced=round(float(np.mean([np.mean(pred[y == c] == c) for c in np.unique(y)])), 4))


def run(groups, variants, seeds):
    eligible = sorted(k for k, rows in groups.items() if min(Counter(r['label'] for r in rows).get(c, 0) for c in range(len(LABELS))) >= 4)
    folds = []
    for k in eligible:
        same = [j for j in eligible if j[2] == k[2] and j != k]
        if not same: continue
        pool = [r for j in same for r in groups[j]]
        xs, y = [r['x'] for r in pool], np.array([r['label'] for r in pool])
        xt, yt = [r['x'] for r in groups[k]], np.array([r['label'] for r in groups[k]])
        res = dict(date=k[0], wear=k[1], hand=k[2], train_takes=len(pool), test_takes=len(xt))
        for name in variants:
            kind, rot, swa = VARIANTS[name]
            per = [score(predict(fit(kind, xs, y, rot, swa, s), xt), yt) for s in seeds]
            res[name] = dict(macro_f1=round(float(np.mean([p['macro_f1'] for p in per])), 4),
                             balanced=round(float(np.mean([p['balanced'] for p in per])), 4), seeds=per)
        print(k, {n: res[n]['macro_f1'] for n in variants}, flush=True)
        folds.append(res)
    return folds


def summarize(folds, variants):
    out = {}
    for n in variants:
        v = np.array([f[n]['macro_f1'] for f in folds]); d = v - np.array([f['base']['macro_f1'] for f in folds])
        out[n] = dict(macro_f1=round(float(v.mean()), 4), balanced=round(float(np.mean([f[n]['balanced'] for f in folds])), 4),
                      minus_base=round(float(d.mean()), 4), folds_better=int((d > 0).sum()), folds_worse=int((d < 0).sum()))
    return out


def checks():
    torch.manual_seed(0); rng = np.random.default_rng(0)
    x = torch.randn(3, 8, CROP)
    # 整数旋转 = torch.roll；0 不变；转 0.5 等于相邻两路平均；转 8 回原样
    assert torch.allclose(ring_shift(x, torch.full((3,), 1.)), torch.roll(x, 1, 1))
    assert torch.allclose(ring_shift(x, torch.zeros(3)), x)
    assert torch.allclose(ring_shift(x, torch.full((3,), .5)), (x + torch.roll(x, 1, 1)) / 2)
    assert torch.allclose(ring_shift(x, torch.full((3,), -1.)), torch.roll(x, -1, 1))
    # 环形主干等变：输入沿电极转 3 路，特征也转 3 路（第 0 路与第 7 路相邻才成立）
    m = RingNet(8, 4).eval()
    with torch.no_grad(): assert torch.allclose(m.trunk(torch.roll(x, 3, 1)), torch.roll(m.trunk(x), 3, 2), atol=1e-5)
    # 反例：把首尾补位换成补零，等变必须被破坏，证明上面那条不是空过
    bad = RingNet(8, 4).eval(); bad.load_state_dict(m.state_dict())
    for rc in bad.r: rc.forward = (lambda rc: lambda z: F.relu(rc.b(rc.c(F.pad(z, (0, 0, 1, 1))))))(rc)
    with torch.no_grad(): assert not torch.allclose(bad.trunk(torch.roll(x, 3, 1)), torch.roll(bad.trunk(x), 3, 2), atol=1e-3)
    params = {k: sum(p.numel() for p in make(k, 8, 4).parameters()) for k in ('base', 'ring')}
    assert params['ring'] < 80_000, params
    # 合成数据：四类各在不同电极有能量；可学 → 留出佩戴（整体转 0–1 路）分数高；打乱标签 → 接近随机
    def synth(n, shift, seed):
        r = np.random.default_rng(seed); xs, ys = [], []
        for i in range(n):
            c = i % 4; g = np.ones(8) * .3; g[(2 * c + shift) % 8] = 2.; g[(2 * c + 1 + shift) % 8] = 1.
            xs.append((r.normal(size=(8, 2100)) * g[:, None]).astype(np.float32)); ys.append(c)
        return xs, np.array(ys)
    xs, y = synth(64, 0, 1); xt, yt = synth(24, 1, 2)
    good = score(predict(fit('ring', xs, y, .5, True, 0, epochs=15), xt), yt)
    assert good['balanced'] > .6, good
    shuf = score(predict(fit('ring', xs, rng.permutation(y), .5, False, 0, epochs=15), xt), yt)
    assert shuf['balanced'] < .5, shuf
    return dict(params=params, synth_shift1=good, synth_shuffled=shuf)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--data', type=Path); ap.add_argument('--out', type=Path); ap.add_argument('--check', action='store_true')
    ap.add_argument('--variants', default=','.join(VARIANTS)); ap.add_argument('--seeds', default='0,1,2')
    a = ap.parse_args()
    torch.set_num_threads(4)
    if a.check: print(json.dumps(checks(), ensure_ascii=False)); print('ring_cnn_rewear check passed'); return
    if not (a.data and a.out): ap.error('要 --data 和 --out，或 --check')
    if a.out.exists(): raise ValueError('拒绝覆盖结果')
    variants = a.variants.split(','); assert variants[0] == 'base' and all(v in VARIANTS for v in variants), variants
    seeds = [int(s) for s in a.seeds.split(',')]
    t0 = time.time(); groups, manifest = load(a.data)
    folds = run(groups, variants, seeds)
    report = dict(checks=checks(), recording_hashes=manifest, variants={n: dict(zip(('net', 'rot', 'swa'), VARIANTS[n])) for n in variants},
                  seeds=seeds, folds=folds, summary=summarize(folds, variants), seconds=round(time.time() - t0),
                  limits='历史结印录音离线；9 次佩戴、录音级判定；不含连续流误触和延迟；与 rewear_diag 的 LDA 取窗不同，只能粗比。')
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(report, ensure_ascii=False, indent=1) + '\n')
    print(json.dumps(report['summary'], ensure_ascii=False, indent=1))


if __name__ == '__main__': main()

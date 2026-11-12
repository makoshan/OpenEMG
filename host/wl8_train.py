"""八通道手势训练（给 App「肌电工作室」的训练剧场和实时识别用）。

特征：每路 5 个频段的 log 功率（去掉 20 Hz 以下和 50 Hz 各次谐波 ±4 Hz），8 × 5 = 40 维；分类器：收缩 LDA。
这套口径在 evidence/2026-09-29-wl8-bringup.md 3.12 / 3.24 事先定好（重戴 3 类 87%），这里不再挑参数。

产物（models/emg/wl8/<run-id>/）：
  run.json   计数、同次佩戴 / 摘下重戴（没有重戴目录时按佩戴编号留一次佩戴，rewear_source 标来源）/ 打乱对照、单路准确率（电极重要性）、学习曲线、2D 判别投影、混淆矩阵、排除了哪些样本和为什么
  model.npz  类别、均值、协方差逆、频段配置 —— LivePredictor 读它做实时识别

    python3 wl8_train.py --check                        # 合成数据：好数据要学得会，打乱标签要掉到机会水平
    python3 wl8_train.py --data <工程>/data/emg          # 用真实数据训练一次，打印摘要
"""
import argparse
import json
import time
from pathlib import Path

import numpy as np
from scipy.signal import welch

FS = 2000
BANDS = [(20, 45), (55, 95), (105, 145), (155, 245), (255, 445)]
SHRINK = .5
DEFAULT_LABELS = ('rest', 'pinch', 'fist')


def features(e):
    """(n,8) µV → 40 维：每路 5 个频段的 log 平均功率，工频格和 20 Hz 以下不算。"""
    e = np.asarray(e, float)
    f, P = welch(e - e.mean(0), FS, nperseg=min(512, len(e)), axis=0)
    ok = f >= 20
    for k in range(1, 20): ok &= np.abs(f - 50 * k) > 4
    return np.array([np.log(P[ok & (f >= lo) & (f < hi)].mean(0) + 1e-9) for lo, hi in BANDS]).ravel()   # 频段在前、通道在后


def ptp_windows(e, fs=FS):
    """每个 1 秒窗（步 0.5 秒）每路的峰峰值，(窗数, 8) µV。识别时 signal_facts 的 vpp = 一窗里各路峰峰值的平均，
    所以放松底噪存整张表，识别时按没屏蔽的路先平均、再取中位，聚合方式和识别时逐窗算的完全一致（复核 #88）。"""
    e = np.asarray(e, float)
    if len(e) < fs: return np.ptp(e, axis=0)[None]
    return np.array([np.ptp(e[i:i + fs], axis=0) for i in range(0, len(e) - fs + 1, fs // 2)])


def fit(X, y, shrink=SHRINK):
    cs = sorted(set(y)); mu = np.array([X[y == c].mean(0) for c in cs])
    C = sum(((X[y == c] - mu[i]).T @ (X[y == c] - mu[i])) for i, c in enumerate(cs)) / len(y)
    C = (1 - shrink) * C + shrink * np.eye(len(C)) * np.trace(C) / len(C)
    return dict(classes=cs, mu=mu, sinv=np.linalg.inv(C), cov=C)


def scores(m, X):
    """每类的 −½ 马氏距离（越大越像），和 softmax 概率。m 带 keep（屏蔽坏路后的子模型）时只用保留的特征列。"""
    if 'keep' in m: X = np.asarray(X)[:, m['keep']]
    d = np.array([np.einsum('ij,jk,ik->i', X - u, m['sinv'], X - u) for u in m['mu']]).T
    z = -.5 * d; p = np.exp(z - z.max(1, keepdims=True)); return z, p / p.sum(1, keepdims=True)


TEMPERATURES = (0.5, 1.0, 1.5, 2.0, 3.0, 4.0, 6.0, 8.0, 12.0, 16.0, 24.0, 32.0, 48.0, 64.0)


def calibrate_temperature(X, y, shrink=SHRINK):
    """留一法马氏距离温度校准（Noul 把握度校准）：抑制 40 维收缩 LDA 在短窗上的概率虚高，不改变 argmax 类别。"""
    X = np.asarray(X, float); y = np.asarray(y)
    cs = sorted(set(y))
    if len(X) <= len(cs) or any(np.sum(y == c) < 2 for c in cs): return 1.0
    held_d = []
    for i in range(len(X)):
        mi = fit(np.delete(X, i, 0), np.delete(y, i), shrink=shrink)
        d = np.array([np.einsum('ij,jk,ik->i', X[i:i + 1] - u, mi['sinv'], X[i:i + 1] - u) for u in mi['mu']]).T[0]
        held_d.append(d)
    held_d = np.asarray(held_d, float)
    target = np.array([cs.index(c) for c in y])
    losses = []
    for t in TEMPERATURES:
        logits = -0.5 * held_d / t
        mx = logits.max(axis=1, keepdims=True)
        lse = mx[:, 0] + np.log(np.exp(logits - mx).sum(axis=1))
        losses.append(float(np.mean(lse - logits[np.arange(len(y)), target])))
    return float(TEMPERATURES[int(np.argmin(losses))])


def calibrated_probs(m, X, temp=None):
    """按留一温度缩放马氏距离 logit，输出校准后的类别概率分布（argmax 与 scores 完全一致）。"""
    z, _ = scores(m, X)
    t = max(float(m.get('temp', 1.0) if temp is None else temp), 1e-6)
    zt = z / t; p = np.exp(zt - zt.max(1, keepdims=True))
    return p / p.sum(1, keepdims=True)


def noise_ratio_summary(rest_ptp, effort_ptp, max_ratio=0.10, min_pass_channels=6):
    """8 路静息/发力峰谷噪声比诊断（Sharma 2025 Eq. 1/5/6 口径）：每路静息中位峰峰值 ÷ 发力 P90 峰峰值 <= 10%。"""
    r_med = np.median(np.asarray(rest_ptp, float), axis=0)
    e_p90 = np.maximum(np.percentile(np.asarray(effort_ptp, float), 90, axis=0), 1e-9)
    ratio = r_med / e_p90
    ch_pass = ratio <= max_ratio
    n_pass = int(np.sum(ch_pass))
    return dict(
        ok=bool(n_pass >= min_pass_channels),
        pass_channels=n_pass,
        total_channels=int(len(ratio)),
        max_ratio_limit=float(max_ratio),
        mean_ratio_pct=round(float(np.mean(ratio) * 100.0), 2),
        ratio_pct=[round(float(v * 100.0), 2) for v in ratio],
        failed_channels_1based=[int(i + 1) for i, ok in enumerate(ch_pass) if not ok],
    )


def lane_keep(lanes, dim=len(BANDS) * 8):
    """屏蔽这些路（1–8）后保留的特征列。特征是频段在前、通道在后：第 i 列属于第 i % 8 + 1 路。"""
    return [i for i in range(dim) if i % 8 + 1 not in set(lanes)]


def mask_model(m, lanes):
    """去掉这几路：LDA 每类均值和共用协方差直接删对应行列（高斯边缘分布）。不收缩时严格等于不用这几路重训；
    有收缩时收缩量按全部路的方差均值定，和重训略有差别（自检里预测一致 ≥95%）。不重训，不到 1 ms。"""
    if not lanes: return m
    keep = lane_keep(lanes, m['mu'].shape[1]); C = m['cov'] if 'cov' in m else np.linalg.inv(m['sinv'])
    return dict(classes=m['classes'], mu=m['mu'][:, keep], sinv=np.linalg.inv(C[np.ix_(keep, keep)]), keep=keep)


def predict(m, X): return np.array(m['classes'])[scores(m, X)[0].argmax(1)]


def bal(yt, yp): return float(np.mean([np.mean(yp[yt == c] == c) for c in sorted(set(yt))]))


def projection(m, X):
    """LDA 判别方向上的 2D 坐标（类间散布对类内散布的前两个广义特征向量）。"""
    Sb = np.cov(m['mu'].T) if len(m['mu']) > 1 else np.eye(X.shape[1])
    w, V = np.linalg.eig(m['sinv'] @ Sb); order = np.argsort(-w.real)[:2]
    W = V[:, order].real; P = X @ W
    return P, W


def donning_of(f):
    """录音旁的 .json 里记的佩戴编号；没有就是 None。"""
    try: d = json.loads(Path(f).with_suffix('.json').read_text()).get('donning')
    except (OSError, ValueError, AttributeError): return None
    return d if type(d) is int else None


def load(root, labels, since=None):
    """<root>/<label>/*.npz → [(label, 特征, 元数据)]；元数据带文件名、时间、放松底噪。"""
    out = []
    for label in labels:
        for f in sorted(Path(root).glob(f'{label}/*.npz')):
            if since and f.stat().st_mtime < since: continue
            with np.load(f, allow_pickle=False) as z: e = z['emg_uv'].astype(float)
            if len(e) < FS: continue
            rms_ch = np.sqrt(((e - e.mean(0)) ** 2).mean(0))
            out.append((label, features(e), dict(file=f.name, mtime=f.stat().st_mtime, rms=float(np.median(rms_ch)), rms_ch=rms_ch, ptp=ptp_windows(e), donning=donning_of(f))))
    return out


def train(data_root, labels=DEFAULT_LABELS, since=None, progress=print, seed=0):
    """返回 (run 字典, model 字典)。progress(dict) 用来给界面推学习曲线等进度。"""
    rng = np.random.default_rng(seed); t0 = time.time()
    tr = load(Path(data_root) / 'emg-wl8-data', labels, since); te = load(Path(data_root) / 'emg-wl8-data-rewear', labels, since)
    # 训练集里的放松条：底噪超过放松中位数 1.5 倍的算"手在动"，不进训练（相对阈值，不写死 µV）；重戴集一条不挑
    rest_rms = [m['rms'] for l, _, m in tr if l == 'rest']; cut = 1.5 * float(np.median(rest_rms)) if rest_rms else np.inf
    excluded = [m['file'] for l, _, m in tr if l == 'rest' and m['rms'] > cut]
    tr = [r for r in tr if not (r[0] == 'rest' and r[2]['rms'] > cut)]
    labels = [l for l in labels if sum(r[0] == l for r in tr) >= 3]
    tr = [r for r in tr if r[0] in labels]; te = [r for r in te if r[0] in labels]
    if len(labels) < 2: raise ValueError('每类至少要 3 条训练样本、至少两类')
    Xtr, ytr = np.array([r[1] for r in tr]), np.array([r[0] for r in tr])
    Xte, yte = (np.array([r[1] for r in te]), np.array([r[0] for r in te])) if te else (np.zeros((0, Xtr.shape[1])), np.array([]))
    run = dict(labels=labels, counts=dict(train={l: int((ytr == l).sum()) for l in labels}, rewear={l: int((yte == l).sum()) for l in labels}),
               excluded=dict(files=excluded, rule=f'训练集放松条底噪 > 放松中位数 × 1.5（{cut:.0f} µV）视为手在动'), features='8 路 × 5 频段 log 功率，去工频格', shrink=SHRINK)
    progress(dict(stage='data', message=f"训练 {len(ytr)} 条（排除 {len(excluded)} 条手在动的放松），重戴 {len(yte)} 条"))
    # 同次佩戴：留一法
    loo = np.array([predict(fit(np.delete(Xtr, i, 0), np.delete(ytr, i)), Xtr[i:i + 1])[0] for i in range(len(ytr))])
    run['same_wear'] = bal(ytr, loo); progress(dict(stage='same_wear', value=run['same_wear']))
    # 缺一路时的同次佩戴留一：第 k 项 = 屏蔽第 k+1 路后的认对率，用来提示哪一路坏了会让哪对手势分不开
    run['lane_drop'] = []
    for lane in range(1, 9):
        k = lane_keep([lane], Xtr.shape[1])
        run['lane_drop'].append(bal(ytr, np.array([predict(fit(np.delete(Xtr, i, 0)[:, k], np.delete(ytr, i)), Xtr[i:i + 1, k])[0] for i in range(len(ytr))])))
    model = fit(Xtr, ytr)
    model['temp'] = run['temp'] = calibrate_temperature(Xtr, ytr, shrink=SHRINK)
    # 放松底噪（每路 1 秒窗峰峰值，取训练集放松条的中位）：识别时倍数门槛 = 倍数 × 这个数，所以每个人、每次重训都按自己的底噪
    # 只用最新一次佩戴的放松条：重戴、换人后底噪跟着这次的走，不被历史条数稀释（复核 #88）。别处自己拼的元数据可能没有 ptp
    rests = [m for l, _, m in tr if 'rest' in l and 'ptp' in m]
    wears = [m['donning'] for m in rests if m.get('donning') is not None]
    latest_wear = max(wears) if wears else None
    if latest_wear is not None: rests = [m for m in rests if m.get('donning') == latest_wear]
    if rests:
        model['rest_ptp'] = np.concatenate([m['ptp'] for m in rests])
        run['rest_vpp_uv'] = [round(float(v), 1) for v in np.median(model['rest_ptp'], axis=0)]   # 每路中位，只给页面看
        run['rest_wear'] = latest_wear
        rms_rows = [m['rms_ch'] for m in rests if 'rms_ch' in m]
        model['rest_rms'] = np.median(rms_rows, axis=0) if rms_rows else np.median(model['rest_ptp'], axis=0) / 6.0
        run['rest_rms_uv'] = [round(float(v), 1) for v in model['rest_rms']]
        efforts = [m for l, _, m in tr if 'rest' not in l and 'ptp' in m and (latest_wear is None or m.get('donning') == latest_wear)]
        if efforts:
            run['noise_ratio'] = noise_ratio_summary(model['rest_ptp'], np.concatenate([m['ptp'] for m in efforts]))
    groups = np.array([-1 if m['donning'] is None else m['donning'] for _, _, m in tr])
    wear_ids = sorted(set(groups.tolist()) - {-1})
    if len(yte):
        p = predict(model, Xte); run['rewear'] = bal(yte, p); run['rewear_source'] = '重戴目录'
        run['confusion'] = dict(rows=labels, matrix=[[int(((yte == a) & (p == b)).sum()) for b in labels] for a in labels])
        run['shuffled'] = float(np.mean([bal(yte, predict(fit(Xtr, rng.permutation(ytr)), Xte)) for _ in range(20)]))
        B, Bt = Xtr.reshape(len(ytr), len(BANDS), 8), Xte.reshape(len(yte), len(BANDS), 8)
        run['per_channel'] = [bal(yte, predict(fit(B[:, :, c], ytr, .3), Bt[:, :, c])) for c in range(8)]
        progress(dict(stage='rewear', value=run['rewear'], source=run['rewear_source'], shuffled=run['shuffled'], per_channel=run['per_channel']))
    elif len(wear_ids) >= 2:
        # 没有重戴目录：按录音记的佩戴编号轮流留出一次佩戴测试、其余训练（BrainFlow 训练脚本的分组留出）。
        # 同次佩戴留一条会把同一次佩戴的兄弟条放进训练，数偏高；这里测的永远是模型没见过的那次佩戴。没编号的条只进训练。
        held = np.isin(groups, wear_ids); yh = ytr[held]
        def by_wear(y=ytr, cols=slice(None), shrink=SHRINK):
            p = np.empty(len(y), object)
            for w in wear_ids:
                m = groups == w; p[m] = predict(fit(Xtr[~m][:, cols], y[~m], shrink), Xtr[m][:, cols])
            return p[held].astype(str)
        p = by_wear(); run['rewear'] = bal(yh, p); run['rewear_source'] = '留一次佩戴'
        run['confusion'] = dict(rows=labels, matrix=[[int(((yh == a) & (p == b)).sum()) for b in labels] for a in labels])
        run['shuffled'] = float(np.mean([bal(yh, by_wear(rng.permutation(ytr))) for _ in range(20)]))
        run['per_channel'] = [bal(yh, by_wear(cols=list(range(c, Xtr.shape[1], 8)), shrink=.3)) for c in range(8)]   # 第 c 路的 5 个频段列
        run['note'] = f'没有重戴目录：按佩戴编号留一次佩戴估计（{len(wear_ids)} 次佩戴轮流留出）'
        progress(dict(stage='rewear', value=run['rewear'], source=run['rewear_source'], shuffled=run['shuffled'], per_channel=run['per_channel']))
    else:
        run['rewear'] = None; run['note'] = '还没有重戴数据：只报同次佩戴（偏乐观）'
    # 学习曲线：每类 n 条训练，10 次随机抽样，测在重戴集上（没有就测留出的训练样本）
    curve = []
    nmax = min(int((ytr == l).sum()) for l in labels)
    for n in sorted({x for x in (2, 3, 5, 8, 10, 15, 20, 30, nmax) if 2 <= x <= nmax}):
        accs = []
        for _ in range(10):
            idx = np.concatenate([rng.choice(np.flatnonzero(ytr == l), n, replace=False) for l in labels])
            if len(yte): accs.append(bal(yte, predict(fit(Xtr[idx], ytr[idx]), Xte)))
            else:
                rest = np.setdiff1d(np.arange(len(ytr)), idx)
                if len(set(ytr[rest])) == len(labels): accs.append(bal(ytr[rest], predict(fit(Xtr[idx], ytr[idx]), Xtr[rest])))
        if accs:
            pt = dict(n=n, mean=float(np.mean(accs)), std=float(np.std(accs))); curve.append(pt); progress(dict(stage='curve', **pt))
    run['learning_curve'] = dict(points=curve, tested_on='重戴集' if len(yte) else '训练集留出部分')
    # 2D 判别投影：训练 / 重戴样本坐标 + 类中心，按录制时间排序，界面可以逐个"落点"
    P, W = projection(model, Xtr); Pt = Xte @ W if len(yte) else np.zeros((0, 2))
    order = np.argsort([r[2]['mtime'] for r in tr])
    run['projection'] = dict(train=[dict(x=float(P[i, 0]), y=float(P[i, 1]), label=str(ytr[i])) for i in order],
                             rewear=[dict(x=float(Pt[i, 0]), y=float(Pt[i, 1]), label=str(yte[i]), pred=str(predict(model, Xte[i:i + 1])[0])) for i in range(len(yte))],
                             centroids=[dict(x=float(c[0]), y=float(c[1]), label=l) for l, c in zip(model['classes'], model['mu'] @ W)])
    run['seconds'] = round(time.time() - t0, 1)
    progress(dict(stage='done', rewear=run['rewear'], same_wear=run['same_wear']))
    return run, dict(**model, W=W)


def save(run, model, out_root):
    rid = time.strftime('%Y%m%d-%H%M%S'); d = Path(out_root) / rid; d.mkdir(parents=True, exist_ok=True)
    run = dict(run, id=rid, created=time.strftime('%Y-%m-%dT%H:%M:%S'))
    (d / 'run.json').write_text(json.dumps(run, ensure_ascii=False, indent=1))
    np.savez(d / 'model.npz', classes=np.array(model['classes']), mu=model['mu'], sinv=model['sinv'], W=model['W'],
             bands=np.array(BANDS), fs=FS, shrink=SHRINK, **rest_extra(model))
    return d


def rest_extra(model):
    """存模型时带上放松底噪与留一校准温度（旧模型没有就不带）。emg8-server 覆盖 save 时也用它。"""
    out = {}
    if model.get('rest_ptp') is not None: out['rest_ptp'] = np.asarray(model['rest_ptp'], float)
    if model.get('rest_rms') is not None: out['rest_rms'] = np.asarray(model['rest_rms'], float)
    if model.get('temp') is not None: out['temp'] = float(model['temp'])
    return out


def times_setting(value):
    """幅度门槛的倍数：0..20 倍放松底噪，0 表示不拦。"""
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= float(value) <= 20:
        raise ValueError('幅度门槛倍数必须在 0 到 20')
    return round(float(value), 2)


def gate_settings(threshold_uv, sensitivity):
    """幅度门槛 0..5000 µV，0 表示不拦。灵敏度是 1..10 的整数，有效门槛 = 门槛 × (11 − 灵敏度) / 5：6 保持原门槛（5 是 1.2 倍），越大越容易触发。"""
    if isinstance(threshold_uv, bool) or not isinstance(threshold_uv, (int, float)):
        raise ValueError('幅度门槛必须在 0 到 5000 微伏')
    threshold = float(threshold_uv)
    if threshold < 0 or threshold > 5000:
        raise ValueError('幅度门槛必须在 0 到 5000 微伏')
    if isinstance(sensitivity, bool) or not isinstance(sensitivity, (int, float)) or float(sensitivity) != int(sensitivity):
        raise ValueError('灵敏度必须是 1 到 10 的整数')
    level = int(sensitivity)
    if level < 1 or level > 10:
        raise ValueError('灵敏度必须是 1 到 10 的整数')
    effective = 0.0 if threshold == 0 else threshold * (11 - level) / 5
    return threshold, level, effective


def signal_facts(window, fs=FS, skip=()):
    """1 秒窗上的三块读数。基线是绝对值中位数，时域噪声是各路峰峰值的平均，频域噪声是 45–55 Hz 功率相对 20–450 Hz 的分贝。
    skip：已屏蔽的路（1–8），不算进读数，免得坏路的噪声抬高幅度门槛的读数。"""
    x = np.asarray(window, float)
    if x.ndim != 2 or x.shape[1] != 8 or len(x) < 32:
        raise ValueError('信号窗至少要有 32 点、8 路')
    x = x[:, [i for i in range(8) if i + 1 not in set(skip)]]
    baseline = float(np.median(np.abs(x)))
    vpp = float(np.mean(np.ptp(x, axis=0)))
    f, power = welch(x - x.mean(0), fs, nperseg=min(256, len(x)), axis=0)
    band = (f >= 20) & (f <= 450)
    mains = (f >= 45) & (f <= 55)
    broad = float(np.mean(power[band])) if np.any(band) else 0.0
    hum = float(np.mean(power[mains])) if np.any(mains) else 0.0
    noise_db = None if broad <= 0 else float(10 * np.log10((hum + 1e-18) / broad))
    return {'baseline_uv': round(baseline, 1), 'vpp_uv': round(vpp, 1), 'noise_db': None if noise_db is None else round(noise_db, 1)}


def min_prob_setting(value):
    """动作阈值（把握度）：0..0.99，0 表示不拦。唯理上位机的「动作阈值 70%」。"""
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= float(value) < 1:
        raise ValueError('动作阈值必须在 0% 到 99%')
    return round(float(value), 2)


def apply_recognition_gate(pred, facts, threshold_uv, sensitivity, min_prob=0.0, threshold_x=None, rest_ref=None):
    """峰峰值低于有效门槛（blocked），或最高那类概率低于 min_prob（unsure）时，把非放松的 top 改回放松。概率本身不改。门槛为 0 时不拦。
    threshold_x 给了就按倍数：门槛 = threshold_x × rest_ref（这个人的放松底噪，µV），绝对值 threshold_uv 不再起作用；
    模型没记放松底噪（rest_ref 为空）时倍数门槛不拦，gate.rest_ref_uv 为 None，页面据此提示重训。"""
    threshold, level, effective = gate_settings(threshold_uv, sensitivity)
    times = None if threshold_x is None else times_setting(threshold_x)
    if times is not None:
        effective = (times * float(rest_ref) if rest_ref else 0.0) * (11 - level) / 5
    floor = min_prob_setting(min_prob)
    rest = next((name for name in pred['probs'] if 'rest' in name), None)
    calm = pred['top'] == rest or pred['top'].endswith('_move')        # 随意动手本来就是「不触发」，和放松同一档，不进门槛
    blocked = effective > 0 and float(facts['vpp_uv']) < effective and rest is not None and not calm
    unsure = not blocked and floor > 0 and rest is not None and not calm and float(pred['probs'][pred['top']]) < floor
    out = dict(pred)
    if blocked or unsure:
        out['top'] = rest
    out['signal'] = facts
    out['gate'] = {'threshold_uv': threshold, 'sensitivity': level, 'effective_uv': round(effective, 1), 'blocked': blocked, 'min_prob': floor, 'unsure': unsure,
                   'threshold_x': times, 'rest_ref_uv': None if not rest_ref else round(float(rest_ref), 1)}
    return out


class LivePredictor:
    """实时识别：保留最近 1 s 的 8 路原始数据，每 100 ms 算一次特征和概率。"""
    def __init__(self, model_path, window_s=1.0, step_s=.1):
        z = np.load(model_path)
        self.m = self.full = dict(classes=[str(c) for c in z['classes']], mu=z['mu'], sinv=z['sinv']); self.W = z['W']; self.mask = []
        self.rest_ptp = np.asarray(z['rest_ptp'], float) if 'rest_ptp' in z.files else None   # 训练时放松窗每路峰峰值 (窗数, 8)
        self.rest_rms = (np.asarray(z['rest_rms'], float) if 'rest_rms' in z.files
                         else (np.median(self.rest_ptp, axis=0) / 6.0 if self.rest_ptp is not None else None))
        self.temp = float(z['temp']) if 'temp' in z.files else 1.0
        self.m['temp'] = self.full['temp'] = self.temp
        self.win, self.step, self.buf, self.since = int(window_s * FS), int(step_s * FS), np.zeros((0, 8)), 0

    def set_mask(self, lanes):
        """屏蔽坏路（1–8 的列表，空 = 不屏蔽）。只换模型，不清缓冲。"""
        self.mask = sorted({int(l) for l in lanes}); self.m = mask_model(self.full, self.mask)
        self.m['temp'] = getattr(self, 'temp', 1.0)

    def rest_ref(self):
        """没屏蔽的那几路放松底噪的平均（和 signal_facts(skip=mask) 的 vpp 同口径）；旧模型没记就是 None。"""
        if self.rest_ptp is None: return None
        keep = [i for i in range(8) if i + 1 not in self.mask]
        return float(np.median(self.rest_ptp[:, keep].mean(1))) if keep else None

    def reset(self):
        """配置变化后清掉整窗，重新积累，模型参数保留。"""
        self.buf = np.zeros((0, 8)); self.since = 0

    def push(self, emg):
        """喂一块 (n,8)；到点了就返回 {'probs': {类: 概率}, 'top': 类, 'xy': 投影坐标}，否则 None。"""
        self.buf = np.concatenate([self.buf, np.asarray(emg, float)])[-self.win:]; self.since += len(emg)
        if len(self.buf) < self.win or self.since < self.step: return None
        self.since = 0; x = features(self.buf)[None]
        _, p = scores(self.m, x); xy = (x @ self.W)[0]
        return dict(probs={c: round(float(v), 3) for c, v in zip(self.m['classes'], p[0])}, top=self.m['classes'][int(p[0].argmax())],
                    xy=[round(float(xy[0]), 3), round(float(xy[1]), 3)])


def check():
    import tempfile, wl8
    rng = np.random.default_rng(3)
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        def synth(label, n, split, gainmap):
            d = root / split / label; d.mkdir(parents=True, exist_ok=True)
            for i in range(n):
                g = gainmap[label] * rng.uniform(.8, 1.2, 8)
                e = rng.normal(0, 1, (4000, 8)) * g; np.savez(d / f'{label}-{i:03d}.npz', emg_uv=e.astype(np.float32))
        gains = dict(rest=np.full(8, 20.), pinch=np.array([20, 60, 70, 20, 20, 20, 20, 20.]), fist=np.array([50, 50, 150, 200, 120, 60, 40, 40.]))
        for l in DEFAULT_LABELS: synth(l, 12, 'emg-wl8-data', gains); synth(l, 6, 'emg-wl8-data-rewear', gains)
        events = []
        run, model = train(root, progress=events.append)
        assert run['rewear'] > .9 and run['same_wear'] > .9 and run['shuffled'] < .6, (run['rewear'], run['same_wear'], run['shuffled'])
        assert run['confusion']['rows'] == list(DEFAULT_LABELS) and sum(map(sum, run['confusion']['matrix'])) == 18
        assert run['learning_curve']['points'][-1]['mean'] >= run['learning_curve']['points'][0]['mean'] - .05
        assert len(run['projection']['train']) == 36 and len(run['projection']['centroids']) == 3 and len(run['per_channel']) == 8
        assert [e['stage'] for e in events][0] == 'data' and events[-1]['stage'] == 'done' and any(e['stage'] == 'curve' for e in events)
        d = save(run, model, root / 'models'); assert (d / 'run.json').exists() and (d / 'model.npz').exists()
        # 实时：放松的流判成 rest，握拳的流判成 fist
        lp = LivePredictor(d / 'model.npz'); outs = []
        # 放松底噪与留一温度进模型：合成放松每路 σ≈gains['rest']，1 秒峰峰值约 7σ；屏蔽一路后参考只取其余路
        assert len(run['rest_vpp_uv']) == 8 and lp.rest_ptp is not None and lp.rest_ref() > 0, run.get('rest_vpp_uv')
        assert lp.rest_rms is not None and len(lp.rest_rms) == 8 and lp.temp == run['temp'] and run['temp'] in TEMPERATURES
        assert 'noise_ratio' in run and len(run['noise_ratio']['ratio_pct']) == 8
        nr_ok = noise_ratio_summary(np.full((10, 8), 20.), np.full((10, 8), 300.))
        nr_bad = noise_ratio_summary(np.full((10, 8), 50.), np.full((10, 8), 200.))
        assert nr_ok['ok'] and nr_ok['pass_channels'] == 8 and not nr_bad['ok'] and nr_bad['pass_channels'] == 0
        lp.set_mask([1]); assert lp.rest_ref() == float(np.median(lp.rest_ptp[:, 1:].mean(1))) and lp.m.get('temp') == lp.temp; lp.set_mask([])
        # 同口径：放松流逐窗算的 vpp 中位，应和 rest_ref 很接近（之前先逐路中位再平均会差 ~20%）
        live_v = [signal_facts(rng.normal(0, 1, (FS, 8)) * gains['rest'])['vpp_uv'] for _ in range(30)]
        assert abs(np.median(live_v) / lp.rest_ref() - 1) < .1, (np.median(live_v), lp.rest_ref())
        for label in ('rest', 'fist'):
            for _ in range(15):
                r = lp.push(rng.normal(0, 1, (200, 8)) * gains[label])
                if r: outs.append((label, r['top']))
        assert sum(a == b for a, b in outs[-5:]) >= 4 and outs[0][1] == 'rest', outs
        # 屏蔽：删行列的子模型 = 不用这几路直接训练的模型（概率逐项相同）；只靠第 4 路区分的两类，屏蔽别的路不掉、屏蔽第 4 路就分不开
        X = rng.normal(0, 1, (60, 40)); y = np.repeat(['a', 'b', 'c'], 20); X[y == 'b', 3::8] += 3; X[y == 'c', 6::8] += 3
        k = lane_keep([4, 7])
        assert np.allclose(scores(mask_model(fit(X, y, 0), [4, 7]), X)[1], scores(fit(X[:, k], y, 0), X[:, k])[1])   # 不收缩时严格相等：行列删得对
        full = fit(X, y)   # 默认收缩：收缩目标按整体方差均值定，删路后略有差别，预测几乎一致
        assert np.mean(predict(mask_model(full, [4, 7]), X) == predict(fit(X[:, k], y), X[:, k])) >= .95
        Xt = rng.normal(0, 1, (60, 40)); Xt[y == 'b', 3::8] += 3; Xt[y == 'c', 6::8] += 3   # 另一组数据评分，免得 40 维在训练集上靠噪声硬分开
        assert bal(y, predict(mask_model(full, [2]), Xt)) > .9 and bal(y, predict(mask_model(full, [4]), Xt)) < .8
        # 温度校准：纯噪声高维 LDA 留一必然过拟合虚高，校准温度 T > 1 压低虚高把握度，且 argmax 100% 不变
        X_noisy = rng.normal(0, 1, (18, 40)); y_noisy = np.repeat(['a', 'b', 'c'], 6)
        t_noisy = calibrate_temperature(X_noisy, y_noisy)
        m_noisy = fit(X_noisy, y_noisy); p_raw = scores(m_noisy, Xt)[1]; p_cal = calibrated_probs(m_noisy, Xt, temp=t_noisy)
        assert t_noisy > 1.0 and np.array_equal(p_raw.argmax(1), p_cal.argmax(1)) and p_cal.max(1).mean() < p_raw.max(1).mean() - .15, (t_noisy, p_raw.max(1).mean(), p_cal.max(1).mean())
        assert len(run['lane_drop']) == 8 and all(0 <= v <= 1 for v in run['lane_drop'])
        lp.set_mask([3]); r = None
        for _ in range(10): r = lp.push(rng.normal(0, 1, (200, 8)) * gains['fist']) or r
        assert r['top'] == 'fist' and lp.mask == [3], r
        lp.set_mask([]); assert 'keep' not in lp.m
        quiet = signal_facts(rng.normal(0, 20, (FS, 8)))
        loud = signal_facts(rng.normal(0, 200, (FS, 8)))
        assert loud['vpp_uv'] > quiet['vpp_uv'] * 3 and quiet['baseline_uv'] < loud['baseline_uv'], (quiet, loud)
        one_bad = rng.normal(0, 20, (FS, 8)); one_bad[:, 2] *= 50   # 第 3 路坏：不屏蔽时抬高读数，屏蔽后回到安静水平
        assert signal_facts(one_bad)['vpp_uv'] > quiet['vpp_uv'] * 3 and signal_facts(one_bad, skip=[3])['vpp_uv'] < quiet['vpp_uv'] * 1.3
        assert gate_settings(1000, 10)[2] < 1000 < gate_settings(1000, 1)[2]
        fist = dict(probs={'rest': .1, 'fist': .9}, top='fist', xy=[0., 0.])
        held = apply_recognition_gate(fist, quiet, 5000, 1)
        assert held['top'] == 'rest' and held['gate']['blocked'] and held['probs']['fist'] == .9, held
        free = apply_recognition_gate(fist, loud, 0, 5)
        assert free['top'] == 'fist' and not free['gate']['blocked'], free
        # 把握度：最高类 0.9 过 0.7 不拦；0.6 低于 0.7 判回放松（unsure），概率不改
        assert apply_recognition_gate(fist, loud, 0, 5, .7)['top'] == 'fist'
        doubt = apply_recognition_gate(dict(fist, probs={'rest': .4, 'fist': .6}), loud, 0, 5, .7)
        assert doubt['top'] == 'rest' and doubt['gate']['unsure'] and not doubt['gate']['blocked'] and doubt['probs']['fist'] == .6, doubt
        # 倍数门槛：灵敏度 5 时有效门槛 = 倍数 × 底噪 × 1.2；没有底噪参考时不拦
        quiet_v, loud_v = quiet['vpp_uv'], loud['vpp_uv']
        assert apply_recognition_gate(fist, quiet, 0, 5, 0, threshold_x=3, rest_ref=quiet_v / 2)['gate']['blocked']        # 1/2 底噪 × 3 = 1.5 倍底噪 > 实际
        assert not apply_recognition_gate(fist, loud, 0, 5, 0, threshold_x=3, rest_ref=quiet_v)['gate']['blocked']        # 用力时远超 3 倍底噪
        free_x = apply_recognition_gate(fist, quiet, 5000, 1, 0, threshold_x=3, rest_ref=None)
        assert not free_x['gate']['blocked'] and free_x['gate']['rest_ref_uv'] is None and free_x['gate']['threshold_x'] == 3   # 倍数模式下绝对值不起作用
        for bad in (-1, 21, True, '2'):
            try: times_setting(bad)
            except ValueError: continue
            raise AssertionError(f'坏倍数没被拒绝 {bad!r}')
        move = dict(probs={'rest': .3, 'x_move': .5, 'fist': .2}, top='x_move', xy=[0., 0.])
        assert apply_recognition_gate(move, quiet, 5000, 1, .7)['top'] == 'x_move'      # 随意动手不被门槛改判
        for bad in (-.1, 1, True, '0.7'):
            try: min_prob_setting(bad)
            except ValueError: continue
            raise AssertionError(f'坏动作阈值没被拒绝 {bad!r}')
        for bad in ((-1, 5), (10, 0), (10, 5.5), (True, 5)):
            try:
                gate_settings(*bad)
            except ValueError:
                continue
            raise AssertionError(f'坏门槛没被拒绝 {bad}')
        # 必失败：标签全部打乱后，重戴准确率要掉到机会水平附近
        for split in ('emg-wl8-data', 'emg-wl8-data-rewear'):
            files = sorted((root / split).glob('*/*.npz')); labs = [f.parent.name for f in files]; rng.shuffle(labs)
            for f, l in zip(files, labs): f.rename(f.parent.parent / l / (f.stem + '-s.npz'))
        run2, _ = train(root, progress=lambda e: None)
        assert run2['rewear'] < .7, run2['rewear']
        # 没有重戴目录：4 次佩戴，每次佩戴各路增益整体漂移（电极位置变了），按佩戴编号留一次佩戴估计
        root3 = root / 'wears'
        for w in range(1, 5):
            shift = rng.uniform(.6, 1.6, 8)
            for l in DEFAULT_LABELS:
                d = root3 / 'emg-wl8-data' / l; d.mkdir(parents=True, exist_ok=True)
                for i in range(4):
                    f = d / f'{l}-w{w}-{i}.npz'; np.savez(f, emg_uv=(rng.normal(0, 1, (4000, 8)) * gains[l] * shift * rng.uniform(.9, 1.1, 8)).astype(np.float32))
                    f.with_suffix('.json').write_text(json.dumps({'donning': w}))
        for l in DEFAULT_LABELS:   # 没有佩戴编号的旧录音：只进训练，不进测试（混淆总数仍是 48）
            for i in range(3): np.savez(root3 / 'emg-wl8-data' / l / f'{l}-old-{i}.npz', emg_uv=(rng.normal(0, 1, (4000, 8)) * gains[l]).astype(np.float32))
        ev3 = []; run3, _ = train(root3, progress=ev3.append)
        assert run3['rewear_source'] == '留一次佩戴' and run3['rewear'] > .8 and run3['shuffled'] < .6, (run3['rewear'], run3['shuffled'])
        assert sum(map(sum, run3['confusion']['matrix'])) == 48 and len(run3['per_channel']) == 8 and '留一次佩戴' in run3['note']
        assert [e['source'] for e in ev3 if e['stage'] == 'rewear'] == ['留一次佩戴'] and run['rewear_source'] == '重戴目录'
        assert [e['source'] for e in events if e['stage'] == 'rewear'] == ['重戴目录']   # 进度事件带来源，页面据此写「重戴测试」或「留一次佩戴测试」
        # 必失败 1：留一次佩戴必须真按佩戴分组。每次佩戴的同类条几乎一样、不同佩戴差很远时，留一条（兄弟条在训练里）接近满分，留一次佩戴要明显更低
        root4 = root / 'twins'
        for w in range(1, 5):
            base = {l: rng.uniform(10, 200, 8) for l in DEFAULT_LABELS}   # 每次佩戴各类的样子都重新随机：跨佩戴学不到规律
            for l in DEFAULT_LABELS:
                d = root4 / 'emg-wl8-data' / l; d.mkdir(parents=True, exist_ok=True)
                for i in range(4):
                    f = d / f'{l}-w{w}-{i}.npz'; np.savez(f, emg_uv=(rng.normal(0, 1, (4000, 8)) * base[l]).astype(np.float32))
                    f.with_suffix('.json').write_text(json.dumps({'donning': w}))
        run4, _ = train(root4, progress=lambda e: None)
        assert run4['same_wear'] > .7 and run4['rewear'] < run4['same_wear'] - .3, (run4['same_wear'], run4['rewear'])
        # 单路准确率取对列：只有第 3 路能分三类、其余各路一样，第 3 路要接近满分、别的路接近瞎猜
        root6 = root / 'lane3'
        for w in (1, 2):
            for l, g3 in zip(DEFAULT_LABELS, (20, 100, 500)):
                d = root6 / 'emg-wl8-data' / l; d.mkdir(parents=True, exist_ok=True)
                g = np.full(8, 20.); g[2] = g3
                for i in range(4):
                    f = d / f'{l}-w{w}-{i}.npz'; np.savez(f, emg_uv=(rng.normal(0, 1, (4000, 8)) * g).astype(np.float32))
                    f.with_suffix('.json').write_text(json.dumps({'donning': w}))
        pc = train(root6, progress=lambda e: None)[0]['per_channel']
        assert pc[2] > .9 and max(pc[:2] + pc[3:]) < .7, pc
        # 必失败 2：只有一次佩戴时不能凭空给重戴分
        for f in root3.glob('*/*/*.json'): f.write_text(json.dumps({'donning': 1}))
        run5, _ = train(root3, progress=lambda e: None)
        assert run5['rewear'] is None and 'rewear_source' not in run5, run5.get('rewear')
    print(f"wl8_train check passed: 合成数据 同次 {run['same_wear']:.2f} / 重戴 {run['rewear']:.2f} / 打乱 {run['shuffled']:.2f}；学习曲线、投影、混淆、单路、进度事件、模型保存、实时识别；打乱标签后重戴 {run2['rewear']:.2f}（机会水平）；"
          f"无重戴目录留一次佩戴 {run3['rewear']:.2f}（打乱 {run3['shuffled']:.2f}）；佩戴间不可迁移时 留一条 {run4['same_wear']:.2f} / 留一次佩戴 {run4['rewear']:.2f}；单次佩戴不给分")


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--check', action='store_true'); ap.add_argument('--data'); ap.add_argument('--labels', default=','.join(DEFAULT_LABELS))
    ap.add_argument('--out'); a = ap.parse_args()
    if a.check: check()
    elif a.data:
        run, model = train(a.data, a.labels.split(','), progress=lambda e: print(json.dumps(e, ensure_ascii=False)))
        if a.out: print('saved', save(run, model, a.out))
        print(json.dumps({k: run[k] for k in ('counts', 'same_wear', 'rewear', 'shuffled', 'per_channel', 'confusion') if k in run}, ensure_ascii=False))
    else: print(__doc__)

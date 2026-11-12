"""Sharma (2025) 硬件与佩戴静息/发力峰谷噪声比（<= 10%）验收门与 9 次佩戴实测诊断。

依据 Sharma et al. (2025) Eq. (1)/(5)/(6)：当单通道静息噪声带宽度 NM（剔除 1%/99% 离群点后的峰谷差）
与发力峰峰值 MApp 之比 <= 10% 时，固定静息门槛与脉冲分段才成立。
本脚本提供：
1. check_noise_ratio(rest_uv, effort_uv, max_ratio=0.10)：逐通道计算 q99-q1 峰谷比、200 ms 窗中位峰谷比与 RMS 比；
2. --check：合成阳性对照（8/8 达标）与单通道松动/底噪超标阴性对照自检；
3. 对 emg-wl8-data 全部 9 次佩戴（222 条录制）做逐通道体检，并对比达标佩戴 vs 超标佩戴、同手 vs 混手的留出准确率。

用法：
    PYTHONPATH=host host/.venv-emg/bin/python -B host/check_noise_ratio_gate.py --check
    PYTHONPATH=host host/.venv-emg/bin/python -B host/check_noise_ratio_gate.py \
        ~/Library/Application\\ Support/原力手环/project/data/emg/emg-wl8-data \
        --out evidence/2026-10-25-noise-ratio-gate/report.json
"""
import argparse
import json
from pathlib import Path

import numpy as np

import device_desc as dd
import emg_model
import emg_threshold_ablation as ta
import gates

FS, WIN, STEP = ta.FS, ta.WIN, ta.STEP
LABELS, REST = ta.LABELS, ta.REST
MAX_RATIO_DEFAULT = 0.10


def p2p_q99_q1(x):
    """按论文 NM 口径（剔除两端 1% 离群值）计算每通道峰谷差。"""
    return np.percentile(x, 99, axis=0) - np.percentile(x, 1, axis=0)


def win_median_p2p(x):
    """按 200 ms 窗口计算每窗 (max - min) 的中位数。"""
    ws = ta.windows(x)
    if not ws:
        return x.max(axis=0) - x.min(axis=0)
    return np.median([w.max(axis=0) - w.min(axis=0) for w in ws], axis=0)


def check_noise_ratio(rest_uv, effort_uv, max_ratio=MAX_RATIO_DEFAULT, min_pass_channels=6):
    """逐通道核查静息/发力峰谷比是否 <= max_ratio（默认 10%）。"""
    rest = np.asarray(rest_uv, dtype=float)
    effort = np.asarray(effort_uv, dtype=float)
    assert rest.ndim == 2 and effort.ndim == 2 and rest.shape[1] == effort.shape[1]

    rest_nm = p2p_q99_q1(rest)
    eff_mapp = np.maximum(p2p_q99_q1(effort), 1e-9)
    ratio_q99 = rest_nm / eff_mapp

    rest_wp2p = win_median_p2p(rest)
    eff_wp2p = np.maximum(win_median_p2p(effort), 1e-9)
    ratio_win = rest_wp2p / eff_wp2p

    rest_rms = np.sqrt(np.mean((rest - rest.mean(axis=0)) ** 2, axis=0))
    eff_rms = np.maximum(np.sqrt(np.mean((effort - effort.mean(axis=0)) ** 2, axis=0)), 1e-9)
    ratio_rms = rest_rms / eff_rms

    ch_pass = ratio_q99 <= max_ratio
    n_pass = int(np.sum(ch_pass))
    failed_channels = [int(i + 1) for i, ok in enumerate(ch_pass) if not ok]

    return {
        'ok': bool(n_pass >= min_pass_channels),
        'strict_all_8_ok': bool(n_pass == rest.shape[1]),
        'pass_channels': n_pass,
        'total_channels': int(rest.shape[1]),
        'failed_channels_1based': failed_channels,
        'max_ratio_limit': float(max_ratio),
        'mean_ratio_q99_pct': round(float(np.mean(ratio_q99) * 100.0), 2),
        'max_ratio_q99_pct': round(float(np.max(ratio_q99) * 100.0), 2),
        'ratio_q99_pct': [round(float(v * 100.0), 2) for v in ratio_q99],
        'ratio_win_p2p_pct': [round(float(v * 100.0), 2) for v in ratio_win],
        'ratio_rms_pct': [round(float(v * 100.0), 2) for v in ratio_rms],
        'rest_nm_uv': [round(float(v), 2) for v in rest_nm],
        'effort_mapp_uv': [round(float(v), 2) for v in eff_mapp],
    }


def load_with_notes(folder):
    """加载录制并保留佩戴手别（左手/右手）与备注信息。"""
    recs = []
    for label in LABELS:
        for f in sorted((Path(folder) / label).glob('*.npz')):
            meta = json.loads(f.with_suffix('.json').read_text())
            z = np.load(f)
            assert int(z['emg_hz']) == FS, f
            notes = meta.get('session', meta.get('notes', ''))
            hand = 'right' if '右手' in notes else ('left' if '左手' in notes else 'unknown')
            recs.append({
                'file': f.name,
                'label': label,
                'group': int(meta['donning']),
                'at': meta['recordedAt'],
                'notes': notes,
                'hand': hand,
                'x': ta.clean(z['emg_uv'].astype(float)),
            })
    return recs


def evaluate_subset(ev_recs, cal_rest, groups_to_eval=None, same_hand_only=False):
    """在指定佩戴子集或同手训练集条件下评估 A（0.1×RMS 门槛）与 B（静息固定门槛 k=2）。"""
    cals = {g: ta.calibrate(r, 2.0) for g, r in cal_rest.items()}
    target_groups = sorted(cal_rest) if groups_to_eval is None else sorted(groups_to_eval)
    out = {}
    for arm_name, fixed in (('A_window_rms', False), ('B_rest_fixed_k2', True)):
        truth, pred = [], []
        per_fold = {}
        for g in target_groups:
            te = [r for r in ev_recs if r['group'] == g]
            hand_g = te[0]['hand']
            tr = [
                r for r in ev_recs
                if r['group'] != g and (not same_hand_only or r['hand'] == hand_g)
            ]

            def vecs(rs):
                X, y = [], []
                for r in rs:
                    cal = dict(cals[r['group']], **({'fixed': 1} if fixed else {}))
                    for w in ta.windows(r['x']):
                        X.append(ta.features(w, cal, False))
                        y.append(r['label'])
                return np.asarray(X), y

            Xtr, ytr = vecs(tr)
            Xte, yte = vecs(te)
            model = emg_model._fit_generic(Xtr, ytr)
            pte = emg_model.predict(model, Xte)
            truth.extend(yte)
            pred.extend(pte)
            per_fold[g] = ta.metrics(yte, pte)
        out[arm_name] = {
            **ta.metrics(truth, pred),
            'per_fold': per_fold,
        }
    return out


def analyze_folder(folder):
    recs = load_with_notes(folder)
    ev_recs, cal_rest = ta.split_calibration(recs)

    per_donning = {}
    compliant_groups = []
    non_compliant_groups = []

    for g in sorted(cal_rest):
        drecs = [r for r in recs if r['group'] == g]
        rest_cat = np.vstack([r['x'] for r in drecs if r['label'] == REST])
        eff_cat = np.vstack([r['x'] for r in drecs if r['label'] != REST])
        gate = check_noise_ratio(rest_cat, eff_cat, max_ratio=0.10, min_pass_channels=6)
        # 同时计算仅用首条校准放松 vs 首条发力的在线快速体检值
        first_eff = sorted([r for r in drecs if r['label'] != REST], key=lambda r: r['at'])[0]['x']
        quick_gate = check_noise_ratio(cal_rest[g], first_eff, max_ratio=0.10, min_pass_channels=6)

        per_donning[g] = {
            'donning': g,
            'recordings': len(drecs),
            'hand': drecs[0]['hand'],
            'notes': drecs[0]['notes'],
            'full_donning_gate': gate,
            'quick_calibration_gate': quick_gate,
        }
        if gate['ok']:
            compliant_groups.append(g)
        else:
            non_compliant_groups.append(g)

    all_9_mixed = evaluate_subset(ev_recs, cal_rest, None, same_hand_only=False)
    all_9_same_hand = evaluate_subset(ev_recs, cal_rest, None, same_hand_only=True)
    compliant_mixed = evaluate_subset(ev_recs, cal_rest, compliant_groups, same_hand_only=False)
    compliant_same_hand = evaluate_subset(ev_recs, cal_rest, compliant_groups, same_hand_only=True)
    non_compliant_mixed = evaluate_subset(ev_recs, cal_rest, non_compliant_groups, same_hand_only=False)

    # 配对比较：在达标佩戴 vs 未达标佩戴上，静息固定门槛(B)相对窗内RMS门槛(A)的折均差
    diff_compliant = [
        all_9_mixed['B_rest_fixed_k2']['per_fold'][g]['balanced']
        - all_9_mixed['A_window_rms']['per_fold'][g]['balanced']
        for g in compliant_groups
    ]
    diff_non_compliant = [
        all_9_mixed['B_rest_fixed_k2']['per_fold'][g]['balanced']
        - all_9_mixed['A_window_rms']['per_fold'][g]['balanced']
        for g in non_compliant_groups
    ]

    return {
        'total_recordings': len(recs),
        'eval_recordings': len(ev_recs),
        'compliant_donnings_ge6of8': compliant_groups,
        'strict_8of8_donnings': [g for g, d in per_donning.items() if d['full_donning_gate']['strict_all_8_ok']],
        'non_compliant_donnings': non_compliant_groups,
        'right_hand_donnings': [g for g, d in per_donning.items() if d['hand'] == 'right'],
        'left_hand_donnings': [g for g, d in per_donning.items() if d['hand'] == 'left'],
        'per_donning': per_donning,
        'ablation_summary': {
            'all_9_mixed_hand': {k: {m: v[m] for m in ('balanced', 'rest_false_trigger', 'seal_accuracy', 'seal_miss')} for k, v in all_9_mixed.items()},
            'all_9_same_hand': {k: {m: v[m] for m in ('balanced', 'rest_false_trigger', 'seal_accuracy', 'seal_miss')} for k, v in all_9_same_hand.items()},
            'compliant_donnings_only': {k: {m: v[m] for m in ('balanced', 'rest_false_trigger', 'seal_accuracy', 'seal_miss')} for k, v in compliant_mixed.items()},
            'compliant_donnings_same_hand': {k: {m: v[m] for m in ('balanced', 'rest_false_trigger', 'seal_accuracy', 'seal_miss')} for k, v in compliant_same_hand.items()},
            'non_compliant_donnings_only': {k: {m: v[m] for m in ('balanced', 'rest_false_trigger', 'seal_accuracy', 'seal_miss')} for k, v in non_compliant_mixed.items()},
            'b_minus_a_balanced_mean_on_compliant': round(float(np.mean(diff_compliant)), 4),
            'b_minus_a_balanced_mean_on_non_compliant': round(float(np.mean(diff_non_compliant)), 4),
        },
    }


def check():
    """合成阳性与阴性对照自检。"""
    rng = np.random.default_rng(42)
    # 1. 阳性对照：8 通道静息 RMS=2 uV，发力 RMS=40 uV -> 峰谷比约 5% <= 10%
    rest_clean = rng.normal(0.0, 2.0, (4000, 8))
    eff_clean = rng.normal(0.0, 40.0, (4000, 8))
    res_ok = check_noise_ratio(rest_clean, eff_clean, max_ratio=0.10, min_pass_channels=6)
    assert res_ok['ok'] and res_ok['strict_all_8_ok'] and res_ok['pass_channels'] == 8, res_ok

    # 2. 阴性对照：第 3、4、7 通道接触不良（静息噪声升至 12 uV，峰谷比 ~30% > 10%）
    rest_noisy = rest_clean.copy()
    rest_noisy[:, [2, 3, 6]] = rng.normal(0.0, 12.0, (4000, 3))
    res_bad = check_noise_ratio(rest_noisy, eff_clean, max_ratio=0.10, min_pass_channels=6)
    assert not res_bad['ok'] and not res_bad['strict_all_8_ok'], res_bad
    assert res_bad['pass_channels'] == 5, res_bad
    assert res_bad['failed_channels_1based'] == [3, 4, 7], res_bad

    # 3. 验证 host/gates.py 的 check_noise_ratio 与 check(..., rest_uv=...) 集成
    desc = dd.load('fake')
    # 构造 20-450 Hz 肌电带信号使 SMR 门禁通过
    t = np.arange(4000)[:, None] / FS
    carrier = np.sin(2 * np.pi * 80.0 * t) + 0.5 * np.cos(2 * np.pi * 140.0 * t)
    eff_band = carrier * 40.0 + rng.normal(0.0, 2.0, (4000, 8))
    rest_band_ok = rng.normal(0.0, 1.5, (4000, 8))
    rest_band_bad = rest_band_ok.copy()
    rest_band_bad[:, [1, 4, 7]] = carrier[:, [0, 0, 0]] * 15.0
    g_ok = gates.check(desc, eff_band, seconds=2.0, rest_uv=rest_band_ok)
    assert g_ok['ok'] and g_ok['noise_ratio']['pass_channels'] == 8, g_ok
    g_bad = gates.check(desc, eff_band, seconds=2.0, rest_uv=rest_band_bad)
    assert not g_bad['ok'] and g_bad['noise_ratio']['failed_channels_1based'] == [2, 5, 8], g_bad
    assert '静息/发力峰谷比超标' in g_bad['why'], g_bad

    print(
        f"check: 阳性对照 pass={res_ok['pass_channels']}/8 (mean={res_ok['mean_ratio_q99_pct']}%)；"
        f"阴性对照 pass={res_bad['pass_channels']}/8 精确检出故障通道 {res_bad['failed_channels_1based']}；"
        f"gates.check(rest_uv=...) 联动通过"
    )


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('folder', nargs='?')
    p.add_argument('--check', action='store_true')
    p.add_argument('--out')
    args = p.parse_args()
    if args.check or not args.folder:
        check()
    else:
        report = analyze_folder(args.folder)
        for g, d in report['per_donning'].items():
            fg = d['full_donning_gate']
            print(
                f"Donning {g} ({d['hand']:5s}, {d['recordings']:2d} 条): "
                f"达标通道 {fg['pass_channels']}/8 | 均值 {fg['mean_ratio_q99_pct']:5.1f}% | "
                f"各路% {fg['ratio_q99_pct']} | 判定={'✓通过' if fg['ok'] else '✗超标'}"
            )
        ab = report['ablation_summary']
        print('汇总对比:', json.dumps(ab, ensure_ascii=False, indent=2))
        if args.out:
            out_path = Path(args.out)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2))

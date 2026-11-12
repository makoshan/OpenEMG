"""唯理腕带陀螺漂移 + 指向姿态重复性 → 对准角度窗（BLE_POINT_LIGHT_PLAN 3.5 节）。

  python3 wl8_gyro_drift.py record still 60      # 腕带戴好、手臂放桌上不动 60 s
  python3 wl8_gyro_drift.py record aim 40        # 指向灯保持 2 s、放下 2 s，重复 ≥5 次
  python3 wl8_gyro_drift.py analyze emg-wl8-raw/still-*.npz emg-wl8-raw/aim-*.npz
  python3 wl8_gyro_drift.py --check              # 合成数据自检

对准量 = 重力向量与标定向量的夹角（不依赖板子朝向）；偏航 = 去零偏陀螺积分（只用来看漂移）。
"""
import sys, glob, json, time
from pathlib import Path
import numpy as np

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import wl8

IMU_HZ = 222.0                      # 2026-09-29 实测 222.1 Hz
STILL_DPS, HOLD_S = 5.0, 0.5        # 静止判定：三轴陀螺模 < 5 °/s 持续 0.5 s（同 compass-turn 死区）
RAISED_DEG = 30.0                   # 与「放下」姿态的重力夹角 > 30° 才算抬手


def load(path):
    d = np.load(path)
    imu = d['imu'].astype(np.float64)
    return np.degrees(imu[:, :3] * float(d['gyro_scale'])), imu[:, 3:] * float(d['acc_scale'])   # °/s, m/s²


def angle(a, b):
    a, b = a / np.linalg.norm(a, axis=-1, keepdims=True), b / np.linalg.norm(b)
    return np.degrees(np.arccos(np.clip(a @ b, -1, 1)))


def still_mask(gyro, bias=0.0):
    n = int(HOLD_S * IMU_HZ)
    quiet = np.linalg.norm(gyro - bias, axis=1) < STILL_DPS
    m = np.zeros_like(quiet)
    run = 0
    for i, q in enumerate(quiet):
        run = run + 1 if q else 0
        if run >= n:
            m[i - n + 1:i + 1] = True
    return m


def analyze_still(gyro, acc):
    half = len(gyro) // 2
    bias = gyro[:half].mean(0)                                     # 前半段定零偏，后半段看剩余漂移
    t = np.arange(len(gyro)) / IMU_HZ
    yaw_raw = np.cumsum(gyro, 0) / IMU_HZ                          # 不去零偏：每轴每分钟漂多少
    yaw_fix = np.cumsum(gyro[half:] - bias, 0) / IMU_HZ            # 去零偏后剩下的（后半段）
    g_ref = acc.mean(0)
    return dict(seconds=round(t[-1], 1), bias_dps=bias.round(3).tolist(), noise_dps=gyro.std(0).round(3).tolist(),
                drift_raw_deg_per_min=(yaw_raw[-1] / t[-1] * 60).round(2).tolist(),
                drift_fixed_deg_per_min=(yaw_fix[-1] / (t[-1] - t[half]) * 60).round(2).tolist(),
                walk_5s_deg=np.abs(yaw_fix[int(5 * IMU_HZ)] if len(yaw_fix) > 5 * IMU_HZ else yaw_fix[-1]).round(2).tolist(),
                gravity_noise_deg=round(float(angle(acc, g_ref).std()), 3), g_mag=round(float(np.linalg.norm(g_ref)), 2))


def analyze_aim(gyro, acc, bias):
    m = still_mask(gyro, np.array(bias))
    # 录制从「放下」开始，所以第一段静止就是放下姿态；其余静止段按与它的夹角分两簇
    d = np.diff(np.r_[0, m.astype(int), 0])
    segs = list(zip(np.flatnonzero(d == 1), np.flatnonzero(d == -1)))     # [start, end) 静止段
    means = np.array([acc[a:b].mean(0) for a, b in segs]) if segs else np.zeros((0, 3))
    if len(means) < 2:
        return dict(error='静止段不足 2 段：录制要从放下开始，指向时停够 %.1f s' % HOLD_S)
    rest = means[angle(means, means[0]) < RAISED_DEG].mean(0)
    raised = means[angle(means, rest) > RAISED_DEG]
    if len(raised) < 3:
        return dict(error=f'抬手静止段只有 {len(raised)} 段（需 ≥3）；每次指向要停够 {HOLD_S} s，且抬起 >{RAISED_DEG}°')
    ref = raised.mean(0)
    spread = angle(raised, ref)
    window = float(max(10.0, np.ceil(3 * spread.std() + spread.max())))
    return dict(holds=len(raised), hold_spread_deg=spread.round(1).tolist(), ref_acc=ref.round(2).tolist(),
                pitch_window_deg=window, note='角度窗 = max(10°, 3σ + 最大偏差)，向上取整')


def analyze(still_path, aim_path=None):
    g, a = load(still_path)
    out = dict(still=analyze_still(g, a))
    if aim_path:
        g2, a2 = load(aim_path)
        out['aim'] = analyze_aim(g2, a2, out['still']['bias_dps'])
    return out


def synth(seed=0):
    rng = np.random.default_rng(seed)
    n = int(60 * IMU_HZ)
    g_still = rng.normal([0.3, -0.2, 0.1], 0.4, (n, 3))                   # °/s，含零偏
    a_still = rng.normal([0, -2.3, 8.7], 0.05, (n, 3))
    g_aim, a_aim = [], []
    for k in range(6):                                                    # 放下 2 s → 抬手 2 s（每次姿态差 ±4°）
        g_aim += [rng.normal(0, 0.4, (int(2 * IMU_HZ), 3)), rng.normal(0, 40, (int(.3 * IMU_HZ), 3)), rng.normal(0, 0.4, (int(2 * IMU_HZ), 3)), rng.normal(0, 40, (int(.3 * IMU_HZ), 3))]
        th = np.radians(60 + rng.normal(0, 4))
        a_aim += [rng.normal([0, -2.3, 8.7], 0.05, (int(2 * IMU_HZ), 3)), rng.normal(0, 3, (int(.3 * IMU_HZ), 3)),
                  rng.normal([9.8 * np.sin(th), -2.3 * np.cos(th), 8.7 * np.cos(th)], 0.05, (int(2 * IMU_HZ), 3)), rng.normal(0, 3, (int(.3 * IMU_HZ), 3))]
    return (g_still, a_still), (np.vstack(g_aim), np.vstack(a_aim))


def check():
    (gs, as_), (ga, aa) = synth()
    s = analyze_still(gs, as_)
    assert all(abs(b - t) < 0.05 for b, t in zip(s['bias_dps'], [0.3, -0.2, 0.1])), s
    assert abs(s['drift_raw_deg_per_min'][0] - 18) < 3, s               # 0.3 °/s × 60
    assert all(abs(d) < 3 for d in s['drift_fixed_deg_per_min']), s
    assert abs(s['drift_fixed_deg_per_min'][0]) < abs(s['drift_raw_deg_per_min'][0]) / 5, s
    r = analyze_aim(ga, aa, s['bias_dps'])
    assert 'error' not in r and r['holds'] == 6, r
    assert 10 <= r['pitch_window_deg'] <= 30 and max(r['hold_spread_deg']) > 1, r   # ±4° 的合成抖动必须被看见
    bad = analyze_aim(ga[:int(3 * IMU_HZ)], aa[:int(3 * IMU_HZ)], s['bias_dps'])
    assert 'error' in bad, bad                                          # 抬手段不够必须报错
    print('wl8_gyro_drift check ok', json.dumps(r, ensure_ascii=False))


if __name__ == '__main__':
    args = sys.argv[1:]
    if args == ['--check']:
        check()
    elif args[:1] == ['record'] and len(args) == 3:
        label, seconds = args[1], float(args[2])
        print(f'录 {label} {seconds:.0f} s：' + ('手臂放桌上不动' if label == 'still' else '指向灯停 2 s、放下 2 s，重复 ≥5 次'), flush=True)
        stem, report = wl8.record(seconds, out=HERE / 'emg-wl8-raw', label=label)
        new = stem.with_name(f'{label}-{stem.name}')
        for suf in ('.npz', '.json'):
            stem.with_suffix(suf).rename(new.with_suffix(suf))
        print(new.with_suffix('.npz'), json.dumps({k: report[k] for k in ('imu_frames', 'imu_hz', 'dropped')}))
    elif args[:1] == ['analyze'] and len(args) in (2, 3):
        print(json.dumps(analyze(*args[1:]), ensure_ascii=False, indent=1))
    else:
        print(__doc__)

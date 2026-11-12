"""统计 / EMG 分析插件门禁（附录 G）：合成 5 段激活必报 5 段；纯噪声报 0 段；MVC 归一百分比合理；
CSV 行数 = 激活数；统计量与 numpy 直接算一致；空数据 / 不足 1 s 必失败。"""
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from plugins import emg_analysis, stats


def main():
    fs = 2000
    x = emg_analysis.synthetic(fs, 10, n_bursts=5, seed=0)
    r = emg_analysis.analyze(x, fs, {'threshold_pct': 20})
    c = r['channels'][0]
    assert c['n_activations'] == 5, c['n_activations']
    durs = [a['duration_ms'] for a in c['activations']]
    assert all(700 < d < 1400 for d in durs), durs
    assert all(a['median_Hz'] > 100 for a in c['activations']), [a['median_Hz'] for a in c['activations']]
    starts = [a['start_s'] for a in c['activations']]
    assert np.allclose(np.diff(starts), 2.0, atol=.15), starts
    print(f'  5 段爆发 → {c["n_activations"]} 段，持续 {durs} ms，间隔≈2 s，中值频率 {[a["median_Hz"] for a in c["activations"]]}')
    csv = emg_analysis.to_csv(r)
    assert csv.count('\n') == 6, csv
    # MVC 归一：给定 MVC = 2×峰值 → 峰值百分比 ≈ 50%
    r2 = emg_analysis.analyze(x, fs, {'threshold_pct': 10}, mvc_uv=[c['mvc_uv'] * 2])
    pct = [a['peak_pct_mvc'] for a in r2['channels'][0]['activations']]
    assert all(30 < p <= 50.5 for p in pct), pct
    print(f'  MVC 归一：峰值 %MVC = {pct}')
    # 纯噪声 0 段（阈值取噪声包络最大值的 20% 会切出碎段——所以必须给 MVC）
    noise = emg_analysis.synthetic(fs, 5, n_bursts=0, seed=1)
    r3 = emg_analysis.analyze(noise, fs, {'threshold_pct': 20}, mvc_uv=[c['mvc_uv']])
    assert r3['channels'][0]['n_activations'] == 0, r3['channels'][0]['n_activations']
    print('  纯噪声（给定 MVC）→ 0 段')
    # 多路
    x8 = np.hstack([x, noise[:len(x)] if len(noise) >= len(x) else np.vstack([noise, noise])[:len(x)]])
    r4 = emg_analysis.analyze(x8, fs, mvc_uv=[c['mvc_uv'], c['mvc_uv']], labels=['A', 'B'])
    assert [ch['n_activations'] for ch in r4['channels']] == [5, 0] and r4['channels'][1]['label'] == 'B'
    # 统计
    s = stats.compute(x8, fs, labels=['A', 'B'])
    assert s['n'] == len(x8) and s['seconds'] == 10.0
    assert abs(s['channels'][0]['rms'] - float(np.sqrt((x[:, 0] ** 2).mean()))) < 1e-3
    assert s['channels'][0]['p2p'] == round(float(x.max() - x.min()), 4) and sum(s['channels'][0]['histogram']['counts']) == len(x)
    print(f'  stats: rms={s["channels"][0]["rms"]} p2p={s["channels"][0]["p2p"]} 直方图 {len(s["channels"][0]["histogram"]["counts"])} 桶')
    # 必失败
    for fn, arg, why in ((stats.compute, np.zeros((0, 1)), '空数据'), (lambda a: emg_analysis.analyze(a, fs), np.zeros((500, 1)), '不足 1 s')):
        try:
            fn(arg)
            raise AssertionError(f'{why} 通过了')
        except ValueError as e:
            print(f'  红 ✓ {why}: {e}')
    print('check_plugin_emg: 5 段激活 / MVC / 0 段 / 多路 / 统计 通过，2 条必失败全红')


if __name__ == '__main__':
    main()

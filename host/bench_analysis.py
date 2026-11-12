"""台架分析库：每路统计、频带 RMS、FFT 指标（SNR/THD/SFDR/ENOB）、CMRR、相干频率。

口径参照 TI ADS1298ECGFE 上位机（SNR_Analysis.vi、dB_reference.vi、Calc_CMRR.vi；只读到控件名和常量，
连线没还原， F7）：
- 功率谱：加窗后的单边谱，按 N·Σw² 归一化。一个正弦泄漏到的几个 bin 加起来正好是 A²/2，
  白噪声全谱加起来是 σ²（Parseval）。
- 基波、谐波、最大杂散都按 ±12 个 bin（SPREAD）求和算能量，口径一致。
- 噪声：频带 [lo, hi) 里去掉直流、基波、谐波的泄漏 bin，剩下的取每 bin 平均功率，
  再乘以频带内的 bin 总数（被去掉的 bin 按平均值补）。
- 谐波折叠后叠在直流、基波上或贴着奈奎斯特的，分不开，记 None、不计入 THD；
  几次谐波互相叠在一起的，能量只算一次，单项记 None。
- 纯噪声的频带 RMS（band_rms）用 Welch：2 s Hann、50% 重叠、每段去均值，和 docs/c08b-low-noise-validation-20261106/analyze.py
  同一口径。单次 FFT 没有平均，窄带抖动大：Spark 合成扫描（evidence/2026-11-09-bench-analysis-sweep/）里 60 s 白噪声、
  49–51 Hz，单次 FFT ±0.64 dB（1σ），Welch ±0.36 dB；20–500 Hz 两者都在 ±0.05 dB 内。
- fft_metrics 只用四项 Blackman-Harris 窗。hann、boxcar 要信号源和 ADC 时钟锁在一起（真相干）才准：非相干误差 2–100 dB，
  信号源偏几十 ppm（0.02 bin）就能错零点几 dB，我们的台架做不到，所以不提供。有效范围（同一扫描）：SNR ≤ 80 dB 误差
  ≤ 0.31 dB（2048 点）、≤ 0.03 dB（≥ 32768 点）；SNR 100 dB 时到 0.1–4.2 dB。
- 0 dB 参考 = 满幅正弦，峰值 = VREF/增益，折算到输入端；用 ads1298_regs.full_scale_uv 从寄存器快照取，
  不写死 4 V（C08B 指南用 2.4 V）。
- CMRR：20·log10(注入共模峰值 / 输出端折算到输入的差分峰值)。幅度用最小二乘拟合。片内振荡器有 ±2% 误差，
  这时凑整周期不成立，用 search 在名义频率附近找；fs 最好用帧时间戳实测后传进来。
  注入频率别选 50 Hz 及其谐波：会和工频混在一起分不开。另录一段不注入的基线传给 baseline，结果里一并给出。

输入一律是一路一维数组，单位 µV（输入端）。只算数：不读文件、不连设备、不判通过与否。
计划 S2。
用法：python bench_analysis.py --check（要 numpy、scipy；本机用 host/.venv-emg/bin/python，系统 python3 没装 scipy）
"""
import math
import sys

import numpy as np
from scipy.signal import get_window, welch

# spectrum() 支持的窗，以及 fft_metrics 在基波两侧各剔几个 bin（fft_metrics 只用 blackmanharris）。
# 四项 Blackman-Harris 主瓣 ±4 bin、旁瓣 −92 dB。合成实测（非相干 50.3 Hz、32768 点）：SNR 67 dB 时 ±5 bin
# 已准（误差 0.01 dB）；SNR 87 dB 时 ±5 bin 低估 0.49 dB，±12 bin 误差 0.04 dB，所以取 12。
# hann、boxcar 只留给 spectrum() 做对照（boxcar 全谱相加精确等于方差）。
SPREAD = {'blackmanharris': 12, 'hann': 3, 'boxcar': 0}


def _x(x):
    x = np.asarray(x, dtype=np.float64)
    if x.ndim != 1 or x.size < 16:
        raise ValueError('要一路一维数据，至少 16 点')
    if not np.all(np.isfinite(x)):
        raise ValueError('数据里有 NaN 或 Inf')
    return x


def stats(x):
    """每路统计：均值、交流 RMS（= 标准差）、含直流 RMS、最小、最大、峰峰值。"""
    x = _x(x)
    lo, hi = float(x.min()), float(x.max())
    return {'n': int(x.size), 'mean': float(x.mean()), 'rms_ac': float(x.std()),
            'rms_total': float(np.sqrt(np.mean(x * x))), 'min': lo, 'max': hi, 'vpp': hi - lo}


def code_histogram(codes):
    """ADC 码值直方图：(出现过的码值, 次数)。"""
    return np.unique(np.asarray(codes, dtype=np.int64), return_counts=True)


def spectrum(x, fs, window='blackmanharris'):
    """单边功率谱 (P, f)，单位 µV²/bin。先去均值再加窗。"""
    x = _x(x)
    if window not in SPREAD:
        raise ValueError(f'窗函数只支持 {sorted(SPREAD)}')
    n = x.size
    w = get_window(window, n)                       # 周期型窗，做频谱用
    p = np.abs(np.fft.rfft((x - x.mean()) * w)) ** 2 / (n * np.sum(w * w))
    p[1:(n + 1) // 2] *= 2                         # 单边：除直流和（偶数点时的）奈奎斯特，其余翻倍
    return p, np.fft.rfftfreq(n, 1 / fs)


def _band(fs, lo, hi):
    hi = fs / 2 if hi is None else hi
    if not 0 <= lo < hi <= fs / 2:
        raise ValueError(f'频带要满足 0 ≤ lo < hi ≤ fs/2，实际 [{lo}, {hi})')
    return lo, hi


def band_rms(x, fs, lo, hi, seg_s=2.0):
    """频带 [lo, hi) 的 RMS（µV），给短路噪声这类没有单音的记录用。Welch：seg_s 秒一段、Hann、50% 重叠、每段去均值。"""
    x = _x(x)
    lo, hi = _band(fs, lo, hi)
    seg = int(round(seg_s * fs))
    if x.size < seg:
        raise ValueError(f'记录 {x.size} 点不到一段 {seg_s} s（{seg} 点）：只有一段时偏低，n=100 低 2.7%')
    f, p = welch(x, fs, window='hann', nperseg=seg, noverlap=seg // 2, detrend='constant')
    sel = (f >= lo) & (f < hi)
    if sel.sum() < 2:
        raise ValueError(f'频带 [{lo}, {hi}) 里不到 2 个 bin（分辨率 {f[1] - f[0]:g} Hz），放宽频带或加长 seg_s')
    return float(np.sqrt(p[sel].sum() * (f[1] - f[0])))


def fft_metrics(x, fs, full_scale, f0=None, lo=0.0, hi=None, n_harm=5):
    """单音记录的 FFT 指标（Blackman-Harris 窗）。full_scale 是满幅正弦峰值（µV，输入端）。

    f0 不给就取直流外最大的 bin；给了就在名义频率 ±12 个 bin 里找峰，峰落在这个范围边上说明名义频率不对
    （比如片内振荡器偏 2% 又没用实测 fs），直接报错。
    """
    x = _x(x)
    lo, hi = _band(fs, lo, hi)
    if full_scale <= 0:
        raise ValueError('full_scale 要大于 0')
    p, f = spectrum(x, fs, 'blackmanharris')
    n, m = x.size, p.size
    s = SPREAD['blackmanharris']                     # 主瓣 ±4 bin，剔 ±12（见 SPREAD 注释），不让调用方改
    if f0 is None:
        k0 = int(np.argmax(p[s + 1:])) + s + 1
    else:
        k = int(round(f0 * n / fs))
        if k <= s or k >= m:
            raise ValueError(f'f0={f0} Hz 落在直流泄漏区或超出奈奎斯特')
        win = slice(max(k - s, s + 1), min(k + s + 1, m))  # 名义频率附近找真峰
        k0 = win.start + int(np.argmax(p[win]))
        if k0 in (win.start, win.stop - 1):
            raise ValueError(f'名义 f0={f0} Hz 附近 ±{s} 个 bin 里没找到峰：采样率不准时先用帧时间戳实测 fs')
    if k0 <= 2 * s or k0 >= m - 1 - 2 * s:
        raise ValueError('基波离直流或奈奎斯特太近，泄漏会折回、分不开')
    excl = np.zeros(m, bool)
    excl[:s + 1] = True                              # 直流泄漏
    excl[k0 - s:k0 + s + 1] = True
    ps = float(p[k0 - s:k0 + s + 1].sum())
    # 谐波：先折叠到第一奈奎斯特区，再分组（互相叠住的并成一组，能量只算一次）
    harm_db = [None] * (n_harm - 1)
    groups = []                                      # [[谐波次数...], 中心 bin...]
    for h in range(2, n_harm + 1):
        kh = (h * k0) % n
        kh = n - kh if kh > n // 2 else kh
        if kh <= 2 * s or abs(kh - k0) <= 2 * s or kh + s >= m:
            excl[max(kh - s, 0):kh + s + 1] = True   # 叠在直流/基波上或贴着奈奎斯特：分不开，不计
            continue
        for g in groups:
            if any(abs(kh - kj) <= 2 * s for kj in g[1]):
                g[0].append(h); g[1].append(kh)
                break
        else:
            groups.append([[h], [kh]])
    energies, in_band = [], []
    for hs, ks in groups:
        mask = np.zeros(m, bool)
        for kh in ks:
            mask[kh - s:kh + s + 1] = True
        e = float(p[mask & ~excl].sum())             # 不和基波、直流、前面的组重复算
        excl |= mask
        energies.append(e)
        in_band.append(e if any(lo <= kh * fs / n < hi for kh in ks) else 0.0)
        if len(hs) == 1:
            harm_db[hs[0] - 2] = e
    band = (f >= lo) & (f < hi)
    noise = band & ~excl
    if noise.sum() < 8:
        raise ValueError('频带里剔完泄漏 bin 后剩不到 8 个，加长记录或放宽频带')
    pn = float(p[noise].mean() * band.sum())         # 被剔掉的 bin 按平均噪声补上
    ph = float(sum(energies))
    # SFDR 只看频带 [lo, hi) 内：频带内的谐波组，加上频带内没剔掉的 bin 里最高的一点（同样按 ±s 求和，只加没剔掉的 bin）
    rest = np.flatnonzero(noise)
    j = int(rest[np.argmax(p[rest])])
    lo_j, hi_j = max(j - s, 0), min(j + s + 1, m)
    spur = max(in_band + [float(p[lo_j:hi_j][noise[lo_j:hi_j]].sum())])   # 只加频带内、没剔掉的 bin
    pfs = full_scale ** 2 / 2
    db = lambda a, b: 10 * math.log10(a / b) if a > 0 and b > 0 else float('-inf')
    return {
        'f0_hz': k0 * fs / n, 'amplitude': math.sqrt(2 * ps), 'noise_rms': math.sqrt(pn),
        'snr_dbc': db(ps, pn), 'snr_dbfs': db(pfs, pn), 'thd_dbc': db(ph, ps),
        'sinad_dbc': db(ps, pn + ph), 'sfdr_dbc': db(ps, spur),
        'enob': (db(pfs, pn + ph) - 1.76) / 6.02,
        'harmonics_dbc': [None if e is None else db(e, ps) for e in harm_db],
        'band_hz': [lo, hi], 'window': 'blackmanharris', 'spread': s, 'n': int(n), 'fs': fs,
    }


def tone_amplitude(x, fs, f0, search=0.0):
    """最小二乘拟合 a·cos + b·sin + c，返回 (峰值幅度, 用的频率)。

    search > 0 时在 f0·(1 ± search) 里找幅度最大的频率：先粗扫 201 点，再在最好点两侧细扫。
    用于片内振荡器（手册 0–70°C ±2%）导致的实际采样率偏差。
    """
    x = _x(x)
    t = np.arange(x.size) / fs

    def amp(fr):
        a = np.column_stack([np.cos(2 * np.pi * fr * t), np.sin(2 * np.pi * fr * t), np.ones_like(t)])
        c = np.linalg.lstsq(a, x, rcond=None)[0]
        return math.hypot(c[0], c[1])

    if not search:
        return amp(f0), f0
    grid = np.linspace(f0 * (1 - search), f0 * (1 + search), 201)
    best = grid[int(np.argmax([amp(g) for g in grid]))]
    step = grid[1] - grid[0]
    fine = np.linspace(best - step, best + step, 41)
    best = fine[int(np.argmax([amp(g) for g in fine]))]
    return amp(best), float(best)


def cmrr_db(inject_vpp, x, fs, f0, search=0.0, baseline=None):
    """CMRR（dB）。inject_vpp：注入的共模峰峰值（µV，人填，不猜）；x：同一通道输入端 µV。

    baseline：同一通道、同样接法但不注入时录的一段。给了就在同一频率拟合它的幅度，
    结果里给出基线相对测量值的 dB；基线不比测量值低很多（比如工频串进来），这次 CMRR 就不可信。
    """
    if inject_vpp <= 0:
        raise ValueError('注入峰峰值要大于 0')
    a, fr = tone_amplitude(x, fs, f0, search)
    out = {'cmrr_db': 20 * math.log10((inject_vpp / 2) / a), 'amplitude': a, 'f_used': fr,
           'method': 'lstsq' + (f'+search±{search:g}' if search else '')}
    if baseline is not None:
        b = tone_amplitude(baseline, fs, fr)[0]
        out['baseline_amplitude'] = b
        out['baseline_db'] = 20 * math.log10(b / a) if b > 0 else float('-inf')
    return out


def coherent_freq(fs, n, f_want):
    """离 f_want 最近、在 n 点里的周期数 k 与 n 互质的频率（TI 上位机的相干频率计算器）。

    n 是 2 的幂时互质就是奇数。结果严格低于奈奎斯特。
    """
    c = f_want * n / fs
    ks = [k for k in range(1, (n - 1) // 2 + 1) if math.gcd(k, n) == 1]
    if not ks:
        raise ValueError('n 太小，找不到合适的周期数')
    k = min(ks, key=lambda k: (abs(k - c), k))
    return k * fs / n


def _selfcheck():
    import ads1298_regs as regs
    rng = np.random.default_rng(20261109)
    # 相干频率：TI 上位机常量 49.98779296875、100.006103515625 Hz（Format_CMRR_BW.vi）
    assert coherent_freq(500, 8192, 50) == 49.98779296875
    assert coherent_freq(2000, 32768, 50) == 49.98779296875
    assert coherent_freq(500, 16384, 100) == 100.006103515625
    assert coherent_freq(2000, 1000, 10) == 6.0        # k=5 与 1000 不互质，取最近的 3（与 7 同距取小）
    assert coherent_freq(2000, 1000, 1000) == 998.0    # 不越过奈奎斯特
    assert coherent_freq(2000, 1000, 0.1) == 2.0
    # 统计
    st = stats([1.0, -1.0, 3.0, -3.0] * 4)
    assert st['mean'] == 0 and st['vpp'] == 6 and abs(st['rms_ac'] - math.sqrt(5)) < 1e-12
    v, c = code_histogram([3, 1, 3, 3])
    assert v.tolist() == [1, 3] and c.tolist() == [1, 3]
    # 能量守恒：全在奈奎斯特的 ±1 交替信号，偶数点时奈奎斯特 bin 不翻倍
    pq, _ = spectrum(np.tile([1.0, -1.0], 32), 2000.0, 'boxcar')
    assert abs(pq.sum() - 1) < 1e-12 and abs(pq[-1] - 1) < 1e-12, pq.sum()
    # 频带 RMS：白噪声，20–500 Hz 应为 σ·√(480/1000)；带直流偏置也不影响（先去均值）
    fs, n = 2000.0, 65536
    w = rng.normal(0, 2.0, n)
    br = band_rms(w, fs, 20, 500)
    assert abs(br / (w.std() * math.sqrt(480 / 1000)) - 1) < 0.02, br
    assert abs(band_rms(w, fs, 0, 1000) / w.std() - 1) < 0.01
    assert abs(band_rms(w + 1e4, fs, 0, 1000) / w.std() - 1) < 0.01
    # 单音 + 白噪声。理论值用实际加进去的那段噪声、同一个窗算出的全带功率（spectrum 全加），
    # 这样只考剔除和补齐的逻辑，窗带来的估计抖动（BH 约 1%）两边抵消；归一化另有下面和 w.std() 的比较兜着。
    n = 32768
    f0 = coherent_freq(fs, n, 50)
    t = np.arange(n) / fs
    fsc = regs.full_scale_uv(regs._table(r01=0x84, r03=0xE0), 1)       # 4 V、增益 6 → 666666.7 µV
    a = fsc / 2
    tone = a * np.sin(2 * np.pi * f0 * t)
    noise = rng.normal(0, 10.0, n)
    sband = lambda nz, lo_, hi_, win='blackmanharris': math.sqrt(
        spectrum(nz, fs, win)[0][(np.fft.rfftfreq(nz.size, 1 / fs) >= lo_) & (np.fft.rfftfreq(nz.size, 1 / fs) < hi_)].sum())
    pref = lambda nz, win='blackmanharris': sband(nz, 0, fs, win) ** 2
    assert abs(pref(w[:n], 'boxcar') / w[:n].var() - 1) < 1e-9          # 单边谱归一化：矩形窗全加精确等于方差
    assert abs(pref(w[:n]) / w[:n].var() - 1) < 0.06                     # BH 单次估计本身有约 1.1%（1σ）抖动，留 5σ
    assert abs(pref(w[:n] + 1e4, 'boxcar') / w[:n].var() - 1) < 1e-9     # 直流偏置先去掉
    var = pref(noise)
    x = tone + noise
    for f0_arg in (f0, None):                                           # 给 f0 和自动找峰都要对
        snr_th = 10 * math.log10((a * a / 2) / var)
        enob_th = (10 * math.log10((fsc * fsc / 2) / var) - 1.76) / 6.02
        r = fft_metrics(x, fs, fsc, f0=f0_arg)
        assert abs(r['snr_dbc'] - snr_th) < 0.1, (f0_arg, r['snr_dbc'], snr_th)
        assert abs(r['enob'] - enob_th) < 0.02, (f0_arg, r['enob'], enob_th)
        assert abs(r['amplitude'] / a - 1) < 1e-3 and abs(r['f0_hz'] - f0) < 1e-9
        assert abs(r['snr_dbfs'] - r['snr_dbc'] - 20 * math.log10(fsc / r['amplitude'])) < 1e-9
    # 电极常有几十 mV 直流：去均值后 SNR 不受影响
    assert abs(fft_metrics(x + 5e4, fs, fsc, f0=f0)['snr_dbc'] - fft_metrics(x, fs, fsc, f0=f0)['snr_dbc']) < 0.01
    # 非相干（50.3 Hz）也要对：Blackman-Harris 默认
    snr_th = 10 * math.log10((a * a / 2) / var)
    xn = a * np.sin(2 * np.pi * 50.3 * t) + noise
    r = fft_metrics(xn, fs, fsc, f0=50.3)
    assert abs(r['snr_dbc'] - snr_th) < 0.15 and abs(r['amplitude'] / a - 1) < 0.01, r
    # 已知二、三次谐波：THD、SINAD、ENOB 都要把谐波算进去，SNR 不能把谐波当噪声
    h2, h3 = a * 1e-3, a * 10 ** (-70 / 20)
    xh = x + h2 * np.sin(2 * np.pi * 2 * f0 * t) + h3 * np.sin(2 * np.pi * 3 * f0 * t)
    r = fft_metrics(xh, fs, fsc, f0=f0)
    ph_th = (h2 * h2 + h3 * h3) / 2
    assert abs(r['thd_dbc'] - 10 * math.log10(ph_th / (a * a / 2))) < 0.1, r['thd_dbc']
    assert abs(r['harmonics_dbc'][0] + 60) < 0.1 and abs(r['harmonics_dbc'][1] + 70) < 0.1
    assert abs(r['sfdr_dbc'] - 60) < 0.1
    assert abs(r['snr_dbc'] - snr_th) < 0.1, r['snr_dbc']
    assert abs(r['sinad_dbc'] - 10 * math.log10((a * a / 2) / (var + ph_th))) < 0.1, r['sinad_dbc']
    assert abs(r['enob'] - (10 * math.log10((fsc * fsc / 2) / (var + ph_th)) - 1.76) / 6.02) < 0.02, r['enob']
    # 非谐波杂散：−70 dBc、37.3 Hz（非相干），SFDR 要按泄漏能量算，不能只取单个 bin
    r = fft_metrics(x + a * 10 ** (-70 / 20) * np.sin(2 * np.pi * 37.3 * t), fs, fsc, f0=f0)
    assert abs(r['sfdr_dbc'] - 70) < 0.2, r['sfdr_dbc']
    # 频带外的杂散（900 Hz）和慢漂（2 Hz）不算进 [20, 500) 的 SFDR；频带内的照算
    xo = x + h2 * np.sin(2 * np.pi * 900.3 * t) + h2 * np.sin(2 * np.pi * 2.03 * t)
    assert fft_metrics(xo, fs, fsc, f0=f0, lo=20, hi=500)['sfdr_dbc'] > 80
    # 带外大杂散（900 Hz，−60）和带内小杂散（300.3 Hz，−80）同时在：只认带内那个
    r = fft_metrics(xo + a * 1e-4 * np.sin(2 * np.pi * 300.3 * t), fs, fsc, f0=f0, lo=20, hi=500)
    assert abs(r['sfdr_dbc'] - 80) < 0.3, r['sfdr_dbc']
    assert abs(fft_metrics(xo, fs, fsc, f0=f0)['sfdr_dbc'] - 60) < 0.2
    # 正好压在频带上沿（500.0 Hz，[20, 500)）的杂散只算落进频带的那部分：比整份算（60）小、比完全不算（>100）大
    assert 62 < fft_metrics(x + h2 * np.sin(2 * np.pi * 500.0 * t), fs, fsc, f0=f0, lo=20, hi=500)['sfdr_dbc'] < 75
    # 频带外的谐波（150 Hz 的 4 次 = 600 Hz）：THD 照算，SFDR 只看频带内
    f150 = coherent_freq(fs, n, 150)
    r = fft_metrics(a * np.sin(2 * np.pi * f150 * t) + h2 * np.sin(2 * np.pi * 4 * f150 * t) + noise,
                    fs, fsc, f0=f150, lo=20, hi=500)
    assert r['sfdr_dbc'] > 80 and abs(r['thd_dbc'] + 60) < 0.1, r
    # 谐波折叠：f0≈400 Hz、fs=2000 时 3 次谐波 1200 Hz 混叠到 800 Hz，和 2 次谐波叠在一起，
    # 能量只算一次、单项记 None；4 次叠在基波上、5 次落在直流上，也记 None
    f4 = coherent_freq(fs, n, 400)
    x4 = a * np.sin(2 * np.pi * f4 * t) + h2 * np.sin(2 * np.pi * 3 * f4 * t) + noise
    r = fft_metrics(x4, fs, fsc, f0=f4)
    assert all(v is None for v in r['harmonics_dbc']), r             # 4 次谐波 1600 Hz 混叠回 400 Hz，叠在基波上
    assert abs(r['thd_dbc'] + 60) < 0.1 and abs(r['snr_dbc'] - snr_th) < 0.1, r
    # 频带：只积 [lo, hi)，和同一段噪声单独算的频带 RMS 对得上
    r = fft_metrics(x, fs, fsc, f0=f0, lo=20, hi=500)
    assert abs(r['noise_rms'] / sband(noise, 20, 500) - 1) < 0.03, r['noise_rms']
    # 短记录：剔掉的 bin 占比大（2048 点里约 13%），被剔的 bin 必须按平均噪声补回，否则偏高约 0.6 dB。
    # 单次 2048 点的估计本身就有 ±0.25 dB（1σ，合成 40 次统计），所以取 16 次平均再比。
    n2 = 2048
    t2 = np.arange(n2) / fs
    f2 = coherent_freq(fs, n2, 50)
    e = []
    for _ in range(16):
        nz = rng.normal(0, 10.0, n2)
        r = fft_metrics(a * np.sin(2 * np.pi * f2 * t2) + nz, fs, fsc, f0=f2)
        e.append(r['snr_dbc'] - 10 * math.log10((a * a / 2) / pref(nz)))
    assert abs(np.mean(e)) < 0.2, e
    # CMRR：注入 1 V 峰峰，输出端 50 µV 峰 → 20·log10(0.5e6/50) = 80 dB
    inj, ad = 1e6, 50.0
    y = ad * np.sin(2 * np.pi * f0 * t + 0.7) + 3.0 + rng.normal(0, 1.0, n)
    r = cmrr_db(inj, y, fs, f0)
    assert abs(r['cmrr_db'] - 80) < 0.05, r
    # 电极常有几十 mV 直流偏置：拟合里必须带直流项，否则非整周期时偏置会漏进幅度
    y3 = ad * np.sin(2 * np.pi * 50.3 * t) + 5e4 + rng.normal(0, 1.0, n)
    assert abs(cmrr_db(inj, y3, fs, 50.3)['cmrr_db'] - 80) < 0.05
    # 片内振荡器快 2%：实际 fs 是 2040，按名义 2000 分析，不搜就错，搜 ±3% 就对
    y2 = ad * np.sin(2 * np.pi * f0 * np.arange(n) / 2040.0) + rng.normal(0, 1.0, n)
    assert cmrr_db(inj, y2, fs, f0)['cmrr_db'] > 90
    base2 = 20.0 * np.sin(2 * np.pi * f0 * np.arange(n) / 2040.0) + rng.normal(0, 1.0, n)
    r = cmrr_db(inj, y2, fs, f0, search=0.03, baseline=base2)
    assert abs(r['cmrr_db'] - 80) < 0.05 and abs(r['f_used'] - f0 * 2000 / 2040) < 0.01, r
    assert abs(r['baseline_db'] - 20 * math.log10(20 / 50)) < 0.05, r     # 基线也要用搜到的频率拟合
    # 基线：不注入时同频还有 20 µV（工频串进来），结果里要能看出来
    base = 20.0 * np.sin(2 * np.pi * f0 * t) + rng.normal(0, 1.0, n)
    r = cmrr_db(inj, y, fs, f0, baseline=base)
    assert abs(r['baseline_db'] - 20 * math.log10(20 / 50)) < 0.05, r
    # 反例：输入不合规一律拒绝
    for bad in (lambda: stats([1.0, float('nan')] * 10), lambda: stats([1.0] * 5),
                lambda: band_rms(w, fs, 20, 1200), lambda: band_rms(w, fs, 500, 20),
                lambda: fft_metrics(x, fs, fsc, f0=0.01), lambda: fft_metrics(x, fs, 0, f0=f0),
                lambda: fft_metrics(a * np.sin(2 * np.pi * 999.95 * t), fs, fsc, f0=999.95),
                lambda: spectrum(x, fs, 'kaiser'), lambda: cmrr_db(0, y, fs, f0),
                lambda: band_rms(w[:3000], fs, 20, 500),                    # 1.5 s，不到一段 2 s
                lambda: band_rms(w, fs, 49.2, 49.4),                        # 频带里不到 2 个 bin
                # 片内振荡器快 2%、按名义 fs 分析：真峰离名义 50 Hz 约 16 个 bin，超出 ±12，要报错不能出乱数
                lambda: fft_metrics(a * np.sin(2 * np.pi * f0 * t * 2000 / 2040) + noise, fs, fsc, f0=f0),
                lambda: coherent_freq(2000, 2, 10)):
        try:
            bad(); raise AssertionError('应该报错')
        except ValueError:
            pass
    print('bench_analysis --check: OK')


if __name__ == '__main__':
    if sys.argv[1:] != ['--check']:
        print(__doc__); sys.exit(2)
    _selfcheck()

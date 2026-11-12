"""质量门（EMG_STUDIO_V2_PLAN 附录 C）：一段录音入集前的判定。返回 {'ok': bool, 'why': str, ...指标}。

阈值先沿用现有代码：wl8.validate（丢帧 / 帧数 / 饱和）、usb_emg 的 SMR 定义；设备描述 limits 可覆盖。
不抛异常——拒绝也是一个结果，页面要显示原因。
"""
import numpy as np
from scipy.signal import welch

RAIL_FRACTION = .01
MIN_FRAMES_FRACTION = .95
SMR_FLOOR_DB = 0.
NOISE_RATIO_MAX = .10


def check_noise_ratio(rest_uv, effort_uv, max_ratio=NOISE_RATIO_MAX, min_pass_channels=None):
    """静息/发力峰谷噪声比门（Sharma 2025 Eq. 1/5/6）：每路 (P99-P1)_rest ÷ (P99-P1)_effort <= max_ratio（默认 10%）。"""
    rest = np.asarray(rest_uv, np.float64)
    effort = np.asarray(effort_uv, np.float64)
    if rest.ndim != 2 or effort.ndim != 2 or rest.shape[1] != effort.shape[1] or len(rest) == 0 or len(effort) == 0:
        raise ValueError(f'rest_uv {rest.shape} 与 effort_uv {effort.shape} 维度不匹配或为空')
    n_ch = int(rest.shape[1])
    if min_pass_channels is None:
        min_pass_channels = max(1, int(np.ceil(n_ch * 0.75)))
    rest_nm = np.percentile(rest, 99, axis=0) - np.percentile(rest, 1, axis=0)
    eff_mapp = np.maximum(np.percentile(effort, 99, axis=0) - np.percentile(effort, 1, axis=0), 1e-9)
    ratio_q99 = rest_nm / eff_mapp
    ch_pass = ratio_q99 <= max_ratio
    n_pass = int(np.sum(ch_pass))
    failed = [int(i + 1) for i, ok in enumerate(ch_pass) if not ok]
    ok = bool(n_pass >= min_pass_channels)
    why = '' if ok else f'静息/发力峰谷比超标（{n_pass}/{n_ch} 路 ≤ {max_ratio:.0%}，超标通道 {failed}）'
    return {
        'ok': ok,
        'why': why,
        'strict_all_ok': bool(n_pass == n_ch),
        'pass_channels': n_pass,
        'total_channels': n_ch,
        'failed_channels_1based': failed,
        'max_ratio_limit': float(max_ratio),
        'mean_ratio_q99_pct': round(float(np.mean(ratio_q99) * 100.0), 2),
        'max_ratio_q99_pct': round(float(np.max(ratio_q99) * 100.0), 2),
        'ratio_q99_pct': [round(float(v * 100.0), 2) for v in ratio_q99],
        'rest_nm_uv': [round(float(v), 2) for v in rest_nm],
        'effort_mapp_uv': [round(float(v), 2) for v in eff_mapp],
    }


def smr_db(uv, fs):
    """肌电带（20–450 Hz）对低频（<20 Hz）的功率比，dB；全路取最小（最差的一路）。"""
    x = np.asarray(uv, np.float64)
    if len(x) < 64:
        return 60.
    f, P = welch(x - x.mean(0), fs, nperseg=min(512, len(x)), axis=0)
    band = P[(f >= 20) & (f <= min(450, fs / 2 - 1))].sum(0)
    low = P[(f > 0) & (f < 20)].sum(0)
    with np.errstate(divide='ignore', invalid='ignore'):
        r = np.where((band > 0) & (low > 0), 10 * np.log10(band / np.maximum(low, 1e-30)), 60.)
    return float(np.min(np.minimum(r, 60.)))


def check(desc, uv, seconds=None, dropped=0, n_expected=None, limits=None, rest_uv=None):
    lim = dict(desc.limits or {})
    lim.update(limits or {})
    uv = np.asarray(uv)
    n = len(uv)
    fs = desc.fs_Hz
    out = {'frames': int(n), 'dropped': int(dropped), 'seconds': round(n / fs, 3)}
    if n_expected is None and seconds:
        n_expected = int(seconds * fs)
    max_drop = float(lim.get('max_drop_rate', 0.0))
    if dropped and (n == 0 or dropped / max(n + dropped, 1) > max_drop):
        return dict(out, ok=False, why=f'丢帧 {dropped}')
    if n_expected and n < n_expected * MIN_FRAMES_FRACTION:
        return dict(out, ok=False, why=f'只收到 {n} 帧（应 {n_expected}）')
    if n == 0:
        return dict(out, ok=False, why='没有数据')
    rail = float(lim.get('rail_uV', np.inf))
    railed = float((np.abs(uv) >= rail).mean()) if np.isfinite(rail) else 0.
    out['railed'] = round(railed, 4)
    if railed > RAIL_FRACTION:
        return dict(out, ok=False, why=f'饱和 {railed:.1%}')
    s = smr_db(uv, fs)
    out['smr_db'] = round(s, 2)
    if s < float(lim.get('smr_floor_db', SMR_FLOOR_DB)):
        return dict(out, ok=False, why=f'低频能量偏高：SMR {s:.2f} dB')
    rms = np.sqrt(((uv - uv.mean(0)) ** 2).mean(0))
    out['rms_uv'] = [round(float(v), 1) for v in rms]
    if rest_uv is not None:
        max_nr = float(lim.get('max_noise_ratio', NOISE_RATIO_MAX))
        min_ch = lim.get('min_noise_ratio_channels', None)
        nr = check_noise_ratio(rest_uv, uv, max_ratio=max_nr, min_pass_channels=min_ch)
        out['noise_ratio'] = nr
        if not nr['ok']:
            return dict(out, ok=False, why=nr['why'])
    return dict(out, ok=True, why='')

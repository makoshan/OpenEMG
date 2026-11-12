"""Two bench tests borrowed from Liang et al. 2023 (Micromachines 14, 1085), run on the
single-channel Cheez + XIAO rig through usb_emg.py's own capture path.

sweep   -- frequency response of the front end. A known sine goes into the electrode inputs
           (signal generator, or the Mac's headphone out through a ~1000:1 divider), one 2 s
           take per frequency, a least-squares sine fit at the KNOWN frequency reads the output
           amplitude, so mains hum and noise do not count as signal. No skin involved.
fatigue -- "is this real muscle": hold a sustained load to exhaustion, one 2 s take after
           another. Real EMG shows RMS rising and median frequency falling; motion artefact
           and a lifting electrode do not produce that pair.

    python3 emg_bench.py --check                                  # synthetic, no hardware
    python3 emg_bench.py sweep --tone mac --vin-mvpp 2            # Mac plays each tone via afplay
    python3 emg_bench.py sweep --tone manual                      # you set the generator, press Enter
    python3 emg_bench.py fatigue --seconds 90                     # 屈肘 90° 持重到力竭
    python3 emg_bench.py analyze emg-data/_bench/fatigue/<file>.npz

The rig samples at 1 kHz, so the sweep stops below the 500 Hz Nyquist (the paper's 700 Hz /
1.6 kHz points are not measurable here). Frequencies avoid 50 Hz harmonics.
"""
import argparse
import json
import subprocess
import tempfile
import time
import wave
from pathlib import Path

import numpy as np

import usb_emg as ue

OUT = ue.DATA / '_bench'          # usb_emg.load() globs */*.npz, so this depth never leaks into training
SWEEP_HZ = (5, 10, 20, 35, 75, 130, 230, 330, 430)
MIN_SNR = 10.                      # fitted amplitude over residual RMS; below this the tone is not there
# ponytail: fatigue verdict thresholds are set on synthetic takes; re-set from Mako's first real run.
MF_R_MAX = -.5                     # median-frequency trend must be at least this strongly negative
MIN_TAKES = 8


# ------------------------------------------------------------------ maths ----
def sine_fit(counts, hz):
    """Amplitude (V peak-to-peak) of the hz component and its SNR, via LS on [sin, cos, 1]."""
    x = ue._volts(counts)
    t = np.arange(len(x)) / ue.EMG_HZ
    basis = np.column_stack([np.sin(2 * np.pi * hz * t), np.cos(2 * np.pi * hz * t), np.ones(len(x))])
    coef, *_ = np.linalg.lstsq(basis, x, rcond=None)
    amp = float(np.hypot(*coef[:2]))
    resid = float(np.std(x - basis @ coef))
    return 2 * amp, amp / max(resid, 1e-12)


def sweep_report(points, vin_mvpp=None):
    """points: [(hz, vout_pp, snr)] -> rows with gain, dB re. the peak, and the -3 dB band."""
    good = [(f, v, s) for f, v, s in points if s >= MIN_SNR]
    peak = max((v for _, v, _ in good), default=0.)
    rows = []
    for f, v, s in points:
        row = {'hz': f, 'vout_mvpp': round(v * 1000, 3), 'snr': round(s, 1), 'tone_found': s >= MIN_SNR}
        if s >= MIN_SNR and peak > 0:
            row['rel_db'] = round(20 * np.log10(v / peak), 2)
            if vin_mvpp:
                row['gain_vv'] = round(v * 1000 / vin_mvpp, 1)
        rows.append(row)
    inband = [r['hz'] for r in rows if r.get('rel_db', -99) >= -3]
    return {'rows': rows, 'band_3db_hz': [min(inband), max(inband)] if inband else None,
            'vin_mvpp': vin_mvpp, 'missing_tones': [r['hz'] for r in rows if not r['tone_found']]}


def fatigue_report(t_s, takes):
    """Linear trends of RMS and median frequency over the hold, as the paper fits them."""
    feats = np.array([ue.emg_features((c, 1000)) for c in takes])
    names = list(ue.EMG_FEATURES)
    rms, mf = feats[:, names.index('rms')], feats[:, names.index('median_freq')]
    t = np.asarray(t_s, float)
    out = {'takes': len(t), 'seconds': round(float(t[-1] - t[0]), 1) if len(t) else 0}
    if len(t) < MIN_TAKES:
        return {**out, 'verdict': f'样本不够：{len(t)} 段 < {MIN_TAKES}，持续时间再长一点'}
    for name, y in (('rms_mv', rms * 1000), ('median_hz', mf)):
        slope = float(np.polyfit(t, y, 1)[0])
        out[name] = {'first': round(float(y[:3].mean()), 3), 'last': round(float(y[-3:].mean()), 3),
                     'slope_per_min': round(slope * 60, 3), 'r': round(float(np.corrcoef(t, y)[0, 1]), 3)}
    real = out['median_hz']['r'] <= MF_R_MAX and out['rms_mv']['slope_per_min'] > 0
    out['verdict'] = ('PASS 中值频率下降、RMS 上升：像真肌电疲劳' if real else
                      'FAIL 没有疲劳特征：查电极贴合、是不是没到力竭、或拿到的是运动伪迹')
    out['pass'] = real
    return out


# ---------------------------------------------------------------- capture ----
def _open(port):
    import serial
    device = ue.find_port(port)
    connection = serial.Serial(device.device, 115200, timeout=.2, write_timeout=2, exclusive=True)
    time.sleep(2)
    ue._drain(connection)
    connection.write(b'?')
    ue.read_header(connection, timeout=5, prefix=ue.BANNER)
    return device, connection


def _tone_wav(hz, seconds=ue.SECONDS + 3, level=.5):
    path = Path(tempfile.gettempdir()) / f'emg_bench_{hz}hz.wav'
    rate = 48000
    t = np.arange(int(rate * seconds)) / rate
    pcm = (level * 32767 * np.sin(2 * np.pi * hz * t)).astype('<i2')
    with wave.open(str(path), 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate); w.writeframes(pcm.tobytes())
    return path


def sweep(tone, vin_mvpp, port):
    device, connection = _open(port)
    points, takes = [], []
    with connection:
        for hz in SWEEP_HZ:
            player = None
            if tone == 'mac':
                player = subprocess.Popen(['afplay', str(_tone_wav(hz))])
                time.sleep(.8)                  # let the output and the module's filters settle
            else:
                input(f'信号发生器调到 {hz} Hz（幅值不变），回车开始录…')
            try:
                # wear='off': no skin on a bench sweep. review_smr: a 5 Hz tone IS low-frequency power.
                counts, *_ = ue.read_take(connection, wear='off', review_smr=True)
            except ValueError as error:
                print(f'{hz:>4} Hz  丢弃（{error}）'); counts = np.zeros(ue.EMG_COUNT, '<i2')
            finally:
                if player: player.terminate()
            vpp, snr = sine_fit(counts, hz)
            points.append((hz, vpp, snr)); takes.append(counts)
            print(f'{hz:>4} Hz  out {vpp * 1000:8.2f} mVpp  SNR {snr:6.1f}')
    report = sweep_report(points, vin_mvpp)
    _save('sweep', device, report, np.array(takes), np.array(SWEEP_HZ, float))


def fatigue(seconds, port, wear):
    device, connection = _open(port)
    t_s, takes, dropped = [], [], 0
    print('屈肘 90° 持重保持住，坚持到力竭；Ctrl-C 提前结束。')
    start = time.monotonic()
    with connection:
        try:
            while time.monotonic() - start < seconds:
                at = time.monotonic() - start
                try:
                    counts, *_ = ue.read_take(connection, wear)
                except ValueError as error:
                    dropped += 1; print(f'{at:6.1f}s  丢弃（{error}）'); continue
                f = ue.emg_features((counts, 1000))
                t_s.append(at); takes.append(counts)
                print(f'{at:6.1f}s  rms {f[0] * 1000:6.2f} mV  中值频率 {f[5]:5.1f} Hz')
        except KeyboardInterrupt:
            print()
    report = {**fatigue_report(t_s, takes), 'dropped': dropped}
    _save('fatigue', device, report, np.array(takes), np.array(t_s))


def _save(kind, device, report, takes, axis):
    folder = OUT / kind
    folder.mkdir(parents=True, exist_ok=True)
    stem = folder / f'{kind}-{time.strftime("%Y%m%dT%H%M%S")}'
    np.savez(stem.with_suffix('.npz'), emg=takes, axis=axis, kind=kind, serial=device.serial_number or '')
    stem.with_suffix('.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f'存在 {stem}.npz / .json')


def analyze(path, vin_mvpp=None):
    with np.load(path, allow_pickle=False) as blob:
        takes, axis, kind = blob['emg'], blob['axis'], str(blob['kind'])
    if kind == 'sweep':
        report = sweep_report([(int(f), *sine_fit(c, f)) for f, c in zip(axis, takes)], vin_mvpp)
    else:
        report = fatigue_report(axis, takes)
    print(json.dumps(report, ensure_ascii=False, indent=2))


# ------------------------------------------------------------------ check ----
def _counts(volts):
    return np.clip(np.round(volts / (ue.FULL_SCALE_MV / 1000) * ue.ADC_MAX), 0, ue.ADC_MAX - 1).astype('<i2')


def check():
    rng = np.random.default_rng(7)
    t = np.arange(ue.EMG_COUNT) / ue.EMG_HZ
    # Sweep: a front end with a 20 Hz high-pass and 300 Hz low-pass (first order), gain 1000 on 1 mVpp.
    def response(f):
        return 1 / np.sqrt(1 + (20 / f) ** 2) / np.sqrt(1 + (f / 300) ** 2)
    points = []
    for f in SWEEP_HZ:
        v = 1.65 + .5 * response(f) * np.sin(2 * np.pi * f * t + 1) + .01 * np.sin(2 * np.pi * 50 * t) \
            + rng.normal(0, .003, len(t))
        vpp, snr = sine_fit(_counts(v), f)
        assert abs(vpp - response(f)) < .01, (f, vpp, response(f))     # hum and noise do not count as tone
        points.append((f, vpp, snr))
    rep = sweep_report(points, vin_mvpp=1)
    top = max(response(f) for f in SWEEP_HZ)
    want = [f for f in SWEEP_HZ if 20 * np.log10(response(f) / top) >= -3]
    assert rep['band_3db_hz'] == [want[0], want[-1]] == [20, 330], rep['band_3db_hz']  # -3 dB re. the measured peak
    assert abs(next(r for r in rep['rows'] if r['hz'] == 75)['gain_vv'] - 1000 * response(75)) < 10
    # Must fail: a take with hum and noise but no tone is reported missing, not as a tiny gain.
    hum_only = _counts(1.65 + .01 * np.sin(2 * np.pi * 50 * t) + rng.normal(0, .003, len(t)))
    assert sweep_report([(130, *sine_fit(hum_only, 130))])['missing_tones'] == [130]

    # Fatigue: amplitude creeps up while the spectrum slides down -> PASS.
    def hold(amp, top_hz):
        return _counts(1.65 + amp * ue._bandnoise(ue.EMG_COUNT, 30, top_hz, rng) + rng.normal(0, .002, len(t)))
    n = 20
    times = np.arange(n) * 3.
    tired = [hold(.05 + .05 * i / n, 250 - 120 * i / n) for i in range(n)]
    rep = fatigue_report(times, tired)
    assert rep['pass'], rep
    assert rep['median_hz']['slope_per_min'] < 0 < rep['rms_mv']['slope_per_min'], rep
    # Must fail: a steady hold (no fatigue) and a louder-only drift (RMS up, spectrum fixed).
    assert not fatigue_report(times, [hold(.07, 200) for _ in range(n)])['pass']
    assert not fatigue_report(times, [hold(.05 + .05 * i / n, 200) for i in range(n)])['pass']
    assert 'pass' not in fatigue_report(times[:3], tired[:3])            # too few takes is not a verdict
    print('emg_bench --check: PASS (sweep fit/band/missing-tone, fatigue pass + 2 must-fail + short)')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    p.add_argument('--check', action='store_true')
    sub = p.add_subparsers(dest='cmd')
    s = sub.add_parser('sweep'); s.add_argument('--tone', choices=('mac', 'manual'), default='manual')
    s.add_argument('--vin-mvpp', type=float, help='进入电极端的峰峰值（mV）；不给就只报相对 dB')
    s.add_argument('--port')
    f = sub.add_parser('fatigue'); f.add_argument('--seconds', type=float, default=90)
    f.add_argument('--wear', choices=('high', 'low', 'off'), default='high'); f.add_argument('--port')
    a = sub.add_parser('analyze'); a.add_argument('path'); a.add_argument('--vin-mvpp', type=float)
    args = p.parse_args()
    if args.check: check()
    elif args.cmd == 'sweep': sweep(args.tone, args.vin_mvpp, args.port)
    elif args.cmd == 'fatigue': fatigue(args.seconds, args.port, args.wear)
    elif args.cmd == 'analyze': analyze(args.path, args.vin_mvpp)
    else: p.print_help()

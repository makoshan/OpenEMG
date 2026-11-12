"""Line C host side: record synchronised EMG + IMU takes off emg_imu_usb, keep the honest ones,
and measure how far the muscle leads the arm.

    python3 usb_emg_imu.py --check                      # no hardware: framing + lead maths
    python3 usb_emg_imu.py --record punch --count 30    # takes into emg-imu-data/punch/
    python3 usb_emg_imu.py --lead                        # Δ = EMG onset − IMU onset per take, median/IQR

Δ < 0 means the muscle fired before the arm moved. The number that matters is the median over
≥30 punches against the 4.8 ms IMU period; if it is inside the pacing jitter, line C stops here.
"""
import os
import argparse
import json
import time
import zlib
from pathlib import Path

import numpy as np

import usb_emg
from usb_emg import EMG_HZ, EMG_COUNT, read_header, _drain

BANNER = 'MAKO DAILY 1.usb-emg-imu; USB-EMGIMU-1'
IMU_HZ, FRAME = 208, np.dtype([('ms', '<u4'), ('g', '<i2', 3), ('a', '<i2', 3)])
ACCEL_G = 0.000244               # g/LSB at +-8 g; device/main.cpp converts with the same numbers
GYRO_DPS = 0.035                 # dps/LSB at +-1000 dps
DATA = Path('emg-imu-data')
IMU_MIN_FRAMES = int(IMU_HZ * usb_emg.SECONDS * .9)
IMU_MAX_GAP_MS = 10
# punch_detect.h: gravity low-pass alpha=0.1 at 52 Hz, forward dynamic accel > 2 g. Same time
# constant at 208 Hz needs alpha 1-(1-0.1)^(52/208); magnitude instead of the X axis because the
# bench board is not mounted in the watch's orientation.
PUNCH_G, ALPHA = 2.0, 1 - (1 - .1) ** (52 / 208)


def parse_header(header):
    f = header.split()
    if len(f) != 12 or f[0] != 'EMGIMU':
        raise ValueError(f'Unexpected EMGIMU header: {header!r}')
    emg_hz, n_emg, imu_hz, n_imu = map(int, f[1:5])
    if (emg_hz, n_emg, imu_hz) != (EMG_HZ, EMG_COUNT, IMU_HZ):
        raise ValueError(f'Unexpected capture geometry: {header!r}')
    worn, max_gap_us, late, faults, t0_ms = map(int, f[7:12])
    return {'n_imu': n_imu, 'crc_emg': int(f[5], 16), 'crc_imu': int(f[6], 16), 'worn': worn,
            'max_gap_us': max_gap_us, 'late': late, 'fifo_faults': faults, 't0_ms': t0_ms}


def validate(header, emg_payload, imu_payload, wear='high'):
    """EMG half goes through usb_emg.validate unchanged (wear, rail, drift, pacing); the IMU
    half must be complete, gap-free and fault-free, or the lead number is a lie."""
    h = parse_header(header)
    if len(imu_payload) != h['n_imu'] * FRAME.itemsize or zlib.crc32(imu_payload) != h['crc_imu']:
        raise ValueError('Incomplete/corrupt IMU payload')
    emg_header = f"EMG {EMG_HZ} {EMG_COUNT} {h['crc_emg']:x} {h['worn']} {h['max_gap_us']} {h['late']}"
    worn, railed = usb_emg.validate(emg_header, emg_payload, wear)
    if h['fifo_faults']:
        raise ValueError(f"IMU FIFO 报了 {h['fifo_faults']} 次故障：这条的时序不可信")
    if h['n_imu'] < IMU_MIN_FRAMES:
        raise ValueError(f"IMU 只有 {h['n_imu']} 帧（要 ≥{IMU_MIN_FRAMES}）")
    frames = np.frombuffer(imu_payload, FRAME)
    gaps = np.diff(frames['ms'].astype(np.int64))
    if gaps.size and gaps.max() > IMU_MAX_GAP_MS:
        raise ValueError(f'IMU 帧最大间隔 {gaps.max()} ms')
    return h, worn, railed, frames


def imu_onset_ms(frames, t0_ms):
    """First frame whose dynamic acceleration magnitude exceeds PUNCH_G, relative to the EMG
    clock (t0_ms = millis at EMG sample 0). None if the arm never moved that hard."""
    a = frames['a'].astype(float) * ACCEL_G
    g = a[0].copy()
    for i in range(len(a)):
        g += ALPHA * (a[i] - g)
        if np.linalg.norm(a[i] - g) > PUNCH_G:
            return float(int(frames['ms'][i]) - t0_ms)
    return None


ONSET_WINDOW_MS = 20


def emg_onset_ms(counts, worn):
    """First time a CAUSAL 20 ms RMS clears 20% of its own peak. usb_emg's onset_ms uses a
    centred 100 ms window, which reports the burst up to 50 ms before it happened -- fine for a
    feature, fatal for a lead measurement. The trailing window can only be LATE (<= 20 ms),
    so any lead it reports is an underestimate, never an artefact. Mains hum is notched first
    (usb_emg.clean, also causal): steady 50 Hz can clear 20% of the peak in the first window and
    would stamp every take at ~19 ms."""
    x = usb_emg.clean(usb_emg._volts(counts))
    n = int(EMG_HZ * ONSET_WINDOW_MS / 1000)
    cs = np.concatenate([[0.], np.cumsum(x * x)])
    rms = np.sqrt((cs[n:] - cs[:-n]) / n)                      # rms[i] covers samples i..i+n-1, stamped at i+n-1
    peak = rms.max()
    if peak <= 0:
        return None
    hit = np.flatnonzero(rms > .2 * peak)
    return float((hit[0] + n - 1) * 1000 / EMG_HZ) if hit.size else None


def lead(record):
    """Δ = EMG onset − IMU onset (ms) for one saved take, or None if either onset is missing."""
    e, i = emg_onset_ms(record['emg'], record['worn']), imu_onset_ms(record['imu'], record['t0_ms'])
    return None if e is None or i is None or e >= usb_emg.SECONDS * 1000 else e - i


def summarize(records):
    deltas = [d for d in (lead(r) for r in records) if d is not None]
    if not deltas:
        return {'takes': len(records), 'with_both_onsets': 0, 'message': '没有一条同时找到肌电起点和 IMU 起点'}
    q = np.percentile(deltas, [25, 50, 75])
    return {'takes': len(records), 'with_both_onsets': len(deltas), 'median_ms': float(q[1]),
            'iqr_ms': [float(q[0]), float(q[2])], 'imu_period_ms': 1000 / IMU_HZ,
            'message': f'EMG 比 IMU {"早" if q[1] < 0 else "晚"} {abs(q[1]):.0f} ms（中位，IQR {q[0]:.0f}..{q[2]:.0f}），IMU 一格 {1000 / IMU_HZ:.1f} ms'}


def save(stem, counts, frames, h, label, serial_number, session='', donning=0):
    np.savez_compressed(stem.with_suffix('.npz'), emg=counts, imu=frames, worn_permille=h['worn'], t0_ms=h['t0_ms'],
                        emg_hz=EMG_HZ, imu_hz=IMU_HZ, accel_g=ACCEL_G, gyro_dps=GYRO_DPS, label=label)
    stem.with_suffix('.json').write_text(json.dumps(dict(label=label, deviceSerial=serial_number, session=session, donning=int(donning),
        recordedAt=time.strftime('%Y-%m-%dT%H:%M:%S'), sensor='Cheez sEMG-D + LSM6DS3TR-C', **h), indent=2) + '\n')


def load(folder=DATA):
    out = []
    for path in sorted(Path(folder).glob('*/*.npz')):
        with np.load(path, allow_pickle=False) as b:
            out.append({'label': path.parent.name, 'emg': b['emg'], 'imu': b['imu'], 'worn': int(b['worn_permille']), 't0_ms': int(b['t0_ms'])})
    return out


def read_take(connection, wear='high'):
    """One 'r' round trip on an open connection. Raises ValueError for takes to drop."""
    _drain(connection); connection.write(b'r')
    read_header(connection, timeout=3, prefix='RECORDING')
    header = read_header(connection, timeout=usb_emg.SECONDS + 8, prefix='EMGIMU ')
    h = parse_header(header)
    need = EMG_COUNT * 2 + h['n_imu'] * FRAME.itemsize
    payload = bytearray(); deadline = time.monotonic() + 15
    while len(payload) < need and time.monotonic() < deadline:
        payload.extend(connection.read(need - len(payload)))
    emg_payload, imu_payload = bytes(payload[:EMG_COUNT * 2]), bytes(payload[EMG_COUNT * 2:])
    h, worn, railed, frames = validate(header, emg_payload, imu_payload, wear)
    return h, np.frombuffer(emg_payload, '<i2'), frames, railed


def record(label, count, wear='high', countdown=3, port=None, data=DATA, session='', donning=1):
    import serial
    from serial.tools import list_ports
    candidates = [p for p in list_ports.comports() if (p.device == port if port else p.vid == 0x2886)]
    device = None
    for c in candidates:
        try:
            with serial.Serial(c.device, 115200, timeout=.2, write_timeout=2, exclusive=True) as conn:
                time.sleep(2); _drain(conn); conn.write(b'?'); read_header(conn, timeout=3, prefix=BANNER); device = c; break
        except (OSError, ValueError, TimeoutError, RuntimeError):
            continue
    if device is None:
        raise RuntimeError('没找到跑 emg_imu_usb 固件的板子（要 Sense 版）：python3 bench_flash_uf2.py emg_imu_usb')
    folder = Path(data) / label; folder.mkdir(parents=True, exist_ok=True); kept = 0
    with serial.Serial(device.device, 115200, timeout=.2, write_timeout=2, exclusive=True) as conn:
        time.sleep(2); _drain(conn); conn.write(b'?'); banner = read_header(conn, timeout=5, prefix=BANNER)
        if 'imu=1' not in banner:
            raise RuntimeError(f'固件说 IMU 没起来：{banner}')
        for take in range(count):
            for remaining in range(countdown, 0, -1):
                print(f'\r[{take + 1}/{count}] {label}: {remaining}...', end='', flush=True); time.sleep(1)
            print(f'\r[{take + 1}/{count}] {label}: NOW      ', end='', flush=True)
            try:
                h, counts, frames, railed = read_take(conn, wear)
            except ValueError as error:
                print(f'\r[{take + 1}/{count}] {label}: DROPPED ({error})'); continue
            save(folder / f'{label}-{time.strftime("%Y%m%dT%H%M%S")}-{take:03d}', counts, frames, h, label, device.serial_number, session, donning)
            kept += 1
            d = lead({'emg': counts, 'imu': frames, 'worn': h['worn'], 't0_ms': h['t0_ms']})
            print(f'\r[{take + 1}/{count}] {label}: saved  imu {h["n_imu"]} 帧  gap {h["max_gap_us"]} us  Δ {"—" if d is None else f"{d:+.0f} ms"}')
    print(f'{kept}/{count} takes under {folder.resolve()}')


# ------------------------------------------------------------------ check ----
def _synth(rng, emg_at_ms=500, imu_at_ms=560, punch=True, t0_ms=1000):
    """EMG burst at emg_at_ms; arm spike at imu_at_ms (None = arm never moves)."""
    t = np.arange(EMG_COUNT) / EMG_HZ
    volts = 1.65 + rng.normal(0, .003, EMG_COUNT)
    shape = np.clip(np.minimum((t - emg_at_ms / 1000) / .03, (emg_at_ms / 1000 + .5 - t) / .03), 0, 1)
    volts += .25 * shape * usb_emg._bandnoise(EMG_COUNT, 20, 150, rng)
    counts = np.clip(np.round(volts / (usb_emg.FULL_SCALE_MV / 1000) * usb_emg.ADC_MAX), 0, usb_emg.ADC_MAX - 1).astype('<i2')
    n = IMU_HZ * usb_emg.SECONDS
    frames = np.zeros(n, FRAME); frames['ms'] = t0_ms + (np.arange(n) * 1000 / IMU_HZ).astype('<u4')
    a = np.zeros((n, 3)); a[:, 2] = 1.0
    if punch and imu_at_ms is not None:
        k = int(imu_at_ms * IMU_HZ / 1000); a[k:k + 10, 0] += 4.0
    frames['a'] = np.round(a / ACCEL_G).astype('<i2')
    return counts, frames


def check():
    import tempfile
    rng = np.random.default_rng(20260923)
    counts, frames = _synth(rng)
    h = {'n_imu': len(frames), 'worn': 1000, 't0_ms': 1000, 'max_gap_us': 1010, 'late': 0, 'fifo_faults': 0}
    eb, ib = counts.tobytes(), frames.tobytes()
    header = (f"EMGIMU {EMG_HZ} {EMG_COUNT} {IMU_HZ} {len(frames)} {zlib.crc32(eb):x} {zlib.crc32(ib):x} 1000 1010 0 0 1000")
    hh, worn, railed, fr = validate(header, eb, ib)
    assert worn == 1000 and len(fr) == len(frames)
    d = lead({'emg': counts, 'imu': fr, 'worn': 1000, 't0_ms': 1000})
    # Burst starts at 500 and ramps over 30 ms; the causal 20 ms window crosses 20% of peak
    # somewhere in 505..535, so against a spike at 560 the lead reads -55..-25: never the
    # ideal -60, never zero, always negative. The sign and the shift test are the contract.
    assert d is not None and -60 <= d < -10, f'lead {d}: burst at 500 vs spike at 560'
    # Must fail: shift the EMG burst 50 ms later and the number must follow by ~+50
    c2, f2 = _synth(np.random.default_rng(20260923), emg_at_ms=550)
    d2 = lead({'emg': c2, 'imu': f2, 'worn': 1000, 't0_ms': 1000})
    assert d2 is not None and 40 < d2 - d < 60, f'shift not tracked: {d} -> {d2}'
    # Must fail: a burst AFTER the arm moved must read positive, not get folded into a lead
    c4, f4 = _synth(np.random.default_rng(3), emg_at_ms=620)
    d4 = lead({'emg': c4, 'imu': f4, 'worn': 1000, 't0_ms': 1000})
    assert d4 is not None and d4 > 40, f'late burst read as lead: {d4}'
    # Arm never moves: no IMU onset, take excluded from the summary rather than counted as 0
    c3, f3 = _synth(rng, punch=False)
    assert lead({'emg': c3, 'imu': f3, 'worn': 1000, 't0_ms': 1000}) is None
    s = summarize([{'emg': counts, 'imu': fr, 'worn': 1000, 't0_ms': 1000}, {'emg': c3, 'imu': f3, 'worn': 1000, 't0_ms': 1000}])
    assert s['with_both_onsets'] == 1 and -60 <= s['median_ms'] < -10, s
    # Scale is a contract with the firmware, not a formula: _synth encodes with ACCEL_G itself, so
    # a wrong constant round-trips unnoticed. Anchor it to device/main.cpp and to physical g.
    # 固件在 tiny-ai-watch 仓库（firmware/device/main.cpp），原力手环仓库里没有；找不到就明说没比，不判过也不判错。
    fw = Path(os.environ.get('YUANLI_WATCH_FIRMWARE', Path(__file__).resolve().parents[1] / 'firmware/cheez-s3')) / 'device' / 'main.cpp'
    if fw.exists():
        src = fw.read_text()
        assert f'*{ACCEL_G}f' in src and f'*{GYRO_DPS}f' in src, f'IMU scale disagrees with {fw}'
    else:
        print(f'SKIP: 找不到手表固件 {fw}，IMU 刻度没和固件比对（设 YUANLI_WATCH_FIRMWARE）')
    _, f5 = _synth(rng, punch=False); k = 100
    f5['a'][k:k + 10, 0] += int(round(1.5 / 0.000244))       # a real 1.5 g jolt, below PUNCH_G
    assert imu_onset_ms(f5, 1000) is None, '1.5 g read as a punch: accel scale too large'
    f5['a'][k:k + 10, 0] += int(round(1.5 / 0.000244))       # now 3 g
    assert imu_onset_ms(f5, 1000) is not None, '3 g missed'
    # Must fail: steady 50 Hz hum loud enough to clear 20% of the peak from sample 0; unfiltered,
    # the onset lands at ~19 ms instead of at the burst
    c6, _ = _synth(np.random.default_rng(5))
    t = np.arange(EMG_COUNT) / EMG_HZ
    hum = .15 * np.sin(2 * np.pi * usb_emg.MAINS_HZ * t) / (usb_emg.FULL_SCALE_MV / 1000) * usb_emg.ADC_MAX
    c6 = np.clip(np.round(c6 + hum), 0, usb_emg.ADC_MAX - 1).astype('<i2')
    e6 = emg_onset_ms(c6, 1000)
    assert e6 is not None and 495 <= e6 <= 560, f'mains hum moved the onset to {e6} ms (burst at 500)'
    # IMU half refusals: FIFO fault, too few frames, a gap, corrupt payload
    for bad_header, why in [(header.replace(' 1010 0 0 1000', ' 1010 0 3 1000'), 'FIFO 故障'),
                            (None, 'gap')]:
        try:
            if bad_header:
                validate(bad_header, eb, ib)
            else:
                g = frames.copy(); g['ms'][200:] += 40; gb = g.tobytes()
                validate(f"EMGIMU {EMG_HZ} {EMG_COUNT} {IMU_HZ} {len(g)} {zlib.crc32(eb):x} {zlib.crc32(gb):x} 1000 1010 0 0 1000", eb, gb)
        except ValueError:
            pass
        else:
            raise AssertionError(f'IMU 侧坏 take 被收了: {why}')
    try:
        validate(header, eb, ib[:-3])
    except ValueError:
        pass
    else:
        raise AssertionError('IMU 载荷缺字节被收了')
    with tempfile.TemporaryDirectory() as tmp:
        stem = Path(tmp) / 'punch' / 'punch-000'; stem.parent.mkdir()
        save(stem, counts, fr, {**h, 'crc_emg': 0, 'crc_imu': 0}, 'punch', 'SN')
        back = load(tmp)
        assert len(back) == 1 and abs(lead(back[0]) - d) < 1e-6
    print('EMG+IMU: framing, both refusal sides, lead sign/shift/absence and save/load passed')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--check', action='store_true'); parser.add_argument('--record', metavar='LABEL')
    parser.add_argument('--count', type=int, default=30); parser.add_argument('--wear', choices=('high', 'low', 'off'), default='high')
    parser.add_argument('--port'); parser.add_argument('--data', default=str(DATA)); parser.add_argument('--session', default=''); parser.add_argument('--donning', type=int, default=1)
    parser.add_argument('--lead', action='store_true', help='对 --data 里所有 take 报提前量')
    a = parser.parse_args()
    if a.check:
        check()
    elif a.record:
        record(a.record, a.count, a.wear, port=a.port, data=a.data, session=a.session, donning=a.donning)
    elif a.lead:
        print(json.dumps(summarize(load(a.data)), ensure_ascii=False, indent=2))
    else:
        parser.error('--check / --record LABEL / --lead')

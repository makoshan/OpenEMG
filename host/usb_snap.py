"""Batch A for snap detection: record labelled sound+jolt takes, then ask one
question -- are finger snaps separable from claps?

The deployed detector is a coincidence gate (acoustic transient AND wrist impact
within +-30 ms), which kills door knocks and keyboards for free. It does NOT kill
claps: a clap is also an impact that moves the wrist. So claps are the only
negative class worth measuring before building anything, and this script measures
exactly that. Everything downstream is wasted if --report says the classes overlap.

  python3 usb_snap.py --check                         # no hardware; feature math + framing
  python3 usb_snap.py --record snap  --count 30       # 30 takes into snap-data/snap/
  python3 usb_snap.py --record clap  --count 30
  python3 usb_snap.py --record case_tap --count 20    # IMU strong, audio weak
  python3 usb_snap.py --report                        # separability verdict + scatter.png
"""
import argparse
import json
import struct
import sys
import time
import wave
import zlib
from pathlib import Path

import numpy as np

import separability as sep

BANNER = 'MAKO DAILY 1.usb-snap; USB-SNAP-1'
AUDIO_HZ, ACCEL_HZ, SECONDS = 16000, 833, 3
AUDIO_COUNT, ACCEL_FRAMES = AUDIO_HZ * SECONDS, ACCEL_HZ * SECONDS
ACCEL_G_PER_LSB = 32.0 / 65536.0  # +-16 g full scale
DATA = Path('snap-data')

# separability.py already owns the acoustic half and already names snap/clap/knock as the
# case it was built for; reimplementing it here would let the web gate and this one disagree.
# Only the three numbers the coincidence gate actually turns on are added.
SNAP_FEATURES = dict(sep.AUDIO_FEATURES) | {
    'skew_ms': '声峰到腕部冲击的时间差',
    'accel_peak_g': '腕部冲击峰值',
    'accel_hf_ratio': '冲击高频占比（60 Hz 以上）',
}
# A snap should sit above a clap on these; the self-test pins the directions so a sign
# flip fails loudly instead of quietly re-ranking the features.
SNAP_ABOVE_CLAP = {'crest': True, 'hf_ratio': True, 'decay_ms': False,
                   'accel_peak_g': False, 'accel_hf_ratio': True}


# ---------------------------------------------------------------- framing ----
def snap_header(connection, timeout=12, prefix='SNAP ', on_line=None):
    """Read the header line without swallowing the binary payload behind it.

    usb_emg.py reads the same way with its own prefix; the rule that earns this
    function -- never call readline on a stream whose next byte is payload -- is the
    same one for every batch-capture firmware."""
    line = bytearray()
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if not connection.in_waiting:
            time.sleep(.001)
            continue
        line.extend(connection.read(1))
        if len(line) > 160:
            raise ValueError('Oversized snap header')
        if line.endswith(b'\n'):
            text = line.decode('ascii', errors='replace').strip()
            if text.startswith('ERROR '):
                raise RuntimeError(text)
            if text.startswith(prefix):
                return text
            if on_line is not None: on_line(text)
            line.clear()
    raise TimeoutError('No snap header received')


def parse_header(header):
    fields = header.split()
    if len(fields) != 8 or fields[0] != 'SNAP':
        raise ValueError(f'Unexpected snap header: {header!r}')
    audio_hz, audio_n, audio_crc, accel_hz, accel_n, accel_crc, skew = fields[1:]
    if (int(audio_hz), int(audio_n), int(accel_hz), int(accel_n)) != (
            AUDIO_HZ, AUDIO_COUNT, ACCEL_HZ, ACCEL_FRAMES):
        raise ValueError(f'Unexpected capture geometry: {header!r}')
    return int(audio_crc, 16), int(accel_crc, 16), int(skew)


def validate(header, audio_bytes, accel_bytes):
    audio_crc, accel_crc, skew_us = parse_header(header)
    if len(audio_bytes) != AUDIO_COUNT * 2 or zlib.crc32(audio_bytes) != audio_crc:
        raise ValueError('Incomplete/corrupt PCM capture')
    if len(accel_bytes) != ACCEL_FRAMES * 6 or zlib.crc32(accel_bytes) != accel_crc:
        raise ValueError('Incomplete/corrupt accelerometer capture')
    if abs(skew_us) > 500000:
        raise ValueError(f'Implausible stream skew: {skew_us} us')
    return skew_us


# --------------------------------------------------------------- features ----
def _band_energy(segment, rate, low, high):
    spectrum = np.abs(np.fft.rfft(segment * np.hanning(len(segment)))) ** 2
    freqs = np.fft.rfftfreq(len(segment), 1 / rate)
    return float(spectrum[(freqs >= low) & (freqs < high)].sum())


def _peak_index(signal, rate, window_ms=2.0):
    width = max(1, int(rate * window_ms / 1000))
    smoothed = np.convolve(np.asarray(signal, float) ** 2, np.ones(width) / width, mode='same')
    return int(np.argmax(smoothed))


def snap_features(take):
    """(audio, accel, skew_us) -> separability.py's eight acoustic numbers plus the three
    this detector exists for: where the jolt landed relative to the sound, how hard, how fast."""
    audio, accel, skew_us = take
    audio = np.asarray(audio, float)
    acoustic = sep.audio_features(audio)

    magnitude = np.linalg.norm(np.asarray(accel, float) * ACCEL_G_PER_LSB, axis=1)
    dynamic = magnitude - float(np.median(magnitude))  # gravity is whatever the wrist held still at
    jolt = int(np.argmax(np.abs(dynamic)))
    window = dynamic[max(0, jolt - int(.06 * ACCEL_HZ)):jolt + int(.06 * ACCEL_HZ)]
    if len(window) < 16:
        window = dynamic
    low = _band_energy(window, ACCEL_HZ, 5, 60) or 1e-12
    return np.concatenate([acoustic, [
        # Positive: the wrist impact lands after the sound reaches the mic.
        (jolt / ACCEL_HZ + skew_us / 1e6 - _peak_index(audio, AUDIO_HZ) / AUDIO_HZ) * 1000,
        float(np.max(np.abs(dynamic))),
        _band_energy(window, ACCEL_HZ, 60, 400) / low,
    ]])


# ---------------------------------------------------------------- capture ----
def record(label, count, countdown=3):
    import serial
    from serial.tools import list_ports
    from upgrade import select_port
    from usb_client import wait_line

    port = select_port(list_ports.comports(), 0x8045)
    if not port:
        raise RuntimeError('Verified MAKO USB application is not connected')
    folder = DATA / label
    folder.mkdir(parents=True, exist_ok=True)

    with serial.Serial(port.device, 115200, timeout=.2, write_timeout=2, exclusive=True) as connection:
        time.sleep(2)
        connection.reset_input_buffer()
        connection.write(b'?\n')
        wait_line(connection, BANNER, timeout=5)
        for take in range(count):
            for remaining in range(countdown, 0, -1):
                print(f'\r[{take + 1}/{count}] {label}: {remaining}...', end='', flush=True)
                time.sleep(1)
            connection.reset_input_buffer()
            connection.write(b'r')
            wait_line(connection, 'RECORDING', timeout=3)
            print(f'\r[{take + 1}/{count}] {label}: NOW      ', end='', flush=True)
            header = snap_header(connection)
            payload = bytearray()
            want = AUDIO_COUNT * 2 + ACCEL_FRAMES * 6
            deadline = time.monotonic() + 25
            while len(payload) < want and time.monotonic() < deadline:
                payload.extend(connection.read(want - len(payload)))
            audio_bytes = bytes(payload[:AUDIO_COUNT * 2])
            accel_bytes = bytes(payload[AUDIO_COUNT * 2:])
            try:
                skew_us = validate(header, audio_bytes, accel_bytes)
            except ValueError as error:
                print(f'\r[{take + 1}/{count}] {label}: DROPPED ({error})')
                continue
            save(folder / f'{label}-{time.strftime("%Y%m%dT%H%M%S")}-{take:03d}',
                 audio_bytes, accel_bytes, skew_us, label, port.serial_number)
            print(f'\r[{take + 1}/{count}] {label}: saved (skew {skew_us / 1000:+.1f} ms)')
    print(f'{count} takes under {folder.resolve()}')


def save(stem, audio_bytes, accel_bytes, skew_us, label, serial_number):
    audio = np.frombuffer(audio_bytes, '<i2')
    accel = np.frombuffer(accel_bytes, '<i2').reshape(-1, 3)
    np.savez_compressed(stem.with_suffix('.npz'), audio=audio, accel=accel,
                        skew_us=skew_us, audio_hz=AUDIO_HZ, accel_hz=ACCEL_HZ, label=label)
    # A wav beside the npz so a mislabelled take can be caught by ear, not by eye.
    with wave.open(str(stem.with_suffix('.wav')), 'wb') as handle:
        handle.setparams((1, 2, AUDIO_HZ, len(audio), 'NONE', 'not compressed'))
        handle.writeframes(audio_bytes)
    stem.with_suffix('.json').write_text(json.dumps(
        dict(label=label, deviceSerial=serial_number, skewUs=skew_us,
             audioHz=AUDIO_HZ, accelHz=ACCEL_HZ, seconds=SECONDS), indent=2) + '\n')


# ----------------------------------------------------------------- report ----
def load(folder=DATA):
    """Takes in separability.report's record shape: {'label', 'x'}."""
    records = []
    for path in sorted(Path(folder).glob('*/*.npz')):
        with np.load(path, allow_pickle=False) as blob:
            records.append({'label': path.parent.name,
                            'x': (blob['audio'], blob['accel'], int(blob['skew_us']))})
    return records


def report(folder=DATA):
    records = load(folder)
    if not records:
        raise SystemExit(f'No takes under {Path(folder).resolve()} -- run --record first')
    counts = {}
    for record in records:
        counts[record['label']] = counts.get(record['label'], 0) + 1
    for label, total in sorted(counts.items()):
        print(f'{label}: {total} takes')

    verdict = sep.report(records, extract=snap_features, catalog=SNAP_FEATURES)
    print(f'\n{verdict["status"].upper()}: {verdict["message"]}')
    if verdict['pairs']:
        print(f'\n{"类别对":<22}{"混淆":>7}{"最能分开的":>26}{"d′":>7}{"重叠":>7}')
        for pair in verdict['pairs']:
            print(f'{" / ".join(pair["classes"]):<22}{pair["confusion"]:>6.0%}'
                  f'{pair["best_feature_label"]:>24}{pair["best_separation"]:>7.2f}'
                  f'{pair["best_feature_overlap"]:>7.0%}')
        scatter(records, verdict, folder)
    return verdict['status']


def scatter(records, verdict, folder):
    """The worst pair's best axis against the coincidence feature the gate is built on."""
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
    except ImportError:
        print('(matplotlib missing; table only)')
        return
    names = list(SNAP_FEATURES)
    x_name, y_name = verdict['pairs'][0]['best_feature'], 'skew_ms'
    x_index, y_index = names.index(x_name), names.index(y_name)
    figure, axes = plt.subplots(figsize=(6, 5))
    for label in sorted({r['label'] for r in records}):
        vectors = np.stack([snap_features(r['x']) for r in records if r['label'] == label])
        axes.scatter(vectors[:, x_index], vectors[:, y_index],
                     label=f'{label} (n={len(vectors)})', alpha=.75)
    axes.set_xlabel(f'{x_name} — {SNAP_FEATURES[x_name]}')
    axes.set_ylabel(f'{y_name} — {SNAP_FEATURES[y_name]}')
    axes.legend(); axes.grid(alpha=.3); figure.tight_layout()
    path = Path(folder) / 'scatter.png'
    figure.savefig(path, dpi=130)
    print(f'scatter: {path.resolve()}')


# ------------------------------------------------------------------ check ----
def _synth(kind, rng):
    """A crude physical caricature, only good enough to prove the math has signs."""
    audio = rng.normal(0, 30, AUDIO_COUNT)
    accel = rng.normal(0, 20, (ACCEL_FRAMES, 3))
    accel[:, 2] += 1.0 / ACCEL_G_PER_LSB  # gravity on Z
    hit = AUDIO_COUNT // 2
    time_axis = np.arange(AUDIO_COUNT) - hit
    if kind == 'snap':          # short, bright, small but fast wrist jolt
        tone, tau, gain, jolt_g, jolt_hz, jolt_tau = 3200, .004, 9000, 1.5, 120, .015
    else:                       # clap: duller, longer, big low-frequency deceleration
        tone, tau, gain, jolt_g, jolt_hz, jolt_tau = 1100, .020, 9000, 6.0, 25, .050
    mask = time_axis >= 0
    audio[mask] += gain * np.exp(-time_axis[mask] / (tau * AUDIO_HZ)) * \
        np.sin(2 * np.pi * tone * time_axis[mask] / AUDIO_HZ)
    frame_axis = np.arange(ACCEL_FRAMES) - ACCEL_FRAMES // 2
    jmask = frame_axis >= 0
    accel[jmask, 0] += (jolt_g / ACCEL_G_PER_LSB) * \
        np.exp(-frame_axis[jmask] / (jolt_tau * ACCEL_HZ)) * \
        np.sin(2 * np.pi * jolt_hz * frame_axis[jmask] / ACCEL_HZ)
    return np.clip(audio, -32768, 32767).astype('<i2'), np.clip(accel, -32768, 32767).astype('<i2')


def check():
    import io

    class Buffered(io.BytesIO):
        @property
        def in_waiting(self):
            return len(self.getbuffer()) - self.tell()

    audio_bytes = b'\0\1' * AUDIO_COUNT
    accel_bytes = b'\0\2' * (ACCEL_FRAMES * 3)
    header = (f'SNAP {AUDIO_HZ} {AUDIO_COUNT} {zlib.crc32(audio_bytes):x} '
              f'{ACCEL_HZ} {ACCEL_FRAMES} {zlib.crc32(accel_bytes):x} -1500')
    stream = Buffered(header.encode() + b'\r\n' + audio_bytes + accel_bytes)
    assert snap_header(stream) == header
    assert stream.read() == audio_bytes + accel_bytes, 'Header parser ate the payload'
    assert validate(header, audio_bytes, accel_bytes) == -1500

    for broken, why in [
        (header.replace(str(AUDIO_COUNT), '123', 1), 'wrong audio length'),
        (header.rsplit(' ', 1)[0] + ' 9000000', 'implausible skew'),
    ]:
        try:
            validate(broken, audio_bytes, accel_bytes)
        except ValueError:
            pass
        else:
            raise AssertionError(f'Bad header accepted: {why}')
    for bad in [audio_bytes[:-2], b'\1\1' + audio_bytes[2:]]:
        try:
            validate(header, bad, accel_bytes)
        except ValueError:
            pass
        else:
            raise AssertionError('Corrupt PCM accepted')
    assert struct.calcsize('<h') == 2

    rng = np.random.default_rng(20260917)
    records = [{'label': kind, 'x': (*_synth(kind, rng), 0)}
               for kind in ('snap', 'clap') for _ in range(12)]

    # Directions the whole design argument rests on. If these flip, the physics story in
    # ONDEVICE_LEARNING.md is wrong, not just the thresholds.
    names = list(SNAP_FEATURES)
    vectors = {kind: np.stack([snap_features(r['x']) for r in records if r['label'] == kind])
               for kind in ('snap', 'clap')}
    for name, snap_above in SNAP_ABOVE_CLAP.items():
        index = names.index(name)
        snapped, clapped = np.median(vectors['snap'][:, index]), np.median(vectors['clap'][:, index])
        assert (snapped > clapped) == snap_above, \
            f'{name}: snap={snapped:.3f} clap={clapped:.3f}, expected snap ' \
            f'{"above" if snap_above else "below"}'
    assert abs(np.median(vectors['snap'][:, names.index('skew_ms')])) < 30, 'streams drifted apart'

    # The gate has to agree these are two classes, and say so through separability.py's
    # own verdict shape -- so this gate and the web one can never disagree.
    verdict = sep.report(records, extract=snap_features, catalog=SNAP_FEATURES)
    assert verdict['status'] == 'ok', verdict['message']
    assert set(verdict['classes']) == {'snap', 'clap'}
    identical = [{'label': kind, 'x': (*_synth('clap', rng), 0)}
                 for kind in ('snap', 'clap') for _ in range(8)]
    assert sep.report(identical, extract=snap_features, catalog=SNAP_FEATURES)['status'] == 'block', \
        'two identical classes were called separable'

    print('snap framing, CRC, skew bounds and feature directions passed')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--check', action='store_true', help='offline self-test, no hardware')
    parser.add_argument('--record', metavar='LABEL', help='snap / clap / case_tap / ...')
    parser.add_argument('--count', type=int, default=30)
    parser.add_argument('--report', action='store_true')
    parser.add_argument('--data', type=Path, default=DATA)
    arguments = parser.parse_args()
    if arguments.check:
        check()
    elif arguments.record:
        record(arguments.record, arguments.count)
    elif arguments.report:
        sys.exit(0 if report(arguments.data) != 'STOP' else 1)
    else:
        parser.error('Use --check, --record LABEL or --report')

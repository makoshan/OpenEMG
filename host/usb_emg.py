"""Batch A for surface EMG: record labelled 2 s takes off the Cheez sEMG-D, then ask
the one question worth asking before any of it is built -- do these hand states look
different to a single wrist channel at all?

One dry-electrode channel on the forearm is not eight on an armband. It reads how hard
the flexors are working, not which finger moved, so the classes that survive are the
ones that differ in EFFORT and TIMING: rest / light / hard (the ADR's three tiers), not
index vs middle.
`pipeline.py gate --task emg` says which pairs collapsed and on which feature, and that
verdict is what decides whether there is a model here or just a threshold.

  python3 usb_emg.py --check                        # no hardware; feature math + framing
  python3 usb_emg.py --probe                        # live meter: place electrodes, learn L's polarity
  python3 usb_emg.py --record rest  --count 30      # 30 takes into emg-data/rest/
  python3 usb_emg.py --record light --count 30      # 轻握（授权）
  python3 usb_emg.py --record hard  --count 30      # 明显用力（确认）
  python3 usb_emg.py --record loose --count 10      # 松脱负样本：戴着但电极翘起，闸门必须不亮
  python3 pipeline.py gate --task emg               # the verdict

Wiring (ESP32-S3 DevKitC-1 bench rig, firmware/cheez-s3/; the module needs 5 V from USB):
  module V -> 5V pin (bridge the IN-OUT pad)   S -> GPIO4 through 1k   L -> GPIO5
  module G -> GND    plug the COM (CH340) USB-C   the one-piece three-bar pad (EMG+ / REF / EMG-, REF in the middle) sits on the
  forearm flexor belly with the bars along the muscle fibres; REF cannot be placed apart
"""
import argparse
import json
import time
import zlib
from pathlib import Path

import numpy as np

import separability as sep
from usb_snap import snap_header as read_header

BANNER = 'MAKO DAILY 1.usb-emg; USB-EMG-1'
RIG_VIDS = (0x2886, 0x303A, 0x1A86)   # Seeed XIAO; ESP32-S3 native USB / CH340 COM port (env emg_usb_s3)
EMG_HZ, SECONDS = 1000, 2
EMG_COUNT = EMG_HZ * SECONDS
FULL_SCALE_MV, ADC_MAX = 3600, 4096      # firmware/cheez-s3/src/emg_usb.cpp: 3.6 V full scale, 12 bit
DATA = Path('emg-data')

# The module swings 0-3.3 V, so it rails before the ADC does. Anything parked within
# 50 mV of either module rail is the front end saturating, not muscle.
RAIL_LOW = int(.05 / (FULL_SCALE_MV / 1000) * ADC_MAX)
RAIL_HIGH = int(3.25 / (FULL_SCALE_MV / 1000) * ADC_MAX)
RAIL_FRACTION = .01
# A take is worth keeping only if the electrodes were on the skin for all of it. 99%
# tolerates one glitchy sample on the wear line, not an electrode that peeled at 1.4 s.
WEAR_FLOOR = 990
# Motion artefact and baseline wander live below 20 Hz (ISEK's high-pass corner); muscle
# does not. A take whose sub-20 Hz power rivals its 20-450 Hz power is an arm that swung,
# a cable that tugged or an electrode that lifted -- and it sails through the wear and
# rail checks looking like a strong, clean contraction. 0 dB is set on synthetic takes
# (--check); re-set it from the first real rest / fist / punch takes, and if the module's
# own analogue high-pass already empties the band this check goes inert, not wrong.
SMR_FLOOR_DB = 0.

EMG_FEATURES = {
    'rms': '整段用力大小',
    'mav': '平均绝对幅值',
    'peak_rms': '最用力那 100 ms 的强度',
    'waveform_length': '波形长度（每样本的变化量，抖动与频率的合量）',
    'zero_crossings': '过零率（频率高低的代理）',
    'median_freq': '中值频率（疲劳与募集方式）',
    'hf_ratio': '100 Hz 以上能量占比',
    'onset_ms': '发力起始时刻',
    'rise_ms': '起始到峰值的时间',
    'hold_ratio': '包络维持在半峰以上的时间占比',
    'smr': '肌电对运动伪迹的功率比，dB（20–450 Hz 对 20 Hz 以下）',
}
# Directions the whole "one channel is enough for effort classes" argument rests on.
# hold_ratio is deliberately absent: a flat noise floor sits above half its own peak for
# the entire window, so relaxed takes score HIGHER than a one-second squeeze. That is
# correct and confusing, which is exactly why it is not a direction to pin.
FIST_ABOVE_REST = {'rms': True, 'mav': True, 'peak_rms': True,
                   'waveform_length': True, 'onset_ms': True}


# ---------------------------------------------------------------- framing ----
def _drain(connection):
    """Discard whatever is waiting by READING it. Never reset_input_buffer(): on macOS a
    tcflush after a CDC stall silences the port for good (AGENTS.md rule 5)."""
    while getattr(connection, 'in_waiting', 0):
        connection.read(connection.in_waiting)


MAX_GAP_US = 1500      # a 1 kHz take with any two samples further apart than this was not 1 kHz


# Firmware emits the first "S" line after samples 0..9. Its millis stamp is sample 9, not sample 0.
FIRST_PREVIEW_SAMPLE_INDEX = 9
LOG_TIMING_KEYS = (
    'max_gap_us', 'late', 'device_arm_us', 'prep_to_command_ms', 'command_to_ack_ms',
    'ack_to_cue_ms', 'cue_sample_index_estimate', 'device_clock_available',
    'preview_frames', 'preview_max_device_step_ms', 'preview_max_host_gap_ms',
)


def parse_header(header):
    """'EMG <hz> <n> <crc> <worn/1000> [<max_gap_us> <late> [<t0_ms> <arm_us>]]'.

    Five fields: firmware that did not report pacing. Seven: pacing only.
    Nine: device millis at sample 0, and microseconds from the command mark to that sample.
    Eight fields are a truncated header, not a quieter superset of seven."""
    fields = header.split()
    if len(fields) not in (5, 7, 9) or fields[0] != 'EMG':
        raise ValueError(f'Unexpected EMG header: {header!r}')
    hz, count, crc, worn = fields[1:5]
    if (int(hz), int(count)) != (EMG_HZ, EMG_COUNT):
        raise ValueError(f'Unexpected capture geometry: {header!r}')
    timing = {}
    if len(fields) >= 7:
        timing = {'max_gap_us': int(fields[5]), 'late': int(fields[6])}
    if len(fields) == 9:
        timing['device_t0_ms'] = int(fields[7])
        timing['device_arm_us'] = int(fields[8])
    return int(crc, 16), int(worn), timing


def cue_sample_index(ack_host_ns, shown_ms):
    """Legacy estimate from browser DOM-update time relative to the host ACK.

    Neither event measures physical screen presentation or the first ADC sample.
    A negative result describes host event ordering, not a truncated gesture.
    """
    return int(round((int(shown_ms) * 1_000_000 - int(ack_host_ns)) / 1_000_000))


def preview_continuity(frames):
    """frames are (device_ms, host_ns) for each preview line that actually arrived."""
    steps = [int(b[0]) - int(a[0]) for a, b in zip(frames, frames[1:])]
    host_ms = [(int(b[1]) - int(a[1])) / 1e6 for a, b in zip(frames, frames[1:])]
    out = {
        'preview_frames': len(frames),
        'preview_expected': EMG_COUNT // 10,
        'first_preview_sample_index': FIRST_PREVIEW_SAMPLE_INDEX if frames else None,
    }
    if steps:
        out['preview_max_device_step_ms'] = max(steps)
        out['preview_max_host_gap_ms'] = round(max(host_ms), 3)
    return out


def align_capture(firmware_timing, prep_host_ns=None, cue=None, previews=None):
    """Host-clock offsets for one take. Does not drop a take and does not clamp a negative index."""
    cue = cue or {}
    out = {}
    if prep_host_ns is not None:
        out['prep_host_ns'] = int(prep_host_ns)
    for key in ('command_sent_host_ns', 'recording_ack_host_ns'):
        if firmware_timing.get(key) is not None:
            out[key] = int(firmware_timing[key])
    if 'prep_host_ns' in out and 'command_sent_host_ns' in out:
        out['prep_to_command_ms'] = round((out['command_sent_host_ns'] - out['prep_host_ns']) / 1e6, 3)
    if 'command_sent_host_ns' in out and 'recording_ack_host_ns' in out:
        out['command_to_ack_ms'] = round((out['recording_ack_host_ns'] - out['command_sent_host_ns']) / 1e6, 3)
    if cue.get('pushed_host_ns') is not None:
        out['cue_pushed_host_ns'] = int(cue['pushed_host_ns'])
    ack = out.get('recording_ack_host_ns')
    if cue.get('shown_ms') is not None and ack is not None:
        shown = int(cue['shown_ms'])
        out['cue_shown_ms'] = shown
        out['ack_to_cue_ms'] = round(shown - ack / 1e6, 3)
        out['cue_sample_index_estimate'] = cue_sample_index(ack, shown)
        # Keep old sidecar consumers working; this field has never been a measured index.
        out['cue_sample_index'] = out['cue_sample_index_estimate']
        out['cue_sample_index_is_estimate'] = True
    if previews is not None:
        out.update(preview_continuity(previews))
    out['device_clock_available'] = all(
        firmware_timing.get(k) is not None for k in ('device_t0_ms', 'device_arm_us'))
    if cue and cue.get('phase_shown_ms'):
        out['cue_phase_shown_ms'] = dict(cue['phase_shown_ms'])
    out['cue_time_reference'] = 'browser_dom_update_wall_clock'
    out['sample_alignment_verified'] = False
    out['timing_reference'] = (
        'cue_sample_index and cue_sample_index_estimate are host-ACK-relative estimates at 1 kHz; '
        'browser DOM update is not measured screen presentation; '
        'device timestamps, when present, have no synchronized mapping to the host clock; '
        'physical gesture onset and end-to-end display latency are unmeasured'
    )
    return out


def timing_for_log(timing):
    return {key: timing[key] for key in LOG_TIMING_KEYS if timing.get(key) is not None}


def validate(header, payload, wear='high', quality_warnings=None):   # -> (worn, railed)
    """Reject the takes that arrive intact and still lie.

    A CRC proves 2000 samples survived the wire. It says nothing about whether they
    came off skin, and a peeled electrode produces a beautifully checksummed flat line
    that every feature below reads as 'relaxed'. These two checks are the whole reason
    the L pin is wired.
    """
    crc, worn, timing = parse_header(header)
    if timing and timing['max_gap_us'] > MAX_GAP_US:
        raise ValueError(f"采样不齐：最大间隔 {timing['max_gap_us']} us，迟到 {timing['late']} 次——固件没跟上 1 kHz")
    if len(payload) != EMG_COUNT * 2 or zlib.crc32(payload) != crc:
        raise ValueError('Incomplete/corrupt EMG capture')
    if wear != 'off':
        held = 1000 - worn if wear == 'low' else worn
        if held < WEAR_FLOOR:
            raise ValueError(f'电极没有全程贴合：{held / 10:.1f}%'
                             '（若一直是 0%，L 脚极性反了，用 --wear low）')
    counts = np.frombuffer(payload, '<i2')
    railed = float(np.mean((counts >= RAIL_HIGH) | (counts <= RAIL_LOW)))
    if railed > RAIL_FRACTION:
        raise ValueError(f'前级削顶 {railed * 100:.1f}%：降增益（板上 GAIN 焊盘）或挪电极')
    smr = emg_features((counts, worn))[list(EMG_FEATURES).index('smr')]
    if smr < SMR_FLOOR_DB:
        reason = f'低频能量偏高：SMR {smr:.2f} dB；需检查漂移、接触与动作时序'
        if quality_warnings is None:
            raise ValueError(reason)
        quality_warnings.append(reason)
    return worn, railed


# --------------------------------------------------------------- features ----
def _volts(counts):
    return np.asarray(counts, float) * (FULL_SCALE_MV / 1000) / ADC_MAX


def _envelope(signal, window_ms):
    width = max(1, int(EMG_HZ * window_ms / 1000))
    return np.sqrt(np.convolve(np.asarray(signal, float) ** 2, np.ones(width) / width, mode='same'))


MAINS_HZ = 50            # China; 60 elsewhere
NOTCH_BW_HZ = 2          # every harmonic gets the same 2 Hz notch, so 450 Hz is not a 15 Hz hole


def clean(x):
    """Legacy preprocessing retained for existing model weights (reflection can cause
    phase-dependent onset artefacts; clean_offline is an explicit offline alternative).
    The ADR chain: 20 Hz high-pass, then notches at every mains harmonic
    up to 450 Hz. CAUSAL (lfilter), same as the page and the phone will run it, so onsets are
    never pulled earlier than the muscle. A 2 Hz notch needs ~0.5 s to settle, so the take is
    first extended backwards by an odd reflection of its own start; the pad is dropped after."""
    from scipy.signal import butter, iirnotch, lfilter
    x = np.asarray(x, float)
    pad = min(len(x) - 1, 1000)
    y = np.concatenate([2 * x[0] - x[pad:0:-1], x])
    b, a = butter(2, 20 / (EMG_HZ / 2), 'high')
    y = lfilter(b, a, y)
    for k in range(1, int(450 // MAINS_HZ) + 1):
        b, a = iirnotch(MAINS_HZ * k, MAINS_HZ * k / NOTCH_BW_HZ, EMG_HZ)
        y = lfilter(b, a, y)
    return y[pad:]



def clean_offline(x):
    """Whole-trial harmonic subtraction + causal high-pass, not a live/onset filter.

    Fits only this trial's DC and 50 Hz harmonics, without reflected history.
    Whole-trial fitting uses future samples and can remove muscle energy at those
    exact frequencies. Keep legacy clean for old weights and streaming comparisons.
    """
    from scipy.signal import butter, sosfilt, sosfilt_zi
    x = np.asarray(x, dtype=float)
    if x.shape != (EMG_COUNT,) or not np.isfinite(x).all():
        raise ValueError('Expected finite 2 s EMG trial')
    t = np.arange(len(x)) / EMG_HZ
    columns = [np.ones(len(x))]
    for f in range(MAINS_HZ, 451, MAINS_HZ):
        columns.extend((np.sin(2*np.pi*f*t), np.cos(2*np.pi*f*t)))
    basis = np.column_stack(columns)
    # Integer cycles in exactly 2 s make these basis columns orthogonal.
    coefficients = np.sum(basis * x[:, None], axis=0) / np.sum(basis*basis, axis=0)
    residual = x - np.sum(basis * coefficients, axis=1)
    sos = butter(2, 20, 'highpass', fs=EMG_HZ, output='sos')
    return sosfilt(sos, residual, zi=sosfilt_zi(sos)*residual[0])[0]

def _mains_bins(freqs):
    return np.any([np.abs(freqs - MAINS_HZ * k) <= NOTCH_BW_HZ for k in range(1, int(450 // MAINS_HZ) + 1)], axis=0)


def mains_share(counts):
    """Fraction of the raw 20-450 Hz power sitting on mains harmonics. Not a classifier feature --
    hum changes with posture and with whatever the arm is near, so it would 'separate' classes
    recorded a minute apart -- only a quality number saved with the take."""
    x = _volts(counts); x = x - np.median(x)
    spectrum = np.abs(np.fft.rfft(x * np.hanning(len(x)))) ** 2
    freqs = np.fft.rfftfreq(len(x), 1 / EMG_HZ)
    band = (freqs >= 20) & (freqs <= 450)
    total = float(spectrum[band].sum())
    return float(spectrum[band & _mains_bins(freqs)].sum()) / total if total > 0 else 0.


def emg_features(take):
    """(counts, worn_permille) -> eleven named numbers: how hard, how fast, how long, how high, how clean.

    The 1.65 V bias is nominal and drifts with electrode contact and temperature, so the
    baseline is the take's own median, never the datasheet's number.
    """
    counts, _worn = take
    raw = _volts(counts)
    raw = raw - np.median(raw)
    # SMR judges the RAW take (motion artefact is what it is looking for); everything else reads
    # the cleaned signal, so 50 Hz hum can never pass for effort.
    spec_raw = np.abs(np.fft.rfft(raw * np.hanning(len(raw)))) ** 2
    freqs = np.fft.rfftfreq(len(raw), 1 / EMG_HZ)
    muscle = (freqs >= 20) & (freqs <= 450) & ~_mains_bins(freqs)
    low = float(spec_raw[freqs < 20].sum()); band_raw = float(spec_raw[muscle].sum())
    smr = min(10 * np.log10(band_raw / low), 60.) if band_raw > 0 and low > 0 else 60.
    x = clean(raw)
    rms = float(np.sqrt((x ** 2).mean()))

    envelope = _envelope(x, 100)
    peak = float(envelope.max())
    # Thresholds relative to the take's own peak: absolute microvolts mean nothing
    # across electrode placements, and this has to compare takes recorded days apart.
    above = envelope > .2 * peak if peak > 0 else np.zeros(len(x), bool)
    onset = int(np.argmax(above)) if above.any() else len(x)
    crest = int(np.argmax(envelope))

    spectrum = np.abs(np.fft.rfft(x * np.hanning(len(x)))) ** 2
    band = muscle                             # 20-450 Hz minus the mains notches
    power, f = spectrum[band], freqs[band]
    total = float(power.sum())
    median_freq = float(f[np.searchsorted(np.cumsum(power), total / 2)]) if total > 0 else 0.

    # Deadzone so a relaxed take's noise floor does not score as a 500 Hz signal.
    signs = np.sign(np.where(np.abs(x) < .1 * max(rms, 1e-9), 0, x))
    signs = signs[signs != 0]

    return np.array([
        rms,
        float(np.abs(x).mean()),
        peak,
        float(np.abs(np.diff(x)).mean()),
        float(np.count_nonzero(np.diff(signs) != 0)) * EMG_HZ / len(x),
        median_freq,
        float(power[f >= 100].sum()) / max(float(power[f < 100].sum()), 1e-12),
        onset * 1000 / EMG_HZ,
        max(crest - onset, 0) * 1000 / EMG_HZ,
        float(np.mean(envelope > .5 * peak)) if peak > 0 else 0.,
        float(smr),
    ], dtype=np.float64)


# ---------------------------------------------------------------- capture ----
def find_port(explicit=None):
    """Identify the rig by what it IS, not by which board it is.

    upgrade.py's select_port is locked to the 1.0 watch's serial on purpose, and this
    bench rig is deliberately some other XIAO -- plain or Sense, either works, the EMG
    firmware needs neither IMU nor mic. So ask each candidate what it is running.
    """
    import serial
    from serial.tools import list_ports
    ports = list_ports.comports()
    candidates = [p for p in ports if p.device == explicit] if explicit else \
                 [p for p in ports if p.vid in RIG_VIDS]
    for candidate in candidates:
        try:
            with serial.Serial(candidate.device, 115200, timeout=.2, write_timeout=2,
                               exclusive=True) as connection:
                time.sleep(2)              # CDC enumerates before the sketch is listening
                _drain(connection)
                connection.write(b'?')
                read_header(connection, timeout=3, prefix=BANNER)
                return candidate
        except (OSError, ValueError, TimeoutError, RuntimeError):
            continue
    raise RuntimeError('没找到跑 emg_usb 固件的板子：先 pio run -d firmware/cheez-s3 -e emg_usb_s3 -t upload 刷进去，或用 --port 指定')


class RejectedTake(ValueError):
    def __init__(self, reason, header, payload, timing=None):
        super().__init__(reason)
        self.header, self.payload, self.timing = header, payload, timing or {}


def read_take(connection, wear='high', preview=None, stream_only=False, on_received=None, on_started=None,
              prep_host_ns=None, cue=None, review_smr=False):
    """One 'r' round trip on an open connection: (counts, worn, railed, timing). Raises
    ValueError for a take that arrived and still has to be thrown away. emg_web.py's rig
    calls this too, so the web page and the CLI can never disagree about a take.

    `cue` is a dict the page fills with shown_ms while this call is blocked in the 2 s
    capture. Alignment is read from it after the samples arrive, not when the command goes out."""
    if stream_only and preview is None: raise ValueError('stream recording requires preview')
    if cue is None: cue = {}
    if not preview: _drain(connection)
    capture_timing = {'command_sent_host_ns': time.time_ns()}
    connection.write(b'V' if stream_only else b'R' if preview else b'r')
    read_header(connection, timeout=3, prefix='RECORDING', on_line=preview)
    capture_timing['recording_ack_host_ns'] = time.time_ns()
    if on_started: on_started(dict(capture_timing))
    payload = bytearray()
    previews = []
    def collect(line):
        if line.startswith('S '):
            host_ns = time.time_ns()
            device_ms = int(line.split()[1])
            previews.append((device_ms, host_ns))
            if 'first_preview_host_ns' not in capture_timing:
                capture_timing['first_preview_host_ns'] = host_ns
                capture_timing['first_preview_device_ms'] = device_ms
        if preview: preview(line)
        if stream_only and line.startswith('S '):
            values = [int(v) for v in line.split()[3:]]
            if len(values) != 10: raise ValueError('Invalid stream frame')
            payload.extend(np.asarray(values, dtype='<i2').tobytes())
    header = read_header(connection, timeout=SECONDS + 8,
                         prefix='EMGP ' if stream_only else 'EMG ', on_line=collect)
    if stream_only:
        header = 'EMG ' + header[5:]
    else:
        deadline = time.monotonic() + 15
        while len(payload) < EMG_COUNT * 2 and time.monotonic() < deadline:
            payload.extend(connection.read(EMG_COUNT * 2 - len(payload)))
    capture_timing['recording_received_host_ns'] = time.time_ns()
    if on_received: on_received()
    timing = {**parse_header(header)[2], **capture_timing}
    timing.update(align_capture(timing, prep_host_ns, cue, previews))
    try:
        warnings = [] if review_smr else None
        worn, railed = validate(header, bytes(payload), wear, **({'quality_warnings': warnings} if review_smr else {}))
        if review_smr:
            timing['quality_warnings'] = warnings
            timing['quality_status'] = 'review_required' if warnings else 'capture_checks_passed'
            timing['training_eligible'] = False
    except ValueError as e:
        raise RejectedTake(str(e), header, bytes(payload), timing) from e
    return np.frombuffer(bytes(payload), '<i2'), worn, railed, timing


def record(label, count, wear='high', countdown=3, port=None, data=DATA, session='', donning=0):
    import serial
    device = find_port(port)
    folder = Path(data) / label
    folder.mkdir(parents=True, exist_ok=True)
    kept = 0
    with serial.Serial(device.device, 115200, timeout=.2, write_timeout=2,
                       exclusive=True) as connection:
        time.sleep(2)
        _drain(connection)
        connection.write(b'?')
        read_header(connection, timeout=5, prefix=BANNER)
        for take in range(count):
            for remaining in range(countdown, 0, -1):
                print(f'\r[{take + 1}/{count}] {label}: {remaining}...', end='', flush=True)
                time.sleep(1)
            print(f'\r[{take + 1}/{count}] {label}: NOW      ', end='', flush=True)
            prep_ns = time.time_ns()
            # The terminal prints NOW before the board is asked to sample. The saved index
            # stays negative when that is true; it is not rewritten to look aligned.
            cue = {'shown_ms': prep_ns // 1_000_000, 'pushed_host_ns': prep_ns}
            try:
                counts, worn, railed, timing = read_take(connection, wear, prep_host_ns=prep_ns, cue=cue)
            except ValueError as error:
                print(f'\r[{take + 1}/{count}] {label}: DROPPED ({error})')
                continue
            save(folder / f'{label}-{time.strftime("%Y%m%dT%H%M%S")}-{take:03d}',
                 counts, worn, label, device.serial_number, session=session, donning=donning, timing=timing)
            kept += 1
            level = emg_features((counts, worn))[0] * 1000
            print(f'\r[{take + 1}/{count}] {label}: saved (rms {level:5.2f} mV, '
                  f'削顶 {railed * 100:.1f}%)')
    print(f'{kept}/{count} takes under {folder.resolve()}')
    if kept < count:
        print('丢掉的那些不是噪声，是贴合或增益问题——先 --probe 看稳了再补录')


def save(stem, counts, worn_permille, label, serial_number, session='', donning=0, timing=None):
    """session = who/when/where (free text), donning = how many times the strap has been put on
    tonight; both are what separates a training set from a rewear set later."""
    np.savez_compressed(stem.with_suffix('.npz'), emg=counts, worn_permille=worn_permille,
                        emg_hz=EMG_HZ, full_scale_mv=FULL_SCALE_MV, adc_max=ADC_MAX, label=label)
    stem.with_suffix('.json').write_text(json.dumps(
        dict(label=label, deviceSerial=serial_number, wornPermille=int(worn_permille),
             emgHz=EMG_HZ, seconds=SECONDS, fullScaleMv=FULL_SCALE_MV, sensor='Cheez sEMG-D',
             session=session, donning=int(donning), recordedAt=time.strftime('%Y-%m-%dT%H:%M:%S'),
             mainsShare=round(mains_share(counts), 3),
             **(timing or {})), indent=2) + '\n')


def probe(port=None):
    """Live meter until Ctrl-C. Two things to settle here before recording anything:
    the baseline holds still when the arm is relaxed, and `worn` flips when the strap
    comes off -- that flip is the only way to learn which level the L pin calls worn."""
    import serial
    device = find_port(port)
    with serial.Serial(device.device, 115200, timeout=.5, write_timeout=2,
                       exclusive=True) as connection:
        time.sleep(2)
        _drain(connection)
        connection.write(b'p')
        print('放松手臂看 mean 稳不稳，握拳看 span 涨不涨，摘下表带看 worn 跳不跳。Ctrl-C 结束。')
        try:
            while True:
                line = connection.readline().decode('ascii', errors='replace').strip()
                if line:
                    print(line, flush=True)
        except KeyboardInterrupt:
            connection.write(b'p')
            print()


# ----------------------------------------------------------------- report ----
def load(folder=DATA):
    """Takes in separability.report's record shape: {'label', 'x'}."""
    records = []
    for path in sorted(Path(folder).glob('*/*.npz')):
        with np.load(path, allow_pickle=False) as blob:
            records.append({'label': path.parent.name,
                            'x': (blob['emg'], int(blob['worn_permille']))})
    return records


# ------------------------------------------------------------------ check ----
def _bandnoise(count, low, high, rng):
    """White noise with everything outside [low, high] removed; peak-normalised."""
    spectrum = np.fft.rfft(rng.normal(0, 1, count))
    freqs = np.fft.rfftfreq(count, 1 / EMG_HZ)
    spectrum[(freqs < low) | (freqs > high)] = 0
    shaped = np.fft.irfft(spectrum, count)
    return shaped / max(float(np.abs(shaped).max()), 1e-9)


def _synth(kind, rng):
    """A crude caricature of one take, only good enough to prove the features have signs.

    Mains hum is in both classes on purpose: a feature that separates fist from rest
    only because one of them was recorded next to a charger has separated nothing.
    """
    t = np.arange(EMG_COUNT) / EMG_HZ
    volts = 1.65 + rng.normal(0, .003, EMG_COUNT) + .002 * np.sin(2 * np.pi * 50 * t)
    fist = np.clip(np.minimum((t - .5) / .08, (1.5 - t) / .08), 0, 1)
    if kind in ('fist', 'hard'):          # a firm one-second squeeze
        volts = volts + .25 * fist * _bandnoise(EMG_COUNT, 20, 150, rng)
    elif kind == 'light':               # same hold, a third of the effort: the ADR's middle tier
        volts = volts + .08 * fist * _bandnoise(EMG_COUNT, 20, 150, rng)
    elif kind == 'flick':        # same muscle, a quarter of the time
        shape = np.clip(np.minimum((t - .5) / .03, (.75 - t) / .03), 0, 1)
        volts = volts + .2 * shape * _bandnoise(EMG_COUNT, 20, 150, rng)
    elif kind == 'drift':        # the fist plus the arm swinging at 1 Hz, bigger than the burst
        volts = volts + .25 * fist * _bandnoise(EMG_COUNT, 20, 150, rng) + .6 * np.sin(2 * np.pi * t)
    return np.clip(np.round(volts / (FULL_SCALE_MV / 1000) * ADC_MAX),
                   0, ADC_MAX - 1).astype('<i2')


def check():
    import io

    class Buffered(io.BytesIO):
        @property
        def in_waiting(self):
            return len(self.getbuffer()) - self.tell()

    payload = b'\0\1' * EMG_COUNT
    header = f'EMG {EMG_HZ} {EMG_COUNT} {zlib.crc32(payload):x} 1000'
    stream = Buffered(header.encode() + b'\r\n' + payload)
    assert read_header(stream, prefix='EMG ') == header
    assert stream.read() == payload, 'Header parser ate the payload'
    assert validate(header, payload)[0] == 1000
    paced = header + ' 1010 0'
    assert parse_header(paced)[2] == {'max_gap_us': 1010, 'late': 0} and validate(paced, payload)[0] == 1000
    nine = paced + ' 12345 678'
    assert parse_header(nine)[2] == {
        'max_gap_us': 1010, 'late': 0, 'device_t0_ms': 12345, 'device_arm_us': 678}
    try:
        parse_header(paced + ' 1')
    except ValueError:
        pass
    else:
        raise AssertionError('8 字段的残缺头被当成合法头收了')
    assert cue_sample_index(1_700_000_000_000_000_000, 1_700_000_000_250) == 250
    assert cue_sample_index(1_700_000_000_000_000_000, 1_699_999_999_700) == -300, '提前的提示被收成 0'
    early = align_capture(
        {'command_sent_host_ns': 2_000_000_000, 'recording_ack_host_ns': 1_700_000_000_000_000_000},
        prep_host_ns=3_000_000_000,
        cue={'shown_ms': 1_699_999_999_700},
        previews=[])
    assert early['prep_to_command_ms'] == -1000.0, early
    assert early['cue_sample_index'] == -300, early
    assert 'cue_sample_index' not in align_capture(
        {'recording_ack_host_ns': 1_700_000_000_000_000_000}, cue={}, previews=[])
    jumped = preview_continuity([(0, 0), (10, 10_000_000), (90, 20_000_000)])
    assert jumped['preview_max_device_step_ms'] == 80, jumped
    assert jumped['preview_max_host_gap_ms'] == 10.0, jumped
    assert jumped['first_preview_sample_index'] == 9
    assert preview_continuity([])['first_preview_sample_index'] is None
    assert preview_continuity([])['preview_frames'] == 0

    class Port:
        def __init__(self, response):
            self.buf = bytearray()
            self.response = response
            self.written = b''
        def write(self, data):
            self.written += data
            self.buf.extend(self.response)
            return len(data)
        @property
        def in_waiting(self):
            return len(self.buf)
        def read(self, n=1):
            out = bytes(self.buf[:n])
            del self.buf[:n]
            return out

    samples = _synth('rest', np.random.default_rng(1))
    body = samples.tobytes()
    frame = 'S {ms} 10 ' + ' '.join(['2048'] * 10) + '\n'
    script = ('RECORDING 2\n' + frame.format(ms=5000) + frame.format(ms=5010) + frame.format(ms=5090)
              + f'EMG {EMG_HZ} {EMG_COUNT} {zlib.crc32(body):x} 1000 1005 0 4000 120\n').encode() + body
    seen = {}
    def started(timing):
        seen['ack'] = timing['recording_ack_host_ns']
    cue = {}
    def remember(timing):
        cue['shown_ms'] = timing['recording_ack_host_ns'] // 1_000_000 + 250
        cue['pushed_host_ns'] = timing['recording_ack_host_ns']
    port = Port(script)
    counts, worn, railed, timing = read_take(port, on_started=lambda timing: (started(timing), remember(timing)),
                                              prep_host_ns=1, cue=cue)
    assert port.written == b'r' and len(counts) == EMG_COUNT and worn == 1000
    assert timing['cue_sample_index'] == cue_sample_index(seen['ack'], cue['shown_ms']), timing
    assert abs(timing['cue_sample_index'] - 250) <= 1, timing
    assert timing['preview_frames'] == 3 and timing['preview_max_device_step_ms'] == 80, timing
    assert timing['first_preview_sample_index'] == 9 and timing['device_arm_us'] == 120, timing
    assert timing['preview_expected'] == 200
    try:
        validate(header + ' 2400 3', payload)
    except ValueError as error:
        assert '采样不齐' in str(error), error
    else:
        raise AssertionError('固件自报采样掉队的 take 被收了')

    for broken, why in [(header.replace(str(EMG_COUNT), '123', 1), 'wrong length'),
                        (header.replace('EMG', 'SNAP', 1), 'wrong sensor')]:
        try:
            validate(broken, payload)
        except ValueError:
            pass
        else:
            raise AssertionError(f'Bad header accepted: {why}')
    for bad in [payload[:-2], b'\1\1' + payload[2:]]:
        try:
            validate(header, bad)
        except ValueError:
            pass
        else:
            raise AssertionError('Corrupt capture accepted')

    # The two takes that arrive intact and still have to be thrown away. Without these
    # the L pin and the rail check are decoration.
    loose = f'EMG {EMG_HZ} {EMG_COUNT} {zlib.crc32(payload):x} 640'
    try:
        validate(loose, payload)
    except ValueError as error:
        assert '贴合' in str(error), error
    else:
        raise AssertionError('半程脱落的 take 被当成好数据收了')
    inverted = f'EMG {EMG_HZ} {EMG_COUNT} {zlib.crc32(payload):x} 5'
    try:
        validate(inverted, payload)
    except ValueError as error:
        assert '极性' in str(error), error
    else:
        raise AssertionError('极性反了的一整批被当成好数据收了')
    assert validate(inverted, payload, wear='low')[0] == 5, '--wear low 没有反过来读'
    railed = np.full(EMG_COUNT, ADC_MAX - 1, dtype='<i2').tobytes()
    try:
        validate(f'EMG {EMG_HZ} {EMG_COUNT} {zlib.crc32(railed):x} 1000', railed)
    except ValueError as error:
        assert '削顶' in str(error), error
    else:
        raise AssertionError('整段削顶的 take 被当成好数据收了')
    # Same burst twice: with the arm swinging it must go, without it must stay. Neither
    # the wear count nor the rail check can tell them apart -- that is what SMR is for.
    rng = np.random.default_rng(20260923)
    swung = _synth('drift', rng).tobytes()
    try:
        validate(f'EMG {EMG_HZ} {EMG_COUNT} {zlib.crc32(swung):x} 1000', swung)
    except ValueError as error:
        assert '漂移' in str(error), error
    else:
        raise AssertionError('手臂甩动的 take 被当成漂亮的发力收了')
    still = _synth('fist', rng).tobytes()
    assert validate(f'EMG {EMG_HZ} {EMG_COUNT} {zlib.crc32(still):x} 1000', still)[0] == 1000

    rng = np.random.default_rng(20260922)
    records = [{'label': kind, 'x': (_synth(kind, rng), 1000)}
               for kind in ('fist', 'rest') for _ in range(12)]
    names = list(EMG_FEATURES)
    vectors = {kind: np.stack([emg_features(r['x']) for r in records if r['label'] == kind])
               for kind in ('fist', 'rest')}
    for name, fist_above in FIST_ABOVE_REST.items():
        index = names.index(name)
        fist, rest = np.median(vectors['fist'][:, index]), np.median(vectors['rest'][:, index])
        assert (fist > rest) == fist_above, \
            f'{name}: fist={fist:.4f} rest={rest:.4f}, expected fist ' \
            f'{"above" if fist_above else "below"}'
    onset = np.median(vectors['fist'][:, names.index('onset_ms')])
    assert 400 < onset < 700, f'发力起点找偏了：{onset:.0f} ms，应在 500 ms 附近'

    # The gate has to agree these are two classes, through separability.py's own verdict
    # shape -- so this gate and pipeline.py's can never disagree about the same takes.
    verdict = sep.report(records, extract=emg_features, catalog=EMG_FEATURES)
    assert verdict['status'] == 'ok', verdict['message']
    assert set(verdict['classes']) == {'fist', 'rest'}
    # 20 a side: with 8, 1-NN on two identical clouds lands under the 20% confusion line by luck
    # often enough to flip this test with the seed.
    identical = [{'label': kind, 'x': (_synth('rest', rng), 1000)}
                 for kind in ('fist', 'rest') for _ in range(20)]
    assert sep.report(identical, extract=emg_features, catalog=EMG_FEATURES)['status'] == 'block', \
        'two identical classes were called separable'
    # Tried and rejected 2026-09-22: a "barely any signal" control -- a fist synthesised at
    # 0.004 V against a 0.003 V noise floor -- expecting the gate to refuse it. The gate
    # passes it, and is right to: the burst is band-limited 20-150 Hz while the floor is
    # white, so waveform_length and median_freq separate the two classes even when RMS
    # barely does. That is a real detection, not a false green. Where the floor actually
    # sits is a question for recorded takes, not for a synth that decides the answer.

    # Must fail without the notch: a relaxed arm under 150 mV of 50 Hz (+150 Hz) hum -- what the
    # first real session on 2026-09-23 looked like -- must read like rest, not like a squeeze.
    t = np.arange(EMG_COUNT) / EMG_HZ
    hum = .15 * np.sin(2 * np.pi * 50 * t) + .05 * np.sin(2 * np.pi * 150 * t)
    humming = np.clip(np.round((_volts(_synth('rest', rng)) + hum) / (FULL_SCALE_MV / 1000) * ADC_MAX), 0, ADC_MAX - 1).astype('<i2')
    rest_rms = np.median(vectors['rest'][:, 0]); fist_rms = np.median(vectors['fist'][:, 0])
    hum_rms = emg_features((humming, 1000))[0]
    assert hum_rms < 3 * rest_rms and hum_rms < fist_rms / 10, f'hum read as effort: {hum_rms:.4f} vs rest {rest_rms:.4f} fist {fist_rms:.4f}'
    assert mains_share(humming) > .9 and mains_share(_synth('fist', rng)) < .2
    print('EMG framing, wear/rail/drift rejection, mains notch, feature directions and gate agreement passed')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--check', action='store_true', help='offline self-test, no hardware')
    parser.add_argument('--probe', action='store_true', help='live meter for electrode placement')
    parser.add_argument('--record', metavar='LABEL', help='rest / fist / flick / ...')
    parser.add_argument('--count', type=int, default=30)
    parser.add_argument('--wear', choices=('high', 'low', 'off'), default='high',
                        help='L 脚哪个电平算戴上；--probe 里摘下表带就能看出来')
    parser.add_argument('--port', help='串口设备路径，默认按固件横幅自动找')
    parser.add_argument('--data', default=str(DATA), help='存到哪个根目录（重贴后录 emg-data-rewear）')
    parser.add_argument('--session', default='', help='一句话：谁、哪只手、电极贴哪')
    parser.add_argument('--donning', type=int, default=1, help='今晚第几次戴上（重贴一次 +1）')
    arguments = parser.parse_args()
    if arguments.check:
        check()
    elif arguments.probe:
        probe(arguments.port)
    elif arguments.record:
        record(arguments.record, arguments.count, arguments.wear, port=arguments.port,
               data=arguments.data, session=arguments.session, donning=arguments.donning)
    else:
        parser.error('Use --check, --probe or --record LABEL')

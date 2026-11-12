"""F01包→原始码+实际C滤波输出；只读本地记录，不连接设备。"""
from pathlib import Path
import argparse
import csv
import hashlib
import json
import sys
import tempfile
import numpy as np
from runtime import DSP, compile_library, ROOT

sys.path.insert(0, str(ROOT.parent / 'offline-f01'))
from codec import Receiver, decode_frame


def measured_sample_rate(clock_points, fs):
    """包头ISR时刻对样本序号最小二乘，斜率即实测周期；含中断延迟抖动，非时钟验收。"""
    rows = []
    for segment, points in sorted(clock_points.items()):
        span = points[-1][0] - points[0][0]
        row = dict(segment=segment, packets=len(points), sample_span=span,
                   measured_fs_Hz=None, deviation_ppm=None)
        # 少于两个不同序号无法定斜率，如实留空，不拿标称值顶替。
        if len(points) >= 2 and span > 0:
            x, t = (np.array(v, dtype=np.float64) for v in zip(*points))
            period_us = np.polyfit(x - x[0], t - t[0], 1)[0]
            row['measured_fs_Hz'] = round(1e6 / period_us, 3)
            row['deviation_ppm'] = round((1e6 / period_us / fs - 1) * 1e6, 1)
        rows.append(row)
    return rows


def replay(events, output, library, fs, notch=False, allow_real=False):
    output = Path(output)
    # 新输出目录，防止一次试验覆盖原始证据。
    output.mkdir(parents=True, exist_ok=False)
    dsp = DSP(library, fs, notch)
    period_us = 1000000 // fs
    receiver = Receiver(allow_real=allow_real)
    report = dict(status='回放完成，非实物验收', sample_rate_Hz=fs, notch=notch,
                  hardware_tested=False, rejected_events=[], resets=[], accepted_packets=0,
                  clipped_code_samples=0, timestamp_discontinuities=0,
                  synthetic_sessions=0, real_label_sessions=0,
                  timestamp_tolerance='半个名义周期+累计时间3%；临时筛查，非时钟验收')
    anchor_timestamp = None
    anchor_samples = None
    previous_timestamp = None
    previous_count = 0
    segment = 0
    # 每段收集「包首样本序号, 包头ISR时刻」，结束后拟合实测采样率；只进报告，不改时间戳。
    clock_points = {}
    with (output / 'samples.csv').open('w', newline='') as file:
        columns = ['session', 'segment', 'sequence', 'packet_timestamp_us', 'frame_offset',
                   'estimated_timestamp_us', 'synthetic', 'dsp_ready', 'raw_code_at_rail', 'status_word']
        columns += [f'raw{i}' for i in range(1, 9)] + [f'filtered_fs{i}' for i in range(1, 9)]
        writer = csv.writer(file)
        writer.writerow(columns)
        for index, event in enumerate(events):
            if event == {'disconnect': True}:
                receiver.disconnect()
                dsp.reset()
                anchor_timestamp = None
                anchor_samples = None
                previous_timestamp = None
                previous_count = 0
                continue
            # 对事件结构采用白名单，错误事件不会静默变成空包。
            if not isinstance(event, dict) or set(event) != {'packet_hex', 'mtu'}:
                report['rejected_events'].append(dict(index=index, reason='未知事件结构'))
                continue
            try:
                data = bytes.fromhex(event['packet_hex'])
                old_missing = receiver.missing_samples
                start = receiver.expected is None or bool(len(data)>3 and data[3]&4)
                p = receiver.receive(data, event['mtu'])
            except (ValueError, TypeError) as e:
                report['rejected_events'].append(dict(index=index, reason=str(e)))
                continue
            gap = receiver.missing_samples - old_missing
            # 按段累计核对，不能逐包重置参考时间，否则单帧包可掩盖错误采样率。
            # 3%频差预算只是候选筛查；包内等周期和真实时钟仍须台架验证。
            position = receiver.accepted_samples - len(p.frames) + receiver.missing_samples
            elapsed = (position-anchor_samples)*period_us if anchor_samples is not None else 0
            tolerance = period_us//2 + elapsed*3//100
            cumulative_break = anchor_timestamp is not None and abs(p.timestamp_us-(anchor_timestamp+elapsed)) > tolerance
            step = (previous_count+gap)*period_us
            adjacent_break = previous_timestamp is not None and abs(p.timestamp_us-(previous_timestamp+step)) > period_us//2+step*3//100
            # 相邻检查负责突跳，累计检查负责持续频差；二者都要保留。
            timing_break = not start and (cumulative_break or adjacent_break)
            if start or gap or timing_break:
                dsp.reset()
                segment += 1
                report['resets'].append(dict(index=index, segment=segment,
                                             reason='configuration' if p.flags&4 else 'session' if start else 'gap' if gap else 'timestamp',
                                             missing_samples=gap, timestamp_discontinuity=timing_break,
                                             cumulative_time_error=cumulative_break,
                                             adjacent_time_error=adjacent_break))
            if start or anchor_timestamp is None or timing_break:
                anchor_timestamp = p.timestamp_us
                anchor_samples = position
            if timing_break:
                report['timestamp_discontinuities'] += 1
            clock_points.setdefault(segment, []).append((position, p.timestamp_us))
            if start:
                key = 'synthetic_sessions' if receiver.synthetic else 'real_label_sessions'
                report[key] += 1
            decoded = [decode_frame(frame) for frame in p.frames]
            raw = np.array([codes for _, codes in decoded], dtype=np.int32)
            filtered, ready = dsp.process(raw)
            rail = np.any((raw == -8388608) | (raw == 8388607), axis=1)
            report['clipped_code_samples'] += int(rail.sum())
            for offset, ((status, codes), values) in enumerate(zip(decoded, filtered)):
                writer.writerow([receiver.sessions, segment, (p.sequence + offset) & 0xffffffff,
                                 p.timestamp_us, offset, p.timestamp_us + offset * period_us,
                                 int(receiver.synthetic), int(ready[offset]), int(rail[offset]), status,
                                 *codes, *[float(v) for v in values]])
            report['accepted_packets'] += 1
            previous_timestamp = p.timestamp_us
            previous_count = len(p.frames)
    report['configuration_boundaries'] = receiver.boundaries
    report['measured_sample_rate'] = measured_sample_rate(clock_points, fs)
    report.update(accepted_samples=receiver.accepted_samples, missing_samples=receiver.missing_samples,
                  reordered=receiver.reordered, malformed=receiver.malformed, sessions=receiver.sessions)
    report['source_sha256'] = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
                               for name in ('replay.py', 'runtime.py', 'v12_dsp.c', 'v12_dsp.h', 'coefficients.h')}
    report['protocol_sha256'] = hashlib.sha256((ROOT.parent / 'offline-f01/codec.py').read_bytes()).hexdigest()
    report['samples_sha256'] = hashlib.sha256((output / 'samples.csv').read_bytes()).hexdigest()
    (output / 'result.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('events', type=Path, help='JSONL：packet_hex+mtu或disconnect')
    parser.add_argument('output', type=Path, help='不存在的新输出目录')
    parser.add_argument('--fs', type=int, choices=(2000, 4000), required=True)
    parser.add_argument('--notch', action='store_true')
    parser.add_argument('--allow-real', action='store_true', help='接受真实标签；不认证记录来源')
    args = parser.parse_args()
    # 原始输入完整留存；解析错误不改变原文件。
    content = args.events.read_bytes()
    events = [json.loads(line) for line in content.decode().splitlines() if line.strip()]
    with tempfile.TemporaryDirectory(prefix='v12-dsp-replay-') as tmp:
        result = replay(events, args.output, compile_library(tmp), args.fs, args.notch, args.allow_real)
    (args.output / 'events.jsonl').write_bytes(content)
    result['input_sha256'] = hashlib.sha256(content).hexdigest()
    (args.output / 'result.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(result, ensure_ascii=False, indent=2))
    # 错包仍保留可用原始行和诊断，退出码明确未完整通过。
    return 2 if (result['rejected_events'] or result['timestamp_discontinuities'] or not result['accepted_samples']) else 0


if __name__ == '__main__':
    raise SystemExit(main())

"""F05 IMU原包与离线回放；单位换算为标称值，不构成校准或同步实测。"""
import argparse
import csv
from dataclasses import dataclass
import json
from pathlib import Path
import struct
import sys

HEADER = struct.Struct('<BBBBIQ')
PROFILE = dict(chip='LSM6DS3TR-C', odr_Hz=104, accel_range_g=8,
               gyro_range_dps=1000, accel_g_per_count=.000244, gyro_dps_per_count=.035,
               calibration_verified=False, alignment_verified=False,
               timestamp='MCU INT1 ISR', clock_source='TIMER2_1MHz', clock_resolution_us=1)


@dataclass(frozen=True)
class Packet:
    sequence: int
    timestamp_us: int
    flags: int
    frames: tuple[bytes, ...]


def decode(data, mtu=247):
    if type(mtu) is not int or not 23 <= mtu <= 517 or len(data) != 36 or len(data) > mtu-3:
        raise ValueError('IMU长度或MTU无效')
    version, kind, count, flags, seq, ts = HEADER.unpack_from(data)
    if (version, kind, count) != (1, 2, 1) or flags & ~7:
        raise ValueError('IMU版本、类型、计数或标志无效')
    if flags & 2 and seq != 0 or flags & 4 and not flags & 2:
        raise ValueError('IMU会话边界无效')
    if data[28] != 3 or data[29:32] != bytes(3) or struct.unpack_from('<I', data, 32)[0] >= 9000:
        raise ValueError('IMU新鲜度、保留字段或读取延迟无效')
    return Packet(seq, ts, flags, (bytes(data[16:]),))


def sample(frame):
    if len(frame) != 20:
        raise ValueError('IMU帧长度无效')
    raw = struct.unpack_from('<6h', frame)
    return dict(gyro_raw=raw[:3], accel_raw=raw[3:],
                gyro_dps=[v*PROFILE['gyro_dps_per_count'] for v in raw[:3]],
                accel_g=[v*PROFILE['accel_g_per_count'] for v in raw[3:]],
                status=frame[12], read_latency_us=struct.unpack_from('<I', frame, 16)[0])


def decode_status(data):
    if len(data) != 64:
        raise ValueError('IMU状态长度无效')
    if (data[0] != 1 or data[1] != 1 or data[2] not in (0, 1) or data[3] > 7 or
            data[4] not in (0, 0x6a) or data[5] != 8 or struct.unpack_from('<H', data, 6)[0] != 1000 or
            struct.unpack_from('<I', data, 8)[0] != 104 or data[12:16] != bytes((1, 0, 0, 0))):
        raise ValueError('IMU状态配置或保留字段无效')
    result = dict(active=bool(data[2]), fault=data[3], chip_id=data[4], alignment_verified=False)
    result.update(zip(('raw_edges', 'produced', 'sent', 'dropped', 'notify_failures', 'last_timestamp_us'),
                      struct.unpack_from('<6Q', data, 16)))
    if result['sent'] > result['produced']:
        raise ValueError('IMU发送计数大于产出计数')
    return result


def replay(directory, output, allow_real=False):
    from v12_ble import load_codec
    codec = load_codec()
    receiver = codec.Receiver(allow_real=allow_real, decoder=decode)
    # 原码和标称单位一起输出；保持独立时轴，不给未测同步误差一个假值。
    with Path(output).open('x', newline='') as out:
        writer = csv.writer(out)
        writer.writerow(['session', 'sequence', 'timestamp_ISR_us', 'gx_raw', 'gy_raw', 'gz_raw',
                         'ax_raw', 'ay_raw', 'az_raw', 'gx_dps', 'gy_dps', 'gz_dps',
                         'ax_g', 'ay_g', 'az_g', 'read_latency_us'])
        for line in (Path(directory)/'imu-events.jsonl').read_text().splitlines():
            event = json.loads(line)
            if event == dict(disconnect=True):
                receiver.disconnect()
                continue
            packet = receiver.receive(bytes.fromhex(event['packet_hex']), event['mtu'])
            decoded = sample(packet.frames[0])
            writer.writerow([receiver.sessions, packet.sequence, packet.timestamp_us,
                             *decoded['gyro_raw'], *decoded['accel_raw'], *decoded['gyro_dps'],
                             *decoded['accel_g'], decoded['read_latency_us']])
    if not receiver.accepted_samples:
        raise ValueError('没有有效IMU样本')
    return dict(samples=receiver.accepted_samples, missing_samples=receiver.missing_samples,
                sessions=receiver.sessions, boundaries=receiver.boundaries,
                calibration_verified=False, alignment_verified=False, hardware_verified=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--allow-real', action='store_true')
    args = parser.parse_args()
    try:
        print(json.dumps(replay(args.directory, args.out, args.allow_real), ensure_ascii=False, indent=2))
    except (ValueError, OSError, KeyError) as error:
        print(f'回放失败：{error}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())

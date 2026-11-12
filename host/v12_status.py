"""F05状态特征的离线解码；不会连接设备，也不把自报诊断当实物验收。"""
import argparse
import json
import struct


def decode_status(data):
    data = bytes(data)
    if len(data) not in (48, 64, 136, 163):
        raise ValueError('F05状态长度应为48、64、136或163字节')
    version = data[43]
    # v3（163 字节）= v2 + 寄存器快照：R01 dual 镜像在配置完、开连续读前读回的 0x00–0x19（TI 计划 S3）
    if (len(data), version) not in ((48, 0), (64, 1), (136, 2), (163, 3)):
        raise ValueError('F05状态版本与长度不一致')
    if data[41] not in (0, 1) or data[42] not in (0, 1):
        raise ValueError('F05状态布尔字段无效')
    names = ('produced', 'ring_dropped', 'scheduler_skipped', 'sent_samples', 'notify_failures')
    result = dict(zip(names, struct.unpack_from('<5Q', data)))
    result.update(status_version=version, fault=data[40], active=bool(data[41]),
                  bench_measured=bool(data[42]), ads_status=struct.unpack_from('<I', data, 44)[0],
                  drdy_raw_edges=None, drdy_min_interval_us=None, spi_Hz=None,
                  physical_device_verified=False)
    if version >= 1:
        edges, interval, spi = struct.unpack_from('<QII', data, 48)
        if spi not in (1_000_000, 2_000_000, 4_000_000, 8_000_000):
            raise ValueError('F05状态SPI速率不在候选范围')
        if (edges < 2) != (interval == 0xFFFFFFFF):
            raise ValueError('F05原始沿数与最短间隔不一致')
        result.update(drdy_raw_edges=edges, drdy_min_interval_us=None if interval == 0xFFFFFFFF else interval,
                      spi_Hz=spi)
    if version >= 2:
        fields = ('read_frames', 'isr_pending', 'stream_pending', 'hvn_pending',
                  'ring_peak', 'isr_peak', 'max_loop_gap_us', 'notify_resources',
                  'notify_other_errors', 'hvn_completed', 'last_hvx_error',
                  'rejected_frames', 'flow_phase', 'max_send_gap_us')
        result.update(zip(fields, struct.unpack_from('<Q6I3Q4I', data, 64)))
        if result['flow_phase'] > 4:
            raise ValueError('无效的停止/排空阶段')
    if version == 3:
        if data[136] not in (0, 1):
            raise ValueError('F05状态寄存器快照标志无效')
        # 没有有效快照（本次还没成功配置过）就给 None，不拿全 0 冒充寄存器值；解码用 host/ads1298_regs.py
        result.update(ads_regs_valid=bool(data[136]), ads_regs=data[137:163].hex() if data[136] else None)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('hex', help='状态特征完整十六进制值；48、64、136 或 163 字节')
    args = parser.parse_args()
    print(json.dumps(decode_status(bytes.fromhex(args.hex)), ensure_ascii=False, indent=2))

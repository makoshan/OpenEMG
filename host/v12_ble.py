"""V12 离体台架 BLE 入口：默认只读诊断，显式采集才发命令；不解除固件锁。"""
import argparse
import asyncio
import importlib.util
import json
import math
from pathlib import Path
import queue
import re
import sys
import time

from v12_raw import RawArchive
from v12_status import decode_status
import v12_imu

ROOT = Path(__file__).resolve().parent.parent
UUID_PREFIX = '7b24c101-3948-4f03-9d11-12bb9d'
SERVICE, DATA, META, STATUS, CONTROL = (UUID_PREFIX + f'{i:06d}' for i in range(1, 6))
IMU_DATA, IMU_STATUS = (UUID_PREFIX + f'{i:06d}' for i in (6, 7))
# IMU 联合采集要求两路用同一个 MCU 时钟打时间戳：F05（nRF52840）是 TIMER2，F05C（CH585M）是 SysTick。
IMU_CLOCKS = ('TIMER2_1MHz', 'CH585_SYSTICK')
COMMANDS = dict(test=b'TST1', short=b'SHT1', external=b'EXT1', rld=b'EXR1', rld_measure=b'RLD1')
ADS_PROFILES = ('F05_ADS_CANDIDATE', 'F05_ADS1292_2CH_CANDIDATE')


def load_codec():
    spec = importlib.util.spec_from_file_location('v12_ble_codec', ROOT / 'firmware/offline-f01/codec.py')
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def validate_metadata(raw, expected=None):
    meta = json.loads(bytes(raw))
    if not isinstance(meta, dict) or meta.get('profile') not in ADS_PROFILES:
        raise ValueError('设备不是受支持的 V12 ADS 候选固件')
    is_1292 = meta['profile'] == 'F05_ADS1292_2CH_CANDIDATE'
    spi_allowed = (1000000,) if is_1292 else (1000000, 2000000, 4000000, 8000000)
    proto_allowed = (1,) if is_1292 else (1, 2, 3)
    for key, values in dict(protocol=proto_allowed, channels=(8,), fs_Hz=(2000, 4000),
                            spi_Hz=spi_allowed).items():
        if type(meta.get(key)) is not int or meta[key] not in values:
            raise ValueError(f'固件元数据 {key} 无效')
    if is_1292:
        if meta.get('afe') != 'ADS1292':
            raise ValueError('ADS1292 候选固件元数据 afe 无效')
        if type(meta.get('active_channels')) is not int or meta['active_channels'] != 2:
            raise ValueError('ADS1292 候选固件元数据 active_channels 无效')
        if type(meta.get('vref_mV')) is not int or meta['vref_mV'] not in (2420, 4033):
            raise ValueError('ADS1292 候选固件元数据 vref_mV 无效')
        if type(meta.get('gain')) is not int or meta['gain'] not in (1, 2, 3, 4, 6, 8, 12):
            raise ValueError('ADS1292 候选固件元数据 gain 无效')
    if type(meta.get('bench_measured')) is not bool:
        raise ValueError('固件台架锁字段无效')
    if not isinstance(meta.get('build_id'), str) or not re.fullmatch('[0-9a-f]{16}', meta['build_id']):
        raise ValueError('固件构建 ID 无效')
    if expected is not None and meta['build_id'] != expected:
        raise ValueError('设备构建 ID 与预期镜像不一致')
    if meta['protocol'] != 1 and meta.get('pack16_copies') != meta['protocol'] - 1:
        raise ValueError('pack16 元数据与协议号不一致')
    if 'imu_enabled' in meta and type(meta['imu_enabled']) is not bool:
        raise ValueError('IMU开关元数据无效')
    return meta


FAULT_NOTES = {
    1: '台架锁未解开 Locked',
    2: '采样参数无效 Argument',
    3: '模拟电源/互锁异常 Rails：请确认已拔掉 USB 线且电池/3.0V AVDD 正常',
    4: 'ADS1298 芯片 ID 不匹配 Identity',
    5: 'ADS1298 寄存器读回不一致 Readback：EXR1 模式下注意 CONFIG3 bit0 RLD_STAT 只读位若为 1 会触发安全停机',
    6: 'ADS1298 数据帧状态头无效 Frame',
    8: 'DRDY 脉冲等待超时 Timeout',
    9: '采集被取消 Cancelled：采集中插入 USB 触发互锁或连接中断',
    10: '软件 VBUS 互锁触发 UsbInterlock：检测到 USB VBUS 供电，已拉低 PWDN 安全停机',
}


def format_adc_fault(status, meta):
    """按 ads1298.h / ads1292.h Fault 枚举给出明确中文原因，区分蓝牙链路吞吐低（7）、互锁（3/10）与读回（5）。"""
    fault = status['fault']
    slots = meta.get('queue_slots', 128)
    pending = status.get('stream_pending', 0)
    peak = status.get('ring_peak', 0)
    produced = status.get('produced', 0)
    sent = status.get('sent_samples', 0)
    if fault == 7 and (peak >= slots or pending >= slots // 2 or (produced > 0 and sent < produced and pending > 0)):
        return (f"设备故障码 7（蓝牙链路吞吐低：发送队列峰值 {peak}/{slots}、积压 {pending}，"
                f"已发 {sent}/{produced} 样；请将接收器移到 0.5m 内且勿隔人体）")
    note = FAULT_NOTES.get(fault)
    if note and meta.get('afe') == 'ADS1292':
        note = 'ADS1292 寄存器读回不一致 Readback' if fault == 5 else note.replace('ADS1298', 'ADS1292')
    return f"设备故障码 {fault}（{note}）" if note else f"设备故障码 {fault}"


def assert_adc_closure(status, result):
    """停机后核对ISR、发送队列、无线完成事件和主机归档，不用零计数冒充通过。"""
    if (status['flow_phase'] != 3 or status['active'] or status['fault'] or
            any(status[k] for k in ('isr_pending', 'stream_pending', 'hvn_pending',
                                    'rejected_frames', 'ring_dropped', 'scheduler_skipped',
                                    'notify_other_errors'))):
        raise RuntimeError('ADC 停止未排空或存在错误')
    if not (status['read_frames'] == status['produced'] == status['sent_samples'] == result['valid_samples'] > 0):
        raise RuntimeError('ADC 末尾计数不闭合：读取、入队、发送与主机接收不一致')
    if status['hvn_completed'] != result['packets']:
        raise RuntimeError('ADC 无线完成包数与主机接收不一致')


async def capture(client, output, seconds=5, mode=None, allow_real=False, expected=None,
                  queue_limit=1024, poll_seconds=1, archive_class=RawArchive, with_imu=False, on_first_data=None):
    """client 是 Bleak 的外部传输边界；测试只替换这个边界，不伪造内部状态。"""
    if not math.isfinite(seconds) or seconds <= 0 or not math.isfinite(poll_seconds) or poll_seconds <= 0:
        raise ValueError('时长与轮询间隔必须为正有限数')
    if type(queue_limit) is not int or queue_limit < 1:
        raise ValueError('接收队列大小无效')
    if mode is not None and (mode not in (*COMMANDS, 'imu') or not allow_real or expected is None):
        raise ValueError('采集需明确模式、--allow-real 和 --expected-build-id；仅限离体台架')
    if type(with_imu) is not bool or with_imu and mode is None:
        raise ValueError('IMU联合采集需明确采集模式')
    want_imu = with_imu or mode == 'imu'
    want_adc = mode is not None and mode != 'imu'
    codec = load_codec()
    # 先确认特征属于同一个服务，不能只凭广播名称向未知设备发控制命令。
    service = client.services.get_service(SERVICE)
    if service is None or not {DATA, META, STATUS, CONTROL}.issubset(
            {str(c.uuid).lower() for c in service.characteristics}):
        raise ValueError('设备缺少完整 V12 BLE 服务')
    raw_meta = bytes(await asyncio.wait_for(client.read_gatt_char(META), 10))
    meta = validate_metadata(raw_meta, expected)
    if mode == 'rld_measure' and meta['profile'] != 'F05_ADS1292_2CH_CANDIDATE':
        raise ValueError('rld_measure (RLD1) 仅适用于 ADS1292 两路候选固件')
    raw_status = bytes(await asyncio.wait_for(client.read_gatt_char(STATUS), 10))
    initial_status = decode_status(raw_status)
    if initial_status['bench_measured'] != meta['bench_measured']:
        raise ValueError('元数据与状态的台架锁不一致')
    if initial_status['spi_Hz'] is not None and initial_status['spi_Hz'] != meta['spi_Hz']:
        raise ValueError('元数据与状态的 SPI 不一致')
    if mode is not None and (want_adc and not meta['bench_measured'] or initial_status['active'] or initial_status['fault']):
        raise ValueError('固件仍锁定、已在采集或有故障；不发送启动命令')

    raw_imu_status = None
    if want_imu:
        if (not meta.get('imu_enabled') or meta.get('clock_source') not in IMU_CLOCKS or
                meta.get('clock_resolution_us') != 1 or not {IMU_DATA, IMU_STATUS}.issubset(
                    {str(c.uuid).lower() for c in service.characteristics})):
            raise ValueError('IMU候选通道或共同时间源未启用')
        raw_imu_status = bytes(await asyncio.wait_for(client.read_gatt_char(IMU_STATUS), 10))
        initial_imu = v12_imu.decode_status(raw_imu_status)
        if initial_imu['active'] or initial_imu['fault']:
            raise ValueError('IMU已活动或有故障，不启动')

    # 协议 2/3 的原包是差分打包，回放要用 codec.decode_pack16；ADS1292 按元数据 vref_mV/gain 归档，防止误按 4.0 V 放大 65.3%。
    if meta['profile'] == 'F05_ADS1292_2CH_CANDIDATE':
        archive_profile = dict(afe='ADS1292', active_channels=meta['active_channels'],
                               vref_V=meta['vref_mV'] / 1000.0, gain=meta['gain'],
                               fs_Hz=meta['fs_Hz'], transport_protocol=meta['protocol'],
                               reference_verified=False)
    else:
        archive_profile = dict(vref_V=4.0, gain=6, fs_Hz=meta['fs_Hz'],
                               transport_protocol=meta['protocol'], reference_verified=False)
    archive = archive_class(output, archive_profile, codec, allow_real)
    diag = None
    rx = codec.Receiver(allow_real=allow_real, decoder=codec.decode if meta['protocol'] == 1 else
                         lambda data, mtu: codec.decode_pack16(data, mtu, meta['protocol']))
    packet_limit = 232 if meta['protocol'] == 1 else 244
    incoming = queue.Queue(maxsize=queue_limit)
    imu_rx = codec.Receiver(allow_real=allow_real, decoder=v12_imu.decode)
    overflow = 0
    attempted = False
    subscriptions = []
    result = dict(state='运行中', mode=mode or 'status', build_id=meta['build_id'],
                  fs_Hz=meta['fs_Hz'], spi_Hz=meta['spi_Hz'], packets=0, valid_samples=0,
                  bad_packets=0, bad_status_frames=0, queue_overflow=0,
                  missing_samples=0, physical_device_verified=False, stop_confirmed=False)
    if want_imu:
        result.update(imu_packets=0, imu_samples=0, imu_bad_packets=0, imu_missing_samples=0,
                      imu_stop_confirmed=False, alignment_verified=False)
    failure = None
    final_imu = None
    stopped = None

    def diagnostic(event):
        diag.write(json.dumps(event, ensure_ascii=False) + '\n')
        diag.flush()

    first_data = []  # 首个 ADC 通知的主机时刻；R01 发 START 后约 5.9 s 才出样本（2026-10-29 实测）

    def receive(_, value, stream='adc'):
        nonlocal overflow
        if stream == 'adc' and not first_data:
            first_data.append(time.monotonic())
            if on_first_data is not None:
                on_first_data()
        # 回调只复制原始字节；队列满要报告未知缺口，不能阻塞蓝牙线程或悄悄丢弃。
        try:
            incoming.put_nowait((time.monotonic_ns(), bytes(value), stream))
        except queue.Full:
            overflow += 1

    def drain():
        first_error = None
        while not incoming.empty():
            stamp, packet, stream = incoming.get_nowait()
            reported = client.mtu_size
            if type(reported) is not int or not 23 <= reported <= 517:
                raise ValueError('传输返回无效 MTU')
            # macOS 可能只报告23；完整通知长度证明一个下界，不声称已读回协商MTU。
            mtu = max(reported, len(packet) + 3)
            event = dict(packet_hex=packet.hex(), mtu=mtu)
            if stream == 'imu':
                archive.write_imu(event)
            else:
                archive.write(event)
            diagnostic(dict(stream=stream, notification_ns=stamp, reported_mtu=reported, decode_mtu=mtu,
                            mtu_source='reported' if reported >= len(packet)+3 else 'notification_lower_bound'))
            if stream == 'imu':
                result['imu_packets'] += 1
                try:
                    parsed = imu_rx.receive(packet, mtu)
                    if parsed.flags & codec.SYNTHETIC:
                        raise ValueError('真实IMU入口收到了合成来源标记')
                    result['imu_samples'] += 1
                except ValueError as error:
                    result['imu_bad_packets'] += 1
                    diagnostic(dict(rejected_imu_packet=str(error)))
                    first_error = first_error or error
                continue
            result['packets'] += 1
            try:
                if len(packet) > packet_limit:
                    raise ValueError('超过 F05 通知上限')
                parsed = rx.receive(packet, mtu)
                if parsed.flags & codec.SYNTHETIC:
                    raise ValueError('真实 F05 入口收到了合成来源标记')
                bad = sum(f[0] >> 4 != 0xc for f in parsed.frames)
                result['bad_status_frames'] += bad
                result['valid_samples'] += len(parsed.frames) - bad
                if bad:
                    raise ValueError('ADS 状态字无效，原包已保存')
            except ValueError as error:
                result['bad_packets'] += 1
                diagnostic(dict(rejected_packet=str(error)))
                first_error = first_error or error
        if first_error is not None:
            raise first_error

    try:
        diag = (Path(output) / 'diagnostics.jsonl').open('x', encoding='utf-8')
        if want_imu:
            archive.enable_imu(dict(v12_imu.PROFILE, clock_source=meta['clock_source']))  # 归档如实记设备的时钟
            diagnostic(dict(imu_status_hex=raw_imu_status.hex(), imu_status=initial_imu))
        diagnostic(dict(metadata_hex=raw_meta.hex(), metadata=meta,
                        status_hex=raw_status.hex(), status=initial_status))
        if mode is not None:
            if want_adc:
                await asyncio.wait_for(client.start_notify(DATA, receive), 10)
                subscriptions.append(DATA)
            if want_imu:
                await asyncio.wait_for(client.start_notify(IMU_DATA, lambda u, v: receive(u, v, 'imu')), 10)
                subscriptions.append(IMU_DATA)
            # 写入失败也可能已经送到设备；退出时仍尝试 STOP，不能仅凭本地异常判断没启动。
            attempted = True
            await asyncio.wait_for(client.write_gatt_char(CONTROL, b'IMU1' if mode == 'imu' else COMMANDS[mode], response=True), 10)
        # 时长按“有数据的秒数”算，不含设备启动延迟；首包前最多多等 min(seconds, 15 s)
        deadline = time.monotonic() + seconds + (min(seconds, 15) if want_adc else 0)
        next_poll = 0
        while True:
            if first_data and want_adc:
                deadline = first_data[0] + seconds  # 先改写再判断，首包落在宽限末尾也采满
            if time.monotonic() >= deadline:
                break
            if not client.is_connected:
                raise ConnectionError('BLE 已断开；不自动重连拼接会话')
            drain()
            if overflow:
                raise RuntimeError('接收队列溢出；有未知缺口')
            if time.monotonic() >= next_poll:
                raw = bytes(await asyncio.wait_for(client.read_gatt_char(STATUS), 10))
                status = decode_status(raw)
                diagnostic(dict(status_hex=raw.hex(), status=status, host_ns=time.monotonic_ns()))
                if status['bench_measured'] != meta['bench_measured'] or (
                        status['spi_Hz'] is not None and status['spi_Hz'] != meta['spi_Hz']):
                    raise ValueError('运行中台架锁或 SPI 状态变化')
                if want_adc and status['ring_dropped']:
                    raise RuntimeError('设备 ADC 发送队列丢帧')
                if mode is not None and status['fault']:
                    raise RuntimeError(format_adc_fault(status, meta))
                if want_imu:
                    raw = bytes(await asyncio.wait_for(client.read_gatt_char(IMU_STATUS), 10))
                    current_imu = v12_imu.decode_status(raw)
                    diagnostic(dict(imu_status_hex=raw.hex(), imu_status=current_imu, host_ns=time.monotonic_ns()))
                    if current_imu['fault'] or current_imu['dropped']:
                        raise RuntimeError('IMU故障或丢样，不能记为联合采集成功')
                next_poll = time.monotonic() + poll_seconds
            await asyncio.sleep(min(.02, max(0, deadline-time.monotonic())))
        drain()
        if overflow:
            raise RuntimeError('接收队列溢出；有未知缺口')
        if want_imu and not result['imu_samples']:
            raise RuntimeError('没有有效IMU样本')
        if want_adc and not result['valid_samples']:
            raise RuntimeError('没有有效 ADC 样本；不能记为采集成功')
    except BaseException as error:
        failure = error
        result['error'] = str(error) or type(error).__name__
    finally:
        # 先停止设备，再取消订阅；等待状态读回，写了STOP不等于已停止。
        if attempted:
            try:
                await asyncio.wait_for(client.write_gatt_char(CONTROL, b'STOP', response=True), 3)
                stop_deadline = time.monotonic() + 3
                while True:
                    raw = bytes(await asyncio.wait_for(client.read_gatt_char(STATUS), 3))
                    stopped = decode_status(raw)
                    diagnostic(dict(stop_status_hex=raw.hex(), stop_status=stopped))
                    imu_stopped = True
                    if want_imu:
                        raw = bytes(await asyncio.wait_for(client.read_gatt_char(IMU_STATUS), 3))
                        final_imu = v12_imu.decode_status(raw)
                        diagnostic(dict(imu_stop_status_hex=raw.hex(), imu_stop_status=final_imu))
                        imu_stopped = not final_imu['active']
                        result['imu_stop_confirmed'] = imu_stopped
                        if final_imu['fault'] or final_imu['dropped']:
                            raise RuntimeError('IMU停止读回有故障或丢样')
                    if not stopped['active'] and imu_stopped:
                        result['stop_confirmed'] = True
                        break
                    if time.monotonic() >= stop_deadline:
                        raise RuntimeError('STOP 后设备仍活动')
                    await asyncio.sleep(.05)
            except BaseException as error:
                result['stop_error'] = str(error) or type(error).__name__
                failure = failure or error
        for uuid in subscriptions:
            try:
                await asyncio.wait_for(client.stop_notify(uuid), 3)
            except BaseException as error:
                result['unsubscribe_error'] = str(error) or type(error).__name__
                failure = failure or error
        if subscriptions:
            try:
                # STOP与取消订阅之间两路的尾包都必须归档，溢出不能假绿。
                drain()
                if overflow:
                    raise RuntimeError('停止期间接收队列溢出；有未知缺口')
            except BaseException as error:
                failure = failure or error
                result.setdefault('error', str(error) or type(error).__name__)
        if want_imu:
            result['imu_missing_samples'] = imu_rx.missing_samples
            if final_imu is not None:
                result['imu_final_status'] = final_imu
                if (final_imu['sent'] != result['imu_samples'] or
                        final_imu['produced'] != final_imu['sent']):
                    failure = failure or RuntimeError('IMU末尾计数不闭合：设备发送与电脑接收不一致')
                    result.setdefault('error', str(failure))
            if imu_rx.missing_samples:
                failure = failure or RuntimeError('IMU序号存在缺口')
                result.setdefault('error', str(failure))
        if want_adc:
            try:
                if rx.missing_samples:
                    raise RuntimeError('ADC 序号存在缺口')
                if stopped is not None:
                    result['adc_final_status'] = stopped
                    if stopped['fault'] and (
                            (isinstance(failure, ValueError) and '状态长度' in str(failure)) or
                            (isinstance(failure, RuntimeError) and '没有有效 ADC 样本' in str(failure))):
                        # 停止快照已记下明确硬件故障码（如 Rails=3、Readback=5、Overrun=7），不能被轮询状态截断或 0 样本笼统错误掩盖
                        failure = RuntimeError(f"{format_adc_fault(stopped, meta)}（前序异常：{failure}）")
                        result['error'] = str(failure)
                    if stopped['fault'] or stopped['ring_dropped'] or stopped['scheduler_skipped']:
                        raise RuntimeError(format_adc_fault(stopped, meta) if stopped['fault'] else 'ADC 停止末值有故障或丢样')
                result['adc_count_closure'] = '旧固件不支持停止快照'
                if meta.get('stop_snapshot') == 2:
                    if stopped is None or stopped['status_version'] < 2:  # v3 = v2 + 寄存器快照（R01 dual，TI 计划 S3）
                        raise RuntimeError('缺少新版 ADC 停止快照')
                    assert_adc_closure(stopped, result)
                    result['adc_count_closure'] = '闭合'
            except BaseException as error:
                failure = failure or error
                result.setdefault('error', str(error) or type(error).__name__)
        result.update(missing_samples=rx.missing_samples, queue_overflow=overflow,
                      state='失败' if failure else '只读诊断完成' if mode is None else '离体原始采集完成，未实物验收')
        try:
            archive.write(dict(disconnect=True))
            if want_imu and archive.imu_file is not None:
                archive.write_imu(dict(disconnect=True))
            (Path(output) / 'summary.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
        finally:
            archive.close()
            if diag is not None:
                diag.close()
    if failure:
        raise failure
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('status', 'capture'))
    parser.add_argument('--device', required=True, help='系统中的明确设备标识，不按名称自动选设备')
    parser.add_argument('--out', type=Path, required=True, help='新归档目录，拒绝覆盖已有记录')
    parser.add_argument('--seconds', type=float, default=5)
    parser.add_argument('--mode', choices=(*COMMANDS, 'imu'))
    parser.add_argument('--with-imu', action='store_true', help='两路分别归档，共同MCU时间但对齐未实测')
    parser.add_argument('--allow-real', action='store_true')
    parser.add_argument('--expected-build-id')
    args = parser.parse_args()
    if args.action == 'capture' and (not args.mode or not args.allow_real or not args.expected_build_id):
        parser.error('离体采集需 --mode、--allow-real、--expected-build-id；不会解除固件锁')
    if args.action == 'status' and (args.mode or args.allow_real or args.with_imu):
        parser.error('status 只读，不能指定采集模式或 --allow-real')
    if not math.isfinite(args.seconds) or args.seconds < .2:
        parser.error('--seconds 至少0.2且必须有限')
    if args.out.exists():
        parser.error('归档目录已存在，拒绝覆盖')

    async def run():
        try:
            from bleak import BleakClient
        except ImportError as error:
            raise RuntimeError('真实 BLE 入口需安装 bleak；不自动换成合成设备') from error
        async with BleakClient(args.device, timeout=10) as client:
            return await capture(client, args.out, args.seconds, args.mode,
                                 args.allow_real, args.expected_build_id, with_imu=args.with_imu)
    try:
        print(json.dumps(asyncio.run(run()), ensure_ascii=False, indent=2))
    except (OSError, ValueError, RuntimeError) as error:
        print(f'失败：{error}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())

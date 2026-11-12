"""离线验证生产 BLE 入口；仅在 Bleak 外部传输边界替身，无设备与人体。"""
import asyncio
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
from types import SimpleNamespace

import v12_ble as app
from v12_raw import RawArchive


class FakeClient:
    """按 F05 源码的 UUID、元数据与64字节状态组织，不代表实物时序。"""
    def __init__(self, packets=(), locked=False, fs=2000, disconnect=False,
                 fault=0, write_fail=False, stop_fail=False, tail=()):
        self.metadata = dict(profile='F05_ADS_CANDIDATE', build_id='0123456789abcdef',
                             protocol=1, channels=8, fs_Hz=fs, spi_Hz=2000000,
                             bench_measured=not locked)
        self.characteristics = [SimpleNamespace(uuid=u) for u in (app.DATA, app.META, app.STATUS, app.CONTROL)]
        self.services = SimpleNamespace(get_service=lambda u: self if u == app.SERVICE else None)
        self.is_connected = True
        self.mtu_size = 23  # macOS报告下界的分支必须真的跑过。
        self.packets, self.tail = packets, tail
        self.disconnect_after_start, self.fault_after_start = disconnect, fault
        self.write_fail, self.stop_fail = write_fail, stop_fail
        self.active = False
        self.fault = 0
        self.writes = []
        self.callback = None
        self.unsubscribed = False
        self.status_reads = 0

    async def read_gatt_char(self, uuid):
        if not self.is_connected:
            raise ConnectionError('替身断连')
        if uuid == app.META:
            return json.dumps(self.metadata).encode()
        assert uuid == app.STATUS
        self.status_reads += 1
        data = bytearray(64)
        data[40:44] = bytes((self.fault, int(self.active), int(self.metadata['bench_measured']), 1))
        struct.pack_into('<QII', data, 48, 0, 0xffffffff, self.metadata['spi_Hz'])
        return data

    async def start_notify(self, uuid, callback):
        assert uuid == app.DATA
        self.callback = callback

    async def write_gatt_char(self, uuid, value, response):
        assert uuid == app.CONTROL and response
        self.writes.append(value)
        if not self.is_connected:
            raise ConnectionError('替身断连')
        if value == b'STOP':
            if self.stop_fail:
                raise OSError('STOP传输失败')
            self.active = False
            self.fault = 0
            for packet in self.tail:
                self.callback(None, bytearray(packet))
        else:
            self.active = True
            for packet in self.packets:
                self.callback(None, bytearray(packet))
            self.fault = self.fault_after_start
            if self.disconnect_after_start:
                self.is_connected = False
            if self.write_fail:
                raise OSError('启动写入返回失败，但设备可能已收到')

    async def stop_notify(self, uuid):
        assert uuid == app.DATA
        self.unsubscribed = True



class LateStartClient(FakeClient):
    """START 后隔一段才出首包，模拟 R01 约 5.9 s 启动延迟（这里缩成 0.05 s，在 min(seconds,15) 宽限内）。"""
    async def write_gatt_char(self, uuid, value, response):
        if value == b'STOP':
            return await super().write_gatt_char(uuid, value, response)
        self.writes.append(value)
        self.active = True
        loop = asyncio.get_running_loop()
        for packet in self.packets:
            loop.call_later(.05, self.callback, None, bytearray(packet))


class FakeAds1292Client(FakeClient):
    """按 xiao-ads1292-2ch/src/main.cpp 元数据与 64 字节状态组织（2.42V/增益6/1MHz SPI/两路补八路帧）。"""
    def __init__(self, packets=(), locked=False, fs=2000, **kwargs):
        super().__init__(packets=packets, locked=locked, fs=fs, **kwargs)
        self.metadata = dict(
            profile='F05_ADS1292_2CH_CANDIDATE', board='ADS1292_2CH_P44E', afe='ADS1292',
            build_id='0123456789abcdef', fs_Hz=fs, spi_Hz=1000000,
            channels=8, active_channels=2, vref_mV=2420, gain=6,
            bench_measured=not locked, protocol=1, clock_tolerance_pct=2.0,
            usb_interlock='HW_Q1_AND_SW_USBREGSTATUS', clock_source='TIMER2_1MHz',
        )


def packets_1292(fs=2000):
    codec = app.load_codec()
    # CH1=+123456、CH2=-654321、CH3..CH8=0；状态头 0xc01021（IN1P=1, IN2N=1, GPIO=1）
    vals = (123456, -654321, 0, 0, 0, 0, 0, 0)
    frame = bytes.fromhex('c01021') + b''.join(v.to_bytes(3, 'big', signed=True) for v in vals)
    return [codec.encode(codec.Packet(0, 10000, 2, (frame,))),
            codec.encode(codec.Packet(1, 10000 + (1000000 // fs), 0, (frame,)))]


class SnapshotClient(FakeClient):
    """新协议136字节：只在传输边界造状态，归档和末值验收走真实入口。"""
    def __init__(self, patch=None):
        super().__init__(packets())
        self.metadata['stop_snapshot'] = 2
        self.patch = patch

    async def read_gatt_char(self, uuid):
        data = await super().read_gatt_char(uuid)
        if uuid != app.STATUS:
            return data
        data = bytearray(data) + bytearray(72)
        data[43] = 2
        if self.writes:
            struct.pack_into('<5Q', data, 0, 2, 0, 0, 2, 5)
            struct.pack_into('<QII', data, 48, 2, 500, 2000000)
            struct.pack_into('<Q6I3Q4I', data, 64, 2, 0, 0, 0, 8, 2, 100,
                             5, 0, 2, 0, 0, 1 if self.active else 3, 4000)
            if not self.active and self.patch:
                offset, value, size = self.patch
                data[offset:offset+size] = value.to_bytes(size, 'little')
        return data


def packets(fs=2000, bad_status=False):
    codec = app.load_codec()
    frame = bytes.fromhex('c00007') + b''.join(i.to_bytes(3, 'big', signed=True) for i in range(-4, 4))
    if bad_status:
        frame = bytes(27)
    # 非零序号、负24位码、连续序号与4k刻度都走生产编码器。
    return [codec.encode(codec.Packet(0, 10000, 2, (frame,))),
            codec.encode(codec.Packet(1, 10000+1*(1000000//fs), 0, (frame,)))]


def check():
    passed = 0
    with tempfile.TemporaryDirectory(prefix='v12-ble-check-') as directory:
        root = Path(directory)

        def drive(name, client, success=True, mode='short', archive_class=RawArchive, **options):
            nonlocal passed
            output = root / name
            try:
                result = asyncio.run(app.capture(client, output, seconds=.03,
                    mode=mode, allow_real=mode is not None, expected='0123456789abcdef',
                    poll_seconds=.005, archive_class=archive_class, **options))
            except (OSError, ValueError, RuntimeError):
                assert not success, name
                result = json.loads((output / 'summary.json').read_text()) if (output/'summary.json').exists() else None
                if result:
                    assert result['state'] == '失败', result
            else:
                assert success, name
                assert result['physical_device_verified'] is False
            passed += 1
            return output, result

        for fs in (2000, 4000):
            client = FakeClient(packets(fs), fs=fs)
            out, result = drive(f'valid-{fs}', client)
            assert result['valid_samples'] == 2 and result['missing_samples'] == 0
            assert result['fs_Hz'] == fs and result['stop_confirmed']
            assert client.writes == [b'SHT1', b'STOP'] and client.unsubscribed
            events = [json.loads(line) for line in (out/'events.jsonl').read_text().splitlines()]
            assert events[0]['packet_hex'] == packets(fs)[0].hex()
            assert events[-1] == {'disconnect': True}
            assert app.load_codec().decode_frame(app.load_codec().decode(bytes.fromhex(events[0]['packet_hex']), events[0]['mtu']).frames[0])[1][0] == -4
            diag = (out/'diagnostics.jsonl').read_text()
            assert 'notification_lower_bound' in diag and 'stop_status_hex' in diag
            assert json.loads((out/'metadata.json').read_text())['hardware_verified'] is False

        # 时长从首个样本起算：首包晚到 0.05 s，采集要在首包后正好再跑 0.1 s（不对齐会是 0.15 s）
        import time
        hits = []
        result = asyncio.run(app.capture(LateStartClient(packets()), root / 'late-start', seconds=.1, mode='short',
            allow_real=True, expected='0123456789abcdef', poll_seconds=.005,
            on_first_data=lambda: hits.append(time.monotonic())))
        after = time.monotonic() - hits[0]
        assert len(hits) == 1 and result['valid_samples'] == 2, (hits, result)
        assert .1 <= after < .2, after
        passed += 1

        _, result = drive('snapshot-valid', SnapshotClient())
        assert result['adc_count_closure'] == '闭合'
        # 状态 v3（R01 dual，TI 计划 S3）= v2 + 寄存器快照：停机快照照样闭合，快照随末值状态归档
        regs = bytes([0x92, 0x84, 0, 0xE0] + [0x01] * 8 + [0] * 8 + [0x0F, 0, 0x20, 0, 0, 0])

        class SnapshotV3Client(SnapshotClient):
            async def read_gatt_char(self, uuid):
                data = await super().read_gatt_char(uuid)
                if uuid != app.STATUS:
                    return data
                data = bytearray(data) + bytes([1]) + regs
                data[43] = 3
                return data
        _, result = drive('snapshot-v3', SnapshotV3Client())
        assert result['adc_count_closure'] == '闭合' and result['adc_final_status']['ads_regs'] == regs.hex(), result
        passed += 1
        for name, patch in (
                ('stop-zero', (0, 0, 8)), ('tail-unread', (64, 3, 8)),
                ('isr-tail', (72, 1, 4)), ('stream-tail', (76, 1, 4)),
                ('hvn-tail', (80, 1, 4)), ('notify-error', (104, 1, 8)),
                ('missing-complete', (112, 1, 8)), ('rejected', (124, 1, 4)),
                ('incomplete', (128, 4, 4)), ('stop-fault', (40, 8, 1))):
            drive(name, SnapshotClient(patch), success=False)

        broken = packets()
        codec = app.load_codec()
        parsed = codec.decode(broken[1], 247)
        broken[1] = codec.encode(codec.Packet(2, 11000, 0, parsed.frames))
        _, result = drive('gap-refused', FakeClient(broken), success=False)
        assert result['missing_samples'] == 1

        client = FakeClient(locked=True)
        _, result = drive('status-only', client, mode=None)
        assert client.writes == [] and client.callback is None and client.status_reads >= 2
        assert result['state'] == '只读诊断完成' and not result['stop_confirmed']
        client = FakeClient(locked=True)
        drive('locked', client, success=False)
        assert client.writes == []
        client = FakeClient();client.metadata['build_id'] = 'f'*16
        drive('wrong-build', client, success=False)
        assert client.writes == []
        client = FakeClient();client.characteristics.pop()
        drive('missing-service', client, success=False)
        assert client.writes == []
        for field, value in [('channels', True), ('fs_Hz', 3000), ('protocol', 2),
                             ('spi_Hz', 3000000), ('bench_measured', 1), ('build_id', 'bad')]:
            client = FakeClient();client.metadata[field] = value
            drive(f'bad-meta-{field}', client, success=False)
            assert client.writes == []

        for mode, command in app.COMMANDS.items():
            if mode == 'rld_measure':
                client = FakeClient(packets())
                drive('r01-refuse-rld1', client, mode=mode, success=False)
                assert client.writes == []
                continue
            client = FakeClient(packets())
            drive('mode-'+mode, client, mode=mode)
            assert client.writes == [command, b'STOP']

        # ADS1292+P44e+XIAO 候选固件：5 种模式（含 RLD1）、2.42V 归档刻度、C 离线回放与专有元数据/故障码拦截
        for mode, command in app.COMMANDS.items():
            c1292 = FakeAds1292Client(packets_1292())
            out1292, res1292 = drive('ads1292-mode-' + mode, c1292, mode=mode)
            assert c1292.writes == [command, b'STOP'] and res1292['valid_samples'] == 2
            meta1292 = json.loads((out1292 / 'metadata.json').read_text())
            assert meta1292['voltage_at'] == 'ADS1292 PGA input', meta1292
            assert meta1292['adc_profile'] == dict(
                afe='ADS1292', active_channels=2, vref_V=2.42, gain=6,
                fs_Hz=2000, transport_protocol=1, reference_verified=False), meta1292
        c1292_4k = FakeAds1292Client(packets_1292(4000), fs=4000)
        out1292_4k, _ = drive('ads1292-4000', c1292_4k, mode='rld_measure')
        replay = (app.ROOT / 'firmware/dsp-f03/replay.py' if (app.ROOT / 'firmware/dsp-f03/replay.py').exists()
                  else app.ROOT / 'v12/dsp-f03/replay.py')
        rep_refused = subprocess.run([sys.executable, str(replay), str(out1292_4k / 'events.jsonl'),
                                      str(root / 'ads1292-replay-refused'), '--fs', '4000'],
                                     capture_output=True, text=True, timeout=30)
        assert rep_refused.returncode == 2  # 默认不加 --allow-real 必须拒收实采标签
        rep_run = subprocess.run([sys.executable, str(replay), str(out1292_4k / 'events.jsonl'),
                                  str(root / 'ads1292-replay'), '--fs', '4000', '--allow-real'],
                                 capture_output=True, text=True, timeout=30)
        assert rep_run.returncode == 0, rep_run.stderr
        rep_res = json.loads((root / 'ads1292-replay/result.json').read_text())
        assert rep_res['accepted_samples'] == 2 and rep_res['measured_sample_rate'][0]['measured_fs_Hz'] == 4000.0
        passed += 1
        for field, value in [('spi_Hz', 2000000), ('afe', 'ADS1298'), ('active_channels', 8),
                             ('active_channels', True), ('vref_mV', 4000), ('vref_mV', True),
                             ('gain', 5), ('gain', True), ('protocol', 2)]:
            bad1292 = FakeAds1292Client(packets_1292())
            bad1292.metadata[field] = value
            drive(f'ads1292-bad-{field}-{value}', bad1292, success=False)
            assert bad1292.writes == []
        _, f10 = drive('ads1292-fault10-usb', FakeAds1292Client(packets_1292(), fault=10), success=False)
        assert '设备故障码 10' in f10['error'] and 'UsbInterlock' in f10['error'], f10['error']
        _, f5 = drive('ads1292-fault5-readback', FakeAds1292Client(packets_1292(), fault=5), success=False)
        assert 'ADS1292 寄存器读回不一致' in f5['error'] and 'ADS1298' not in f5['error'], f5['error']
        # 坏包后排队的原包也保存；只拒解析，不让证据跟着异常丢失。
        client = FakeClient([b'bad'] + packets())
        out, result = drive('malformed', client, success=False)
        assert result['bad_packets'] >= 1 and result['packets'] == 3
        assert json.loads((out/'events.jsonl').read_text().splitlines()[0])['packet_hex'] == b'bad'.hex()
        client = FakeClient(packets(bad_status=True))
        _, result = drive('bad-status', client, success=False)
        assert result['bad_status_frames'] == 2 and result['valid_samples'] == 0
        synthetic = bytearray(packets()[0]);synthetic[3] |= 1
        drive('synthetic-refused', FakeClient([synthetic]), success=False)
        drive('duplicate', FakeClient([packets()[0]]*2), success=False)
        _, result = drive('empty', FakeClient(), success=False)
        assert result['valid_samples'] == 0
        client = FakeClient(packets(), disconnect=True)
        out, result = drive('disconnect', client, success=False)
        assert result['stop_confirmed'] is False and 'stop_error' in result
        assert len((out/'events.jsonl').read_text().splitlines()) == 3
        _, result = drive('fault', FakeClient(packets(), fault=3), success=False)
        assert '设备故障码 3' in result['error']
        # 蓝牙链路吞吐过低（如接收器距离 5m / 隔人体）致发送队列积压触发 fault=7，必须直接报蓝牙链路吞吐低与积压计数
        class CongestedClient(SnapshotClient):
            def __init__(self, truncate_poll=False):
                super().__init__()
                self.metadata['queue_slots'] = 2048
                self.truncate_poll = truncate_poll
            async def read_gatt_char(self, uuid):
                data = await super().read_gatt_char(uuid)
                if uuid != app.STATUS or not self.writes:
                    return data
                if self.active and self.truncate_poll:
                    return bytearray(22)  # MTU 23->247 切换或拥塞导致轮询状态被截断
                data[40] = 7  # Fault::Overrun
                struct.pack_into('<5Q', data, 0, 2192, 0, 0, 296, 0)
                struct.pack_into('<Q6I3Q4I', data, 64, 2192, 0, 1896, 16, 2048, 16, 504,
                                 0, 0, 21, 0, 0, 2 if self.active else 4, 1520278)
                return data
        _, result = drive('congested-fault7', CongestedClient(), success=False)
        assert '设备故障码 7' in result['error'] and '蓝牙链路吞吐低' in result['error'] and '296/2192' in result['error'], result['error']
        _, result = drive('congested-truncated-poll', CongestedClient(truncate_poll=True), success=False)
        assert '蓝牙链路吞吐低' in result['error'] and '296/2192' in result['error'], result['error']
        # EXR1 启动阶段若触发 Readback(5) 或 Rails(3) 致 0 样本停机，停止快照里的故障码必须覆盖“没有有效 ADC 样本”
        class StartupFaultZeroSampleClient(SnapshotClient):
            def __init__(self, fault_code):
                super().__init__()
                self.packets = []
                self.fault_code = fault_code
            async def read_gatt_char(self, uuid):
                data = await super().read_gatt_char(uuid)
                if uuid == app.STATUS and self.writes and not self.active:
                    data[40] = self.fault_code
                return data
        _, result = drive('startup-fault5-readback', StartupFaultZeroSampleClient(5), success=False)
        assert '设备故障码 5' in result['error'] and 'Readback' in result['error'], result['error']
        _, result = drive('startup-fault3-rails', StartupFaultZeroSampleClient(3), success=False)
        assert '设备故障码 3' in result['error'] and 'Rails' in result['error'], result['error']
        client = FakeClient(packets(), write_fail=True)
        _, result = drive('write-fail', client, success=False)
        assert client.writes[-1] == b'STOP' and result['stop_confirmed']
        _, result = drive('stop-fail', FakeClient(packets(), stop_fail=True), success=False)
        assert not result['stop_confirmed']
        _, result = drive('overflow', FakeClient(packets()), success=False, queue_limit=1)
        assert result['queue_overflow'] == 1
        _, result = drive('tail', FakeClient([packets()[0]], tail=[packets()[1]]))
        assert result['packets'] == 2
        _, result = drive('tail-overflow', FakeClient([packets()[0]], tail=[packets()[1]]*2),
                          success=False, queue_limit=1)
        assert result['queue_overflow'] == 1 and '停止期间' in result['error']

        class BrokenArchive(RawArchive):
            def write(self, event):
                if 'packet_hex' in event:
                    raise OSError('模拟磁盘写入失败')
                super().write(event)
        client = FakeClient(packets())
        _, result = drive('disk-fail', client, success=False, archive_class=BrokenArchive)
        assert result['valid_samples'] == 0 and client.writes[-1] == b'STOP'

        out = root/'existing';out.mkdir();(out/'marker').write_text('保留')
        drive('existing', FakeClient(packets()), success=False)
        assert (out/'marker').read_text() == '保留'

        # 真CLI以临时bleak模块替换外部蓝牙边界；命令参数→归档→退出码全程执行。
        adapter = root/'adapter';adapter.mkdir()
        (adapter/'bleak.py').write_text('''from check_v12_ble import FakeClient, packets
class BleakClient(FakeClient):
    def __init__(self, device, timeout):
        assert device == 'offline-boundary'
        super().__init__(packets(), locked=False)
    async def __aenter__(self): return self
    async def __aexit__(self, *args): self.is_connected = False
''')
        import os
        env = dict(os.environ, PYTHONPATH=str(adapter)+os.pathsep+str(app.ROOT/'host'))
        cli = [sys.executable, str(app.ROOT/'host/v12_ble.py')]
        args = ['--device', 'offline-boundary', '--out', str(root/'cli'), '--seconds', '.2']
        run = subprocess.run(cli+['capture']+args+['--mode','test','--allow-real',
                             '--expected-build-id','0123456789abcdef'], env=env, capture_output=True, text=True)
        assert run.returncode == 0, run.stderr
        assert json.loads(run.stdout)['valid_samples'] == 2
        assert (root/'cli/events.jsonl').exists()
        bad = subprocess.run(cli+['capture']+args, env=env, capture_output=True, text=True)
        assert bad.returncode == 2 and '需 --mode' in bad.stderr
        passed += 2
    print(f'PASS: BLE 外部边界与真实CLI共{passed}组；2k/4k、原包、锁定、坏包、断连、队列/磁盘失败与STOP读回；未连实物')


if __name__ == '__main__':
    check()

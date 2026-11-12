"""执行真实C++状态机→Python解码→BLE外部边界→归档→回放CLI；不连接设备。"""
import asyncio
import csv
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import v12_ble as app
import v12_imu as imu
from check_v12_ble import FakeClient, packets


class ImuClient(FakeClient):
    def __init__(self, imu_packets, status, adc_packets=(), locked=False, fault=0, dropped=0, tail=()):
        super().__init__(adc_packets, locked=locked)
        self.metadata.update(imu_enabled=True, clock_source='TIMER2_1MHz', clock_resolution_us=1)
        self.characteristics += [SimpleNamespace(uuid=u) for u in (app.IMU_DATA, app.IMU_STATUS)]
        self.callbacks = {}
        self.imu_packets, self.imu_status, self.imu_tail = imu_packets, bytearray(status), tail
        self.imu_active = False
        self.imu_fault, self.imu_dropped = fault, dropped

    async def read_gatt_char(self, uuid):
        if uuid != app.IMU_STATUS:
            return await super().read_gatt_char(uuid)
        data = bytearray(self.imu_status)
        data[2] = int(self.imu_active)
        if self.writes:
            data[3] = self.imu_fault
            struct.pack_into('<Q', data, 40, self.imu_dropped)
            sent = len(self.imu_packets) + (len(self.imu_tail) if not self.imu_active else 0)
            struct.pack_into('<QQ', data, 24, sent, sent)
        return data

    async def start_notify(self, uuid, callback):
        self.callbacks[uuid] = callback

    async def write_gatt_char(self, uuid, value, response):
        assert uuid == app.CONTROL and response
        self.writes.append(value)
        if value == b'STOP':
            self.active = self.imu_active = False
            for packet in self.imu_tail:
                self.callbacks[app.IMU_DATA](None, packet)
        else:
            self.active = value != b'IMU1'
            self.imu_active = True
            for packet in self.packets:
                self.callbacks[app.DATA](None, packet)
            for packet in self.imu_packets:
                self.callbacks[app.IMU_DATA](None, packet)

    async def stop_notify(self, uuid):
        self.callbacks.pop(uuid)


def check():
    passed = 0
    with tempfile.TemporaryDirectory(prefix='yuanli-imu-check-') as tmp:
        root = Path(tmp)
        fw = app.ROOT/'hardware/8ch-ads1298/r01-bench/firmware-f05'
        probe = root/'probe'
        subprocess.run(['c++', '-std=c++17', '-Wall', '-Wextra', '-Werror', '-fsanitize=undefined',
                        str(fw/'test_imu.cpp'), '-o', str(probe)], check=True)
        result = subprocess.run([str(probe)], check=True, capture_output=True, text=True)
        backend = root/'backend'
        subprocess.run(['c++', '-std=c++17', '-Wall', '-Wextra', '-Werror',
                        '-I'+str(fw/'tests/mock'), str(fw/'test_imu_board.cpp'), '-o', str(backend)], check=True)
        subprocess.run([str(backend)], check=True, capture_output=True, text=True)
        passed += 1
        packet, status = (bytes.fromhex(line) for line in result.stdout.splitlines()[:2])
        decoded = imu.decode(packet)
        sample = imu.sample(decoded.frames[0])
        assert sample['gyro_raw'] == (-32768, 32767, -1) and sample['accel_raw'] == (1, 2, 3)
        assert decoded.timestamp_us > 2**32 and sample['read_latency_us'] == 500
        assert not imu.decode_status(status)['alignment_verified']
        passed += 1
        # 每条新增检查都有合法阳性样本与单独的必拒样本。
        bad_packets = [packet[:-1], packet+bytes(1)]
        for offset, value in ((0, 2), (1, 1), (2, 2), (3, 8), (28, 2), (29, 1)):
            bad = bytearray(packet);bad[offset] = value;bad_packets.append(bad)
        bad = bytearray(packet);struct.pack_into('<I', bad, 32, 9000);bad_packets.append(bad)
        for bad in bad_packets:
            try: imu.decode(bad)
            except ValueError: passed += 1
            else: raise AssertionError('坏IMU包未拒绝')
        for offset in (0, 1, 2, 3, 4, 5, 6, 8, 12, 13, 14):
            bad = bytearray(status);bad[offset] = 99
            try: imu.decode_status(bad)
            except ValueError: passed += 1
            else: raise AssertionError('坏IMU状态未拒绝')

        def drive(name, client, success=True, mode='imu', **kw):
            nonlocal passed
            out = root/name
            try:
                value = asyncio.run(app.capture(client, out, seconds=.02, mode=mode,
                    allow_real=True, expected='0123456789abcdef', poll_seconds=.005, **kw))
            except (ValueError, OSError, RuntimeError):
                assert not success, name
                value = json.loads((out/'summary.json').read_text()) if (out/'summary.json').exists() else None
                if value: assert value['state'] == '失败'
            else:
                assert success, name
                assert value['physical_device_verified'] is False
            passed += 1
            return out, value

        client = ImuClient([packet], status, locked=True)
        out, value = drive('imu-only-locked', client)
        assert client.writes == [b'IMU1', b'STOP'] and value['valid_samples'] == 0
        assert value['imu_samples'] == 1 and value['imu_stop_confirmed']
        assert len((out/'events.jsonl').read_text().splitlines()) == 1
        assert json.loads((out/'imu-events.jsonl').read_text().splitlines()[0])['packet_hex'] == packet.hex()
        assert json.loads((out/'metadata.json').read_text())['imu_profile']['alignment_verified'] is False
        run = subprocess.run([sys.executable, str(app.ROOT/'host/v12_imu.py'), str(out),
                              '--out', str(root/'replay.csv'), '--allow-real'], capture_output=True, text=True)
        assert run.returncode == 0, run.stderr
        rows = list(csv.DictReader((root/'replay.csv').open()))
        assert int(rows[0]['gx_raw']) == -32768 and int(rows[0]['timestamp_ISR_us']) == decoded.timestamp_us
        refused = subprocess.run([sys.executable, str(app.ROOT/'host/v12_imu.py'), str(out),
                                  '--out', str(root/'refused.csv')], capture_output=True, text=True)
        assert refused.returncode == 1 and 'real source not enabled' in refused.stderr
        passed += 2
        for fs in (2000, 4000):
            client = ImuClient([packet], status, packets(fs));client.metadata['fs_Hz'] = fs
            _, value = drive(f'joint-{fs}', client, mode='short', with_imu=True)
            assert value['valid_samples'] == 2 and value['imu_samples'] == 1
            assert value['stop_confirmed'] and value['imu_stop_confirmed']
        client = ImuClient([packet], status, packets(), locked=True)
        drive('joint-lock', client, False, mode='short', with_imu=True)
        assert client.writes == []
        # CH585M（F05C）用 SysTick 作共同时钟，也能联合采集；归档里记设备报的时钟名，不写死 TIMER2
        client = ImuClient([packet], status, packets());client.metadata['clock_source'] = 'CH585_SYSTICK'
        out, value = drive('joint-ch585', client, mode='short', with_imu=True)
        assert value['valid_samples'] == 2 and value['imu_samples'] == 1
        assert json.loads((out/'metadata.json').read_text())['imu_profile']['clock_source'] == 'CH585_SYSTICK'
        out, _ = drive('joint-nrf-profile', ImuClient([packet], status, packets()), mode='short', with_imu=True)
        assert json.loads((out/'metadata.json').read_text())['imu_profile']['clock_source'] == 'TIMER2_1MHz'
        passed += 1
        for name, field, value in (('disabled', 'imu_enabled', False), ('bad-clock', 'clock_source', 'micros'),
                                   ('bad-clock-nrf-typo', 'clock_source', 'TIMER2_1MHZ'), ('bad-clock-ch585-typo', 'clock_source', 'CH585_SYSTICK '),
                                   ('bad-switch', 'imu_enabled', 1)):
            client = ImuClient([packet], status);client.metadata[field] = value
            drive(name, client, False);assert client.writes == []
        client = ImuClient([packet], status);client.characteristics.pop()
        drive('missing-imu-status', client, False);assert client.writes == []
        drive('empty', ImuClient([], status), False)
        drive('bad-wire', ImuClient([b'bad'], status), False)
        synthetic = bytearray(packet);synthetic[3] |= 1
        drive('synthetic', ImuClient([synthetic], status), False)
        drive('duplicate', ImuClient([packet, packet], status), False)
        drive('status-fault', ImuClient([packet], status, fault=7), False)
        drive('known-drop', ImuClient([packet], status, dropped=1), False)
        drive('overflow', ImuClient([packet, packet], status), False, queue_limit=1)
        next_packet = bytearray(packet);next_packet[3] = 0
        struct.pack_into('<I', next_packet, 4, 1);struct.pack_into('<Q', next_packet, 8, decoded.timestamp_us+9615)
        _, value = drive('tail', ImuClient([packet], status, tail=[next_packet]))
        assert value['imu_samples'] == 2
        drive('tail-overflow', ImuClient([packet], status, tail=[next_packet, next_packet]), False, queue_limit=1)
        gap = bytearray(next_packet);struct.pack_into('<I', gap, 4, 2)
        drive('missing-sequence', ImuClient([packet, gap], status), False)
        class LostTail(ImuClient):
            async def read_gatt_char(self, uuid):
                data = await super().read_gatt_char(uuid)
                if uuid == app.IMU_STATUS and self.writes:
                    data = bytearray(data);struct.pack_into('<QQ', data, 24, 2, 2)
                return data
        _, value = drive('lost-whole-tail', LostTail([packet], status), False)
        assert '末尾计数不闭合' in value['error'] and value['imu_missing_samples'] == 0
        # 真实CLI参数也执行，Bleak仅换外部连接，不替换协议/归档/回放。
        adapter = root/'adapter';adapter.mkdir()
        (adapter/'bleak.py').write_text(f'''from check_v12_imu import ImuClient
class BleakClient(ImuClient):
    def __init__(self, device, timeout):
        assert device == 'offline-boundary'
        super().__init__([bytes.fromhex('{packet.hex()}')], bytes.fromhex('{status.hex()}'), locked=True)
    async def __aenter__(self): return self
    async def __aexit__(self, *args): self.is_connected = False
''')
        env = dict(os.environ, PYTHONPATH=str(adapter)+os.pathsep+str(app.ROOT/'host'))
        run = subprocess.run([sys.executable, str(app.ROOT/'host/v12_ble.py'), 'capture', '--device',
              'offline-boundary', '--out', str(root/'cli'), '--seconds', '.2', '--mode', 'imu',
              '--allow-real', '--expected-build-id', '0123456789abcdef'], env=env, capture_output=True, text=True)
        assert run.returncode == 0, run.stderr
        assert json.loads(run.stdout)['imu_samples'] == 1
        passed += 1
    print(f'PASS: IMU与共同计时器、C++→BLE→原包→回放CLI，{passed}组正反例；同步与实物未验收')


if __name__ == '__main__':
    check()

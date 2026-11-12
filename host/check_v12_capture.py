"""V12 刻度与原包记录检查；已知码值、坏输入和实际 C 离线回放，均为合成台架。"""
import csv
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile

import numpy as np

import v12


def refused(call, error=ValueError):
    try:
        call()
    except error:
        return
    raise AssertionError('必失败的输入没有被拒绝')


def known_packet(sequence=0, start=True, real=False):
    # 直接按协议构造已知码值，不经过 µV 合成编码器，防止同错抵消。
    codes = [0, 1, -1, 8388607, -8388608, 4194304, -4194304, 123]
    frames = [bytes([0xc0, n, 7]) + b''.join(c.to_bytes(3, 'big', signed=True) for c in codes)
              for n in range(8)]
    flags = (0 if real else 1) | (2 if start else 0)
    return struct.pack('<BBBBIQ', 1, 1, 8, flags, sequence, 1 + sequence * 500) + b''.join(frames)


def check_capture():
    codec = v12.load_codec()
    assert (v12.F05_PROFILE.vref_V, v12.F05_PROFILE.gain, v12.F05_PROFILE.fs_Hz) == (4, 6, 2000)
    assert abs(v12.UV_PER_COUNT - 0.079472869174) < 1e-12
    for kw in ({'vref_V': float('nan')}, {'vref_V': 3.3}, {'vref_V': True},
               {'gain': 5}, {'gain': True}, {'gain': 6.0}, {'fs_Hz': 2500}, {'fs_Hz': 2000.0}):
        refused(lambda: v12.AdcProfile(**kw))
    refused(lambda: v12.V12Rig(profile=v12.AdcProfile(fs_Hz=4000), codec=codec))
    packet = known_packet()
    rig, got = v12.V12Rig(codec=codec), []
    rig.frame_subscribers.append(got.append)
    rig.feed_packet(packet)
    assert np.array_equal(got[0][0], [0, 0, 0, 666667, -666667, 333333, -333333, 10]), got
    # 非默认合法刻度也要实际改变显示结果。
    rig2, got2 = v12.V12Rig(codec=codec, profile=v12.AdcProfile(vref_V=2.4, gain=12)), []
    rig2.frame_subscribers.append(got2.append)
    rig2.feed_packet(packet)
    assert np.array_equal(got2[0][0], [0, 0, 0, 200000, -200000, 100000, -100000, 3])

    with tempfile.TemporaryDirectory(prefix='v12-capture-check-') as tmp:
        root = Path(tmp)
        directory = root / 'raw'
        rig = v12.V12Rig(codec=codec, raw_dir=directory)
        rig.feed_packet(packet)
        # 未关闭文件就能读到原包，避免数据只留在 Python 缓冲。
        assert json.loads((directory / 'events.jsonl').read_text()) == {'packet_hex': packet.hex(), 'mtu': 247}
        rig.feed_packet(known_packet(16, False))
        refused(lambda: rig.feed_packet(b'\x00'))
        rig.disconnect()
        assert len(rig.page_buf) == 0 and rig.buf == b''
        rig.feed_packet(packet)
        assert rig.status()['v12']['accepted_samples'] == 24
        assert rig.status()['v12']['missing_samples'] == 8
        assert rig.status()['v12']['sessions'] == 2
        rig.close_capture()
        assert not rig.status()['v12']['raw_capture']
        events = [json.loads(line) for line in (directory / 'events.jsonl').read_text().splitlines()]
        assert events == [dict(packet_hex=packet.hex(), mtu=247),
                          dict(packet_hex=known_packet(16, False).hex(), mtu=247),
                          dict(packet_hex='00', mtu=247), {'disconnect': True},
                          dict(packet_hex=packet.hex(), mtu=247)]
        metadata = json.loads((directory / 'metadata.json').read_text())
        assert metadata['adc_profile'] == dict(vref_V=4.0, gain=6, fs_Hz=2000)
        assert metadata['voltage_at'] == 'ADS1298 PGA input'
        assert metadata['calibration_verified'] is False and metadata['hardware_verified'] is False
        assert metadata['source_authentication'] is False and metadata['allow_real'] is False
        assert len(metadata['codec_sha256']) == 64
        before = (directory / 'events.jsonl').read_bytes()
        refused(lambda: v12.V12Rig(codec=codec, raw_dir=directory), FileExistsError)
        assert (directory / 'events.jsonl').read_bytes() == before

        # 记录默认拒绝的真实标签，保留诊断但不向显示或训练输出。
        rejected = v12.V12Rig(codec=codec, raw_dir=root / 'rejected')
        refused(lambda: rejected.feed_packet(known_packet(real=True)))
        assert rejected.rx.accepted_samples == 0
        refused(lambda: rejected.take())
        rejected.close_capture()
        assert json.loads((root / 'rejected/events.jsonl').read_text())['packet_hex'] == known_packet(real=True).hex()

        # 模拟写入失败：错误必须向调用者传播，接收计数不得继续推进。
        failed = v12.V12Rig(codec=codec, raw_dir=root / 'failed')
        failed.archive.file.close()
        refused(lambda: failed.feed_packet(packet))
        assert failed.rx.accepted_samples == 0
        failed.close_capture()

        # 用既有 DSP 的实际 C 代码回放本次文件，而非另写一个自证解码器。
        replay = v12.CODEC.parent.parent / 'dsp-f03/replay.py'
        if not replay.exists():
            raise FileNotFoundError(f'缺少离线回放器：{replay}')
        output = root / 'dsp'
        run = subprocess.run([sys.executable, str(replay), str(directory / 'events.jsonl'),
                              str(output), '--fs', '2000'], capture_output=True, text=True, timeout=30)
        assert run.returncode == 2, run.stderr + run.stdout  # 含故意坏包，必须报告不完整。
        result = json.loads((output / 'result.json').read_text())
        assert (result['accepted_samples'], result['missing_samples'], result['sessions']) == (24, 8, 2)
        assert len(result['rejected_events']) == 1 and result['timestamp_discontinuities'] == 0
        rows = list(csv.DictReader((output / 'samples.csv').open()))
        assert len(rows) == 24
        for index, row in enumerate(rows):
            assert [int(row[f'raw{i}']) for i in range(1, 9)] == [0, 1, -1, 8388607, -8388608, 4194304, -4194304, 123]
            assert int(row['status_word']) == 0xc00007 + (index % 8) * 256
        assert [int(r['sequence']) for r in rows] == list(range(8)) + list(range(16, 24)) + list(range(8))
        assert [int(r['session']) for r in rows] == [1] * 16 + [2] * 8

        # 命令入口真正写出可回放文件；重复路径必须非零退出且不覆盖。
        path = root / 'cli'
        command = [sys.executable, str(Path(v12.__file__)), '--capture-synth', str(path)]
        run = subprocess.run(command, capture_output=True, text=True, timeout=10)
        assert run.returncode == 0 and '非实物数据' in run.stdout, run.stderr
        original = (path / 'events.jsonl').read_bytes()
        run = subprocess.run(command, capture_output=True, text=True, timeout=10)
        assert run.returncode != 0 and (path / 'events.jsonl').read_bytes() == original
        replay_run = subprocess.run([sys.executable, str(replay), str(path / 'events.jsonl'),
                                     str(root / 'cli-replay'), '--fs', '2000'],
                                    capture_output=True, text=True, timeout=30)
        assert replay_run.returncode == 0, replay_run.stderr
        assert json.loads((root / 'cli-replay/result.json').read_text())['accepted_samples'] == 2000
    print('PASS: V12 已知码刻度、错误配置拒绝、原包/状态字保真、坏包/缺口/断连回放、写入失败与覆盖拦截；均为合成台架')


if __name__ == '__main__':
    check_capture()

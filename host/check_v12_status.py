"""编译固件状态编码→电脑解析，并用损坏状态验证拒绝路径。"""
from pathlib import Path
import subprocess
import sys
import tempfile
from v12_status import decode_status


def check():
    root = Path(__file__).resolve().parent.parent
    source = root / 'hardware/8ch-ads1298/r01-bench/firmware-f05/test_diagnostics.cpp'
    with tempfile.TemporaryDirectory(prefix='v12-diagnostics-') as tmp:
        executable = Path(tmp) / 'diagnostics'
        subprocess.run(['c++', '-std=c++17', '-Wall', '-Wextra', '-Werror', str(source), '-o', str(executable)], check=True)
        run = subprocess.run([str(executable)], capture_output=True, text=True, check=True)
        print(run.stderr.strip())
        data = bytes.fromhex(run.stdout.strip())
    value = decode_status(data)
    assert value['produced'] == 9 and value['ring_dropped'] == 2 and value['sent_samples'] == 7
    assert value['drdy_raw_edges'] == 0x100000003 and value['drdy_min_interval_us'] == 10
    assert value['spi_Hz'] == 4_000_000 and value['ads_status'] == 0xc00007
    assert value['fault'] == 3 and not value['active'] and not value['physical_device_verified']
    old = bytearray(data[:48]);old[43] = 0
    assert decode_status(old)['drdy_raw_edges'] is None
    single = bytearray(data);single[48:56] = (1).to_bytes(8, 'little');single[56:60] = bytes([255])*4
    assert decode_status(single)['drdy_min_interval_us'] is None
    extended = bytearray(data) + bytearray(72); extended[43] = 2
    import struct
    struct.pack_into('<Q6I3Q4I', extended, 64, 9, 0, 0, 0, 8, 2, 300, 5, 0, 7, 0, 0, 3, 600)
    decoded = decode_status(extended)
    assert decoded['read_frames'] == 9 and decoded['flow_phase'] == 3
    assert decoded['notify_resources'] == 5 and decoded['hvn_completed'] == 7
    wrong_phase = bytearray(extended); wrong_phase[128] = 5
    # v3（R01 dual，TI 计划 S3）：v2 + 有效标志 + 26 字节寄存器快照
    regs = bytes([0x92, 0x84, 0, 0xE0] + [0x01] * 8 + [0] * 8 + [0x0F, 0, 0x20, 0, 0, 0])
    v3 = bytearray(extended) + bytes([1]) + regs; v3[43] = 3
    got = decode_status(v3)
    assert got['ads_regs'] == regs.hex() and got['ads_regs_valid'] and got['read_frames'] == 9 and got['flow_phase'] == 3
    import ads1298_regs
    assert ads1298_regs.check(bytes.fromhex(got['ads_regs'])) == []  # 快照能直接交给寄存器表解码
    v3_empty = bytearray(v3); v3_empty[136] = 0
    assert decode_status(v3_empty)['ads_regs'] is None and not decode_status(v3_empty)['ads_regs_valid']
    v3_flag = bytearray(v3); v3_flag[136] = 2
    v3_as_v2 = bytearray(v3); v3_as_v2[43] = 2
    v2_as_v3 = bytearray(extended); v2_as_v3[43] = 3
    bad_inputs = [data[:47], data[:63], data+b'\0', extended[:135], wrong_phase, v3[:162], v3 + b'\0', v3_flag, v3_as_v2, v2_as_v3]
    for index, replacement in ((43, 2), (41, 2), (42, 2)):
        wrong = bytearray(data);wrong[index] = replacement;bad_inputs.append(wrong)
    wrong = bytearray(data);wrong[60:64] = (3_000_000).to_bytes(4, 'little');bad_inputs.append(wrong)
    wrong = bytearray(data);wrong[56:60] = bytes([255])*4;bad_inputs.append(wrong)
    wrong = bytearray(data);wrong[48:56] = (1).to_bytes(8, 'little');bad_inputs.append(wrong)
    rejected = 0
    for wrong in bad_inputs:
        try:decode_status(wrong)
        except ValueError:rejected += 1
        else:raise AssertionError('损坏状态未被拒绝')
    # 真正执行可用的诊断命令入口，确认非默认SPI速度与原始沿数读回。
    run = subprocess.run([sys.executable, str(root/'host/v12_status.py'), data.hex()], capture_output=True, text=True, check=True)
    assert '4294967299' in run.stdout and '4000000' in run.stdout
    print(f'PASS: 固件C++→Python状态/命令入口；旧版兼容、未测间隔、v3 寄存器快照；{rejected}个坏状态全部拒绝，未连实物')


if __name__ == '__main__':
    check()

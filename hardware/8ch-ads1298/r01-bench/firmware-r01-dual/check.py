"""一镜像两通道自检：入口分流 + 两份原程序各自的自检。不接设备。"""
from pathlib import Path
import subprocess, sys, tempfile
HERE = Path(__file__).resolve().parent
with tempfile.TemporaryDirectory(prefix='r01-dual-') as tmp:
    exe = Path(tmp) / 'dispatch'
    subprocess.run(['c++', '-std=c++17', '-Wall', '-Wextra', '-I' + str(HERE / 'tests/stubs'), str(HERE / 'tests/test_dispatch.cpp'), '-o', str(exe)], check=True)
    subprocess.run([str(exe)], check=True)
for rel in ('firmware-f05-ble-dout/check_flow.py', 'firmware-f05-usb/check_usb_frame.py'):
    subprocess.run([sys.executable, str(HERE.parent / rel)], check=True)
# RLD 通道补丁：暂存副本里只让 CH1 进 RLD，F05 原文件不变
spec = __import__('importlib.util').util.spec_from_file_location('r01_dual_build', HERE / 'build.py')
b = __import__('importlib.util').util.module_from_spec(spec); spec.loader.exec_module(b)
staged = (b.stage() / 'src' / 'ads1298.cpp').read_text()
assert b.RLD_SENS == 0x01, 'R01 人体只接 CH1，RLD_SENS 应为 0x01；改通道时同步改这里和 README'
assert staged.count(f'regs[0xd]=regs[0xe]=0x{b.RLD_SENS:02x};') == 1 and b.RLD_OLD not in staged, 'RLD 通道补丁没生效'
assert (HERE.parent / 'firmware-f05' / 'src' / 'ads1298.cpp').read_text().count(b.RLD_OLD) == 1, 'F05 原文件被改了'
# 注意：stage() 会清掉 .pio/stage，先跑 check.py 再 build.py
print('PASS: EXR1 的 RLD 只用 CH1（暂存副本 0x01），firmware-f05 原文件仍为 0xFF')

# TI 计划 S3+S4（bench_patch.py）：寄存器快照、LOF1。默认镜像和 --loff 镜像各编一遍。
import re, shutil
sys.path.insert(0, str(HERE.parents[3] / 'host'))
import ads1298_regs as regs
DOUT = HERE.parent / 'firmware-f05-ble-dout'
for m in ('EXT1', 'EXR1', 'LOF1'):  # 反例：三种外部输入模式各自都要被 USB 半边的检查拦下
    assert b.bench.usb_has_external(f'if (!strcmp(line, "{m}"))') == [f'"{m}"'], f'USB 外部输入检查漏了 {m}'
for loff in (False, True):
    out = b.stage(loff=loff)
    src_text = {n: (out / 'src' / n).read_text() for n in ('ads1298.cpp', 'usb_app.cpp', 'ble_app.cpp', 'flow_control.h')}
    assert not b.bench.usb_has_external(src_text['usb_app.cpp']), 'USB 半边出现外部输入模式'
    assert ('-DMAKO_R01_LOFF=1' in (out / 'platformio.ini').read_text()) == loff, 'LOF1 编译开关和 --loff 不一致'
    assert src_text['ble_app.cpp'].count('"LOF1"') == 1 and '"LOF1"' not in src_text['flow_control.h']
    assert src_text['usb_app.cpp'].count('  send_regs();  // 放最后\n}\n\nstatic void send_status()') == 1, 'USB 停机报告没在最后调用 send_regs'
    assert src_text['usb_app.cpp'].count('if (mode == 1 || mode == 2) ads.start(') == 1, 'USB 半边少了内部信号模式护栏'
    flag = ['-DMAKO_R01_LOFF=1'] if loff else []  # 默认镜像不传，走 ads1298.h 里的默认 0
    with tempfile.TemporaryDirectory(prefix='r01-bench-') as tmp:
        tmp = Path(tmp); shutil.copytree(out / 'src', tmp / 'src')
        exe = tmp / 'drv'
        subprocess.run(['c++', '-std=c++17', '-Wall', '-Wextra', *flag, '-I' + str(tmp / 'src'), str(HERE / 'tests/test_bench_driver.cpp'), str(tmp / 'src/ads1298.cpp'), '-o', str(exe)], check=True)
        res = subprocess.run([str(exe)], check=True, capture_output=True, text=True).stdout
        print(res.strip().splitlines()[-1])
        snaps = dict(re.findall(r'^SNAP (\w+) ([0-9a-f]{52})$', res, re.M))
        assert set(snaps) == ({'sht', 'exr', 'lof'} if loff else {'sht', 'exr'}), snaps
        for name, hx in snaps.items():  # 固件实际写的整表交给主机寄存器表按手册查：不能有任何保留位或编码问题
            r = bytes.fromhex(hx)
            assert regs.check(r) == [], (name, regs.check(r))
            assert regs.fs_hz(r) == 2000 and regs.vref_v(r) == 4.0 and regs.gain(r, 1) == 6
        if loff:
            d = regs.decode(bytes.fromhex(snaps['lof']))
            assert d['LOFF']['FLEAD_OFF'] == 3 and d['LOFF']['ILEAD_OFF'] == 0 and d['LOFF']['COMP_TH'] == 0 and d['CONFIG4']['PD_LOFF_COMP'] == 1
            assert d['LOFF_SENSP']['BITS'] == d['LOFF_SENSN']['BITS'] == d['RLD_SENSP']['BITS'] == b.RLD_SENS and d['CONFIG3']['PD_RLD'] == 1
            assert d['LOFF_FLIP']['BITS'] == 0  # 电流方向不翻
        for name in ('timebase_board.h', 'bench_release.h', 'v12_build_id.h'):
            shutil.copyfile(DOUT / 'tests/stubs' / name, tmp / 'src' / name)
        common = ['-I' + str(DOUT / 'tests/stubs'), '-I' + str(tmp / 'src'), *flag]
        objs = []
        for name in ('v12_codec.c', 'v12_stream.c', 'v12_dsp.c'):
            obj = tmp / (name + '.o'); subprocess.run(['cc', '-std=c11', *common, '-c', str(tmp / 'src' / name), '-o', str(obj)], check=True); objs.append(str(obj))
        exe = tmp / 'ble'
        subprocess.run(['c++', '-std=c++17', '-Wall', '-Wextra', '-Wno-unused-function', *common, str(HERE / 'tests/test_bench_ble.cpp'), str(tmp / 'src/ads1298.cpp'), *objs, '-o', str(exe)], check=True)
        print(subprocess.run([str(exe)], check=True, capture_output=True, text=True, timeout=60).stdout.strip())
# USB 半边的 send_regs()：只有 PlatformIO 出镜像才会编到它，这里把函数从暂存副本里抠出来配替身单独编（-Werror），
# 输出的帧交给 F05-USB 的 Python 解析器解，查 diag:8 的 JSON。
import json
sys.path.insert(0, str(HERE.parent / 'firmware-f05-usb'))
import usb_capture as uc
usb_src = (b.stage() / 'src' / 'usb_app.cpp').read_text()
fn = re.search(r'^static void send_regs\(\) \{.*?^\}\n', usb_src, re.S | re.M).group(0)
CPP = ('#include "usb_frame.h"\n#include <cstdio>\n#include <cstdint>\n'
       'struct { uint8_t readback[26]; bool readback_valid; } ads;\n'
       'static void send(const uint8_t *out, size_t n) { for (size_t i = 0; i < n; ++i) std::printf("%02x", out[i]); std::printf("\\n"); }\n'
       + fn +
       'int main() { for (int i = 0; i < 26; ++i) ads.readback[i] = uint8_t(0x90 + i); ads.readback_valid = true; send_regs();'
       ' ads.readback_valid = false; send_regs(); }\n')
with tempfile.TemporaryDirectory(prefix='r01-usbregs-') as tmp:
    t = Path(tmp); (t / 't.cpp').write_text(CPP)
    subprocess.run(['c++', '-std=c++17', '-Wall', '-Wextra', '-Werror', '-I', str(b.stage() / 'src'), str(t / 't.cpp'), '-o', str(t / 't')], check=True)
    lines = subprocess.run([str(t / 't')], check=True, capture_output=True, text=True).stdout.split()
p = uc.Parser()
frames = [f for line in lines for f in p.feed(bytes.fromhex(line))]
assert [k for k, _ in frames] == [3, 3] and p.crc_errors == 0, frames
got = [json.loads(v) for _, v in frames]
want = ''.join(f'{0x90 + i:02x}' for i in range(26))
assert got == [{'diag': 8, 'valid': 1, 'regs': want}, {'diag': 8, 'valid': 0, 'regs': want}], got
print('PASS: USB 半边 diag:8 单独编译（-Werror）并经 Python 解析器解出 26 字节寄存器')
print('PASS: TI 计划 S3+S4——快照与手册寄存器表一致、蓝牙状态 v3、USB 半边无外部输入、LOF1 只在 --loff 镜像里')

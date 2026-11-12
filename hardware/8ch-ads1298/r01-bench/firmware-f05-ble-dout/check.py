"""编译执行真实采集状态机；替身只在GPIO/SPI/BLE/时钟边界，不访问设备。"""
from pathlib import Path
import subprocess
import tempfile
import json
import sys
HERE = Path(__file__).resolve().parent
F05 = HERE.parent / 'firmware-f05'
with tempfile.TemporaryDirectory(prefix='r01-ble-dout-check-') as tmp:
    tmp = Path(tmp)
    common = ['-I'+str(HERE/'tests/stubs'), '-I'+str(F05/'src')]
    objects = []
    for name in ['v12_stream.c', 'v12_codec.c', 'v12_dsp.c']:
        obj = tmp / (name + '.o')
        subprocess.run(['cc', '-std=c11', *common, '-c', str(F05/'src'/name), '-o', str(obj)], check=True)
        objects.append(str(obj))
    exe = tmp/'capture'
    subprocess.run(['c++', '-std=c++17', '-Wall', '-Wextra', '-Werror', *common,
                    str(HERE/'tests/test_capture.cpp'), str(F05/'src/ads1298.cpp'), *objects, '-o', str(exe)], check=True)
    output = subprocess.check_output([str(exe)], text=True)
    print(output)
    metadata = json.loads(next(line[5:] for line in output.splitlines() if line.startswith('META:')))
    sys.path.insert(0, str(HERE.parents[3] / 'host'))
    import v12_ble
    assert v12_ble.validate_metadata(json.dumps(metadata).encode(), '0123456789abcdef')['drdy_source'] == 'dout_latch'
    assert metadata['off_body_only'] and metadata['inferred_samples'] == 0
    assert metadata['bench_basis'].endswith('not_measured')
    print('真实BLE主机元数据入口兼容检查通过。')
    guard = tmp/'guard'
    subprocess.run(['c++', '-std=c++17', '-Wall', '-Wextra', '-Werror', str(HERE/'test_dout_guard.cpp'), '-o', str(guard)], check=True)
    subprocess.run([str(guard)], check=True)

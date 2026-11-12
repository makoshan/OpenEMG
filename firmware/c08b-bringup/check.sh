#!/bin/zsh
# 一键检查：引脚核对（含必须报红的反例）→ 干净重编（-Werror）→ 主机端测试 → 向量表与关键符号 → 产物 SHA-256。
# 用法：zsh check.sh [板读回.json]（默认仓库里的 R4U2 读回）。不连设备、不刷机。
set -e
H=${0:A:h}; cd $H
BOARD=${1:-$H/../../hardware/common-mainboard/mainboard-r4u6/r4u6-readback.json}
PY=${PY:-python3}
TC=${TC:-$HOME/.platformio/packages/toolchain-gccarmnoneeabi/bin/}

echo "== 1 引脚核对"
$PY tools/pins.py $BOARD
T=$(mktemp -d)
$PY - $BOARD $T/bad.json <<'EOF'
import json, sys
g = json.load(open(sys.argv[1]))
for p in g['pads']:
    if p['ref'] == 'U18' and p.get('num') == '14': p['net'] = 'XIAO_CS_BAD'   # 反例：把 CS_A 那根网改名
json.dump(g, open(sys.argv[2], 'w'))
EOF
cp l432/pins.h $T/; cp nrf/pins.h $T/nrf_pins.h
if $PY tools/pins.py $T/bad.json >/dev/null 2>&1; then echo "反例没报红：引脚核对失效"; exit 1; fi
cp $T/pins.h l432/pins.h; cp $T/nrf_pins.h nrf/pins.h; /bin/rm -rf $T
echo "   反例（CS_A 网名改坏）报红：通过"

echo "== 2 干净重编"
make clean >/dev/null
# 输出先落日志再 grep：接管道会吞掉 make 的退出码，主机端测试失败也显示通过（11-09 复核复现过）
L=$(mktemp)
if ! make BOARD_JSON=$BOARD all >$L 2>&1; then cat $L; /bin/rm -f $L; echo "编译或主机端测试失败"; exit 1; fi
grep -E "FLASH:|RAM:|主机端测试" $L || true
/bin/rm -f $L
test -f build/l432.hex -a -f build/nrf.hex -a -x build/test_host

echo "== 3 向量表与符号"
$PY - $TC <<'EOF'
import struct, subprocess, sys
tc = sys.argv[1]
def sym(elf):
    out = subprocess.run([tc + 'arm-none-eabi-nm', elf], capture_output=True, text=True, check=True).stdout
    return {l.split()[2]: int(l.split()[0], 16) for l in out.splitlines() if len(l.split()) == 3}
for name, flash, ram in (('l432', (0x08000000, 0x08040000), (0x20000000, 0x2000C000)), ('nrf', (0, 0x100000), (0x20000000, 0x20040000))):
    b = open(f'build/{name}.bin', 'rb').read(8)
    sp, rst = struct.unpack('<II', b)
    assert ram[0] < sp <= ram[1], f'{name} 初始栈 0x{sp:08X} 不在 RAM'
    assert flash[0] <= (rst & ~1) < flash[1] and rst & 1, f'{name} 复位入口 0x{rst:08X} 不对'
    s = sym(f'build/{name}.elf')
    for need in ('_SEGGER_RTT', 'main', 'SysTick_Handler') + (('g_report',) if name == 'l432' else ('adv', 'rx')):
        assert need in s, f'{name} 缺符号 {need}'
    print(f'   {name}: SP 0x{sp:08X}，Reset 0x{rst:08X}，_SEGGER_RTT 0x{s["_SEGGER_RTT"]:08X}' + (f'，g_report 0x{s["g_report"]:08X}' if name == 'l432' else ''))
EOF

echo "== 4 产物"
shasum -a 256 build/l432.hex build/nrf.hex | sed 's/^/   /'
echo "检查通过（只证明能编、引脚对板、协议自洽；没上板）"

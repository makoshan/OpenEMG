#!/bin/zsh
# 一键检查：定稿主控 R4U6 / R4U6N 引脚核对（含 2 项必须报红的反例）→ 干净重编（-Werror）→ 主机端测试 → 向量表与关键符号 → 产物 SHA-256。
# 用法：zsh check.sh [主控板.epcb2]（默认 R4U6 圆孔版，同时核 R4U6N 缺口版）。不连设备、不刷机。
set -e
H=${0:A:h}; cd $H
BOARD=${1:-$H/../../hardware/common-mainboard/mainboard-r4u6/C08B-main-R4U6.epcb2}
BOARD_N=$H/../../hardware/common-mainboard/mainboard-r4u6n/C08B-main-R4U6N.epcb2
OLD_R4U2=$H/../../hardware/common-mainboard/mainboard-r4u6/r4u2-readback-missing.json
PY=${PY:-python3}
TC=${TC:-$HOME/.platformio/packages/toolchain-gccarmnoneeabi/bin/}

echo "== 1 引脚核对（MCU-U9 + v0.01 AFE-30P + R4U6 圆孔 + R4U6N 缺口）"
$PY -B tools/pins_u9.py --selftest
if [ -f "$BOARD_N" ]; then $PY tools/pins.py "$BOARD_N"; fi
$PY tools/pins.py "$BOARD"
T=$(mktemp -d)
cp l432/pins.h $T/; cp nrf/pins.h $T/nrf_pins.h
$PY - "$BOARD" "$T/bad.epcb2" <<'EOF'
import sys
s = open(sys.argv[1], encoding='utf-8').read()
assert '"padNet":"XIAO_CS"' in s
open(sys.argv[2], 'w', encoding='utf-8').write(s.replace('"padNet":"XIAO_CS"', '"padNet":"XIAO_CS_BAD"', 1))
EOF
if $PY tools/pins.py "$T/bad.epcb2" >/dev/null 2>&1; then echo "反例1没报红：引脚核对失效"; exit 1; fi
echo "   反例1（CS_A 网名改坏）报红：通过"
if [ -f "$OLD_R4U2" ]; then
    if $PY tools/pins.py "$OLD_R4U2" >/dev/null 2>&1; then echo "反例2没报红：未抓出旧板 R4U2 缺 BOOT0=VBUS_SENSE"; exit 1; fi
    echo "   反例2（旧版 R4U2 未连 BOOT0=VBUS_SENSE）报红：通过"
fi
cp $T/pins.h l432/pins.h; cp $T/nrf_pins.h nrf/pins.h; /bin/rm -rf $T

echo "== 2 干净重编"
make clean >/dev/null
L=$(mktemp)
if ! make BOARD_JSON="$BOARD" all >$L 2>&1; then cat $L; /bin/rm -f $L; echo "编译或主机端测试失败"; exit 1; fi
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

echo "== 4 主机端广播与97字节报告解码器自检"
$PY -B tools/decode_bringup.py --self-test

echo "== 5 产物"
shasum -a 256 build/l432.hex build/nrf.hex | sed 's/^/   /'
echo "检查通过（只证明能编、引脚对 R4U6/R4U6N 板、16CH/8CH/2CH 协议与主机解码器自洽；没上板）"

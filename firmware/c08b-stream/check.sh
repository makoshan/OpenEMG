#!/usr/bin/env bash
# C08B 共用双核流式候选固件一键验证门禁（零修改源码树，同时兼容 OpenEMG 仓与主仓目录布局，以及云端 Ubuntu CI / 本机完整工具链）。
set -euo pipefail
export PYTHONDONTWRITEBYTECODE=1
HERE="$(cd "$(dirname "$0")" && pwd)"
cd "$HERE"

PY="${PY:-python3}"
HOST_CC="${CC:-cc}"
PIO_PKG="${PIO_PKG:-$HOME/.platformio/packages}"

if [[ -f "$HERE/../../hardware/common-mainboard/mainboard-r4u6/C08B-main-R4U6.epcb2" ]]; then
  BOARD="$HERE/../../hardware/common-mainboard/mainboard-r4u6/C08B-main-R4U6.epcb2"
  BOARD_N="$HERE/../../hardware/common-mainboard/mainboard-r4u6n/C08B-main-R4U6N.epcb2"
  READBACK="$HERE/../../hardware/common-mainboard/mainboard-r4u6/r4u6-readback.json"
else
  BOARD="$HERE/../mainboard-r4u6-boot0-20261111/C08B-main-R4U6.epcb2"
  BOARD_N="$HERE/../mainboard-r4u6-boot0-20261111/C08B-main-R4U6N.epcb2"
  READBACK=""
fi

TMP_DIR="$(mktemp -d)"
trap '/bin/rm -rf "$TMP_DIR"' EXIT

echo "== 1 引脚逐脚只读对账（R4U6 圆孔 + R4U6N 缺口 + J_AFE 20P 跨板映射 + MCU-U9/AFE-30P 专属映射 + 必败反例）"
if [[ -n "$BOARD_N" && -f "$BOARD_N" ]]; then "$PY" -B tools/pins.py --check-headers "$BOARD_N"; fi
if [[ -n "$READBACK" && -f "$READBACK" ]]; then "$PY" -B tools/pins.py --check-headers "$READBACK"; fi
"$PY" -B tools/pins.py --check-headers "$BOARD"
"$PY" -B tools/pins.py --check-jafe "$BOARD"
if [[ -f "$HERE/../../hardware/16ch-afe-hirose-1mm-1nf/OpenEMG_v0.01_DualBoard.epro2" ]]; then
  "$PY" -B tools/pins.py --check-u9 --self-test "$HERE/../../hardware/16ch-afe-hirose-1mm-1nf/OpenEMG_v0.01_DualBoard.epro2"
fi
if [[ -f "$HERE/../../hardware/16ch-u9-dual30/OpenEMG-C08B-Mainboard-Rev0.01.epro2" ]]; then
  "$PY" -B tools/pins.py --check-u9 --self-test "$HERE/../../hardware/16ch-u9-dual30/OpenEMG-C08B-Mainboard-Rev0.01.epro2"
fi

"$PY" -B - "$BOARD" "$TMP_DIR/bad1.epcb2" "$TMP_DIR/bad2_r4u2.json" "$TMP_DIR/bad3_extra.json" <<'EOF'
import json, sys
from pathlib import Path
sys.path.insert(0, 'tools')
import pins

s = Path(sys.argv[1]).read_text(encoding='utf-8')
assert '"padNet":"XIAO_CS"' in s
Path(sys.argv[2]).write_text(s.replace('"padNet":"XIAO_CS"', '"padNet":"XIAO_CS_BAD"', 1), encoding='utf-8')

nets = pins.load_nets(Path(sys.argv[1]))
# 反例2：模拟旧板 R4U2 未把 U18 脚31(PH3-BOOT0) 并入 VBUS_SENSE（旧接 GND）
pads_r4u2 = [{'ref': ref, 'num': str(num), 'net': ('GND' if (ref, num) == ('U18', 31) else net)} for (ref, num), net in sorted(nets.items())]
Path(sys.argv[3]).write_text(json.dumps({'pads': pads_r4u2}), encoding='utf-8')

# 反例3：模拟 U13 多连了一根未声明信号脚 P0.28(脚41)=ROGUE_NET
pads_extra = [{'ref': ref, 'num': str(num), 'net': net} for (ref, num), net in sorted(nets.items())]
pads_extra.append({'ref': 'U13', 'num': '41', 'net': 'ROGUE_NET'})
Path(sys.argv[4]).write_text(json.dumps({'pads': pads_extra}), encoding='utf-8')
EOF

if "$PY" -B tools/pins.py --check-headers "$TMP_DIR/bad1.epcb2" >/dev/null 2>&1; then
  echo "FAIL: 反例1（CS_A 网名篡改）未报红"; exit 1
fi
echo "   反例1（CS_A 网名篡改）报红：通过"

if "$PY" -B tools/pins.py --check-headers "$TMP_DIR/bad2_r4u2.json" >/dev/null 2>&1; then
  echo "FAIL: 反例2（旧版 R4U2 U18.31 PH3-BOOT0=GND）未报红"; exit 1
fi
echo "   反例2（旧版 R4U2 缺 PH3-BOOT0=VBUS_SENSE）报红：通过"

if "$PY" -B tools/pins.py --check-headers "$TMP_DIR/bad3_extra.json" >/dev/null 2>&1; then
  echo "FAIL: 反例3（U13 多接未声明信号脚）未报红"; exit 1
fi
echo "   反例3（U13 多接未声明信号脚 P0.28）报红：通过"

echo "== 2 源码安全红线扫描（10 条红线 + 10 项必败变异反例）"
"$PY" -B tools/pins.py --check-safety --self-test

echo "== 3 主机 C11 协议与寄存器单测（-Wall -Wextra -Werror）"
"$HOST_CC" -std=c11 -O2 -Wall -Wextra -Werror -I common host_test/test_stream_host.c -o "$TMP_DIR/test_stream_host"
"$TMP_DIR/test_stream_host"

echo "== 4 Cortex-M4 交叉编译器 ABI 与结构体对齐检查"
if [[ -x "$PIO_PKG/toolchain-gccarmnoneeabi/bin/arm-none-eabi-gcc" ]]; then
  ARM_GCC="$PIO_PKG/toolchain-gccarmnoneeabi/bin/arm-none-eabi-gcc"
elif command -v arm-none-eabi-gcc >/dev/null 2>&1; then
  ARM_GCC="arm-none-eabi-gcc"
else
  ARM_GCC=""
fi

if [[ -n "$ARM_GCC" ]]; then
  cat > "$TMP_DIR/abi_probe.c" <<'EOF'
#include "stream_proto.h"
uint32_t c08b_abi_probe(c08b_link_tx_t *tx, c08b_link_rx_t *rx) {
    c08b_link_tx_seal(tx);
    c08b_link_rx_seal(rx);
    return (uint32_t)c08b_link_tx_ok(tx) + (uint32_t)c08b_link_rx_ok(rx);
}
EOF
  GCC_INC="$("$ARM_GCC" -print-file-name=include)"
  "$ARM_GCC" -mcpu=cortex-m4 -mthumb -mfloat-abi=hard -mfpu=fpv4-sp-d16 \
    -std=c11 -O2 -Wall -Wextra -Werror -ffreestanding -nostdinc -isystem "$GCC_INC" -I common \
    -c "$TMP_DIR/abi_probe.c" -o "$TMP_DIR/abi_probe.o"
  echo "   Cortex-M4 硬浮点 ABI 编译检查通过（$(basename "$ARM_GCC")）"
fi

if [[ -d "$PIO_PKG/framework-cmsis-stm32l4" && -d "$PIO_PKG/framework-arduinoadafruitnrf52-seeed" && -x "$PIO_PKG/toolchain-gccarmnoneeabi/bin/arm-none-eabi-gcc" ]]; then
  echo "== 5 双 MCU 完整固件零告警链接与向量表符号校验（l432 + nrf_s140 + nrf_nosd）"
  OUT_BUILD="$TMP_DIR/build"
  if ! make PY="$PY" HOST_CC="$HOST_CC" BUILD_DIR="$OUT_BUILD" all 2>"$TMP_DIR/make_err.log"; then
    cat "$TMP_DIR/make_err.log"
    exit 1
  fi
  if [[ -s "$TMP_DIR/make_err.log" ]]; then
    echo "FAIL: 固件编译链接出现 stderr 告警："
    cat "$TMP_DIR/make_err.log"
    exit 1
  fi
  "$PY" -B - "$PIO_PKG/toolchain-gccarmnoneeabi/bin/" "$OUT_BUILD" <<'EOF'
import struct, subprocess, sys
tc, bdir = sys.argv[1], sys.argv[2]
def sym(elf):
    out = subprocess.run([tc + 'arm-none-eabi-nm', elf], capture_output=True, text=True, check=True).stdout
    return {l.split()[2]: int(l.split()[0], 16) for l in out.splitlines() if len(l.split()) == 3}
targets = [
    ('l432',     (0x08000000, 0x08040000), (0x20000000, 0x2000C000), ('_SEGGER_RTT', 'main', 'g_tx_frame')),
    ('nrf_s140', (0x00027000, 0x00100000), (0x20006000, 0x20040000), ('_SEGGER_RTT', 'main', 'g_spis_rx')),
    ('nrf_nosd', (0x00000000, 0x00100000), (0x20000000, 0x20040000), ('_SEGGER_RTT', 'main', 'g_spis_rx')),
]
for name, flash, ram, req in targets:
    sp, rst = struct.unpack('<II', open(f'{bdir}/{name}.bin', 'rb').read(8))
    assert ram[0] < sp <= ram[1], f'{name} SP 0x{sp:08X} 越界'
    assert flash[0] <= (rst & ~1) < flash[1] and (rst & 1), f'{name} Reset 0x{rst:08X} 越界'
    s = sym(f'{bdir}/{name}.elf')
    for k in req:
        assert k in s, f'{name} 缺符号 {k}'
    print(f'   {name:8s}: SP=0x{sp:08X}, Reset=0x{rst:08X}, main=0x{s["main"]:08X}')
EOF
  shasum -a 256 "$OUT_BUILD/l432.hex" "$OUT_BUILD/nrf_s140.hex" "$OUT_BUILD/nrf_nosd.hex" | sed "s|$OUT_BUILD/|build/|; s/^/   /"

  # 额外在临时目录核验台架解锁态代码路径（含 start_real_afe / pulse_ads1292_pwdn_reset）零告警链接，产物随 TMP_DIR 自动销毁
  OUT_UNLOCKED="$TMP_DIR/build_unlocked"
  if ! make PY="$PY" HOST_CC="$HOST_CC" BUILD_DIR="$OUT_UNLOCKED" EXTRA_CFLAGS="-DMAKO_C08B_AFE_ENABLED=1 -DMAKO_BENCH_MEASURED=1" \
       "$OUT_UNLOCKED/l432.hex" "$OUT_UNLOCKED/nrf_s140.hex" "$OUT_UNLOCKED/nrf_nosd.hex" >/dev/null 2>"$TMP_DIR/make_unl_err.log"; then
    cat "$TMP_DIR/make_unl_err.log"
    exit 1
  fi
  if [[ -s "$TMP_DIR/make_unl_err.log" ]]; then
    echo "FAIL: 台架解锁态路径编译链接出现 stderr 告警："
    cat "$TMP_DIR/make_unl_err.log"
    exit 1
  fi
  echo "   台架解锁态代码路径零告警链接核验通过（临时目录自动销毁，正式构建仍保持双锁关闭）"
fi

echo "c08b-stream 检查全部通过（未刷机、未上板，默认双硬件锁保持关闭）"

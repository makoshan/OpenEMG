#!/usr/bin/env bash
# 一键验证：P44e<->ADS1292-2ch 跨板引脚与硬件锁核对（含 6 反例）+ C++17 驱动与协议主机单测 + 流边界单测 + 可选 PlatformIO ARM 编译。
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
cd "$HERE"

PY="${PY:-python3}"
CXX="${CXX:-c++}"
CC="${CC:-cc}"

echo "== 1 跨板引脚契约、I2C 禁令与默认硬件锁核对（含 6 项必败反例）"
"$PY" -B check_pins.py --self-test

echo "== 2 主机 C++17 ADS1292 驱动与 F01 流协议单测"
TMP_BIN="$(mktemp -d)"
trap '/bin/rm -rf "$TMP_BIN"' EXIT
"$CC" -std=c11 -Wall -Wextra -Werror -O2 -c src/v12_codec.c -o "$TMP_BIN/v12_codec.o"
"$CC" -std=c11 -Wall -Wextra -Werror -O2 -c src/v12_dsp.c -o "$TMP_BIN/v12_dsp.o"
"$CC" -std=c11 -Wall -Wextra -Werror -O2 -c src/v12_stream.c -o "$TMP_BIN/v12_stream.o"
"$CXX" -std=c++17 -Wall -Wextra -Werror -O2 src/ads1292.cpp test_ads1292.cpp \
  "$TMP_BIN/v12_codec.o" "$TMP_BIN/v12_dsp.o" "$TMP_BIN/v12_stream.o" -lm -o "$TMP_BIN/test_ads1292"
"$TMP_BIN/test_ads1292"

echo "== 3 V12 流边界单测"
"$CC" -std=c11 -Wall -Wextra -Werror -O2 test_stream_boundary.c \
  "$TMP_BIN/v12_codec.o" "$TMP_BIN/v12_dsp.o" "$TMP_BIN/v12_stream.o" -lm -o "$TMP_BIN/test_stream_boundary"
"$TMP_BIN/test_stream_boundary"

if [[ "${1:-}" == "--pio" ]]; then
  PIO_BIN="${PIO_BIN:-$HOME/.local/bin/pio}"
  echo "== 4 PlatformIO ARM 真实镜像编译（ads1292_2k + ads1292_4k）"
  "$PIO_BIN" run -e ads1292_2k -e ads1292_4k
  shasum -a 256 .pio/build/ads1292_2k/firmware.hex .pio/build/ads1292_4k/firmware.hex | sed 's/^/   /'
fi

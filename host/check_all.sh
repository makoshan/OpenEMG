#!/usr/bin/env bash
set -euo pipefail
export PYTHONDONTWRITEBYTECODE=1
cd "$(dirname "$0")"
PY="${PY:-../.venv/bin/python}"
"$PY" ads1298_regs.py --check
"$PY" ads1292_regs.py --check
"$PY" bench_analysis.py --check
"$PY" check_ads_bench_mutations.py
"$PY" wl8_ctrl.py --check
"$PY" ai_confirm.py --check
"$PY" wear_session.py --check
"$PY" check_gesture_pipe.py
"$PY" v12.py --check
"$PY" check_v12_ble.py
"$PY" v12_dongle.py selftest
"$PY" check_v12_imu.py
"$PY" check_v12_status.py
"$PY" check_c08b_stream.py
if [ -f check_wl18_web.py ]; then "$PY" check_wl18_web.py; fi
if [ -f check_live_archive.py ]; then "$PY" check_live_archive.py; fi
"$PY" ../firmware/offline-f01/check.py
"$PY" ../firmware/dsp-f03/check.py
if [ -f ../apple/openEMG/iOS/c08b_dsp.c ]; then
  SW_TMP=$(mktemp -d "${TMPDIR:-/tmp}/openemg-swift.XXXXXX")
  trap 'rm -rf "$SW_TMP"' EXIT
  DSP_SRC="../hardware/8ch-ads1298/r01-bench/firmware-f05/src"
  cc -std=c11 -ffp-contract=off -Wall -Wextra -Werror -I../apple/openEMG/iOS -I"$DSP_SRC" -c ../apple/openEMG/iOS/c08b_dsp.c -o "$SW_TMP/c08b_dsp.o"
  cc -std=c11 -ffp-contract=off -Wall -Wextra -Werror -I"$DSP_SRC" -c "$DSP_SRC/v12_dsp.c" -o "$SW_TMP/v12_dsp.o"
  if [ "$(uname -s)" = "Darwin" ] && command -v swiftc >/dev/null && [ -f ../apple/openEMG/check/main.swift ]; then
    swiftc -import-objc-header ../apple/openEMG/iOS/Bridging.h -Xcc -I../apple/openEMG/iOS -Xcc -I"$DSP_SRC" \
      -o "$SW_TMP/openemg_check" ../apple/openEMG/check/main.swift ../apple/openEMG/iOS/Band.swift "$SW_TMP/c08b_dsp.o" "$SW_TMP/v12_dsp.o"
    "$SW_TMP/openemg_check"
  else
    echo "c08b_dsp C11 编译通过（非 macOS 或无 swiftc，跳过 CoreBluetooth Swift 自检）"
  fi
fi
if "$PY" -c "import torch" >/dev/null 2>&1 && [ -f research/ring_cnn_rewear.py ]; then
  "$PY" research/ring_cnn_rewear.py --check
fi
echo "host 核心自检全部通过"

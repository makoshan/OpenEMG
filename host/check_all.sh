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
"$PY" ../firmware/offline-f01/check.py
"$PY" ../firmware/dsp-f03/check.py
if command -v swiftc >/dev/null && [ -f ../apple/openEMG/check/main.swift ]; then
  SW_TMP=$(mktemp -d "${TMPDIR:-/tmp}/openemg-swift.XXXXXX")
  trap 'rm -rf "$SW_TMP"' EXIT
  DSP_SRC="../hardware/8ch-ads1298/r01-bench/firmware-f05/src"
  cc -std=c11 -ffp-contract=off -I../apple/openEMG/iOS -I"$DSP_SRC" -c ../apple/openEMG/iOS/c08b_dsp.c -o "$SW_TMP/c08b_dsp.o"
  cc -std=c11 -ffp-contract=off -I"$DSP_SRC" -c "$DSP_SRC/v12_dsp.c" -o "$SW_TMP/v12_dsp.o"
  swiftc -import-objc-header ../apple/openEMG/iOS/Bridging.h -Xcc -I../apple/openEMG/iOS -Xcc -I"$DSP_SRC" \
    -o "$SW_TMP/openemg_check" ../apple/openEMG/check/main.swift ../apple/openEMG/iOS/Band.swift "$SW_TMP/c08b_dsp.o" "$SW_TMP/v12_dsp.o"
  "$SW_TMP/openemg_check"
fi
echo "host 核心自检全部通过"

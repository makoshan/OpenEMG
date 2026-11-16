#!/usr/bin/env zsh
set -euo pipefail

SIM_DIR="${0:A:h}"
BUILD_DIR="${SIM_BUILD_DIR:-$SIM_DIR/build}"
mkdir -p "$BUILD_DIR"

if [[ -z "${REPO_DIR:-}" ]]; then
  for cand in "${SIM_DIR:h:h:h:h}" "${SIM_DIR:h:h}"; do
    if [[ -d "$cand/firmware/c08b-bringup" || -d "$cand/v12/c08b-bringup-fw-20261109" ]]; then
      REPO_DIR="$cand"
      break
    fi
  done
fi

if [[ -d "$REPO_DIR/firmware/c08b-bringup" ]]; then
  BRINGUP_DIR="$REPO_DIR/firmware/c08b-bringup"
  STREAM_DIR="$REPO_DIR/firmware/c08b-stream"
  DONGLE_DIR="$REPO_DIR/firmware/ble-dongle"
  X2_DIR="$REPO_DIR/firmware/xiao-ads1292-2ch"
else
  BRINGUP_DIR="$REPO_DIR/v12/c08b-bringup-fw-20261109"
  STREAM_DIR="$REPO_DIR/v12/c08b-stream-fw-20261112"
  DONGLE_DIR="$REPO_DIR/v12/ble-dongle-20261021"
  X2_DIR="$REPO_DIR/v12/ads1292-p44e-xiao-fw-20261112"
fi

CXXFLAGS=(
  -std=c++20 -O2 -fPIC -fms-extensions
  -Wno-pointer-to-int-cast -Wno-unused-parameter -Wno-missing-field-initializers -Wno-deprecated-volatile -Wno-c99-designator -Wno-address-of-temporary
  -I"$SIM_DIR/hw_twin"
  -I"$SIM_DIR/mock_inc"
)

echo "== [1/6] Compile Virtual Hardware Twin (v001_board.cc) =="
clang++ "${CXXFLAGS[@]}" -c "$SIM_DIR/hw_twin/v001_board.cc" -o "$BUILD_DIR/v001_board.o"

echo "== [2/6] Compile & Section-Isolate Sim-1 (c08b-bringup) =="
clang++ "${CXXFLAGS[@]}" -I"$BRINGUP_DIR/common" -I"$BRINGUP_DIR/l432" \
  -DFW_MAIN_C="\"$BRINGUP_DIR/l432/main.c\"" \
  -c "$SIM_DIR/sim1_bringup/sim1_l432_tu.cc" -o "$BUILD_DIR/sim1_l432_raw.o"
ld -r -rename_section __DATA __data __DATA __l432_d \
      -rename_section __DATA __bss  __DATA __l432_b \
      -rename_section __DATA __common __DATA __l432_c \
      "$BUILD_DIR/sim1_l432_raw.o" -o "$BUILD_DIR/sim1_l432.o"

clang++ "${CXXFLAGS[@]}" -I"$BRINGUP_DIR/common" -I"$BRINGUP_DIR/nrf" \
  -DFW_MAIN_C="\"$BRINGUP_DIR/nrf/main.c\"" \
  -c "$SIM_DIR/sim1_bringup/sim1_nrf_tu.cc" -o "$BUILD_DIR/sim1_nrf_raw.o"
ld -r -rename_section __DATA __data __DATA __nrf_d \
      -rename_section __DATA __bss  __DATA __nrf_b \
      -rename_section __DATA __common __DATA __nrf_c \
      "$BUILD_DIR/sim1_nrf_raw.o" -o "$BUILD_DIR/sim1_nrf.o"

clang++ -dynamiclib -O2 "$BUILD_DIR/v001_board.o" "$BUILD_DIR/sim1_l432.o" "$BUILD_DIR/sim1_nrf.o" \
  -o "$BUILD_DIR/libsim1_bringup.dylib"

echo "== [3/6] Compile & Section-Isolate Sim-2 Locked (0/0, S140=1) =="
clang++ "${CXXFLAGS[@]}" -DC08B_USE_S140=1 \
  -I"$STREAM_DIR/common" -I"$STREAM_DIR/l432" \
  -DFW_MAIN_C="\"$STREAM_DIR/l432/main.c\"" \
  -c "$SIM_DIR/sim2_stream/sim2_l432_tu.cc" -o "$BUILD_DIR/sim2_loc_l432_raw.o"
ld -r -rename_section __DATA __data __DATA __l432_d \
      -rename_section __DATA __bss  __DATA __l432_b \
      -rename_section __DATA __common __DATA __l432_c \
      "$BUILD_DIR/sim2_loc_l432_raw.o" -o "$BUILD_DIR/sim2_loc_l432.o"

clang++ "${CXXFLAGS[@]}" -DC08B_USE_S140=1 \
  -I"$STREAM_DIR/common" -I"$STREAM_DIR/nrf" \
  -DFW_MAIN_C="\"$STREAM_DIR/nrf/main.c\"" \
  -c "$SIM_DIR/sim2_stream/sim2_nrf_tu.cc" -o "$BUILD_DIR/sim2_loc_nrf_raw.o"
ld -r -rename_section __DATA __data __DATA __nrf_d \
      -rename_section __DATA __bss  __DATA __nrf_b \
      -rename_section __DATA __common __DATA __nrf_c \
      "$BUILD_DIR/sim2_loc_nrf_raw.o" -o "$BUILD_DIR/sim2_loc_nrf.o"

clang++ -dynamiclib -O2 "$BUILD_DIR/v001_board.o" "$BUILD_DIR/sim2_loc_l432.o" "$BUILD_DIR/sim2_loc_nrf.o" \
  -o "$BUILD_DIR/libsim2_stream_locked.dylib"

echo "== [4/6] Compile & Section-Isolate Sim-2 Bench (1/1 memory-only, S140=1) =="
clang++ "${CXXFLAGS[@]}" -DC08B_USE_S140=1 -DMAKO_C08B_AFE_ENABLED=1 -DMAKO_BENCH_MEASURED=1 \
  -I"$STREAM_DIR/common" -I"$STREAM_DIR/l432" \
  -DFW_MAIN_C="\"$STREAM_DIR/l432/main.c\"" \
  -c "$SIM_DIR/sim2_stream/sim2_l432_tu.cc" -o "$BUILD_DIR/sim2_ben_l432_raw.o"
ld -r -rename_section __DATA __data __DATA __l432_d \
      -rename_section __DATA __bss  __DATA __l432_b \
      -rename_section __DATA __common __DATA __l432_c \
      "$BUILD_DIR/sim2_ben_l432_raw.o" -o "$BUILD_DIR/sim2_ben_l432.o"

clang++ "${CXXFLAGS[@]}" -DC08B_USE_S140=1 -DMAKO_C08B_AFE_ENABLED=1 -DMAKO_BENCH_MEASURED=1 \
  -I"$STREAM_DIR/common" -I"$STREAM_DIR/nrf" \
  -DFW_MAIN_C="\"$STREAM_DIR/nrf/main.c\"" \
  -c "$SIM_DIR/sim2_stream/sim2_nrf_tu.cc" -o "$BUILD_DIR/sim2_ben_nrf_raw.o"
ld -r -rename_section __DATA __data __DATA __nrf_d \
      -rename_section __DATA __bss  __DATA __nrf_b \
      -rename_section __DATA __common __DATA __nrf_c \
      "$BUILD_DIR/sim2_ben_nrf_raw.o" -o "$BUILD_DIR/sim2_ben_nrf.o"

clang++ -dynamiclib -O2 "$BUILD_DIR/v001_board.o" "$BUILD_DIR/sim2_ben_l432.o" "$BUILD_DIR/sim2_ben_nrf.o" \
  -o "$BUILD_DIR/libsim2_stream_bench.dylib"

echo "== [5/6] Compile Sim-3 USB BLE Dongles (XIAO nRF52840 + ESP32-C6 NimBLE) =="
clang++ -std=c++20 -O2 -fPIC -dynamiclib -Wno-unused-parameter -Wno-missing-field-initializers -Wno-deprecated-volatile \
  -I"$SIM_DIR/sim3_dongle/inc_xiao" -I"$X2_DIR/src" \
  -DDONGLE_TARGET="\"YUANLI-C08B\"" \
  -DFW_XIAO_DONGLE_CPP="\"$DONGLE_DIR/xiao-central/src/main.cpp\"" \
  "$SIM_DIR/sim3_dongle/sim3_xiao_dongle_tu.cc" \
  -o "$BUILD_DIR/libsim3_xiao_dongle_c08b.dylib"

clang++ -std=c++20 -O2 -fPIC -dynamiclib -Wno-unused-parameter -Wno-missing-field-initializers -Wno-deprecated-volatile \
  -I"$SIM_DIR/sim3_dongle/inc_xiao" -I"$X2_DIR/src" \
  -DDONGLE_TARGET="\"MAKO-V12-1292-2K\"" -DDONGLE_PEER_MTU \
  -DFW_XIAO_DONGLE_CPP="\"$DONGLE_DIR/xiao-central/src/main.cpp\"" \
  "$SIM_DIR/sim3_dongle/sim3_xiao_dongle_tu.cc" \
  -o "$BUILD_DIR/libsim3_xiao_dongle_1292.dylib"

clang++ -std=c++20 -O2 -fPIC -dynamiclib -Wno-unused-parameter -Wno-missing-field-initializers -Wno-deprecated-volatile -Wno-c99-designator -Wno-address-of-temporary \
  -I"$SIM_DIR/sim3_dongle/inc_c6" \
  -DTARGET_NAME="\"YUANLI-C08B\"" \
  -DFW_C6_DONGLE_C="\"$DONGLE_DIR/c6-central/main/main.c\"" \
  "$SIM_DIR/sim3_dongle/sim3_c6_dongle_tu.cc" \
  -o "$BUILD_DIR/libsim3_c6_dongle_c08b.dylib"

clang++ -std=c++20 -O2 -fPIC -dynamiclib -Wno-unused-parameter -Wno-missing-field-initializers -Wno-deprecated-volatile -Wno-c99-designator -Wno-address-of-temporary \
  -I"$SIM_DIR/sim3_dongle/inc_c6" \
  -DTARGET_NAME="\"MAKO-V12-ADS-2K\"" \
  -DFW_C6_DONGLE_C="\"$DONGLE_DIR/c6-central/main/main.c\"" \
  "$SIM_DIR/sim3_dongle/sim3_c6_dongle_tu.cc" \
  -o "$BUILD_DIR/libsim3_c6_dongle_r01.dylib"

echo "== [6/6] Compile Sim-4 Standalone XIAO nRF52840 + P44e + ADS1292 2CH (Locked + Bench) =="
X2_SRC="$X2_DIR/src"
clang -std=c11 -O2 -fPIC -c "$X2_SRC/v12_codec.c" -o "$BUILD_DIR/x2_codec.o"
clang -std=c11 -O2 -fPIC -c "$X2_SRC/v12_dsp.c" -o "$BUILD_DIR/x2_dsp.o"
clang -std=c11 -O2 -fPIC -c "$X2_SRC/v12_stream.c" -o "$BUILD_DIR/x2_stream.o"
clang++ -std=c++20 -O2 -fPIC -c "$X2_SRC/ads1292.cpp" -o "$BUILD_DIR/x2_ads1292.o"

clang++ -std=c++20 -O2 -fPIC -dynamiclib -Wno-unused-parameter -Wno-missing-field-initializers -Wno-deprecated-volatile \
  -I"$SIM_DIR/sim4_xiao_2ch/inc" -I"$X2_SRC" \
  -DMAKO_V12_AFE_ENABLED=0 -DMAKO_V12_FS=2000 \
  -DFW_XIAO_2CH_CPP="\"$X2_SRC/main.cpp\"" \
  "$SIM_DIR/sim4_xiao_2ch/sim4_xiao_2ch_tu.cc" \
  "$BUILD_DIR/x2_ads1292.o" "$BUILD_DIR/x2_stream.o" "$BUILD_DIR/x2_codec.o" "$BUILD_DIR/x2_dsp.o" \
  -o "$BUILD_DIR/libsim4_xiao_2ch_locked.dylib"

mkdir -p "$BUILD_DIR/x2_bench_src"
command cp -f "$X2_SRC"/*.h "$X2_SRC/main.cpp" "$BUILD_DIR/x2_bench_src/"
cat > "$BUILD_DIR/x2_bench_src/bench_release.h" << 'BEOF'
#pragma once
#define MAKO_BENCH_MEASURED 1
#define MAKO_BENCH_POR_US 1000000u
#define MAKO_BENCH_REFERENCE_US 150000u
BEOF

clang++ -std=c++20 -O2 -fPIC -dynamiclib -Wno-unused-parameter -Wno-missing-field-initializers -Wno-deprecated-volatile \
  -I"$SIM_DIR/sim4_xiao_2ch/inc" -I"$BUILD_DIR/x2_bench_src" \
  -DMAKO_V12_AFE_ENABLED=0 -DMAKO_V12_FS=2000 \
  -DFW_XIAO_2CH_CPP="\"$BUILD_DIR/x2_bench_src/main.cpp\"" \
  "$SIM_DIR/sim4_xiao_2ch/sim4_xiao_2ch_tu.cc" \
  "$BUILD_DIR/x2_ads1292.o" "$BUILD_DIR/x2_stream.o" "$BUILD_DIR/x2_codec.o" "$BUILD_DIR/x2_dsp.o" \
  -o "$BUILD_DIR/libsim4_xiao_2ch_bench.dylib"

echo "BUILD_ALL_9_DYLIBS_OK"

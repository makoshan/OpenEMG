#!/usr/bin/env bash
set -euo pipefail
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
"$PY" ../firmware/offline-f01/check.py
"$PY" ../firmware/dsp-f03/check.py
echo "host 核心自检全部通过"

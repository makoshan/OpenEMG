# 软件与开发环境

| 模块 | 目录 | 说明 |
|---|---|---|
| **嵌入式固件与协议** | `firmware/` | `c08b-bringup`（`v0.01 MCU-U9` 及 `R4U6/R4U6N` 双核 `L432 + nRF52840` 首板十项自检与主机解码器）、`c08b-stream`（`2 / 8 / 16` 通道自适应 BLE `F01 v1/v4` 流式采集契约）、`xiao-ads1292-2ch`（`ADS1292 + P44e + XIAO` 2 路 BLE `F01` 流式固件）、`xiao-f04`（XIAO 合成参考流）、`ble-dongle`（低延迟无线接收器）、`offline-f01`（帧编解码）、`dsp-f03`（定点滤波）、`cheez-s3`（单路入门）；8 路真实 AFE + IMU 固件见 `hardware/8ch-ads1298/r01-bench/firmware-f05/` |
| **电脑端核心服务** | `host/` | Python 多设备统一采集、50 Hz 陷波与 20–400 Hz 带通、Hudgins 特征、收缩 LDA / 自适应重戴识别、指尖按压力估计（`wl8_force.py`）、首板脚位与 `c08b-bringup` 在线解码 API、台架噪声/CMRR 评估与 SMT 门禁工具 |
| **桌面与网页工作台** | `app/` | Electron + React + Web Serial：支持 `16 / 8 / 2 / 1` 通道切换、佩戴底噪红线检查、动作录制、模型训练、首板对线与自检解码面板及陀螺仪光标控制 |
| **iPhone + Watch 端** | `apple/openEMG/` | SwiftUI iOS + watchOS 源码：BLE 接收 `F01` 数据流、实时八路波形与手表端手势/确认卡联动 |
| **采集质量门禁** | `emg_gate/` | 接触不良、工频干扰、削顶饱和与重戴偏移自动判定 CLI，含 JSON Schema 与 **170 项单元测试** |
| **游戏与机器人控制** | `game/tianjie/`、`duck/` | Three.js 结印手势实时交互场景，以及肌电控制 Microduck 双足机器人行走与作揖强化学习实验 |
| **EDA 互转工具** | `tools/` | `kicad10_to_9_nets.py`：将 KiCad 10 PCB 转为嘉立创 EDA 专业版可无损带网络导入的格式 |

---

## 在仓库根目录运行检查和桌面工作台

需要 Python 3.12（推荐 [uv](https://docs.astral.sh/uv/)）和 Node.js 22：

```bash
# 1. 创建虚拟环境并安装核心依赖
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -r requirements.txt jsonschema scipy scikit-learn pyserial bleak h5py Pillow zstandard

# 2. 跑通公开仓合规门禁（含 9/9 反例与 .epro2/.f3d 穿透）、3D 完备性门禁（4/4 反例）、固件协议门禁与原理图逐脚对板
.venv/bin/python scripts/check_public_hygiene.py --selftest
.venv/bin/python scripts/check_public_hygiene.py .
.venv/bin/python scripts/check_3d_completeness.py --selftest
.venv/bin/python scripts/check_3d_completeness.py .
.venv/bin/python scripts/check_fab_packs.py --selftest
.venv/bin/python scripts/check_fab_packs.py .
.venv/bin/python hardware/16ch-u9-dual30/verify_interface.py --selftest
.venv/bin/python firmware/c08b-bringup/tools/pins_u9.py --selftest
.venv/bin/python firmware/c08b-bringup/tools/decode_bringup.py --self-test
PY=.venv/bin/python bash firmware/c08b-stream/check.sh
PY=.venv/bin/python bash firmware/xiao-ads1292-2ch/check.sh
.venv/bin/python hardware/common-mainboard/schematics/check_all.py
.venv/bin/python hardware/16ch-c08b-round/schematics-afe/check_all.py
.venv/bin/python hardware/8ch-ads1298/stacked-d20-8ch/verify_8ch_dnp.py

# 3. 跑通 170 项采集质检单测与主机信号处理自检
.venv/bin/python -m unittest discover -s emg_gate/tests -p "test_*.py"
PY=.venv/bin/python bash host/check_all.sh

# 4. 启动统一桌面工作台
cd app && npm install && npm start
```

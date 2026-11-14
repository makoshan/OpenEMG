# OpenEMG

OpenEMG 是用于手势研究的表面肌电（sEMG）平台。仓库提供 2、8、16 通道采集板的硬件工程、固件和上位机，以及配套表带与外壳的 3D 文件。

**开发进展**　8 通道 R01 台架板已做过实板测试。在一次 10 分钟的短接输入测试中，上位机收到 1,187,774 帧，归档核对未发现序号缺口。腕带版已整理设计与制造文件，整机装配和佩戴采集仍待实物验证。

表面肌电是肌肉收缩时皮肤表面出现的微伏级电压。手环读取多路差分肌电与手腕角速度（IMU），电脑端通过几分钟的个人校准训练分类器，实时输出细微手势、按压力度或机器人控制指令。

本项目用于算法研究、黑客松原型与硬件工程探索，**不是商业产品，也不是医疗器械**。

![OpenEMG 成品整表与双通道一体盒正反三维光追渲染预览（斜视）](hardware/renders/openemg-finished-iso-dark.png)

| 模块化开源复刻套件防静电 EVA 收纳示意（斜视） | 16ch / 8ch / 2ch 三档共用壳体叠板立体爆炸图（斜视） |
|---|---|
| ![套件收纳包装光追渲染预览](hardware/renders/openemg-kit-packaging-iso-dark.png) | ![三档叠板立体爆炸组装图光追渲染预览](hardware/renders/openemg-assembly-exploded-iso-dark.png) |

| 多档位 34P 柔性电极软板、TPU 定位层与连续表带系统 | 板底直焊六触点、外扣六孔底盖与 Pod D1 干电极微距 |
|---|---|
| ![表带系统三维光追渲染预览](hardware/renders/openemg-strap-system-iso-dark.png) | ![镀金干电极微距三维光追渲染预览](hardware/renders/openemg-electrodes-iso-dark.png) |

![C08B 采集板 D20、共用主控 R4U6 与整机叠装三维光追渲染预览（斜视）](hardware/renders/c08b-overall-iso-dark.png)

> *以上均为基于本仓原生 KiCad PCB（`.kicad_pcb`）与参数化三维结构（`.step` / `.glb`）生成的 Blender Cycles 影棚三维光追设计预览，**非实物照片，不代表制造或人体佩戴验收通过**；其中套件收纳图为模块化开源复刻防静电 EVA 收纳示意，非商业零售包装。全套 8 组 16 张正交俯视与透视斜视 `2400 × 1350` 高清渲染图及一键复现脚本见 [`hardware/renders/`](hardware/renders/)。*

---

## 安全与复刻前提（动手前必读）

> [!CAUTION]
> **人体电安全红线（完整条款见 [SAFETY.md](SAFETY.md)）**
> 1. **严禁插着市电充电器或直连电脑 USB 时将任何版本的电极佩戴在人体上。** 机身内不含医疗级加强绝缘 USB 隔离器；人体佩戴仅允许使用单节锂电池供电并通过蓝牙无线连接。
> 2. **硬件互锁默认开启，严禁擅自短接旁路跳线。** 主控板 `JP701` 默认严禁贴装（DNP）；2 通道板 `R32`（`0 Ω` USB 掉电互锁）默认必须贴装。离体台架若需插 USB 联调模拟前端，前端必须串接 **耐压 ≥ 1 kV 的独立外置 USB 隔离器**，且电极严禁接触人体。
> 3. **防呆警告：`P44e` 转接板的 `J1` 第 19 脚引出了 `5V`，仅限连接 `2ch-ads1292` 载板（用于驱动其 VBUS 掉电互锁管），严禁插到其他未做 5V 隔离的旧版载板。**

---

## A · 统一硬件家族：一个主控 + 三档采集下层板 + 同尺寸壳体

三档穿戴采集板统一采用 **`43.10 × 36.50 mm` 四层板框**（同时提供配螺丝壳 `R12` 的**四角圆孔版**与配无螺丝抱柱壳 `R13` 的**四角缺口版**），通过东南角同款 20P `0.5 mm` FPC 座（`FH34SRJ-20S-0.5SH`）与上层主控叠装互联，上电零跳线自动识别 `2ch / 8ch / 16ch` 板型：

```text
[16ch 小型化旗舰独立配对]                           [2ch / 8ch / 16ch 双34P 共用配对]
  上层 6层主控 Rev0.01 (FPC1 东侧 20P)                上层共用主控 R4U6 / R4U6N 或 入门转接板 P44e
              │ (严禁与右侧跨系列混插!)                             │ (南侧 J_AFE 20P)
              ▼                                         ┌──────────┼──────────┐
  下层 4层超薄双30P采集板 AFE-30P                        ▼          ▼          ▼
  + 双30P四层保护软板 strap-fpc-30p               [2ch-ads1292] [8ch-ads1298] [16ch-c08b-round]
              │                                         └──────────┴──────────┘
              ▼                                                    ▼
  [9.60 mm 超薄圆润手表壳 enclosure-u9-watch]       [46 × 40 mm 圆润外壳家族 (enclosure-46x40)]
              └─────────────────────────┬──────────────────────────┘
                                        ▼
                       [统一上位机: host/ + app/ + apple/openEMG]
```

| 模块 | 目录 | 板框 / 层数 | EDA 工程格式 | 定位与状态 |
|---|---|---|---|---|
| **16 通道小型化旗舰（双 30P）** | `hardware/16ch-u9-dual30/` | `43.1 × 36.5 mm` 四角 `R1.8`（主控 6 层 `0.8 mm` + 采集 4 层 `0.8 mm`） | 嘉立创 `OpenEMG-C08B-Mainboard-Rev0.01.epro2` / `AFE-30P.epro2` + KiCad 10 四层软板 `strap-fpc-30p` + 满载 `-3d.step` + `enclosure-u9-watch` | **当前 16ch 主力推荐**：`26.64 × 20.90 mm` 原矩形电池窗主控 `Rev0.01` + `1.0 mm` 超薄双 30P 座 `C324727` + `32×100k + 2×200k` 软板 + `46.8 × 40.0 × 9.6 mm` 超薄圆润手表壳 |
| **共用上层主控（34P/入门系）** | `hardware/common-mainboard/` | `R4U6` / `R4U6N`: `43.1 × 36.5 mm` 4 层<br>`P44e`: `17.8 × 21.0 mm` 2 层 | 嘉立创 `.epcb2` / `.epro2` + KiCad 10 + 满载 `-3d.step` | `R4U6`（圆孔）/ `R4U6N`（缺口）与入门 `P44e`（`XIAO` 转接）任选 |
| **入门 2 通道叠板** | `hardware/2ch-ads1292/` | `43.1 × 36.5 mm` / 4 层 | KiCad 10 + 嘉立创 `ADS1292-2ch-R9.epro2` + `-3d.step` | `ADS1292` 底面直接集成两排「大—辅—大」六触点，免外部表带排线 |
| **标准 8 通道叠板 + 台架** | `hardware/8ch-ads1298/` | `43.1 × 36.5 mm`（圆孔 `D20-8CH` / 缺口 `D20N-8CH`）<br>`65.0 × 60.0 mm`（R01 台架） | KiCad 10 + 嘉立创 `C08B-8ch全套汇总(R4U6/R4U6N).epro2` + 单面 `-3d.step` + `strap-fpc-d2-8ch` | 纯单面专属 8 路叠板（背面 0 器件绿油绝缘）+ 单片四层软板 `D2-8CH` + `F04` 背开口 TPU 表带 + 已实测 `R01` 台架板 |
| **16 通道双 34P 叠板** | `hardware/16ch-c08b-round/` | `43.1 × 36.5 mm` / 4 层（圆孔 `D20` / 缺口 `D20N`） | KiCad 10 + 嘉立创 `C08B-全套汇总(R4U6/R4U6N).epro2` + 双面 `-3d.step` + `pod-d1` | 双 `ADS1298` 同步采样 + 34P 四层柔性表带软板（`D2` / `R15`）+ 独立电极豆 `Pod D1` |
| **圆润外壳家族** | `hardware/enclosure-46x40/` | `46.0 × 40.0 mm` 外廓 | `build123d` Python + Fusion `.f3d` + STEP + STL + 3MF + GLB | 四角螺丝壳 `R12`（配 `R4U6+D20`）、无螺丝缺口抱柱壳 `R13`（配 `R4U6N+D20N`，附 `.f3d`）、外扣底盖 `D2` 与 2ch 外壳 `R7` |

> **机械对位与嘉立创下单总表**：`MCU-U9 + AFE-30P` 通过东侧 20P 软排线 U 形正对互联；`R4U6` 主控 `J_AFE` 与 `8ch/16ch D20` 采集板 `J_AFE` 均位于板心偏东 `+14.34 mm`，上下 **`0.00 mm` 完全正对**；`2ch-ads1292` 载板的 `J2`（`X=+12.00 mm`）与 `P44e` `0.00 mm` 正对，若改配 `R4U6` 叠装横向仅偏 **`2.34 mm`**，用约 `25 mm` 软排线微斜过渡即可。架构细节见 [hardware/README.md](hardware/README.md)，**全家族 15 套直接上传 Gerber/BOM/CPL 制造包与 SHA-256 核对表见 [hardware/ORDER-MATRIX.md](hardware/ORDER-MATRIX.md)**。

---

## B · 软件、固件与下游应用矩阵

| 模块 | 目录 | 说明 |
|---|---|---|
| **嵌入式固件与协议** | `firmware/` | `c08b-bringup`（`L432 + nRF52840` 双核自检固件）、`xiao-ads1292-2ch`（`ADS1292 + P44e + XIAO` 2 路 BLE `F01` 流式固件）、`xiao-f04`（XIAO 合成参考流）、`ble-dongle`（低延迟无线接收器）、`offline-f01`（帧编解码）、`dsp-f03`（定点滤波）、`cheez-s3`（单路入门）；8 路真实 AFE + IMU 固件见 `hardware/8ch-ads1298/r01-bench/firmware-f05/` |
| **电脑端核心服务** | `host/` | Python 多设备统一采集、50 Hz 陷波与 20–400 Hz 带通、Hudgins 特征、收缩 LDA / 自适应重戴识别、指尖按压力估计（`wl8_force.py`）、台架噪声/CMRR 评估与 SMT 门禁工具 |
| **桌面与网页工作台** | `app/` | Electron + React + Web Serial：支持 1 / 2 / 8 / 16 / 18 通道切换、佩戴底噪红线检查、动作录制、模型训练与陀螺仪光标控制 |
| **iPhone + Watch 端** | `apple/openEMG/` | SwiftUI iOS + watchOS 源码：BLE 接收 `F01` 数据流、实时八路波形与手表端手势/确认卡联动 |
| **采集质量门禁** | `emg_gate/` | 接触不良、工频干扰、削顶饱和与重戴偏移自动判定 CLI，含 JSON Schema 与 **170 项单元测试** |
| **游戏与机器人控制** | `game/tianjie/`、`duck/` | Three.js 结印手势实时交互场景，以及肌电控制 Microduck 双足机器人行走与作揖强化学习实验 |
| **EDA 互转工具** | `tools/` | `kicad10_to_9_nets.py`：将 KiCad 10 PCB 转为嘉立创 EDA 专业版可无损带网络导入的格式 |

---

## C · 不带硬件，5 分钟跑通验证链与上位机

需要 Python 3.12（推荐 [uv](https://docs.astral.sh/uv/)）和 Node.js 22：

```bash
# 1. 创建虚拟环境并安装核心依赖
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -r requirements.txt jsonschema scipy scikit-learn pyserial bleak h5py Pillow

# 2. 跑通公开仓合规门禁（含 9/9 反例与 .epro2/.f3d 穿透）、3D 完备性门禁（4/4 反例）与原理图逐脚对板
.venv/bin/python scripts/check_public_hygiene.py --selftest
.venv/bin/python scripts/check_public_hygiene.py .
.venv/bin/python scripts/check_3d_completeness.py --selftest
.venv/bin/python scripts/check_3d_completeness.py .
.venv/bin/python scripts/check_fab_packs.py --selftest
.venv/bin/python scripts/check_fab_packs.py .
.venv/bin/python hardware/16ch-u9-dual30/verify_interface.py --selftest
.venv/bin/python firmware/c08b-bringup/tools/pins_u9.py --selftest
.venv/bin/python hardware/common-mainboard/schematics/check_all.py
.venv/bin/python hardware/16ch-c08b-round/schematics-afe/check_all.py
.venv/bin/python hardware/8ch-ads1298/stacked-d20-8ch/verify_8ch_dnp.py

# 3. 跑通 170 项采集质检单测与主机信号处理自检
.venv/bin/python -m unittest discover -s emg_gate/tests -p "test_*.py"
PY=.venv/bin/python bash host/check_all.sh

# 4. 启动统一桌面工作台
cd app && npm install && npm start
```

---

## D · 许可证

- **硬件与结构设计**（`hardware/` 下的全部原理图、KiCad 工程、嘉立创 `.epro2/.epcb2` 工程、制造包与 3D 结构文件）：采用强互惠开源硬件协议 **[CERN-OHL-S-2.0](LICENSE-HARDWARE)**（CERN Open Hardware Licence Version 2 – Strongly Reciprocal）。修改本硬件并分发设计文件或实物时，须以相同 `CERN-OHL-S-2.0` 协议公开完整设计源文件。
- **软件、固件、客户端与脚本**（`app/`、`apple/`、`host/`、`emg_gate/`、`firmware/`、`game/`、`duck/`、`tools/`、`scripts/`）：采用 **[MIT License](LICENSE)**；第三方开源组件与参考资料声明见 **[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)**。

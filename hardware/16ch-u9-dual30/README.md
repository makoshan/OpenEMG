# 16 通道 U9 圆角主控 + 双 30 针采集板（2026-11-13 开源修订版）

本目录收录 `ProDoc_主控主板_2026-11-13`（6 层圆角挖电池窗主控 `MCU-U9`）与 `采集板_2026-11-13`（4 层双 30 针 `AFE-30P`）配对工程及其嘉立创直接上传制造包（Gerber / SMT BOM / CPL），按 [CERN-OHL-S-2.0](../../LICENSE-HARDWARE) 发布。

## 文件清单

| 路径 | 说明 |
|---|---|
| `MCU-U9.epro2` | 6 层主控板（`STM32L432KCU6` `U1` + `nRF52840-QIAA` `U9`，`R=1.80 mm` 四角圆角 + `27.40 × 20.90 mm` 电池开窗） |
| `AFE-30P.epro` / `AFE-30P.epro2` | 4 层 16 路采集板（双 `ADS1298IPAGR` `U1/U2` + 双 30P 表带座 `FPC1/FPC3` + 20P 主控接口 `FPC2`） |
| `fab-mcu-u9/Gerber_MCU-U9.zip` | `MCU-U9` 6 层单板 Gerber（`GTL, G1..G4, GBL` + `GKO` + `PTH/NPTH`，已剔除 14 处手焊/DNP 钢网开窗） |
| `fab-mcu-u9/Gerber_MCU-U9-panel702.zip` | `MCU-U9` 自带 `70.20 × 70.20 mm` 工艺边（`2.0 mm` 铣槽 + 四边断口连接筋）一拼一 Gerber |
| `fab-mcu-u9/jlc_smt_bom.csv` / `jlc_smt_cpl.csv` | `MCU-U9` 嘉立创 SMT 物料清单与贴片坐标（45 种 / 110 颗：Top 42 + Bottom 68，100% 含立创 `C` 料号） |
| `fab-afe-30p/Gerber_AFE-30P.zip` | `AFE-30P` 4 层单板 Gerber（`GTL, G1, G2, GBL` + `GKO` + `PTH`） |
| `fab-afe-30p/jlc_smt_bom.csv` / `jlc_smt_cpl.csv` | `AFE-30P` 嘉立创 SMT 物料清单与贴片坐标（23 种 / 114 颗：Top 64 + Bottom 50，100% 含立创 `C` 料号） |
| `verify_interface.py` | 20P 反序排线逐脚对账、`ADS1298` `RESV1=GND`、铺铜规则与制造包一键自检脚本 |
| `SHA256SUMS` | 本目录全部开源工程与制造包的 SHA-256 校验表 |

## 已修复的工程与制造问题（嘉立创 EDA 专业版 `4.1.93` 原生复核通过）

### 1. 主控板 `MCU-U9`（6 层，`43.10 × 36.50 mm`）
- **扩宽电池镂空窗以容纳 `26.59 × 19.67 × 2.78 mm` 电池**：电池开窗 `a6b31685508e342e` 东侧扩至 `X = 40.853 mm`（净开窗 **`27.400 × 20.900 mm`**，东侧梁宽 `2.00 mm`，东南角阶梯避让 `SCREW3`），同步更新 `Inner3/Inner4` 内电层镂空框，并重铺全部 10 块铜皮（`10/10 POURED`）。
- **四角 `R=1.80 mm` 圆角板框与北边拉平**：消除原版北边 `0.166 mm` 倾斜，统一四角圆弧与内电层退缩外框。
- **消除全部网络飞线与孤立铜皮**：将 `BUTTON_N` 走线 `aa2a5e4ee3874f57` 延伸至 `SW300.1` 焊盘中心 `324.087 mil`，移除 2 处孤立泪滴，西南角地过孔 `cc7fc0d843f8c411` 内移至 `-1303 mil`；原生 DRC **0 间距/几何/连接错误、0 飞线**。
- **原理图与 PCB 充电芯片同步**：`U17` 统一为 `LTC4054ES5-4.2#TRPBF`（`SOT-23-5`，立创 `C462648`）。
- **钢网防连锡处理**：单板与 `70.2 × 70.2 mm` 工艺边 Gerber 已自动剔除 `J301`、`JP701`、`D62`、`BT1`、`ANT1` 等 14 处手焊/空贴焊盘钢网开孔。

### 2. 采集板 `AFE-30P`（4 层，`43.10 × 36.50 mm`）
- **20P 反序排线 `FPC2.17 / 18` 交叉修复**：`FPC2` 第 17 脚改接 `CS#2`（`U2.39`，对 `MCU-U9 J302.4 PA2`），第 18 脚改接 `DRDY2#`（`U2.47`，对 `MCU-U9 J302.5 PA0`），过孔 `e1998` 移至 `(130.5, 79.23834) mil`。
- **双 `ADS1298` 第 31 脚 `RESV1` 修正为数字地 `GND`**：依 TI `ADS1298` 数据手册（`RESV1` 必须接 `DGND`），将原理图（`1.esch` `e95/e300`）与 PCB（`U1.31`、`U2.31` 及相连过孔/短线）从 `AGND` 改为 `GND`，消除原理图与 PCB 网表差异（`0 Netlist Error`）。
- **消除 `Inner1` 负片死铜短路与 13 处热焊盘未连**：将 `Inner2`（`layer 16`）由负片 `PLANE` 转为正片 `SIGNAL` + `POUR e1678 (GND)`，并将铜皮连接规则 `RULE 7` 设为直连（`DIRECT`，`connType=1`），在 `LCEDA-Pro 4.1.93` 重建全部 14 块铺铜（`17` 个 `POURED` 区），彻底消除 `DRDY2#` 过孔与 `Inner1 AGND` 间距报错及 `FPC2`/`LM27762` 热焊盘辐条悬空；原生 DRC **0 错误、0 飞线、0 网表不一致**。
- **补齐全部 SMT 立创料号**：补齐 `C1, C2`（`22uF` `0402` `C105226`）与 `C4, C34`（`10uF` `0402` `C7472949`），整板 23 种 / 114 颗贴片件 100% 具备有效 `C` 料号。

## 20 芯反序排线逐脚映射（`MCU-U9 J302` pin $k$ ↔ `AFE-30P FPC2` pin $21-k$）

| `MCU-U9 J302` 脚 | 主控网络 | `AFE-30P FPC2` 脚 | 采集板网络 | 功能说明 |
|---:|---|---:|---|---|
| 1, 2 | `3V3_AFE` | 20, 19 | `3V3` | 3.3V 受控供电 |
| 3 | `PA8` | 18 | `CLKSEL` | 时钟源选择 |
| 4 | `PA2` | 17 | `CS#2` | 从片 `U2` 片选 |
| 5 | `PA0` | 16 | `DRDY2#` | 从片 `U2` 数据就绪中断 |
| 6 | `SPI1_MISO` | 15 | `SPI_MISO` | SPI MISO |
| 7, 8, 9, 20 | `GND` | 14, 13, 12, 1 | `GND` | 多点数字地回流 |
| 10 | `SPI1_SCK` | 11 | `SPI_SCLK` | SPI 时钟 |
| 11 | `PB0` | 10 | `CS#1` | 主片 `U1` 片选 |
| 12 | `PA3` | 9 | `START` | 同步采样启动 |
| 13 | `NC` | 8 | `CLK` | 悬空（板载缓冲时钟） |
| 14 | `PA1` | 7 | `RESET#` | 硬件复位 |
| 15 | `PA4` | 6 | `PWDN#` | 硬件掉电控制 |
| 16 | `SPI1_MOSI` | 5 | `SPI_MOSI` | SPI MOSI |
| 17 | `PB1` | 4 | `GPIO1` | 通用 GPIO1 |
| 18 | `PB5` | 3 | `DRDY1#` | 主片 `U1` 数据就绪中断 |
| 19 | `PB6` | 2 | `GPIO2` | 通用 GPIO2 |

## 复核命令

```bash
python3 hardware/16ch-u9-dual30/verify_interface.py
(cd hardware/16ch-u9-dual30 && shasum -a 256 -c SHA256SUMS)
```

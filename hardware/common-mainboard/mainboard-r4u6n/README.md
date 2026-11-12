# C08B 双核共用主控板 `R4U6N`（四角缺口版，配无螺丝外壳 `R13`）

- **板框与结构配对**：外形包络 `43.10 × 36.50 mm`（4 层、`0.6 mm` 板厚 `JLC04061H-3313`，树脂塞孔+电镀盖帽），去掉四角 `M1.6` 安装孔 `H901..H904`，改为与无螺丝抱柱外壳 [`c08b-shell-r13-notch`](../../enclosure-46x40/c08b-shell-r13-notch/) 配套的四角缺口（西北/东北/西南 `3.0 × 3.0 mm`，东南 `J_AFE` 侧 `3.0 × 2.6 mm`）；中部 `20.90 × 27.40 mm` 电池开窗与东侧 Type-C 沉板凹口与圆孔版 [`mainboard-r4u6`](../mainboard-r4u6/) 完全一致。
- **电气与 BOM 同源**：器件位号（47 种 109 颗，Top 66 + Bottom 43）、坐标、4 层走线及 `U18.31 PH3/BOOT0 = VBUS_SENSE`（免焊线插 USB 上电进 STM32 ROM DFU）与 `R4U6` 100% 相同，通过 20P `0.5 mm` FPC `J_AFE` 零跳线自动识别并连接下层 `D20N`（16ch 双面）、`D20N-8CH`（8ch 单面）或 `2ch-ads1292`。
- **关键文件**：
  - `C08B-main-R4U6N.epcb2`：嘉立创 EDA 专业版原生 4 层 PCB 源档（`firmware/c08b-bringup/tools/pins.py` 直接逐脚核对）。
  - `c08b-mainboard-r4u6n-3d.step`：满载整板三维装配 STEP 模型（四角缺口板框 + 全器件 3D 实体）。
  - `C08B-main-R4U6N-gerber.zip` / `jlc_smt_bom.csv` / `jlc_smt_cpl.csv`：可直接投板的 4 层 Gerber 压缩包与嘉立创 SMT 贴片清单/坐标。

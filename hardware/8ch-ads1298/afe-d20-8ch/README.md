# C08B 纯单面 8 通道采集板 · 圆孔版 D20-8CH（2026-11-12）

基于 C08B 正面基准布局 人工正面布局与已修清全部安全/电气缺陷的 `../../16ch-c08b-round/afe-d20/afe-d20-silk.kicad_pcb`（`31323826…`）派生，同步吸收 `ProPrj_ads1298v3.4` 单颗 ADS1298 八路拓扑：

- **纯正面单面贴**：保留正面全部 76 颗贴片器件（`V4_U1` ADS1298 CH1–8、`V4_FPC1` 34P、`J_AFE` 20P、`V4_LM27762` ±2.5V、`V4_X1` 2.048 MHz、`D910–D927` ESD401、`V4_U3–U6` 15k 排阻、`V4_C72–C79` 22 pF 差分电容、`V4_R18` 0R 单点接地、`V4_R34` 392 kΩ RLD 限流）+ `TP901/TP902` + `H901–H904`；删除背面全部 53 个封装（51 颗贴片 + `TP903/TP904`）。
- **背面整面绿油绝缘**：`B.Paste = 0`、`B.Mask = 0`，背面无裸露焊盘或凸起阻容，可直接贴合 `302025` 锂电池；省去双面贴片换面费。
- **主控与外壳 1:1 兼容**：板框 `43.10 × 36.50 mm` 与 `D20` 完全一致，`J_AFE`（20P）与主控板 `R4U6` 逐脚对插（3/4 脚 `ADS_DRDY_B`/`ADS_CS_B` 置为 `NC`）。
- **走线与 DRC**：仅对原借道背面焊盘连通正面的 7 条网络补齐纳米级 135°/共线桥接，剪除 140 段残桩与 10 颗单端过孔，倒角 `V4_REF2` 原三岔口留下的 1 处 90° 拐角。KiCad 10 DRC（含重铺）0 违规 / 0 未连，`route_lint` 七项硬指标全 0，`smt_dfm_gate` 通过。

## 图纸、逐针核对表与嘉立创工程（对标 16 通道 v0.01 交付标准）

| 文件 / 目录 | 说明 |
|---|---|
| [`PINOUT-AND-REVIEW.md`](PINOUT-AND-REVIEW.md) · [`pinout-34p-20p.csv`](pinout-34p-20p.csv) | **34P 表带接口（`V4_FPC1`）与 20P 板间接口（`J_AFE` `k ↔ 21−k`）逐针核对总表**、固件寄存器表、制造包 SHA-256 绑定与五阶段验收记录表 |
| [`views/schematic.pdf`](views/schematic.pdf) | **11 页全套矢量可搜索原理图 PDF**（P1 整机框图、P2 电源树、P3–P7 主控板 `R4U6`、P8–P11 采集板 `D20-8CH`） |
| [`views/afe-schematic.pdf`](views/afe-schematic.pdf) | **6 页采集板独立矢量可搜索原理图 PDF**（P1 整机框图、P2 电源树、P3–P6 采集板详图；同步更新 [`schematics-8ch/C08B-8ch采集板原理图-D20-8CH-20261113.pdf`](schematics-8ch/C08B-8ch采集板原理图-D20-8CH-20261113.pdf)） |
| [`views/d20-8ch-wiring-orientation.svg`](views/d20-8ch-wiring-orientation.svg) · [`.png`](views/d20-8ch-wiring-orientation.png) | **贴肤侧 18 枚电极编号（盒底 6 + 北短带 4 + 南长带 8）与 34P/20P 座子开口朝向核对图** |
| [`views/d20-8ch-system-zh.svg`](views/d20-8ch-system-zh.svg) · [`-en.svg`](views/d20-8ch-system-en.svg) | P1 整机框图（中英双语矢量图） |
| [`views/d20-8ch-power-zh.svg`](views/d20-8ch-power-zh.svg) · [`-en.svg`](views/d20-8ch-power-en.svg) | P2 电源树与实测记录栏（中英双语矢量图） |
| [`views/afe-copper.png`](views/afe-copper.png) · [`views/schematic-afe-input-preview.png`](views/schematic-afe-input-preview.png) | 4 层铜皮预览与 34P 电极输入保护页预览 |
| [`jlc-eda/C08B-8ch全套汇总-主控R4U6-采集D20-8CH单面.epro2`](jlc-eda/C08B-8ch全套汇总-主控R4U6-采集D20-8CH单面.epro2) | 嘉立创 EDA 专业版全套双板工程（含 **11 页原理图**：`01.01 整机框图`、`01.02 电源树`、主控 5 页、采集 4 页） |
| [`jlc-eda/C08B-AFE采集板-D20-8CH-单面8路-原理图+PCB+3D.epro2`](jlc-eda/C08B-AFE采集板-D20-8CH-单面8路-原理图+PCB+3D.epro2) | 嘉立创 EDA 专业版采集板独立工程（含 **6 页原理图**：`01.01 整机框图`、`01.02 电源树`、采集 4 页） |

状态：**待人工工程师独立审板**（自动化逐脚对板与 DRC 已过；未人工审板、未打样、未上台架、未过人体安全门）。

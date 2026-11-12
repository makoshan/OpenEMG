# 入门 2 通道底面六触点一体叠板（`2ch-ads1292`）

> **验证状态**：已实现未实物验收（KiCad 原生 DRC 0 违规 / 0 未连，158 脚逐焊盘对真源 0 差，走线规矩硬项全 0；尚未打样贴肤）。

## 统一家族特性

- **同尺寸圆角板框**：`43.10 × 36.50 mm`（R4.6 圆角，四孔 `±19.05, ±15.75 mm`），四层 `0.8 mm`，底面直接集成两排「大—辅—大」六触点电极焊盘（CH1±、CH2± + 双 RLD 辅点，免外接表带软板）。
- **上层主控二选一**：
  1. 配入门上层板 [`../common-mainboard/adapter-p44e-xiao/`](../common-mainboard/adapter-p44e-xiao/)（直焊 `XIAO nRF52840`，20P 座 `J2` 与 `P44e J1` X 坐标 `0.00 mm` 完全正对）。
  2. 配旗舰双核主控 [`../common-mainboard/mainboard-r4u6/`](../common-mainboard/mainboard-r4u6/)（20P 引脚电气完全兼容；横向仅差 `2.34 mm`，用约 `25 mm` 软排线微斜过渡）。
- **配套圆角外壳**：见 [`../enclosure-46x40/ads1292-shell-r7/`](../enclosure-46x40/ads1292-shell-r7/)（含总装 `host.step` 与单件可打印 `shell.step`/`lid.step`/`.stl`；装机贴肤前必须阅读 [SINGLE-FAULT.md](SINGLE-FAULT.md)，拔除物理 USB 并做好电极孔防水密封）。

## 目录结构

- `schematics/`：电气真源 `design.py`、单页原理图生成与几何比对 `page1.py`、可读 PDF `ADS1292-双通道原理图-R9-20261112.pdf`。
- `board/`：自包含 KiCad 10 PCB（`ads1292-2ch.kicad_pcb`）、满载器件与底面电极铜片的整板三维模型 **`ads1292-2ch-3d.step`**、拼板与制造包 `fab/`（Gerber / `jlc_smt_bom.csv` / `jlc_smt_cpl.csv`）。
- `jlc-eda/`：**嘉立创 EDA 专业版单文件工程** `ADS1292-2ch-R9-原理图+PCB+3D.epro2`。

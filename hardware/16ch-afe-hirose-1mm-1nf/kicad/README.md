# OpenEMG v0.01（16CH 双板 + 九页原理图）— KiCad 8 原生工程

本目录由同级 [`../OpenEMG_v0.01_DualBoard.epro2`](../OpenEMG_v0.01_DualBoard.epro2)（`OpenEMG_v0.01_双板工程_九页原理图_20261115.epro2`）1:1 转换生成，完整保留双板封装焊盘、过孔、铜线、铺铜区域（`zone`）、可见位号丝印（遵循 `.epru` `Designator.valueVisible`）、`LM1` 散热焊盘双窗钢网分割（`78.2%`），以及全部 9 页原理图与立创 `LCSC` / `MPN` 属性。可直接用 **KiCad 8.0+** 或 **Backplane GPUI** 打开查看与联调。

## 目录结构

| 子目录 | 包含文件 | 对应源工程与说明 |
| :--- | :--- | :--- |
| [`02-afe-16ch-r01b/`](02-afe-16ch-r01b/) | `openemg-v001-16ch-afe.kicad_pro`<br>`openemg-v001-16ch-afe.kicad_pcb`<br>`openemg-v001-16ch-afe.kicad_sch` | **`02 采集板（AFE-16CH，R01b）`**：`43.10 × 36.50 mm` 四角 `R1.80` 4 层板（150 器件 = 146 贴片 + 4 定位孔、2239 段铜线、234 过孔、14 铜皮 + `LM1` 双窗钢网）+ `02.01 / 02.02` 合并原理图 |
| [`01-mainboard-c08b-u9/`](01-mainboard-c08b-u9/) | `openemg-v001-mainboard-u9.kicad_pro`<br>`openemg-v001-mainboard-u9.kicad_pcb`<br>`openemg-v001-mainboard-u9.kicad_sch` | **`01 主控板（C08B-U9，OpenEMG）`**：`43.10 × 36.50 mm` 四角 `R1.80` 6 层板（`STM32L432KB + nRF52840`，128 器件、1114 段铜线、204 过孔、24 铜皮）+ `01.01 ~ 01.07` 合并原理图 |
| [`nine-pages-sch/`](nine-pages-sch/) | `01_01.kicad_sch` ～ `01_07.kicad_sch`<br>`02_01.kicad_sch` ～ `02_02.kicad_sch` | **9 页独立单页 KiCad 原理图**：`01.01` 整机框图、`01.02` 电源树、`01.03–01.07` 主控电路、`02.01` 双 `ADS1298R` 与模拟电源、`02.02` 双 30P 广濑接口与 32 路 `ESD401DPYR` 滤波网络 |

> **投产提示**：打板与 SMT 贴片请直接使用上级目录经人工工程师逐脚审核定版的生产制造包（[`../Gerber_AFE-30P.zip`](../Gerber_AFE-30P.zip)、[`../Gerber_C08B-U9_v0.01.zip`](../Gerber_C08B-U9_v0.01.zip)、[`../jlc_smt_bom.csv`](../jlc_smt_bom.csv)、[`../jlc_smt_cpl.csv`](../jlc_smt_cpl.csv)）。

# 8 通道 ADS1298 硬件模块（`8ch-ads1298`）

本目录同时提供纯单面专属 8 通道穿戴叠板、双面通用板单面贴片子集、离体台架开发板及配套柔性表带结构：

1. **`afe-d20-8ch/` 与 `afe-d20n-8ch/`（`43.1×36.5 mm` 纯单面专属 8 通道采集板 · 推荐打样）**
   - 正面 76 颗贴片件，背面 **0 器件、`B.Paste = 0`、`B.Mask = 0`**（100% 绿油绝缘铜皮直接贴合 `302025` 锂电池，免双面贴片翻面费）。
   - **`afe-d20-8ch/`（圆孔版，配螺丝壳 `R12` + 主控 `R4U6`）**：含自包含 KiCad 10 PCB、满载整板 `afe-d20-8ch-3d.step`、4 页专属原理图 `schematics-8ch/`（306 脚逐脚对板）、`fab/` 拼板 Gerber 与 `jlc-eda/` 两份嘉立创工程。
   - **`afe-d20n-8ch/`（四角缺口版，配无螺丝壳 `R13` + 主控 `R4U6N`）**：BOM/CPL 与圆孔版逐字节一致，含四角缺口 KiCad 10 PCB、满载整板 `afe-d20n-8ch-3d.step`、`fab/` 拼板 Gerber 与 `jlc-eda/` 两份嘉立创工程（单板 + 含 `R4U6N` 与 `D2-8CH` 软板的全套汇总）。
2. **`strap-fpc-d2-8ch/`（8 通道单片 4 层柔性表带软板 `D2-8CH`）**
   - 单片直插 `V4_FPC1` 34P 座，覆盖胶囊底 2 路 + 2 辅助（双 `200 kΩ` 独立保护串阻，零悬空贴肤金属）与表带 6 路（北 2 路 + 南 4 路），胶囊背面带 6 窗 `0.20 mm` PI 垫片直接复用现成外壳底盖（`fit_3d_check.py` 实测 `0.0 mm³` 零干涉）；含自包含 KiCad 10 工程、`check.py` 20 道门自检、37 实体满载 `strap-d2-8ch-3d.step`、`fab/` 嘉立创 FPC+SMT 直传包（`strap-d2-8ch-gerber.zip` `7ed551d4`，含 `0.10/0.20 mm` 分厚补强层、全基础库 BOM/CPL 与 `.d356` 电测网表）与 `jlc-eda/C08B-表带软板-D2-8CH单片.epro2`。
3. **`stacked-d20-8ch/`（`16ch D20` 共板单面贴片 BOM/CPL 兼容包）**
   - 若手头已有 16 通道 `D20` 裸板，可直接使用本目录的单面 BOM/CPL 仅贴正面 76 颗元件，随附单面贴片构型三维模型 **`c08b-afe-d20-8ch-single-3d.step`** 与校验脚本 `verify_8ch_dnp.py`。
4. **`r01-bench/`（`65.0×60.0 mm` 离体杜邦线台架开发板 `V12-R01` · 已实板验证）**
   - 含 12 页原生 KiCad 原理图、自包含封装库、四层 `1.6 mm` PCB、满载器件整板三维模型 **`v12-r01-3d.step`**、分组 BOM/CPL、`F05` 固件（硬件锁默认关闭）与离体台架验收表 `BENCH-ACCEPTANCE.md`。
5. **`f04-strap-fpc/` 与 `f04-openback-tpu/`（另一路 8 通道弹片软板与背开口一体 TPU 表带套件）**
   - `f04-strap-fpc/`：原生 KiCad 10 工程、自包含几何原语与整板 `fpc-f04-3d.step`。
   - `f04-openback-tpu/`：自包含 `build123d` 参数化源码 `build.py`、单排壳 `shell.step`/`shell-print.stl`、9 排连续内衬 `liner.step`/`liner-print.stl` 与装配总成 `assembled.step`。
6. **`jlc-eda/`**：收录 `F04-八通道软板-原理图+PCB.epro2`；8ch 叠板主机与 `D2-8CH` 软板嘉立创工程分别见 `afe-d20-8ch/jlc-eda/`、`afe-d20n-8ch/jlc-eda/` 与 `strap-fpc-d2-8ch/jlc-eda/`。

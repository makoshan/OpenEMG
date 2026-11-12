# C08B 16 通道双面采集板 `D20`（圆孔版，配螺丝壳 `R12`）

- **板框与工艺**：`43.10 × 36.50 mm`（四角 `R4.6 mm` 圆角 + 4 个 `Ø1.7 mm` 安装孔 `H901..H904`），4 层 `0.8 mm`（`JLC04081H-3313`），沉金，过孔盖油。
- **器件与接口**：正反双面双 `ADS1298` 同步采样（24 种物料共 127 颗贴片件，16 颗输入差分电容为 `22 pF` `C76924`），东南角 20P `0.5 mm` `J_AFE` 与主控板 `R4U6` 正对互联，双 34P 软板座连接 [`../strap-fpc-d2/`](../strap-fpc-d2/) 或 [`../strap-fpc-r15/`](../strap-fpc-r15/)。
- **打样与贴片投产三件套**：
  1. 工艺边拼板 Gerber：`panel/c08b-afe-d20-panel-gerber.zip`（`70.2 × 70.2 mm` 一拼一邮票孔工艺边，只传此拼板包，不传单板 `gerber/` 目录）
  2. 物料清单：`jlc_smt_bom.csv`
  3. 贴片坐标：`jlc_smt_cpl.csv`（采用单板原点，与拼板 Gerber 同坐标系；SMT 预览请核对 `V4_U2`、`V4_FPC3` 及 36 颗 ESD 极性方向）
- **三维模型与自检**：
  - 满载整板 STEP：`c08b-afe-d20-3d.step`（连接器模型随附于 `assembly/models/FPC2-fh34.step`）
  - 源板 `afe-d20-silk.kicad_pcb`（SHA-256 `31323826…`）：KiCad 10 DRC 0 违规 / 0 未连，`route_lint.py` 硬项全 0，`panel/check_panel.py` 通过。

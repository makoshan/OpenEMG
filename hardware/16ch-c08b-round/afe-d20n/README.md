# C08B 16 通道双面采集板 `D20N`（四角缺口版，配无螺丝抱柱壳 `R13`）

- **板框与结构配对**：`43.10 × 36.50 mm` 四角方缺口板框（去掉 `H901..H904` 安装孔，NW/NE/SW 缺口 `3.0 × 3.0 mm`、SE 缺口 `3.0 × 2.6 mm`），配四角缺口主控 [`../../common-mainboard/mainboard-r4u6n/`](../../common-mainboard/mainboard-r4u6n/) 与无螺丝抱柱外壳 [`../../enclosure-46x40/c08b-shell-r13-notch/`](../../enclosure-46x40/c08b-shell-r13-notch/)。4 层 `0.8 mm`（`JLC04081H-3313`），沉金，过孔盖油。
- **电气与 BOM 同源**：127 颗贴片件、走线、过孔与圆孔版 [`../afe-d20/`](../afe-d20/) 逐项一致，`jlc_smt_bom.csv` 与 `jlc_smt_cpl.csv` 逐字节相同。
- **打样与贴片投产三件套**：
  1. 工艺边拼板 Gerber：`panel/c08b-afe-d20n-panel-gerber.zip`（`70.2 × 70.2 mm` 一拼一邮票孔工艺边；订单备注可注明「四角缺口内角按铣刀圆角即可」，掰板后打磨邮票孔连接筋毛刺再装入 `R13` 抱柱）
  2. 物料清单：`jlc_smt_bom.csv`
  3. 贴片坐标：`jlc_smt_cpl.csv`
- **三维模型与自检**：
  - 满载整板 STEP：`c08b-afe-d20n-3d.step`
  - 源板 `afe-d20n.kicad_pcb`（SHA-256 `e37f9734…`）：KiCad 10 DRC 0 违规 / 0 未连，缺口外扩 `0.25 mm` 内四层无铜，`panel/check_panel.py` 通过。

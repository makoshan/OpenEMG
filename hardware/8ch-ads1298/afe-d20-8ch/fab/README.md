# C08B 单面 8 通道采集板制造包 · 圆孔版 D20-8CH（2026-11-12）

- 源板：`../afe-d20-8ch.kicad_pcb`（SHA-256 `7615e0774d70…`）
- 下单只传三个：`panel/c08b-afe-d20-8ch-panel-gerber.zip`（70.2×70.2 mm 一拼一工艺边，正面 3 MARK、背面 0 MARK）、`jlc_smt_bom.csv`、`jlc_smt_cpl.csv`；根目录单板 zip 不入库、不传平台。
- 贴片面：**单面贴（Top）**，4 层 `JLC04081H-3313`（0.8 mm），24 种物料共 76 颗贴片件（BOM/CPL 仅 Top 行）。
- 开口核对：单板 `F_Paste = 305`、`B_Paste = 0`、`F_Mask = 307`、`B_Mask = 0`，PTH 249、NPTH 4；工艺边拼板 `panel_mm = [70.2, 70.2]`，邮票孔到铜最小净距 `0.36 mm`，DRC 0/0。
- 自检：`KPY -B make_fab.py`；`cd panel && KPY -B check_panel.py`（通过）。

状态：已实现未验收，未传平台审单、未下单。

# C08B 纯单面 8 通道采集板 · 四角缺口版 D20N-8CH（2026-11-12）

由 `../afe-d20-8ch/build_afe_8ch.py` 从 `../../16ch-c08b-round/afe-d20n/afe-d20n.kicad_pcb`（`e37f9734…`）生成：器件、走线、过孔与圆孔版 `D20-8CH` 逐项一致，仅去掉 `H901–H904` 四颗安装孔并将四角改为与主控板 `R4U6N`、上盖 `R13` 匹配的方缺口（NW/NE/SW `3.0×3.0 mm`，SE `3.0×2.6 mm`）。

- 正面 76 颗贴片器件 + `TP901/TP902`，背面 0 器件（`B.Paste = 0`、`B.Mask = 0`）。
- KiCad 10 DRC（含重铺）0 违规 / 0 未连，`route_lint` 七项硬指标全 0，`smt_dfm_gate` 通过。

状态：已实现未验收。

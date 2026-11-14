# `strap-fpc-30p` 制造包说明

本目录包含 `strap-30p-a` 与 `strap-30p-b` 两片四层柔性表带软板的嘉立创 FPC + SMT 打样文件（由 `make_fab.py` 从冻结源板生成，源板字节零改动，并经 `gnet_fpc.py` 像素级四层铜 + 镀通孔连通与 6 项断路/短路/漏孔反例核验通过）。

## 文件清单

| 文件 | 用途 |
|---|---|
| `strap-30p-a-gerber.zip` / `strap-30p-b-gerber.zip` | 四层铜、阻焊、丝印、钢网、外框、金属化钻孔及 `0.10 mm` / `0.20 mm` 分厚 PI 补强 Gerber |
| `strap-30p-a-jlc-bom.csv` / `strap-30p-b-jlc-bom.csv` | 嘉立创 SMT 物料清单（`C25741` 100kΩ 0402 × 16 + `C25811` 200kΩ 0603 × 1，全基础库） |
| `strap-30p-a-jlc-cpl.csv` / `strap-30p-b-jlc-cpl.csv` | 嘉立创 SMT 贴片坐标表 |
| `strap-30p-a.d356` / `strap-30p-b.d356` | IPC-D-356 飞针电测网表 |
| `stiffener-map-a.png` / `stiffener-map-b.png` | B 面分厚 PI 补强定位示意图（供下单备注附图） |
| `工艺要求.md` | 嘉立创 FPC 与 SMT 审单工艺说明 |
| `SOURCE.json`、`gnet-a.json`、`gnet-b.json` | 源板 SHA-256 绑定清单与 Gerber 离线像素飞针核验结果 |

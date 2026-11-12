# D2-8CH 单片四层表带软板制造包（`fab/`）

状态：**已实现未验收（Gerber 像素级反推网表 0 断 0 短 + 3 反例全红，嘉立创三项预检门全绿；未上传平台审单、未打样）。**

## 1. 交付物清单

| 文件 | 用途 |
|---|---|
| `strap-d2-8ch-gerber.zip` | 上传嘉立创 FPC 下单页的 Gerber 压缩包（含 4 层铜、双面阻焊/钢网/丝印、`Edge_Cuts`、PTH/NPTH 钻孔、`0.10mm` 与 `0.20mm` 分层实心 PI 补强 Gerber） |
| `strap-d2-8ch.d356` | IPC-D-356 飞针电测网表 |
| `jlc_smt_bom.csv` | 嘉立创 SMT BOM（全基础库：`C25741` 100k 0402 × 16 + `C25811` 200k 0603 × 2，0 换料费） |
| `jlc_smt_cpl.csv` | 嘉立创 SMT 双面坐标文件（F 面 12 颗 + B 面 6 颗，全部 `0.0°` 水平放置） |
| `stiffener-map.png` | 发给嘉立创 CAM 核对的 B 面 `0.10mm / 0.20mm` PI 补强分色顶视定位图（含胶囊 6 窗避让串阻示意） |
| `工艺要求.md` | 嘉立创下单备注与钢网开孔特别说明 |
| `SOURCE.json` | 锁定源板 `strap-d2-8ch.kicad_pcb`（`17c3693a…`）与各产物 SHA-256 指纹 |
| `fab_facts.json` | `fab_facts.py` 实测几何、钻孔、钢网与 BOM/CPL 对账结果 |
| `gnet.json` | `gnet_fpc.py` 从上传 `Gerber.zip` 像素级反推 4 层铜 + 69 个镀铜孔对 `pin-map.json` 独立核对结果（88 焊盘、37 网、0 断 0 短） |

## 2. 一键复现与核验

```bash
KPY=/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3
$KPY -B make_fab.py
```

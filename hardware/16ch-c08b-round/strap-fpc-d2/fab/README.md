# D2 16 路双片四层表带软板制造包（`fab/`）

状态：**已实现未验收（A/B 两片 Gerber 像素级反推网表 0 断 0 短 + 6 个必败反例全红，嘉立创三项预检门全绿；未上传平台审单、未打样、A/B 胶囊 EB2 灌锡对焊未实测）。**

## 1. 交付物清单

| 片别 | Gerber 压缩包 | 电测网表 | SMT BOM（全基础库） | SMT 坐标 | 补强定位图 | 事实与反推报告 |
|---|---|---|---|---|---|---|
| **A 片**（CH1–8 + EB1 + EB2A） | `strap-a-gerber.zip` | `strap-a.d356` | `strap-a-jlc-bom.csv`（17 颗） | `strap-a-jlc-cpl.csv` | `stiffener-map-a.png` | `strap-a-fab-facts.json`, `strap-a-gnet.json` |
| **B 片**（CH9–16 + EB2） | `strap-b-gerber.zip` | `strap-b.d356` | `strap-b-jlc-bom.csv`（17 颗） | `strap-b-jlc-cpl.csv` | `stiffener-map-b.png` | `strap-b-fab-facts.json`, `strap-b-gnet.json` |

另含 `工艺要求.md`（嘉立创 CAM 工艺与钢网备注）与 `SOURCE.json`（锁定源板 `strap-a` `36560282…`、`strap-b` `7c229f21…` 指纹）。

## 2. 一键复现

```bash
KPY=/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3
$KPY -B make_fab.py
```

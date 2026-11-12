# F04 八通道软板导入嘉立创EDA（2026-11-05）

状态：已实现未验收。交付文件 `exports/嘉立创-F04-八通道软板-20261105/F04-八通道软板-原理图+PCB.epro2`，含原理图和 PCB。下单仍以 `v12/strap-f04-order/F04-FPC-样品打样5片.zip` 为准；软板源文件和订单未改。

## 重出步骤

官方 CLI 要在 Bash 沙箱外跑（沙箱里 `open` 不返回）。全程用无头会话，不碰别的窗口。

1. `python3 tools/kicad10_to_9_nets.py ../fpc-f04.kicad_pcb fpc-f04-k9.kicad_pcb`：KiCad 10 写法导入会丢铜线。
2. `python3 k9_no_tail_paste.py fpc-f04-k9.kicad_pcb`：尾端 17 个手焊盘本来没有 F.Paste，嘉立创导入后会自动开钢网，这里加负余量关掉。
3. K9 板连同 `.kicad_pro`、`.kicad_sch`、`FPC.kicad_sym`、两个 lib-table、`FPC.pretty/` 压成 zip，板文件名用 `fpc-f04.kicad_pcb`。
4. easyeda-eprj3 的 `init.js` 建空工程，`python3 import_f04.py <工程.eprj3> <zip>` 导入并配板。
5. `../../c08-eprj3-20261102/sync_uid.py <工程文件夹>` 配对元件编号，`python3 apply_rules_f04.py <工程.eprj3>` 写规则（铜间距 0.10、线宽 ≥ 0.15、铜到板边 0.30）。
6. `../../c08-eprj3-20261102/export_epro2.py <工程.eprj3> <输出.epro2>`。

## 验证（量导出的文件，不只量源工程）

| 项 | 结果 | 证据 |
|---|---|---|
| 器件 / 走线 / 飞线 | 18 = 18，799 = 799，飞线 0 | `verify-source.json`、`reimport-check.json` |
| 焊盘网络 | 34 个逻辑脚 0 不符；17 网长度差 0 | `verify-source.json` |
| 嘉立创解析的原理图网表对 PCB | 34 脚 0 不符 | `native-check.json` |
| 导回后 DRC | 只剩 Netlist Error 1 条 | `reimport-check.json` |
| DRC 阳性对照 | 注入异网短线报 2 条线距、1 条焊盘距、2 条连接错误，删除后恢复 | `reimport-check.json` |
| 铜 / 覆盖膜开窗 / 钢网 Gerber 对下单包 | 异或面积 0.0006 / 0 / 0 mm² | `gerber-diff.json` |
| Gerber 比对阳性对照 | 修钢网前报差异 30.6 mm²，正好是 17 × 3.0 × 0.6 | 本轮输出 |

## 已知差异

- **Netlist Error 1 条**：原理图和 PCB 的器件属性不同（`Name`、`Channel ID`、引脚名等），网络一致。改 PCB 的 `Name` 后这条仍在，没再追。
- **丝印字更小**：26 个字内容和中心位置都对，嘉立创字体比 KiCad 小约四成。
- **板框线宽**：中心线都是 186.8×23 mm；嘉立创线宽 0.15，下单包 0.05。
- **未比对**：PI 补强只作为自定义层上的矩形框导入。叠层没写成 106 µm 软板，在嘉立创里一键下单不能代替 `FAB-SPEC.md`。

`fpc-f04-k9.kicad_pcb` 是中间板，不入库，也不要拿回 KiCad 改。

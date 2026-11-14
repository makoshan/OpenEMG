# OpenEMG 共用主控家族（2 / 8 / 16 通道）嘉立创制造包与联调总表

本文档提供全系 17 套嘉立创（JLCPCB）直接上传生产包（Gerber `.zip`、SMT `BOM.csv`、贴片坐标 `CPL.csv` 与飞针网表 `.d356`）的精确路径、工艺参数与 SHA-256 指纹核对表，并由 [`scripts/check_fab_packs.py`](../scripts/check_fab_packs.py) 在 CI 中逐字节锁定核验。

> [!CAUTION]
> **打样与安全必读**
> 1. **切勿在嘉立创 EDA 内点击「从原理图更新 PCB」后直接下单**：`.epro2` 工程仅供查看原理图、走线与三维预览；正式打板与贴片请直接上传下表锁定的 Gerber `.zip`、`BOM.csv` 与 `CPL.csv`。
> 2. **人体电安全红线（详见 [SAFETY.md](../SAFETY.md)）**：主控 `JP701` 默认空贴（DNP），2 路板 `R32`（`0 Ω`）默认必贴；**严禁插着市电充电器或直连电脑 USB 时将电极接触人体**。
> 3. **严禁跨系列混插 20P 排线（防 `3V3_AFE` 对 `GND` 硬短路）**：新版旗舰 `OpenEMG-C08B-Mainboard-Rev0.01`（东侧 `FPC1.1=GND, 19/20=3V3_AFE`）**仅限配对 `AFE-30P`**（使用 20P 同面 A 型软排线 U 形反折实现 `k ↔ 21−k`）；`R4U6 / R4U6N`（南侧 `J_AFE.1/2=3V3_AFE, 20=GND`）**仅限配对 `D20 / D20N / D20-8CH / D20N-8CH / ADS1292-2ch`**。两套体系的 20P 首尾电源极性正好相反，**严禁跨系列混插或 `1 ↔ 1` 直连**。

---

## A · 上下板互换与固件免跳线自动识别矩阵

两套 20P 体系分别在各自配对组内互连（旗舰组 `OpenEMG-C08B-Mainboard-Rev0.01` 经东侧 **20P `0.5 mm` A 型同面软排线** U 形反折连 `AFE-30P`；经典组 `R4U6 / R4U6N` 经南侧 **20P `0.5 mm` 反向软排线** 如立创 `C22434842` 连三档下层采集板）；`firmware/c08b-bringup` 与 `firmware/c08b-stream` 上电通过 `afe_detect(id_a, id_b)` 自动识别通道档位：

| 档位组合 | 上层主控（二选一外形） | 下层采集板 | 表带 / 电极侧 | 固件自动识别（`afe_mode_t`） | 自检掩码 |
|---|---|---|---|---|---|
| **16 通道旗舰（双 30P）** | `OpenEMG-C08B-Mainboard-Rev0.01`（6 层 `0.8 mm` 圆角原矩形窗，仅配 `AFE-30P`） | `AFE-30P`（4 层 `0.8 mm` 圆角，双 `ADS1298` + 双 `1.0 mm` 30P `C324727`） | 双片 4 层软板 `strap-fpc-30p`（`strap-30p-a` + `strap-30p-b`，`32×100k + 2×200k` 限流串阻） | `id_a=0x92, id_b=0x92` → `AFE_16CH (16)` | `0x03FF` |
| **16 通道全腕（双 34P）** | `R4U6`（圆孔）或 `R4U6N`（缺口） | `D20`（圆孔）或 `D20N`（缺口），正反双 `ADS1298` | 双片 4 层软板 `D2`（`strap-a` + `strap-b`，32+2 触点） | `id_a=0x92, id_b=0x92` → `AFE_16CH (16)` | `0x03FF` |
| **8 通道单面** | `R4U6`（圆孔）或 `R4U6N`（缺口） | `D20-8CH`（圆孔）或 `D20N-8CH`（缺口），纯顶面单颗 `ADS1298` | 单片 4 层软板 `D2-8CH`（`strap-d2-8ch`，16+2 触点，胶囊背带 6 窗 `0.20 mm` PI 垫片） | `id_a=0x92, id_b∈{0x00,0xFF}` → `AFE_8CH (8)` | `0x03F5` |
| **2 通道一体** | `R4U6` / `R4U6N`；或入门转接板 `P44e` + XIAO | `ADS1292-2ch`（顶面贴件、底面 6 焊盘手焊铜片） | 底面自带两排「大—辅—大」6 触点（免外部表带软板） | `(id_a&0xDF)==0x53, id_b∈{0x00,0xFF}` → `AFE_2CH (2)` | `0x03F5` |

> 若 `id_b` 读出非空非 `0x92` 杂值，或 `U1` 无响应仅 `U2` 在线，`afe_detect()` 返回 `AFE_NONE (0)` 报错拦截，不会将故障 16 路板误降级为单芯片模式。

---

## B · 嘉立创直接上传制造包清单（全家族 17 套，按 SHA-256 前 8 位核对）

| 编号 | 板件与版本 | 关键板厂工艺与贴片面 | 仓内精确路径（相对仓库根） | SHA-256 前 8 位 |
|---|---|---|---|---|
| `01` | **共用主控板 `R4U6`**（圆孔） | 4 层 `0.6 mm` `JLC04061H-3313`，沉金，**树脂塞孔+电镀盖帽**，单板 `43.10×36.50 mm`（勾选**非常规人工代拼 ≥70×70**），**双面贴**（47 种 / 109 颗：Top 66 + Bottom 43） | `hardware/common-mainboard/mainboard-r4u6/C08B-main-R4U6-gerber.zip`<br>`hardware/common-mainboard/mainboard-r4u6/jlc_smt_bom.csv`<br>`hardware/common-mainboard/mainboard-r4u6/jlc_smt_cpl.csv` | `b714cccc`<br>`038dde47`<br>`ac566c41` |
| `02` | **共用主控板 `R4U6N`**（缺口） | 同上（四角装配缺口，NPTH 0；BOM/CPL 与 `R4U6` 逐字节相同） | `hardware/common-mainboard/mainboard-r4u6n/C08B-main-R4U6N-gerber.zip`<br>`hardware/common-mainboard/mainboard-r4u6n/jlc_smt_bom.csv`<br>`hardware/common-mainboard/mainboard-r4u6n/jlc_smt_cpl.csv` | `68ef0932`<br>`038dde47`<br>`ac566c41` |
| `03` | **8 路单面采集板 `D20-8CH`**（圆孔） | 4 层 `0.8 mm` `JLC04081H-3313`，沉金，过孔盖油，自带 `70.20×70.20 mm` 工艺边，**纯顶面单面贴**（24 种 / 76 颗） | `hardware/8ch-ads1298/afe-d20-8ch/fab/panel/c08b-afe-d20-8ch-panel-gerber.zip`<br>`hardware/8ch-ads1298/afe-d20-8ch/fab/jlc_smt_bom.csv`<br>`hardware/8ch-ads1298/afe-d20-8ch/fab/jlc_smt_cpl.csv` | `adefd36d`<br>`4d330ad0`<br>`ba082820` |
| `04` | **8 路单面采集板 `D20N-8CH`**（缺口） | 同上（BOM/CPL 与 `D20-8CH` 逐字节相同） | `hardware/8ch-ads1298/afe-d20n-8ch/fab/panel/c08b-afe-d20n-8ch-panel-gerber.zip`<br>`hardware/8ch-ads1298/afe-d20n-8ch/fab/jlc_smt_bom.csv`<br>`hardware/8ch-ads1298/afe-d20n-8ch/fab/jlc_smt_cpl.csv` | `82ba95e5`<br>`4d330ad0`<br>`ba082820` |
| `05` | **8 路单片表带软板 `D2-8CH`** | 4 层压延铜 FPC（`0.203 mm`，`105.20×26.20 mm`），沉金 `2u"`，含实心补强层 `0.10 mm`（金手指）+ `0.20 mm`（12 岛 + 胶囊 6 窗垫片，与 `tray_d2/cap_d2` 零干涉）；全基础库双面贴 **2 种 / 18 颗**（`C25741`×16 + `C25811`×2） | `hardware/8ch-ads1298/strap-fpc-d2-8ch/fab/strap-d2-8ch-gerber.zip`<br>`hardware/8ch-ads1298/strap-fpc-d2-8ch/fab/jlc_smt_bom.csv`<br>`hardware/8ch-ads1298/strap-fpc-d2-8ch/fab/jlc_smt_cpl.csv`<br>`hardware/8ch-ads1298/strap-fpc-d2-8ch/fab/strap-d2-8ch.d356` | `7ed551d4`<br>`5ec689fd`<br>`5c1213bd`<br>`86a917c5` |
| `06` | **16 路双面采集板 `D20`**（圆孔） | 4 层 `0.8 mm` `JLC04081H-3313`，沉金，过孔盖油，自带 `70.20×70.20 mm` 工艺边，**双面贴**（24 种 / 127 颗：Top 76 + Bottom 51） | `hardware/16ch-c08b-round/afe-d20/panel/c08b-afe-d20-panel-gerber.zip`<br>`hardware/16ch-c08b-round/afe-d20/jlc_smt_bom.csv`<br>`hardware/16ch-c08b-round/afe-d20/jlc_smt_cpl.csv` | `a5f52ffe`<br>`445bea42`<br>`0c6c4d22` |
| `07` | **16 路双面采集板 `D20N`**（缺口） | 同上（BOM/CPL 与 `D20` 逐字节相同） | `hardware/16ch-c08b-round/afe-d20n/panel/c08b-afe-d20n-panel-gerber.zip`<br>`hardware/16ch-c08b-round/afe-d20n/jlc_smt_bom.csv`<br>`hardware/16ch-c08b-round/afe-d20n/jlc_smt_cpl.csv` | `511283a6`<br>`445bea42`<br>`0c6c4d22` |
| `08` | **16 路表带软板 `D2-A`**（A 片） | 4 层压延铜 FPC（`0.203 mm`，`105.20×26.20 mm`），沉金 `2u"`，实心补强层 `0.10 mm` + `0.20 mm`（12 岛；`A+B` 叠层与 `tray_d2/cap_d2` 及层间 `0.0 mm³` 零干涉）；全基础库双面贴 **2 种 / 17 颗**（`C25741`×16 + `C25811`×1） | `hardware/16ch-c08b-round/strap-fpc-d2/fab/strap-a-gerber.zip`<br>`hardware/16ch-c08b-round/strap-fpc-d2/fab/strap-a-jlc-bom.csv`<br>`hardware/16ch-c08b-round/strap-fpc-d2/fab/strap-a-jlc-cpl.csv`<br>`hardware/16ch-c08b-round/strap-fpc-d2/fab/strap-a.d356` | `b7aa2a09`<br>`8f02ec30`<br>`d61ce0af`<br>`2a639737` |
| `09` | **16 路表带软板 `D2-B`**（B 片） | 4 层压延铜 FPC（`0.203 mm`，`150.51×26.20 mm`），沉金 `2u"`，实心补强层 `0.10 mm` + `0.20 mm`（16 岛）；全基础库双面贴 **2 种 / 17 颗**（`C25741`×16 + `C25811`×1） | `hardware/16ch-c08b-round/strap-fpc-d2/fab/strap-b-gerber.zip`<br>`hardware/16ch-c08b-round/strap-fpc-d2/fab/strap-b-jlc-bom.csv`<br>`hardware/16ch-c08b-round/strap-fpc-d2/fab/strap-b-jlc-cpl.csv`<br>`hardware/16ch-c08b-round/strap-fpc-d2/fab/strap-b.d356` | `43175156`<br>`cffbbd76`<br>`a45ef4a2`<br>`b91204df` |
| `10` | **2 路六触点板 `ADS1292-2ch`** | 4 层 `0.8 mm` FR-4，沉金，过孔塞油，自带 `70.20×70.20 mm` 工艺边，**纯顶面单面贴**（22 种 / 47 颗；底面 `E1–E6` 手焊铜片） | `hardware/2ch-ads1292/board/fab/ads1292-2ch-panel-gerber.zip`<br>`hardware/2ch-ads1292/board/fab/jlc_smt_bom.csv`<br>`hardware/2ch-ads1292/board/fab/jlc_smt_cpl.csv` | `bdd44d31`<br>`614e0854`<br>`2a2bc50e` |
| `11` | **XIAO 转接板 `P44e`** | 2 层 `0.8 mm` FR-4（`17.78×21.00 mm`）光板手焊（不开钢网，不走 SMT） | `hardware/common-mainboard/adapter-p44e-xiao/fab-20261106/p44e-gerber.zip` | `044240f6` |
| `12` | **新版 6 层圆角主控 `OpenEMG-C08B-Mainboard-Rev0.01`** | 6 层 `0.8 mm` FR-4，沉金，**树脂塞孔+电镀盖帽**，自带 `70.20×70.20 mm` 工艺边（同时提供单板 `OpenEMG-C08B-Mainboard-Rev0.01-Gerber.zip` `344dc71f`），`26.64×20.90 mm` 原矩形电池窗（无中央 DEBUG 框），**双面贴**（45 种 / 110 颗：Top 42 + Bottom 68，CPL 保持默认「AD 等其他」） | `hardware/16ch-u9-dual30/fab-mcu-u9/OpenEMG-C08B-Mainboard-Rev0.01-panel702-Gerber.zip`<br>`hardware/16ch-u9-dual30/fab-mcu-u9/jlc_smt_bom.csv`<br>`hardware/16ch-u9-dual30/fab-mcu-u9/jlc_smt_cpl.csv` | `f45c3233`<br>`a20d1163`<br>`ab8bce02` |
| `13` | **新版超薄双 30P 采集板 `AFE-30P`** | 4 层 `0.8 mm` `JLC04081H-3313`（`43.10×36.50 mm` 四角 `R1.80` 圆角），沉金，过孔盖油，自带 `70.20×70.20 mm` 工艺边（同时提供单板 `Gerber_AFE-30P.zip` `f23c063a`；已剥离 32 颗 DNP 共模电容共 64 个钢网开孔），**双面贴**（22 种 / 82 颗：Top 48 + Bottom 34，含双 `1.0 mm` 30P `C324727`、`R4=C2984407`、`C10=1µF` `C52923` 与 16×`22pF` `C76924`，CPL 保持默认「AD 等其他」） | `hardware/16ch-u9-dual30/fab-afe-30p/Gerber_AFE-30P-panel702.zip`<br>`hardware/16ch-u9-dual30/fab-afe-30p/jlc_smt_bom.csv`<br>`hardware/16ch-u9-dual30/fab-afe-30p/jlc_smt_cpl.csv` | `e986cb1f`<br>`458954e0`<br>`05bb9036` |
| `14` | **新版双 30P 表带软板 `strap-30p-a`**（A 片） | 4 层压延铜 FPC（`0.203 mm`，`105.20×26.20 mm`），沉金 `2u"`，实心补强层 `0.10 mm`（尾端）+ `0.20 mm`（12 岛）；全基础库双面贴 **2 种 / 17 颗**（`C25741`×16 + `C25811`×1） | `hardware/16ch-u9-dual30/strap-fpc-30p/fab/strap-30p-a-gerber.zip`<br>`hardware/16ch-u9-dual30/strap-fpc-30p/fab/strap-30p-a-jlc-bom.csv`<br>`hardware/16ch-u9-dual30/strap-fpc-30p/fab/strap-30p-a-jlc-cpl.csv`<br>`hardware/16ch-u9-dual30/strap-fpc-30p/fab/strap-30p-a.d356` | `16e9cea8`<br>`8f02ec30`<br>`d61ce0af`<br>`e660b602` |
| `15` | **新版双 30P 表带软板 `strap-30p-b`**（B 片） | 4 层压延铜 FPC（`0.203 mm`，`150.51×26.20 mm`，与 A 片横向错位 `1.524 mm`），沉金 `2u"`，实心补强层 `0.10 mm`（尾端）+ `0.20 mm`（16 岛）；全基础库双面贴 **2 种 / 17 颗**（`C25741`×16 + `C25811`×1） | `hardware/16ch-u9-dual30/strap-fpc-30p/fab/strap-30p-b-gerber.zip`<br>`hardware/16ch-u9-dual30/strap-fpc-30p/fab/strap-30p-b-jlc-bom.csv`<br>`hardware/16ch-u9-dual30/strap-fpc-30p/fab/strap-30p-b-jlc-cpl.csv`<br>`hardware/16ch-u9-dual30/strap-fpc-30p/fab/strap-30p-b.d356` | `c0e61647`<br>`cffbbd76`<br>`a45ef4a2`<br>`ff42b45b` |
| `16` | **v0.01 广濑 `1.0 mm` `1 nF` 离体台架采集板** | 4 层 FR-4（台架 `1.6 mm` / 装壳 `0.8 mm`，`43.10×36.50 mm` 四角 `R1.80` 圆角，勾选代拼工艺边），沉金，**树脂塞孔+电镀盖帽（7 处盘中孔/切盘孔）**，`LM1` 顶面双窗钢网已裁好，**双面贴**（23 种 / 114 颗：Top 64 + Bottom 50，CPL 保持默认「AD 等其他」） | `hardware/16ch-afe-hirose-1mm-1nf/Gerber_AFE-30P.zip`<br>`hardware/16ch-afe-hirose-1mm-1nf/jlc_smt_bom.csv`<br>`hardware/16ch-afe-hirose-1mm-1nf/jlc_smt_cpl.csv` | `adab6ae0`<br>`c9b9a36a`<br>`2316380c` |
| `17` | **讯普 `2.0 mm` `1 nF` 离体台架采集板** | 4 层 FR-4（`43.10×36.67 mm` 直角，勾选代拼工艺边），沉金，**树脂塞孔+电镀盖帽**，**双面贴**（23 种 / 114 颗：Top 64 + Bottom 50，CPL 保持默认「AD 等其他」） | `hardware/16ch-afe-xunpu-2mm-1nf/Gerber_AFE-30P.zip`<br>`hardware/16ch-afe-xunpu-2mm-1nf/jlc_smt_bom.csv`<br>`hardware/16ch-afe-xunpu-2mm-1nf/jlc_smt_cpl.csv` | `f4628471`<br>`d7b21e5b`<br>`e5591b8d` |

### 下单填表与贴片预览核对要点

1. **主控板 `01 / 02`（`R4U6 / R4U6N`）**：单板 Gerber（`43.10 × 36.50 mm`），板厚 **`0.6 mm`** + **双面 SMT** + **树脂塞孔电镀盖帽**，下单页须勾选人工代拼工艺边（`≥ 70 × 70 mm`），并在贴片预览页对照同目录 `polarity-top.png` / `polarity-bottom.png` 逐颗确认极性器件方向。
2. **采集板 `03 / 04 / 06 / 07` 与 2 路板 `10`**：Gerber 均已自带 `70.20 × 70.20 mm` 一拼一工艺边与光学定位孔，下单选「自带拼板 / 1×1」即可，切勿重复加框；在贴片预览页确认 `ADS1298` / `ADS1292`、ESD 阵列与 FPC 连接器第一脚朝向。
3. **表带软板 `05 / 08 / 09 / 14 / 15`**：走嘉立创 **FPC 软板打样**，压缩包内已包含拆分厚度的实心补强层 `*-BOT_STIFF_0p10mm_PI.gbr`（金手指背面 `0.10 mm`）与 `*-BOT_STIFF_0p20mm_PI.gbr`（岛区及 `D2-8CH` 胶囊 6 窗垫片 `0.20 mm`），下单时将同目录 `stiffener-map*.png` 与 `工艺要求.md` 附于工程备注；若随单 SMT 仅贴装限流电阻（`Φ6×2.0` 圆铜片与 `3×3×2` 方铜片收货后二次焊接），工程备注须写明：**「请 CAM 仅在正面 `F_Paste.gtp` 钢网中删去 `Φ6.5 / Φ4.5` 大圆电极开孔并保留正面 0402 电阻焊盘；背面 `B_Paste.gbp` 的 0402/0603 电阻焊盘全部保留」**。
4. **新版 16 路旗舰双板 `12 / 13`（`MCU-U9` + `AFE-30P`）**：两套 `-panel702.zip` 均已自带 `70.20 × 70.20 mm` 一拼一工艺边（`2.0 mm` 铣槽 + 断口连接筋），下单选「自带拼板 / 1×1」；其中 `MCU-U9` 选 **6 层 `0.8 mm` 沉金 + 树脂塞孔电镀盖帽 + 双面 SMT**（`U7 STM32L432KCU6 C1337280` 视实时库存走邮寄或全球代购，`USB1` 沉板座勾选异形/沉板治具确认），`AFE-30P` 选 **4 层 `0.8 mm` `JLC04081H-3313` 沉金 + 过孔盖油 + 双面 SMT**。**上传 `jlc_smt_cpl.csv` 时必须保持平台默认的「AD,99SE,Allegro,PADS(宏)等其他」选项（切勿改选「嘉立创EDA」）**，并在 2D 预览页对照同目录 `orientation.csv` 与 `polarity-top.png` / `polarity-bottom.png` 逐颗确认顶/底层极性方向。

---

## C · 配套 3D 打印结构件与 1:1 装配裁胶纸样

| 适用版本 | 零件 / 纸样 | 规格与打印工艺 | 仓内精确路径（相对仓库根） | SHA-256 前 8 位 |
|---|---|---|---|---|
| **16ch 旗舰双 30P 专属** | 超薄圆润无外露螺丝手表壳 `enclosure-u9-watch`（另附台架壳 `case-30p`） | 3D 打印光敏树脂（`tray` / `cover` / `side_button`）+ `TPU 95A`（`cap_bottom`），主体净高 **`46.80×40.00×9.60 mm`**（全壳最小壁厚 `0.85 mm ≥ 0.80 mm`），内柱盲孔 **`4 × M1.4`** 锁紧 + 底盖遮蔽，23 对三维布尔 `0.000 mm³` 零干涉 | `hardware/16ch-u9-dual30/enclosure-u9-watch/tray.step`<br>`hardware/16ch-u9-dual30/enclosure-u9-watch/cover.step`<br>`hardware/16ch-u9-dual30/enclosure-u9-watch/side_button.step`<br>`hardware/16ch-u9-dual30/enclosure-u9-watch/cap_bottom.step`<br>`hardware/16ch-u9-dual30/enclosure-u9-watch/assembly.step` | `044dde45`<br>`f0401545`<br>`55221bcf`<br>`72f08525`<br>`c5d438d1` |
| **8ch + 16ch 共用** | 胶囊电极底盖切片包 `cap_d2` | Bambu X2D `TPU 95A HF` 一盘两件（4 圆孔 `Φ6.5` + 2 方孔 `3.5×3.5`） | `hardware/enclosure-46x40/c08b-shell-r12/capsule-cap-d2/cap_d2_x2-X2D-TPU95A.3mf` | `b49b121d` |
| **8ch + 16ch 共用** | 胶囊底壳外发 STEP `tray_d2` | 3D 打印树脂外发件（8ch 靠胶囊背 6 窗 `0.20 mm` PI 垫片零改模复用） | `hardware/enclosure-46x40/c08b-shell-r12/capsule-cap-d2/tray_d2.step` | `b76c2a66` |
| **8 通道专属** | 表带 TPU 电极层切片包 `layer_d2_8ch` | Bambu X2D `TPU 95A HF` `0.16mm`（北 `26.2×16.2` + 南 **`26.2×32.2`**，5 层、`10m 2s`、`0.86 g`） | `hardware/8ch-ads1298/strap-fpc-d2-8ch/tpu-layer-d2-8ch/layer_d2_8ch-X2D-TPU95A.3mf` | `6189e957` |
| **8 通道专属** | 1:1 装配与 9448A / PI 垫片裁切纸样 | A4 横版 `100%` 打印（含北/南 9448A 与胶囊 PI 垫片独立 1:1 裁切模板 + 横纵双轴校准尺） | `hardware/8ch-ads1298/strap-fpc-d2-8ch/tpu-layer-d2-8ch/paper_pattern_d2_8ch_1to1_A4.pdf` | `5f69d2c3` |
| **16 通道专属** | 表带 TPU 电极层切片包 `layer_d2` | Bambu X2D `TPU 95A HF` `0.16mm`（北 `26.2×16.2` + 南 `26.2×96.2`，`17.5m`、`2.30 g`） | `hardware/16ch-c08b-round/strap-fpc-d2/tpu-layer-d2/layer_d2-X2D-TPU95A.3mf` | `06d8448b` |
| **16 通道专属** | 1:1 表带对位纸样 | A4 横版 `100%` 打印（14 路表带 + 胶囊 6 点） | `hardware/16ch-c08b-round/strap-fpc-d2/tpu-layer-d2/paper_pattern_d2_1to1_A4.pdf` | `701e7d65` |

---

## D · 首板烧录、十步硬件自检与主机解码（`firmware/c08b-bringup/`）

1. **引脚、主机单测与解码器自检门禁**：
   ```bash
   python3 -B firmware/c08b-bringup/tools/pins_u9.py --selftest
   python3 firmware/c08b-bringup/tools/pins.py hardware/common-mainboard/mainboard-r4u6n/C08B-main-R4U6N.epcb2
   python3 -B firmware/c08b-bringup/tools/decode_bringup.py --self-test
   cc -std=c11 -O2 -Wall -Wextra -Werror -I firmware/c08b-bringup/common -I firmware/c08b-bringup/l432 -I firmware/c08b-bringup/nrf firmware/c08b-bringup/host_test/test_host.c -o /tmp/test_c08b_host && /tmp/test_c08b_host
   ```
2. **固件刷写路径**：
   - `nRF52840`（`MCU-U9` 上为 **`U8`**，`R4U6/R4U6N` 上为 `U13`）：经顶面 `J301`（`SWDIO / SWDCLK / GND`）使用 SWD 探针烧写 `nrf.hex`（`c4d046ab`）。
   - `STM32L432KC`（`MCU-U9` 上为 **`U7`**，`R4U6/R4U6N` 上为 `U18`）：
     - 在 **`MCU-U9`** 上：`U7.31`（`PH3-BOOT0`）连至独立 `L_BOOT0`（经 **`R5 = 10 kΩ`** `C25744` 下拉至 `GND`；注意 `R26` 是安全互锁网络 `U7_EN ↔ ILK_D` 的 `0 Ω` 电阻，切勿改动），推荐直接经顶面 `DEBUG` 焊盘组（`SWCLK / SWDIO / NRST / GND`）用 SWD 探针烧写 `l432.hex`，或上电时将 `DEBUG` 的 `BOOT0` 焊盘临时拉高至 `3.3 V` 进入系统 ROM USB DFU（`0483:DF11`）。
     - 在 **`R4U6 / R4U6N`** 上：已将 `PH3-BOOT0` 连至 `VBUS_SENSE`，插 USB 上电自动进入系统 ROM DFU（`0483:DF11`），执行 `dfu-util -a 0 -s 0x08000000:leave -D build/l432.bin` 免探针烧写（`l432.hex` `7fc800df`，`CFG1292_TEST` 已修正 `RESP2=0x07`）；拔掉 USB 改由 `J401` 电池供电即自动运行采集自检固件。
   - `2CH + P44e + XIAO nRF52840 Sense` 独立 BLE `F01` 流式候选固件：[`firmware/xiao-ads1292-2ch/`](../firmware/xiao-ads1292-2ch/README.md)（`bash check.sh --pio`：20/20 脚对账、6 项必败反例、48 项单测与 `ads1292_2k`/`ads1292_4k` 镜像全绿，默认硬件锁关闭）。
   - `C08B` 双核主控家族（`OpenEMG-C08B-Mainboard-Rev0.01 + AFE-30P` 以及 `R4U6 / R4U6N + D20/8CH/2CH`：`L432 + nRF52840`）`2/8/16ch` 自动识别实时 BLE `F01 v1/v4 + IMU` 流式候选固件与主机接入契约：[`firmware/c08b-stream/`](../firmware/c08b-stream/README.md) + [`host/c08b_stream.py`](../host/c08b_stream.py)（`bash firmware/c08b-stream/check.sh` & `python3 -B host/check_c08b_stream.py`：`l432.hex` `0e0f6eb9` / `nrf_s140.hex` `a569fdbf` / `nrf_nosd.hex` `ca23b0cc`，默认双硬件锁关闭）。
3. **手机广播与 97 字节报告一键判读（免调试器）**：
   - 手机 nRF Connect 复制 `0xFFFF` 厂商十六进制串：`python3 -B firmware/c08b-bringup/tools/decode_bringup.py --ble-hex "<HEX>"`
   - SWD / GDB 导出 97 字节 `g_report`：`python3 -B firmware/c08b-bringup/tools/decode_bringup.py --report-hex "<HEX>"`
   - 若解码器报 `CRITICAL_USB_INTERLOCK_BYPASSED`（`VBUS=1` 且 `OE_N=0`），立即断电排查互锁电路，严禁接触人体。

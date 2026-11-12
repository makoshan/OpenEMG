# OpenEMG 共用主控家族（2 / 8 / 16 通道）嘉立创制造包与联调总表

本文档提供全系 11 套嘉立创（JLCPCB）直接上传生产包（Gerber `.zip`、SMT `BOM.csv`、贴片坐标 `CPL.csv` 与飞针网表 `.d356`）的精确路径、工艺参数与 SHA-256 指纹核对表，并由 [`scripts/check_fab_packs.py`](../scripts/check_fab_packs.py) 在 CI 中逐字节锁定核验。

> [!CAUTION]
> **打样与安全必读**
> 1. **切勿在嘉立创 EDA 内点击「从原理图更新 PCB」后直接下单**：`.epro2` 工程仅供查看原理图、走线与三维预览；正式打板与贴片请直接上传下表锁定的 Gerber `.zip`、`BOM.csv` 与 `CPL.csv`。
> 2. **人体电安全红线（详见 [SAFETY.md](../SAFETY.md)）**：主控 `JP701` 默认空贴（DNP），2 路板 `R32`（`0 Ω`）默认必贴；**严禁插着市电充电器或直连电脑 USB 时将电极接触人体**。

---

## A · 上下板互换与固件免跳线自动识别矩阵

同一套上层主控板（圆孔版 `R4U6` 配螺丝壳 `R12`，四角缺口版 `R4U6N` 配无螺丝抱柱壳 `R13`）经同一根 **20P `0.5 mm` 反向软排线**（如聚硕 `JS05A-20P-020-3-4`，立创 `C22434842`，双面触点适配 `FH34SRJ`）直插三档下层采集板；`firmware/c08b-bringup` 上电通过 `afe_detect(id_a, id_b)` 自动识别通道档位：

| 档位组合 | 上层主控（二选一外形） | 下层采集板 | 表带 / 电极侧 | 固件自动识别（`afe_mode_t`） | 自检掩码 |
|---|---|---|---|---|---|
| **16 通道全腕** | `R4U6`（圆孔）或 `R4U6N`（缺口） | `D20`（圆孔）或 `D20N`（缺口），正反双 `ADS1298` | 双片 4 层软板 `D2`（`strap-a` + `strap-b`，32+2 触点） | `id_a=0x92, id_b=0x92` → `AFE_16CH (16)` | `0x03FF` |
| **8 通道单面** | `R4U6`（圆孔）或 `R4U6N`（缺口） | `D20-8CH`（圆孔）或 `D20N-8CH`（缺口），纯顶面单颗 `ADS1298` | 单片 4 层软板 `D2-8CH`（`strap-d2-8ch`，16+2 触点，胶囊背带 6 窗 `0.20 mm` PI 垫片） | `id_a=0x92, id_b∈{0x00,0xFF}` → `AFE_8CH (8)` | `0x03F5` |
| **2 通道一体** | `R4U6` / `R4U6N`；或入门转接板 `P44e` + XIAO | `ADS1292-2ch`（顶面贴件、底面 6 焊盘手焊铜片） | 底面自带两排「大—辅—大」6 触点（免外部表带软板） | `(id_a&0xDF)==0x53, id_b∈{0x00,0xFF}` → `AFE_2CH (2)` | `0x03F5` |

> 若 `id_b` 读出非空非 `0x92` 杂值，或 `U1` 无响应仅 `U2` 在线，`afe_detect()` 返回 `AFE_NONE (0)` 报错拦截，不会将故障 16 路板误降级为单芯片模式。

---

## B · 嘉立创直接上传制造包清单（全家族 11 套，按 SHA-256 前 8 位核对）

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

### 下单填表与贴片预览核对要点

1. **主控板 `01 / 02`（`R4U6 / R4U6N`）**：单板 Gerber（`43.10 × 36.50 mm`），板厚 **`0.6 mm`** + **双面 SMT** + **树脂塞孔电镀盖帽**，下单页须勾选人工代拼工艺边（`≥ 70 × 70 mm`），并在贴片预览页对照同目录 `polarity-top.png` / `polarity-bottom.png` 逐颗确认极性器件方向。
2. **采集板 `03 / 04 / 06 / 07` 与 2 路板 `10`**：Gerber 均已自带 `70.20 × 70.20 mm` 一拼一工艺边与光学定位孔，下单选「自带拼板 / 1×1」即可，切勿重复加框；在贴片预览页确认 `ADS1298` / `ADS1292`、ESD 阵列与 FPC 连接器第一脚朝向。
3. **表带软板 `05 / 08 / 09`**：走嘉立创 **FPC 软板打样**，压缩包内已包含拆分厚度的实心补强层 `*-BOT_STIFF_0p10mm_PI.gbr`（金手指背面 `0.10 mm`）与 `*-BOT_STIFF_0p20mm_PI.gbr`（岛区及 `D2-8CH` 胶囊 6 窗垫片 `0.20 mm`），下单时将同目录 `stiffener-map*.png` 与 `工艺要求.md` 附于工程备注；若随单 SMT 仅贴装限流电阻（`Φ6×2.0` 圆铜片与 `3×3×2` 方铜片收货后二次焊接），工程备注须写明：**「请 CAM 在 SMT 钢网中删去 `F_Paste.gtp` 上的 `Φ6.5 / Φ4.5` 大圆电极开孔，仅保留 0402/0603 电阻焊盘」**。

---

## C · 首板烧录与十步硬件自检（`firmware/c08b-bringup/`）

1. **引脚与主机单测门禁**：
   ```bash
   python3 firmware/c08b-bringup/tools/pins.py hardware/common-mainboard/mainboard-r4u6n/C08B-main-R4U6N.epcb2
   cc -std=c11 -O2 -Wall -Wextra -Werror -I firmware/c08b-bringup/common -I firmware/c08b-bringup/l432 -I firmware/c08b-bringup/nrf firmware/c08b-bringup/host_test/test_host.c -o /tmp/test_c08b_host && /tmp/test_c08b_host
   ```
2. **固件刷写路径**：
   - `nRF52840`（`U13`）：经 `J301`（`SWDIO / SWDCLK / GND`）使用 SWD 探针烧写 `nrf.hex`。
   - `STM32L432KC`（`U18`）：`R4U6 / R4U6N` 已将 `PH3-BOOT0` 连至 `VBUS_SENSE`，插 USB 上电自动进入系统 ROM DFU（`0483:DF11`），执行 `dfu-util -a 0 -s 0x08000000:leave -D build/l432.bin` 免探针烧写；拔掉 USB 改由 `J401` 电池供电即自动运行采集自检固件。

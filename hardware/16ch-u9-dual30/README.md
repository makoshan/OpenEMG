# 16 通道小型化旗舰：U9 圆角 6 层主控（`Rev0.01`）+ 超薄双 30 针采集板 + 四层保护软板 + 超薄圆润手表壳（2026-11-14 开源定版）

本目录收录 `OpenEMG-C08B-Mainboard-Rev0.01`（6 层 `0.80 mm` 圆角双核主控，原矩形 `26.64 × 20.90 mm` 电池窗、去中央 DEBUG 框洁净丝印版）与 `AFE-30P`（4 层 `0.80 mm` 圆角超薄双 30 针 16 路采集板）配对工程、嘉立创直接上传制造包（单板与 `70.20 × 70.20 mm` 工艺边 Gerber、SMT BOM、192 颗逐脚拟合校核 CPL、极性图）、满载器件整板 STEP、双 30P 四层保护表带软板（`strap-fpc-30p/`）以及 `9.60 mm` 超薄圆润无外露螺丝手表壳（`enclosure-u9-watch/`，同时保留台架候选壳 `case-30p/`），按 [CERN-OHL-S-2.0](../../LICENSE-HARDWARE) 发布。

## 文件清单

| 路径 | 说明 |
|---|---|
| `OpenEMG-C08B-Mainboard-Rev0.01.epro2` / `mcu-u9-3d.step` | 6 层 `0.80 mm` 主控板（`STM32L432KCU6` `U7` + `nRF52840-QFAA` `U8`，`43.10 × 36.50 mm` 四角 `R=1.80 mm` + `26.64 × 20.90 mm` 原矩形电池开窗 + 去中央 DEBUG 框洁净丝印）及满载 588 实体 STEP |
| `AFE-30P.epro` / `AFE-30P.epro2` / `afe-30p-3d.step` | 4 层 `0.80 mm` 16 路圆角采集板（双 `ADS1298IPAGR` `U1/U2` + 双 `1.00 mm` 超薄上下双面触点 30P 座 `FPC1/FPC3` `C324727` + 20P 双面触点座 `FPC2` `Molex 503480-2000`）及满载 306 实体 STEP（已剔除 32 颗 DNP 共模电容占位块） |
| `20针接口.csv` | `MCU-U9 FPC1`（1..20）↔ `AFE-30P FPC2`（20..1）逐脚网络锁定表 |
| `fab-mcu-u9/OpenEMG-C08B-Mainboard-Rev0.01-Gerber.zip` | 主控 `Rev0.01` 6 层单板 Gerber（`GTL, G1..G4, GBL` + `GKO` + `PTH/NPTH`，已剔除 14 处手焊/DNP 钢网开窗，无中央 DEBUG 线框） |
| `fab-mcu-u9/OpenEMG-C08B-Mainboard-Rev0.01-panel702-Gerber.zip` | 主控 `Rev0.01` 自带 `70.20 × 70.20 mm` 工艺边（`2.0 mm` 铣槽 + 四边断口连接筋）一拼一 Gerber |
| `fab-mcu-u9/jlc_smt_bom.csv` / `jlc_smt_cpl.csv` | 主控 `Rev0.01` 嘉立创 SMT 物料清单与贴片坐标（45 种 / 110 颗：Top 42 + Bottom 68，按平台默认「AD 等其他」逐脚拟合） |
| `fab-mcu-u9/orientation.csv` / `polarity-*.png` | 主控 `Rev0.01` 有极性/多引脚器件 1 脚与阴极坐标核对表及顶/底层粉点核对图 |
| `fab-afe-30p/Gerber_AFE-30P.zip` | `AFE-30P` 4 层 `0.80 mm` `R=1.80 mm` 圆角单板 Gerber（`GTL, G1, G2, GBL` + `GKO` + `PTH`；`GTP/GBP` 已剥离全部 32 颗 DNP 共模电容共 64 个钢网开孔） |
| `fab-afe-30p/Gerber_AFE-30P-panel702.zip` | `AFE-30P` 自带 `70.20 × 70.20 mm` 工艺边（同心 `R1.80/R3.80` 圆角 `2.0 mm` 铣槽 + 6 处断口连接筋，完全避开南侧双 30P 与东侧 20P 插口）一拼一 Gerber |
| `fab-afe-30p/jlc_smt_bom.csv` / `jlc_smt_cpl.csv` | `AFE-30P` 嘉立创 SMT 物料清单与贴片坐标（22 种 / 82 颗：Top 48 + Bottom 34，100% 现货 `C` 料号，含 `C324727`、`R4=C2984407`、`C10=C52923` 1µF 与 16×`22pF` `C76924`，按平台默认「AD 等其他」逐脚拟合） |
| `fab-afe-30p/orientation.csv` / `polarity-*.png` | `AFE-30P` 有极性/多引脚器件 1 脚与阴极坐标核对表及顶/底层粉点核对图 |
| `strap-fpc-30p/` | 适配 `FPC1/FPC3` 横向错位 `1.524 mm` 的 **12+2+2 双极四层柔性表带软板**（`strap-30p-a` + `strap-30p-b`）：自带 `32 × 100 kΩ`（`C25741`）采样限流串阻与 `2 × 200 kΩ`（`C25811`）偏置串阻（叠加板上 `15 kΩ` / `392 kΩ` 后总串联阻抗 `115 kΩ` / `592 kΩ`），含 28 项门禁 `check.py`、满载 3D STEP 与 `fab/` 生产包 |
| `enclosure-u9-watch/` | **穿戴主力超薄圆润无外露螺丝手表壳**（主体净高 **`46.80 × 40.00 × 9.60 mm`**，`≤ 9.70 mm`；含外扣底盖不计铜凸 `10.806 mm`，含 `1.20 mm` 电极尖端总包络 `12.006 mm`；全壳最小壁厚 **`0.85 mm ≥ 0.80 mm`**）：内柱盲孔 `4 × M1.4` 紧固 + `cap_bottom` 卡扣遮蔽，经 `fit_3d_check.py` 核验满载双板/电芯/双软板共 **23 对三维布尔交叠 `0.000 mm³`** 及 9 项正反例对照 |
| `case-30p/` | 离体台架候选盒总装 STEP（`Case.step`、`Lid.step`、`assembly.step`）、`19.67 × 26.59 × 2.78 mm` 电芯干涉报告 `checks.json` 与装配图 |
| `verify_interface.py` / `SHA256SUMS` | 20P 逐脚对账、双核 39 信号脚固件兼容、60 脚双 30P 映射、双板 `0.80 mm` 叠层、前端 RC/电荷泵修正与 0/64 DNP 钢网零残留、192 颗 CPL 逐脚拟合（含 4 项必败反例）、铺铜与全套 3D 总装自检脚本及 SHA-256 校验表 |

## 已修复的工程与制造问题（嘉立创 EDA 专业版 `4.1.93` 原生复核通过）

### 1. 主控板 `OpenEMG-C08B-Mainboard-Rev0.01`（6 层 `0.80 mm`，`43.10 × 36.50 mm`）
- **定版原矩形电池镂空窗、东梁强度恢复与 `0.80 mm` 真实叠层同步**：电池开窗 `a6b31685508e342e` 采用无阶梯纯矩形 **`26.638 × 20.900 mm`**（东侧梁宽恢复至 **`2.762 mm`**，完美容纳标准 `302025` 锂电池且与 `SCREW3` 孔留足边距），同步对齐 `Inner3/Inner4` 内电层镂空框并重铺全部 10 块铜皮（`10 POUR / 24 POURED`）；`LAYER_PHYS` 同步为真实 6 层 `0.80 mm`（`JLC06081H-3313`，`31.321 mil = 0.7956 mm`），导出 588 实体 `mcu-u9-3d.step` 使整表壳体净高降至 **`9.60 mm`**。
- **四角 `R=1.80 mm` 圆角板框、北边拉平与洁净丝印**：消除原版北边 `0.166 mm` 倾斜，统一四角圆弧与内电层退缩外框；板面升级 `OpenEMG 0.01` 标识、去掉顶面中央 `DEBUG` 线框并双列对齐背面位号丝印。
- **消除全部网络飞线与孤立铜皮**：将 `BUTTON_N` 走线 `aa2a5e4ee3874f57` 延伸至 `SW300.1` 焊盘中心 `324.087 mil`，移除 2 处孤立泪滴，西南角地过孔 `cc7fc0d843f8c411` 内移至 `-1303 mil`；原生 DRC **0 间距/几何/连接错误、0 飞线**。
- **原理图与 PCB 充电芯片同步**：`U17` 统一为 `LTC4054ES5-4.2#TRPBF`（`SOT-23-5`，立创 `C462648`）。
- **钢网防连锡处理**：单板与 `70.2 × 70.2 mm` 工艺边 Gerber 已自动剔除 `J301`、`JP701`、`D62`、`BT1`、`ANT1` 等 14 处手焊/空贴焊盘钢网开孔。

### 2. 采集板 `AFE-30P`（4 层 `0.80 mm`，`43.100 × 36.500 mm` 四角 `R=1.80 mm`）
- **小型化机械与超薄双触点连接器升级**：板框收为与主控同心的 **`43.100 × 36.500 mm` 四角 `R=1.800 mm` 圆角板框**，四层叠层设为 **`0.80 mm`（`JLC04081H-3313`）**；正反双面 30P 表带座 `FPC1 / FPC3` 由 `2.00 mm` 高下接座升级为 **`1.00 mm` 超薄上下双面触点广濑 `FH34SRJ-30S-0.5SH(50)`（立创 `C324727`）**（无需区分上下接金手指面）。
- **前端高阻干电极 RC 滤波修正（消除工频共模转差模与肌电通带衰减）**：配合四层软板 `strap-fpc-30p` 的 `100 kΩ` 贴肤限流电阻（每脚总串联电阻 `R_leg = 115 kΩ`），将 32 颗对地共模电容（`C55, C57..C71, C93..C108`）全部设为 **空贴 DNP** 并在单板/拼板 Gerber `GTP/GBP` 钢网中 100% 剥离其 64 个焊盘开孔（避免 `±5%` 容差把 50 Hz 共模干扰直接转成差模底噪，并将原 `115 kΩ × 564 pF → f_c = 2.45 kHz` 误削肌电高频的问题彻底修正），同时将 16 颗跨通道差分电容（`C72..C79, C109..C116`）由 `47 pF` 调整为 **`22 pF C0G`（`GRM0335C1H220JA01D`，立创 `C76924`）**，精确锁定纯差模抗混叠截止频率 $f_{c,\text{diff}} = \frac{1}{2\pi \cdot 230\,\text{k}\Omega \cdot 22\,\text{pF}} = 31.45\,\text{kHz}$。
- **`LM27762` 负压电荷泵飞跨电容修正**：依 TI `LM27762` 手册 §8.2.1.2.3 要求，将飞跨电容 `C10` 由 `10 µF` 修正为 **`1 µF X5R 0402`（`CL05A105KA5NQNC`，立创 `C52923`）**，消除启动浪涌电流与电荷泵开关纹波超标隐患。
- **20P 反序排线 `FPC2.17 / 18` 交叉修复**：`FPC2` 第 17 脚改接 `CS#2`（`U2.39`，对主控 `FPC1.4，AFE_CS_B`），第 18 脚改接 `DRDY2#`（`U2.47`，对主控 `FPC1.3，AFE_DRDY_B`），过孔 `e1998` 移至 `(1305, 792.3834) mil`。
- **双 `ADS1298` 第 31 脚 `RESV1` 修正为数字地 `GND`**：依 TI `ADS1298` 数据手册（`RESV1` 必须接 `DGND`），将原理图（`1.esch` `e95/e300`）与 PCB（`U1.31`、`U2.31` 及相连过孔/短线）从 `AGND` 改为 `GND`，消除原理图与 PCB 网表差异（`0 Netlist Error`）。
- **`Inner2` 北数字 `GND` / 南模拟 `AGND` 分岛与晶振完整参考地**：将 `Inner2`（`layer 16`）拆分为北侧数字区 `POUR e1678 (GND)` 与南侧模拟电极区 `POUR e1687 (AGND)`（避免数字返回电流耦合进高阻电极扇出区），移除 `2.048 MHz` 晶振 `X1` 正下方的禁止铺铜框 `REGION e1680` 为时钟提供完整 `GND` 参考平面，保留 `RULE 7` 直连（`connType=1`），并在 `LCEDA-Pro 4.1.93` 重建全部 15 块铺铜；原生 DRC **0 错误、0 飞线、0 网表不一致**。
- **补齐全部 SMT 立创现货料号**：补齐 `C1, C2`（`22uF` `0402` `C105226`）、`C4, C34`（`10uF` `0402` `C7472949`）并将负轨反馈电阻 `R4` 更新为现货 `105 kΩ ±0.1%`（`C2984407`），整板 22 种 / 82 颗贴片件 100% 具备有效现货 `C` 料号。

### 3. 嘉立创 SMT 贴片坐标（`jlc_smt_cpl.csv`）极性与背面镜像修正
- 嘉立创 SMT 下单页默认选中 **「AD,99SE,Allegro,PADS(宏)等其他」**（背面按封装先 `X` 取反再旋转 `Rotation` 角），而嘉立创 EDA 内部 `COMPONENT` 背面按 `Y` 取反旋转，二者在背面相差 **`180°`**。
- `fab-mcu-u9/jlc_smt_cpl.csv`（110 颗）与 `fab-afe-30p/jlc_smt_cpl.csv`（82 颗）共 **192 颗**贴片件已统一修正为嘉立创默认上传模式（顶层保持原角，底层加 `180°`），经 `verify_interface.py` 逐脚拟合校验（最大焊盘偏差 **`0.0000 mm`**；`U17`、`FPC1`、`U2`、`FPC3` 减回 `180°` 反例均报 `> 1.5 mm` 错位拦截）。
- **下单必读**：上传 `jlc_smt_cpl.csv` 时**保持平台默认的「AD,99SE,Allegro,PADS(宏)等其他」选项，切勿改选「嘉立创EDA」**；在 2D 预览页同时勾选顶层与底层，对照 `orientation.csv` 及 `polarity-top.png` / `polarity-bottom.png` 核对粉点。

## 20 芯反序排线与三维 U 形装配关系（含防混插短路告警）

- 电气映射：主控 `FPC1` 的第 $k$ 脚接采集板 `FPC2` 的第 $21-k$ 脚。主控 `19、20` 脚为受控 `3V3_AFE`，接采集板 `2、1` 脚（`+3.3V`）；主控第 `1` 脚为 `GND`，接采集板第 `20` 脚（`GND`）。完整逐脚映射见 [20 针接口表](20针接口.csv)。
- 三维叠板走线：主控 `Rev0.01` 底面 `FPC1`（开口朝东，第 `1` 脚在北、第 `20` 脚在南）与下层 `AFE-30P` 顶面 `FPC2`（开口朝东，第 `20` 脚在北、第 `1` 脚在南）均为 `Molex 503480-2000` 上下双面触点座且南北物理对齐；使用 **20 芯 `0.5 mm` A 型（同面）软排线**向外平折 U 形直插即可自然实现 `k ↔ 21−k` 连接。
- **严禁跨系列混插警告**：`OpenEMG-C08B-Mainboard-Rev0.01`（东侧 `FPC1.1=GND, 19/20=3V3_AFE`）**仅限与 `AFE-30P` 互连**；切勿与 `R4U6 / D20 / D20-8CH / ADS1292-2ch` 系列（南侧 `J_AFE.1/2=3V3_AFE, 20=GND`）混插 20P 排线，亦严禁台架 `1 ↔ 1` 直连，否则上电瞬间 `3V3_AFE` 直接对 `GND` 短路。

## 固件二进制兼容与烧录路径

主控 `Rev0.01` 的双核信号脚（`U7 STM32L432KCU6` 23+3 脚 + `U8 nRF52840-QFAA` 16 脚，由 `verify_interface.py`、`c08b-bringup/tools/pins_u9.py` 与 `c08b-stream/tools/pins.py --check-u9` 三重自动断言）可直接运行免改动的 [`firmware/c08b-bringup`](../../firmware/c08b-bringup/README.md) 与 [`firmware/c08b-stream`](../../firmware/c08b-stream/README.md) 固件镜像：其中运行信号脚分配与 `R4U6 / R4U6N` 完全一致，仅 `U7.31`（`PH3-BOOT0`）接 `L_BOOT0`（经 `R5` `10 kΩ` 下拉至 `GND`，固件配置为无上下拉高阻输入，`L432` 侧 `l432_vbus_present()` 恒读 `0`；USB 电气安全互锁由硬件 `VBUS → R703/R704 → Q3 → U4 → OE_N` 切断隔离器以及 `nRF52840` 侧 `U8.3 P0.01=VBUS_SENSE` / `U8.15 P0.17=OE_N` 完整执行，自检与采集流均正常通过）：
1. **`nRF52840`（`U8`）**：通过顶面 `J301` 焊盘（`SWDIO / SWDCLK / GND / 3V3`）经 SWD 探针烧写 `nrf.hex` / `nrf_s140.hex`。
2. **`STM32L432KC`（`U7`）**：顶面已引出独立 `DEBUG` 焊盘组（`SWCLK / SWDIO / NRST / BOOT0 / GND`），推荐直接用 SWD 探针烧写 `l432.hex`；若需走系统 ROM USB DFU（`0483:DF11`），须在上电时将顶面 `DEBUG` 的 `BOOT0` 焊盘临时拉高至 `3V3`（板上 `R213` 另一端 `L_BOOT0_CTL` 为预留孤立焊盘、未连 `VBUS`，单贴 `R213` 不会自动进 DFU）。

## 采集板首板复核

当前锁定单板包为 [Gerber_AFE-30P.zip](fab-afe-30p/Gerber_AFE-30P.zip)，SHA-256 为 `f23c063a88cb0b465a9af0a627ced205fdfe856572672e554036a0ad747971a6`；同源 `70.20 × 70.20 mm` 工艺边包为 [Gerber_AFE-30P-panel702.zip](fab-afe-30p/Gerber_AFE-30P-panel702.zip)，SHA-256 为 `e986cb1f1304497b80513d90a5f71a3ef3495bb22d788826deda2481f3165c8c`。

| 核查项 | 制造包实查结果 |
|---|---|
| `FPC1.31/32` 与 `FPC3.31/32` 固定耳 | 同属连通的 `AGND` 平面（原生 DRC 0 未连） |
| `−2.5 V` 走线与 `C10.1`（`1 µF` 飞跨电容） | `C10.1` 通 `LM1.10`，`C10.2` 通 `LM1.9`，与 `−2.5 V` 三网彼此独立零粘连 |
| 32 颗 DNP 共模电容钢网开孔 | `Gerber_TopPasteMaskLayer.GTP` / `Gerber_BottomPasteMaskLayer.GBP` 实测 `0/64` 命中；16 颗 `22 pF` 差分电容 `32/32` 命中 |

这份采集板生产包已通过嘉立创 EDA `4.1.93` 原生 DRC（0 错误 / 0 飞线，含 1 项正对照拦截）与 `verify_interface.py --selftest`（4/4 反例拦截），可用于首板打样；实际开短路以板厂飞针电测为准，首板回板后须先在离体台架复核 `±2.5 V` 轨纹波、双片独立片选与短接输入底噪。

## 负电源反馈电阻 R4

R4 使用 Viking ARG02BTC1053（C2984407，105 kΩ，0402，±0.1%，±25 ppm/℃）。按板上网络，R4 跨 LM1 的 OUT− 与 FB−（6、7 脚），R5 为 FB− 到 AGND 的 100 kΩ。按 TI 式 (3)，输出设定为 −1.22 × (1 + 105/100) = −2.5010 V；原 104 kΩ 设定为 −2.4888 V。按反馈基准限值和两颗电阻初始容差独立取极值，负轨为 −2.541 至 −2.462 V。正轨 R6/R3 = 107/100 kΩ，典型 +2.4840 V，按相同方法合算两轨差为 4.906 至 5.064 V，处于 ADS1298 推荐的 2.7 至 5.25 V 内。上述为稳压状态的设定值估算；带载启动、纹波及实际输出待首板测量。[LM27762 手册 §5.5、§7.2.2](https://www.ti.com/lit/ds/symlink/lm27762.pdf) · [ADS1298 手册 §7.3](https://www.ti.com/lit/ds/symlink/ads1298.pdf)

## 复核命令

```bash
python3 -B hardware/16ch-u9-dual30/verify_interface.py --selftest
python3 -B hardware/16ch-u9-dual30/verify_interface.py
python3 -B firmware/c08b-bringup/tools/pins_u9.py --selftest
bash firmware/c08b-stream/check.sh
(cd hardware/16ch-u9-dual30 && shasum -a 256 -c SHA256SUMS)
```

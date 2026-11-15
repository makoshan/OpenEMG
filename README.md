# OpenEMG

**简体中文** · [English](README.en.md)

OpenEMG 是一个 **16 通道开源肌电手环**项目。我们想用腕部的表面肌电信号识别手势。桌面软件可以查看各通道波形、录制动作和训练模型。

我们想做肌电界的 DeepSeek。电路、结构、固件和桌面软件全部开源，谁都可以照着做一块板，用自己的数据训练模型。

[当前状态与进展计划](#当前状态与进展计划) · [Gallery](#gallery) · [工作原理与调研](#工作原理) · [桌面工作台](#桌面工作台)

![16 通道 OpenEMG 手环的 U9 外壳设计渲染](hardware/16ch-afe-hirose-1mm-1nf/views/v001-enclosure-iso-dark.png)

**OpenEMG 还在早期研制阶段。** 2026 年 11 月 15 日定下的是打样用的 PCB。固件、桌面软件与板子的联调、手势识别都还在开发，16 通道整机尚未上机验证。

6 层主控板通过 20 针排线连接 4 层采集板。采集板用两颗 ADS1298，设计为 16 路差分输入。[打开双板工程与制造文件](hardware/16ch-afe-hirose-1mm-1nf/)

## Gallery

### PCB · 主控与采集板

**v0.01 的 PCB 设计已完成，下一步是打板、贴片和上电测试。** 采集板新增 32 颗输入保护管（D101–D132），贴片 BOM 和坐标表共 146 个位号。

![OpenEMG 16 通道双板 PCB 正反面：上排为主控板，下排为采集板，左列为正面，右列为背面](hardware/16ch-afe-hirose-1mm-1nf/views/v001-pcb-four-views.png)

图由同版 Gerber 生成。右列按翻到板背后的方向显示。[双板工程与制造文件](hardware/16ch-afe-hirose-1mm-1nf/) · [主控板元件正视图](hardware/renders/v001-mcu-front.png) · [采集板元件正视图](hardware/renders/v001-afe-front.png)

### 结构与装配

| v0.01 双板叠放 · 主控在上、采集在下 | U9 壳体与 v0.01 双板 · 分层视图 |
|---|---|
| ![透过主控板电池开窗可见下方的采集板](hardware/16ch-afe-hirose-1mm-1nf/views/v001-stack-iso-dark.png) | ![从上到下为上盖、主控板、采集板与底壳](hardware/16ch-afe-hirose-1mm-1nf/views/v001-exploded-iso-dark.png) |

装配图按 v0.01 制造文件绘制，采用 0.8 mm 裸板。右图拉开了层间距，省略了元件、排线和电池。实物还没试装。[U9 外壳模型](hardware/16ch-u9-dual30/enclosure-u9-watch/) · [历代结构与表带图集](hardware/renders/)

### 走线与原理图

| C08B-U9 主控板 · 6 层铜箔 | 16 通道采集板 · 4 层铜箔 |
|---|---|
| ![主控板从顶到底的六个铜层](hardware/16ch-afe-hirose-1mm-1nf/views/mcu-copper.png) | ![采集板从顶到底的四个铜层](hardware/16ch-afe-hirose-1mm-1nf/views/afe-copper.png) |

从左到右、从上到下依次是顶层、内层和底层。各层都从板顶看，方便对照走线和过孔。[主控 Gerber 与钻孔](hardware/16ch-afe-hirose-1mm-1nf/Gerber_C08B-U9_v0.01.zip) · [采集板 Gerber 与钻孔](hardware/16ch-afe-hirose-1mm-1nf/Gerber_AFE-30P.zip)

[![第 7 页原理图，电极输入、滤波和静电保护，点击查看七页 PDF](hardware/16ch-afe-hirose-1mm-1nf/views/schematic-afe-preview.png)](hardware/16ch-afe-hirose-1mm-1nf/views/schematic.pdf)

**[下载七页矢量原理图](hardware/16ch-afe-hirose-1mm-1nf/views/schematic.pdf)**。第 1–5 页是主控板的供电、蓝牙、USB、板间接口与采样主控，第 6–7 页是采集板的模拟电源、采集芯片、电极接口与输入滤波。PDF 可放大和搜索位号；修改电路请打开[嘉立创 EDA 专业版双板源工程](hardware/16ch-afe-hirose-1mm-1nf/OpenEMG_v0.01_DualBoard.epro2)。

| 复刻资料 | 主控板 | 采集板 |
|---|---|---|
| 物料清单（BOM） | [主控 BOM](hardware/16ch-u9-dual30/fab-mcu-u9/jlc_smt_bom.csv) | [采集 BOM](hardware/16ch-afe-hirose-1mm-1nf/jlc_smt_bom.csv) |
| 贴片坐标（CPL） | [主控坐标](hardware/16ch-u9-dual30/fab-mcu-u9/jlc_smt_cpl.csv) | [采集坐标](hardware/16ch-afe-hirose-1mm-1nf/jlc_smt_cpl.csv) |

板厚、盘中孔工艺、钢网和底面贴装方向见[同版制造说明](hardware/16ch-afe-hirose-1mm-1nf/)。本版采集板用于离体台架，通电前请阅读[测试与佩戴边界](SAFETY.md)。

## 工作原理

捏指时，肌肉活动会让皮肤表面产生微小的电压变化。手环的每个通道测一对电极之间的电压差。电极位置不同，同一次捏指在各通道上录到的波形也不同。桌面软件把波形和动作标签一起保存，供模型学习区分放松、捏指等动作。

摘下再戴，电极位置和松紧都会变。我们读过的一项四通道实验，在握拳、张手、屈腕和伸腕测试中判对了 152/160 次。论文没说明测试前是否重新佩戴。OpenEMG 计划把训练和测试分在两次佩戴中，单独记录重戴后的识别结果。[阅读项目调研节选与论文出处](research/wrist-semg.md)

## 当前状态与进展计划

**2026-11-15**　16 通道 v0.01 的双板工程和制造文件已公开。下一步打板、贴片。样板到手后，先测供电和两板通信，再在离体台架上逐路检查 16 个输入。

| 步骤 | 怎么测 | 看什么结果 |
|---|---|---|
| 1 · 16 通道双板采集 | 核对主控与采集板的排线方向，在台架上检查供电、通信，再逐路接入已知信号 | 记录每一路对应的输入、波形、短接底噪和连续采集时的丢帧数 |
| 2 · 工作台接入 | 将台架实录回放到桌面端，逐项核对 2、8、16 通道配置 | 各配置的通道数、编号和录制文件与输入一致，重新打开仍能回放 |
| 3 · 重戴后识别 | 完成佩戴安全检查后，用一次佩戴录制训练样本，再用另一次佩戴单独测试 | 分别报告放松、唤起和四个方向滑动的识别结果，以及放松时的误触发次数 |

### 桌面工作台

![OpenEMG 演示工程的 16 路肌电波形和各通道幅值](app/screenshots/studio-16ch-demo.png)

左侧逐行显示 CH1–CH16 的波形，右侧圆环显示各通道的均方根幅值（RMS，单位 µV）。图中数据来自演示工程。

桌面工作台用于查看波形、录制动作和训练手势模型。[打开软件目录](app/)

### 各版本工程与实测记录

目前优先验证 16 通道双板。8 通道和 2 通道的设计与测试进度列在下表。

| 通道 | 硬件工程 | 固件 | 3D 外观 | 实板测试进展 |
|---|---|---|---|---|
| **16 通道** | [广濑双 30 针](hardware/16ch-u9-dual30/) · [v0.01 双板与广濑 1 nF](hardware/16ch-afe-hirose-1mm-1nf/) · [讯普双 30 针](hardware/16ch-afe-xunpu-2mm-1nf/) · [双 34 针](hardware/16ch-c08b-round/) | [主控自检](firmware/c08b-bringup/) · [双 ADS1298 采集](firmware/c08b-stream/) | [U9 广濑版手表壳](hardware/16ch-u9-dual30/enclosure-u9-watch/) | 广濑版已核对 CAD 装配。v0.01 下一步打板，验证 16 路采集。另一个讯普版的偏置电路仍待定值。[三处改值与接线](hardware/16ch-afe-xunpu-2mm-1nf/#待工程师确认) |
| **8 通道** | [D20-8CH 腕带板](hardware/8ch-ads1298/afe-d20-8ch/) · [R01 台架板](hardware/8ch-ads1298/r01-bench/) | [腕带采集](firmware/c08b-stream/) · [R01 蓝牙采集](hardware/8ch-ads1298/r01-bench/firmware-f05-ble-dout/) | [R12 外壳](hardware/enclosure-46x40/c08b-shell-r12/) · [D2-8CH 电极软板](hardware/8ch-ads1298/strap-fpc-d2-8ch/) | R01 实板短接输入采集 10 分钟，1,187,774 帧序号连续。D20-8CH 腕带待装机实测。 |
| **2 通道** | [ADS1292 六触点板](hardware/2ch-ads1292/) | [XIAO 蓝牙采集](firmware/xiao-ads1292-2ch/) | [R7 六触点外壳](hardware/enclosure-46x40/ads1292-shell-r7/) | 已完成设计检查，待打样、上电。 |

## 开始使用

[桌面工作台](app/) · [软件与开发环境](firmware/software.md) · [硬件与制造文件索引](hardware/README.md) · [通电与佩戴安全须知](SAFETY.md)

[软件许可 MIT](LICENSE) · [硬件许可 CERN-OHL-S-2.0](LICENSE-HARDWARE) · [第三方声明](THIRD_PARTY_NOTICES.md)

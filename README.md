# OpenEMG

OpenEMG 是一个硬件和软件完全开源的表面肌电（sEMG）项目。我们从一只手环开始，研究一个具体的问题：手指轻轻一捏，能不能只凭手腕上的肌电信号把这个动作认出来？

**我们的愿景是做肌电界的 DeepSeek。** 希望学生、研究者和独立开发者都能从一套公开的设计开始做肌电实验。你可以照着原理图做一块采集板，打开固件看每个采样点怎么传到电脑，再用桌面工作台给自己的动作打标签，训练自己的手势分类器。下一位开发者可以换一种电极布局、试一种识别算法，和原方案比较，把改进留给后来的人。

[当前状态与进展计划](#当前状态与进展计划) · [Gallery](#gallery) · [工作原理与调研](#工作原理) · [桌面工作台](#桌面工作台)

![手环与六触点一体盒的正反面设计渲染](hardware/renders/openemg-finished-iso-dark.png)

**最新板稿 · OpenEMG v0.01**　6 层 C08B-U9 主控板通过 20 针排线连接 4 层采集板，两颗 ADS1298 共提供 16 路差分采集。嘉立创专业版工程包含两块 PCB 和 7 页原理图，目录内附主控板与采集板各自的 Gerber。这一版用于离体台架，整机采集待实测。[打开双板工程与制造文件](hardware/16ch-afe-hirose-1mm-1nf/)

## Gallery

### 产品 · 三种通道配置

![三款手环的 CAD 外观，从左到右为 2 通道 R7、8 通道 R12 与电极软板、16 通道 U9 广濑版](hardware/renders/openemg-channel-gallery.png)

查看单张大图　[2 通道](hardware/renders/2ch-iso-dark.png) · [8 通道](hardware/renders/8ch-iso-dark.png) · [16 通道](hardware/renders/16ch-iso-dark.png)

### PCB · 主控与采集板

| v0.01 主控板 · C08B-U9 | v0.01 采集板 · 16 通道 |
|---|---|
| ![v0.01 主控板正面，左侧为 USB 接口，中部为电池开窗](hardware/renders/v001-main-controller.png) | ![v0.01 采集板正面，可见 ADS1298 与排线接口](hardware/renders/v001-16ch-acquisition.png) |

两图均为 OpenEMG v0.01 双板的正面 3D 视图。采集板正反面各有一颗 ADS1298，通过 20 针排线与主控板连接。[查看同版原理图、PCB 与制造文件](hardware/16ch-afe-hirose-1mm-1nf/)

### 结构与装配

下面的设计渲染展示不同代际的结构。左图是 D20 采集板与 R4U6 主控的叠装方式，右图展示 2、8、16 通道方案的装配层次。复刻 v0.01 时请使用上方双板工程核对板形和接口。

| D20 与 R4U6 叠装 | 三档方案的爆炸图 |
|---|---|
| ![D20 采集板、R4U6 主控板与整机叠装](hardware/renders/c08b-overall-iso-dark.png) | ![外壳、主控和采集板分层展开](hardware/renders/openemg-assembly-exploded-iso-dark.png) |
| **柔性电极与表带** | **干电极与底盖** |
| ![34 针柔性电极软板、定位层和表带](hardware/renders/openemg-strap-system-iso-dark.png) | ![六触点底盖与 Pod D1 干电极的局部结构](hardware/renders/openemg-electrodes-iso-dark.png) |

<details>
<summary>查看套件收纳设计</summary>

![主板、软板和结构件在 EVA 收纳盒中的摆放示意](hardware/renders/openemg-kit-packaging-iso-dark.png)

</details>

[全部渲染图、俯视图与生成脚本](hardware/renders/)

## 工作原理

**一次捏指 → 多路电压波形 → 带标签的动作样本 → 手势判断**

手指发力时，参与动作的肌肉会产生微弱电信号。手环上每一路取两个贴肤电极之间的电压差；电极放在不同位置，同一次捏指在各路留下的波形也会不同。以 v0.01 为例，两颗 ADS1298 各把八路电压转换成数字采样，主控读取采样帧，桌面工作台按通道画出波形。录制时给放松、捏指等动作打标签，分类器再用这些样本学习区分动作。

**为什么还要摘下手环再测一次？** 重新佩戴会改变电极位置和接触情况。我们在柔性表带调研里复核过一个例子：一套四通道原型在握拳、张手、屈腕、伸腕四类动作上答对 152/160 次，但论文没有交代训练和测试是否来自不同佩戴。OpenEMG 因此把重新佩戴后的识别单列为一个里程碑。[阅读项目调研节选与论文出处](docs/research/wrist-semg.md)

## 当前状态与进展计划

截至 **2026-11-15**，8 通道 R01 台架板已在输入短接时连续采集 10 分钟，1,187,774 帧序号连续。最新 16 通道 v0.01 已公开工程和制造文件，下一步是在离体台架上逐路验证双板采集。

| 里程碑 | 下一步做什么 | 怎样判断完成 |
|---|---|---|
| 1 · 16 通道双板采集 | 核对主控与采集板的排线方向，在台架上检查供电、通信，再逐路接入已知信号 | 记录每一路对应的输入、波形、短接底噪和连续采集时的丢帧数 |
| 2 · 工作台接入 | 将台架实录回放到桌面端，逐项核对 2、8、16 通道配置 | 各配置的通道数、编号和录制文件与输入一致，重新打开仍能回放 |
| 3 · 重戴后识别 | 完成佩戴安全检查后，用一次佩戴录制训练样本，再用另一次佩戴单独测试 | 分别报告放松、唤起和四个方向滑动的识别结果，以及放松时的误触发次数 |

### 各版本工程与实测记录

| 通道 | 硬件工程 | 固件 | 3D 外观 | 实板测试进展 |
|---|---|---|---|---|
| **2 通道** | [ADS1292 六触点板](hardware/2ch-ads1292/) | [XIAO 蓝牙采集](firmware/xiao-ads1292-2ch/) | [R7 六触点外壳](hardware/enclosure-46x40/ads1292-shell-r7/) | 已完成设计检查，待打样、上电。 |
| **8 通道** | [D20-8CH 腕带板](hardware/8ch-ads1298/afe-d20-8ch/) · [R01 台架板](hardware/8ch-ads1298/r01-bench/) | [腕带采集](firmware/c08b-stream/) · [R01 蓝牙采集](hardware/8ch-ads1298/r01-bench/firmware-f05-ble-dout/) | [R12 外壳](hardware/enclosure-46x40/c08b-shell-r12/) · [D2-8CH 电极软板](hardware/8ch-ads1298/strap-fpc-d2-8ch/) | R01 实板短接输入采集 10 分钟，1,187,774 帧序号连续。D20-8CH 腕带待装机实测。 |
| **16 通道** | [广濑双 30 针](hardware/16ch-u9-dual30/) · [v0.01 双板与广濑 1 nF](hardware/16ch-afe-hirose-1mm-1nf/) · [讯普双 30 针](hardware/16ch-afe-xunpu-2mm-1nf/) · [双 34 针](hardware/16ch-c08b-round/) | [主控自检](firmware/c08b-bringup/) · [双 ADS1298 采集](firmware/c08b-stream/) | [U9 广濑版手表壳](hardware/16ch-u9-dual30/enclosure-u9-watch/) | 广濑版已核对数字装配，待整机采集实测。讯普版有 3 个位号待工程师确认。 |

## 桌面工作台

八通道连接页用圆环显示每个通道是否收到数据。顶部可依次进入佩戴检查、动作录制、训练和手势识别。截图使用合成信号回放。

![OpenEMG 桌面工作台的八通道连接页](app/screenshots/desktop-connection.png)

## 开始使用

[桌面工作台](app/) · [软件与开发环境](firmware/software.md) · [硬件与制造文件索引](hardware/README.md) · [通电与佩戴安全须知](SAFETY.md)

[软件许可 MIT](LICENSE) · [硬件许可 CERN-OHL-S-2.0](LICENSE-HARDWARE) · [第三方声明](THIRD_PARTY_NOTICES.md)

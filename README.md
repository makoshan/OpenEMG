# OpenEMG

OpenEMG 是用于手势研究的表面肌电（sEMG）平台。采集板记录肌电信号，桌面工作台显示波形、录制动作并训练手势分类器。

| 通道 | 硬件工程 | 固件 | 3D 外观与装配 | 实板测试进展 |
|---|---|---|---|---|
| **2 通道** | [ADS1292 六触点采集板](hardware/2ch-ads1292/) | [XIAO 蓝牙采集](firmware/xiao-ads1292-2ch/) | [R7 六触点一体盒](hardware/enclosure-46x40/ads1292-shell-r7/) | 已完成电路与 PCB 设计检查，待打样、上电。 |
| **8 通道** | [ADS1298 单面腕带板](hardware/8ch-ads1298/stacked-d20-8ch/) · [R01 台架板](hardware/8ch-ads1298/r01-bench/) | [腕带采集](firmware/c08b-stream/) · [台架采集](hardware/8ch-ads1298/r01-bench/firmware-f05/) | [F04 表带](hardware/8ch-ads1298/f04-openback-tpu/) · [叠板外壳](hardware/enclosure-46x40/) | **R01 实板**完成一次 10 分钟短接输入测试，收到 1,187,774 帧，序号连续。腕带版待装机实测。 |
| **16 通道** | 双 ADS1298：[双 30 针广濑版](hardware/16ch-u9-dual30/) · [双 30 针讯普版](hardware/16ch-afe-xunpu-2mm-1nf/) · [双 34 针版](hardware/16ch-c08b-round/) | [双核自检](firmware/c08b-bringup/) · [双芯片采集](firmware/c08b-stream/) | [广濑版手表壳](hardware/16ch-u9-dual30/enclosure-u9-watch/) · [讯普版底面装配图](hardware/16ch-afe-xunpu-2mm-1nf/assembly-bottom.png) · [双 34 针版电极组件](hardware/16ch-c08b-round/pod-d1/) | 广濑版已做数字装配检查，讯普版有 3 个位号待确认；腕带整机采集待实测。 |

![腕带与六触点一体盒的 3D 外观渲染](hardware/renders/openemg-finished-iso-dark.png)

[桌面工作台](app/) · [软件与开发环境](docs/software.md) · [硬件与制造文件索引](hardware/README.md) · [通电与佩戴安全须知](SAFETY.md)

[软件许可 MIT](LICENSE) · [硬件许可 CERN-OHL-S-2.0](LICENSE-HARDWARE) · [第三方声明](THIRD_PARTY_NOTICES.md)

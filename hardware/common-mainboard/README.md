# 共用上层主控模块（`common-mainboard`）

本目录提供两款与下层采集板通过 20P `0.5 mm` 排线座互联的上层主控方案：

| 共用主控 `R4U6` 正交俯视（渲染预览） | 共用主控 `R4U6` 透视斜视（渲染预览） |
|---|---|
| ![主控板 R4U6 俯视渲染](../renders/c08b-mainboard-top-dark.png) | ![主控板 R4U6 斜视渲染](../renders/c08b-mainboard-iso-dark.png) |

1. **`mainboard-r4u6/`（旗舰双核圆角主控）**：`43.10 × 36.50 mm` 四层 `0.6 mm` 板，板载 `STM32L432KCU6` + `nRF52840-QFAA` + `LSM6DS3TR-C` + 锂电充电与 USB 硬件互锁，适配 **2ch / 8ch / 16ch** 全系下层板；含嘉立创源文件 `C08B-main-R4U6.epcb2`、生产制造包、满载器件整板三维模型 **`c08b-mainboard-r4u6-3d.step`**，对应 5 页原理图见 `schematics/`。
2. **`adapter-p44e-xiao/`（入门开发板转接主控）**：`17.78 × 21.00 mm` 双层（2 层）`0.8 mm` 转接板，直接焊接市售 `Seeed Studio XIAO nRF52840` 模块，含原生 KiCad 工程、制造包、嘉立创 `jlc-eda/P44e-XIAO转接板-0.8mm-PCB+3D.epro2` 与带 XIAO 模块的整板三维模型 **`p44e-3d.step`**。（注意：`P44e` 的 `J1-19` 脚输出 `5V` 驱动 `2ch-ads1292` 的 USB 互锁，严禁插到未隔离该脚的旧版采集板）。

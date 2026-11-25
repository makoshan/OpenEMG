# 装配模型与许可

[整板 STEP](shoulder-s1.step) 含 1 块电路板和 49 个实装位号。模型原点在板框中心，元件面为 +Z。J3、J4 在背面，从相对的两条板边插线。数据来自 S1 PCB；装配不含 P44e、XIAO、电池、外壳、插头或电极线。

| 自绘模型 | 位号 | 尺寸依据，单位 mm |
|---|---|---|
| [JST PH 三针侧插](models/PH3-side.step) | J3、J4 | 宽 9.9、高 5.5，信号脚距 2.0。模型从焊尾到插口的深度 8.6，开口朝模型局部 −Y。[JST PH 图纸第 4 页](https://www.jst.com/wp-content/uploads/2025/06/ePH.pdf#page=4) |
| [Hirose FH34 20 针](models/FH34-20.step) | J2 | 总宽 12、深 3.8、高 1.0。信号排 1 脚在局部 +X，壳体中心由信号排向插口偏 1.4。[Hirose 产品图纸](https://www.hirose.com/en/product/p/CL0580-1256-9-50) |
| [TI PBS 32 引脚](models/TI-PBS32.step) | U1 | 5 × 5 塑体，含引脚 7 × 7，0.50 脚距，按 1.20 最大高度建模。[TI ADS1292 机械图](https://www.ti.com/lit/ds/symlink/ads1292.pdf#page=77) |
| [TI DPY 双端封装](models/TI-DPY2.step) | D1–D5 | 1.0 × 0.6 塑体，按 0.45 最大高度建模。[TI ESD401 外形图](https://www.ti.com/lit/ds/symlink/esd401.pdf) |

以上四种模型的插腔、端子和壳壁为按封装方向绘制的简化几何，供布置与静态间隙核对。锁扣行程、极限公差、压接触点啮合、线缆折弯半径和实物插拔仍待验证。其余 40 个位号使用 KiCad 标准模型。标称 0.8 mm 是成板厚度；本次 STEP 使用 KiCad 的板体导出设置，未单独导出铜层和阻焊层。

## 复现

1. 安装 KiCad 10 的标准封装与 3D 模型库。打开同目录的 `shoulder-s1.kicad_pro`，随工程的 `S1.pretty` 和 `models/` 通过相对路径引用。
2. 用 `kicad-cli pcb export step --force --user-origin 100x100mm -o shoulder-s1.step shoulder-s1.kicad_pcb` 重新导出。
3. 用带有 FreeCAD 1.1 的 `Part`、`Import` 模块的 Python 运行 `models/check_assembly.py`。检查包括实装位号集合、50 个装配实例的有效性、两两相交体积及左右插腔方向。要重建四种简化模型，在同一环境运行 `models/build.py`。

## 来源和再利用

OpenEMG 的板图、原理图、自绘封装结构及四种自绘机械模型按 CERN-OHL-S-2.0 公开，Python 脚本按 MIT 公开。[硬件许可](https://github.com/makoshan/OpenEMG/blob/main/LICENSE-HARDWARE) · [代码许可](https://github.com/makoshan/OpenEMG/blob/main/LICENSE)

`S1.pretty` 中的 JST PH、TQFP 两份封装来自 KiCad 10.0.6 封装库。此处改为引用随工程提供的 3D 模型，原封装的 CC BY-SA 4.0 和 KiCad 附加例外继续适用。其余三个项目封装源自 OpenEMG 已公开的双通道板库。整板 STEP 内包含 KiCad 标准库的电阻、电容、电感和 SOT 封装几何；各自的署名及原许可证以 KiCad 库文件为准，包括对使用库创建的电子设计和导出物的例外。[KiCad 库许可说明](https://www.kicad.org/libraries/license/) · [KiCad 封装库](https://gitlab.com/kicad/libraries/kicad-footprints) · [OpenEMG 双通道板封装库](https://github.com/makoshan/OpenEMG/tree/main/hardware/2ch-ads1292/board/libs)

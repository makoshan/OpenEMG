# 通用 `46 × 40 mm` 圆润外壳结构家族（`enclosure-46x40`）

> **验证状态**：CAD 参数化建模、跨目录自包含重算与布尔干涉/反例检查已通过，当前处于 3D 打印首件试配迭代阶段（名义尺寸，量产前请先打单件试配公差）。

- **`c08b-shell-r12/`（8/16ch 四角螺丝柱圆角壳）**：适配 `R4U6 + D20` 上下叠板的 `46 × 40 mm` 光固化透明圆角螺丝壳，含单实体可打印 `tray`、`cover`、`switch_plunger`、东北角专用绝缘支柱 `pcb_standoff_ne` 与标准支柱（`.step`/`.stl`）、总装与爆炸图（`.step`/`.glb`）、外扣式六孔电极平底盖 `capsule-cap-d2/`（含 `.3mf` 切片工程）及一体成型表带切片 `slice-tpu-x2d-20261109/`。
- **`c08b-shell-r13-notch/`（8/16ch 四角缺口无螺丝抱柱壳 + Fusion `.f3d`）**：将四角穿板圆孔柱改为抱进上下 PCB 四角方缺口的无螺丝抱柱结构（含上盖四根定位销与开关顶杆东西向导向脚），同时提供 **`build123d` 参数化源码（`build.py` / `check.py`）**、**Fusion 360 原生源档（`.f3d`）** 以及全部单件/总装/爆炸 `.step`、`.stl`、`.glb`。
- **`ads1292-shell-r7/`（2ch 底面六触点叠板壳）**：适配 `2ch-ads1292 + P44e + XIAO nRF52840` 的同尺寸圆润壳体，自带官方 `sources/XIAO-nRF52840-v15.step`，提供自包含生成器 `model.py`、整机总装 `host.step`、可直接切片打印的单件 `shell.step` / `lid.step` / `ads1292-r7-{shell,lid}.stl` 及 1:1 纸样 PDF。

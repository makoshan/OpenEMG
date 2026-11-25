# OpenEMG MAIN V1.0B 主板定版

本次首件下单采用 2026-11-24 丝印版。主板单板 46.0 × 36.5 mm、四层，底面丝印为 `OpenEMG MAIN V1.0B` 和 `20261124`。首批 5 块裸板，其中 2 块双面贴片。当前状态为已下单，实物供电、烧录和射频性能待首件验证。

## 文件用途

- `OpenEMG-MAIN-V1.0B/` 为嘉立创 EDA 专业版文件夹工程，含主板 PCB 和 5 页主板原理图，打开同名 .eprj3。
- `fabrication/` 保留本次提交给工厂的 Gerber 压缩包、原始 BOM 和贴片坐标 CPL。制板取该 Gerber。
- `assembly/BOM.csv` 对应工厂实际选料，贴片时与 `fabrication/CPL.csv` 配套使用。每板 127 个贴片位号。
- [主板 STEP 模型与尺寸](mechanical/README.md)提供裸板和首件带器件模型，可用于设计外壳和核对插口。
- `SHA256SUMS` 可在此目录用 `shasum -a 256 -c SHA256SUMS` 校验文件。

## 首件装配

X1 使用 Abracon ABS05-32.768KHZ-X-T5（C5355144，32.768 kHz、4 pF、1610 两脚），替代原 BOM 中的 C515348。U4 选用 nRF52840-QIAA-R（C190794）。R31 和烧录排针 H1 均不贴，H1 保留焊盘。重新从 EDA 导出物料或钢网时需重新核对 R31、H1、U4、X1，确保与此定版一致。

台架固件默认使用线性稳压。启用 nRF 的 DC/DC 前需重新核对 L2 的直流电阻和供电配置。板载天线与 RF1 的分支仍保留，蓝牙距离待实测。

## 许可

主板设计使用 CERN-OHL-S-2.0。许可证全文见同目录的 [LICENSE-HARDWARE](LICENSE-HARDWARE)。原理图中第三方图框保留原作者署名。

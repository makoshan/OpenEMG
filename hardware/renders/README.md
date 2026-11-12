# OpenEMG 硬件三维光追渲染图集（`hardware/renders`）

> **性质与验收边界声明**：本目录下全部图片均为基于仓库原生 KiCad PCB（`.kicad_pcb`）与参数化三维结构（`.step` / `.glb`）生成的 **Blender Cycles 三维光追设计预览图，非实物照片，不代表制造或人体佩戴验收通过**。其中 `openemg-kit-packaging-*` 为**模块化开源复刻套件防静电 EVA 收纳示意**，非商业零售包装。

## 1 · 图集索引（共 8 组 16 张 `2400 × 1350` 影棚暗底渲染图）

| 类别 | 正交俯视图（Top） | 85 mm 透视斜视图（Iso） | 对应仓库真源资产 |
|---|---|---|---|
| **成品图（整表 + 一体盒）** | `openemg-finished-top-dark.png` | `openemg-finished-iso-dark.png` | `c08b-shell-r13-notch/watch_military_green_strap.glb` + `afe-d20n` + `mainboard-r4u6n` + `ads1292-shell-r7/host.step` |
| **套件收纳包装图（开源复刻示意）** | `openemg-kit-packaging-top-dark.png` | `openemg-kit-packaging-iso-dark.png` | `c08b-shell-r13-notch/assembly.glb` + `afe-d20-8ch` + `ads1292-2ch` + `strap-d2-8ch` + `p44e` + `pod_strip_d1` |
| **三档叠板立体爆炸组装图** | `openemg-assembly-exploded-top-dark.png` | `openemg-assembly-exploded-iso-dark.png` | 左 16ch `R13+R4U6N+D20N` · 中 8ch `Cap D2+D20-8CH+R4U6N` · 右 2ch `R7+ADS1292+P44e+XIAO` |
| **多档位柔性电极表带系统图** | `openemg-strap-system-top-dark.png` | `openemg-strap-system-iso-dark.png` | `strap-fpc-d2` (`strap-a/b`) + `tpu-layer-d2` + `strap-fpc-d2-8ch` + `tpu-layer-d2-8ch` + `f04-openback-tpu` |
| **贴肤镀金干电极微距图** | `openemg-electrodes-top-dark.png` | `openemg-electrodes-iso-dark.png` | `2ch-ads1292` 板底六触点 + `capsule-cap-d2` 外扣六孔底盖 + `pod-d1` 单豆组装/分解与 16 节织带电极条 |
| **C08B 核心双板与胶囊总览** | `c08b-overall-top-dark.png` | `c08b-overall-iso-dark.png` | `afe-d20` + `mainboard-r4u6` + `c08b-shell-r12` 叠装总览 |
| **16ch 采集下板 `D20` 单板特写** | `c08b-afe-d20-top-dark.png` | `c08b-afe-d20-iso-dark.png` | `16ch-c08b-round/afe-d20` |
| **共用双核主控上板 `R4U6` 单板特写** | `c08b-mainboard-top-dark.png` | `c08b-mainboard-iso-dark.png` | `common-mainboard/mainboard-r4u6` |

## 2 · 一键可复现重算管线（源文件 100% 只读）

渲染管线由两步脚本组成，运行前后对全部 23 份源仓库 PCB/STEP/GLB 执行 SHA-256 逐字节校验（`SOURCE_UNCHANGED`），并在渲染时内置四重硬门禁（`assert_no_xy_overlap` 水平净距断言、`assert_z_stack_order` 爆炸塔自下而上逐层净空递增断言、`in_frame(0.01)` 100% 安全框取景断言、`clipped <= 1.0%` 防高光过曝断言）：

```bash
# 1. 从 hardware/ 只读提取 .pcb3d（2032 DPI 铜纹 + 哑光黑阻焊 + 沉金焊盘）与子实体语义 STL（需 KiCad 9/10 与 build123d 环境）
python3 hardware/renders/prepare_assets.py hardware /tmp/openemg-render-assets

# 2. 调用 Blender 5.x Cycles（AgX - Base Contrast，85mm 镜头，128 samples）独立进程逐场景渲染全部 10 张 2400×1350 PNG
python3 hardware/renders/render_gallery.py \
  --assets /tmp/openemg-render-assets \
  --out hardware/renders \
  --samples 128 \
  --scale 100
```

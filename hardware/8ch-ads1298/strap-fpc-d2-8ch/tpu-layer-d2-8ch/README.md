# C08B 表带电极层 D2-8CH（8通道单片软板版，2026-11-12）

状态：**已实现未验收**（STEP/STL 生成、0.5 mm 三层网格门、源板 `.kicad_pcb` 右手系独立核对、与满载 `strap-d2-8ch-3d.step` 实心三维布尔零干涉、33 项反例全红、DfAM 测量、Bambu X2D TPU 95A HF 含 G-code `.3mf` 切片、1:1 A4 装配与裁胶纸样均已完成；未实际打印、未试戴、未上人体）。

## A 适用范围与较 16 通道版的改动

适配 **C08B 8 通道单面方案**（顶层主控 `R4U6 / R4U6N` + 下层单面采集板 `D20-8CH / D20N-8CH` + 单片四层表带软板 `strap-d2-8ch` + 胶囊底壳/底盖 `tray_d2 / cap_d2`）：

| 分件 | 8ch 版尺寸（`D2-8CH`） | 16ch 版尺寸（`D2`） | 孔数与背面串阻浅槽 | 说明 |
|---|---|---|---|---|
| 北片 `layer_d2_8ch_north` | `26.2 × 16.2 × 0.80 mm` | `26.2 × 16.2 × 0.80 mm` | 4 孔（`CH3, CH4`）+ 4 浅槽（`R5–R8`） | 与 16ch 北片几何同规 |
| 南片 `layer_d2_8ch_south` | **`26.2 × 32.2 × 0.80 mm`** | `26.2 × 96.2 × 0.80 mm` | 8 孔（`CH5–CH8`）+ 8 浅槽（`R9–R16`） | 缩短 **64.0 mm**，消除南侧 16 个悬空盲孔积汗带 |
| 胶囊底盖（直接复用） | `../../../enclosure-46x40/c08b-shell-r12/capsule-cap-d2/cap_d2` | 同左 | 4 圆孔（`CH1, CH2` `Φ6`）+ 2 方孔（`EB1, EB2` `3×3`） | 8ch 单片软板背面带 6 窗 `0.20 mm` PI 垫片，零改模复用 `tray_d2 / cap_d2` |

## B 叠层与坐标系（从表带往皮肤）

1. **现成 25 mm 战术表带**（约 `1.6 mm`，假设值，不改表带本体）
2. **焊盘背面圆形 PI 补强**（`Ø7.2 × 0.20 mm`，共 12 处，嘉立创 FPC 出厂压合）
3. **单片四层压延铜 FPC**（`strap-d2-8ch`，`0.203 mm`，`F.Cu` 朝皮肤，12 颗 `0402` 100 kΩ 串阻在 `F.Cu`）
4. **3M 9448A 双面胶**（`0.10 mm`，按纸样右下角 1:1 模板镂空 12 个 `Φ6.5` 孔与 12 个 `2.16 × 1.24` 串阻窗）
5. **TPU 电极层（本件）**（`0.80 mm`，`Φ6.5` 通孔 + 背面 `0.45 mm` 深串阻浅槽，槽顶余 `0.35 mm`）
6. **镀金铜片**（`Φ6.0 × 2.0 mm`，表带段共 12 颗，胶囊底另需 4 颗 `Φ6.0 × 2.0` 圆铜片 + 2 颗 `3 × 3 × 2` 方铜片；垫 9448A 时凸出 TPU 表面 `1.10 mm`，压平贴死时凸出 `1.20 mm`）

- **右手系坐标换算**：TPU 层 `+Z` 朝皮肤，`X = 50 − FPC 板 y`，`Y = 58 − FPC 板 x`，`Z = −板 z`（行列式 `= +1`）。北端 `+X` 角切 `1.5 mm × 45°` 防翻面角：安装时浅槽面朝 FPC、切角朝北端 `+X`，避免左右/南北翻面压坏串阻。

## C 生成、检查与切片产物

| 文件 | 用途 |
|---|---|
| `build.py` → `layer_d2_8ch_north.{step,stl}`、`layer_d2_8ch_south.{step,stl}`、`manifest.json` | 参数化生成 STEP 主模型与打印向 STL（校验源板 `strap-d2-8ch.kicad_pcb` SHA-256 `17c3693a`） |
| `check.py` → `checks.json` | 0.5 mm 三层网格全扫 + 源板 `.kicad_pcb` 独立解析落槽核对 + 与 `strap-d2-8ch-3d.step` 实心三维布尔干涉（垫 `0.10 mm` 9448A 与 `0.00 mm` 贴死均为 `0.0 mm³`）+ 33 项反例全红 |
| `slice.sh` + `flatten.py` → `layer_d2_8ch-X2D-TPU95A.3mf` | Bambu Lab X2D `0.4 mm` 喷嘴，`Bambu TPU 95A HF`，`0.16mm Standard` 北南两片同盘平放含 G-code 切片包（SHA-256 `6189e957`，2 对象、`outside=0`、5 层、预计 `10m 2s`、耗材 `0.86 g`；较 16ch 版 `17.5m / 2.30 g` 减半） |
| `paper_pattern.py` → `paper_pattern_d2_8ch_1to1_A4.{pdf,png}` | A4 横版 1:1 整体对位纸样（PDF SHA-256 `5f69d2c3`）+ 北/南 9448A 与胶囊 PI 垫片独立 1:1 裁切模板 + 横 100 mm / 纵 50 mm 双轴校准尺 |
| `dfam_north.json`、`dfam_south.json` | `dfam_tool.py` 对照 ISO/ASTM 52910 FDM 默认门限测量：水密单连通（`watertight=true`，欧拉示性数北 `-6` / 南 `-14`），串阻浅槽无支撑桥接跨度 `1.24 mm ≤ 10.0 mm` 通过；中位壁厚 `0.80 mm`、槽顶最薄 `0.35 mm`（2 层）、边壁 `0.85 mm`（2 圈 0.42 线宽），属柔性 TPU 贴片薄壁有意设计（低于刚性件 `1.2 mm` 通用默认限值，与 16ch `layer_d2` 同规） |

## D 复现命令

```bash
CAD_PY=${CAD_PY:-python3}
PY=${PY:-python3}
$CAD_PY -B build.py
$CAD_PY -B check.py
$PY -B paper_pattern.py
PY=$PY sh slice.sh /tmp/d2-8ch-slice
```

## E 未验证项

- 日字扣环离北生耳距离按 `55 mm` 保守估算（未实量现成表带扣位）；北片仅 2 路，净距余量 `29.05 mm`。
- `layer_d2_8ch-X2D-TPU95A.3mf` 仅完成本机 CLI 切片与 G-code/CRC 校验，未发送至打印机实打，建议在 Bambu Studio 中作为项目打开预览确认后再发起打印。
- 未试戴、未做人体肌电采集验收。

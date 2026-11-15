# C08B 双核真机免飞线 HIL 联调与桌面正式包 E2E 验证套件

本目录归档 `STM32L432KBU6/KCU6`（经 ST-LINK V2 SWD 连接）与 `Seeed XIAO nRF52840 Sense`（经 USB CDC 串口连接，含板载真实 `LSM6DS3TR-C` 六轴 IMU `0x6A` 与 S140 `YUANLI-C08B` BLE 广播）的双核协议、故障/互锁注入、同连接在线跨档热切及桌面正式包真窗口 E2E 验证脚本与实测报告。

> **安全红线**：全套脚本全程保持默认双硬件锁关闭（`MAKO_C08B_AFE_ENABLED=0`、`MAKO_BENCH_MEASURED=0`），`PC14 (ANA_EN)` 实测全程为 `0`。

## 目录结构

| 文件 / 目录 | 说明 |
|---|---|
| `prepare_and_build.py` | 在临时目录构建 `STM32L432`（`C08B_SWD_HIL=1` 128 槽环形邮箱）与 `XIAO nRF52840` UF2 镜像（不污染源码树） |
| `xiao_c08b_hil_pio/` | `Seeed XIAO nRF52840 Sense` PlatformIO 联调工程（复用 `../../../common/stream_proto.h`，支持免焊 USB 桥与 6 线硬件 `SPIS1` 无缝切换） |
| `run_dual_mcu_full_matrix.py` | `T1-a` 全档位切换（`16CH@1kHz / 8CH@2kHz / 2CH@500Hz / 16CH@500Hz`）、`10 s` 浸泡（`10,032` 帧 `0` 丢样）与 CRC16 篡改拦截实测 |
| `run_t1d_fault_injection.py` | `T1-d` 首包断链自停（`FAULT_LINK_DROP=7`）、`800 ms` 拥塞溢出缺口捕获、跨核 `VBUS` 互锁拦截 6 类真采及跨连接防拼接必败反例 |
| `run_t1e_fw_opt_hil.py` | `T1-e` 裸板 `PA9/PA10` 内部弱上拉快启（`40.45 ms`）与同连接四段在线跨档热切（`16->8->2->16CH` `0` 混包 / `0` 缺口）实测 |
| `run_t0c_packaged_e2e.cjs` / `run_app_ux_e2e.cjs` | 独立打包 `OpenEMG.app` 真窗口验证（冷启动单进程、首屏三卡同屏、`97B` 16 路底噪网格、非现场源禁录 `403` 反例） |
| `reports/*.json` | 2026-11-15 双真机与正式包实测原始 JSON 报告 |

## 快速复现命令

```bash
# 1. 构建 L432 HIL ELF 并烧录（需连接 ST-LINK V2）
python3 firmware/c08b-stream/tools/hil_dual_mcu/prepare_and_build.py
pyocd load -t stm32l432kc /tmp/c08b-dual-hil/c08b-stream-hil/build/l432.elf

# 2. 编译并烧录 Seeed XIAO nRF52840 Sense（需连接 USB）
pio run -d firmware/c08b-stream/tools/hil_dual_mcu/xiao_c08b_hil_pio -t upload

# 3. 运行双真机在线热切与硬件故障/互锁套件
python3 firmware/c08b-stream/tools/hil_dual_mcu/run_t1e_fw_opt_hil.py
python3 firmware/c08b-stream/tools/hil_dual_mcu/run_t1d_fault_injection.py
```

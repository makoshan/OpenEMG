# OpenEMG 全栈硅级在环测试矩阵（STM32L432 + nRF52840 + XIAO Dongle + XIAO-2CH，48/48 用例）

本目录提供一套**零硬件连接、不改默认安全锁（`0/0`）**的 C++20 寄存器级数字孪生与 Mach-O 段隔离纤程协同仿真器，把仓库中全部四大嵌入式目标（共 **9 个原生动态库**）与 Python 上位机/DSP 闭环联调：

1. **`Sim-1`（`10/10`）**：`c08b-bringup`（`STM32L432` + `nRF52840` + `16CH / 8CH / 2CH` 上电自检、关机与 6 项硬件故障/短路反例）。
2. **`Sim-2`（`19/19`）**：`c08b-stream`（`64 MHz STM32L432` + `nRF52840 S140` 全速流式采集、在线 `WREG` 分通道 `channel_gains` 幅值折算与校准 MUX 防覆盖、`CONFIG1` 采样率对齐与双片异速/冲突拦截、`CLRO` 双核纪元确认防假清零、`16CH@2k+IMU`、`VBUS` 微秒级硬关断）。
3. **`Sim-3`（`11/11`）**：`ble-dongle/xiao-central`（Seeed XIAO nRF52840，含 **256B TinyUSB CDC TX FIFO 压力仿真**、正时长 `seconds=1` `'B'` 带宽压测、停读/断连看门狗恢复及 `0xFFFFFF00` 跨 $2^{32}$ 回绕模差边界校验）与 `ble-dongle/c6-central`（Seeed XIAO ESP32-C6 NimBLE）无线桥接。
4. **`Sim-4`（`8/8`）**：`xiao-ads1292-2ch`（Seeed XIAO nRF52840 Sense + P44e + ADS1292 独立 2CH 固件）直连与接收器 `DONGLE_PEER_MTU` 双向 MTU=247 防撞、两步法 `150 ms` RLD 预热、运行中 `VBUS` / `AVDD` / `DRDY Overrun` 零延迟 `status_chr` 刷新与 `STOP` 故障码保留。

## 一键复现（macOS clang++ & arm64/x86_64）

```bash
TMP_BUILD=$(mktemp -d)
SIM_BUILD_DIR="$TMP_BUILD" zsh firmware/c08b-stream/tools/sil_full_matrix/build_all.sh
SIM_BUILD_DIR="$TMP_BUILD" python3 -B firmware/c08b-stream/tools/sil_full_matrix/run_sim1_bringup.py
SIM_BUILD_DIR="$TMP_BUILD" python3 -B firmware/c08b-stream/tools/sil_full_matrix/run_sim2_stream.py
SIM_BUILD_DIR="$TMP_BUILD" python3 -B firmware/c08b-stream/tools/sil_full_matrix/run_sim3_dongle.py
SIM_BUILD_DIR="$TMP_BUILD" python3 -B firmware/c08b-stream/tools/sil_full_matrix/run_sim4_xiao_2ch.py
/bin/rm -rf "$TMP_BUILD"
```

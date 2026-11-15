# OpenEMG 蓝牙与 USB 传输协议及分离式主控接口规范

**状态**：已实现未验收（主机编解码、C11 共享协议头、安全掩码变异自检与双核 HIL 虚拟排线已验证；实物首板上电与穿戴验收待做）。

---

## 1. 架构定位：上下分离设计、单晶振同源时钟与上位机全量计算

OpenEMG C08B 采用**模拟采集板（下板）与数字主控板（上板）物理分离**架构，两板通过 20P 0.4 mm FPC 排线对接：

1. **主控板可插拔演进，模拟下板保持冻结**：
   - 下层采集板（`AFE-30P` / `D20` 16 通道双 `ADS1298`、`D20-8CH` 8 通道单 `ADS1298`、`2ch-ads1292` 2 通道 `ADS1292`）只承载生物电前端、ESD 防护、模拟供电（`LM27762` $\pm 2.5\text{ V}$）与电极接口；
   - 上层数字主控板只要遵守第 2 节定义的 20P `FPC1/J_AFE` 引脚契约，可自由选用不同方案（如当前 v0.01 双芯片 `STM32L432KC + nRF52840`、单芯片 `nRF52840/nRF54L15`、双模 Wi-Fi/BLE `ESP32-S3/C6` 或带屏幕的交互主控），无需重画或重认证下层模拟板。
2. **端侧零特征计算，100% 算力放在上位机**：
   - `STM32L432KC` 在架构中仅承担**确定性实时 DMA/SPI 采样缓冲、双片 `DRDY` 对齐、同源微秒打戳、安全寄存器回读校验与 USB DFU 烧录**，不在 MCU 上跑滤波、特征提取或神经网络推理，更不驱动屏幕；所有信号处理、结印识别与力回归统一在 Mac / PC / 手机上位机完成。
3. **全机 ADC 同源单晶振，消除多晶振拍频与滑码**：
   - 16 通道采集板上只有**唯一一颗 `2.048 MHz` 有源晶振 `X1`**，同时喂给 `U1` 与 `U2` 两颗 `ADS1298` 的 `CLK` 引脚（`CLKSEL=0`），并由同一根 `ADS_START` 同步起采，双片 $\Delta\Sigma$ 调制器严格同频同相，不存在双 ADC 异频滑码；
   - `STM32L432KC` 外部**零晶振**（使用内部 `HSI16` 经 PLL 倍频至 `64 MHz` CPU、APB 分频保持 `16 MHz` SPI 总线主机时钟，不驱动 ADC 采样率）；`nRF52840` 的 `32 MHz` 晶振仅服务 `2.4 GHz` BLE 射频载波（低频睡眠时钟走内部 RC，`XL1/XL2` 复用为安全互锁引脚）。

---

## 2. 上下板 20P 分离接口契约（`FPC1` ↔ `FPC2` / `J_AFE`）

上层主控板通过 `ANA_EN` 信号在**主控板内部**门控受保护的 `3V3_AFE` 开关供电轨（`ANA_EN` 不占用 20P 排线引脚；收到 `STOP`、触发故障或检测到 USB VBUS 硬件互锁时立即关断 `3V3_AFE` 并把全部 SPI/控制线置安全低阻，采集板侧由 `3V3_AFE` 派生数字 IOVDD 与 `LM27762` $\pm 2.5\text{ V}$ 模拟双极电源）。两板通过 20P 0.4 mm 同面异侧翻折排线对接（主控脚 $k$ 对采集板脚 $21-k$，由 `firmware/c08b-stream/tools/pins.py --check-u9 --self-test` 自动逐脚核验）。

### 2.1 v0.01 旗舰 6 层双核主控契约（`MCU-U9 FPC1.1..20` ↔ `AFE-30P FPC2.20..1`）

任何接入 v0.01 `AFE-30P` 超薄采集板的替换版上层主控板，须严格对齐下表引脚（真值源：`tools/pins.py:U9_FPC1_TO_AFE30P_MAP`）：

| 主控 `FPC1` | 采集 `FPC2` | 主控网络 | 采集板网络 | 方向（相对主控） | 电气与时序约束 |
|---:|---:|---|---|---|---|
| `1` | `20` | `GND` | `GND` | 公共参考地 | 排线首端地屏蔽 |
| `2` | `19` | `NC` | `GND` | 悬空 / 地 | 主控空脚，采集侧接地屏蔽 |
| `3` | `18` | `AFE_DRDY_B` | `DRDY2#` | 输入（下降沿有效） | 副片 `U2`（CH9..16）转换就绪；核对与 `U1` 失步计数 |
| `4` | `17` | `AFE_CS_B` | `CS#2` | 输出（低有效） | 副片 `U2` SPI 片选 |
| `5` | `16` | `AFE_DIN` | `DIN` | 输出（`SPI_MOSI`） | 主控写命令 / 寄存器配置数据 |
| `6` | `15` | `AFE_PWDN` | `PWDN#` | 输出 | `ADS1298` 会话全程保持高（防泄放 `22 µF` `VCAP1`） |
| `7` | `14` | `AFE_RESET` | `RESET#` | 输出 | `3V3_AFE` 上电稳定 $\ge 1050\text{ ms}$ 后发 `20 µs` 低脉冲复位双片 |
| `8` | `13` | `NC` | `CLK` | 悬空（子板自供） | 采集板板载单颗 `2.048 MHz` 晶振 `X1` 同源直驱双 `ADS1298`，主控不灌钟 |
| `9` | `12` | `AFE_START` | `START` | 输出 | 双片同步起采门控；寄存器写核通过后统一拉高 |
| `10` | `11` | `AFE_CS_A` | `CS#` | 输出（低有效） | 主片 `U1`（CH1..8）SPI 片选 |
| `11` | `10` | `AFE_SCLK` | `SCLK` | 输出（`SPI_SCK`） | `CPOL=0, CPHA=1`（SPI Mode 1）；ID 探测 `1 MHz`，流式采样 `4 MHz` |
| `12` | `9` | `GND` | `GND` | 公共参考地 | `SCLK` 与 `DOUT` 之间的高速串扰隔离地线 |
| `13` | `8` | `NC` | `GND` | 悬空 / 地 | 隔离地槽 |
| `14` | `7` | `GND` | `GND` | 公共参考地 | 隔离地线 |
| `15` | `6` | `DOUT_B` | `DOUT` | 输入（`SPI_MISO`，弱下拉） | 双片共享 MISO（片选未中时三态；未贴 `U2` 时 `RREG 0x00` 稳定读回 `0x00`） |
| `16` | `5` | `AFE_GPIO3` | `GPIO3` | 输入 | 预留状态线（板上 `GPIO1/2/4` 接地，固件强制 `GPIO=0x0F` 全输入防短路） |
| `17` | `4` | `ADS_DRDY_A` | `DRDY#` | 输入（下降沿有效） | 主片 `U1` 转换就绪中断线 |
| `18` | `3` | `NC` | `CLKSEL` | 悬空 | 采集板上固定拉低选择外部同源晶振 `X1` |
| `19..20` | `2..1` | `3V3_AFE` | `+3.3V` | 主控 → 采集（受控供电） | 由主控内部 `ANA_EN` 门控并受硬件 `U10 OE_N` VBUS 互锁保护的供电轨 |

### 2.2 候选演进系列映射与跨代防呆红线（`R4U6(N) J_AFE` ↔ `D20` / `2ch-ads1292`）

> **严禁跨代混插警告**：候选演进板 `R4U6 / R4U6N` 的 `J_AFE`（`1..2 = 3V3_AFE`，`20 = GND`）与 v0.01 旗舰版 `MCU-U9 FPC1`（`1 = GND`，`19..20 = 3V3_AFE`）**首尾电源极性正好相反**！`MCU-U9` 仅可接 `AFE-30P`；`R4U6(N)` 仅可接 `D20`（16CH/8CH）或 `2ch-ads1292`（真值源：`tools/pins.py:JAFE_CROSS_MAP`，即 `1..2:3V3_AFE`, `3:NC`, `4:ADS_DRDY_A`, `5:AFE_GPIO3`, `6:DOUT_B`, `7:GND`, `8:NC[2ch=GND]`, `9:GND`, `10:AFE_SCLK`, `11:AFE_CS_A`, `12:AFE_START`, `13:NC`, `14:AFE_RESET`, `15:AFE_PWDN[2ch=复位]`, `16:AFE_DIN`, `17:AFE_CS_B`, `18:AFE_DRDY_B[2ch=AVDD_SENSE]`, `19:NC[2ch=XIAO_5V]`, `20:GND`）。

---

## 3. BLE GATT 无线传输协议（外设名 `YUANLI-C08B`）

统一 128-bit UUID 基址：`7b24c101-3948-4f03-9d11-12bb9d0000XX`（连接参数目标：`2M PHY`、`DLE = 251`、`ATT MTU = 247`、连接间隔 `7.5 ms`）。

### 3.1 服务与特征表

| 末字节 `XX` | 名称 | 属性 | 长度上限 | 用途 |
|---|---|---|---|---|
| `01` | `SERVICE` | Primary Service | — | OpenEMG V12 / C08B 统一采集服务 |
| `02` | `DATA` | Notify | `232 B` | 实时肌电原始帧（F01 `v1` 8CH/2CH 或 `v4` 16CH 无损双片包） |
| `03` | `META` | Read | `440 B` | UTF-8 JSON 元数据（拓扑、协议号、采样率、构建 ID、在线寄存器回读摘要） |
| `04` | `STATUS` | Read | `64 B` | 二进制四段健康与阻塞计数器（小端，对齐 `host/v12_status.py` v1） |
| `05` | `CONTROL` | Write (With Response) | `8 B` | 模式启停、采样率切换、子板探测、**在线寄存器读写（`RREG`/`WREG`/`CLRO`）** |
| `06` | `IMU_DATA` | Notify | `36 B` | `104 Hz` 6 轴陀螺+加速度包（同源 `L432_DWT_1MHz` 64 位微秒时间戳） |

### 3.2 `DATA (0002)` 与 `IMU_DATA (0006)` 数据包格式

共用 16 字节小端包头（`<BBBBIQ`）：

| 偏移 | 类型 | 字段 | 取值说明 |
|---:|---|---|---|
| `0` | `u8` | `version` | `1`（8CH/2CH 肌电或 IMU） \| `4`（16CH 双 `ADS1298` 无损帧） |
| `1` | `u8` | `kind` | `1` = EMG ADC \| `2` = 6 轴 IMU |
| `2` | `u8` | `count` | `v1` EMG: `1..8` 帧；`v4` 16CH EMG: `1..4` 帧；IMU: `1` 帧 |
| `3` | `u8` | `flags` | `bit0=SYNTHETIC(0x01)`，`bit1=SESSION_START(0x02)`，`bit2=RECONFIGURE(0x04)` |
| `4..7` | `u32 LE` | `seq` | 本包首帧样本序号（带 `SESSION_START` 时必为 `0`；断连重连绝不拼接） |
| `8..15` | `u64 LE` | `timestamp_us` | 首帧采样时刻（`L432_DWT_1MHz` 自由运行 64 位微秒计时器） |

载荷结构：
- **F01 `v1` 单帧（`27 B`，用于 8CH / 2CH）**：`status_u24_be[3]`（高 4 位必为 `0xC`）+ `ch1..ch8` 共 $8 \times 3\text{ B}$ 有符号 24-bit 大端补码（2CH 模式下 `ch3..ch8` 填 `0`）。8 帧满包 $16 + 8 \times 27 = 232\text{ B}$。
- **F01 `v4` 单帧（`54 B`，用于 16CH）**：`status_a[3] + ch1..8[24] + status_b[3] + ch9..16[24]`（主副两片状态头均保留供上位机逐帧核验 `0xC`）。4 帧满包 $16 + 4 \times 54 = 232\text{ B}$。
- **`IMU_DATA` 单帧（`20 B`，总包长 `36 B`）**：`gx, gy, gz, ax, ay, az`（`<6h`）+ `fresh_mask(u8=0x03)` + `pad[3]` + `read_latency_us(u32 LE, <9000)`。

### 3.3 `CONTROL (0005)` 命令集（BLE 直连与 USB 接收器 `'W'` 帧完全通用）

| 4 字节命令字 | 长度 | 附加参数字节 | 功能与硬件锁要求 |
|---|---:|---|---|
| `"STOP"` | `4 B` | 无 | 立即停采并拉低 `ANA_EN` / `ADS_START` / `ADS_PWDN`（任何锁态可用） |
| `"SYN1"` | `4..7 B` | `[4..5]=fs_hz(u16 LE)`，`[6]=ch(2/8/16)` | 免开模拟电的双核合成流压测（默认锁关闭时可用，强制打 `SYNTHETIC`） |
| `"PRB1"` | `4 B` | 无 | 只读探测子板 `ID` 更新 `META.afe` 后立即断电（需解锁台架门且无 VBUS） |
| `"TST1"` | `4` 或 `6 B` | 可选 `[4..5]=fs_hz(500/1000/2000)` | 内部 `1 Hz` 方波自检（`U1/U2` 均开 `INT_TEST=1`，需解锁且无 VBUS） |
| `"SHT1"` | `4` 或 `6 B` | 可选 `[4..5]=fs_hz(500/1000/2000)` | 内部输入短接（`MUX=0x01`）测本底噪声（需解锁且无 VBUS） |
| `"EXT1"` | `4` 或 `6 B` | 可选 `[4..5]=fs_hz(500/1000/2000)` | 外部电极输入、不开 RLD（需解锁且无 VBUS） |
| `"EXR1"` | `4` 或 `6 B` | 可选 `[4..5]=fs_hz(500/1000/2000)` | 外部电极 + 两步 `150 ms` 预热启用主片 `U1` RLD（需解锁且无 VBUS） |
| `"RLD1"` | `4` 或 `6 B` | 可选 `[4..5]=fs_hz(500/1000/2000)` | RLD 环路诊断（`ADS1298` 禁置 `RLD_MEAS`，见 3.4 节安全掩码） |
| `"RREG"` | `6 B` | `[4]=chip_sel(0=U1,1=U2,2=BOTH)`，`[5]=addr` | **在线单寄存器硬件回读**：加载当前配置与覆盖项后从 SPI1 实读目标地址写入 `META.last_reg`，随即安全断电 |
| `"WREG"` | `7 B` | `[4]=chip_sel`，`[5]=addr`，`[6]=val` | **在线安全寄存器写核与会话覆盖**：通过硬件安全掩码后写入 SPI1 并立即回读比对，存入会话覆盖表供后续流式模式叠加生效 |
| `"CLRO"` | `4 B` | 无 | **清空全部运行时寄存器覆盖项**，恢复固件预设表（任何锁态可用） |

### 3.4 在线 `WREG` 硬件安全掩码（防误调烧板或短路）

在线调试 `ADS1298` / `ADS1292` 寄存器（如切换 PGA 增益 `1/2/3/4/6/8/12`、导联脱落激励 `LOFF`、单通道静音 `PDn=1`、RLD 反馈通道掩码 `RLD_SENSP/N`）时，固件 `c08b_validate_reg_write()` 强制拦截以下硬件禁区，违规一律拒绝上电并置 `fault = C08B_FAULT_ARG(2)`：

- **禁止只读地址写入**：`ADS1298` 的 `0x00(ID)`、`0x12(LOFF_STATP)`、`0x13(LOFF_STATN)`；`ADS1292` 的 `0x00(ID)`、`0x08(LOFF_STAT)`。
- **保护 `ADS1298 CONFIG3 (0x03)`**：强制 `(val & 0xC0) == 0xC0` 且 **`(val & 0x38) == 0`**：
  - 禁置 `VREF_4V(0x20)`（$\pm 2.5\text{ V}$ 模拟供电仅支持 `2.40 V` 基准）；
  - 禁置 `RLD_MEAS(0x10)`（v0.01 采集板 Pin 62 `RLDIN` 接 `+2.5 V`，置 1 会把电源轨灌入内部总线）；
  - 禁置 `RLDREF_INT(0x08)`（Pin 60 `RLDREF` 硬连 `AGND`，置 1 会令片内缓冲与地短路顶牛）；
  - 副片 `U2` 严禁开 `PD_RLD(0x04)` 或写非零 `RLD_SENSP/N(0x0D/0x0E)`。
- **保护通道与引脚**：`CH1SET..CH8SET(0x05..0x0C)` 严禁设 `MUX = 0x02 (RLD_MEASURE)` 或未定义 `GAIN = 111`；`GPIO(0x14)` 低 4 位强制 `0x0F`（板上 `GPIO1/2/4` 接地，设推挽输出即短路）；`PACE=0x00`、`RESP=0x20`、`WCT1/2=0x00`、`SINGLE_SHOT=0`。
- **回读闭环与防陈旧序号**：每次 `WREG` 均经完整两步 `150 ms` 基准/RLD 预热状态机写入并当场按可写位掩码回读 SPI1，不一致立即断电并报 `C08B_FAULT_READBACK(5)`、绝不污染会话覆盖表。结果附带单调命令纪元低 16 位 `seq` 通过 `META` JSON 返回（上位机核对 `last_reg.seq != prev_seq`，彻底消除同地址连续 `RREG` 时读到 SoftDevice 栈缓存旧值的竞态）：
  ```json
  {"reg_overrides":2,"last_reg":{"seq":1,"addr":5,"u1":96,"u2":16}}
  ```

---

## 4. 双核板内 SPI 链路与 USB 传输协议

### 4.1 双核 `L432 (SPI3 Master)` ↔ `nRF52840 (SPIS1 Slave)` 8 MHz 帧协议

- **`L432 → nRF` 上行帧 `c08b_link_tx_t`（固定 `280 B`，CRC16-CCITT `0x1021`）**：
  - 头字段含 `magic=0xC853`、`afe_mode`、`state_flags`、`fault`、`sample_count(0..4)`、`f01_flags`、`seq_first`、`timestamp_us(u64)`、`produced`、`dropped`、`bad_status`、`drdy_desync`、`min_interval_us_sat`、`ack_epoch_lo`、`imu_timestamp_us(u64)`、`imu_raw[6]`；
  - `samples[4][54]` 承载最多 4 个 16CH 样本槽；当 `sample_count < 4`（待机心跳或 2 kHz 双帧批）时，`samples[3][46..53]` 捎带 8 字节在线寄存器回读摘要（`seq_lo | seq_hi | 0x52 | valid | addr | val_a | val_b | ovr_count`），保持 `280 B` 固定帧长零膨胀。
- **`nRF → L432` 下行帧 `c08b_link_rx_t`（固定 `16 B`，CRC16-CCITT）**：
  `magic(0x53C8) | version(1) | req_mode | nrf_flags | synth_channels_or_chip_sel | fs_hz(u16) | cmd_epoch(u32) | reg_addr(u8) | reg_val(u8) | crc(u16)`。

### 4.2 USB 接收器与 HIL 桥接串口协议（`0xA5` 二进制帧，主机端 `host/v12_dongle.py`）

用于 `firmware/ble-dongle/xiao-central`（XIAO nRF52840 接收器）、`firmware/ble-dongle/c6-central`（ESP32-C6 接收器）以及 `firmware/c08b-stream/tools/hil_dual_mcu/xiao_c08b_hil_pio`（双核 HIL 桥）。采集手环本体**严禁插 USB 贴肤使用**；USB 协议运行在无线接收器或离体台架上：

- **设备 → 电脑（`8 B` 头 + `payload`）**：`0xA5 | kind(u8) | len(u16 LE) | t_us(u32 LE) | payload`
  - `kind = 2`：`DATA (0002)` 肌电通知原样载荷（F01 `v1` / `v4`）
  - `kind = 6`：`IMU_DATA (0006)` 6 轴 IMU 通知原样载荷（`36 B`）
  - `kind = 0x10`：ASCII 诊断日志
  - `kind = 0x11`：`26 B` 链路健康帧（`<BHBHHHIIII`：`ready, conn_itvl, phy, mtu, data_len, want_ci, ring_drops, notifies, ring_peak_or_spis_frames, connects`）
  - `kind = 0x80 | op`：电脑命令应答（`payload[0] == 0` 表示成功，后跟返回数据）
- **电脑 → 设备（`4 B` 头 + `payload`）**：`0xA5 | op(u8) | len(u16 LE) | payload`
  - `'W'`（`0x57`）：写 GATT `CONTROL (0005)`（支持全部模式启停、`RREG`、`WREG`、`CLRO`）
  - `'R'`（`0x52`）：长读 GATT 特征（`payload = [3]` 读 `META`，`[4]` 读 `64 B STATUS`）
  - `'I'`（`0x49`，无线接收器）：设定 BLE 连接间隔（`u16 LE`，单位 `1.25 ms`，默认 `6 = 7.5 ms`）
  - `'Q'`（`0x51`）：立即刷新并回传 `0x11` 链路健康帧
  - `'D'`（`0x44`）：主动断开当前 BLE 连接并重新扫描（保证每次采集从全新连接 `seq=0` 起步）
  - `'L'` / `'S'` / `'I'`（仅 `xiao_c08b_hil_pio` 双核 HIL 桥）：`'L'` 免焊接 USB 注入 `280 B` `c08b_link_tx_t` 并取回 `16 B` `c08b_link_rx_t`；`'S'` 返回 `17 B` 硬件 SPIS1/虚拟帧/CRC 诊断计数（`0x00 + 4×u32 LE`）；`'I'` 返回 `21 B` 板载 `LSM6DS3TR-C` 实时状态与最新 6 轴读数。

*附注：单板原型与商用对比适配器 USB 协议见 `host/usb_emg_imu.py`（`0xAA 0x55` 46B 帧）与 `host/wl_band.py`（`0xAA` 串口协议）。*

---

## 5. 全链路四段阻塞与丢包精确定位表

针对双芯片 + 无线接收器链路“不知道卡在哪一段”的问题，`64 B STATUS`（偏移 `0..63`）与接收器 `0x11` 链路帧将每一级队列拆成独立单调计数器，一次读取即可定位阻塞点：

| 链路阶段 | 物理边界 | 观测计数器与字段 | 异常判据与含义 |
|---|---|---|---|
| **第 1 段：模拟前端** | `ADS1298/1292` → `L432 SPI1` | `STATUS.drdy_raw_edges`、`drdy_min_interval_us`、`ads_status`、`fault=4/5/6/8` | `fault=8(DRDY_TO)` 说明晶振/START 未起振；`fault=6(BAD_FRAME)` 或 `ads_status` 高 4 位非 `0xC` 说明 `OE_N=1` 互锁断电、SPI1 时序异常或 `drdy_desync>0` 副片失步 |
| **第 2 段：双核板内** | `L432 SPI3` → `nRF SPIS1` | `STATUS.produced` vs `STATUS.ring_dropped`（即 `L432 dropped`） | `produced` 增长但 `ring_dropped > 0` 说明 `nRF` 未及时拉高 `LINK_RDY`（SPIS1 被关中断或阻塞） |
| **第 3 段：BLE 空口** | `nRF S140 HVX` → 接收器/主机 | `STATUS.sent_samples`、`STATUS.notify_failures`、`fault=7` | `ring_dropped == 0` 但 `notify_failures > 0` 说明 BLE 连接间隔过宽、MTU 未达 247 或 2.4 GHz 射频拥塞 |
| **第 4 段：USB 串口** | 接收器 `32 KB Ring` → 电脑 | `dongle.json` 中 `link.ring_drops`、`link.connects`、F01 `seq` 缺口 | `notify_failures == 0` 但 `link.ring_drops > 0` 说明电脑端 USB 读取线程卡顿；`connects` 增加说明中途闪断重连（整段作废不拼接） |

### 命令行快速调用示例

```bash
# 1. 经 USB 接收器在线把 U1/U2 的 CH1/CH9 增益改为 12 (0x60) 并核验硬件回读（仅离体台架解锁后）
host/.venv-emg/bin/python host/c08b_stream.py --port /dev/cu.usbmodemXXXX \
  --wreg both:CH1SET=0x60 --allow-real --expected <16位build_id>

# 2. 在线回读 CONFIG3 (0x03) 实测寄存器值
host/.venv-emg/bin/python host/c08b_stream.py --port /dev/cu.usbmodemXXXX \
  --rreg both:CONFIG3 --allow-real --expected <16位build_id>

# 3. 清空全部会话寄存器覆盖项，恢复预设表
host/.venv-emg/bin/python host/c08b_stream.py --port /dev/cu.usbmodemXXXX --clear-reg-overrides
```

# ADS1292-2ch + P44e + XIAO nRF52840 Sense BLE F01 流式候选固件

状态：**已实现未验收**（跨板引脚 20/20 自动对账、6 项静态必败反例、48 项 C++17 驱动与 F01 协议正反例、`ads1292_2k` / `ads1292_4k` 双档 ARM 镜像编译均通过；未打样、未刷机、未做台架与人体实测）。默认硬件锁保持关闭（`MAKO_V12_AFE_ENABLED=0`、`MAKO_BENCH_MEASURED=0`）。

## A 硬件链路与引脚契约

适配 **`ADS1292-2ch` 六触点载板** + **`P44e` 0.8 mm XIAO 专用转接板** + **20P 反向软排线（`J1.k ↔ J2.(21-k)`）** + **Seeed XIAO nRF52840 Sense**：

| XIAO 引脚 | P44e `J1` | 载板 `J2` | 载板网络 | 固件配置与防漏电说明 |
|---|---|---|---|---|
| `D0, D1, D2` | — | `J2.4, J2.7` 空 | `NC` | `P44e` 保留 `D0/D2` 10 kΩ 上拉到常开 `3V3`，固件保持 **`INPUT`**（设 `LOW` 会白耗 `0.66 mA`） |
| `D3` | `J1.12` | `J2.9` | `ADS_START` | `P44e` 10 kΩ 下拉；固件恒置 `OUTPUT LOW`，统一用 SPI `START(0x08)` 命令启动 |
| `D4` | `J1.15` | `J2.6` | `MCU_PWDN` | `P44e` 10 kΩ 下拉；停机置 `LOW` 零漏电，上电拉高 `>= 1 s` 后发 `20 µs` 低脉冲复位 |
| `D5` | `J1.18` | `J2.3` | `AVDD_SENSE` | `AVDD 3.0 V` 经 `R26 100 kΩ` 回读（SAADC 3.6 V 量程窗 `2.75–3.25 V`，设 `analogSampleTime(20)` 支持 `<= 400 kΩ` 源阻抗）；**严禁初始化 `Wire`（`D5` 复用 SCL）** |
| `D6` | `J1.4` | `J2.17` | `ADS_DRDY_N` | `INPUT` 下降沿中断（`TIMER2` 1 MHz 捕获时间戳） |
| `D7` | `J1.11` | `J2.10` | `ADS_CS_N` | `P44e` 10 kΩ 上拉到常开 `3V3`；停机保持 **`OUTPUT HIGH`**（置 `LOW` 会耗 `0.33 mA` 并常选芯片） |
| `D8 / D9 / D10` | `J1.10 / 6 / 16` | `J2.11 / 15 / 5` | `SCLK / DOUT / DIN` | `SPI_MODE1`，固定 **`1 MHz`**（满足 TI SBAS502C §7.6 内部 512 kHz 下 `f_SCLK <= 1.024 MHz`） |
| `5V` | `J1.19` | `J2.2` | `XIAO_5V` | 板上 `R32 + Q1(AO3400A)` 硬拉低 `ADS_RESET_N`；固件同步读 `NRF_POWER->USBREGSTATUS` 构成第二道互锁 |

## B 寄存器与安全门要点（TI SBAS502C）

- **上电与复位**：`D4` 拉高等待 `MAKO_BENCH_POR_US`（`>= 1,000,000 µs` 让 `VCAP1` 1 µF 建立）→ `20 µs` 低脉冲复位（`>= 7.81 µs` 且远小于 `4,000 µs` 硬掉电线）→ 等 `40 µs`（`>= 18 t_CLK`）→ `SDATAC(0x11)`。
- **ID 核验**：`(id & 0xDF) == 0x53`（放行 `0x53` ADS1292 与 `0x73` ADS1292R；拒绝 `0x51` 1 通道与 `0x92` 8 通道）。
- **必写固定位**：`CONFIG2 = 0xA0`（`TST1` 模式 `0xA3` 开 1 Hz 方波；写 `0xA2` 是直流）、`LOFF = 0x10`、`RESP1 = 0x02`（手册第 60 页硬要求）、`RESP2 = 0x07`（手册表 24 非 R 版 ADS1292 `bit2` 必写 `1`，`RLDREF_INT=1`，`bit0=1`）、`GPIO = 0x0C`（全输入）。
- **两步开 RLD**：`EXR1` / `RLD1` 模式下第 1 步先写 `RLD_SENS = 0x20` 开启 `PDB_RLD` 预热运放（断开电极反馈开关）并等待 `MAKO_BENCH_REFERENCE_US`（`>= 150,000 µs` 让 `C7 10 µF + C6 100 nF` 内部 `2.42 V` 基准稳定），第 2 步再写 `RLD_SENS = 0x23`（首测只把 CH1 送入 RLD 平均，相位裕度 `65–89°`；`RLD1` 另将 `CH2SET` 切为 `0x02 RLD_MEASURE` 经 29 脚直看 RLD 波形）。
- **协议兼容**：9 字节原始帧解包为 `CH1, CH2`（`CH3–CH8 = 0`）压入 V12 统一 27 字节 `F01` BLE 流；每帧前 3 字节经 `Ads1292::map_f01_status` 映射为统一 `F01` 状态位序（`LOFF_STATP[1:0]=IN2P,IN1P`、`LOFF_STATN[1:0]=IN2N,IN1N`、`GPIO[1:0]`，对齐 `host/ads1298_regs.py:decode_ads_status`），而 `status_chr` 的 `ads_status` 保留芯片原生 24 位状态字（含 `bit19 RLD_STAT`）；`meta_chr` 标明 `"active_channels":2,"vref_mV":2420,"gain":6`。

## C 验证命令

```bash
bash check.sh          # 引脚跨板对账(含6反例) + C++17驱动单测(48项) + 流边界单测
bash check.sh --pio    # 追加运行 PlatformIO 编译 ads1292_2k / ads1292_4k 固件镜像
```

# C08B 共用双核主控（`MCU-U9` / `R4U6` / `R4U6N`）2/8/16ch 实时流式采集候选固件

状态：**已实现未验收**（`MCU-U9` 与 `R4U6/R4U6N` 引脚逐脚对账、源码安全红线 10/10 反例、C11 协议单测与双核 ARM 零告警链接全绿；未刷机、未做台架供电纹波与互锁实测、未做人体测试）。默认双硬件锁保持关闭（`MAKO_C08B_AFE_ENABLED=0`、`MAKO_BENCH_MEASURED=0`），BLE 广播名固定为 `"YUANLI-C08B"`。

## A 双核分工与三档下层板自动识别

共用主控 **`MCU-U9`（`Rev0.01` 6 层圆角旗舰）/ `C08B-main-R4U6`（圆孔）/ `C08B-main-R4U6N`（四角缺口）** 通过 20P `0.5 mm` 反序排线零跳线自动适配三档采集底板（冷启动未上电探测前 GATT `META` 如实报 `"afe":"NONE","protocol":1,"active_channels":0`，绝不伪装为 16ch）：

| 下层采集底板 | `ID_A / ID_B` | SPI1 速率 | 特殊引脚与寄存器保护 | BLE 数据协议 |
|---|---|---|---|---|
| **16ch `AFE-30P / D20 / D20N`** | `0x92 / 0x92` | `4.000 MHz` | `LM27762` `±2.5V` 双极供电锁定内部 `2.40 V` 基准（`VREF_4V=0`）；`Pin 60(RLDREF)` 与 `Pin 62(RLDIN)` 硬连 `AGND` 故严禁置 `RLDREF_INT=1`（两步 `0xC0` → `EXR1:0xC4` / `RLD1:0xD4`）；逐帧核对 `DRDY_A/B` 同步 | `F01 v4`（`16B + 4×54B = 232B` 无损双片） |
| **8ch `D20-8CH / D20N-8CH`** | `0x92 / 0x00\|0xFF` | `4.000 MHz` | `PA4(DRDY_B)` 开内部上拉防浮空；`GPIO1..4` 全设输入（`0x0F`）；同用两步 `RLDREF_INT=0` 规则 | `F01 v1`（`16B + 8×27B = 232B`） |
| **2ch `ADS1292-2ch-R9`** | `0x53\|0x73 / 0x00\|0xFF` | `1.000 MHz` | 保持 `ADS_PWDN=1` 等满 `>=1050 ms` 建立 `VCAP1=1µF`；先打 `PA8(ADS_RESET)` 测是否 `0x92(ADS1298)`，确认 `id_a != 0x92` 后再对 `PA1(ADS_PWDN -> J2.6 -> R31 -> Pin15 PWDN/RESET)` 发 `20 µs`（`<< 4000 µs` 掉电阈值）纯数字复位脉冲并重读 ID（既补齐 `2ch J2.7=NC` 缺失的复位脉冲，又绝不放掉 `ADS1298` 22µF `VCAP1`）；`PA4` 先 `10 µs` 下拉放净残荷再保持 `P_NONE` 监测 `3.0V AVDD_SENSE`；`RESP2=0x07`；两步开 RLD（`0x20` 等满 `>=150 ms` 再写 `0x23`） | `F01 v1`（`CH1..2` + `CH3..8=0`，状态头映射对齐 `decode_ads_status`） |

## B 硬件红线与互锁链路（`tools/pins.py --check-safety` 强扫 10 条）

1. **双默认硬件锁**：`common/bench_release.h` 默认 `MAKO_C08B_AFE_ENABLED=0` 且 `MAKO_BENCH_MEASURED=0`。未解锁前仅响应免开 AFE 供电的 `SYN1` 双核合成流测试（包头强制置 `SYNTHETIC=1`），所有真实采集命令（含只读子板探测 `PRB1`）返回 `C08B_FAULT_LOCKED(1)`。
2. **禁止外部低频晶振（`XL1/XL2` 复用红线）**：板上 `U13`（`MCU-U9` 为 `U8`）的 `P0.00/XL1 = MCU_BENCH_EN`、`P0.01/XL2 = VBUS_SENSE`，无外部 `32.768 kHz` 晶振。`nrf/main.c` 强制 SoftDevice S140 使用 `NRF_CLOCK_LF_SRC_RC`（`rc_ctiv=16, rc_temp_ctiv=2`）。
3. **双核 USB VBUS / `OE_N` 同步握手与急停**：`L432` 拉高 `ANA_EN` 后先与 `nRF SPIS1` 执行两步握手排空陈旧缓冲并核对 `OE_N==0 & VBUS==0`；运行态任一侧见 `VBUS` 或 `OE_N` 断开或 2ch `AVDD` 掉电，立刻关断 `ADS_START / ADS_PWDN / ANA_EN` 并报 `C08B_FAULT_INTERLOCK(3)`（与 BLE 断连 `C08B_FAULT_CANCELLED(9)` 严格区分）。

## C 构建档位与验证命令

```bash
bash check.sh
```

| 产物（本机安装 CMSIS + S140 包时生成） | Flash 起始地址 | 用途 |
|---|---|---|
| `build/l432.hex` | `0x08000000` | `STM32L432KCU6`（`MCU-U9` 上为 `U7`，`R4U6` 上为 `U18`）实时采集与 `SPI3` 主机推送（`R4U6` 插 USB 冷开机直进 ROM DFU；`MCU-U9` 走 `SWDIO/SWCLK` 或拉高 `L_BOOT0` 进 DFU） |
| `build/nrf_s140.hex` | `0x00027000` | `nRF52840-QFAA`（`MCU-U9` 上为 `U8`，`R4U6` 上为 `U13`）正式 BLE GATT 流式固件（配合官方 `s140_nrf52_7.3.0_softdevice.hex` 经 SWD 烧录） |
| `build/nrf_nosd.hex` | `0x00000000` | 免 SoftDevice 裸机双核 `SPI3↔SPIS1` 流式联调固件（首板直烧验证） |

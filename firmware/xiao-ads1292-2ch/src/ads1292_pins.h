#pragma once
// ADS1292-2ch 载板 J2 <--(20P 反向排线 J2.n = J1.(21-n))--> P44e J1 <--> XIAO nRF52840 Sense 引脚契约。
// 由 check_pins.py 与 ads1292-2ch/design.json 及 adapter-p44e-xiao/pin-table.csv 自动跨板逐脚对账。
namespace v12_p44e {
// D0、D2 在 P44e 上留有 10 kΩ 上拉到常开 3V3（J1.14/J1.17 已断开），D1 悬空：必须保持高阻 INPUT，驱动 LOW 会白耗 0.66 mA。
static constexpr unsigned PIN_UNUSED_D0 = 0u;
static constexpr unsigned PIN_UNUSED_D1 = 1u;
static constexpr unsigned PIN_UNUSED_D2 = 2u;

// J1.12 (D3) <-> J2.9 (ADS_START)：P44e 有 10 kΩ 下拉；全程保持 OUTPUT LOW，转换由 SPI START(0x08) 命令触发。
static constexpr unsigned PIN_ADS_START = 3u;
static constexpr unsigned J1_PIN_START  = 12u;
static constexpr unsigned J2_PIN_START  = 9u;

// J1.15 (D4) <-> J2.6 (MCU_PWDN -> R31 4.7k -> ADS_RESET_N)：P44e 有 10 kΩ 下拉；空闲 LOW 零漏电，工作 HIGH。
static constexpr unsigned PIN_ADS_PWDN  = 4u;
static constexpr unsigned J1_PIN_PWDN   = 15u;
static constexpr unsigned J2_PIN_PWDN   = 6u;

// J1.18 (D5) <-> J2.3 (AVDD_SENSE <- R26 100k <- AVDD 3.0V)：SAADC 输入，严禁初始化 Wire(I2C SCL 复用 D5)。
static constexpr unsigned PIN_AVDD_ADC  = 5u;
static constexpr unsigned J1_PIN_AVDD   = 18u;
static constexpr unsigned J2_PIN_AVDD   = 3u;

// J1.4 (D6) <-> J2.17 (ADS_DRDY_N)：下降沿中断。
static constexpr unsigned PIN_ADS_DRDY  = 6u;
static constexpr unsigned J1_PIN_DRDY   = 4u;
static constexpr unsigned J2_PIN_DRDY   = 17u;

// J1.11 (D7) <-> J2.10 (ADS_CS_N)：P44e 有 10 kΩ 上拉到常开 3V3；空闲与停机必须置 HIGH，置 LOW 会耗 0.33 mA 并常选芯片。
static constexpr unsigned PIN_ADS_CS    = 7u;
static constexpr unsigned J1_PIN_CS     = 11u;
static constexpr unsigned J2_PIN_CS     = 10u;

// SPI1 模式 1（CPOL=0, CPHA=1），1 MHz：J1.10(D8)->J2.11(MCU_SCLK)，J1.6(D9)<-J2.15(ADS_DOUT)，J1.16(D10)->J2.5(ADS_DIN)。
static constexpr unsigned XIAO_PIN_SCLK = 8u;
static constexpr unsigned J1_PIN_SCLK   = 10u;
static constexpr unsigned J2_PIN_SCLK   = 11u;

static constexpr unsigned XIAO_PIN_MISO = 9u;
static constexpr unsigned J1_PIN_MISO   = 6u;
static constexpr unsigned J2_PIN_MISO   = 15u;

static constexpr unsigned XIAO_PIN_MOSI = 10u;
static constexpr unsigned J1_PIN_MOSI   = 16u;
static constexpr unsigned J2_PIN_MOSI   = 5u;

// J1.19 (XIAO 5V) <-> J2.2 (XIAO_5V -> R32 0R -> Q1 AO3400A 硬拉低 ADS_RESET_N)；固件同步读 NRF_POWER->USBREGSTATUS 作第二道互锁。
static constexpr unsigned J1_PIN_VBUS   = 19u;
static constexpr unsigned J2_PIN_VBUS   = 2u;
}  // namespace v12_p44e

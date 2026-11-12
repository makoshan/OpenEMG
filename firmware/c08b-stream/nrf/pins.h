/* 由 tools/pins.py 从 C08B-main-R4U6.epcb2 核对生成，请勿手改。 */
#pragma once
#define BENCH_EN_PIN 0u  /* P0.00 = MCU_BENCH_EN：台架解互锁（复用 XL1！严禁开外部低频晶振，保持输出低） */
#define VBUS_SENSE_PIN 1u  /* P0.01 = VBUS_SENSE：VBUS 68k/100k 分压（复用 XL2！只读数字输入） */
#define VBAT_SENSE_PIN 4u  /* P0.04 = VBAT_SENSE：VBAT/2，SAADC AIN2 */
#define PWR_HOLD_PIN 5u  /* P0.05 = PWR_HOLD：高 = 保持供电 */
#define LINK_RDY_PIN 7u  /* P0.07 = LINK_RDY：拉高 = SPIS 已准备好 */
#define LINK_MOSI_PIN 8u  /* P0.08 = LINK_MOSI：SPIS MOSI */
#define LINK_MISO_PIN 40u  /* P1.08 = LINK_MISO：SPIS MISO */
#define LINK_SCK_PIN 41u  /* P1.09 = LINK_SCK：SPIS SCK */
#define LINK_CS_PIN 11u  /* P0.11 = LINK_CS：SPIS CSN */
#define CHRG_N_PIN 12u  /* P0.12 = CHRG_N：充电中为低（TP4054 开漏） */
#define BUTTON_N_PIN 14u  /* P0.14 = BUTTON_N：按下为低，外部上拉 R38 */
#define OE_N_PIN 17u  /* P0.17 = OE_N：低 = AFE 缓冲打开（互锁线，严禁推挽输出！） */
#define MCU_RST_N_PIN 18u  /* P0.18 = MCU_RST_N：nRF 复位脚 */
#define LED_PIN 23u  /* P0.23 = MCU_LED：D401 阴极，低 = 亮 */
#define UART_TX_PIN 24u  /* P0.24 = MCU_TX：UARTE0 TX，115200，引到 J301.5 */

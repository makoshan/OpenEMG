/* Seeed XIAO nRF52840 Sense 联调引脚映射（避开板载 QSPI / IMU / PDM / 32.768kHz 晶振） */
#pragma once
#define BENCH_EN_PIN   30u /* P0.30 = LED_GREEN（安全占位输出低，绝不碰 XL1） */
#define VBUS_SENSE_PIN  3u /* P0.03 = D1（外部互锁模拟输入，默认内部下拉=0） */
#define VBAT_SENSE_PIN  4u /* P0.04 = D4 / AIN2 */
#define PWR_HOLD_PIN    5u /* P0.05 = D5（供电保持模拟输出高） */
#define LINK_RDY_PIN   43u /* P1.11 = D6  <-> L432 PB6 */
#define LINK_CS_PIN    44u /* P1.12 = D7  <-> L432 PA15 (SPI3_CS) */
#define LINK_SCK_PIN   45u /* P1.13 = D8  <-> L432 PB3  (SPI3_SCK) */
#define LINK_MISO_PIN  46u /* P1.14 = D9  <-> L432 PB4  (SPI3_MISO) */
#define LINK_MOSI_PIN  47u /* P1.15 = D10 <-> L432 PB5  (SPI3_MOSI) */
#define CHRG_N_PIN     17u /* P0.17 = 板载 BQ25100 ~CHG */
#define BUTTON_N_PIN   29u /* P0.29 = D3（默认内部上拉=1） */
#define OE_N_PIN       28u /* P0.28 = D2（默认内部下拉=0 模拟缓冲使能；拉高模拟 OE_OFF） */
#define MCU_RST_N_PIN  18u /* P0.18 = RESET */
#define LED_PIN        26u /* P0.26 = 板载红灯 LED_RED（低电平点亮） */
#define UART_TX_PIN     2u /* P0.02 = D0（115200 调试串口 TX） */

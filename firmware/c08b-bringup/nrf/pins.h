/* 由 tools/pins.py 生成，别手改。核对源：C08B-main-R4U6.epcb2 */
#pragma once
#define BENCH_EN_PIN (0 * 32 + 0)  /* P0.00 脚2 MCU_BENCH_EN：台架解互锁，本固件保持低 */
#define VBUS_SENSE_PIN (0 * 32 + 1)  /* P0.01 脚3 VBUS_SENSE：VBUS 68k/100k 分压（0.595×VBUS），数字读 */
#define VBAT_SENSE_PIN (0 * 32 + 4)  /* P0.04 脚4 VBAT_SENSE：VBAT/2，SAADC AIN2 */
#define PWR_HOLD_PIN (0 * 32 + 5)  /* P0.05 脚5 PWR_HOLD：高 = 保持供电 */
#define LINK_RDY_PIN (0 * 32 + 7)  /* P0.07 脚6 LINK_RDY：拉高 = SPIS 已准备好 */
#define LINK_MOSI_PIN (0 * 32 + 8)  /* P0.08 脚7 LINK_MOSI：SPIS MOSI */
#define LINK_MISO_PIN (1 * 32 + 8)  /* P1.08 脚8 LINK_MISO：SPIS MISO */
#define LINK_SCK_PIN (1 * 32 + 9)  /* P1.09 脚9 LINK_SCK：SPIS SCK */
#define LINK_CS_PIN (0 * 32 + 11)  /* P0.11 脚10 LINK_CS：SPIS CSN */
#define CHRG_N_PIN (0 * 32 + 12)  /* P0.12 脚11 CHRG_N：充电中为低（TP4054 开漏） */
#define BUTTON_N_PIN (0 * 32 + 14)  /* P0.14 脚14 BUTTON_N：按下为低，外部上拉 R38 */
#define OE_N_PIN (0 * 32 + 17)  /* P0.17 脚15 OE_N：低 = AFE 缓冲打开（互锁状态） */
#define MCU_RST_N_PIN (0 * 32 + 18)  /* P0.18 脚16 MCU_RST_N：nRF 自己的复位脚（UICR PSELRESET=18） */
#define LED_PIN (0 * 32 + 23)  /* P0.23 脚22 MCU_LED：D401 阴极，低 = 亮 */
#define UART_TX_PIN (0 * 32 + 24)  /* P0.24 脚23 MCU_TX：UARTE0 TX，115200，引到 J301.5 */

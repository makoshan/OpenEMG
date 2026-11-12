/* 由 tools/pins.py 从 C08B-main-R4U6.epcb2 核对生成，请勿手改。 */
#pragma once
#define ANA_EN_PORT GPIOC
#define ANA_EN_PIN  14  /* PC14 = ANA_EN：高 = 打开 AFE 缓冲（U10 反相出 OE_N） */
#define AFE_GPIO3_PORT GPIOA
#define AFE_GPIO3_PIN  0  /* PA0 = AFE_GPIO3：ADS GPIO3，只读 */
#define ADS_PWDN_PORT GPIOA
#define ADS_PWDN_PIN  1  /* PA1 = XIAO_PWDN：高 = ADS 工作（2CH 下兼作 ADS1292 PWDN/RESET） */
#define DRDY_A_PORT GPIOA
#define DRDY_A_PIN  2  /* PA2 = XIAO_DRDY：U1 DRDY，低有效 */
#define ADS_START_PORT GPIOA
#define ADS_START_PIN  3  /* PA3 = AFE_START：同步启动转换 */
#define DRDY_B_PORT GPIOA
#define DRDY_B_PIN  4  /* PA4 = AFE_DRDY_B：16CH 为 U2 DRDY；2CH 为 AVDD_SENSE（3.0V 监测） */
#define SPI1_SCK_PORT GPIOA
#define SPI1_SCK_PIN  5  /* PA5 = XIAO_SCLK：SPI1 AF5 */
#define SPI1_MISO_PORT GPIOA
#define SPI1_MISO_PIN  6  /* PA6 = XIAO_MISO：SPI1 AF5 */
#define SPI1_MOSI_PORT GPIOA
#define SPI1_MOSI_PIN  7  /* PA7 = XIAO_MOSI：SPI1 AF5 */
#define CS_A_PORT GPIOB
#define CS_A_PIN  0  /* PB0 = XIAO_CS：U1 片选，低有效 */
#define CS_B_PORT GPIOB
#define CS_B_PIN  1  /* PB1 = MCU_CS_B：U2 片选，低有效 */
#define ADS_RESET_PORT GPIOA
#define ADS_RESET_PIN  8  /* PA8 = XIAO_RESET：低脉冲复位（ADS1298） */
#define IMU_SCL_PORT GPIOA
#define IMU_SCL_PIN  9  /* PA9 = IMU_SCL：I2C1 AF4，外部上拉 R198 */
#define IMU_SDA_PORT GPIOA
#define IMU_SDA_PIN  10  /* PA10 = IMU_SDA：I2C1 AF4，外部上拉 R199 */
#define USB_DM_PORT GPIOA
#define USB_DM_PIN  11  /* PA11 = MCU_DM：本固件不用 */
#define USB_DP_PORT GPIOA
#define USB_DP_PIN  12  /* PA12 = MCU_DP：本固件不用 */
#define LINK_CS_PORT GPIOA
#define LINK_CS_PIN  15  /* PA15 = LINK_CS：SPI3 片选（GPIO 控制） */
#define LINK_SCK_PORT GPIOB
#define LINK_SCK_PIN  3  /* PB3 = LINK_SCK：SPI3 AF6 */
#define LINK_MISO_PORT GPIOB
#define LINK_MISO_PIN  4  /* PB4 = LINK_MISO：SPI3 AF6 */
#define LINK_MOSI_PORT GPIOB
#define LINK_MOSI_PIN  5  /* PB5 = LINK_MOSI：SPI3 AF6 */
#define LINK_RDY_PORT GPIOB
#define LINK_RDY_PIN  6  /* PB6 = LINK_RDY：nRF 拉高 = SPIS 接收缓冲已就绪 */
#define IMU_INT1_PORT GPIOB
#define IMU_INT1_PIN  7  /* PB7 = IMU_INT1：本固件只读 */
#define BOOT0_PORT GPIOH
#define BOOT0_PIN  3  /* PH3 = VBUS_SENSE：R4U6 起并入 VBUS 分压（68k/100k）：运行态只读不驱动 */

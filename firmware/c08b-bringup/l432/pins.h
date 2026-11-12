/* 由 tools/pins.py 生成，别手改。核对源：r4u6-readback.json */
#pragma once
#define ANA_EN_PORT GPIOC
#define ANA_EN_PIN 14  /* PC14 脚2 ANA_EN：高 = 打开 AFE 缓冲（U10 反相出 OE_N） */
#define AFE_GPIO3_PORT GPIOA
#define AFE_GPIO3_PIN 0  /* PA0 脚6 AFE_GPIO3：ADS GPIO3，只读 */
#define ADS_PWDN_PORT GPIOA
#define ADS_PWDN_PIN 1  /* PA1 脚7 XIAO_PWDN：高 = ADS 工作 */
#define DRDY_A_PORT GPIOA
#define DRDY_A_PIN 2  /* PA2 脚8 XIAO_DRDY：U1 DRDY，低有效 */
#define ADS_START_PORT GPIOA
#define ADS_START_PIN 3  /* PA3 脚9 AFE_START：两片同沿启动 */
#define DRDY_B_PORT GPIOA
#define DRDY_B_PIN 4  /* PA4 脚10 AFE_DRDY_B：U2 DRDY，低有效 */
#define SPI1_SCK_PORT GPIOA
#define SPI1_SCK_PIN 5  /* PA5 脚11 XIAO_SCLK：SPI1 AF5 */
#define SPI1_MISO_PORT GPIOA
#define SPI1_MISO_PIN 6  /* PA6 脚12 XIAO_MISO：SPI1 AF5 */
#define SPI1_MOSI_PORT GPIOA
#define SPI1_MOSI_PIN 7  /* PA7 脚13 XIAO_MOSI：SPI1 AF5 */
#define CS_A_PORT GPIOB
#define CS_A_PIN 0  /* PB0 脚14 XIAO_CS：U1 片选，低有效 */
#define CS_B_PORT GPIOB
#define CS_B_PIN 1  /* PB1 脚15 MCU_CS_B：U2 片选，低有效 */
#define ADS_RESET_PORT GPIOA
#define ADS_RESET_PIN 8  /* PA8 脚18 XIAO_RESET：低脉冲复位 */
#define IMU_SCL_PORT GPIOA
#define IMU_SCL_PIN 9  /* PA9 脚19 IMU_SCL：I2C1 AF4，外部上拉 R198 */
#define IMU_SDA_PORT GPIOA
#define IMU_SDA_PIN 10  /* PA10 脚20 IMU_SDA：I2C1 AF4，外部上拉 R199 */
#define USB_DM_PORT GPIOA
#define USB_DM_PIN 11  /* PA11 脚21 MCU_DM：本固件不用 */
#define USB_DP_PORT GPIOA
#define USB_DP_PIN 12  /* PA12 脚22 MCU_DP：本固件不用 */
#define LINK_CS_PORT GPIOA
#define LINK_CS_PIN 15  /* PA15 脚25 LINK_CS：SPI3 片选（GPIO 控制） */
#define LINK_SCK_PORT GPIOB
#define LINK_SCK_PIN 3  /* PB3 脚26 LINK_SCK：SPI3 AF6 */
#define LINK_MISO_PORT GPIOB
#define LINK_MISO_PIN 4  /* PB4 脚27 LINK_MISO：SPI3 AF6 */
#define LINK_MOSI_PORT GPIOB
#define LINK_MOSI_PIN 5  /* PB5 脚28 LINK_MOSI：SPI3 AF6 */
#define LINK_RDY_PORT GPIOB
#define LINK_RDY_PIN 6  /* PB6 脚29 LINK_RDY：nRF 拉高 = 可以发 */
#define IMU_INT1_PORT GPIOB
#define IMU_INT1_PIN 7  /* PB7 脚30 IMU_INT1：本固件只读 */
#define BOOT0_PORT GPIOH
#define BOOT0_PIN 3  /* PH3 脚31 VBUS_SENSE：R4U6 接 VBUS 分压，插 USB 上电直进 DFU */

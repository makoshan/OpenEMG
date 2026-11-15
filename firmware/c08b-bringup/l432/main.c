/* C08B 共用主控 STM32L432KCU6 上电自检（裸机，只用 CMSIS 头）。
   自动识别三档下层采集板：
   - 16CH：双片 ADS1298/R（D20 / D20N）
   - 8CH ：单面单片 ADS1298/R（D20-8CH / D20N-8CH，B 片未贴）
   - 2CH ：双通道六触点 ADS1292/R（ADS1292-2ch-R9，B 片未贴，PA4 兼读 AVDD_SENSE）
   做什么：开 AFE 缓冲 → 脉冲复位 ADS_PWDN/ADS_RESET → 读 A/B 片 ID 判别板型 → 写寄存器并逐个回读
          → 内部方波测有效通道幅度与采样率 → 输入短接测底噪 → I2C 读 IMU → 结果打包经 SPI3 发给 nRF52840。
   结果也放在 RAM 变量 g_report 和 RTT 日志里，接 SWD（J302 + J301 的 3V3/GND）可以直接读。
   不碰 USB，不写 flash 选项字节，不驱动 PH3-BOOT0。时钟用 HSI16（16 MHz），不依赖外部晶振。 */
#define RTT_IMPL
#include "stm32l432xx.h"
#include "pins.h"
#include "../common/report.h"
#include "../common/rtt.h"

void log_sink(const char *s, unsigned n) { (void)s; (void)n; }   /* L432 没有串口脚，日志只走 RTT */

volatile c08b_report_t g_report;    /* 调试器读这个 */
static volatile uint32_t g_ms;
void SysTick_Handler(void) { g_ms++; }

static void delay_us(uint32_t us)
{
    uint32_t t0 = DWT->CYCCNT, n = us * (SystemCoreClock / 1000000u);
    while ((DWT->CYCCNT - t0) < n) {}
}
static void delay_ms(uint32_t ms) { uint32_t t = g_ms; while (g_ms - t < ms) {} }

/* ---------- GPIO ---------- */
enum { M_IN = 0, M_OUT = 1, M_AF = 2 };
enum { P_NONE = 0, P_UP = 1, P_DOWN = 2 };
static void pin_mode(GPIO_TypeDef *p, int pin, int mode, int af, int pull, int od)
{
    p->PUPDR = (p->PUPDR & ~(3u << pin * 2)) | ((uint32_t)pull << pin * 2);
    p->OTYPER = (p->OTYPER & ~(1u << pin)) | ((uint32_t)od << pin);
    /* 复用口（SPI/I2C）用高速；普通输出用低速：PC13–15 经电源开关供电，手册限 2 MHz（DS11451 引脚表脚注） */
    p->OSPEEDR = (p->OSPEEDR & ~(3u << pin * 2)) | ((mode == M_AF ? 2u : 0u) << pin * 2);
    if (mode == M_AF) {
        volatile uint32_t *afr = &p->AFR[pin >> 3];
        int s = (pin & 7) * 4;
        *afr = (*afr & ~(0xFu << s)) | ((uint32_t)af << s);
    }
    p->MODER = (p->MODER & ~(3u << pin * 2)) | ((uint32_t)mode << pin * 2);
}
static inline void pin_set(GPIO_TypeDef *p, int pin, int v) { p->BSRR = v ? (1u << pin) : (1u << (pin + 16)); }
static inline int pin_get(GPIO_TypeDef *p, int pin) { return (int)((p->IDR >> pin) & 1u); }
#define OUT_INIT(name, lv) do { pin_set(name##_PORT, name##_PIN, lv); pin_mode(name##_PORT, name##_PIN, M_OUT, 0, P_NONE, 0); } while (0)
#define SET(name, lv) pin_set(name##_PORT, name##_PIN, lv)
#define GET(name) pin_get(name##_PORT, name##_PIN)

/* ---------- SPI ---------- */
static void spi_init(SPI_TypeDef *s, uint32_t br, int cpha)
{
    s->CR1 = 0;
    s->CR1 = SPI_CR1_MSTR | SPI_CR1_SSM | SPI_CR1_SSI | (br << SPI_CR1_BR_Pos) | (cpha ? SPI_CR1_CPHA : 0);
    s->CR2 = (7u << SPI_CR2_DS_Pos) | SPI_CR2_FRXTH;   /* 8 位，RXNE 按 8 位触发 */
    s->CR1 |= SPI_CR1_SPE;
}
static uint8_t spi_xfer(SPI_TypeDef *s, uint8_t b)
{
    while (!(s->SR & SPI_SR_TXE)) {}
    *(volatile uint8_t *)&s->DR = b;          /* 必须 8 位访问，否则 FIFO 按 16 位打包 */
    while (!(s->SR & SPI_SR_RXNE)) {}
    return *(volatile uint8_t *)&s->DR;
}

/* ---------- ADS1298 / ADS1292 通用命令 ---------- */
#define ADS_SDATAC 0x11
#define ADS_RDATAC 0x10
static const char *const CHIP = "AB";

/* 同一时刻只拉低一片的 CS：两片 DOUT 并在一根线上，同时选中会打架 */
static void cs(int chip, int lv) { if (chip == 0) SET(CS_A, lv); else SET(CS_B, lv); }

/* 命令字节之间留 ≥4 tCLK：ADS1298(2.048 MHz) 需 2 µs，ADS1292(内部 512 kHz，SBAS502C tSDECODE) 需 7.81 µs；统一留 10 µs */
static void ads_cmd(int chip, uint8_t c)
{
    cs(chip, 0); delay_us(4); spi_xfer(SPI1, c); delay_us(10); cs(chip, 1); delay_us(10);
}
static uint8_t ads_rreg(int chip, uint8_t a)
{
    cs(chip, 0); delay_us(4);
    spi_xfer(SPI1, 0x20 | a); delay_us(10);
    spi_xfer(SPI1, 0x00); delay_us(10);
    uint8_t v = spi_xfer(SPI1, 0x00); delay_us(10);
    cs(chip, 1); delay_us(10);
    return v;
}
static void ads_wreg(int chip, uint8_t a, uint8_t v)
{
    cs(chip, 0); delay_us(4);
    spi_xfer(SPI1, 0x40 | a); delay_us(10);
    spi_xfer(SPI1, 0x00); delay_us(10);
    spi_xfer(SPI1, v); delay_us(10);
    cs(chip, 1); delay_us(10);
}

/* ADS1298 自检寄存器表：500 SPS 高精度、测试方波、不开 RLD、GPIO 全设输入（GPIO1/2/4 接地，设输出会短路）。
   16CH 下 U1 与 U2 均开启片内测试源（CONFIG2=0x10，INT_TEST=1）：
   - 人工审核定版 v0.01 AFE-30P 上 U1.17/18 与 U2.17/18 独立悬空，必须两片均置 INT_TEST=1 才能让 CH9..16 产生 1 Hz 方波；
   - PACE(0x15)=0x00 (PD_PACE=0) 不向 17/18 脚外驱，因此在 D20（17/18 互联）上同样无驱动冲突。
   CONFIG3(0x03)=0xC0：Pin 60(RLDREF) 接 AGND、v0.01 Pin 62(RLDIN) 接 +2.5V，严禁置 VREF_4V/RLD_MEAS/RLDREF_INT（即 (cfg[0x03]&0x38)==0）。 */
static const uint8_t CFG1298_TEST[0x1A] = {
    [0x01] = 0x86,             /* CONFIG1：HR=1，DR=110 → 500 SPS */
    [0x02] = 0x10,             /* CONFIG2：INT_TEST=1，1×VREF/2400，约 1 Hz */
    [0x03] = 0xC0,             /* CONFIG3：内部基准 2.4 V，VREF_4V=0，RLD_MEAS=0，RLDREF_INT=0，PD_RLD=0 */
    [0x05 ... 0x0C] = 0x05,    /* CHnSET：增益 6，输入接测试信号 */
    [0x14] = 0x0F,             /* GPIO：4 脚都设输入 */
    [0x16] = 0x20,             /* RESP：bit5 手册要求写 1 */
};
static const uint8_t MASK1298[0x1A] = {
    [0x01] = 0xFF, [0x02] = 0x3F, [0x03] = 0xFE, [0x04 ... 0x11] = 0xFF, [0x14] = 0x0F, [0x15 ... 0x19] = 0xFF,
};

/* ADS1292 自检寄存器表（TI SBAS502C §9.6.1）：
   - CONFIG1(0x01)=0x02：连续转换 500 SPS（高 4 位 bit6:3 保留读 0，掩码 0x87）
   - CONFIG2(0x02)=0xA3：bit7=1，PDB_REFBUF=1（开内部 2.42 V 基准），INT_TEST=1，TEST_FREQ=1（1 Hz 方波；写 0 是直流！）
   - LOFF(0x03)=0x10：bit4 写 1；CH1SET/CH2SET(0x04/0x05)=0x05（增益 6，MUX=0101 测试信号）
   - LOFF_STAT(0x08) 只读不写；RESP1(0x09)=0x02（bit1 写 1）；RESP2(0x0A)=0x07（SBAS502C 表 24：非 R 版 ADS1292 bit2 必写 1，RLDREF_INT=1，bit0=1）
   - GPIO(0x0B)=0x0C：GPIOC[2:1]=11 两脚都设输入（板上 R21/R22 47k 下拉接地） */
static const uint8_t CFG1292_TEST[0x0C] = {
    [0x01] = 0x02, [0x02] = 0xA3, [0x03] = 0x10, [0x04] = 0x05, [0x05] = 0x05,
    [0x06] = 0x00, [0x07] = 0x00, [0x09] = 0x02, [0x0A] = 0x07, [0x0B] = 0x0C,
};
static const uint8_t MASK1292[0x0C] = {
    [0x01] = 0x87, [0x02] = 0x7B, [0x03] = 0xFF, [0x04] = 0xFF, [0x05] = 0xFF,
    [0x06] = 0x3F, [0x07] = 0x3F, [0x09] = 0xFF, [0x0A] = 0x87, [0x0B] = 0x0C,
};

static int ads_write_check(int chip, const uint8_t *cfg, const uint8_t *mask, int a0, int a1)
{
    int bad = 0;
    for (int a = a0; a <= a1; a++) if (mask[a]) ads_wreg(chip, (uint8_t)a, cfg[a]);
    for (int a = a0; a <= a1; a++) {
        if (!mask[a]) continue;
        uint8_t v = ads_rreg(chip, (uint8_t)a);
        if ((v ^ cfg[a]) & mask[a]) { bad++; logf_("  ADS_%c 寄存器 0x%02X 写 0x%02X 读回 0x%02X\n", CHIP[chip], a, cfg[a], v); }
    }
    return bad;
}

/* 采集统计 */
typedef struct {
    int32_t mn[16], mx[16];
    int64_t s[16], s2[16];
    uint32_t n;
    uint32_t t_first, t_last;   /* DWT 周期计数 */
} stats_t;

static int32_t s24(const uint8_t *b) { int32_t v = (b[0] << 16) | (b[1] << 8) | b[2]; return (v << 8) >> 8; }

/* 返回 0 = 正常；-1 = DRDY 超时。ch_per_chip：ADS1298 为 8（每帧 27B），ADS1292 为 2（每帧 9B） */
static int capture(int alive_a, int alive_b, int ch_per_chip, uint32_t frames, uint32_t skip, stats_t *st)
{
    volatile c08b_report_t *r = &g_report;
    int frame_bytes = 3 + ch_per_chip * 3;
    for (int c = 0; c < 16; c++) { st->mn[c] = INT32_MAX; st->mx[c] = INT32_MIN; st->s[c] = st->s2[c] = 0; }
    st->n = 0;
    for (uint32_t i = 0; i < frames + skip; i++) {
        uint32_t t = g_ms;
        while (GET(DRDY_A)) if (g_ms - t > 20) return -1;      /* 500 SPS 周期 2 ms，20 ms 没来算超时 */
        uint32_t now = DWT->CYCCNT;
        delay_us(2);
        if (alive_b && GET(DRDY_B)) r->drdy_desync++;
        uint8_t buf[2][27] = {{0}};
        for (int chip = 0; chip < 2; chip++) {
            if (!(chip ? alive_b : alive_a)) continue;
            cs(chip, 0); delay_us(1);
            for (int k = 0; k < frame_bytes; k++) buf[chip][k] = spi_xfer(SPI1, 0x00);
            delay_us(10); cs(chip, 1); delay_us(1);               /* ADS1292 t_SCCS >= 4 t_CLK = 7.81 us */
            if ((buf[chip][0] & 0xF0) != 0xC0) r->bad_status++;
            /* 16CH 两片共用 SCLK，读 U1 时 U2 的 DRDY 被 SCLK 清成高；还是低说明 DRDY_B 卡低 */
            if (chip == 0 && alive_b && !GET(DRDY_B)) r->drdy_desync++;
            /* 2CH 模式下 PA4 已放净残荷并保持无上下拉高阻输入，逐帧核对 AVDD_SENSE(3.0V) 持续为高 */
            if (chip == 0 && !alive_b && ch_per_chip == 2 && !GET(DRDY_B)) r->bad_status++;
        }
        if (i < skip) continue;
        if (st->n == 0) st->t_first = now;
        st->t_last = now;
        for (int chip = 0; chip < 2; chip++) {
            if (!(chip ? alive_b : alive_a)) continue;
            for (int ch = 0; ch < ch_per_chip; ch++) {
                int c = chip * 8 + ch;
                int32_t v = s24(&buf[chip][3 + ch * 3]);
                if (v < st->mn[c]) st->mn[c] = v;
                if (v > st->mx[c]) st->mx[c] = v;
                st->s[c] += v; st->s2[c] += (int64_t)v * v;
            }
        }
        st->n++;
        t = g_ms;
        while (!GET(DRDY_A)) if (g_ms - t > 5) break;          /* 读走数据后 DRDY 应回高 */
    }
    return 0;
}

/* 1 LSB = 2·VREF / 增益 / (2^24 − 1)：ADS1298 VREF=2.40 V（47.68 nV），ADS1292 VREF=2.42 V（48.08 nV） */
#define LSB_NV_1298 (2.0 * 2.40e9 / 6.0 / 16777215.0)
#define LSB_NV_1292 (2.0 * 2.42e9 / 6.0 / 16777215.0)

/* ---------- IMU（I2C1，LSM6DS3TR-C，SA0 接地 → 0x6A） ---------- */
static int i2c_wait(uint32_t flag)
{
    uint32_t t = g_ms;
    while (!(I2C1->ISR & flag)) {
        if (I2C1->ISR & I2C_ISR_NACKF) { I2C1->ICR = I2C_ICR_NACKCF | I2C_ICR_STOPCF; return -1; }
        if (g_ms - t > 10) return -2;
    }
    return 0;
}
static int i2c_read(uint8_t addr, uint8_t reg, uint8_t *b, int n)
{
    I2C1->ICR = 0x3F38;
    I2C1->CR2 = ((uint32_t)addr << 1) | (1u << I2C_CR2_NBYTES_Pos) | I2C_CR2_START;
    if (i2c_wait(I2C_ISR_TXIS)) return -1;
    I2C1->TXDR = reg;
    if (i2c_wait(I2C_ISR_TC)) return -1;
    I2C1->CR2 = ((uint32_t)addr << 1) | I2C_CR2_RD_WRN | ((uint32_t)n << I2C_CR2_NBYTES_Pos) | I2C_CR2_AUTOEND | I2C_CR2_START;
    for (int i = 0; i < n; i++) { if (i2c_wait(I2C_ISR_RXNE)) return -1; b[i] = (uint8_t)I2C1->RXDR; }
    if (i2c_wait(I2C_ISR_STOPF)) return -1;
    I2C1->ICR = I2C_ICR_STOPCF;
    return 0;
}
static int i2c_write(uint8_t addr, uint8_t reg, uint8_t v)
{
    I2C1->ICR = 0x3F38;
    I2C1->CR2 = ((uint32_t)addr << 1) | (2u << I2C_CR2_NBYTES_Pos) | I2C_CR2_AUTOEND | I2C_CR2_START;
    if (i2c_wait(I2C_ISR_TXIS)) return -1;
    I2C1->TXDR = reg;
    if (i2c_wait(I2C_ISR_TXIS)) return -1;
    I2C1->TXDR = v;
    if (i2c_wait(I2C_ISR_STOPF)) return -1;
    I2C1->ICR = I2C_ICR_STOPCF;
    return 0;
}

/* ---------- 初始化 ---------- */
static void clock_init(void)
{
    RCC->CR |= RCC_CR_HSION;
    while (!(RCC->CR & RCC_CR_HSIRDY)) {}
    RCC->CFGR = (RCC->CFGR & ~RCC_CFGR_SW) | RCC_CFGR_SW_HSI;   /* 16 MHz，量程 1 下 0 等待周期即可 */
    while ((RCC->CFGR & RCC_CFGR_SWS) != RCC_CFGR_SWS_HSI) {}
    SystemCoreClockUpdate();
    SysTick_Config(SystemCoreClock / 1000u);
    CoreDebug->DEMCR |= CoreDebug_DEMCR_TRCENA_Msk;
    DWT->CYCCNT = 0;
    DWT->CTRL |= DWT_CTRL_CYCCNTENA_Msk;
    RCC->AHB2ENR |= RCC_AHB2ENR_GPIOAEN | RCC_AHB2ENR_GPIOBEN | RCC_AHB2ENR_GPIOCEN | RCC_AHB2ENR_GPIOHEN;
    RCC->APB2ENR |= RCC_APB2ENR_SPI1EN;
    RCC->APB1ENR1 |= RCC_APB1ENR1_SPI3EN | RCC_APB1ENR1_I2C1EN;
    (void)RCC->APB1ENR1;
}

static void gpio_init(void)
{
    /* 先定电平再切输出：CS 高、START 低、PWDN/RESET 低（ADS 保持掉电）、ANA_EN 低（缓冲关） */
    OUT_INIT(CS_A, 1); OUT_INIT(CS_B, 1); OUT_INIT(ADS_START, 0);
    OUT_INIT(ADS_PWDN, 0); OUT_INIT(ADS_RESET, 0); OUT_INIT(ANA_EN, 0);
    OUT_INIT(LINK_CS, 1);
    pin_mode(DRDY_A_PORT, DRDY_A_PIN, M_IN, 0, P_NONE, 0);     /* 板上 R701 100k 下拉 */
    pin_mode(DRDY_B_PORT, DRDY_B_PIN, M_IN, 0, P_UP, 0);       /* 主控侧无外部电阻，默认上拉防浮空 */
    pin_mode(AFE_GPIO3_PORT, AFE_GPIO3_PIN, M_IN, 0, P_DOWN, 0);
    pin_mode(LINK_RDY_PORT, LINK_RDY_PIN, M_IN, 0, P_DOWN, 0);
    pin_mode(IMU_INT1_PORT, IMU_INT1_PIN, M_IN, 0, P_NONE, 0);
    pin_mode(BOOT0_PORT, BOOT0_PIN, M_IN, 0, P_NONE, 0);       /* PH3-BOOT0 接 VBUS_SENSE，只读不驱动 */
    pin_mode(SPI1_SCK_PORT, SPI1_SCK_PIN, M_AF, 5, P_NONE, 0);
    pin_mode(SPI1_MISO_PORT, SPI1_MISO_PIN, M_AF, 5, P_DOWN, 0);
    pin_mode(SPI1_MOSI_PORT, SPI1_MOSI_PIN, M_AF, 5, P_NONE, 0);
    pin_mode(LINK_SCK_PORT, LINK_SCK_PIN, M_AF, 6, P_NONE, 0);
    pin_mode(LINK_MISO_PORT, LINK_MISO_PIN, M_AF, 6, P_DOWN, 0);
    pin_mode(LINK_MOSI_PORT, LINK_MOSI_PIN, M_AF, 6, P_NONE, 0);
    pin_mode(IMU_SCL_PORT, IMU_SCL_PIN, M_AF, 4, P_NONE, 1);
    pin_mode(IMU_SDA_PORT, IMU_SDA_PIN, M_AF, 4, P_NONE, 1);
}

static void mark(int t, int ok)
{
    g_report.done_mask |= (uint16_t)(1u << t);
    if (!ok) g_report.fail_mask |= (uint16_t)(1u << t);
    logf_("[%s] %s\n", ok ? "过" : "不过", TEST_NAME[t]);
}

static void test_ads(void)
{
    volatile c08b_report_t *r = &g_report;
    spi_init(SPI1, 1, 1);                 /* 16 MHz / 4 = 4 MHz，模式 1 */
    SET(ANA_EN, 1);                       /* 打开 U2/U3 缓冲 */
    delay_ms(60);                         /* 等 OE_N RC 建立变低 */
    /* 兼顾 ADS1298（RESET 接 PA8）与 ADS1292（PWDN/RESET 接 PA1）：先拉高 20 ms，再发 50 µs 同步复位低脉冲，后等满 200 ms > tPOR */
    SET(ADS_PWDN, 1); SET(ADS_RESET, 1);
    delay_ms(20);
    SET(ADS_PWDN, 0); SET(ADS_RESET, 0);
    delay_us(50);
    SET(ADS_PWDN, 1); SET(ADS_RESET, 1);
    delay_ms(200);

    for (int chip = 0; chip < 2; chip++) {
        ads_cmd(chip, ADS_SDATAC);
        uint8_t id = ads_rreg(chip, 0x00);
        if (chip == 0) r->id_a = id; else r->id_b = id;
        logf_("ADS_%c ID = 0x%02X\n", CHIP[chip], id);
    }

    afe_mode_t mode = afe_detect(r->id_a, r->id_b);
    logf_("自动识别采集板：%s\n", afe_mode_name(mode));
    if (mode == AFE_NONE) {
        mark(T_ADS_A_ID, ADS1298_ID_OK(r->id_a) || ADS1292_ID_OK(r->id_a));
        mark(T_ADS_B_ID, ADS1298_ID_OK(r->id_b));
        logf_("采集板未就绪或 ID 异常：查 3V3_AFE、J_AFE 排线朝向、OE_N（互锁）\n");
        return;
    }

    int is_1292 = (mode == AFE_2CH);
    int alive_a = 1, alive_b = (mode == AFE_16CH);
    int ch_per_chip = is_1292 ? 2 : 8;
    int total_ch = (int)mode;             /* 2 / 8 / 16 */
    double lsb_nv = is_1292 ? LSB_NV_1292 : LSB_NV_1298;

    mark(T_ADS_A_ID, 1);
    if (alive_b) mark(T_ADS_B_ID, 1);

    /* 2CH 专属检查：PA4（DRDY_B）在 ADS1292-2ch 板上经 R26(100k) 接 3.0V AVDD_SENSE。
     * 先短暂下拉 10 us 放净前置 P_UP 在引脚/排线寄生电容上的 3.3V 残荷（防止开路假阳性），
     * 再切并全程保持 P_NONE 高阻输入（不回切 P_UP，防止 3.3V 往 3.0V AVDD 灌电，且供 capture 逐帧监测）。 */
    if (is_1292) {
        pin_mode(DRDY_B_PORT, DRDY_B_PIN, M_IN, 0, P_DOWN, 0);
        delay_us(10);
        pin_mode(DRDY_B_PORT, DRDY_B_PIN, M_IN, 0, P_NONE, 0);
        delay_us(50);
        int avdd_ok = GET(DRDY_B);
        logf_("  2CH AVDD_SENSE(3.0V) = %d%s\n", avdd_ok, avdd_ok ? "" : "（异常：U3 3.0V LDO 未输出或 J2.3 开路）");
        if (!avdd_ok) r->bad_status++;
    }

    if (is_1292) {
        int bad = ads_write_check(0, CFG1292_TEST, MASK1292, 0x01, 0x0B);
        r->reg_bad_a = (uint8_t)bad;
        mark(T_REG_A, bad == 0);
    } else {
        for (int chip = 0; chip < 2; chip++) {
            if (!(chip ? alive_b : alive_a)) continue;
            uint8_t cfg[0x1A]; for (int a = 0; a < 0x1A; a++) cfg[a] = CFG1298_TEST[a];
            /* U1 与 U2 均保持 cfg[0x02]=0x10 (INT_TEST=1)，兼容 v0.01 AFE-30P 独立 17/18 脚与 D20 */
            int bad = ads_write_check(chip, cfg, MASK1298, 0x01, 0x19);
            if (chip == 0) r->reg_bad_a = (uint8_t)bad; else r->reg_bad_b = (uint8_t)bad;
            mark(chip ? T_REG_B : T_REG_A, bad == 0);
        }
    }
    delay_ms(150);                        /* 内部基准稳定 */

    /* 方波阶段：2000 帧（4 s，约 4 个周期），丢前 100 帧 */
    ads_cmd(0, ADS_RDATAC);
    if (alive_b) ads_cmd(1, ADS_RDATAC);
    SET(ADS_START, 1);
    static stats_t st;
    int to1 = capture(alive_a, alive_b, ch_per_chip, 2000, 100, &st);
    SET(ADS_START, 0);
    delay_ms(3);
    r->frames = (uint16_t)st.n;
    uint32_t dt = st.t_last - st.t_first;
    if (st.n > 1 && dt) r->rate_hz_x10 = (uint16_t)((uint64_t)(st.n - 1) * SystemCoreClock * 10u / dt);
    /* ADS1298 走板上有源晶振 2.048 MHz（严守 ±2%）；ADS1292 走片内 RC 512 kHz（全温 ±2% 叠加 HSI16，给 ±4%） */
    uint16_t rate_lo = is_1292 ? 4800 : 4900, rate_hi = is_1292 ? 5200 : 5100;
    int rate_ok = r->rate_hz_x10 >= rate_lo && r->rate_hz_x10 <= rate_hi;
    logf_("方波阶段 %u 帧，采样率 %u.%u Hz%s\n", (unsigned)st.n, r->rate_hz_x10 / 10, r->rate_hz_x10 % 10, to1 ? "，DRDY 超时" : "");

    uint16_t pp[16]; int npp = 0;
    for (int c = 0; c < total_ch; c++) {
        double uv = st.n ? (double)(st.mx[c] - st.mn[c]) * lsb_nv / 1000.0 : 0;
        r->sig_pp_uv[c] = (uint16_t)(uv > 65535 ? 65535 : uv);
        if (st.n) pp[npp++] = r->sig_pp_uv[c];
    }
    for (int i = 1; i < npp; i++) for (int j = i; j > 0 && pp[j - 1] > pp[j]; j--) { uint16_t t = pp[j]; pp[j] = pp[j - 1]; pp[j - 1] = t; }
    uint32_t med = npp ? pp[npp / 2] : 0;
    int sig_ok = (npp == total_ch) && !to1;
    for (int c = 0; c < total_ch; c++) {
        uint32_t v = r->sig_pp_uv[c];
        int ok = v >= 500 && v <= 5000 && v * 10 >= med * 8 && v * 10 <= med * 12;
        if (!ok) sig_ok = 0;
        logf_("  CH%-2d 方波峰峰值 %5u µV%s\n", c + 1, (unsigned)v, ok ? "" : "  ←");
    }
    mark(T_TEST_SIG, sig_ok);

    /* 短接阶段：CHnSET = 0x01、关测试源，1000 帧，丢前 100 帧 */
    if (is_1292) {
        ads_cmd(0, ADS_SDATAC);
        uint8_t cfg[0x0C]; for (int a = 0; a < 0x0C; a++) cfg[a] = CFG1292_TEST[a];
        cfg[0x02] = 0xA0;                 /* 保持 PDB_REFBUF=1 内部 2.42V 基准开启，只关 INT_TEST/TEST_FREQ */
        cfg[0x04] = 0x01; cfg[0x05] = 0x01;
        int bad = ads_write_check(0, cfg, MASK1292, 0x01, 0x05);
        if (bad) { r->reg_bad_a += (uint8_t)bad; mark(T_REG_A, 0); }
        ads_cmd(0, ADS_RDATAC);
    } else {
        for (int chip = 0; chip < 2; chip++) {
            if (!(chip ? alive_b : alive_a)) continue;
            ads_cmd(chip, ADS_SDATAC);
            uint8_t cfg[0x1A]; for (int a = 0; a < 0x1A; a++) cfg[a] = CFG1298_TEST[a];
            cfg[0x02] = 0x00; for (int a = 0x05; a <= 0x0C; a++) cfg[a] = 0x01;
            int bad = ads_write_check(chip, cfg, MASK1298, 0x01, 0x0C);
            if (bad) { if (chip == 0) r->reg_bad_a += (uint8_t)bad; else r->reg_bad_b += (uint8_t)bad; mark(chip ? T_REG_B : T_REG_A, 0); }
            ads_cmd(chip, ADS_RDATAC);
        }
    }
    SET(ADS_START, 1);
    int to2 = capture(alive_a, alive_b, ch_per_chip, 1000, 100, &st);
    SET(ADS_START, 0);
    delay_ms(3);
    int noise_ok = !to2 && st.n > 0;
    for (int c = 0; c < total_ch; c++) {
        double rms_nv = 0;
        if (st.n > 1) {
            double m = (double)st.s[c] / st.n, var = (double)st.s2[c] / st.n - m * m;
            rms_nv = (var > 0 ? __builtin_sqrt(var) : 0) * lsb_nv;
        }
        r->noise_rms_nv[c] = (uint16_t)(rms_nv > 65535 ? 65535 : rms_nv);
        int ok = rms_nv >= 100 && rms_nv < 5000;
        if (!ok) noise_ok = 0;
        logf_("  CH%-2d 短接底噪 %5u nV RMS%s\n", c + 1, r->noise_rms_nv[c], ok ? "" : "  ←");
    }
    mark(T_NOISE, noise_ok);
    logf_("两阶段合计：DRDY 不同步 %u 帧，状态字错 %u 帧%s\n", r->drdy_desync, r->bad_status, to2 ? "，短接阶段 DRDY 超时" : "");
    mark(T_DRDY, !to1 && !to2 && rate_ok && (!alive_b || r->drdy_desync == 0));
    mark(T_STATUS, r->bad_status == 0 && !to1 && !to2);
    ads_cmd(0, ADS_SDATAC);
    if (alive_b) ads_cmd(1, ADS_SDATAC);
}

static void test_imu(void)
{
    volatile c08b_report_t *r = &g_report;
    I2C1->CR1 = 0;
    I2C1->TIMINGR = 0x00303D5B;           /* PCLK1 16 MHz → 100 kHz */
    I2C1->CR1 = I2C_CR1_PE;
    uint8_t id = 0;
    int e = i2c_read(0x6A, 0x0F, &id, 1);
    r->imu_id = e ? 0 : id;
    logf_("IMU WHO_AM_I = 0x%02X%s\n", id, e ? "（I2C 无应答）" : "");
    mark(T_IMU_ID, !e && id == 0x6A);
    if (e || id != 0x6A) return;
    i2c_write(0x6A, 0x10, 0x40);          /* CTRL1_XL：104 Hz，±2 g */
    delay_ms(100);
    uint8_t b[6];
    if (i2c_read(0x6A, 0x28, b, 6)) { mark(T_IMU_G, 0); return; }
    int32_t sum2 = 0;
    for (int i = 0; i < 3; i++) {
        int16_t raw = (int16_t)(b[2 * i] | (b[2 * i + 1] << 8));
        r->imu_mg[i] = (int16_t)(raw * 61 / 1000);
        sum2 += (int32_t)r->imu_mg[i] * r->imu_mg[i];
    }
    logf_("IMU 加速度 %d %d %d mg\n", r->imu_mg[0], r->imu_mg[1], r->imu_mg[2]);
    mark(T_IMU_G, sum2 >= 800 * 800 && sum2 <= 1200 * 1200);
}

static void link_send(void)
{
    c08b_report_t r = g_report;
    r.seq++;
    report_seal(&r);
    g_report.seq = r.seq;
    SET(LINK_CS, 0); delay_us(20);
    const uint8_t *p = (const uint8_t *)&r;
    for (unsigned i = 0; i < sizeof r; i++) spi_xfer(SPI3, p[i]);
    delay_us(5); SET(LINK_CS, 1);
}

int main(void)
{
    clock_init();
    gpio_init();
    rtt_init();
    spi_init(SPI3, 2, 0);                 /* LINK：16 MHz / 8 = 2 MHz，模式 0 */
    g_report.magic = REPORT_MAGIC;
    g_report.version = REPORT_VERSION;
    logf_("\nC08B L432 自检开始（自动识别 16CH / 8CH / 2CH）\n");
    test_ads();
    test_imu();
    logf_("自检完：done 0x%04X，fail 0x%04X\n", g_report.done_mask, g_report.fail_mask);
    for (;;) {
        if (GET(LINK_RDY)) link_send();
        delay_ms(500);
    }
}

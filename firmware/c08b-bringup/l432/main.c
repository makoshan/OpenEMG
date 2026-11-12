/* C08B 主控 STM32L432KCU6 上电自检（裸机，只用 CMSIS 头）。
   做什么：开 AFE 缓冲 → 复位两片 ADS1298 → 读 ID → 写寄存器并逐个回读 → 内部方波测 16 路幅度与采样率
          → 输入短接测底噪 → I2C 读 IMU → 结果打包，每 500 ms 经 SPI3 发给 nRF52840（nRF 拉高 LINK_RDY 才发）。
   结果也放在 RAM 变量 g_report 和 RTT 日志里，接 SWD（J302 + J301 的 3V3/GND）可以直接读。
   不碰 USB，不写 flash 选项字节，不驱动 BOOT0。时钟用 HSI16（16 MHz），不依赖外部晶振。 */
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

/* ---------- ADS1298 ---------- */
#define ADS_SDATAC 0x11
#define ADS_RDATAC 0x10
#define ADS_ID_OK(id) (((id) & 0x1F) == 0x12)   /* ADS1298 = 0x92（ADS1298R = 0xD2 也认） */
static const char *const CHIP = "AB";

/* 同一时刻只拉低一片的 CS：两片 DOUT 并在一根线上，同时选中会打架 */
static void cs(int chip, int lv) { if (chip == 0) SET(CS_A, lv); else SET(CS_B, lv); }

/* 命令字节之间留 ≥4 tCLK（2.048 MHz 下约 2 µs，手册 tSDECODE），这里给 3 µs */
static void ads_cmd(int chip, uint8_t c)
{
    cs(chip, 0); delay_us(2); spi_xfer(SPI1, c); delay_us(3); cs(chip, 1); delay_us(3);
}
static uint8_t ads_rreg(int chip, uint8_t a)
{
    cs(chip, 0); delay_us(2);
    spi_xfer(SPI1, 0x20 | a); delay_us(3);
    spi_xfer(SPI1, 0x00); delay_us(3);
    uint8_t v = spi_xfer(SPI1, 0x00); delay_us(3);
    cs(chip, 1); delay_us(3);
    return v;
}
static void ads_wreg(int chip, uint8_t a, uint8_t v)
{
    cs(chip, 0); delay_us(2);
    spi_xfer(SPI1, 0x40 | a); delay_us(3);
    spi_xfer(SPI1, 0x00); delay_us(3);
    spi_xfer(SPI1, v); delay_us(3);
    cs(chip, 1); delay_us(3);
}

/* 自检用寄存器表：500 SPS 高精度、测试方波、两片都不开 RLD、GPIO 全设输入（GPIO1/2/4 在板上接地，设输出会短路）。
   两片的 TESTP/TESTN（17/18 脚）在采集板上并在 V4_REF1/V4_REF2（只接 TP901–904）：按手册 9.3.1.3.2 的多片用法，
   只让 U1 内部产生测试信号（INT_TEST=1）往外送，U2 写 INT_TEST=0 接收同一个信号，避免两片输出顶在一个节点上。 */
static const uint8_t CFG_TEST[0x1A] = {
    [0x01] = 0x86,             /* CONFIG1：HR=1，DR=110 → 500 SPS */
    [0x02] = 0x10,             /* CONFIG2：INT_TEST=1，1×VREF/2400，约 1 Hz（U2 在 test_ads 里改成 0x00） */
    [0x03] = 0xC0,             /* CONFIG3：内部基准 2.4 V，不开 RLD */
    [0x05 ... 0x0C] = 0x05,    /* CHnSET：增益 6，输入接测试信号 */
    [0x14] = 0x0F,             /* GPIO：4 脚都设输入 */
    [0x16] = 0x20,             /* RESP：bit5 手册要求写 1 */
};
/* 回读比较掩码：0 = 只读或不比；CONFIG2 bit7:6 保留（复位值 1、手册要求写 0，回读不比）；CONFIG3 bit0 是 RLD_STAT；GPIO 高 4 位是输入电平 */
static const uint8_t CFG_MASK[0x1A] = {
    [0x01] = 0xFF, [0x02] = 0x3F, [0x03] = 0xFE, [0x04 ... 0x11] = 0xFF, [0x14] = 0x0F, [0x15 ... 0x19] = 0xFF,
};

static int ads_write_check(int chip, const uint8_t *cfg, int a0, int a1)
{
    int bad = 0;
    for (int a = a0; a <= a1; a++) if (CFG_MASK[a]) ads_wreg(chip, (uint8_t)a, cfg[a]);
    for (int a = a0; a <= a1; a++) {
        if (!CFG_MASK[a]) continue;
        uint8_t v = ads_rreg(chip, (uint8_t)a);
        if ((v ^ cfg[a]) & CFG_MASK[a]) { bad++; logf_("  ADS_%c 寄存器 0x%02X 写 0x%02X 读回 0x%02X\n", CHIP[chip], a, cfg[a], v); }
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

/* 返回 0 = 正常；-1 = DRDY 超时 */
static int capture(int alive_a, int alive_b, uint32_t frames, uint32_t skip, stats_t *st)
{
    volatile c08b_report_t *r = &g_report;
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
            for (int k = 0; k < 27; k++) buf[chip][k] = spi_xfer(SPI1, 0x00);
            delay_us(2); cs(chip, 1); delay_us(1);
            if ((buf[chip][0] & 0xF0) != 0xC0) r->bad_status++;
            /* 两片共用 SCLK，读 U1 时 U2 的 DRDY 被 SCLK 清成高（手册 9.4.1.2）；还是低说明 DRDY_B 卡低，上面那条查不出 */
            if (chip == 0 && alive_b && !GET(DRDY_B)) r->drdy_desync++;
        }
        if (i < skip) continue;
        if (st->n == 0) st->t_first = now;
        st->t_last = now;
        for (int chip = 0; chip < 2; chip++) {
            if (!(chip ? alive_b : alive_a)) continue;
            for (int ch = 0; ch < 8; ch++) {
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

/* 1 LSB = 2·VREF / 增益 / (2^24 − 1)；VREF 2.4 V、增益 6 → 约 47.68 nV */
#define LSB_NV (2.0 * 2.4e9 / 6.0 / 16777215.0)

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
    RCC->AHB2ENR |= RCC_AHB2ENR_GPIOAEN | RCC_AHB2ENR_GPIOBEN | RCC_AHB2ENR_GPIOCEN;
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
    pin_mode(DRDY_A_PORT, DRDY_A_PIN, M_IN, 0, P_NONE, 0);     /* 板上 R701 100k 下拉，内部再上拉会分出约 2.4 V 的不定电平 */
    pin_mode(DRDY_B_PORT, DRDY_B_PIN, M_IN, 0, P_UP, 0);       /* 主控侧没有外部电阻，没接采集板时上拉防浮空 */
    pin_mode(AFE_GPIO3_PORT, AFE_GPIO3_PIN, M_IN, 0, P_DOWN, 0); /* ADS GPIO 全设输入，没人驱动 */
    pin_mode(LINK_RDY_PORT, LINK_RDY_PIN, M_IN, 0, P_DOWN, 0);  /* 板上没有外部电阻，nRF 没跑时保持低 */
    pin_mode(IMU_INT1_PORT, IMU_INT1_PIN, M_IN, 0, P_NONE, 0);
    pin_mode(SPI1_SCK_PORT, SPI1_SCK_PIN, M_AF, 5, P_NONE, 0);
    pin_mode(SPI1_MISO_PORT, SPI1_MISO_PIN, M_AF, 5, P_DOWN, 0);
    pin_mode(SPI1_MOSI_PORT, SPI1_MOSI_PIN, M_AF, 5, P_NONE, 0);
    pin_mode(LINK_SCK_PORT, LINK_SCK_PIN, M_AF, 6, P_NONE, 0);
    pin_mode(LINK_MISO_PORT, LINK_MISO_PIN, M_AF, 6, P_DOWN, 0); /* nRF CSN 高时 MISO 高阻 */
    pin_mode(LINK_MOSI_PORT, LINK_MOSI_PIN, M_AF, 6, P_NONE, 0);
    pin_mode(IMU_SCL_PORT, IMU_SCL_PIN, M_AF, 4, P_NONE, 1);    /* 开漏，外部上拉 */
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
    SET(ANA_EN, 1);                       /* 打开 U2/U3 缓冲（插 USB 且没贴 JP701 时互锁会关住，ID 会读不到） */
    delay_ms(60);                         /* R24 47k / R25 100k → R41 4.7k → C24 1 µF，τ≈37 ms，OE_N 约 20–40 ms 后才变低 */
    SET(ADS_PWDN, 1); SET(ADS_RESET, 1);
    delay_ms(200);                        /* tPOR = 2^18 tCLK ≈ 128 ms，再给 VCAP1 建立留余量 */
    SET(ADS_RESET, 0); delay_us(10); SET(ADS_RESET, 1); delay_ms(1);
    int alive[2];
    for (int chip = 0; chip < 2; chip++) {
        ads_cmd(chip, ADS_SDATAC);        /* 上电默认在连续读，读写寄存器前先停 */
        uint8_t id = ads_rreg(chip, 0x00);
        if (chip == 0) r->id_a = id; else r->id_b = id;
        alive[chip] = ADS_ID_OK(id);
        logf_("ADS_%c ID = 0x%02X\n", CHIP[chip], id);
        mark(chip ? T_ADS_B_ID : T_ADS_A_ID, alive[chip]);
    }
    if (!alive[0] && !alive[1]) { logf_("两片 ADS 都没应答：查 3V3_AFE、J_AFE 排线方向、OE_N（互锁）\n"); return; }
    for (int chip = 0; chip < 2; chip++) {
        if (!alive[chip]) continue;
        uint8_t cfg[0x1A]; for (int a = 0; a < 0x1A; a++) cfg[a] = CFG_TEST[a];
        if (chip == 1 && alive[0]) cfg[0x02] = 0x00;  /* U2 接收 U1 送出的测试信号；U1 不应答时 U2 用自己的内部方波 */
        int bad = ads_write_check(chip, cfg, 0x01, 0x19);
        if (chip == 0) r->reg_bad_a = (uint8_t)bad; else r->reg_bad_b = (uint8_t)bad;
        mark(chip ? T_REG_B : T_REG_A, bad == 0);
    }
    delay_ms(150);                        /* 内部基准建立 */

    /* 方波阶段：2000 帧（4 s，约 4 个周期），丢前 100 帧 */
    for (int chip = 0; chip < 2; chip++) if (alive[chip]) ads_cmd(chip, ADS_RDATAC);
    SET(ADS_START, 1);
    static stats_t st;
    int to1 = capture(alive[0], alive[1], 2000, 100, &st);
    SET(ADS_START, 0);
    delay_ms(3);                          /* 停转换后等一帧再发 SDATAC，避开 DRDY 前后 4 tCLK 的禁区（手册 9.5.2.6） */
    r->frames = (uint16_t)st.n;
    uint32_t dt = st.t_last - st.t_first;
    if (st.n > 1 && dt) r->rate_hz_x10 = (uint16_t)((uint64_t)(st.n - 1) * SystemCoreClock * 10u / dt);
    int rate_ok = r->rate_hz_x10 >= 4900 && r->rate_hz_x10 <= 5100;
    logf_("方波阶段 %u 帧，采样率 %u.%u Hz%s\n", (unsigned)st.n, r->rate_hz_x10 / 10, r->rate_hz_x10 % 10, to1 ? "，DRDY 超时" : "");

    uint16_t pp[16]; int npp = 0;
    for (int c = 0; c < 16; c++) {
        int ok = alive[c / 8] && st.n;
        double uv = ok ? (double)(st.mx[c] - st.mn[c]) * LSB_NV / 1000.0 : 0;
        r->sig_pp_uv[c] = (uint16_t)(uv > 65535 ? 65535 : uv);
        if (ok) pp[npp++] = r->sig_pp_uv[c];
    }
    /* 中位数：插入排序 16 个数 */
    for (int i = 1; i < npp; i++) for (int j = i; j > 0 && pp[j - 1] > pp[j]; j--) { uint16_t t = pp[j]; pp[j] = pp[j - 1]; pp[j - 1] = t; }
    uint32_t med = npp ? pp[npp / 2] : 0;
    int sig_ok = npp == 16 && !to1;
    for (int c = 0; c < 16; c++) {
        uint32_t v = r->sig_pp_uv[c];
        int ok = v >= 500 && v <= 5000 && v * 10 >= med * 8 && v * 10 <= med * 12;
        if (!ok) sig_ok = 0;
        logf_("  CH%-2d 方波峰峰值 %5u µV%s\n", c + 1, (unsigned)v, ok ? "" : "  ←");
    }
    mark(T_TEST_SIG, sig_ok);

    /* 短接阶段：CHnSET = 0x01、关测试源，1000 帧，丢前 100 帧 */
    for (int chip = 0; chip < 2; chip++) {
        if (!alive[chip]) continue;
        ads_cmd(chip, ADS_SDATAC);
        uint8_t cfg[0x1A]; for (int a = 0; a < 0x1A; a++) cfg[a] = CFG_TEST[a];
        cfg[0x02] = 0x00; for (int a = 0x05; a <= 0x0C; a++) cfg[a] = 0x01;
        int bad = ads_write_check(chip, cfg, 0x01, 0x0C);
        if (bad) { if (chip == 0) r->reg_bad_a += (uint8_t)bad; else r->reg_bad_b += (uint8_t)bad; mark(chip ? T_REG_B : T_REG_A, 0); }
        ads_cmd(chip, ADS_RDATAC);
    }
    SET(ADS_START, 1);
    int to2 = capture(alive[0], alive[1], 1000, 100, &st);
    SET(ADS_START, 0);
    delay_ms(3);
    int noise_ok = !to2 && st.n > 0 && alive[0] && alive[1];
    for (int c = 0; c < 16; c++) {
        double rms_nv = 0;
        if (alive[c / 8] && st.n > 1) {
            double m = (double)st.s[c] / st.n, var = (double)st.s2[c] / st.n - m * m;
            rms_nv = (var > 0 ? __builtin_sqrt(var) : 0) * LSB_NV;
        }
        r->noise_rms_nv[c] = (uint16_t)(rms_nv > 65535 ? 65535 : rms_nv);
        int ok = alive[c / 8] && rms_nv >= 100 && rms_nv < 5000;   /* 下限防数据卡死（手册典型约 0.6 µV） */
        if (!ok) noise_ok = 0;
        logf_("  CH%-2d 短接底噪 %5u nV RMS%s\n", c + 1, r->noise_rms_nv[c], ok ? "" : "  ←");
    }
    mark(T_NOISE, noise_ok);
    /* DRDY、状态字两项按两个阶段合计判 */
    logf_("两阶段合计：DRDY 不同步 %u 帧，状态字错 %u 帧%s\n", r->drdy_desync, r->bad_status, to2 ? "，短接阶段 DRDY 超时" : "");
    mark(T_DRDY, !to1 && !to2 && rate_ok && r->drdy_desync == 0 && alive[0] && alive[1]);
    mark(T_STATUS, r->bad_status == 0 && !to1 && !to2);
    for (int chip = 0; chip < 2; chip++) if (alive[chip]) ads_cmd(chip, ADS_SDATAC);
}

static void test_imu(void)
{
    volatile c08b_report_t *r = &g_report;
    I2C1->CR1 = 0;
    I2C1->TIMINGR = 0x00303D5B;           /* PCLK1 16 MHz → 100 kHz（ST 标准值） */
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
        r->imu_mg[i] = (int16_t)(raw * 61 / 1000);   /* ±2 g 档 0.061 mg/LSB */
        sum2 += (int32_t)r->imu_mg[i] * r->imu_mg[i];
    }
    logf_("IMU 加速度 %d %d %d mg\n", r->imu_mg[0], r->imu_mg[1], r->imu_mg[2]);
    mark(T_IMU_G, sum2 >= 800 * 800 && sum2 <= 1200 * 1200);
}

static void link_send(void)
{
    c08b_report_t r = g_report;           /* 拷一份，发送中不被改 */
    r.seq++;
    report_seal(&r);
    g_report.seq = r.seq;
    SET(LINK_CS, 0); delay_us(20);        /* 给 nRF SPIS 留出 CSN 下降到收数的时间 */
    const uint8_t *p = (const uint8_t *)&r;
    for (unsigned i = 0; i < sizeof r; i++) spi_xfer(SPI3, p[i]);
    delay_us(5); SET(LINK_CS, 1);
}

int main(void)
{
    clock_init();
    gpio_init();
    rtt_init();
    g_report.magic = REPORT_MAGIC;
    g_report.version = REPORT_VERSION;
    logf_("C08B L432 自检开始（HSI16，ADS 500 SPS）\n");
    test_ads();
    test_imu();
    report_seal((c08b_report_t *)&g_report);
    logf_("完成：done 0x%04X，fail 0x%04X\n", g_report.done_mask, g_report.fail_mask);
    spi_init(SPI3, 3, 0);                 /* 16 MHz / 16 = 1 MHz，模式 0 */
    uint32_t last = 0;
    for (;;) {
        if (g_ms - last >= 500 && GET(LINK_RDY)) { link_send(); last = g_ms; }
    }
}

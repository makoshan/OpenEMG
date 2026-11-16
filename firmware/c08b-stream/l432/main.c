/* C08B 共用双核主控 STM32L432KCU6 实时流式采集候选固件（裸机 CMSIS）。
 *
 * 职责：
 *   1. 默认双硬件锁关闭（MAKO_C08B_AFE_ENABLED=0, MAKO_BENCH_MEASURED=0）：
 *      任何真实 AFE 命令（TST1/SHT1/EXT1/EXR1/RLD1/PRB1）均置 C08B_FAULT_LOCKED(1)，
 *      ANA_EN / ADS_PWDN / ADS_START 锁死低电平；仅允许免开 AFE 电源的 SYN1 双核合成流模式（打 SYNTHETIC=1）。
 *   2. 台架实测解锁后：
 *      - 自动识别三档采集板：16CH(双片 ADS1298) / 8CH(单片 ADS1298) / 2CH(ADS1292 六触点)；
 *      - 拉高 ANA_EN 后执行两步 SPIS1 互锁同步握手，排空陈旧缓冲并确认 nRF 实测 OE_N==0 & VBUS==0；
 *      - 上电保持 ADS_PWDN=1 等待满 >=1050 ms（满足 ADS1292 VCAP1=1 µF 1s 上电建立），仅对 ADS_RESET 发低脉冲；
 *      - 2CH 专属：SPI1 1.000 MHz（<=1.024 MHz），PA4 先 10 µs 下拉放净残荷再保持 P_NONE 监测 3.0V AVDD，
 *        RESP2=0x07，EXR1/RLD1 强制两步开 RLD（0x20 等满 >=150 ms 再写 0x23）；
 *      - 16CH/8CH 专属：SPI1 4.000 MHz，LM27762 ±2.5V 双极供电下锁定内部 2.40V 基准（VREF_4V=0），
 *        Pin 60(RLDREF) 硬连 AGND 且 v0.01 Pin 62(RLDIN) 接 +2.5V，严禁置 VREF_4V / RLD_MEAS / RLDREF_INT（两步 0xC0 -> EXR1/RLD1:0xC4）；
 *      - LSM6DS3TR-C 6 轴 IMU（104 Hz，±8 g / ±1000 dps）使用同源 L432_DWT_1MHz 64 位微秒时间戳；
 *   3. 经 SPI3(8 MHz) 向 nRF52840(SPIS1) 批量推送 280 字节流式帧，同时从 MISO 回收 16 字节控制/互锁帧；
 *      任一侧检测到 USB VBUS、OE_N 断开或 2CH AVDD 掉电立即切断模拟前端并置 C08B_FAULT_INTERLOCK(3)。
 */
#define RTT_IMPL
#include "stm32l432xx.h"
#include "pins.h"
#include "../common/stream_proto.h"
#include "../common/rtt.h"
#include "../common/baremetal_stubs.h"

#if MAKO_C08B_AFE_ENABLED != 0 || MAKO_BENCH_MEASURED != 0
/* 允许外部编译参数在台架验证时显式传入成对的 1，但源码树默认必须为 0（tools/pins.py --check-safety 强扫） */
#endif

void log_sink(const char *s, unsigned n) { (void)s; (void)n; }

/* 供 SWD 调试器直接观察的全局遥测快照 */
volatile c08b_link_tx_t g_tx_frame;
volatile c08b_link_rx_t g_last_rx;

static volatile uint32_t g_ms;
static uint32_t g_cyc_per_us = 16u;
static uint32_t g_cyccnt_prev;
static uint64_t g_cyc_total;

void SysTick_Handler(void) { g_ms++; }

/* 基于 32 位 DWT->CYCCNT（64 MHz PLL 下每 64 拍 = 1 µs）维护不回绕的 64 位 1 MHz 微秒时钟 */
static uint64_t clock_us(void)
{
    uint32_t cur = DWT->CYCCNT;
    uint32_t diff = cur - g_cyccnt_prev;
    g_cyccnt_prev = cur;
    g_cyc_total += diff;
    return g_cyc_total / g_cyc_per_us;
}

static void delay_us(uint32_t us)
{
    uint32_t t0 = DWT->CYCCNT, n = us * g_cyc_per_us;
    while ((DWT->CYCCNT - t0) < n) {}
    (void)clock_us();
}

static void delay_ms(uint32_t ms)
{
    uint32_t t = g_ms;
    while (g_ms - t < ms) { (void)clock_us(); }
}

/* ---------- GPIO ---------- */
enum { M_IN = 0, M_OUT = 1, M_AF = 2 };
enum { P_NONE = 0, P_UP = 1, P_DOWN = 2 };

static void pin_mode(GPIO_TypeDef *p, int pin, int mode, int af, int pull, int od)
{
    p->PUPDR = (p->PUPDR & ~(3u << (pin * 2))) | ((uint32_t)pull << (pin * 2));
    p->OTYPER = (p->OTYPER & ~(1u << pin)) | ((uint32_t)od << pin);
    /* PC13–15 经电源开关供电限 2 MHz；复用口 SPI/I2C 开高速 */
    p->OSPEEDR = (p->OSPEEDR & ~(3u << (pin * 2))) | ((mode == M_AF ? 2u : 0u) << (pin * 2));
    if (mode == M_AF) {
        volatile uint32_t *afr = &p->AFR[pin >> 3];
        int s = (pin & 7) * 4;
        *afr = (*afr & ~(0xFu << s)) | ((uint32_t)af << s);
    }
    p->MODER = (p->MODER & ~(3u << (pin * 2))) | ((uint32_t)mode << (pin * 2));
}

static inline void pin_set(GPIO_TypeDef *p, int pin, int v)
{
    p->BSRR = v ? (1u << pin) : (1u << (pin + 16));
}
static inline int pin_get(GPIO_TypeDef *p, int pin)
{
    return (int)((p->IDR >> pin) & 1u);
}

#define OUT_INIT(name, lv) do { pin_set(name##_PORT, name##_PIN, lv); pin_mode(name##_PORT, name##_PIN, M_OUT, 0, P_NONE, 0); } while (0)
#define SET(name, lv) pin_set(name##_PORT, name##_PIN, lv)
#define GET(name) pin_get(name##_PORT, name##_PIN)

/* ---------- SPI ---------- */
static void spi_init(SPI_TypeDef *s, uint32_t br, int cpha)
{
    s->CR1 = 0;
    s->CR1 = SPI_CR1_MSTR | SPI_CR1_SSM | SPI_CR1_SSI | (br << SPI_CR1_BR_Pos) | (cpha ? SPI_CR1_CPHA : 0);
    s->CR2 = (7u << SPI_CR2_DS_Pos) | SPI_CR2_FRXTH;
    s->CR1 |= SPI_CR1_SPE;
}

static inline uint8_t spi_xfer(SPI_TypeDef *s, uint8_t b)
{
    while (!(s->SR & SPI_SR_TXE)) {}
    *(volatile uint8_t *)&s->DR = b;
    while (!(s->SR & SPI_SR_RXNE)) {}
    return *(volatile uint8_t *)&s->DR;
}

/* ---------- 安全停机：立刻切断 AFE 缓冲与全部控制线 ---------- */
static void afe_safe_off(void)
{
    SET(ADS_START, 0);
    SET(CS_A, 1);
    SET(CS_B, 1);
    SET(ADS_PWDN, 0);
    SET(ADS_RESET, 0);
    SET(ANA_EN, 0);
    pin_mode(DRDY_B_PORT, DRDY_B_PIN, M_IN, 0, P_NONE, 0);
}

static inline bool l432_vbus_present(void)
{
    return GET(BOOT0) != 0; /* PH3-BOOT0 接 VBUS 68k/100k 分压，只读 */
}

/* ---------- ADS1298 / ADS1292 底层访问 ---------- */
#define ADS_SDATAC 0x11u
#define ADS_RDATAC 0x10u

static void cs_select(int chip, int lv)
{
    if (chip == 0) SET(CS_A, lv);
    else SET(CS_B, lv);
}

static void ads_cmd(int chip, uint8_t c)
{
    cs_select(chip, 0); delay_us(4);
    spi_xfer(SPI1, c); delay_us(C08B_ADS_TSCCS_US);
    cs_select(chip, 1); delay_us(C08B_ADS_TSCCS_US);
}

static uint8_t ads_rreg(int chip, uint8_t a)
{
    cs_select(chip, 0); delay_us(4);
    spi_xfer(SPI1, (uint8_t)(0x20u | a)); delay_us(C08B_ADS_TSCCS_US);
    spi_xfer(SPI1, 0x00u); delay_us(C08B_ADS_TSCCS_US);
    uint8_t v = spi_xfer(SPI1, 0x00u); delay_us(C08B_ADS_TSCCS_US);
    cs_select(chip, 1); delay_us(C08B_ADS_TSCCS_US);
    return v;
}

static void ads_wreg(int chip, uint8_t a, uint8_t v)
{
    cs_select(chip, 0); delay_us(4);
    spi_xfer(SPI1, (uint8_t)(0x40u | a)); delay_us(C08B_ADS_TSCCS_US);
    spi_xfer(SPI1, 0x00u); delay_us(C08B_ADS_TSCCS_US);
    spi_xfer(SPI1, v); delay_us(C08B_ADS_TSCCS_US);
    cs_select(chip, 1); delay_us(C08B_ADS_TSCCS_US);
}

static int ads_write_verify(int chip, const uint8_t *cfg, const uint8_t *mask, int a0, int a1)
{
    int bad = 0;
    for (int a = a0; a <= a1; a++) {
        if (mask[a]) ads_wreg(chip, (uint8_t)a, cfg[a]);
    }
    for (int a = a0; a <= a1; a++) {
        if (!mask[a]) continue;
        uint8_t v = ads_rreg(chip, (uint8_t)a);
        if ((v ^ cfg[a]) & mask[a]) bad++;
    }
    return bad;
}

/* ---------- IMU（I2C1，LSM6DS3TR-C @ 0x6A，104 Hz，±8 g / ±1000 dps） ---------- */
static void i2c_reset_bus(void)
{
    I2C1->CR1 = 0;
    I2C1->TIMINGR = 0x0010061Au; /* PCLK1 16 MHz -> 400 kHz 快速模式，读 12 字节仅需 ~350 µs */
    I2C1->CR1 = I2C_CR1_PE;
}

static int i2c_wait(uint32_t flag)
{
    uint32_t t0 = DWT->CYCCNT;
    uint32_t limit = 1500u * g_cyc_per_us; /* 最多等 1.5 ms，超时立即复位外设防死锁 */
    while (!(I2C1->ISR & flag)) {
        if (I2C1->ISR & I2C_ISR_NACKF) {
            I2C1->ICR = I2C_ICR_NACKCF | I2C_ICR_STOPCF;
            return -1;
        }
        if ((DWT->CYCCNT - t0) > limit) {
            i2c_reset_bus();
            return -2;
        }
    }
    return 0;
}

static int i2c_read(uint8_t addr, uint8_t reg, uint8_t *b, int n)
{
    if (I2C1->ISR & I2C_ISR_BUSY) {
        i2c_reset_bus();
        if (I2C1->ISR & I2C_ISR_BUSY) return -2;
    }
    I2C1->ICR = 0x3F38u;
    I2C1->CR2 = ((uint32_t)addr << 1) | (1u << I2C_CR2_NBYTES_Pos) | I2C_CR2_START;
    if (i2c_wait(I2C_ISR_TXIS)) return -1;
    I2C1->TXDR = reg;
    if (i2c_wait(I2C_ISR_TC)) return -1;
    I2C1->CR2 = ((uint32_t)addr << 1) | I2C_CR2_RD_WRN | ((uint32_t)n << I2C_CR2_NBYTES_Pos) | I2C_CR2_AUTOEND | I2C_CR2_START;
    for (int i = 0; i < n; i++) {
        if (i2c_wait(I2C_ISR_RXNE)) return -1;
        b[i] = (uint8_t)I2C1->RXDR;
    }
    if (i2c_wait(I2C_ISR_STOPF)) return -1;
    I2C1->ICR = I2C_ICR_STOPCF;
    return 0;
}

static int i2c_write(uint8_t addr, uint8_t reg, uint8_t v)
{
    if (I2C1->ISR & I2C_ISR_BUSY) {
        i2c_reset_bus();
        if (I2C1->ISR & I2C_ISR_BUSY) return -2;
    }
    I2C1->ICR = 0x3F38u;
    I2C1->CR2 = ((uint32_t)addr << 1) | (2u << I2C_CR2_NBYTES_Pos) | I2C_CR2_AUTOEND | I2C_CR2_START;
    if (i2c_wait(I2C_ISR_TXIS)) return -1;
    I2C1->TXDR = reg;
    if (i2c_wait(I2C_ISR_TXIS)) return -1;
    I2C1->TXDR = v;
    if (i2c_wait(I2C_ISR_STOPF)) return -1;
    I2C1->ICR = I2C_ICR_STOPCF;
    return 0;
}

static bool imu_setup_stream(void)
{
    /* 若裸板引脚被外部硬拉低，跳过 I2C 探测（0 µs 快速回退，绝不阻塞会话启动） */
    if (!GET(IMU_SCL) || !GET(IMU_SDA)) {
        I2C1->CR1 = 0;
        return false;
    }
    i2c_reset_bus();
    if (I2C1->ISR & I2C_ISR_BUSY) {
        I2C1->CR1 = 0;
        return false;
    }
    uint8_t who = 0;
    if (i2c_read(0x6Au, 0x0Fu, &who, 1) || who != 0x6Au) {
        I2C1->CR1 = 0;
        return false;
    }
    /* CTRL3_C(0x12)=0x44: BDU=1, IF_INC=1
     * CTRL1_XL(0x10)=0x4C: 104 Hz, ±8 g (0.244 mg/LSB)
     * CTRL2_G(0x11)=0x48:  104 Hz, ±1000 dps (35 mdps/LSB)，严格对齐 host/v12_imu.py PROFILE */
    if (i2c_write(0x6Au, 0x12u, 0x44u)) return false;
    if (i2c_write(0x6Au, 0x10u, 0x4Cu)) return false;
    if (i2c_write(0x6Au, 0x11u, 0x48u)) return false;
    return true;
}

/* 非阻塞硬件 I2C1 采样状态机：每次调用仅推进 1 个硬件寄存器事件（< 0.5 µs），
 * 让 400 kHz I2C 字节移位完全在 DRDY_A 等待窗后台并发完成，彻底消除 16CH@2000SPS 阻塞漏采与批次量化。 */
typedef enum {
    IMU_NB_IDLE = 0,
    IMU_NB_ST_TX,
    IMU_NB_ST_TC,
    IMU_NB_ST_RX,
    IMU_NB_ST_STOP,
    IMU_NB_DAT_TX,
    IMU_NB_DAT_TC,
    IMU_NB_DAT_RX,
    IMU_NB_DAT_STOP,
} imu_nb_state_t;

static struct {
    imu_nb_state_t st;
    uint8_t        status_reg;
    uint8_t        idx;
    uint8_t        raw[12];
    int16_t        out6[6];
    uint64_t       last_poll_us;
    uint64_t       op_start_us;
    uint64_t       sample_ts_us;
    uint16_t       read_us;
    bool           ready;
} g_imu_nb;

static void imu_nb_reset(uint64_t now_us)
{
    memset(&g_imu_nb, 0, sizeof(g_imu_nb));
    g_imu_nb.last_poll_us = now_us;
}

static void imu_nb_step(bool enabled)
{
    if (!enabled) {
        if (g_imu_nb.st != IMU_NB_IDLE) {
            i2c_reset_bus();
            g_imu_nb.st = IMU_NB_IDLE;
        }
        return;
    }

    uint64_t now = clock_us();
    uint32_t isr = I2C1->ISR;
    if (g_imu_nb.st != IMU_NB_IDLE) {
        if (isr & I2C_ISR_NACKF) {
            I2C1->ICR = I2C_ICR_NACKCF | I2C_ICR_STOPCF;
            g_imu_nb.st = IMU_NB_IDLE;
            g_imu_nb.last_poll_us = now;
            return;
        }
        if (now - g_imu_nb.op_start_us > 2000u) {
            i2c_reset_bus();
            g_imu_nb.st = IMU_NB_IDLE;
            g_imu_nb.last_poll_us = now;
            return;
        }
    }

    switch (g_imu_nb.st) {
    case IMU_NB_IDLE:
        if (g_imu_nb.ready || (now - g_imu_nb.last_poll_us < 2400u)) return;
        if (isr & I2C_ISR_BUSY) {
            i2c_reset_bus();
            g_imu_nb.last_poll_us = now;
            return;
        }
        I2C1->ICR = 0x3F38u;
        I2C1->CR2 = (0x6Au << 1) | (1u << I2C_CR2_NBYTES_Pos) | I2C_CR2_START;
        g_imu_nb.op_start_us = now;
        g_imu_nb.st = IMU_NB_ST_TX;
        break;
    case IMU_NB_ST_TX:
        if (isr & I2C_ISR_TXIS) {
            I2C1->TXDR = 0x1Eu;
            g_imu_nb.st = IMU_NB_ST_TC;
        }
        break;
    case IMU_NB_ST_TC:
        if (isr & I2C_ISR_TC) {
            I2C1->CR2 = (0x6Au << 1) | I2C_CR2_RD_WRN | (1u << I2C_CR2_NBYTES_Pos) | I2C_CR2_AUTOEND | I2C_CR2_START;
            g_imu_nb.st = IMU_NB_ST_RX;
        }
        break;
    case IMU_NB_ST_RX:
        if (isr & I2C_ISR_RXNE) {
            g_imu_nb.status_reg = (uint8_t)I2C1->RXDR;
            g_imu_nb.st = IMU_NB_ST_STOP;
        }
        break;
    case IMU_NB_ST_STOP:
        if (isr & I2C_ISR_STOPF) {
            I2C1->ICR = I2C_ICR_STOPCF;
            g_imu_nb.last_poll_us = now;
            if ((g_imu_nb.status_reg & 0x03u) != 0x03u) {
                g_imu_nb.st = IMU_NB_IDLE;
            } else {
                I2C1->ICR = 0x3F38u;
                I2C1->CR2 = (0x6Au << 1) | (1u << I2C_CR2_NBYTES_Pos) | I2C_CR2_START;
                g_imu_nb.sample_ts_us = now;
                g_imu_nb.op_start_us = now;
                g_imu_nb.idx = 0u;
                g_imu_nb.st = IMU_NB_DAT_TX;
            }
        }
        break;
    case IMU_NB_DAT_TX:
        if (isr & I2C_ISR_TXIS) {
            I2C1->TXDR = 0x22u;
            g_imu_nb.st = IMU_NB_DAT_TC;
        }
        break;
    case IMU_NB_DAT_TC:
        if (isr & I2C_ISR_TC) {
            I2C1->CR2 = (0x6Au << 1) | I2C_CR2_RD_WRN | (12u << I2C_CR2_NBYTES_Pos) | I2C_CR2_AUTOEND | I2C_CR2_START;
            g_imu_nb.st = IMU_NB_DAT_RX;
        }
        break;
    case IMU_NB_DAT_RX:
        if (isr & I2C_ISR_RXNE) {
            g_imu_nb.raw[g_imu_nb.idx++] = (uint8_t)I2C1->RXDR;
            if (g_imu_nb.idx >= 12u) g_imu_nb.st = IMU_NB_DAT_STOP;
        }
        break;
    case IMU_NB_DAT_STOP:
        if (isr & I2C_ISR_STOPF) {
            I2C1->ICR = I2C_ICR_STOPCF;
            for (int i = 0; i < 6; i++) {
                g_imu_nb.out6[i] = (int16_t)((uint16_t)g_imu_nb.raw[2 * i] | ((uint16_t)g_imu_nb.raw[2 * i + 1] << 8));
            }
            uint64_t dt = now - g_imu_nb.sample_ts_us;
            g_imu_nb.read_us = (dt > 8999u) ? 8999u : (uint16_t)dt;
            g_imu_nb.ready = true;
            g_imu_nb.st = IMU_NB_IDLE;
        }
        break;
    }
}

/* ---------- LINK SPI3（8 MHz 主机，发 280B 帧同时收 16B 命令头） ---------- */
static bool link_exchange(c08b_link_tx_t *tx, c08b_link_rx_t *rx_out, bool *got_valid_rx)
{
    *got_valid_rx = false;
    if (!GET(LINK_RDY)) return false;
    c08b_link_tx_seal(tx);
    g_tx_frame = *tx;

    const uint8_t *p_tx = (const uint8_t *)tx;
    uint8_t rx_buf[sizeof(c08b_link_rx_t)];
    SET(LINK_CS, 0);
    delay_us(2);
    for (size_t i = 0; i < sizeof(c08b_link_tx_t); i++) {
        uint8_t b = spi_xfer(SPI3, p_tx[i]);
        if (i < sizeof(rx_buf)) rx_buf[i] = b;
    }
    delay_us(2);
    SET(LINK_CS, 1);

    c08b_link_rx_t cand;
    memcpy(&cand, rx_buf, sizeof(cand));
    if (c08b_link_rx_ok(&cand)) {
        *rx_out = cand;
        g_last_rx = cand;
        *got_valid_rx = true;
    }
    return true;
}

/* ---------- 会话运行上下文 ---------- */
typedef struct {
    bool            active;
    bool            is_synth;
    uint8_t         active_mode;
    uint8_t         nrf_flags;
    c08b_afe_mode_t afe_mode;
    c08b_fault_t    fault;
    uint16_t        fs_hz;
    uint8_t         id_a, id_b;
    bool            imu_ok;
    bool            avdd_ok;
    bool            sent_session_start;
    bool            has_carry;
    uint32_t        carry_missed;
    uint64_t        carry_ts;
    uint8_t         carry_slot[C08B_RAW_SLOT_BYTES];
    uint32_t        last_cmd_epoch;
    uint32_t        produced;
    uint32_t        dropped;
    uint16_t        bad_status;
    uint16_t        drdy_desync;
    uint32_t        min_interval_us;
    uint64_t        last_sample_us;
    uint64_t        next_synth_us;
    uint32_t        last_imu_ms;
} session_ctx_t;

static session_ctx_t g_sess;
static uint8_t         g_reg_ovr_set[2][0x1A];
static uint8_t         g_reg_ovr_val[2][0x1A];
static c08b_reg_reply_t g_reg_reply;

static uint8_t recount_reg_overrides(c08b_afe_mode_t mode)
{
    uint8_t n = 0;
    int nchips = (mode == AFE_16CH) ? 2 : 1;
    uint8_t max_a = (mode == AFE_2CH) ? 0x0Bu : 0x19u;
    for (int c = 0; c < nchips; c++) {
        for (uint8_t a = 0x01u; a <= max_a; a++) {
            if (g_reg_ovr_set[c][a]) n++;
        }
    }
    return n;
}

static void apply_ads1292_overrides(
    uint8_t base_mode,
    const uint8_t ovr_set[2][0x1A], const uint8_t ovr_val[2][0x1A],
    uint8_t cfg[0x0C], uint8_t mask[0x0C], uint8_t *rld_step2)
{
    for (uint8_t a = 0x01u; a <= 0x0Bu; a++) {
        if (!ovr_set[0][a]) continue;
        uint8_t vm = 0xFFu, v = ovr_val[0][a];
        if (!c08b_validate_reg_write(AFE_2CH, 0u, a, v, &vm)) continue;
        if (a == 0x06u) {
            if ((v & 0x20u) != 0u) {
                cfg[0x06] = 0x20u; /* 第 1 步仍只开 PDB_RLD 预热 >=150 ms */
                if (rld_step2) *rld_step2 = v;
            } else {
                cfg[0x06] = v;
                if (rld_step2) *rld_step2 = 0u;
            }
        } else if (a == 0x02u && base_mode == C08B_MODE_TST1) {
            cfg[0x02] = (uint8_t)(v | 0x03u); /* TST1 保持内部 1Hz 测试源开启 */
            mask[0x02] = vm;
        } else if ((a == 0x04u || a == 0x05u) &&
                   (base_mode == C08B_MODE_TST1 || base_mode == C08B_MODE_SHT1) &&
                   (v & 0x87u) == 0u) {
            /* 在线调增益 (MUX=000) 后运行 TST1/SHT1 标定时，保留 PGA 增益覆盖并维持内部方波/短接多路器 */
            cfg[a] = (uint8_t)((v & 0xF0u) | (base_mode == C08B_MODE_TST1 ? 0x05u : 0x01u));
            mask[a] = vm;
        } else {
            cfg[a] = v;
            mask[a] = vm;
        }
    }
}

static void apply_ads1298_overrides(
    uint8_t base_mode, c08b_afe_mode_t mode, int chip_idx,
    const uint8_t ovr_set[2][0x1A], const uint8_t ovr_val[2][0x1A],
    uint8_t cfg[0x1A], uint8_t mask[0x1A],
    uint8_t *cfg3_step2, uint8_t *rld_p_step2, uint8_t *rld_n_step2)
{
    for (uint8_t a = 0x01u; a <= 0x19u; a++) {
        if (!ovr_set[chip_idx][a]) continue;
        uint8_t vm = 0xFFu, v = ovr_val[chip_idx][a];
        if (!c08b_validate_reg_write(mode, (uint8_t)chip_idx, a, v, &vm)) continue;
        if (a == 0x03u) {
            cfg[0x03] = 0xC0u; /* 第 1 步先锁定 2.40V 基准预热 */
            if ((v & 0x04u) != 0u) {
                if (cfg3_step2) *cfg3_step2 = v;
            } else {
                if (cfg3_step2) *cfg3_step2 = 0u;
            }
        } else if (a == 0x0Du) {
            if (rld_p_step2) *rld_p_step2 = v;
        } else if (a == 0x0Eu) {
            if (rld_n_step2) *rld_n_step2 = v;
        } else if (a == 0x02u && base_mode == C08B_MODE_TST1) {
            cfg[0x02] = (uint8_t)(v | 0x10u); /* TST1 保持双片 INT_TEST=1 */
            mask[0x02] = vm;
        } else if (a >= 0x05u && a <= 0x0Cu &&
                   (base_mode == C08B_MODE_TST1 || base_mode == C08B_MODE_SHT1) &&
                   (v & 0x87u) == 0u) {
            /* 在线调增益 (MUX=000) 后运行 TST1/SHT1 标定时，保留 PGA 增益覆盖并维持内部方波(0x05)/短接(0x01) */
            cfg[a] = (uint8_t)((v & 0xF0u) | (base_mode == C08B_MODE_TST1 ? 0x05u : 0x01u));
            mask[a] = vm;
        } else {
            cfg[a] = v;
            mask[a] = vm;
        }
    }
    /* 若 CONFIG3 覆盖关闭了 PD_RLD(bit2=0)，无论 0x0D/0x0E 顺序如何，第 2 步 RLD 选通必须同步清零 */
    if (cfg3_step2 && (*cfg3_step2 & 0x04u) == 0u) {
        if (rld_p_step2) *rld_p_step2 = 0u;
        if (rld_n_step2) *rld_n_step2 = 0u;
    }
}

static void session_stop(c08b_fault_t reason)
{
    afe_safe_off();
    imu_nb_step(false);
    g_sess.active = false;
    g_sess.is_synth = false;
    g_sess.has_carry = false;
    g_sess.active_mode = C08B_MODE_IDLE;
    if (reason != C08B_FAULT_NONE) g_sess.fault = reason;
}

static void fill_tx_telemetry(c08b_link_tx_t *tx)
{
    memset(tx, 0, sizeof(*tx));
    tx->afe_mode = (uint8_t)g_sess.afe_mode;
    uint8_t sf = 0;
    if (g_sess.active) sf |= C08B_SF_ACTIVE;
    if (MAKO_BENCH_MEASURED) sf |= C08B_SF_BENCH_MEAS;
    if (l432_vbus_present()) sf |= C08B_SF_L432_VBUS;
    if (g_sess.avdd_ok) sf |= C08B_SF_AVDD_OK;
    if (g_sess.imu_ok) sf |= C08B_SF_IMU_OK;
    tx->state_flags = sf;
    tx->fault = (uint8_t)g_sess.fault;
    tx->produced = g_sess.produced;
    tx->dropped = g_sess.dropped;
    tx->bad_status = g_sess.bad_status;
    tx->drdy_desync = g_sess.drdy_desync;
    tx->min_interval_us_sat = (g_sess.produced < 2u || g_sess.min_interval_us > 0xFFFEu)
                                  ? 0xFFFFu : (uint16_t)g_sess.min_interval_us;
    tx->id_a = g_sess.id_a;
    tx->id_b = g_sess.id_b;
    tx->active_mode = g_sess.active_mode;
    tx->ack_epoch_lo = (uint16_t)g_sess.last_cmd_epoch;
    c08b_link_tx_put_reg_reply(tx, &g_reg_reply);
}

/* 拉高 ANA_EN 等待 U10 反相器建立后，执行两轮 SPIS1 心跳握手：
 * 第 1 轮排空 nRF 在 ANA_EN=0 期间预装的旧 OE_OFF=1 帧；
 * 第 2 轮验证 nRF 实测 OE_N==0 且 VBUS==0，杜绝首帧回传旧 OE_OFF=1 误杀自身。 */
static c08b_fault_t sync_nrf_interlock_after_ana_en(bool *abort_by_stop)
{
    static c08b_link_tx_t hb;
    c08b_link_rx_t rx;
    bool got_rx = false;
    *abort_by_stop = false;

    for (int pass = 0; pass < 2; pass++) {
        uint32_t t0 = g_ms;
        while (!GET(LINK_RDY)) {
            if (l432_vbus_present()) return C08B_FAULT_INTERLOCK;
            if (g_ms - t0 > 25u)     return C08B_FAULT_INTERLOCK;
            (void)clock_us();
        }
        fill_tx_telemetry(&hb);
        hb.sample_count = 0;
        if (!link_exchange(&hb, &rx, &got_rx) || !got_rx) {
            return C08B_FAULT_INTERLOCK;
        }
        g_sess.nrf_flags = rx.nrf_flags;
        if (rx.cmd_epoch != g_sess.last_cmd_epoch &&
            (rx.req_mode == C08B_MODE_STOP || rx.req_mode == C08B_MODE_IDLE)) {
            g_sess.last_cmd_epoch = rx.cmd_epoch;
            *abort_by_stop = true;
            return C08B_FAULT_NONE;
        }
        if (rx.nrf_flags & C08B_NF_VBUS_INTERLOCK) {
            return C08B_FAULT_INTERLOCK;
        }
        if (pass == 0) {
            delay_ms(5); /* 等 nRF 用新鲜的 OE_N==0 电平重装 SPIS1 */
        } else if (rx.nrf_flags & C08B_NF_OE_OFF) {
            return C08B_FAULT_INTERLOCK;
        }
    }
    return C08B_FAULT_NONE;
}

/* 仅在确认非 ADS1298 (g_sess.id_a != 0x92u) 后调用：
 * 2ch-ads1292 板上 J2.7(对 PA8/ADS_RESET) 为 NC，J2.6(对 PA1/ADS_PWDN) 经 R31 接 ADS1292 Pin15(PWDN/RESET)。
 * 按 TI SBAS502C §10.1 Fig.74 & §8.5.1.8，20 µs 低脉冲 (>=7.81 µs 且 << 4000 µs 掉电阈值)
 * 仅复位数字核与 SPI 状态机，不进 Power-Down 亦不泄放 VCAP1，随后等待 >= 18 t_CLK (100 µs)。 */
static void pulse_ads1292_pwdn_reset(void)
{
    SET(ADS_PWDN, 0);
    delay_us(C08B_ADS1292_RESET_LOW_US);
    SET(ADS_PWDN, 1);
    delay_us(C08B_ADS1292_RESET_SETTLE_US);
}

/* 启动真实 AFE 会话，或执行 PRB1 探测 / RREG 在线回读 / WREG 安全写核（仅在双硬件锁显式放行且无 VBUS 互锁时可达） */
static c08b_fault_t start_real_afe(
    uint8_t req_mode, uint16_t fs_hz, uint8_t nrf_flags, uint16_t cmd_seq,
    uint8_t chip_sel, uint8_t reg_addr, uint8_t reg_val, bool *aborted)
{
    *aborted = false;
    if (l432_vbus_present() || (nrf_flags & C08B_NF_VBUS_INTERLOCK))
        return C08B_FAULT_INTERLOCK;

    /* 先用 1 MHz 安全速率（BR=3: 16MHz/16=1MHz）上电探测 ID，兼顾 ADS1292 <=1.024MHz 约束 */
    spi_init(SPI1, 3u, 1);
    SET(ANA_EN, 1);
    delay_ms(60); /* 等 U10 反相器与 OE_N RC 建立 */
    if (l432_vbus_present()) { afe_safe_off(); return C08B_FAULT_INTERLOCK; }

    c08b_fault_t sync_err = sync_nrf_interlock_after_ana_en(aborted);
    if (sync_err != C08B_FAULT_NONE || *aborted) {
        afe_safe_off();
        return sync_err;
    }

    /* 第 1 步（保护 ADS1298 22µF VCAP1）：保持 ADS_PWDN=1、ADS_RESET=1 等满 >=1050 ms，
     * 先仅对 ADS_RESET(PA8 -> J_AFE.14 -> D20.7) 发 20 µs 低脉冲并读 ID。
     * 若 id_a == 0x92 (ADS1298)，PA8 已完成复位且全程未拉低 PA1(ADS_PWDN)。
     * 第 2 步（复位 ADS1292）：2ch-ads1292 板上 J2.7 为 NC，J2.6(对 PA1/ADS_PWDN) 接 Pin15(PWDN/RESET)；
     * 仅当 id_a != 0x92 时对 PA1 发 20 µs (<<4000 µs 掉电阈值) 纯数字复位脉冲并重读 ID！ */
    SET(ADS_PWDN, 1);
    SET(ADS_RESET, 1);
    for (uint32_t waited = 0; waited < C08B_ADS1292_POR_WAIT_MS; waited += 10u) {
        delay_ms(10u);
        if (l432_vbus_present()) { afe_safe_off(); return C08B_FAULT_INTERLOCK; }
        if (GET(LINK_RDY)) {
            static c08b_link_tx_t hb;
            c08b_link_rx_t rx;
            bool got_rx = false;
            fill_tx_telemetry(&hb);
            if (link_exchange(&hb, &rx, &got_rx) && got_rx) {
                g_sess.nrf_flags = rx.nrf_flags;
                if (rx.nrf_flags & (C08B_NF_VBUS_INTERLOCK | C08B_NF_OE_OFF)) {
                    afe_safe_off(); return C08B_FAULT_INTERLOCK;
                }
                if (rx.cmd_epoch != g_sess.last_cmd_epoch &&
                    (rx.req_mode == C08B_MODE_STOP || rx.req_mode == C08B_MODE_IDLE)) {
                    g_sess.last_cmd_epoch = rx.cmd_epoch;
                    *aborted = true;
                    afe_safe_off();
                    return C08B_FAULT_NONE;
                }
            }
        }
    }
    SET(ADS_RESET, 0);
    delay_us(20u);
    SET(ADS_RESET, 1);
    delay_ms(2u);

    ads_cmd(0, ADS_SDATAC);
    ads_cmd(1, ADS_SDATAC);
    g_sess.id_a = ads_rreg(0, 0x00u);
    g_sess.id_b = ads_rreg(1, 0x00u);
    if (g_sess.id_a != 0x92u) {
        pulse_ads1292_pwdn_reset();
        ads_cmd(0, ADS_SDATAC);
        g_sess.id_a = ads_rreg(0, 0x00u);
    }
    c08b_afe_mode_t mode = c08b_afe_detect(g_sess.id_a, g_sess.id_b);
    g_sess.afe_mode = mode;
    if (mode == AFE_NONE) {
        afe_safe_off();
        return C08B_FAULT_AFE_ID;
    }

    /* PRB1 只读探测：识别出 2/8/16CH 后立刻关断 AFE 供电返回 */
    if (req_mode == C08B_MODE_PRB1) {
        afe_safe_off();
        return C08B_FAULT_NONE;
    }

    bool is_reg_op = (req_mode == C08B_MODE_RREG || req_mode == C08B_MODE_WREG);
    uint8_t base_mode = is_reg_op ? C08B_MODE_EXT1 : req_mode;

    if (req_mode == C08B_MODE_RREG && !c08b_validate_reg_read(mode, chip_sel, reg_addr)) {
        afe_safe_off();
        return C08B_FAULT_ARG;
    }

    int w_first = 0, w_last = -1;
    uint8_t w_vm[2] = {0xFFu, 0xFFu};
    uint8_t eff_set[2][0x1A], eff_val[2][0x1A];
    memcpy(eff_set, g_reg_ovr_set, sizeof(eff_set));
    memcpy(eff_val, g_reg_ovr_val, sizeof(eff_val));
    if (req_mode == C08B_MODE_WREG) {
        if (chip_sel > C08B_CHIP_BOTH || (chip_sel == C08B_CHIP_U2 && mode != AFE_16CH)) {
            afe_safe_off();
            return C08B_FAULT_ARG;
        }
        w_first = (chip_sel == C08B_CHIP_U2) ? 1 : 0;
        w_last  = (chip_sel == C08B_CHIP_U1) ? 0 : ((mode == AFE_16CH) ? 1 : 0);
        for (int c = w_first; c <= w_last; c++) {
            if (!c08b_validate_reg_write(mode, (uint8_t)c, reg_addr, reg_val, &w_vm[c])) {
                afe_safe_off();
                return C08B_FAULT_ARG;
            }
            /* 先写入局部候选覆盖表，统一经两步 150 ms 基准/RLD 预热状态机下发并校验，成功后再原子提交全局表 */
            eff_set[c][reg_addr] = 1u;
            eff_val[c][reg_addr] = reg_val;
        }
    }

    if (mode == AFE_2CH) {
        /* PA4(AVDD_SENSE) 先 10 µs P_DOWN 泄放寄生电容，再保持纯高阻输入 P_NONE 判读 3.0V */
        pin_mode(DRDY_B_PORT, DRDY_B_PIN, M_IN, 0, P_DOWN, 0);
        delay_us(C08B_PA4_BLEED_US);
        pin_mode(DRDY_B_PORT, DRDY_B_PIN, M_IN, 0, P_NONE, 0);
        delay_us(50u);
        g_sess.avdd_ok = (GET(DRDY_B) != 0);
        if (!g_sess.avdd_ok) { afe_safe_off(); return C08B_FAULT_INTERLOCK; }

        uint8_t cfg[0x0C], mask[0x0C], rld_step2 = 0;
        if (!c08b_build_ads1292_regs(base_mode, fs_hz, cfg, mask, &rld_step2)) {
            afe_safe_off(); return C08B_FAULT_ARG;
        }
        apply_ads1292_overrides(base_mode, eff_set, eff_val, cfg, mask, &rld_step2);
        if (ads_write_verify(0, cfg, mask, 0x01, 0x0B) != 0) {
            afe_safe_off(); return C08B_FAULT_READBACK;
        }
        /* 两步开 RLD：先等 PDB_RLD 与外部 C7(10 µF) 预热满 >=150 ms，再合上电极反馈 */
        for (uint32_t waited = 0; waited < C08B_ADS_RLD_WARMUP_US; waited += 5000u) {
            delay_us(5000u);
            if (l432_vbus_present() || !GET(DRDY_B)) { afe_safe_off(); return C08B_FAULT_INTERLOCK; }
        }
        if (rld_step2) {
            ads_wreg(0, 0x06u, rld_step2);
            if ((ads_rreg(0, 0x06u) & 0x3Fu) != rld_step2) {
                afe_safe_off(); return C08B_FAULT_READBACK;
            }
        }
        if (is_reg_op) {
            uint8_t rb0 = ads_rreg(0, reg_addr);
            if (req_mode == C08B_MODE_WREG) {
                if ((rb0 & w_vm[0]) != (reg_val & w_vm[0])) {
                    afe_safe_off(); return C08B_FAULT_READBACK;
                }
                memcpy(g_reg_ovr_set, eff_set, sizeof(g_reg_ovr_set));
                memcpy(g_reg_ovr_val, eff_val, sizeof(g_reg_ovr_val));
            }
            g_reg_reply.seq       = cmd_seq;
            g_reg_reply.addr      = reg_addr;
            g_reg_reply.val_a     = rb0;
            g_reg_reply.val_b     = 0u;
            g_reg_reply.ovr_count = recount_reg_overrides(mode);
            g_reg_reply.valid     = true;
            afe_safe_off();
            return C08B_FAULT_NONE;
        }
        ads_cmd(0, ADS_RDATAC);
    } else {
        /* 8CH / 16CH ADS1298（LM27762 ±2.5V 双极供电，Pin 60 RLDREF 硬连 AGND，v0.01 Pin 62 RLDIN 接 +2.5V）：
         * 切 SPI1 到 4.000 MHz（BR=1: 16MHz/4=4MHz），DRDY_B 开上拉防 8CH 悬空 */
        pin_mode(DRDY_B_PORT, DRDY_B_PIN, M_IN, 0, P_UP, 0);
        spi_init(SPI1, 1u, 1);
        g_sess.avdd_ok = true;
        int nchips = (mode == AFE_16CH) ? 2 : 1;
        uint8_t cfg3_step2[2]  = {0, 0};
        uint8_t rld_p_step2[2] = {0, 0};
        uint8_t rld_n_step2[2] = {0, 0};
        for (int c = 0; c < nchips; c++) {
            uint8_t cfg[0x1A], mask[0x1A], rld_def = 0;
            if (!c08b_build_ads1298_regs(base_mode, fs_hz, c, cfg, mask, &cfg3_step2[c], &rld_def)) {
                afe_safe_off(); return C08B_FAULT_ARG;
            }
            rld_p_step2[c] = rld_def;
            rld_n_step2[c] = rld_def;
            apply_ads1298_overrides(base_mode, mode, c, eff_set, eff_val, cfg, mask, &cfg3_step2[c], &rld_p_step2[c], &rld_n_step2[c]);
            if (ads_write_verify(c, cfg, mask, 0x01, 0x19) != 0) {
                afe_safe_off(); return C08B_FAULT_READBACK;
            }
        }
        /* 等满 >=150 ms 让内部 2.40V 基准稳定，随后对 U1 执行第 2 步 RLD 启用（RLDREF_INT/RLD_MEAS 保持 0！） */
        for (uint32_t waited = 0; waited < C08B_ADS_RLD_WARMUP_US; waited += 5000u) {
            delay_us(5000u);
            if (l432_vbus_present()) { afe_safe_off(); return C08B_FAULT_INTERLOCK; }
        }
        if (cfg3_step2[0] || eff_set[0][0x0Du] || eff_set[0][0x0Eu]) {
            ads_wreg(0, 0x0Du, rld_p_step2[0]);
            ads_wreg(0, 0x0Eu, rld_n_step2[0]);
            if (cfg3_step2[0]) ads_wreg(0, 0x03u, cfg3_step2[0]);
            if (ads_rreg(0, 0x0Du) != rld_p_step2[0] ||
                ads_rreg(0, 0x0Eu) != rld_n_step2[0] ||
                (cfg3_step2[0] && (ads_rreg(0, 0x03u) & 0xFEu) != cfg3_step2[0])) {
                afe_safe_off(); return C08B_FAULT_READBACK;
            }
        }
        if (is_reg_op) {
            uint8_t rb0 = ads_rreg(0, reg_addr);
            uint8_t rb1 = (mode == AFE_16CH) ? ads_rreg(1, reg_addr) : 0u;
            if (req_mode == C08B_MODE_WREG) {
                for (int c = w_first; c <= w_last; c++) {
                    uint8_t rbc = (c == 0) ? rb0 : rb1;
                    /* 若写 0x0D/0x0E 但当前 CONFIG3.PD_RLD=0，第 2 步状态机保持硬件寄存器为 0，待下次开 EXR1/PD_RLD=1 时一并合上；
                     * 此时单独下发目标寄存器回读校验芯片 I/O 完好性，校验后再退回安全零态 */
                    if ((reg_addr == 0x0Du || reg_addr == 0x0Eu) && c == 0 && cfg3_step2[0] == 0u && reg_val != 0u) {
                        ads_wreg(0, reg_addr, reg_val);
                        rbc = ads_rreg(0, reg_addr);
                        ads_wreg(0, reg_addr, 0u);
                        if (c == 0) rb0 = rbc;
                    }
                    if ((rbc & w_vm[c]) != (reg_val & w_vm[c])) {
                        afe_safe_off(); return C08B_FAULT_READBACK;
                    }
                }
                memcpy(g_reg_ovr_set, eff_set, sizeof(g_reg_ovr_set));
                memcpy(g_reg_ovr_val, eff_val, sizeof(g_reg_ovr_val));
            }
            g_reg_reply.seq       = cmd_seq;
            g_reg_reply.addr      = reg_addr;
            g_reg_reply.val_a     = rb0;
            g_reg_reply.val_b     = rb1;
            g_reg_reply.ovr_count = recount_reg_overrides(mode);
            g_reg_reply.valid     = true;
            afe_safe_off();
            return C08B_FAULT_NONE;
        }
        ads_cmd(0, ADS_RDATAC);
        if (mode == AFE_16CH) ads_cmd(1, ADS_RDATAC);
    }

    g_sess.imu_ok = imu_setup_stream();
    imu_nb_reset(clock_us());
    SET(ADS_START, 1);
    return C08B_FAULT_NONE;
}

static void handle_rx_cmd(const c08b_link_rx_t *rx)
{
    g_sess.nrf_flags = rx->nrf_flags;
    if ((rx->nrf_flags & C08B_NF_IMU_SUBSCRIBED) == 0u) {
        imu_nb_step(false);
    }
    bool nrf_interlock = (rx->nrf_flags & (C08B_NF_VBUS_INTERLOCK | C08B_NF_OE_OFF)) != 0;
    /* 无论命令序号是否更新，一旦 nRF 侧报告 VBUS 或 OE_N 互锁断开，运行中的真实 AFE 必须立刻断电并报 INTERLOCK(3) */
    if (g_sess.active && !g_sess.is_synth && nrf_interlock) {
        session_stop(C08B_FAULT_INTERLOCK);
        if (rx->req_mode == C08B_MODE_STOP || rx->req_mode == C08B_MODE_IDLE) {
            g_sess.last_cmd_epoch = rx->cmd_epoch;
        }
        return;
    }
    if (rx->cmd_epoch == g_sess.last_cmd_epoch) return;
    g_sess.last_cmd_epoch = rx->cmd_epoch;

    if (rx->req_mode == C08B_MODE_STOP || rx->req_mode == C08B_MODE_IDLE) {
        bool keep_interlock = (g_sess.fault == C08B_FAULT_INTERLOCK) &&
                              (l432_vbus_present() || nrf_interlock);
        session_stop(keep_interlock ? C08B_FAULT_INTERLOCK : C08B_FAULT_NONE);
        if (!keep_interlock) g_sess.fault = C08B_FAULT_NONE;
        return;
    }

    if (rx->req_mode == C08B_MODE_CLRO) {
        bool keep_interlock = (g_sess.fault == C08B_FAULT_INTERLOCK) &&
                              (l432_vbus_present() || nrf_interlock);
        session_stop(keep_interlock ? C08B_FAULT_INTERLOCK : C08B_FAULT_NONE);
        if (!keep_interlock) g_sess.fault = C08B_FAULT_NONE;
        memset(g_reg_ovr_set, 0, sizeof(g_reg_ovr_set));
        memset(g_reg_ovr_val, 0, sizeof(g_reg_ovr_val));
        memset(&g_reg_reply, 0, sizeof(g_reg_reply));
        logf_("已清空全部运行时 ADS 寄存器覆盖项\n");
        return;
    }

    session_stop(C08B_FAULT_NONE);
    if (rx->req_mode == C08B_MODE_RREG || rx->req_mode == C08B_MODE_WREG) {
        g_reg_reply.valid = false;
    }
    uint16_t fs = rx->fs_hz ? rx->fs_hz : 1000u;
    bool unlocked = (MAKO_C08B_AFE_ENABLED != 0) && (MAKO_BENCH_MEASURED != 0);
    bool vbus = l432_vbus_present() || ((rx->nrf_flags & C08B_NF_VBUS_INTERLOCK) != 0);
    c08b_fault_t gate = c08b_gate_mode_request(rx->req_mode, fs, unlocked, vbus);
    if (gate != C08B_FAULT_NONE) {
        g_sess.fault = gate;
        logf_("拒绝启动模式 %u：故障码 %u\n", rx->req_mode, (unsigned)gate);
        return;
    }

    g_sess.fault = C08B_FAULT_NONE;
    g_sess.fs_hz = fs;
    if (rx->req_mode != C08B_MODE_PRB1 && rx->req_mode != C08B_MODE_RREG && rx->req_mode != C08B_MODE_WREG) {
        g_sess.produced = 0;
        g_sess.dropped = 0;
        g_sess.bad_status = 0;
        g_sess.drdy_desync = 0;
        g_sess.min_interval_us = 0xFFFFFFFFu;
        g_sess.last_sample_us = 0;
        g_sess.last_imu_ms = g_ms;
        g_sess.sent_session_start = false;
        g_sess.has_carry = false;
    }

    if (rx->req_mode == C08B_MODE_SYN1) {
        uint8_t sc = rx->synth_channels;
        g_sess.afe_mode = (sc == 2u) ? AFE_2CH : (sc == 8u) ? AFE_8CH : AFE_16CH;
        g_sess.is_synth = true;
        g_sess.active = true;
        g_sess.active_mode = C08B_MODE_SYN1;
        g_sess.imu_ok = imu_setup_stream();
        imu_nb_reset(clock_us());
        g_sess.next_synth_us = clock_us();
        logf_("启动 SYN1 合成流：%uCH @ %u Hz\n", (unsigned)g_sess.afe_mode, fs);
        return;
    }

    bool aborted = false;
    c08b_fault_t err = start_real_afe(
        rx->req_mode, fs, rx->nrf_flags, (uint16_t)rx->cmd_epoch,
        rx->synth_channels, rx->reg_addr, rx->reg_val, &aborted);
    if (err != C08B_FAULT_NONE) {
        g_sess.fault = err;
        logf_("启动真实 AFE 或寄存器操作失败：故障码 %u\n", (unsigned)err);
        return;
    }
    if (aborted || rx->req_mode == C08B_MODE_PRB1 ||
        rx->req_mode == C08B_MODE_RREG || rx->req_mode == C08B_MODE_WREG) {
        logf_("完成单次探测/寄存器操作或被 STOP 中止：mode=%u afe=%uCH\n", rx->req_mode, (unsigned)g_sess.afe_mode);
        return;
    }
    g_sess.is_synth = false;
    g_sess.active = true;
    g_sess.active_mode = rx->req_mode;
    logf_("启动真实流：%uCH 模式=%u @ %u Hz\n", (unsigned)g_sess.afe_mode, rx->req_mode, fs);
}

/* 采 1 个真实 AFE 样本槽（54 字节） */
static bool read_one_afe_slot(uint8_t slot[54], uint64_t *ts_out)
{
    bool imu_en = g_sess.imu_ok && ((g_sess.nrf_flags & C08B_NF_IMU_SUBSCRIBED) != 0u);
    uint32_t t0 = g_ms;
    while (GET(DRDY_A)) {
        if (l432_vbus_present()) { session_stop(C08B_FAULT_INTERLOCK); return false; }
        if (g_ms - t0 > 20u)     { session_stop(C08B_FAULT_DRDY_TO);   return false; }
        imu_nb_step(imu_en);
    }
    *ts_out = clock_us();
    memset(slot, 0, 54);

    if (g_sess.afe_mode == AFE_2CH) {
        if (!GET(DRDY_B)) {
            g_sess.avdd_ok = false;
            session_stop(C08B_FAULT_INTERLOCK);
            return false;
        }
        uint8_t raw9[9];
        cs_select(0, 0); delay_us(1);
        for (int i = 0; i < 9; i++) raw9[i] = spi_xfer(SPI1, 0x00u);
        delay_us(C08B_ADS_TSCCS_US); cs_select(0, 1);
        if ((raw9[0] & 0xF0u) != 0xC0u) g_sess.bad_status++;
        c08b_ads1292_map_f01_status(raw9, slot);
        memcpy(slot + 3, raw9 + 3, 6); /* CH1, CH2；CH3..CH8 保持 0 */
    } else {
        if (g_sess.afe_mode == AFE_16CH && GET(DRDY_B)) g_sess.drdy_desync++;
        cs_select(0, 0); delay_us(1);
        for (int i = 0; i < 27; i++) slot[i] = spi_xfer(SPI1, 0x00u);
        delay_us(2); cs_select(0, 1); delay_us(1);
        if ((slot[0] & 0xF0u) != 0xC0u) g_sess.bad_status++;

        if (g_sess.afe_mode == AFE_16CH) {
            if (!GET(DRDY_B)) g_sess.drdy_desync++;
            cs_select(1, 0); delay_us(1);
            for (int i = 0; i < 27; i++) slot[27 + i] = spi_xfer(SPI1, 0x00u);
            delay_us(2); cs_select(1, 1);
            if ((slot[27] & 0xF0u) != 0xC0u) g_sess.bad_status++;
        }
        imu_nb_step(imu_en);
    }

    /* 第一道安全铁闸：若 OE_N=1 三态缓冲 + R701/R702 下拉导致 MISO 读回 0x000000 坏状态头，
     * 立即切断 ANA_EN=0 并锁存 FAULT_BAD_FRAME(6)（或 VBUS INTERLOCK(3)），严禁把全零伪样本装入 SPI3 发送帧！ */
    if (!c08b_slot_status_valid(slot, g_sess.afe_mode)) {
        session_stop(l432_vbus_present() ? C08B_FAULT_INTERLOCK : C08B_FAULT_BAD_FRAME);
        return false;
    }

    uint32_t tw = DWT->CYCCNT;
    while (!GET(DRDY_A) && (DWT->CYCCNT - tw) < 80u * g_cyc_per_us) {}
    return true;
}

static void clock_and_gpio_init(void)
{
    /* 配置 STM32L432：HSI16(16MHz) -> PLL(16/1*8/2 = 64MHz HCLK)，VOS Range 1 + Flash 3WS；
     * 同时设 PPRE1=DIV4、PPRE2=DIV4 使 PCLK1=PCLK2 保持精确 16 MHz，确保 SPI1(4MHz/1MHz)、
     * SPI3(8MHz, 对齐 nRF52840 SPIS1 <=8MHz 上限) 与 I2C1(400kHz) 波特率零偏差。 */
    RCC->CR |= RCC_CR_HSION;
    while (!(RCC->CR & RCC_CR_HSIRDY)) {}
    RCC->APB1ENR1 |= RCC_APB1ENR1_PWREN;
    (void)RCC->APB1ENR1;
    PWR->CR1 = (PWR->CR1 & ~PWR_CR1_VOS) | PWR_CR1_VOS_0;
    while (PWR->SR2 & PWR_SR2_VOSF) {}
    FLASH->ACR = FLASH_ACR_PRFTEN | FLASH_ACR_ICEN | FLASH_ACR_DCEN | FLASH_ACR_LATENCY_3WS;
    while ((FLASH->ACR & FLASH_ACR_LATENCY) != FLASH_ACR_LATENCY_3WS) {}

    RCC->CR &= ~RCC_CR_PLLON;
    while (RCC->CR & RCC_CR_PLLRDY) {}
    RCC->PLLCFGR = RCC_PLLCFGR_PLLSRC_HSI | (8u << RCC_PLLCFGR_PLLN_Pos) | RCC_PLLCFGR_PLLREN;
    RCC->CR |= RCC_CR_PLLON;
    while (!(RCC->CR & RCC_CR_PLLRDY)) {}

    RCC->CFGR = RCC_CFGR_PPRE1_DIV4 | RCC_CFGR_PPRE2_DIV4 | RCC_CFGR_SW_PLL;
    while ((RCC->CFGR & RCC_CFGR_SWS) != RCC_CFGR_SWS_PLL) {}
    SystemCoreClockUpdate();
    g_cyc_per_us = SystemCoreClock / 1000000u;
    if (g_cyc_per_us == 0u) g_cyc_per_us = 64u;
    SysTick_Config(SystemCoreClock / 1000u);
    CoreDebug->DEMCR |= CoreDebug_DEMCR_TRCENA_Msk;
    DWT->CYCCNT = 0;
    DWT->CTRL |= DWT_CTRL_CYCCNTENA_Msk;
    RCC->AHB2ENR |= RCC_AHB2ENR_GPIOAEN | RCC_AHB2ENR_GPIOBEN | RCC_AHB2ENR_GPIOCEN | RCC_AHB2ENR_GPIOHEN;
    RCC->APB2ENR |= RCC_APB2ENR_SPI1EN;
    RCC->APB1ENR1 |= RCC_APB1ENR1_SPI3EN | RCC_APB1ENR1_I2C1EN;
    (void)RCC->APB1ENR1;

    OUT_INIT(CS_A, 1); OUT_INIT(CS_B, 1); OUT_INIT(ADS_START, 0);
    OUT_INIT(ADS_PWDN, 0); OUT_INIT(ADS_RESET, 0); OUT_INIT(ANA_EN, 0);
    OUT_INIT(LINK_CS, 1);
    pin_mode(DRDY_A_PORT, DRDY_A_PIN, M_IN, 0, P_NONE, 0);
    pin_mode(DRDY_B_PORT, DRDY_B_PIN, M_IN, 0, P_NONE, 0);
    pin_mode(AFE_GPIO3_PORT, AFE_GPIO3_PIN, M_IN, 0, P_DOWN, 0);
    pin_mode(LINK_RDY_PORT, LINK_RDY_PIN, M_IN, 0, P_DOWN, 0);
    pin_mode(IMU_INT1_PORT, IMU_INT1_PIN, M_IN, 0, P_NONE, 0);
    pin_mode(BOOT0_PORT, BOOT0_PIN, M_IN, 0, P_NONE, 0); /* PH3-BOOT0=VBUS_SENSE 只读 */
    pin_mode(SPI1_SCK_PORT, SPI1_SCK_PIN, M_AF, 5, P_NONE, 0);
    pin_mode(SPI1_MISO_PORT, SPI1_MISO_PIN, M_AF, 5, P_DOWN, 0);
    pin_mode(SPI1_MOSI_PORT, SPI1_MOSI_PIN, M_AF, 5, P_NONE, 0);
    pin_mode(LINK_SCK_PORT, LINK_SCK_PIN, M_AF, 6, P_NONE, 0);
    pin_mode(LINK_MISO_PORT, LINK_MISO_PIN, M_AF, 6, P_DOWN, 0);
    pin_mode(LINK_MOSI_PORT, LINK_MOSI_PIN, M_AF, 6, P_NONE, 0);
    pin_mode(IMU_SCL_PORT, IMU_SCL_PIN, M_AF, 4, P_UP, 1); /* 内部弱上拉兜底：防未贴 R198/R199 时浮空锁死 BUSY */
    pin_mode(IMU_SDA_PORT, IMU_SDA_PIN, M_AF, 4, P_UP, 1);

    spi_init(SPI3, 0u, 0); /* PCLK1(16 MHz) / 2 = 8 MHz，模式 0 对接 nRF SPIS1 */
}

int main(void)
{
    clock_and_gpio_init();
    rtt_init();
    logf_("\nC08B L432 流式候选固件启动（HCLK=%lu MHz, AFE_LOCK=%d, BENCH_MEASURED=%d）\n",
          (unsigned long)(SystemCoreClock / 1000000u), MAKO_C08B_AFE_ENABLED, MAKO_BENCH_MEASURED);

    static c08b_link_tx_t tx;
    c08b_link_rx_t rx;
    bool got_rx = false;
    uint32_t last_hb_ms = 0;

    for (;;) {
        (void)clock_us();
        if (g_sess.active && !g_sess.is_synth && l432_vbus_present()) {
            session_stop(C08B_FAULT_INTERLOCK);
            last_hb_ms = g_ms - 20u;
        }

        if (!g_sess.active) {
            if (g_ms - last_hb_ms >= 20u) {
                last_hb_ms = g_ms;
                fill_tx_telemetry(&tx);
                tx.sample_count = 0;
                if (link_exchange(&tx, &rx, &got_rx) && got_rx) {
                    handle_rx_cmd(&rx);
                }
            }
            continue;
        }

        /* 采集中：2000 SPS 每批 2 帧（1 ms 一次，防 500 µs 周期超限）；500/1000 SPS 每批 4 帧 */
        uint8_t target_batch = (g_sess.fs_hz >= 2000u) ? 2u : 4u;
        uint32_t step_us = 1000000u / g_sess.fs_hz;
        uint32_t overrun_thresh_us = step_us + (step_us * 3u) / 5u; /* >= 1.6 * t_DR 判为硬件 DRDY 漏采 */
        bool imu_sub = (g_sess.nrf_flags & C08B_NF_IMU_SUBSCRIBED) != 0u;
        bool imu_en  = g_sess.imu_ok && imu_sub;

        if (g_sess.has_carry) {
            g_sess.dropped += g_sess.carry_missed;
            g_sess.produced += g_sess.carry_missed;
        }
        fill_tx_telemetry(&tx);
        tx.seq_first = g_sess.produced;

        for (uint8_t b = 0; b < target_batch; b++) {
            if (b == 0u && g_sess.has_carry) {
                memcpy(tx.samples[0], g_sess.carry_slot, C08B_RAW_SLOT_BYTES);
                tx.timestamp_us = g_sess.carry_ts;
                g_sess.last_sample_us = g_sess.carry_ts;
                tx.sample_count = 1u;
                g_sess.has_carry = false;
                continue;
            }

            uint64_t ts = 0;
            uint8_t slot_buf[C08B_RAW_SLOT_BYTES];
            if (g_sess.is_synth) {
                while (clock_us() < g_sess.next_synth_us) {
                    imu_nb_step(imu_en);
                }
                ts = g_sess.next_synth_us;
                g_sess.next_synth_us += step_us;
                c08b_fill_synth_slot(slot_buf, g_sess.afe_mode, g_sess.produced + tx.sample_count);
            } else {
                if (!read_one_afe_slot(slot_buf, &ts)) break;
            }

            if (g_sess.produced + tx.sample_count > 0u) {
                uint64_t dt = (ts > g_sess.last_sample_us) ? (ts - g_sess.last_sample_us) : 0u;
                if (dt < g_sess.min_interval_us) g_sess.min_interval_us = (uint32_t)dt;
                if (!g_sess.is_synth && dt >= overrun_thresh_us) {
                    uint32_t missed = (uint32_t)((dt + step_us / 2u) / step_us) - 1u;
                    if (missed == 0u) missed = 1u;
                    if (tx.sample_count == 0u) {
                        g_sess.dropped += missed;
                        g_sess.produced += missed;
                        tx.dropped = g_sess.dropped;
                        tx.seq_first = g_sess.produced;
                    } else {
                        /* 保持单帧内部序号严格连续：先发完已采连续样本，跳号样本暂存至下一帧首槽发出 */
                        memcpy(g_sess.carry_slot, slot_buf, C08B_RAW_SLOT_BYTES);
                        g_sess.carry_ts = ts;
                        g_sess.carry_missed = missed;
                        g_sess.has_carry = true;
                        break;
                    }
                }
            }

            memcpy(tx.samples[tx.sample_count], slot_buf, C08B_RAW_SLOT_BYTES);
            if (tx.sample_count == 0u) tx.timestamp_us = ts;
            g_sess.last_sample_us = ts;
            tx.sample_count++;
        }

        if (!g_sess.active) {
            /* 一旦采集中发生任何故障停机（BAD_FRAME/DRDY_TO/INTERLOCK），立即在下一轮发心跳上报故障码 */
            last_hb_ms = g_ms - 20u;
            continue;
        }
        if (tx.sample_count == 0u) continue;

        /* 收获后台非阻塞 I2C1 状态机就绪的 104 Hz IMU 样本（仅在主机订阅 IMU_DATA 时启动轮询） */
        imu_nb_step(imu_en);
        if (imu_sub && g_imu_nb.ready) {
            tx.imu_fresh = 1u;
            tx.imu_timestamp_us = g_imu_nb.sample_ts_us;
            tx.imu_read_us = g_imu_nb.read_us;
            memcpy(tx.imu_raw, g_imu_nb.out6, sizeof(tx.imu_raw));
            g_imu_nb.ready = false;
        } else if (imu_sub && g_sess.is_synth && !g_sess.imu_ok && (g_ms - g_sess.last_imu_ms >= 10u)) {
            g_sess.last_imu_ms = g_ms;
            tx.imu_fresh = 1u;
            tx.imu_timestamp_us = clock_us();
            tx.imu_read_us = 0u;
            tx.imu_raw[0] = (int16_t)(g_sess.produced & 0xFFu);
            tx.imu_raw[5] = 4096; /* 标称 +1 g @ ±8g (0.244 mg/LSB) */
        }

        uint8_t flags = g_sess.is_synth ? C08B_F01_SYNTHETIC : 0u;
        if (!g_sess.sent_session_start) {
            flags |= C08B_F01_SESSION_START;
            g_sess.sent_session_start = true;
        }
        tx.f01_flags = flags;
        g_sess.produced += tx.sample_count;
        tx.produced = g_sess.produced;
        tx.dropped = g_sess.dropped;
        tx.min_interval_us_sat = (g_sess.produced < 2u || g_sess.min_interval_us > 0xFFFEu)
                                      ? 0xFFFFu : (uint16_t)g_sess.min_interval_us;

        if (link_exchange(&tx, &rx, &got_rx)) {
            if (got_rx) handle_rx_cmd(&rx);
        } else {
            g_sess.dropped += tx.sample_count;
            /* 首包丢失时下次无法续接 seq=0，记入故障码停机 */
            if (flags & C08B_F01_SESSION_START) {
                session_stop(C08B_FAULT_LINK_DROP);
                last_hb_ms = g_ms - 20u;
            }
        }
    }
}

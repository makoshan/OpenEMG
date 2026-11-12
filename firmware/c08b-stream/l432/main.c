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
 *        Pin 60(RLDREF)/Pin 62(RLDIN) 硬连 AGND 故严格保持 RLDREF_INT=0（两步 0xC0 -> EXR1:0xC4 / RLD1:0xD4）；
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
static uint32_t g_cyccnt_prev;
static uint64_t g_cyc_total;

void SysTick_Handler(void) { g_ms++; }

/* 基于 32 位 DWT->CYCCNT（16 MHz 下每 16 拍 = 1 µs）维护不回绕的 64 位微秒时钟 */
static uint64_t clock_us(void)
{
    uint32_t cur = DWT->CYCCNT;
    uint32_t diff = cur - g_cyccnt_prev;
    g_cyccnt_prev = cur;
    g_cyc_total += diff;
    return g_cyc_total / 16u;
}

static void delay_us(uint32_t us)
{
    uint32_t t0 = DWT->CYCCNT, n = us * 16u;
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
static int i2c_wait(uint32_t flag)
{
    uint32_t t0 = DWT->CYCCNT;
    uint32_t limit = 3000u * 16u; /* 最多等 3 ms，绝不拖慢流循环 */
    while (!(I2C1->ISR & flag)) {
        if (I2C1->ISR & I2C_ISR_NACKF) {
            I2C1->ICR = I2C_ICR_NACKCF | I2C_ICR_STOPCF;
            return -1;
        }
        if ((DWT->CYCCNT - t0) > limit) return -2;
    }
    return 0;
}

static int i2c_read(uint8_t addr, uint8_t reg, uint8_t *b, int n)
{
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
    I2C1->CR1 = 0;
    I2C1->TIMINGR = 0x0010061Au; /* PCLK1 16 MHz -> 400 kHz 快速模式，读 12 字节仅需 ~350 µs */
    I2C1->CR1 = I2C_CR1_PE;
    uint8_t who = 0;
    if (i2c_read(0x6Au, 0x0Fu, &who, 1) || who != 0x6Au) return false;
    /* CTRL3_C(0x12)=0x44: BDU=1, IF_INC=1
     * CTRL1_XL(0x10)=0x4C: 104 Hz, ±8 g (0.244 mg/LSB)
     * CTRL2_G(0x11)=0x48:  104 Hz, ±1000 dps (35 mdps/LSB)，严格对齐 host/v12_imu.py PROFILE */
    if (i2c_write(0x6Au, 0x12u, 0x44u)) return false;
    if (i2c_write(0x6Au, 0x10u, 0x4Cu)) return false;
    if (i2c_write(0x6Au, 0x11u, 0x48u)) return false;
    return true;
}

static bool imu_poll_sample(int16_t out_raw[6])
{
    uint8_t st = 0;
    if (i2c_read(0x6Au, 0x1Eu, &st, 1)) return false;
    if ((st & 0x03u) != 0x03u) return false; /* XLDA | GDA 同时就绪才取 */
    uint8_t raw[12];
    if (i2c_read(0x6Au, 0x22u, raw, 12)) return false; /* OUTX_L_G(0x22)..OUTZ_H_XL(0x2D) */
    for (int i = 0; i < 6; i++) {
        out_raw[i] = (int16_t)((uint16_t)raw[2 * i] | ((uint16_t)raw[2 * i + 1] << 8));
    }
    return true;
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
    c08b_afe_mode_t afe_mode;
    c08b_fault_t    fault;
    uint16_t        fs_hz;
    uint8_t         id_a, id_b;
    bool            imu_ok;
    bool            avdd_ok;
    bool            sent_session_start;
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

static void session_stop(c08b_fault_t reason)
{
    afe_safe_off();
    g_sess.active = false;
    g_sess.is_synth = false;
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

/* 启动真实 AFE 会话或执行 PRB1 子板探测（仅在双硬件锁显式放行且无 VBUS 互锁时可达） */
static c08b_fault_t start_real_afe(uint8_t req_mode, uint16_t fs_hz, uint8_t nrf_flags, bool *aborted)
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

    if (mode == AFE_2CH) {
        /* PA4(AVDD_SENSE) 先 10 µs P_DOWN 泄放寄生电容，再保持纯高阻输入 P_NONE 判读 3.0V */
        pin_mode(DRDY_B_PORT, DRDY_B_PIN, M_IN, 0, P_DOWN, 0);
        delay_us(C08B_PA4_BLEED_US);
        pin_mode(DRDY_B_PORT, DRDY_B_PIN, M_IN, 0, P_NONE, 0);
        delay_us(50u);
        g_sess.avdd_ok = (GET(DRDY_B) != 0);
        if (!g_sess.avdd_ok) { afe_safe_off(); return C08B_FAULT_INTERLOCK; }

        uint8_t cfg[0x0C], mask[0x0C], rld_step2 = 0;
        if (!c08b_build_ads1292_regs(req_mode, fs_hz, cfg, mask, &rld_step2)) {
            afe_safe_off(); return C08B_FAULT_ARG;
        }
        if (ads_write_verify(0, cfg, mask, 0x01, 0x0B) != 0) {
            afe_safe_off(); return C08B_FAULT_READBACK;
        }
        /* 两步开 RLD：先等 PDB_RLD 与外部 C7(10 µF) 预热满 >=150 ms，再合上电极反馈 0x23 */
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
        ads_cmd(0, ADS_RDATAC);
    } else {
        /* 8CH / 16CH ADS1298（LM27762 ±2.5V 双极供电，Pin 60 RLDREF & Pin 62 RLDIN 硬连 AGND）：
         * 切 SPI1 到 4.000 MHz（BR=1: 16MHz/4=4MHz），DRDY_B 开上拉防 8CH 悬空 */
        pin_mode(DRDY_B_PORT, DRDY_B_PIN, M_IN, 0, P_UP, 0);
        spi_init(SPI1, 1u, 1);
        g_sess.avdd_ok = true;
        int nchips = (mode == AFE_16CH) ? 2 : 1;
        uint8_t cfg3_step2[2] = {0, 0};
        uint8_t rld_step2[2]  = {0, 0};
        for (int c = 0; c < nchips; c++) {
            uint8_t cfg[0x1A], mask[0x1A];
            if (!c08b_build_ads1298_regs(req_mode, fs_hz, c, cfg, mask, &cfg3_step2[c], &rld_step2[c])) {
                afe_safe_off(); return C08B_FAULT_ARG;
            }
            if (ads_write_verify(c, cfg, mask, 0x01, 0x19) != 0) {
                afe_safe_off(); return C08B_FAULT_READBACK;
            }
        }
        /* 等满 >=150 ms 让内部 2.40V 基准稳定，随后对 U1 执行第 2 步 RLD 启用（RLDREF_INT 保持 0！） */
        for (uint32_t waited = 0; waited < C08B_ADS_RLD_WARMUP_US; waited += 5000u) {
            delay_us(5000u);
            if (l432_vbus_present()) { afe_safe_off(); return C08B_FAULT_INTERLOCK; }
        }
        if (cfg3_step2[0]) {
            ads_wreg(0, 0x0Du, rld_step2[0]);
            ads_wreg(0, 0x0Eu, rld_step2[0]);
            ads_wreg(0, 0x03u, cfg3_step2[0]);
            if (ads_rreg(0, 0x0Du) != rld_step2[0] ||
                ads_rreg(0, 0x0Eu) != rld_step2[0] ||
                (ads_rreg(0, 0x03u) & 0xFEu) != cfg3_step2[0]) {
                afe_safe_off(); return C08B_FAULT_READBACK;
            }
        }
        ads_cmd(0, ADS_RDATAC);
        if (mode == AFE_16CH) ads_cmd(1, ADS_RDATAC);
    }

    g_sess.imu_ok = imu_setup_stream();
    SET(ADS_START, 1);
    return C08B_FAULT_NONE;
}

static void handle_rx_cmd(const c08b_link_rx_t *rx)
{
    /* 无论命令序号是否更新，一旦 nRF 侧报告 VBUS 或 OE_N 互锁断开，运行中的真实 AFE 必须立刻断电并报 INTERLOCK(3) */
    if (g_sess.active && !g_sess.is_synth) {
        if ((rx->nrf_flags & (C08B_NF_VBUS_INTERLOCK | C08B_NF_OE_OFF)) != 0) {
            session_stop(C08B_FAULT_INTERLOCK);
            return;
        }
    }
    if (rx->cmd_epoch == g_sess.last_cmd_epoch) return;
    g_sess.last_cmd_epoch = rx->cmd_epoch;

    if (rx->req_mode == C08B_MODE_STOP || rx->req_mode == C08B_MODE_IDLE) {
        session_stop(C08B_FAULT_NONE);
        g_sess.fault = C08B_FAULT_NONE;
        return;
    }

    session_stop(C08B_FAULT_NONE);
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
    g_sess.produced = 0;
    g_sess.dropped = 0;
    g_sess.bad_status = 0;
    g_sess.drdy_desync = 0;
    g_sess.min_interval_us = 0xFFFFFFFFu;
    g_sess.last_sample_us = 0;
    g_sess.sent_session_start = false;

    if (rx->req_mode == C08B_MODE_SYN1) {
        uint8_t sc = rx->synth_channels;
        g_sess.afe_mode = (sc == 2u) ? AFE_2CH : (sc == 8u) ? AFE_8CH : AFE_16CH;
        g_sess.is_synth = true;
        g_sess.active = true;
        g_sess.active_mode = C08B_MODE_SYN1;
        g_sess.imu_ok = imu_setup_stream();
        g_sess.next_synth_us = clock_us();
        logf_("启动 SYN1 合成流：%uCH @ %u Hz\n", (unsigned)g_sess.afe_mode, fs);
        return;
    }

    bool aborted = false;
    c08b_fault_t err = start_real_afe(rx->req_mode, fs, rx->nrf_flags, &aborted);
    if (err != C08B_FAULT_NONE) {
        g_sess.fault = err;
        logf_("启动真实 AFE 失败：故障码 %u\n", (unsigned)err);
        return;
    }
    if (aborted || rx->req_mode == C08B_MODE_PRB1) {
        logf_("完成 PRB1 探测或被 STOP 中止：afe=%uCH\n", (unsigned)g_sess.afe_mode);
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
    uint32_t t0 = g_ms;
    while (GET(DRDY_A)) {
        if (l432_vbus_present()) { session_stop(C08B_FAULT_INTERLOCK); return false; }
        if (g_ms - t0 > 20u)     { session_stop(C08B_FAULT_DRDY_TO);   return false; }
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
    }

    uint32_t tw = DWT->CYCCNT;
    while (!GET(DRDY_A) && (DWT->CYCCNT - tw) < 80u * 16u) {}
    return true;
}

static void clock_and_gpio_init(void)
{
    RCC->CR |= RCC_CR_HSION;
    while (!(RCC->CR & RCC_CR_HSIRDY)) {}
    RCC->CFGR = (RCC->CFGR & ~RCC_CFGR_SW) | RCC_CFGR_SW_HSI; /* HSI16 = 16 MHz */
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
    pin_mode(IMU_SCL_PORT, IMU_SCL_PIN, M_AF, 4, P_NONE, 1);
    pin_mode(IMU_SDA_PORT, IMU_SDA_PIN, M_AF, 4, P_NONE, 1);

    spi_init(SPI3, 0u, 0); /* 16 MHz / 2 = 8 MHz，模式 0 对接 nRF SPIS1 */
}

int main(void)
{
    clock_and_gpio_init();
    rtt_init();
    logf_("\nC08B L432 流式候选固件启动（AFE_LOCK=%d, BENCH_MEASURED=%d）\n",
          MAKO_C08B_AFE_ENABLED, MAKO_BENCH_MEASURED);

    static c08b_link_tx_t tx;
    c08b_link_rx_t rx;
    bool got_rx = false;
    uint32_t last_hb_ms = 0;

    for (;;) {
        (void)clock_us();
        if (g_sess.active && !g_sess.is_synth && l432_vbus_present()) {
            session_stop(C08B_FAULT_INTERLOCK);
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
        fill_tx_telemetry(&tx);
        tx.seq_first = g_sess.produced;

        for (uint8_t b = 0; b < target_batch; b++) {
            uint64_t ts = 0;
            if (g_sess.is_synth) {
                uint32_t step_us = 1000000u / g_sess.fs_hz;
                while (clock_us() < g_sess.next_synth_us) {}
                ts = g_sess.next_synth_us;
                g_sess.next_synth_us += step_us;
                c08b_fill_synth_slot(tx.samples[b], g_sess.afe_mode, g_sess.produced + b);
            } else {
                if (!read_one_afe_slot(tx.samples[b], &ts)) break;
            }
            if (b == 0) tx.timestamp_us = ts;
            if (g_sess.produced + b > 0) {
                uint64_t dt = ts - g_sess.last_sample_us;
                if (dt < g_sess.min_interval_us) g_sess.min_interval_us = (uint32_t)dt;
            }
            g_sess.last_sample_us = ts;
            tx.sample_count++;
        }

        if (!g_sess.active || tx.sample_count == 0) continue;

        /* 每 ~10 ms 顺带轮询一次 104 Hz IMU，打同源 L432_DWT_1MHz 64 位时间戳 */
        if (g_ms - g_sess.last_imu_ms >= 9u) {
            int16_t imu6[6] = {0};
            uint64_t t_imu0 = clock_us();
            if (g_sess.imu_ok && imu_poll_sample(imu6)) {
                uint64_t dt_imu = clock_us() - t_imu0;
                g_sess.last_imu_ms = g_ms;
                tx.imu_fresh = 1u;
                tx.imu_timestamp_us = t_imu0;
                tx.imu_read_us = (dt_imu > 8999u) ? 8999u : (uint16_t)dt_imu;
                memcpy(tx.imu_raw, imu6, sizeof(imu6));
            } else if (g_sess.is_synth && !g_sess.imu_ok && (g_ms - g_sess.last_imu_ms >= 10u)) {
                g_sess.last_imu_ms = g_ms;
                tx.imu_fresh = 1u;
                tx.imu_timestamp_us = t_imu0;
                tx.imu_read_us = 0u;
                tx.imu_raw[0] = (int16_t)(g_sess.produced & 0xFFu);
                tx.imu_raw[5] = 4096; /* 标称 +1 g @ ±8g (0.244 mg/LSB) */
            }
        }

        uint8_t flags = g_sess.is_synth ? C08B_F01_SYNTHETIC : 0u;
        if (!g_sess.sent_session_start) {
            flags |= C08B_F01_SESSION_START;
            g_sess.sent_session_start = true;
        }
        tx.f01_flags = flags;
        g_sess.produced += tx.sample_count;
        tx.produced = g_sess.produced;
        tx.min_interval_us_sat = (g_sess.produced < 2u || g_sess.min_interval_us > 0xFFFEu)
                                      ? 0xFFFFu : (uint16_t)g_sess.min_interval_us;

        if (link_exchange(&tx, &rx, &got_rx)) {
            if (got_rx) handle_rx_cmd(&rx);
        } else {
            g_sess.dropped += tx.sample_count;
            /* 首包丢失时下次无法续接 seq=0，记入故障码停机 */
            if (flags & C08B_F01_SESSION_START) {
                session_stop(C08B_FAULT_LINK_DROP);
            }
        }
    }
}

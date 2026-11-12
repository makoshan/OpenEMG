/* C08B 主控 nRF52840（QFN48）上电自检（裸机，只用 Nordic MDK 头，不用 SoftDevice）。
   上电先拉 PWR_HOLD 保持供电，然后：
   - 起 32 MHz 晶振（Y3），读 VBAT（SAADC）、VBUS、充电、按键、互锁 OE_N；
   - SPIS1 当 LINK 从机，拉高 LINK_RDY 等 L432 发自检报告，CRC 校验；
   - 结果三路输出：UART（J301.5，115200）、RTT、BLE 不可连接广播（名字 "C08B"，厂商数据带结果，手机 nRF Connect 可看）；
   - LED 闪码：没收到报告 5 Hz 快闪；全过 1 Hz 慢闪；有失败 = 闪 (第一个失败项编号 + 1) 下再停顿。
   长按按键 3 s 放开 PWR_HOLD，松手后断电（开机或烧录时一直按着不算，要先松开一次）。烧录会覆盖 0 地址起的 flash（包括任何 bootloader）。 */
#define RTT_IMPL
#include "nrf.h"
#include "pins.h"
#include "../common/report.h"
#include "../common/rtt.h"

static volatile uint32_t g_ms;
void SysTick_Handler(void) { g_ms++; }

/* ---------- GPIO ---------- */
static NRF_GPIO_Type *gport(uint32_t p) { return (p >> 5) ? NRF_P1 : NRF_P0; }
static void gpio_out(uint32_t p, int v)
{
    NRF_GPIO_Type *g = gport(p); uint32_t b = 1u << (p & 31);
    if (v) g->OUTSET = b; else g->OUTCLR = b;
    g->PIN_CNF[p & 31] = (GPIO_PIN_CNF_DIR_Output << GPIO_PIN_CNF_DIR_Pos) | (GPIO_PIN_CNF_INPUT_Disconnect << GPIO_PIN_CNF_INPUT_Pos);
}
static void gpio_set(uint32_t p, int v) { NRF_GPIO_Type *g = gport(p); uint32_t b = 1u << (p & 31); if (v) g->OUTSET = b; else g->OUTCLR = b; }
static void gpio_in(uint32_t p, uint32_t pull)
{
    gport(p)->PIN_CNF[p & 31] = (GPIO_PIN_CNF_DIR_Input << GPIO_PIN_CNF_DIR_Pos) | (GPIO_PIN_CNF_INPUT_Connect << GPIO_PIN_CNF_INPUT_Pos) |
                                (pull << GPIO_PIN_CNF_PULL_Pos);
}
static int gpio_get(uint32_t p) { return (int)((gport(p)->IN >> (p & 31)) & 1u); }

/* ---------- UART（EasyDMA 只能从 RAM 发，先拷到 RAM 缓冲） ---------- */
static uint8_t uart_buf[160];
void log_sink(const char *s, unsigned n)
{
    if (n > sizeof uart_buf) n = sizeof uart_buf;
    for (unsigned i = 0; i < n; i++) uart_buf[i] = (uint8_t)s[i];
    NRF_UARTE0->TXD.PTR = (uint32_t)uart_buf;
    NRF_UARTE0->TXD.MAXCNT = n;
    NRF_UARTE0->EVENTS_ENDTX = 0;
    NRF_UARTE0->TASKS_STARTTX = 1;
    uint32_t t = g_ms;
    while (!NRF_UARTE0->EVENTS_ENDTX) if (g_ms - t > 50) break;
    NRF_UARTE0->EVENTS_ENDTX = 0;
}
static void uart_init(void)
{
    gpio_out(UART_TX_PIN, 1);
    NRF_UARTE0->PSEL.TXD = UART_TX_PIN;
    NRF_UARTE0->PSEL.RXD = 0xFFFFFFFFu;
    NRF_UARTE0->BAUDRATE = UARTE_BAUDRATE_BAUDRATE_Baud115200;
    NRF_UARTE0->CONFIG = 0;
    NRF_UARTE0->ENABLE = UARTE_ENABLE_ENABLE_Enabled;
}

/* ---------- VBAT：AIN2，增益 1/6、内部 0.6 V 基准 → 满量程 3.6 V；板上 1 MΩ/1 MΩ 分压，源阻抗高，采样 40 µs ---------- */
static int vbat_mv(void)
{
    static volatile int16_t sample;
    NRF_SAADC->RESOLUTION = SAADC_RESOLUTION_VAL_12bit;
    NRF_SAADC->CH[0].PSELP = SAADC_CH_PSELP_PSELP_AnalogInput2;
    NRF_SAADC->CH[0].PSELN = SAADC_CH_PSELN_PSELN_NC;
    NRF_SAADC->CH[0].CONFIG = (SAADC_CH_CONFIG_GAIN_Gain1_6 << SAADC_CH_CONFIG_GAIN_Pos) |
                              (SAADC_CH_CONFIG_REFSEL_Internal << SAADC_CH_CONFIG_REFSEL_Pos) |
                              (SAADC_CH_CONFIG_TACQ_40us << SAADC_CH_CONFIG_TACQ_Pos) |
                              (SAADC_CH_CONFIG_MODE_SE << SAADC_CH_CONFIG_MODE_Pos);
    NRF_SAADC->RESULT.PTR = (uint32_t)&sample;
    NRF_SAADC->RESULT.MAXCNT = 1;
    NRF_SAADC->ENABLE = 1;
    NRF_SAADC->EVENTS_STARTED = 0; NRF_SAADC->TASKS_START = 1; while (!NRF_SAADC->EVENTS_STARTED) {}
    NRF_SAADC->EVENTS_END = 0; NRF_SAADC->TASKS_SAMPLE = 1;
    uint32_t t = g_ms; while (!NRF_SAADC->EVENTS_END) if (g_ms - t > 10) break;
    NRF_SAADC->EVENTS_STOPPED = 0; NRF_SAADC->TASKS_STOP = 1; while (!NRF_SAADC->EVENTS_STOPPED) {}
    NRF_SAADC->ENABLE = 0;
    int v = sample < 0 ? 0 : sample;
    return v * 3600 * 2 / 4096;
}

/* ---------- LINK：SPIS1 从机，收满一份报告 ---------- */
static c08b_report_t rx;
static uint8_t tx[4] = {0xA5, 0x5A, 0x00, 0x00};
static void spis_arm(void)
{
    NRF_SPIS1->RXD.PTR = (uint32_t)&rx;
    NRF_SPIS1->RXD.MAXCNT = sizeof rx;
    NRF_SPIS1->TXD.PTR = (uint32_t)tx;
    NRF_SPIS1->TXD.MAXCNT = sizeof tx;
    NRF_SPIS1->EVENTS_ACQUIRED = 0;
    NRF_SPIS1->TASKS_RELEASE = 1;          /* 把缓冲交给硬件 */
    gpio_set(LINK_RDY_PIN, 1);              /* 告诉 L432 可以发了 */
}
static void spis_init(void)
{
    gpio_out(LINK_RDY_PIN, 0);
    NRF_SPIS1->PSEL.SCK = LINK_SCK_PIN;
    NRF_SPIS1->PSEL.MOSI = LINK_MOSI_PIN;
    NRF_SPIS1->PSEL.MISO = LINK_MISO_PIN;
    NRF_SPIS1->PSEL.CSN = LINK_CS_PIN;
    NRF_SPIS1->CONFIG = 0;                 /* 模式 0，高位先发，与 L432 SPI3 一致 */
    NRF_SPIS1->DEF = 0xFF; NRF_SPIS1->ORC = 0xFF;
    NRF_SPIS1->SHORTS = SPIS_SHORTS_END_ACQUIRE_Msk;   /* 收完自动把缓冲还给 CPU */
    NRF_SPIS1->ENABLE = SPIS_ENABLE_ENABLE_Enabled;
    NRF_SPIS1->EVENTS_ACQUIRED = 0;
    NRF_SPIS1->TASKS_ACQUIRE = 1;
    uint32_t t = g_ms; while (!NRF_SPIS1->EVENTS_ACQUIRED) if (g_ms - t > 10) break;
    spis_arm();
}

/* ---------- BLE 不可连接广播（直接驱动 RADIO，BLE 1M，信道 37/38/39） ---------- */
static uint8_t adv[2 + 37];                /* S0（PDU 头）、LENGTH、载荷 */
static uint8_t adv_addr[6];
static void radio_init(void)
{
    NRF_RADIO->MODE = RADIO_MODE_MODE_Ble_1Mbit;
    NRF_RADIO->TXPOWER = RADIO_TXPOWER_TXPOWER_0dBm;
    NRF_RADIO->PCNF0 = (8u << RADIO_PCNF0_LFLEN_Pos) | (1u << RADIO_PCNF0_S0LEN_Pos) | (0u << RADIO_PCNF0_S1LEN_Pos);
    NRF_RADIO->PCNF1 = (37u << RADIO_PCNF1_MAXLEN_Pos) | (0u << RADIO_PCNF1_STATLEN_Pos) | (3u << RADIO_PCNF1_BALEN_Pos) |
                       (RADIO_PCNF1_ENDIAN_Little << RADIO_PCNF1_ENDIAN_Pos) | (RADIO_PCNF1_WHITEEN_Enabled << RADIO_PCNF1_WHITEEN_Pos);
    NRF_RADIO->BASE0 = 0x89BED600u;        /* 广播接入地址 0x8E89BED6 */
    NRF_RADIO->PREFIX0 = 0x8Eu;
    NRF_RADIO->TXADDRESS = 0;
    NRF_RADIO->RXADDRESSES = 1;
    NRF_RADIO->CRCCNF = (RADIO_CRCCNF_LEN_Three << RADIO_CRCCNF_LEN_Pos) | (RADIO_CRCCNF_SKIPADDR_Skip << RADIO_CRCCNF_SKIPADDR_Pos);
    NRF_RADIO->CRCPOLY = 0x00065Bu;
    NRF_RADIO->CRCINIT = 0x555555u;
    NRF_RADIO->PACKETPTR = (uint32_t)adv;
    NRF_RADIO->SHORTS = RADIO_SHORTS_READY_START_Msk | RADIO_SHORTS_END_DISABLE_Msk;
    /* 随机静态地址：取 FICR 设备地址，最高两位置 1 */
    uint32_t a0 = NRF_FICR->DEVICEADDR[0], a1 = NRF_FICR->DEVICEADDR[1];
    adv_addr[0] = (uint8_t)a0; adv_addr[1] = (uint8_t)(a0 >> 8); adv_addr[2] = (uint8_t)(a0 >> 16); adv_addr[3] = (uint8_t)(a0 >> 24);
    adv_addr[4] = (uint8_t)a1; adv_addr[5] = (uint8_t)(a1 >> 8) | 0xC0;
}

#include "adv_build.inc"

static void radio_tx(int ch)
{
    static const uint8_t freq[3] = {2, 26, 80};      /* 2402 / 2426 / 2480 MHz */
    NRF_RADIO->FREQUENCY = freq[ch - 37];
    NRF_RADIO->DATAWHITEIV = (uint32_t)ch;
    NRF_RADIO->EVENTS_DISABLED = 0;
    NRF_RADIO->TASKS_TXEN = 1;
    uint32_t t = g_ms; while (!NRF_RADIO->EVENTS_DISABLED) if (g_ms - t > 5) break;
}

/* nRF52840 Rev3（构建码 F 起；U13 料号 QFAA-F-R）上电默认锁调试口（Nordic 勘误 249、IN-141）。
   每次上电写 APPROTECT.DISABLE = SwDisable；UICR.APPROTECT 还是擦除值 0xFFFFFFFF 时写成 HwDisabled（0x5A）再复位一次。
   UICR 已被写成别的值（例如 0x00 真锁）时不碰；写过一次仍是全 F 也不再复位（GPREGRET2 记一笔，软件复位不清），避免复位死循环。
   新老芯片按 Nordic MDK nrf52_configuration_249() 的判法：FICR 0x10000130 = 0x08（52840）且 0x10000134 ≥ 0x05。
   MDK 8.30.2 没有 NRF_APPROTECT 外设定义，直接写地址。 */
static void approtect_open(void)
{
    if (*(volatile uint32_t *)0x10000130u != 0x08u || *(volatile uint32_t *)0x10000134u < 0x05u) return;   /* 老版本没有这套机制，不写 */
    *(volatile uint32_t *)0x40000558u = 0x5Au;
    if (NRF_UICR->APPROTECT == 0xFFFFFFFFu && NRF_POWER->GPREGRET2 != 0xA5u) {
        NRF_POWER->GPREGRET2 = 0xA5u;
        NRF_NVMC->CONFIG = NVMC_CONFIG_WEN_Wen; while (!NRF_NVMC->READY) {}
        NRF_UICR->APPROTECT = 0x5Au; while (!NRF_NVMC->READY) {}
        NRF_NVMC->CONFIG = NVMC_CONFIG_WEN_Ren; while (!NRF_NVMC->READY) {}
        NVIC_SystemReset();
    }
}

/* nRF 状态位 */
enum { NF_HFXO = 1, NF_LINK = 2, NF_VBUS = 4, NF_CHRG = 8, NF_BTN = 16, NF_OE_OFF = 32 };

static void print_report(const c08b_report_t *r)
{
    logf_("—— 收到 L432 报告 #%lu：done 0x%04X fail 0x%04X ——\n", (unsigned long)r->seq, r->done_mask, r->fail_mask);
    for (int t = 0; t < T_COUNT; t++)
        logf_("  %-9s %s\n", TEST_NAME[t], !(r->done_mask >> t & 1) ? "没做" : (r->fail_mask >> t & 1) ? "不过" : "过");
    logf_("  ADS ID A=0x%02X B=0x%02X，回读错 A=%u B=%u，采样率 %u.%u Hz，不同步 %u，状态字错 %u，帧 %u\n", r->id_a, r->id_b,
          r->reg_bad_a, r->reg_bad_b, r->rate_hz_x10 / 10, r->rate_hz_x10 % 10, r->drdy_desync, r->bad_status, r->frames);
    for (int c = 0; c < 16; c++) logf_("  CH%-2d 方波 %5u µV  底噪 %5u nV\n", c + 1, r->sig_pp_uv[c], r->noise_rms_nv[c]);
    logf_("  IMU 0x%02X  %d %d %d mg\n", r->imu_id, r->imu_mg[0], r->imu_mg[1], r->imu_mg[2]);
}

int main(void)
{
    /* 第一件事：保持供电（PWR_HOLD 高），关台架解互锁（BENCH_EN 低），LED 先亮（低有效）；然后开调试口 */
    gpio_out(PWR_HOLD_PIN, 1);
    approtect_open();
    gpio_out(BENCH_EN_PIN, 0);
    gpio_out(LED_PIN, 0);
    gpio_in(BUTTON_N_PIN, GPIO_PIN_CNF_PULL_Disabled);    /* 外部上拉 R38 */
    gpio_in(CHRG_N_PIN, GPIO_PIN_CNF_PULL_Pullup);        /* TP4054 CHRG 开漏 */
    gpio_in(VBUS_SENSE_PIN, GPIO_PIN_CNF_PULL_Disabled);
    gpio_in(OE_N_PIN, GPIO_PIN_CNF_PULL_Disabled);

    SysTick_Config(SystemCoreClock / 1000u);
    rtt_init();
    uart_init();
    logf_("\nC08B nRF52840 自检开始\n");

    NRF_CLOCK->EVENTS_HFCLKSTARTED = 0;
    NRF_CLOCK->TASKS_HFCLKSTART = 1;
    uint32_t t0 = g_ms;
    while (!NRF_CLOCK->EVENTS_HFCLKSTARTED && g_ms - t0 < 50) {}
    int hfxo = NRF_CLOCK->EVENTS_HFCLKSTARTED != 0;
    logf_("32 MHz 晶振：%s（%lu ms）\n", hfxo ? "起振" : "没起振", (unsigned long)(g_ms - t0));

    radio_init();
    spis_init();

    static c08b_report_t cur;               /* 校验过的报告副本：rx 交回 SPIS 后会被 DMA 改写 */
    int have = 0, btn_armed = 0; uint16_t last_done = 0xFFFF, last_fail = 0xFFFF;
    uint32_t t_adv = 0, t_stat = 0, btn_t = 0, vbat = (uint32_t)vbat_mv();
    for (;;) {
        uint32_t now = g_ms;
        if (NRF_SPIS1->EVENTS_END) {
            NRF_SPIS1->EVENTS_END = 0;
            gpio_set(LINK_RDY_PIN, 0);
            uint32_t t = g_ms; while (!NRF_SPIS1->EVENTS_ACQUIRED) if (g_ms - t > 5) break;
            if (NRF_SPIS1->RXD.AMOUNT == sizeof rx && report_ok(&rx)) {
                cur = rx;
                if (!have || cur.done_mask != last_done || cur.fail_mask != last_fail) print_report(&cur);
                have = 1; last_done = cur.done_mask; last_fail = cur.fail_mask;
            } else {
                logf_("LINK 收到 %lu 字节，校验不过\n", (unsigned long)NRF_SPIS1->RXD.AMOUNT);
            }
            spis_arm();
        }
        uint8_t nf = (uint8_t)((hfxo ? NF_HFXO : 0) | (have ? NF_LINK : 0) | (gpio_get(VBUS_SENSE_PIN) ? NF_VBUS : 0) |
                               (!gpio_get(CHRG_N_PIN) ? NF_CHRG : 0) | (!gpio_get(BUTTON_N_PIN) ? NF_BTN : 0) | (gpio_get(OE_N_PIN) ? NF_OE_OFF : 0));
        if (now - t_stat >= 5000) {
            t_stat = now; vbat = (uint32_t)vbat_mv();
            logf_("状态：VBAT %lu mV，VBUS %s，充电 %s，AFE 缓冲 %s，L432 报告 %s\n", (unsigned long)vbat, nf & NF_VBUS ? "有" : "无",
                  nf & NF_CHRG ? "中" : "否", nf & NF_OE_OFF ? "关（互锁或 L432 没开）" : "开", have ? "已收到" : "还没收到");
        }
        if (now - t_adv >= 200 && hfxo) {
            t_adv = now;
            uint32_t v20 = vbat / 20; if (v20 > 255) v20 = 255;
            adv_build(adv, adv_addr, have ? cur.done_mask : 0, have ? cur.fail_mask : 0xFFFF, nf, (uint8_t)v20,
                      have ? (uint8_t)cur.seq : 0, have ? cur.id_a : 0, have ? cur.id_b : 0);
            for (int ch = 37; ch <= 39; ch++) radio_tx(ch);
        }
        /* LED 闪码（低 = 亮） */
        int on;
        if (!have) on = (now / 100) & 1;
        else if (!cur.fail_mask && cur.done_mask == (1u << T_COUNT) - 1) on = (now / 500) & 1;
        else {
            int k = 0; while (k < T_COUNT && !(cur.fail_mask >> k & 1)) k++;
            if (k == T_COUNT) k = 0;                      /* 只是没做全：闪 1 下 */
            uint32_t per = (uint32_t)(k + 1) * 400 + 1200, ph = now % per;
            on = ph < (uint32_t)(k + 1) * 400 && (ph % 400) < 200;
        }
        gpio_set(LED_PIN, !on);
        /* 长按 3 s 关机：开机、烧录时一直按着不算，先松开过一次才开始计 */
        if (!gpio_get(BUTTON_N_PIN)) {
            if (btn_armed) { if (!btn_t) btn_t = now ? now : 1; else if (now - btn_t > 3000) { logf_("长按关机，松手断电\n"); gpio_set(PWR_HOLD_PIN, 0); btn_armed = 0; } }
        } else { btn_t = 0; btn_armed = 1; }
    }
}

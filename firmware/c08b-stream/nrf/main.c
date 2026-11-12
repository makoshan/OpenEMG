/* C08B 共用双核主控 nRF52840-QFAA 实时 BLE GATT 流式候选固件。
 *
 * 构建档位（由 Makefile 控制）：
 *   - C08B_USE_S140=1（默认，配合 Nordic SoftDevice S140 v7.3.0，FLASH 0x27000）：
 *     纯 C 直调 S140 SVC 接口，广播名 "YUANLI-C08B"（对齐 host/devices/c08b-*.json），
 *     暴露完整 V12 GATT 服务 7b24c101-3948-4f03-9d11-12bb9d000001..000006
 *     （DATA Notify / META Read / STATUS Read / CONTROL Write / IMU_DATA Notify），支持 MTU 247 + DLE + 2M PHY，
 *     无缝兼容现有 XIAO ble-dongle 接收器与 host/c08b_stream.py。
 *   - C08B_USE_S140=0（免 SoftDevice 裸机联调档，FLASH 0x00000）：
 *     首板未烧 S140 时直烧 0 地址验证 PWR_HOLD、互锁、SPIS1 双核双向流式收发与 UART/RTT 遥测。
 *
 * 关键硬件铁律（R4U6 / R4U6N）：
 *   1. main() 第一条指令拉高 PWR_HOLD(P0.05)，否则松开按键断电；
 *   2. P0.00/XL1 = MCU_BENCH_EN（保持输出低 0！严禁开外部低频晶振 XTAL！SoftDevice 强制用内部 RC 低频时钟）；
 *   3. P0.01/XL2 = VBUS_SENSE（纯数字输入）；
 *   4. P0.17 = OE_N（互锁状态线，纯数字输入，严禁推挽输出！）；
 *   5. 任何时刻检测到 VBUS_SENSE==1 或 OE_N 电平变化，立刻刷新 SPIS1 MISO 控制帧并置 C08B_FAULT_INTERLOCK(3)。
 */
#define RTT_IMPL
#include "nrf.h"
#include "pins.h"
#include "../common/stream_proto.h"
#include "../common/rtt.h"
#include "../common/baremetal_stubs.h"

#ifndef C08B_USE_S140
#define C08B_USE_S140 1
#endif

#if C08B_USE_S140
#include "nrf_sdm.h"
#include "nrf_soc.h"
#include "ble.h"
#include "ble_gap.h"
#include "ble_gatts.h"
#include "ble_gatt.h"
#endif

static volatile uint32_t g_ms;
void SysTick_Handler(void) { g_ms++; }

/* ---------- GPIO 底层（零外部库，严格只碰 pins.h 核对过的 15 根脚） ---------- */
static NRF_GPIO_Type *gport(uint32_t p) { return (p >> 5) ? NRF_P1 : NRF_P0; }

static void gpio_out(uint32_t p, int v)
{
    NRF_GPIO_Type *g = gport(p);
    uint32_t b = 1u << (p & 31);
    if (v) g->OUTSET = b; else g->OUTCLR = b;
    g->PIN_CNF[p & 31] = (GPIO_PIN_CNF_DIR_Output << GPIO_PIN_CNF_DIR_Pos) |
                         (GPIO_PIN_CNF_INPUT_Disconnect << GPIO_PIN_CNF_INPUT_Pos);
}

static void gpio_set(uint32_t p, int v)
{
    NRF_GPIO_Type *g = gport(p);
    uint32_t b = 1u << (p & 31);
    if (v) g->OUTSET = b; else g->OUTCLR = b;
}

static void gpio_in(uint32_t p, uint32_t pull)
{
    gport(p)->PIN_CNF[p & 31] = (GPIO_PIN_CNF_DIR_Input << GPIO_PIN_CNF_DIR_Pos) |
                                (GPIO_PIN_CNF_INPUT_Connect << GPIO_PIN_CNF_INPUT_Pos) |
                                (pull << GPIO_PIN_CNF_PULL_Pos);
}

static int gpio_get(uint32_t p) { return (int)((gport(p)->IN >> (p & 31)) & 1u); }

/* ---------- nRF52840 Rev3 (QFAA-F) APPROTECT 勘误 249 ---------- */
static void approtect_open(void)
{
    if (*(volatile uint32_t *)0x10000130u != 0x08u || *(volatile uint32_t *)0x10000134u < 0x05u) return;
    *(volatile uint32_t *)0x40000558u = 0x5Au;
    if (NRF_UICR->APPROTECT == 0xFFFFFFFFu && NRF_POWER->GPREGRET2 != 0xA5u) {
        NRF_POWER->GPREGRET2 = 0xA5u;
        NRF_NVMC->CONFIG = NVMC_CONFIG_WEN_Wen; while (!NRF_NVMC->READY) {}
        NRF_UICR->APPROTECT = 0x5Au; while (!NRF_NVMC->READY) {}
        NRF_NVMC->CONFIG = NVMC_CONFIG_WEN_Ren; while (!NRF_NVMC->READY) {}
        NVIC_SystemReset();
    }
}

/* ---------- UART（J301.5，115200 EasyDMA） ---------- */
static uint8_t uart_buf[160];
void log_sink(const char *s, unsigned n)
{
    if (n > sizeof uart_buf) n = sizeof uart_buf;
    memcpy(uart_buf, s, n);
    NRF_UARTE0->TXD.PTR = (uint32_t)uart_buf;
    NRF_UARTE0->TXD.MAXCNT = n;
    NRF_UARTE0->EVENTS_ENDTX = 0;
    NRF_UARTE0->TASKS_STARTTX = 1;
    uint32_t t = g_ms;
    while (!NRF_UARTE0->EVENTS_ENDTX && g_ms - t < 20u) {}
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

/* ---------- TIMER2 1 MHz 微秒计数器（辅助短延时，不冒充采样时钟） ---------- */
static uint32_t timer2_us(void)
{
    NRF_TIMER2->TASKS_CAPTURE[0] = 1;
    return NRF_TIMER2->CC[0];
}

static void delay_us_nrf(uint32_t us)
{
    uint32_t t0 = timer2_us();
    while ((timer2_us() - t0) < us) {}
}

static void timer2_init(void)
{
    NRF_TIMER2->TASKS_STOP = 1;
    NRF_TIMER2->MODE = TIMER_MODE_MODE_Timer;
    NRF_TIMER2->BITMODE = TIMER_BITMODE_BITMODE_32Bit;
    NRF_TIMER2->PRESCALER = 4u; /* 16 MHz / 2^4 = 1 MHz */
    NRF_TIMER2->TASKS_CLEAR = 1;
    NRF_TIMER2->TASKS_START = 1;
}

/* ---------- VBAT 监测（AIN2，1M/1M 分压，采样保持 40 µs） ---------- */
static int read_vbat_mv(void)
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
    NRF_SAADC->EVENTS_STARTED = 0; NRF_SAADC->TASKS_START = 1;
    uint32_t t = g_ms; while (!NRF_SAADC->EVENTS_STARTED && g_ms - t < 5u) {}
    NRF_SAADC->EVENTS_END = 0; NRF_SAADC->TASKS_SAMPLE = 1;
    t = g_ms; while (!NRF_SAADC->EVENTS_END && g_ms - t < 10u) {}
    NRF_SAADC->EVENTS_STOPPED = 0; NRF_SAADC->TASKS_STOP = 1;
    t = g_ms; while (!NRF_SAADC->EVENTS_STOPPED && g_ms - t < 5u) {}
    NRF_SAADC->ENABLE = 0;
    int v = sample < 0 ? 0 : sample;
    return v * 3600 * 2 / 4096;
}

/* ---------- SPIS1 从机（收 L432 280B 帧，同时经 MISO 回传 16B 控制帧） ---------- */
volatile c08b_link_tx_t g_spis_rx;
static c08b_link_rx_t g_spis_tx;

static uint8_t  g_req_mode = C08B_MODE_IDLE;
static uint8_t  g_synth_ch = 16u;
static uint16_t g_req_fs_hz = 1000u;
static uint32_t g_cmd_epoch = 0;
static bool     g_ble_subscribed = false;
static bool     g_imu_subscribed = false;
static bool     g_conn_emg_started = false;
static bool     g_conn_imu_started = false;

static uint8_t calc_nrf_flags(void)
{
    uint8_t nf = 0;
    if (gpio_get(VBUS_SENSE_PIN)) nf |= C08B_NF_VBUS_INTERLOCK;
    if (gpio_get(OE_N_PIN))       nf |= C08B_NF_OE_OFF;
    if (g_ble_subscribed)         nf |= C08B_NF_BLE_SUBSCRIBED;
    return nf;
}

static void spis_refresh_tx_cmd(void)
{
    memset(&g_spis_tx, 0, sizeof(g_spis_tx));
    g_spis_tx.req_mode = g_req_mode;
    g_spis_tx.nrf_flags = calc_nrf_flags();
    g_spis_tx.synth_channels = g_synth_ch;
    g_spis_tx.fs_hz = g_req_fs_hz;
    g_spis_tx.cmd_epoch = g_cmd_epoch;
    c08b_link_rx_seal(&g_spis_tx);
}

static void spis_arm(void)
{
    spis_refresh_tx_cmd();
    NRF_SPIS1->RXD.PTR = (uint32_t)&g_spis_rx;
    NRF_SPIS1->RXD.MAXCNT = sizeof(g_spis_rx);
    NRF_SPIS1->TXD.PTR = (uint32_t)&g_spis_tx;
    NRF_SPIS1->TXD.MAXCNT = sizeof(g_spis_tx);
    NRF_SPIS1->EVENTS_ACQUIRED = 0;
    NRF_SPIS1->TASKS_RELEASE = 1;
    gpio_set(LINK_RDY_PIN, 1);
}

/* 当控制命令或 VBUS/OE_N 互锁电平变化时，若 CSN 空闲则立刻刷新 SPIS1 发送缓冲 */
static void spis_rearm_now(void)
{
    if (!gpio_get(LINK_CS_PIN)) return; /* L432 正在通信，交由本次 EVENTS_END 自然重装 */
    gpio_set(LINK_RDY_PIN, 0);
    delay_us_nrf(3u);
    if (!gpio_get(LINK_CS_PIN)) {
        gpio_set(LINK_RDY_PIN, 1);
        return;
    }
    NRF_SPIS1->EVENTS_ACQUIRED = 0;
    NRF_SPIS1->TASKS_ACQUIRE = 1;
    uint32_t t = g_ms;
    while (!NRF_SPIS1->EVENTS_ACQUIRED && g_ms - t < 5u) {}
    spis_arm();
}

static void spis_init(void)
{
    gpio_in(LINK_CS_PIN, GPIO_PIN_CNF_PULL_Pullup);
    gpio_out(LINK_RDY_PIN, 0);
    NRF_SPIS1->PSEL.SCK  = LINK_SCK_PIN;
    NRF_SPIS1->PSEL.MOSI = LINK_MOSI_PIN;
    NRF_SPIS1->PSEL.MISO = LINK_MISO_PIN;
    NRF_SPIS1->PSEL.CSN  = LINK_CS_PIN;
    NRF_SPIS1->CONFIG = 0; /* SPI Mode 0, MSB first */
    NRF_SPIS1->DEF = 0xFFu;
    NRF_SPIS1->ORC = 0xFFu;
    NRF_SPIS1->SHORTS = SPIS_SHORTS_END_ACQUIRE_Msk;
    NRF_SPIS1->ENABLE = SPIS_ENABLE_ENABLE_Enabled;
    NRF_SPIS1->EVENTS_ACQUIRED = 0;
    NRF_SPIS1->TASKS_ACQUIRE = 1;
    uint32_t t = g_ms;
    while (!NRF_SPIS1->EVENTS_ACQUIRED && g_ms - t < 10u) {}
    spis_arm();
}

/* ---------- 流状态与聚合缓存（2000 SPS 下把两次 2 样本聚合成 4 样本再发 HVX） ---------- */
static struct {
    c08b_afe_mode_t afe_mode;
    uint8_t         fault;
    bool            active;
    uint64_t        produced;
    uint64_t        ring_dropped;
    uint64_t        sent_samples;
    uint64_t        notify_failures;
    uint32_t        ads_status;
    uint32_t        min_interval_us;
    uint32_t        imu_seq;
    /* 样本聚合槽（最多攒 8 个 8CH 帧或 4 个 16CH 帧 -> 统一 232B 包） */
    uint8_t         pend_count;
    uint8_t         pend_flags;
    uint32_t        pend_seq;
    uint64_t        pend_ts_us;
    uint8_t         pend_slots[8][54];
} g_bridge;

static void bridge_reset_session(void)
{
    g_bridge.sent_samples = 0;
    g_bridge.notify_failures = 0;
    g_bridge.imu_seq = 0;
    g_bridge.pend_count = 0;
    g_bridge.pend_flags = 0;
}

#if C08B_USE_S140
/* ==================== S140 v7.3.0 BLE GATT 实现 ==================== */
#define APP_BLE_CONN_CFG_TAG 1u

static uint16_t g_conn_handle = BLE_CONN_HANDLE_INVALID;
static uint16_t g_att_mtu = 23u;
static uint8_t  g_adv_handle = BLE_GAP_ADV_SET_HANDLE_NOT_SET;
static uint16_t g_svc_handle;
static ble_gatts_char_handles_t g_chr_data, g_chr_meta, g_chr_status, g_chr_ctrl, g_chr_imu;
static uint8_t  g_adv_buf[31];
static uint8_t  g_scan_rsp_buf[31];
static char     g_meta_json[440];
static uint8_t  g_status_raw[C08B_STATUS_BYTES];

static void sd_fault_handler(uint32_t id, uint32_t pc, uint32_t info)
{
    (void)id; (void)pc; (void)info;
    NVIC_SystemReset();
}

static uint8_t add_v12_uuid(uint8_t suffix, ble_uuid_t *out)
{
    ble_uuid128_t u128;
    c08b_v12_uuid128_le(suffix, u128.uuid128);
    uint8_t t = 0;
    (void)sd_ble_uuid_vs_add(&u128, &t);
    out->type = t;
    out->uuid = C08B_V12_UUID_BYTES12_13;
    return t;
}

/* 如实暴露 g_bridge.afe_mode（未探测时为 AFE_NONE -> "afe":"NONE","protocol":1,"active_channels":0），
 * 绝不把未探测状态伪装成 AFE_16CH！ */
static void refresh_gatt_meta_and_status(void)
{
    c08b_afe_mode_t m = g_bridge.afe_mode;
    int mlen = c08b_format_meta_json(
        g_meta_json, sizeof(g_meta_json), m, g_req_fs_hz,
        MAKO_BENCH_MEASURED != 0, true);
    if (mlen > 0) {
        ble_gatts_value_t val = { .len = (uint16_t)mlen, .offset = 0, .p_value = (uint8_t *)g_meta_json };
        (void)sd_ble_gatts_value_set(g_conn_handle, g_chr_meta.value_handle, &val);
    }

    c08b_ble_status_t st = {
        .produced            = g_bridge.produced,
        .ring_dropped        = g_bridge.ring_dropped,
        .scheduler_skipped   = 0,
        .sent_samples        = g_bridge.sent_samples,
        .notify_failures     = g_bridge.notify_failures,
        .fault               = g_bridge.fault,
        .active              = g_bridge.active,
        .bench_measured      = (MAKO_BENCH_MEASURED != 0),
        .ads_status          = g_bridge.ads_status,
        .drdy_raw_edges      = g_bridge.produced,
        .drdy_min_interval_us= g_bridge.min_interval_us,
        .spi_hz              = c08b_spi_hz_for_mode(m),
    };
    c08b_encode_ble_status(g_status_raw, &st);
    ble_gatts_value_t sval = { .len = sizeof(g_status_raw), .offset = 0, .p_value = g_status_raw };
    (void)sd_ble_gatts_value_set(g_conn_handle, g_chr_status.value_handle, &sval);
}

static void add_char(uint8_t suffix, bool rd, bool wr, bool ntf, uint16_t init_len, uint16_t max_len,
                     uint8_t *init_val, ble_gatts_char_handles_t *handles)
{
    ble_uuid_t cuuid;
    add_v12_uuid(suffix, &cuuid);

    ble_gatts_char_md_t char_md;
    memset(&char_md, 0, sizeof(char_md));
    char_md.char_props.read   = rd ? 1 : 0;
    char_md.char_props.write  = wr ? 1 : 0;
    char_md.char_props.notify = ntf ? 1 : 0;

    ble_gatts_attr_md_t cccd_md;
    if (ntf) {
        memset(&cccd_md, 0, sizeof(cccd_md));
        BLE_GAP_CONN_SEC_MODE_SET_OPEN(&cccd_md.read_perm);
        BLE_GAP_CONN_SEC_MODE_SET_OPEN(&cccd_md.write_perm);
        cccd_md.vloc = BLE_GATTS_VLOC_STACK;
        char_md.p_cccd_md = &cccd_md;
    }

    ble_gatts_attr_md_t attr_md;
    memset(&attr_md, 0, sizeof(attr_md));
    if (rd || ntf) BLE_GAP_CONN_SEC_MODE_SET_OPEN(&attr_md.read_perm);
    else           BLE_GAP_CONN_SEC_MODE_SET_NO_ACCESS(&attr_md.read_perm);
    if (wr)        BLE_GAP_CONN_SEC_MODE_SET_OPEN(&attr_md.write_perm);
    else           BLE_GAP_CONN_SEC_MODE_SET_NO_ACCESS(&attr_md.write_perm);
    attr_md.vloc = BLE_GATTS_VLOC_STACK;
    attr_md.vlen = (init_len == max_len && !ntf && !rd) ? 0 : 1;

    ble_gatts_attr_t attr;
    memset(&attr, 0, sizeof(attr));
    attr.p_uuid    = &cuuid;
    attr.p_attr_md = &attr_md;
    attr.init_len  = init_len;
    attr.max_len   = max_len;
    attr.p_value   = init_val;
    (void)sd_ble_gatts_characteristic_add(g_svc_handle, &char_md, &attr, handles);
}

static void ble_adv_start_now(void)
{
    ble_gap_adv_params_t params;
    memset(&params, 0, sizeof(params));
    params.properties.type = BLE_GAP_ADV_TYPE_CONNECTABLE_SCANNABLE_UNDIRECTED;
    params.interval        = 64u; /* 40 ms */
    params.duration        = 0;
    params.filter_policy   = BLE_GAP_ADV_FP_ANY;
    params.primary_phy     = BLE_GAP_PHY_1MBPS;

    /* AD: Flags(3B) + Complete 128-bit Service UUID(18B) = 21B */
    uint8_t svc_le[16];
    c08b_v12_uuid128_le(0x01u, svc_le);
    g_adv_buf[0] = 2u;  g_adv_buf[1] = BLE_GAP_AD_TYPE_FLAGS; g_adv_buf[2] = BLE_GAP_ADV_FLAGS_LE_ONLY_GENERAL_DISC_MODE;
    g_adv_buf[3] = 17u; g_adv_buf[4] = BLE_GAP_AD_TYPE_128BIT_SERVICE_UUID_COMPLETE;
    memcpy(&g_adv_buf[5], svc_le, 16);

    static const char dev_name[] = C08B_BLE_DEV_NAME;
    uint8_t nlen = (uint8_t)(sizeof(dev_name) - 1u);
    g_scan_rsp_buf[0] = (uint8_t)(1u + nlen);
    g_scan_rsp_buf[1] = BLE_GAP_AD_TYPE_COMPLETE_LOCAL_NAME;
    memcpy(&g_scan_rsp_buf[2], dev_name, nlen);

    ble_gap_adv_data_t adv_data = {
        .adv_data      = { .p_data = g_adv_buf,      .len = 21u },
        .scan_rsp_data = { .p_data = g_scan_rsp_buf, .len = (uint16_t)(2u + nlen) },
    };
    (void)sd_ble_gap_adv_set_configure(&g_adv_handle, &adv_data, &params);
    (void)sd_ble_gap_adv_start(g_adv_handle, APP_BLE_CONN_CFG_TAG);
}

static void ble_stack_init(void)
{
    /* 板上 P0.00/XL1=BENCH_EN、P0.01/XL2=VBUS_SENSE，必须用内部 RC 低频时钟！ */
    nrf_clock_lf_cfg_t lf_cfg = {
        .source       = NRF_CLOCK_LF_SRC_RC,
        .rc_ctiv      = 16u,
        .rc_temp_ctiv = 2u,
        .accuracy     = NRF_CLOCK_LF_ACCURACY_500_PPM,
    };
    (void)sd_softdevice_enable(&lf_cfg, sd_fault_handler);

    extern uint32_t __data_start__;
    uint32_t ram_start = (uint32_t)&__data_start__;
    ble_cfg_t cfg;

    memset(&cfg, 0, sizeof(cfg));
    cfg.common_cfg.vs_uuid_cfg.vs_uuid_count = 6u; /* 01..06 六个末尾不同的 128-bit UUID */
    (void)sd_ble_cfg_set(BLE_COMMON_CFG_VS_UUID, &cfg, ram_start);

    memset(&cfg, 0, sizeof(cfg));
    cfg.conn_cfg.conn_cfg_tag = APP_BLE_CONN_CFG_TAG;
    cfg.conn_cfg.params.gatt_conn_cfg.att_mtu = 247u;
    (void)sd_ble_cfg_set(BLE_CONN_CFG_GATT, &cfg, ram_start);

    memset(&cfg, 0, sizeof(cfg));
    cfg.conn_cfg.conn_cfg_tag = APP_BLE_CONN_CFG_TAG;
    cfg.conn_cfg.params.gap_conn_cfg.conn_count   = 1u;
    cfg.conn_cfg.params.gap_conn_cfg.event_length = 320u; /* 400 ms 高吞吐事件窗 */
    (void)sd_ble_cfg_set(BLE_CONN_CFG_GAP, &cfg, ram_start);

    memset(&cfg, 0, sizeof(cfg));
    cfg.conn_cfg.conn_cfg_tag = APP_BLE_CONN_CFG_TAG;
    cfg.conn_cfg.params.gatts_conn_cfg.hvn_tx_queue_size = 16u;
    (void)sd_ble_cfg_set(BLE_CONN_CFG_GATTS, &cfg, ram_start);

    (void)sd_ble_enable(&ram_start);

    ble_gap_conn_sec_mode_t sec;
    BLE_GAP_CONN_SEC_MODE_SET_OPEN(&sec);
    static const uint8_t name[] = C08B_BLE_DEV_NAME;
    (void)sd_ble_gap_device_name_set(&sec, name, sizeof(name) - 1u);

    ble_uuid_t svc_uuid;
    add_v12_uuid(0x01u, &svc_uuid);
    (void)sd_ble_gatts_service_add(BLE_GATTS_SRVC_TYPE_PRIMARY, &svc_uuid, &g_svc_handle);

    uint8_t dummy[4] = {0};
    add_char(0x02u, false, false, true,  1u, C08B_F01_MAX_PKT_BYTES, dummy, &g_chr_data);
    add_char(0x03u, true,  false, false, 2u, 440u,                   (uint8_t *)"{}", &g_chr_meta);
    add_char(0x04u, true,  false, false, C08B_STATUS_BYTES, C08B_STATUS_BYTES, g_status_raw, &g_chr_status);
    add_char(0x05u, false, true,  false, 0u, 8u,                     dummy, &g_chr_ctrl);
    add_char(0x06u, false, false, true,  1u, C08B_IMU_PKT_BYTES,     dummy, &g_chr_imu);

    refresh_gatt_meta_and_status();
    ble_adv_start_now();
}

static bool ble_send_notify(uint16_t val_handle, bool subscribed, const uint8_t *pkt, uint16_t len)
{
    if (g_conn_handle == BLE_CONN_HANDLE_INVALID || !subscribed) return false;
    if (len + 3u > g_att_mtu) return false;
    uint16_t hvx_len = len;
    ble_gatts_hvx_params_t hvx = {
        .handle = val_handle,
        .type   = BLE_GATT_HVX_NOTIFICATION,
        .offset = 0,
        .p_len  = &hvx_len,
        .p_data = pkt,
    };
    return sd_ble_gatts_hvx(g_conn_handle, &hvx) == NRF_SUCCESS;
}

static void handle_ctrl_payload(const uint8_t *data, uint16_t len)
{
    if (len < 4u) return;
    uint8_t mode = c08b_parse_ctrl4(data);
    if (!mode) return;
    /* 可选第 5..6 字节覆盖采样率（如 "SYN1\xD0\x07" = 2000 Hz），第 7 字节选合成通道档 2/8/16 */
    if (len >= 6u) {
        uint16_t fs = (uint16_t)data[4] | ((uint16_t)data[5] << 8);
        if (fs == 500u || fs == 1000u || fs == 2000u) g_req_fs_hz = fs;
    }
    if (len >= 7u && (data[6] == 2u || data[6] == 8u || data[6] == 16u)) {
        g_synth_ch = data[6];
    }
    g_req_mode = mode;
    g_cmd_epoch++;
    if (mode != C08B_MODE_STOP && mode != C08B_MODE_PRB1) {
        bridge_reset_session();
    }
    spis_rearm_now();
    refresh_gatt_meta_and_status();
    logf_("BLE CONTROL 命令：mode=%u fs=%u epoch=%lu\n", mode, g_req_fs_hz, (unsigned long)g_cmd_epoch);
}

static void ble_poll_events(void)
{
    static uint32_t evt_buf[(sizeof(ble_evt_t) + 260u) / 4u];
    for (;;) {
        uint16_t len = sizeof(evt_buf);
        if (sd_ble_evt_get((uint8_t *)evt_buf, &len) != NRF_SUCCESS) break;
        const ble_evt_t *evt = (const ble_evt_t *)evt_buf;
        switch (evt->header.evt_id) {
        case BLE_GAP_EVT_CONNECTED: {
            g_conn_handle = evt->evt.gap_evt.conn_handle;
            g_att_mtu = 23u;
            g_ble_subscribed = false;
            g_imu_subscribed = false;
            g_conn_emg_started = false;
            g_conn_imu_started = false;
            ble_gap_phys_t phys = { .tx_phys = BLE_GAP_PHY_2MBPS, .rx_phys = BLE_GAP_PHY_2MBPS };
            (void)sd_ble_gap_phy_update(g_conn_handle, &phys);
            (void)sd_ble_gap_data_length_update(g_conn_handle, NULL, NULL);
            break;
        }
        case BLE_GAP_EVT_DISCONNECTED:
            g_conn_handle = BLE_CONN_HANDLE_INVALID;
            g_att_mtu = 23u;
            g_ble_subscribed = false;
            g_imu_subscribed = false;
            g_conn_emg_started = false;
            g_conn_imu_started = false;
            /* 断连一律停采并置 C08B_FAULT_CANCELLED(9)，绝不自动重连拼接同一佩戴段（AGENTS 铁律） */
            if (g_req_mode != C08B_MODE_IDLE && g_req_mode != C08B_MODE_STOP) {
                g_req_mode = C08B_MODE_STOP;
                g_cmd_epoch++;
                g_bridge.fault = C08B_FAULT_CANCELLED;
                spis_rearm_now();
            }
            ble_adv_start_now();
            break;
        case BLE_GAP_EVT_PHY_UPDATE_REQUEST: {
            ble_gap_phys_t phys = { .tx_phys = BLE_GAP_PHY_AUTO, .rx_phys = BLE_GAP_PHY_AUTO };
            (void)sd_ble_gap_phy_update(evt->evt.gap_evt.conn_handle, &phys);
            break;
        }
        case BLE_GAP_EVT_DATA_LENGTH_UPDATE_REQUEST:
            (void)sd_ble_gap_data_length_update(evt->evt.gap_evt.conn_handle, NULL, NULL);
            break;
        case BLE_GATTS_EVT_EXCHANGE_MTU_REQUEST: {
            uint16_t req = evt->evt.gatts_evt.params.exchange_mtu_request.client_rx_mtu;
            uint16_t reply = req < 23u ? 23u : (req > 247u ? 247u : req);
            if (sd_ble_gatts_exchange_mtu_reply(evt->evt.gatts_evt.conn_handle, reply) == NRF_SUCCESS)
                g_att_mtu = reply;
            break;
        }
        case BLE_GATTS_EVT_WRITE: {
            const ble_gatts_evt_write_t *w = &evt->evt.gatts_evt.params.write;
            if (w->handle == g_chr_data.cccd_handle && w->len >= 2u) {
                bool sub = ((w->data[0] & 0x01u) != 0u);
                g_ble_subscribed = sub;
                if (!sub) g_conn_emg_started = false;
                spis_rearm_now();
            } else if (w->handle == g_chr_imu.cccd_handle && w->len >= 2u) {
                bool sub = ((w->data[0] & 0x01u) != 0u);
                if (!sub) {
                    g_imu_subscribed = false;
                    g_conn_imu_started = false;
                } else if (!g_imu_subscribed) {
                    g_imu_subscribed = true;
                    g_bridge.imu_seq = 0;
                    g_conn_imu_started = false;
                }
            } else if (w->handle == g_chr_ctrl.value_handle) {
                handle_ctrl_payload(w->data, w->len);
            }
            break;
        }
        case BLE_GATTS_EVT_SYS_ATTR_MISSING:
            (void)sd_ble_gatts_sys_attr_set(evt->evt.gatts_evt.conn_handle, NULL, 0, 0);
            break;
        default:
            break;
        }
    }
}
#else
/* ==================== 免 SoftDevice 裸机联调档 ==================== */
static void ble_stack_init(void)
{
    NRF_CLOCK->EVENTS_HFCLKSTARTED = 0;
    NRF_CLOCK->TASKS_HFCLKSTART = 1;
    uint32_t t0 = g_ms;
    while (!NRF_CLOCK->EVENTS_HFCLKSTARTED && g_ms - t0 < 50u) {}
    /* 裸机联调档默认发一条 SYN1 让双核 SPI3<->SPIS1 跑通合成流 */
    bridge_reset_session();
    g_req_mode = C08B_MODE_SYN1;
    g_req_fs_hz = 1000u;
    g_synth_ch = 16u;
    g_cmd_epoch = 1u;
    g_ble_subscribed = true;
    g_imu_subscribed = true;
}
static void refresh_gatt_meta_and_status(void) {}
static void ble_poll_events(void) {}
static bool ble_send_notify(uint16_t h, bool sub, const uint8_t *p, uint16_t n)
{
    (void)h; (void)p; (void)n;
    return sub;
}
#endif

static void flush_pending_ble_packet(void)
{
    if (g_bridge.pend_count == 0) return;
    c08b_afe_mode_t m = g_bridge.afe_mode;
    if (m == AFE_NONE) {
        g_bridge.pend_count = 0;
        g_bridge.pend_flags = 0;
        return;
    }

    uint8_t flags = g_bridge.pend_flags;
    if ((flags & C08B_F01_SESSION_START) && g_conn_emg_started) {
        flags |= C08B_F01_RECONFIGURE;
    }

    uint8_t pkt[C08B_F01_MAX_PKT_BYTES];
    size_t plen = 0;
    if (m == AFE_16CH) {
        plen = c08b_pack_f01_v4_16ch(
            pkt, sizeof(pkt), g_bridge.pend_count, flags,
            g_bridge.pend_seq, g_bridge.pend_ts_us,
            (const uint8_t (*)[54])g_bridge.pend_slots);
    } else {
        uint8_t f8[8][27];
        for (uint8_t i = 0; i < g_bridge.pend_count; i++) {
            memcpy(f8[i], g_bridge.pend_slots[i], 27u);
        }
        plen = c08b_pack_f01_v1_8ch(
            pkt, sizeof(pkt), g_bridge.pend_count, flags,
            g_bridge.pend_seq, g_bridge.pend_ts_us,
            (const uint8_t (*)[27])f8);
    }

    if (plen > 0) {
#if C08B_USE_S140
        uint16_t h = g_chr_data.value_handle;
#else
        uint16_t h = 0;
#endif
        if (ble_send_notify(h, g_ble_subscribed, pkt, (uint16_t)plen)) {
            g_bridge.sent_samples += g_bridge.pend_count;
            if (flags & C08B_F01_SESSION_START) g_conn_emg_started = true;
        } else {
            g_bridge.notify_failures++;
            if (flags & C08B_F01_SESSION_START) {
                g_bridge.fault = C08B_FAULT_LINK_DROP;
                g_req_mode = C08B_MODE_STOP;
                g_cmd_epoch++;
                spis_rearm_now();
            }
        }
    }
    g_bridge.pend_count = 0;
    g_bridge.pend_flags = 0;
}

static void ingest_l432_frame(const c08b_link_tx_t *f)
{
    c08b_afe_mode_t prev_mode = g_bridge.afe_mode;
    g_bridge.afe_mode        = (c08b_afe_mode_t)f->afe_mode;
    g_bridge.fault           = f->fault;
    g_bridge.active          = (f->state_flags & C08B_SF_ACTIVE) != 0;
    g_bridge.produced        = f->produced;
    g_bridge.ring_dropped    = f->dropped;
    g_bridge.min_interval_us = (f->min_interval_us_sat == 0xFFFFu) ? 0xFFFFFFFFu : f->min_interval_us_sat;

    /* 一旦子板模式变化（如从 AFE_NONE 识别为 AFE_16CH/8CH/2CH），在发出第 1 条通知前先更新 GATT META/STATUS */
    if (prev_mode != g_bridge.afe_mode) {
        refresh_gatt_meta_and_status();
    }

    if (f->sample_count > 0 && g_bridge.afe_mode != AFE_NONE) {
        g_bridge.ads_status = ((uint32_t)f->samples[0][0] << 16) |
                              ((uint32_t)f->samples[0][1] << 8) |
                              (uint32_t)f->samples[0][2];

        /* 16CH 每包上限 4 帧（232B），8CH/2CH 每包上限 8 帧（232B） */
        uint8_t max_pkt_frames = (g_bridge.afe_mode == AFE_16CH) ? 4u : 8u;
        if ((f->f01_flags & C08B_F01_SESSION_START) && g_bridge.pend_count > 0) {
            flush_pending_ble_packet();
        }
        if (g_bridge.pend_count + f->sample_count > max_pkt_frames) {
            flush_pending_ble_packet();
        }
        if (g_bridge.pend_count == 0) {
            g_bridge.pend_seq   = f->seq_first;
            g_bridge.pend_ts_us = f->timestamp_us;
            g_bridge.pend_flags = f->f01_flags;
        }
        for (uint8_t i = 0; i < f->sample_count; i++) {
            memcpy(g_bridge.pend_slots[g_bridge.pend_count++], f->samples[i], 54u);
        }
        if (g_bridge.pend_count >= max_pkt_frames) {
            flush_pending_ble_packet();
        }
    } else if (!g_bridge.active && g_bridge.pend_count > 0) {
        flush_pending_ble_packet();
    }

    if (f->imu_fresh && g_imu_subscribed) {
        uint8_t imu_pkt[C08B_IMU_PKT_BYTES];
        int16_t imu_aligned[6];
        memcpy(imu_aligned, f->imu_raw, sizeof(imu_aligned));
        uint8_t iflags = (f->f01_flags & C08B_F01_SYNTHETIC);
        if (g_bridge.imu_seq == 0) {
            iflags |= C08B_F01_SESSION_START;
            if (g_conn_imu_started) iflags |= C08B_F01_RECONFIGURE;
        }
        if (c08b_pack_imu_pkt(imu_pkt, iflags, g_bridge.imu_seq,
                              f->imu_timestamp_us, imu_aligned, f->imu_read_us)) {
#if C08B_USE_S140
            uint16_t ih = g_chr_imu.value_handle;
#else
            uint16_t ih = 0;
#endif
            if (ble_send_notify(ih, g_imu_subscribed, imu_pkt, sizeof(imu_pkt))) {
                if (g_bridge.imu_seq == 0) g_conn_imu_started = true;
                g_bridge.imu_seq++;
            } else {
                g_bridge.notify_failures++;
            }
        }
    }
}

int main(void)
{
    /* 1. 第一条指令：锁住供电保持 PWR_HOLD，保持 BENCH_EN=0，OE_N 与 VBUS_SENSE 纯输入 */
    gpio_out(PWR_HOLD_PIN, 1);
    approtect_open();
    gpio_out(BENCH_EN_PIN, 0);
    gpio_out(LED_PIN, 0);
    gpio_in(BUTTON_N_PIN, GPIO_PIN_CNF_PULL_Disabled);
    gpio_in(CHRG_N_PIN, GPIO_PIN_CNF_PULL_Pullup);
    gpio_in(VBUS_SENSE_PIN, GPIO_PIN_CNF_PULL_Disabled);
    gpio_in(OE_N_PIN, GPIO_PIN_CNF_PULL_Disabled);

    SysTick_Config(SystemCoreClock / 1000u);
    timer2_init();
    rtt_init();
    uart_init();
    logf_("\nC08B nRF52840 流式无线固件启动（S140=%d, LOCK=%d, NAME=%s）\n",
          C08B_USE_S140, MAKO_BENCH_MEASURED, C08B_BLE_DEV_NAME);

    ble_stack_init();
    spis_init();

    int btn_armed = 0;
    uint32_t btn_t = 0, last_stat_ms = 0;

    for (;;) {
        uint32_t now = g_ms;
        ble_poll_events();

        /* 任何时刻在真实采集下检测到 USB VBUS，立即发 STOP 急停并置 INTERLOCK(3) */
        if (gpio_get(VBUS_SENSE_PIN) && g_req_mode != C08B_MODE_IDLE &&
            g_req_mode != C08B_MODE_STOP && g_req_mode != C08B_MODE_SYN1) {
            g_req_mode = C08B_MODE_STOP;
            g_cmd_epoch++;
            g_bridge.fault = C08B_FAULT_INTERLOCK;
            spis_rearm_now();
        } else if (calc_nrf_flags() != g_spis_tx.nrf_flags) {
            /* 一旦 OE_N 或 VBUS_SENSE 电平变化，立刻更新 SPIS1 预装帧（消除陈旧 OE_OFF=1） */
            spis_rearm_now();
        }

        if (NRF_SPIS1->EVENTS_END) {
            NRF_SPIS1->EVENTS_END = 0;
            gpio_set(LINK_RDY_PIN, 0);
            uint32_t tw = g_ms;
            while (!NRF_SPIS1->EVENTS_ACQUIRED && g_ms - tw < 5u) {}
            if (NRF_SPIS1->RXD.AMOUNT == sizeof(c08b_link_tx_t)) {
                c08b_link_tx_t snap = g_spis_rx;
                if (c08b_link_tx_ok(&snap)) {
                    ingest_l432_frame(&snap);
                }
            }
            spis_arm();
        }

        if (now - last_stat_ms >= 200u) {
            last_stat_ms = now;
            refresh_gatt_meta_and_status();
            (void)read_vbat_mv();
        }

        /* LED 指示（低有效）：采集中 4 Hz 快闪；有故障常亮告警；待机 0.5 Hz 呼吸慢闪 */
        int led_on = g_bridge.fault ? 1 : g_bridge.active ? ((now / 125u) & 1) : ((now / 1000u) == 0);
        gpio_set(LED_PIN, !led_on);

        /* 长按 3 s 关机（先松开一次再计时，防止上电按住开机误触发） */
        if (!gpio_get(BUTTON_N_PIN)) {
            if (btn_armed) {
                if (!btn_t) btn_t = now ? now : 1u;
                else if (now - btn_t > 3000u) {
                    logf_("按键长按 3 s，释放 PWR_HOLD 关机\n");
                    gpio_set(PWR_HOLD_PIN, 0);
                    btn_armed = 0;
                }
            }
        } else {
            btn_t = 0;
            btn_armed = 1;
        }
    }
}

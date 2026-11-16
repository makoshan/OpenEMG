/* C08B 无线聚合核 (nRF52840) -> Seeed XIAO nRF52840 Sense 真机联调固件
 *
 * 100% 复用 firmware/c08b-stream/common/stream_proto.h 与 nrf/main.c 核心状态机：
 *   1. 硬件 NRF_SPIS1 EasyDMA 从机（D6=LINK_RDY, D7=CSN, D8=SCK, D9=MISO, D10=MOSI）：
 *      焊好排针连上 6 根杜邦线后，无需重刷即可与蓝板 STM32L432KBU6 跑真 8 MHz SPI3 <-> SPIS1 硬件级联！
 *   2. 真实 S140 BLE GATT 外设广播 "YUANLI-C08B"（UUID 7b24c101-3948-4f03-9d11-12bb9d000001..06，MTU 247 / 2M PHY / DLE）：
 *      OpenEMG.app 或第 2 颗 MAKO-DONGLE 可直接无线发现并订阅 16ch F01 v4 + 104Hz IMU！
 *   3. 保留 TinyUSB CDC Serial（支持 1200bps 免按键自动重刷回 MAKO-DONGLE），并暴露双核免焊接虚拟排线桥 ('L') 与
 *      v12_dongle 兼容帧 ('Q'/'R'/'W'/'D' + kind=2 EMG / kind=6 IMU)，当场即可与真机 L432 跑双 MCU 闭环！
 */
#include <Arduino.h>
#include <bluefruit.h>

extern "C" {
#include "stream_proto.h"
#include "pins_xiao_hil.h"
}

/* ---------- 底层寄存器 GPIO 与 TIMER2 1MHz ---------- */
static NRF_GPIO_Type *gport(uint32_t p) { return (p >> 5) ? NRF_P1 : NRF_P0; }

static void gpio_out_raw(uint32_t p, int v)
{
    NRF_GPIO_Type *g = gport(p);
    uint32_t b = 1u << (p & 31);
    if (v) g->OUTSET = b; else g->OUTCLR = b;
    g->PIN_CNF[p & 31] = (GPIO_PIN_CNF_DIR_Output << GPIO_PIN_CNF_DIR_Pos) |
                         (GPIO_PIN_CNF_INPUT_Disconnect << GPIO_PIN_CNF_INPUT_Pos);
}

static void gpio_set_raw(uint32_t p, int v)
{
    NRF_GPIO_Type *g = gport(p);
    uint32_t b = 1u << (p & 31);
    if (v) g->OUTSET = b; else g->OUTCLR = b;
}

static void gpio_in_raw(uint32_t p, uint32_t pull)
{
    gport(p)->PIN_CNF[p & 31] = (GPIO_PIN_CNF_DIR_Input << GPIO_PIN_CNF_DIR_Pos) |
                                (GPIO_PIN_CNF_INPUT_Connect << GPIO_PIN_CNF_INPUT_Pos) |
                                (pull << GPIO_PIN_CNF_PULL_Pos);
}

static int gpio_get_raw(uint32_t p) { return (int)((gport(p)->IN >> (p & 31)) & 1u); }

static void timer2_init(void)
{
    NRF_TIMER2->TASKS_STOP = 1;
    NRF_TIMER2->MODE = TIMER_MODE_MODE_Timer;
    NRF_TIMER2->BITMODE = TIMER_BITMODE_BITMODE_32Bit;
    NRF_TIMER2->PRESCALER = 4u; /* 16 MHz / 16 = 1 MHz */
    NRF_TIMER2->TASKS_CLEAR = 1;
    NRF_TIMER2->TASKS_START = 1;
}

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

/* ---------- V12 BLE GATT 服务与特征 ---------- */
static BLEService        c08b_svc("7b24c101-3948-4f03-9d11-12bb9d000001");
static BLECharacteristic chr_data("7b24c101-3948-4f03-9d11-12bb9d000002");
static BLECharacteristic chr_meta("7b24c101-3948-4f03-9d11-12bb9d000003");
static BLECharacteristic chr_stat("7b24c101-3948-4f03-9d11-12bb9d000004");
static BLECharacteristic chr_ctrl("7b24c101-3948-4f03-9d11-12bb9d000005");
static BLECharacteristic chr_imu ("7b24c101-3948-4f03-9d11-12bb9d000006");

static volatile uint16_t g_conn_handle = BLE_CONN_HANDLE_INVALID;
static bool     g_usb_subscribed = false;
static uint32_t g_spis_hw_frames = 0;
static uint32_t g_usb_hil_frames = 0;
static uint32_t g_crc_bad_frames = 0;

/* ---------- 板载真实物理 LSM6DS3TR-C (0x6A, NRF_TWIM0 400kHz, 与 SPIS1 0x40004000 完全独立) ---------- */
static bool     g_xiao_imu_ok = false;
static uint8_t  g_xiao_imu_who = 0;
static int16_t  g_xiao_imu_latest[6] = {0, 0, 0, 0, 0, 4096};
static uint16_t g_xiao_imu_read_us = 0;
static uint32_t g_xiao_imu_frames = 0;
static uint32_t g_last_xiao_imu_ms = 0;

static bool twim0_xfer(uint8_t addr, const uint8_t *tx, uint32_t txn, uint8_t *rx, uint32_t rxn)
{
    NRF_TWIM0->ADDRESS = addr;
    NRF_TWIM0->EVENTS_STOPPED = 0;
    NRF_TWIM0->EVENTS_ERROR = 0;
    NRF_TWIM0->EVENTS_LASTTX = 0;
    NRF_TWIM0->EVENTS_LASTRX = 0;
    NRF_TWIM0->ERRORSRC = NRF_TWIM0->ERRORSRC;
    NRF_TWIM0->TXD.PTR = (uint32_t)(uintptr_t)tx;
    NRF_TWIM0->TXD.MAXCNT = txn;
    NRF_TWIM0->RXD.PTR = (uint32_t)(uintptr_t)rx;
    NRF_TWIM0->RXD.MAXCNT = rxn;
    NRF_TWIM0->SHORTS = rxn
        ? (TWIM_SHORTS_LASTTX_STARTRX_Msk | TWIM_SHORTS_LASTRX_STOP_Msk)
        : TWIM_SHORTS_LASTTX_STOP_Msk;
    __DMB();
    NRF_TWIM0->TASKS_STARTTX = 1;
    uint32_t t0 = timer2_us();
    while (!NRF_TWIM0->EVENTS_STOPPED) {
        if (NRF_TWIM0->EVENTS_ERROR || (timer2_us() - t0) > 3000u) {
            NRF_TWIM0->TASKS_RESUME = 1;
            NRF_TWIM0->TASKS_STOP = 1;
            return false;
        }
    }
    __DMB();
    if (NRF_TWIM0->EVENTS_ERROR || NRF_TWIM0->TXD.AMOUNT != txn) return false;
    if (rxn && NRF_TWIM0->RXD.AMOUNT != rxn) return false;
    return true;
}

static void xiao_imu_init(void)
{
    /* XIAO Sense 板载 LSM6DS3TR-C 由 P1.08 直接供电，必须配 H0H1 高驱动 */
    NRF_P1->OUTSET = (1u << 8);
    NRF_P1->PIN_CNF[8] = (GPIO_PIN_CNF_DIR_Output << GPIO_PIN_CNF_DIR_Pos) |
                         (GPIO_PIN_CNF_INPUT_Disconnect << GPIO_PIN_CNF_INPUT_Pos) |
                         (GPIO_PIN_CNF_DRIVE_H0H1 << GPIO_PIN_CNF_DRIVE_Pos);
    delay(25);
    const uint32_t i2c_cnf = (GPIO_PIN_CNF_DIR_Input << GPIO_PIN_CNF_DIR_Pos) |
                             (GPIO_PIN_CNF_INPUT_Connect << GPIO_PIN_CNF_INPUT_Pos) |
                             (GPIO_PIN_CNF_PULL_Pullup << GPIO_PIN_CNF_PULL_Pos) |
                             (GPIO_PIN_CNF_DRIVE_S0D1 << GPIO_PIN_CNF_DRIVE_Pos) |
                             (GPIO_PIN_CNF_SENSE_Disabled << GPIO_PIN_CNF_SENSE_Pos);
    NRF_P0->PIN_CNF[7]  = i2c_cnf; /* SDA = P0.07 */
    NRF_P0->PIN_CNF[27] = i2c_cnf; /* SCL = P0.27 */
    NRF_TWIM0->ENABLE = 0;
    NRF_TWIM0->PSEL.SDA = 7u;
    NRF_TWIM0->PSEL.SCL = 27u;
    NRF_TWIM0->INTENCLR = 0xFFFFFFFFu;
    NRF_TWIM0->FREQUENCY = TWIM_FREQUENCY_FREQUENCY_K400;
    NRF_TWIM0->ENABLE = TWIM_ENABLE_ENABLE_Enabled;

    uint8_t reg_who = 0x0Fu, who = 0;
    if (!twim0_xfer(0x6Au, &reg_who, 1, &who, 1)) return;
    g_xiao_imu_who = who;
    if (who != 0x6Au) return;

    /* 与 C08B L432 imu_setup_stream 逐寄存器一致：BDU+IF_INC, 104Hz ±8g, 104Hz ±1000dps */
    const uint8_t c3[2] = {0x12u, 0x44u};
    const uint8_t c1[2] = {0x10u, 0x4Cu};
    const uint8_t c2[2] = {0x11u, 0x48u};
    if (!twim0_xfer(0x6Au, c3, 2, nullptr, 0)) return;
    if (!twim0_xfer(0x6Au, c1, 2, nullptr, 0)) return;
    if (!twim0_xfer(0x6Au, c2, 2, nullptr, 0)) return;
    delay(15);
    g_xiao_imu_ok = true;
}

static void xiao_imu_poll(void)
{
    if (!g_xiao_imu_ok) return;
    uint32_t now_ms = millis();
    if (now_ms - g_last_xiao_imu_ms < 7u) return;
    uint32_t t0 = timer2_us();
    uint8_t reg_st = 0x1Eu, st = 0;
    if (!twim0_xfer(0x6Au, &reg_st, 1, &st, 1)) return;
    if ((st & 0x03u) != 0x03u) return;
    uint8_t reg_out = 0x22u, raw[12];
    if (!twim0_xfer(0x6Au, &reg_out, 1, raw, 12)) return;
    uint32_t dt = timer2_us() - t0;
    for (int i = 0; i < 6; i++) {
        g_xiao_imu_latest[i] = (int16_t)((uint16_t)raw[2 * i] | ((uint16_t)raw[2 * i + 1] << 8));
    }
    g_xiao_imu_read_us = (dt > 8999u) ? 8999u : (uint16_t)dt;
    g_xiao_imu_frames++;
    g_last_xiao_imu_ms = now_ms;
}

/* ---------- SPIS1 从机状态与 C08B 聚合状态（与 nrf/main.c 完全同构） ---------- */
volatile c08b_link_tx_t g_spis_rx;
static c08b_link_rx_t   g_spis_tx;

static uint8_t  g_req_mode = C08B_MODE_IDLE;
static uint8_t  g_synth_ch = 16u;
static uint8_t  g_reg_addr = 0u;
static uint8_t  g_reg_val  = 0u;
static uint16_t g_req_fs_hz = 1000u;
static bool     g_req_fs_explicit = false;
static uint32_t g_cmd_epoch = 0;
static uint16_t g_await_epoch_lo = 0;
static bool     g_conn_emg_started = false;
static bool     g_conn_imu_started = false;

static char     g_meta_json[512];
static uint8_t  g_status_raw[C08B_STATUS_BYTES];

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
    c08b_reg_reply_t reg_reply;
    c08b_afe_mode_t pend_mode;
    uint8_t         pend_count;
    uint8_t         pend_flags;
    uint32_t        pend_seq;
    uint64_t        pend_ts_us;
    uint8_t         pend_slots[8][54];
} g_bridge;

/* ---------- USB CDC 0xA5 环形发送缓冲（避免阻塞 SPIS1 / BLE） ---------- */
static const uint32_t USB_RING = 32768;
static uint8_t  usb_ring[USB_RING];
static uint32_t usb_head = 0, usb_tail = 0, usb_drops = 0, usb_notifies = 0;

static void usb_queue_frame(uint8_t kind, const void *payload, uint16_t len)
{
    uint32_t need = 8u + len;
    uint32_t used = usb_head - usb_tail;
    if (USB_RING - used < need) {
        usb_drops++;
        return;
    }
    uint32_t t = timer2_us();
    uint8_t hdr[8] = {
        0xA5, kind,
        (uint8_t)len, (uint8_t)(len >> 8),
        (uint8_t)t, (uint8_t)(t >> 8), (uint8_t)(t >> 16), (uint8_t)(t >> 24)
    };
    uint32_t h = usb_head;
    for (uint32_t i = 0; i < 8; i++) usb_ring[(h + i) % USB_RING] = hdr[i];
    const uint8_t *p = (const uint8_t *)payload;
    for (uint32_t i = 0; i < len; i++) usb_ring[(h + 8 + i) % USB_RING] = p[i];
    usb_head = h + need;
}

static void usb_drain(void)
{
    if (!Serial) {
        usb_tail = usb_head;
        return;
    }
    while (usb_tail != usb_head) {
        uint32_t off = usb_tail % USB_RING;
        uint32_t n = min(usb_head - usb_tail, USB_RING - off);
        if (n > 512) n = 512;
        int avail = Serial.availableForWrite();
        if (avail <= 0) break;
        if (n > (uint32_t)avail) n = (uint32_t)avail;
        size_t w = Serial.write(usb_ring + off, n);
        if (!w) break;
        usb_tail += w;
    }
}

static bool any_emg_subscribed(void)
{
    bool ble_sub = (g_conn_handle != BLE_CONN_HANDLE_INVALID) && chr_data.notifyEnabled(g_conn_handle);
    return ble_sub || g_usb_subscribed;
}

static bool any_imu_subscribed(void)
{
    bool ble_sub = (g_conn_handle != BLE_CONN_HANDLE_INVALID) && chr_imu.notifyEnabled(g_conn_handle);
    return ble_sub || g_usb_subscribed;
}

static uint8_t calc_nrf_flags(void)
{
    uint8_t nf = 0;
    if (gpio_get_raw(VBUS_SENSE_PIN)) nf |= C08B_NF_VBUS_INTERLOCK;
    if (gpio_get_raw(OE_N_PIN))       nf |= C08B_NF_OE_OFF;
    if (any_emg_subscribed())         nf |= C08B_NF_BLE_SUBSCRIBED;
    if (any_imu_subscribed())         nf |= C08B_NF_IMU_SUBSCRIBED;
    if (g_req_fs_explicit)            nf |= C08B_NF_EXPLICIT_FS;
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
    g_spis_tx.reg_addr = g_reg_addr;
    g_spis_tx.reg_val = g_reg_val;
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
    gpio_set_raw(LINK_RDY_PIN, 1);
}

static void spis_rearm_now(void)
{
    spis_refresh_tx_cmd();
    if (!gpio_get_raw(LINK_CS_PIN)) return;
    gpio_set_raw(LINK_RDY_PIN, 0);
    delay_us_nrf(3u);
    if (!gpio_get_raw(LINK_CS_PIN)) {
        gpio_set_raw(LINK_RDY_PIN, 1);
        return;
    }
    NRF_SPIS1->EVENTS_ACQUIRED = 0;
    NRF_SPIS1->TASKS_ACQUIRE = 1;
    uint32_t t0 = millis();
    while (!NRF_SPIS1->EVENTS_ACQUIRED && (millis() - t0) < 5u) {}
    spis_arm();
}

static void spis_init(void)
{
    gpio_in_raw(LINK_CS_PIN, GPIO_PIN_CNF_PULL_Pullup);
    gpio_out_raw(LINK_RDY_PIN, 0);
    NRF_SPIS1->PSEL.SCK  = LINK_SCK_PIN;
    NRF_SPIS1->PSEL.MOSI = LINK_MOSI_PIN;
    NRF_SPIS1->PSEL.MISO = LINK_MISO_PIN;
    NRF_SPIS1->PSEL.CSN  = LINK_CS_PIN;
    NRF_SPIS1->CONFIG = 0;
    NRF_SPIS1->DEF = 0xFFu;
    NRF_SPIS1->ORC = 0xFFu;
    NRF_SPIS1->SHORTS = SPIS_SHORTS_END_ACQUIRE_Msk;
    NRF_SPIS1->ENABLE = SPIS_ENABLE_ENABLE_Enabled;
    NRF_SPIS1->EVENTS_ACQUIRED = 0;
    NRF_SPIS1->TASKS_ACQUIRE = 1;
    uint32_t t0 = millis();
    while (!NRF_SPIS1->EVENTS_ACQUIRED && (millis() - t0) < 10u) {}
    spis_arm();
}

static void bridge_reset_session(void)
{
    g_bridge.sent_samples = 0;
    g_bridge.notify_failures = 0;
    g_bridge.imu_seq = 0;
    g_bridge.pend_mode = AFE_NONE;
    g_bridge.pend_count = 0;
    g_bridge.pend_flags = 0;
}

static int refresh_gatt_meta_and_status(void)
{
    c08b_afe_mode_t m = g_bridge.afe_mode;
    int mlen = c08b_format_meta_json_ex(
        g_meta_json, sizeof(g_meta_json), m, g_req_fs_hz,
        MAKO_BENCH_MEASURED != 0, true, &g_bridge.reg_reply);
    if (mlen > 0) {
        chr_meta.write(g_meta_json, (uint16_t)mlen);
    }
    c08b_ble_status_t st = {
        .produced             = g_bridge.produced,
        .ring_dropped         = g_bridge.ring_dropped,
        .scheduler_skipped    = 0,
        .sent_samples         = g_bridge.sent_samples,
        .notify_failures      = g_bridge.notify_failures,
        .fault                = g_bridge.fault,
        .active               = g_bridge.active,
        .bench_measured       = (MAKO_BENCH_MEASURED != 0),
        .ads_status           = g_bridge.ads_status,
        .drdy_raw_edges       = g_bridge.produced,
        .drdy_min_interval_us = g_bridge.min_interval_us,
        .spi_hz               = c08b_spi_hz_for_mode(m),
    };
    c08b_encode_ble_status(g_status_raw, &st);
    chr_stat.write(g_status_raw, sizeof(g_status_raw));
    return mlen;
}

static bool dispatch_emg_or_imu_notify(bool is_imu, const uint8_t *pkt, uint16_t len)
{
    bool ok = false;
    if (g_conn_handle != BLE_CONN_HANDLE_INVALID) {
        BLECharacteristic &c = is_imu ? chr_imu : chr_data;
        if (c.notifyEnabled(g_conn_handle)) {
            if (c.notify(g_conn_handle, pkt, len)) ok = true;
        }
    }
    if (g_usb_subscribed) {
        usb_queue_frame(is_imu ? 6u : 2u, pkt, len);
        usb_notifies++;
        ok = true;
    }
    return ok;
}

static void flush_pending_ble_packet(void)
{
    if (g_bridge.pend_count == 0) return;
    c08b_afe_mode_t m = g_bridge.pend_mode ? g_bridge.pend_mode : g_bridge.afe_mode;
    if (m == AFE_NONE) {
        g_bridge.pend_mode = AFE_NONE;
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
        if (dispatch_emg_or_imu_notify(false, pkt, (uint16_t)plen)) {
            g_bridge.sent_samples += g_bridge.pend_count;
            if (flags & C08B_F01_SESSION_START) g_conn_emg_started = true;
        } else if (any_emg_subscribed()) {
            g_bridge.notify_failures++;
            if (flags & C08B_F01_SESSION_START) {
                g_bridge.fault = C08B_FAULT_LINK_DROP;
                g_req_mode = C08B_MODE_STOP;
                g_cmd_epoch = c08b_next_cmd_epoch(g_cmd_epoch);
                g_await_epoch_lo = (uint16_t)g_cmd_epoch;
                spis_rearm_now();
            }
        }
    }
    g_bridge.pend_mode = AFE_NONE;
    g_bridge.pend_count = 0;
    g_bridge.pend_flags = 0;
}

static void ingest_l432_frame(const c08b_link_tx_t *f)
{
    if (!c08b_bridge_accept_frame(f, &g_await_epoch_lo)) {
        if (f->fault == C08B_FAULT_INTERLOCK) g_bridge.fault = f->fault;
        return;
    }

    c08b_afe_mode_t prev_mode   = g_bridge.afe_mode;
    uint8_t         prev_fault  = g_bridge.fault;
    bool            prev_active = g_bridge.active;
    if (g_bridge.pend_count > 0 && g_bridge.pend_mode != (c08b_afe_mode_t)f->afe_mode) {
        flush_pending_ble_packet();
    }
    g_bridge.afe_mode        = (c08b_afe_mode_t)f->afe_mode;
    g_bridge.fault           = (gpio_get_raw(VBUS_SENSE_PIN) && g_bridge.fault == C08B_FAULT_INTERLOCK &&
                                f->fault == C08B_FAULT_NONE) ? C08B_FAULT_INTERLOCK : f->fault;
    g_bridge.active          = (f->state_flags & C08B_SF_ACTIVE) != 0;
    g_bridge.produced        = f->produced;
    g_bridge.ring_dropped    = f->dropped;
    g_bridge.min_interval_us = (f->min_interval_us_sat == 0xFFFFu) ? 0xFFFFFFFFu : f->min_interval_us_sat;

    bool reg_changed = false;
    c08b_reg_reply_t rrep;
    if (c08b_link_tx_get_reg_reply(f, &rrep)) {
        if ((g_req_mode == C08B_MODE_RREG || g_req_mode == C08B_MODE_WREG) &&
            rrep.valid && rrep.seq != (uint16_t)g_cmd_epoch) {
            rrep.valid = false;
        }
        if (rrep.has_eff_cfg && g_req_mode != C08B_MODE_SYN1 &&
            (rrep.eff_fs_hz == 500u || rrep.eff_fs_hz == 1000u || rrep.eff_fs_hz == 2000u) &&
            g_req_fs_hz != rrep.eff_fs_hz) {
            g_req_fs_hz = rrep.eff_fs_hz;
            reg_changed = true;
        }
        if (rrep.valid != g_bridge.reg_reply.valid ||
            rrep.seq != g_bridge.reg_reply.seq ||
            rrep.addr != g_bridge.reg_reply.addr ||
            rrep.val_a != g_bridge.reg_reply.val_a ||
            rrep.val_b != g_bridge.reg_reply.val_b ||
            rrep.ovr_count != g_bridge.reg_reply.ovr_count ||
            rrep.has_eff_cfg != g_bridge.reg_reply.has_eff_cfg ||
            rrep.eff_fs_hz != g_bridge.reg_reply.eff_fs_hz ||
            memcmp(rrep.ch_gains, g_bridge.reg_reply.ch_gains, sizeof(rrep.ch_gains)) != 0) {
            g_bridge.reg_reply = rrep;
            reg_changed = true;
        }
    }

    if (prev_mode != g_bridge.afe_mode || prev_fault != g_bridge.fault || prev_active != g_bridge.active || reg_changed) {
        refresh_gatt_meta_and_status();
    }

    if (f->sample_count > 0 && g_bridge.afe_mode != AFE_NONE) {
        for (uint8_t i = 0; i < f->sample_count; i++) {
            if (!c08b_slot_status_valid(f->samples[i], g_bridge.afe_mode)) {
                g_bridge.ads_status = ((uint32_t)f->samples[i][0] << 16) |
                                      ((uint32_t)f->samples[i][1] << 8) |
                                      (uint32_t)f->samples[i][2];
                g_bridge.pend_mode  = AFE_NONE;
                g_bridge.pend_count = 0;
                g_bridge.pend_flags = 0;
                g_bridge.active     = false;
                g_bridge.fault      = gpio_get_raw(VBUS_SENSE_PIN) ? C08B_FAULT_INTERLOCK : C08B_FAULT_BAD_FRAME;
                g_req_mode          = C08B_MODE_STOP;
                g_cmd_epoch         = c08b_next_cmd_epoch(g_cmd_epoch);
                g_await_epoch_lo    = (uint16_t)g_cmd_epoch;
                spis_rearm_now();
                refresh_gatt_meta_and_status();
                return;
            }
        }

        g_bridge.ads_status = ((uint32_t)f->samples[0][0] << 16) |
                              ((uint32_t)f->samples[0][1] << 8) |
                              (uint32_t)f->samples[0][2];

        uint8_t max_pkt_frames = (g_bridge.afe_mode == AFE_16CH) ? 4u : 8u;
        if ((f->f01_flags & C08B_F01_SESSION_START) && g_bridge.pend_count > 0) {
            flush_pending_ble_packet();
        }
        if (g_bridge.pend_count > 0 &&
            (g_bridge.pend_count + f->sample_count > max_pkt_frames ||
             f->seq_first != g_bridge.pend_seq + g_bridge.pend_count)) {
            flush_pending_ble_packet();
        }
        if (g_bridge.pend_count == 0) {
            g_bridge.pend_mode  = g_bridge.afe_mode;
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

    if (f->imu_fresh && any_imu_subscribed()) {
        uint8_t imu_pkt[C08B_IMU_PKT_BYTES];
        int16_t imu_aligned[6];
        uint16_t read_us = f->imu_read_us;
        if (((f->state_flags & C08B_SF_IMU_OK) == 0) && g_xiao_imu_ok && g_xiao_imu_frames > 0) {
            /* 蓝板 L432 裸板未焊外部 IMU 时，自动融合 XIAO Sense 板载真物理 LSM6DS3TR-C (0x6A) 实测 6 轴数据，保留 L432 DWT 1MHz 时间戳 */
            memcpy(imu_aligned, g_xiao_imu_latest, sizeof(imu_aligned));
            read_us = g_xiao_imu_read_us;
        } else {
            memcpy(imu_aligned, f->imu_raw, sizeof(imu_aligned));
        }
        uint8_t iflags = (f->f01_flags & C08B_F01_SYNTHETIC);
        if (g_bridge.imu_seq == 0) {
            iflags |= C08B_F01_SESSION_START;
            if (g_conn_imu_started) iflags |= C08B_F01_RECONFIGURE;
        }
        if (c08b_pack_imu_pkt(imu_pkt, iflags, g_bridge.imu_seq,
                              f->imu_timestamp_us, imu_aligned, read_us)) {
            if (dispatch_emg_or_imu_notify(true, imu_pkt, sizeof(imu_pkt))) {
                if (g_bridge.imu_seq == 0) g_conn_imu_started = true;
                g_bridge.imu_seq++;
            } else {
                g_bridge.notify_failures++;
            }
        }
    }
}

static void handle_ctrl_payload(const uint8_t *data, uint16_t len)
{
    if (len < 4u) return;
    uint8_t mode = c08b_parse_ctrl4(data);
    if (!mode) return;
    flush_pending_ble_packet();

    if (mode == C08B_MODE_RREG) {
        if (len != 6u || data[4] > C08B_CHIP_BOTH || data[5] > 0x19u) {
            g_bridge.reg_reply.valid = false;
            g_bridge.fault = C08B_FAULT_ARG;
            refresh_gatt_meta_and_status();
            return;
        }
        g_req_fs_explicit = false;
        g_synth_ch = data[4];
        g_reg_addr = data[5];
        g_reg_val  = 0u;
    } else if (mode == C08B_MODE_WREG) {
        if (len != 7u || data[4] > C08B_CHIP_BOTH || data[5] > 0x19u) {
            g_bridge.reg_reply.valid = false;
            g_bridge.fault = C08B_FAULT_ARG;
            refresh_gatt_meta_and_status();
            return;
        }
        g_req_fs_explicit = false;
        g_synth_ch = data[4];
        g_reg_addr = data[5];
        g_reg_val  = data[6];
    } else if (mode == C08B_MODE_CLRO) {
        if (len != 4u) {
            g_bridge.fault = C08B_FAULT_ARG;
            refresh_gatt_meta_and_status();
            return;
        }
        g_req_fs_explicit = false;
    } else {
        g_req_fs_explicit = (len >= 6u && mode != C08B_MODE_PRB1);
        if (len >= 6u) {
            uint16_t fs = (uint16_t)data[4] | ((uint16_t)data[5] << 8);
            if (fs == 500u || fs == 1000u || fs == 2000u) {
                g_req_fs_hz = fs;
            } else {
                g_bridge.fault = C08B_FAULT_ARG;
                refresh_gatt_meta_and_status();
                return;
            }
        }
        if (len >= 7u && (data[6] == 2u || data[6] == 8u || data[6] == 16u)) {
            g_synth_ch = data[6];
        }
    }

    bool unlocked = (MAKO_C08B_AFE_ENABLED != 0) && (MAKO_BENCH_MEASURED != 0);
    bool vbus_on = gpio_get_raw(VBUS_SENSE_PIN) != 0;
    c08b_fault_t local_gate = c08b_gate_mode_request(mode, g_req_fs_hz, unlocked, vbus_on);

    g_req_mode = mode;
    g_cmd_epoch = c08b_next_cmd_epoch(g_cmd_epoch);
    g_await_epoch_lo = (uint16_t)g_cmd_epoch;
    if (mode == C08B_MODE_STOP) {
        g_bridge.active = false;
        if (!vbus_on) g_bridge.fault = C08B_FAULT_NONE;
    } else if (mode == C08B_MODE_CLRO) {
        if (!g_bridge.reg_reply.valid && g_bridge.reg_reply.ovr_count == 0u) {
            g_bridge.reg_reply.ovr_count = 1u;
        }
        g_bridge.active = false;
        if (!vbus_on) g_bridge.fault = C08B_FAULT_NONE;
    } else if (local_gate != C08B_FAULT_NONE) {
        if (mode == C08B_MODE_RREG || mode == C08B_MODE_WREG) g_bridge.reg_reply.valid = false;
        g_bridge.active = false;
        g_bridge.fault = (uint8_t)local_gate;
    } else if (mode == C08B_MODE_RREG || mode == C08B_MODE_WREG) {
        g_bridge.reg_reply.valid = false;
        g_bridge.active = false;
        g_bridge.fault = C08B_FAULT_NONE;
    } else if (mode == C08B_MODE_PRB1) {
        g_bridge.active = false;
        g_bridge.fault = C08B_FAULT_NONE;
    } else {
        bridge_reset_session();
    }
    spis_rearm_now();
    refresh_gatt_meta_and_status();
}

static void on_ctrl_write(uint16_t conn_hdl, BLECharacteristic *chr, uint8_t *data, uint16_t len)
{
    (void)conn_hdl; (void)chr;
    handle_ctrl_payload(data, len);
}

static void on_ble_connect(uint16_t conn_handle)
{
    g_conn_handle = conn_handle;
    g_conn_emg_started = false;
    g_conn_imu_started = false;
    BLEConnection *conn = Bluefruit.Connection(conn_handle);
    if (conn) {
        conn->requestPHY(BLE_GAP_PHY_2MBPS);
        conn->requestDataLengthUpdate();
    }
    spis_rearm_now();
}

static void on_ble_disconnect(uint16_t conn_handle, uint8_t reason)
{
    (void)conn_handle; (void)reason;
    g_conn_handle = BLE_CONN_HANDLE_INVALID;
    g_conn_emg_started = false;
    g_conn_imu_started = false;
    g_bridge.pend_mode = AFE_NONE;
    g_bridge.pend_count = 0;
    g_bridge.pend_flags = 0;
    if (g_req_mode != C08B_MODE_IDLE && g_req_mode != C08B_MODE_STOP && !g_usb_subscribed) {
        g_req_mode = C08B_MODE_STOP;
        g_cmd_epoch = c08b_next_cmd_epoch(g_cmd_epoch);
        g_await_epoch_lo = (uint16_t)g_cmd_epoch;
        g_bridge.fault = C08B_FAULT_CANCELLED;
        spis_rearm_now();
    }
}

/* ---------- USB CDC 命令解析 ---------- */
static uint8_t s_cmd[320];
static uint16_t s_len = 0;

static void send_usb_link_info(void)
{
    uint8_t b[26] = {0};
    b[0] = 1; /* ready = 1 */
    uint16_t ci = 6, mtu = 247, dl = 251, want_ci = 6;
    uint8_t phy = 2;
    uint32_t cn = 1;
    memcpy(b + 1, &ci, 2);
    b[3] = phy;
    memcpy(b + 4, &mtu, 2);
    memcpy(b + 6, &dl, 2);
    memcpy(b + 8, &want_ci, 2);
    memcpy(b + 10, &usb_drops, 4);
    memcpy(b + 14, &usb_notifies, 4);
    memcpy(b + 18, &g_spis_hw_frames, 4);
    memcpy(b + 22, &cn, 4);
    usb_queue_frame(0x11u, b, 26);
}

static void handle_usb_cmd(uint8_t op, const uint8_t *p, uint16_t len)
{
    uint8_t r[560];
    r[0] = 1;
    uint16_t n = 1;

    if (op == 'L') {
        /* 双核免焊接虚拟排线帧交换：输入 280B c08b_link_tx_t，返回 16B c08b_link_rx_t */
        if (len == sizeof(c08b_link_tx_t)) {
            c08b_link_tx_t snap;
            memcpy(&snap, p, sizeof(snap));
            if (c08b_link_tx_ok(&snap)) {
                g_usb_hil_frames++;
                ingest_l432_frame(&snap);
                r[0] = 0;
            } else {
                g_crc_bad_frames++;
                r[0] = 2;
            }
        } else if (len == 0) {
            r[0] = 0;
        }
        spis_refresh_tx_cmd();
        memcpy(r + 1, &g_spis_tx, sizeof(g_spis_tx));
        n = 1u + sizeof(g_spis_tx);
    } else if (op == 'W') {
        g_usb_subscribed = true;
        handle_ctrl_payload(p, len);
        r[0] = 0;
    } else if (op == 'R' && len == 1 && (p[0] == 3 || p[0] == 4)) {
        int mlen = refresh_gatt_meta_and_status();
        if (p[0] == 3 && mlen > 0) {
            r[0] = 0;
            memcpy(r + 1, g_meta_json, (uint16_t)mlen);
            n = 1u + (uint16_t)mlen;
        } else if (p[0] == 4) {
            r[0] = 0;
            memcpy(r + 1, g_status_raw, C08B_STATUS_BYTES);
            n = 1u + C08B_STATUS_BYTES;
        }
    } else if (op == 'D') {
        g_usb_subscribed = false;
        g_conn_emg_started = false;
        g_conn_imu_started = false;
        const uint8_t stop4[4] = {'S', 'T', 'O', 'P'};
        handle_ctrl_payload(stop4, 4);
        g_bridge.fault = C08B_FAULT_NONE;
        refresh_gatt_meta_and_status();
        r[0] = 0;
    } else if (op == 'Q') {
        send_usb_link_info();
        r[0] = 0;
    } else if (op == 'S') {
        /* 内部诊断计数器查询 */
        r[0] = 0;
        memcpy(r + 1,  &g_spis_hw_frames, 4);
        memcpy(r + 5,  &g_usb_hil_frames, 4);
        memcpy(r + 9,  &g_crc_bad_frames, 4);
        memcpy(r + 13, &usb_notifies, 4);
        n = 17;
    } else if (op == 'I') {
        /* 板载真实物理 LSM6DS3TR-C (0x6A) 状态与最新 6 轴原始读数查询 */
        r[0] = 0;
        r[1] = g_xiao_imu_ok ? 1u : 0u;
        r[2] = g_xiao_imu_who;
        memcpy(r + 3,  &g_xiao_imu_read_us, 2);
        memcpy(r + 5,  &g_xiao_imu_frames, 4);
        memcpy(r + 9,  g_xiao_imu_latest, 12);
        n = 21;
    }
    usb_queue_frame(0x80u | op, r, n);
}

static void poll_usb_serial(void)
{
    while (Serial.available()) {
        int c = Serial.read();
        if (s_len == 0 && c != 0xA5) continue;
        s_cmd[s_len++] = (uint8_t)c;
        if (s_len >= 4) {
            uint16_t plen = (uint16_t)s_cmd[2] | ((uint16_t)s_cmd[3] << 8);
            if (plen > sizeof(s_cmd) - 4u) {
                s_len = 0;
                continue;
            }
            if (s_len == 4u + plen) {
                handle_usb_cmd(s_cmd[1], s_cmd + 4, plen);
                s_len = 0;
            }
        }
    }
}

void setup()
{
    gpio_out_raw(PWR_HOLD_PIN, 1);
    gpio_out_raw(BENCH_EN_PIN, 0);
    gpio_out_raw(LED_PIN, 1); /* 低有效红灯先灭 */
    gpio_in_raw(BUTTON_N_PIN, GPIO_PIN_CNF_PULL_Pullup);
    gpio_in_raw(CHRG_N_PIN, GPIO_PIN_CNF_PULL_Pullup);
    gpio_in_raw(VBUS_SENSE_PIN, GPIO_PIN_CNF_PULL_Pulldown);
    gpio_in_raw(OE_N_PIN, GPIO_PIN_CNF_PULL_Pulldown);

    Serial.begin(115200);
    timer2_init();
    xiao_imu_init();

    Bluefruit.configPrphBandwidth(BANDWIDTH_MAX);
    Bluefruit.begin(1, 0);
    Bluefruit.setTxPower(4);
    Bluefruit.setName(C08B_BLE_DEV_NAME);
    Bluefruit.Periph.setConnectCallback(on_ble_connect);
    Bluefruit.Periph.setDisconnectCallback(on_ble_disconnect);

    c08b_svc.begin();

    chr_data.setProperties(CHR_PROPS_NOTIFY);
    chr_data.setPermission(SECMODE_OPEN, SECMODE_NO_ACCESS);
    chr_data.setMaxLen(C08B_F01_MAX_PKT_BYTES);
    chr_data.begin();

    chr_meta.setProperties(CHR_PROPS_READ);
    chr_meta.setPermission(SECMODE_OPEN, SECMODE_NO_ACCESS);
    chr_meta.setMaxLen(512);
    chr_meta.begin();

    chr_stat.setProperties(CHR_PROPS_READ);
    chr_stat.setPermission(SECMODE_OPEN, SECMODE_NO_ACCESS);
    chr_stat.setFixedLen(C08B_STATUS_BYTES);
    chr_stat.begin();

    chr_ctrl.setProperties(CHR_PROPS_WRITE);
    chr_ctrl.setPermission(SECMODE_NO_ACCESS, SECMODE_OPEN);
    chr_ctrl.setMaxLen(8);
    chr_ctrl.setWriteCallback(on_ctrl_write);
    chr_ctrl.begin();

    chr_imu.setProperties(CHR_PROPS_NOTIFY);
    chr_imu.setPermission(SECMODE_OPEN, SECMODE_NO_ACCESS);
    chr_imu.setMaxLen(C08B_IMU_PKT_BYTES);
    chr_imu.begin();

    refresh_gatt_meta_and_status();

    Bluefruit.Advertising.addFlags(BLE_GAP_ADV_FLAGS_LE_ONLY_GENERAL_DISC_MODE);
    Bluefruit.Advertising.addService(c08b_svc);
    Bluefruit.ScanResponse.addName();
    Bluefruit.Advertising.restartOnDisconnect(true);
    Bluefruit.Advertising.setInterval(64, 64); /* 40 ms */
    Bluefruit.Advertising.setFastTimeout(0);
    Bluefruit.Advertising.start(0);

    spis_init();
}

void loop()
{
    uint32_t now = millis();
    xiao_imu_poll();

    /* VBUS / OE_N 互锁实时监测（与 nrf/main.c 完全一致） */
    if (gpio_get_raw(VBUS_SENSE_PIN) && g_req_mode != C08B_MODE_IDLE &&
        g_req_mode != C08B_MODE_STOP && g_req_mode != C08B_MODE_SYN1 &&
        g_req_mode != C08B_MODE_CLRO) {
        g_req_mode = C08B_MODE_STOP;
        g_cmd_epoch = c08b_next_cmd_epoch(g_cmd_epoch);
        g_await_epoch_lo = (uint16_t)g_cmd_epoch;
        g_bridge.active = false;
        g_bridge.pend_mode = AFE_NONE;
        g_bridge.pend_count = 0;
        g_bridge.pend_flags = 0;
        g_bridge.fault = C08B_FAULT_INTERLOCK;
        spis_rearm_now();
    } else if (calc_nrf_flags() != g_spis_tx.nrf_flags) {
        spis_rearm_now();
    }

    /* 硬件 SPIS1 EasyDMA 收帧（插上 6 根杜邦线后自动生效！） */
    if (NRF_SPIS1->EVENTS_END) {
        NRF_SPIS1->EVENTS_END = 0;
        gpio_set_raw(LINK_RDY_PIN, 0);
        uint32_t tw = millis();
        while (!NRF_SPIS1->EVENTS_ACQUIRED && (millis() - tw) < 5u) {}
        if (NRF_SPIS1->RXD.AMOUNT == sizeof(c08b_link_tx_t)) {
            c08b_link_tx_t snap;
            memcpy(&snap, (const void *)&g_spis_rx, sizeof(snap));
            if (c08b_link_tx_ok(&snap)) {
                g_spis_hw_frames++;
                ingest_l432_frame(&snap);
            } else {
                g_crc_bad_frames++;
            }
        }
        spis_arm();
    }

    poll_usb_serial();
    usb_drain();

    static uint32_t last_stat_ms = 0;
    if (now - last_stat_ms >= 200u) {
        last_stat_ms = now;
        refresh_gatt_meta_and_status();
    }

    /* 红灯指示（低有效）：采集中 4 Hz 快闪；有故障常亮；待机每秒闪 1 下 */
    int led_on = g_bridge.fault ? 1 : g_bridge.active ? ((now / 125u) & 1) : ((now % 1000u) < 80u);
    gpio_set_raw(LED_PIN, !led_on);
}

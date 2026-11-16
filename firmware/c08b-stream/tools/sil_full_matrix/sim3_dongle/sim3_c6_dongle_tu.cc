#include <deque>
#include <vector>
#include <cstring>
extern "C" {
#include "inc_c6/c6_mock_all.h"
}

namespace {
uint64_t g_c6_now_us = 1000;
size_t   g_c6_usb_tx_cap = 256;
std::deque<uint8_t> g_c6_usb_tx;
std::deque<uint8_t> g_c6_usb_rx;

bool     g_c6_connected = false;
bool     g_c6_peer_has_imu = true;
uint16_t g_c6_att_mtu = 23;
uint16_t g_c6_conn_itvl = 6;
uint32_t g_c6_mtu_init_cnt = 0;
uint16_t g_c6_read_frag_size = 244; /* 可设为 22 模拟 MTU=23 分片长读 */
ble_gap_event_fn g_c6_gap_cb = nullptr;

using peer_write_cb_t = int (*)(const uint8_t *data, uint16_t len);
using peer_read_cb_t  = int (*)(uint8_t suffix, uint8_t *out, uint16_t max_len);
using peer_sub_cb_t   = int (*)(uint8_t suffix, bool en);
using peer_mtu_cb_t   = void (*)(uint16_t mtu);

peer_write_cb_t g_c6_wcb = nullptr;
peer_read_cb_t  g_c6_rcb = nullptr;
peer_sub_cb_t   g_c6_scb = nullptr;
peer_mtu_cb_t   g_c6_mcb = nullptr;
} // namespace

extern "C" {
struct ble_hs_cfg_s ble_hs_cfg;

void taskENTER_CRITICAL(portMUX_TYPE *) {}
void taskEXIT_CRITICAL(portMUX_TYPE *) {}
void vTaskDelay(uint32_t) { g_c6_now_us += 1000; }
int  xTaskCreate(TaskFunction_t, const char *, uint32_t, void *, int, void *) { return 1; }
int64_t esp_timer_get_time(void) { return (int64_t)g_c6_now_us; }
int  nvs_flash_init(void) { return 0; }
int  usb_serial_jtag_driver_install(const usb_serial_jtag_driver_config_t *) { return 0; }

int usb_serial_jtag_write_bytes(const void *src, size_t size, uint32_t) {
    if (g_c6_usb_tx.size() >= g_c6_usb_tx_cap) return 0;
    size_t avail = g_c6_usb_tx_cap - g_c6_usb_tx.size();
    size_t n = (size < avail) ? size : avail;
    const uint8_t *p = (const uint8_t *)src;
    for (size_t i = 0; i < n; i++) g_c6_usb_tx.push_back(p[i]);
    return (int)n;
}
int usb_serial_jtag_read_bytes(void *buf, uint32_t length, uint32_t) {
    if (length == 0 || g_c6_usb_rx.empty()) return 0;
    *(uint8_t *)buf = g_c6_usb_rx.front();
    g_c6_usb_rx.pop_front();
    return 1;
}

int ble_uuid_cmp(const ble_uuid_t *a, const ble_uuid_t *b) {
    if (a->type != b->type) return 1;
    if (a->type == 128) {
        return std::memcmp(((const ble_uuid128_t *)a)->value, ((const ble_uuid128_t *)b)->value, 16);
    }
    return (((const ble_uuid16_t *)a)->value == ((const ble_uuid16_t *)b)->value) ? 0 : 1;
}
uint16_t ble_uuid_u16(const ble_uuid_t *u) {
    return (u && u->type == 16) ? ((const ble_uuid16_t *)u)->value : 0;
}
int os_mbuf_copydata(const struct os_mbuf *om, int off, int len, void *dst) {
    if (!om || off + len > om->len) return -1;
    std::memcpy(dst, om->data + off, (size_t)len);
    return 0;
}

int ble_gattc_exchange_mtu(uint16_t c, ble_gatt_mtu_fn cb, void *arg) {
    g_c6_mtu_init_cnt++;
    g_c6_att_mtu = 247;
    if (g_c6_mcb) g_c6_mcb(247);
    struct ble_gatt_error ok = {0};
    if (cb) cb(c, &ok, 247, arg);
    return 0;
}

int ble_gattc_disc_svc_by_uuid(uint16_t c, const ble_uuid_t *, ble_gatt_disc_svc_fn cb, void *arg) {
    struct ble_gatt_error ok = {0}, done = {BLE_HS_EDONE};
    struct ble_gatt_svc svc = {10, 30};
    cb(c, &ok, &svc, arg);
    cb(c, &done, nullptr, arg);
    return 0;
}

int ble_gattc_disc_all_chrs(uint16_t c, uint16_t, uint16_t, ble_gatt_chr_fn cb, void *arg) {
    struct ble_gatt_error ok = {0}, done = {BLE_HS_EDONE};
    auto emit = [&](uint16_t def_h, uint16_t val_h, uint8_t nn) {
        struct ble_gatt_chr ch{};
        ch.def_handle = def_h;
        ch.val_handle = val_h;
        ch.uuid = BLE_UUID128_INIT(nn, 0x00, 0x00, 0x9d, 0xbb, 0x12, 0x11, 0x9d, 0x03, 0x4f, 0x48, 0x39, 0x01, 0xc1, 0x24, 0x7b);
        cb(c, &ok, &ch, arg);
    };
    emit(11, 12, 0x02); /* DATA, CCCD at 13 */
    emit(14, 15, 0x03); /* META */
    emit(16, 17, 0x04); /* STATUS */
    emit(18, 19, 0x05); /* CONTROL */
    if (g_c6_peer_has_imu) {
        emit(20, 21, 0x06); /* IMU, CCCD at 22 */
    }
    cb(c, &done, nullptr, arg);
    return 0;
}

int ble_gattc_disc_all_dscs(uint16_t c, uint16_t start_h, uint16_t end_h, ble_gatt_dsc_fn cb, void *arg) {
    struct ble_gatt_error ok = {0}, done = {BLE_HS_EDONE};
    if (start_h <= 13 && 13 <= end_h) {
        struct ble_gatt_dsc d = {13, {{16}, BLE_GATT_DSC_CLT_CFG_UUID16}};
        cb(c, &ok, start_h, &d, arg);
    }
    if (g_c6_peer_has_imu && start_h <= 22 && 22 <= end_h) {
        struct ble_gatt_dsc d = {22, {{16}, BLE_GATT_DSC_CLT_CFG_UUID16}};
        cb(c, &ok, start_h, &d, arg);
    }
    cb(c, &done, start_h, nullptr, arg);
    return 0;
}

int ble_gattc_write_flat(uint16_t c, uint16_t attr_h, const void *data, uint16_t len, ble_gatt_attr_fn cb, void *arg) {
    int rc = 0;
    if (attr_h == 13) {
        if (g_c6_scb) g_c6_scb(2, true);
    } else if (attr_h == 22) {
        if (g_c6_scb) g_c6_scb(6, true);
    } else if (attr_h == 19) {
        if (g_c6_wcb) rc = g_c6_wcb((const uint8_t *)data, len);
    }
    struct ble_gatt_error err = {(uint16_t)(rc == 0 ? 0 : 1)};
    if (cb) cb(c, &err, nullptr, arg);
    return 0;
}

int ble_gattc_read_long(uint16_t c, uint16_t attr_h, uint16_t, ble_gatt_attr_fn cb, void *arg) {
    uint8_t suffix = (attr_h == 15) ? 3 : (attr_h == 17) ? 4 : 0;
    uint8_t full[600];
    int n = g_c6_rcb ? g_c6_rcb(suffix, full, sizeof(full)) : 0;
    if (n <= 0) {
        struct ble_gatt_error err = {1};
        if (cb) cb(c, &err, nullptr, arg);
        return 0;
    }
    struct ble_gatt_error ok = {0}, done = {BLE_HS_EDONE};
    int off = 0;
    while (off < n) {
        int chunk = (n - off > g_c6_read_frag_size) ? g_c6_read_frag_size : (n - off);
        struct os_mbuf om = {full + off, (uint16_t)chunk};
        struct ble_gatt_attr a = {attr_h, (uint16_t)off, &om};
        cb(c, &ok, &a, arg);
        off += chunk;
    }
    cb(c, &done, nullptr, arg);
    return 0;
}

int ble_hs_adv_parse_fields(struct ble_hs_adv_fields *f, const uint8_t *data, uint8_t len) {
    f->name = data;
    f->name_len = len;
    return 0;
}
int ble_gap_disc(uint8_t, int32_t, const struct ble_gap_disc_params *, ble_gap_event_fn cb, void *) {
    g_c6_gap_cb = cb;
    return 0;
}
int ble_gap_disc_cancel(void) { return 0; }
int ble_gap_connect(uint8_t, const ble_addr_t *, int32_t, const struct ble_gap_conn_params *p, ble_gap_event_fn cb, void *arg) {
    g_c6_gap_cb = cb;
    g_c6_connected = true;
    g_c6_conn_itvl = p ? p->itvl_min : 6;
    struct ble_gap_event ev{};
    ev.type = BLE_GAP_EVENT_CONNECT;
    ev.connect.status = 0;
    ev.connect.conn_handle = 1u;
    cb(&ev, arg);
    struct ble_gap_event dev{};
    dev.type = BLE_GAP_EVENT_DATA_LEN_CHG;
    dev.data_len_chg.max_rx_octets = 251;
    cb(&dev, arg);
    return 0;
}
int ble_gap_terminate(uint16_t, uint8_t reason) {
    if (g_c6_connected) {
        g_c6_connected = false;
        if (g_c6_gap_cb) {
            struct ble_gap_event ev{};
            ev.type = BLE_GAP_EVENT_DISCONNECT;
            ev.disconnect.reason = reason;
            g_c6_gap_cb(&ev, nullptr);
        }
    }
    return 0;
}
int ble_gap_set_prefered_le_phy(uint16_t, uint8_t, uint8_t, uint16_t) { return 0; }
int ble_gap_set_data_len(uint16_t, uint16_t, uint16_t) { return 0; }
int ble_gap_conn_find(uint16_t, struct ble_gap_conn_desc *out) {
    if (!g_c6_connected) return -1;
    out->conn_itvl = g_c6_conn_itvl;
    return 0;
}
int ble_gap_read_le_phy(uint16_t, uint8_t *tx, uint8_t *rx) {
    *tx = 2; *rx = 2; return 0;
}
int ble_gap_update_params(uint16_t, const struct ble_gap_upd_params *p) {
    g_c6_conn_itvl = p->itvl_min;
    return 0;
}
uint16_t ble_att_mtu(uint16_t) { return g_c6_att_mtu; }
int ble_att_set_preferred_mtu(uint16_t) { return 0; }
int ble_hs_util_ensure_addr(int) { return 0; }
int ble_hs_id_infer_auto(int, uint8_t *out) { *out = 0; return 0; }
void nimble_port_init(void) {}
void nimble_port_run(void) {}
void nimble_port_freertos_init(void (*)(void *)) {
    if (ble_hs_cfg.sync_cb) ble_hs_cfg.sync_cb();
}
void nimble_port_freertos_deinit(void) {}

/* 直接编译未经修改的真实固件源码 c6-central/main/main.c */
#include FW_C6_DONGLE_C

static int64_t g_c6_last_link_us = 0;
static uint8_t g_c6_cmd_buf[608];
static uint16_t g_c6_cmd_len = 0;

void c6_init(uint32_t usb_tx_cap, bool peer_has_imu, uint16_t read_frag_size) {
    g_c6_now_us = 1000;
    g_c6_usb_tx_cap = usb_tx_cap ? usb_tx_cap : 256u;
    g_c6_usb_tx.clear();
    g_c6_usb_rx.clear();
    g_c6_connected = false;
    g_c6_peer_has_imu = peer_has_imu;
    g_c6_att_mtu = 23;
    g_c6_conn_itvl = 6;
    g_c6_mtu_init_cnt = 0;
    g_c6_read_frag_size = read_frag_size ? read_frag_size : 244u;
    g_c6_last_link_us = 0;
    g_c6_cmd_len = 0;

    conn = BLE_HS_CONN_HANDLE_NONE;
    ready = false;
    want_ci = 6;
    dl_tx = 27;
    connects = 0; notifies = 0; ring_drops = 0; ring_peak = 0;
    head = 0; tail = 0;
    rd_len = 0; rd_busy = false;

    app_main();
}

void c6_set_peer_callbacks(peer_write_cb_t wcb, peer_read_cb_t rcb, peer_sub_cb_t scb, peer_mtu_cb_t mcb) {
    g_c6_wcb = wcb; g_c6_rcb = rcb; g_c6_scb = scb; g_c6_mcb = mcb;
}

void c6_feed_adv(const char *name_str) {
    if (!g_c6_gap_cb || !name_str) return;
    struct ble_gap_event ev{};
    ev.type = BLE_GAP_EVENT_DISC;
    ev.disc.data = (const uint8_t *)name_str;
    ev.disc.length_data = (uint8_t)std::strlen(name_str);
    g_c6_gap_cb(&ev, nullptr);
}

void c6_feed_notify(uint8_t suffix, const uint8_t *data, uint16_t len) {
    if (!g_c6_gap_cb || !g_c6_connected) return;
    struct os_mbuf om = {data, len};
    struct ble_gap_event ev{};
    ev.type = BLE_GAP_EVENT_NOTIFY_RX;
    ev.notify_rx.attr_handle = (suffix == 6) ? 21u : 12u;
    ev.notify_rx.om = &om;
    g_c6_gap_cb(&ev, nullptr);
}

void c6_peer_disconnect(uint8_t reason) { ble_gap_terminate(1u, reason); }

void c6_usb_host_send(const uint8_t *data, int len) {
    for (int i = 0; i < len; i++) g_c6_usb_rx.push_back(data[i]);
}

int c6_usb_host_recv(uint8_t *out, int max_len) {
    int n = 0;
    while (n < max_len && !g_c6_usb_tx.empty()) {
        out[n++] = g_c6_usb_tx.front();
        g_c6_usb_tx.pop_front();
    }
    return n;
}

void c6_step_io(uint32_t advance_us) {
    g_c6_now_us += advance_us;
    /* 1. reader_task 非阻塞处理所有已收到的 USB RX 命令字节 */
    uint8_t c;
    while (usb_serial_jtag_read_bytes(&c, 1, 0) == 1) {
        if (g_c6_cmd_len == 0 && c != 0xA5) continue;
        g_c6_cmd_buf[g_c6_cmd_len++] = c;
        if (g_c6_cmd_len >= 4) {
            uint16_t n = g_c6_cmd_buf[2] | (g_c6_cmd_buf[3] << 8);
            if (n > sizeof(g_c6_cmd_buf) - 4) { g_c6_cmd_len = 0; continue; }
            if (g_c6_cmd_len == 4u + n) { handle(g_c6_cmd_buf[1], g_c6_cmd_buf + 4, n); g_c6_cmd_len = 0; }
        }
    }
    /* 2. writer_task 1Hz 链路帧 + 环形缓冲排空 */
    if ((int64_t)g_c6_now_us - g_c6_last_link_us > 1000000) {
        g_c6_last_link_us = (int64_t)g_c6_now_us;
        send_link();
    }
    while (tail != head) {
        uint32_t t = tail, h = head;
        uint32_t off = t % RING, n = h - t;
        if (n > RING - off) n = RING - off;
        int w = usb_serial_jtag_write_bytes(ring + off, n, 20);
        if (w <= 0) break;
        tail = t + (uint32_t)w;
    }
}

void c6_get_stats(uint32_t *out_connects, uint32_t *out_drops, uint32_t *out_notifies,
                  uint32_t *out_mtu_inits, bool *out_ready) {
    if (out_connects)  *out_connects  = connects;
    if (out_drops)     *out_drops     = ring_drops;
    if (out_notifies)  *out_notifies  = notifies;
    if (out_mtu_inits) *out_mtu_inits = g_c6_mtu_init_cnt;
    if (out_ready)     *out_ready     = ready;
}
}

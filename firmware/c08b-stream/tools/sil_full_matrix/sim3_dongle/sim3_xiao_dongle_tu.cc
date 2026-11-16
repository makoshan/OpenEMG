#include "inc_xiao/Arduino.h"
#include "inc_xiao/bluefruit.h"
#include <deque>
#include <vector>

namespace {
uint64_t g_now_us = 0;
int      g_suspend_depth = 0;
int      g_max_suspend_depth = 0;
bool     g_unbalanced_suspend = false;
uint32_t g_mtu_req_count = 0;

/* 真实模拟 Adafruit TinyUSB 256B 发送 FIFO（默认 CFG_TUD_CDC_TX_BUFSIZE=256）：
 * Serial.write 非阻塞，当 FIFO 剩余空间 < len 时仅写入可容纳的部分字节并返回实际写入数！ */
size_t              g_usb_tx_cap = 256;
bool                g_usb_connected = true;
uint32_t            g_usb_sof_auto_drain = 0;   /* 模拟主机 USB SOF(每 1000 µs) 自动取走字节数 */
uint64_t            g_last_sof_us = 0;
uint64_t            g_stall_at_us = 0;          /* 非 0 时到达该时刻模拟电脑停止读取串口 */
uint64_t            g_disconnect_at_us = 0;     /* 非 0 时到达该时刻模拟电脑拔掉/关闭 USB CDC (!Serial) */
std::deque<uint8_t> g_usb_tx_fifo;
std::deque<uint8_t> g_usb_rx_fifo;
std::vector<uint8_t> g_usb_auto_captured;

BLEConnection               g_conn_obj;
std::vector<BLEClientCharacteristic *> g_all_chrs;
bool                        g_peer_has_imu = true;

using peer_write_cb_t = int (*)(const uint8_t *data, uint16_t len);
using peer_read_cb_t  = int (*)(uint8_t suffix, uint8_t *out, uint16_t max_len);
using peer_sub_cb_t   = int (*)(uint8_t suffix, bool en);
using peer_mtu_cb_t   = void (*)(uint16_t mtu);

peer_write_cb_t g_peer_write_cb = nullptr;
peer_read_cb_t  g_peer_read_cb  = nullptr;
peer_sub_cb_t   g_peer_sub_cb   = nullptr;
peer_mtu_cb_t   g_peer_mtu_cb   = nullptr;
} // namespace

SimNrfTimer g_xd_timer2;
SimUsbCdcSerial Serial;
SimBluefruit Bluefruit;

SimNrfTimer::CaptureProxy &SimNrfTimer::CaptureProxy::operator=(uint32_t v) {
    if (v) g_xd_timer2.CC[idx] = (uint32_t)g_now_us;
    return *this;
}

void vTaskSuspendAll(void) {
    g_suspend_depth++;
    if (g_suspend_depth > g_max_suspend_depth) g_max_suspend_depth = g_suspend_depth;
}

void xTaskResumeAll(void) {
    if (g_suspend_depth <= 0) g_unbalanced_suspend = true;
    else g_suspend_depth--;
}

static void sim_advance_usb_sof(void) {
    if (g_stall_at_us != 0 && g_now_us >= g_stall_at_us) {
        g_usb_sof_auto_drain = 0;
    }
    if (g_disconnect_at_us != 0 && g_now_us >= g_disconnect_at_us) {
        g_usb_connected = false;
        g_usb_sof_auto_drain = 0;
    }
    while (g_now_us - g_last_sof_us >= 1000ull) {
        g_last_sof_us += 1000ull;
        if (g_usb_connected && g_usb_sof_auto_drain > 0) {
            uint32_t n = 0;
            while (n < g_usb_sof_auto_drain && !g_usb_tx_fifo.empty()) {
                g_usb_auto_captured.push_back(g_usb_tx_fifo.front());
                g_usb_tx_fifo.pop_front();
                n++;
            }
        }
    }
}

uint32_t millis(void) { return (uint32_t)(g_now_us / 1000ull); }
void yield(void) {
    g_now_us += 250ull;
    sim_advance_usb_sof();
}

void SimUsbCdcSerial::begin(uint32_t) {}
SimUsbCdcSerial::operator bool() const { return g_usb_connected; }
size_t SimUsbCdcSerial::write(const uint8_t *buf, size_t len) {
    if (!g_usb_connected || g_usb_tx_fifo.size() >= g_usb_tx_cap) return 0;
    size_t avail = g_usb_tx_cap - g_usb_tx_fifo.size();
    size_t n = (len < avail) ? len : avail;
    for (size_t i = 0; i < n; i++) g_usb_tx_fifo.push_back(buf[i]);
    return n;
}
int SimUsbCdcSerial::available(void) { return (int)g_usb_rx_fifo.size(); }
int SimUsbCdcSerial::read(void) {
    if (g_usb_rx_fifo.empty()) return -1;
    uint8_t c = g_usb_rx_fifo.front();
    g_usb_rx_fifo.pop_front();
    return (int)c;
}

BLEClientCharacteristic::BLEClientCharacteristic(const char *u) : uuid_str(u) {
    size_t n = std::strlen(u);
    suffix = (n >= 2) ? (uint8_t)std::strtoul(u + n - 2, nullptr, 16) : 0;
    g_all_chrs.push_back(this);
}
bool BLEClientService::discover(uint16_t) { return present; }
bool BLEClientCharacteristic::discover(void) {
    if (suffix == 0x06) return g_peer_has_imu;
    return present;
}
bool BLEClientCharacteristic::enableNotify(void) {
    if (suffix == 0x06 && !g_peer_has_imu) return false;
    notify_enabled = true;
    if (g_peer_sub_cb) g_peer_sub_cb(suffix, true);
    return true;
}
uint16_t BLEClientCharacteristic::write_resp(const void *data, uint16_t len) {
    if (g_peer_write_cb) {
        return g_peer_write_cb((const uint8_t *)data, len) == 0 ? len : 0;
    }
    return len;
}
uint16_t BLEClientCharacteristic::read(void *buf, uint16_t max_len) {
    if (g_peer_read_cb) {
        int got = g_peer_read_cb(suffix, (uint8_t *)buf, max_len);
        return (got > 0) ? (uint16_t)got : 0;
    }
    return 0;
}

void BLEConnection::requestDataLengthUpdate(void) {
    dl = 251;
    if (Bluefruit.evt_cb) {
        ble_evt_t ev{};
        ev.header.evt_id = BLE_GAP_EVT_DATA_LENGTH_UPDATE;
        ev.evt.gap_evt.params.data_length_update.effective_params = {251, 2120, 251, 2120};
        Bluefruit.evt_cb(&ev);
    }
}
void BLEConnection::requestMtuExchange(uint16_t m) {
    g_mtu_req_count++;
    mtu = m;
    if (g_peer_mtu_cb) g_peer_mtu_cb(m);
}

void SimBluefruit::disconnect(uint16_t h) {
    if (g_conn_obj.is_conn) {
        g_conn_obj.is_conn = false;
        if (disc_cb) disc_cb(h, 0x16u);
    }
}
BLEConnection *SimBluefruit::Connection(uint16_t h) {
    return (h == 1u && g_conn_obj.is_conn) ? &g_conn_obj : nullptr;
}
void SimBluefruit::CentralApi::setConnectCallback(conn_cb_t cb) { Bluefruit.conn_cb = cb; }
void SimBluefruit::CentralApi::setDisconnectCallback(disc_cb_t cb) { Bluefruit.disc_cb = cb; }
bool SimBluefruit::CentralApi::connect(ble_gap_evt_adv_report_t *) {
    g_conn_obj = BLEConnection{};
    g_conn_obj.is_conn = true;
    g_conn_obj.ci = min_ci;
    g_conn_obj.mtu = 23;
    g_conn_obj.dl = 27;
    g_conn_obj.phy = 1;
    if (Bluefruit.conn_cb) Bluefruit.conn_cb(1u);
    return true;
}
void SimBluefruit::ScannerApi::setRxCallback(scan_cb_t cb) { Bluefruit.rx_cb = cb; }
void SimBluefruit::ScannerApi::start(uint16_t) { Bluefruit.scanning = true; }

/* 直接编译未经修改的真实固件源码 xiao-central/src/main.cpp */
#include FW_XIAO_DONGLE_CPP

extern "C" {
void xd_init(uint32_t usb_tx_fifo_cap, bool peer_has_imu) {
    g_now_us = 1000ull;
    g_suspend_depth = 0;
    g_max_suspend_depth = 0;
    g_unbalanced_suspend = false;
    g_mtu_req_count = 0;
    g_usb_tx_cap = usb_tx_fifo_cap ? usb_tx_fifo_cap : 256u;
    g_usb_connected = true;
    g_usb_sof_auto_drain = 0;
    g_last_sof_us = g_now_us;
    g_stall_at_us = 0;
    g_disconnect_at_us = 0;
    g_usb_tx_fifo.clear();
    g_usb_rx_fifo.clear();
    g_usb_auto_captured.clear();
    g_conn_obj = BLEConnection{};
    g_peer_has_imu = peer_has_imu;
    for (int i = 0; i < 6; i++) g_xd_timer2.TASKS_CAPTURE[i].idx = i;

    conn = BLE_CONN_HANDLE_INVALID;
    ready = false;
    want_ci = 6;
    last_param_req = 0;
    std::memset(tries, 0, sizeof(tries));
    head = 0; tail = 0; pkt_end = 0;
    ring_drops = 0; notifies = 0; ring_peak = 0;
    svc_reports = 0; name_reports = 0; connects = 0; discover_fail = 0;
    cmd_len = 0;
    dle_seq = 0;

    setup();
}

void xd_set_peer_callbacks(peer_write_cb_t wcb, peer_read_cb_t rcb, peer_sub_cb_t scb, peer_mtu_cb_t mcb) {
    g_peer_write_cb = wcb;
    g_peer_read_cb  = rcb;
    g_peer_sub_cb   = scb;
    g_peer_mtu_cb   = mcb;
}

void xd_feed_adv(const char *name_str, bool has_svc_uuid) {
    if (!Bluefruit.rx_cb) return;
    ble_gap_evt_adv_report_t rep{};
    rep.has_service_uuid = has_svc_uuid;
    if (name_str) std::strncpy(rep.adv_name, name_str, sizeof(rep.adv_name) - 1);
    Bluefruit.rx_cb(&rep);
}

void xd_feed_notify(uint8_t suffix, const uint8_t *data, uint16_t len) {
    /* 模拟 SoftDevice BLE 事件任务异步抢占送入 HVX 通知（可能恰好发生在 loop() drain() 写了一半帧的时刻！） */
    BLEClientCharacteristic *chr = (suffix == 6) ? &imu_chr : &data_chr;
    if (chr->notify_cb && chr->notify_enabled) {
        chr->notify_cb(chr, const_cast<uint8_t *>(data), len);
    }
}

void xd_peer_set_mtu(uint16_t mtu) {
    g_conn_obj.mtu = mtu;
}

void xd_peer_disconnect(uint8_t reason) {
    if (g_conn_obj.is_conn) {
        g_conn_obj.is_conn = false;
        if (Bluefruit.disc_cb) Bluefruit.disc_cb(1u, reason);
    }
}

void xd_usb_host_send(const uint8_t *data, int len) {
    for (int i = 0; i < len; i++) g_usb_rx_fifo.push_back(data[i]);
}

int xd_usb_host_recv(uint8_t *out, int max_len) {
    int n = 0;
    while (n < max_len && !g_usb_tx_fifo.empty()) {
        out[n++] = g_usb_tx_fifo.front();
        g_usb_tx_fifo.pop_front();
    }
    return n;
}

int xd_usb_tx_fifo_used(void) { return (int)g_usb_tx_fifo.size(); }

void xd_step_loop(uint32_t advance_us) {
    g_now_us += advance_us;
    sim_advance_usb_sof();
    loop();
}

uint64_t xd_now_us(void) { return g_now_us; }

void xd_seed_ring_cursor(uint32_t base) {
    head = base;
    tail = base;
    pkt_end = base;
}

void xd_config_usb_host_sim(bool connected, uint32_t sof_auto_drain_bytes,
                            uint64_t stall_after_delta_us, uint64_t disconnect_after_delta_us) {
    g_usb_connected = connected;
    g_usb_sof_auto_drain = sof_auto_drain_bytes;
    g_last_sof_us = g_now_us;
    g_stall_at_us = stall_after_delta_us ? (g_now_us + stall_after_delta_us) : 0;
    g_disconnect_at_us = disconnect_after_delta_us ? (g_now_us + disconnect_after_delta_us) : 0;
}

int xd_pop_auto_captured(uint8_t *out, int max_len) {
    int n = (int)g_usb_auto_captured.size();
    if (n > max_len) n = max_len;
    if (n > 0 && out) {
        std::memcpy(out, g_usb_auto_captured.data(), (size_t)n);
        g_usb_auto_captured.erase(g_usb_auto_captured.begin(), g_usb_auto_captured.begin() + n);
    }
    return n;
}

void xd_get_stats(uint32_t *out_connects, uint32_t *out_drops, uint32_t *out_notifies,
                  uint32_t *out_peak, uint32_t *out_mtu_reqs, bool *out_ready, bool *out_crit_bad) {
    if (out_connects) *out_connects = connects;
    if (out_drops)    *out_drops    = ring_drops;
    if (out_notifies) *out_notifies = notifies;
    if (out_peak)     *out_peak     = ring_peak;
    if (out_mtu_reqs) *out_mtu_reqs = g_mtu_req_count;
    if (out_ready)    *out_ready    = ready;
    if (out_crit_bad) *out_crit_bad = g_unbalanced_suspend || (g_suspend_depth != 0);
}
}

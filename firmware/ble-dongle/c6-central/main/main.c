// 蓝牙接收器（XIAO ESP32-C6 版）：NimBLE 当中心连 R01（MAKO-V12-ADS-2K），定 7.5 ms / 2M / DLE / MTU 247，
// 通知经 USB 串口送 Mac。串口协议与 xiao-central（nRF52840 版）逐字节相同，host/v12_dongle.py 不改即可用。
// 只用开发板当接收器；R01 本体只用电池，不接 USB（见 firmware-f05-ble-dout/README）。
//
// 设备→电脑：A5 | kind u8 | len u16 LE | t_us u32 LE | payload
//   2 = 数据特征通知，0x10 = 文本日志，0x11 = 链路信息（26 B），0x80|op = 命令应答（首字节 0 成功）
// 电脑→设备：A5 | op u8 | len u16 LE | payload
//   'W' 写控制特征（带应答），'R' 读特征（1 字节：3 元数据 / 4 状态，长读），'I' 设连接间隔（u16，1.25 ms），
//   'Q' 立刻回链路信息，'D' 断开当前连接（之后自动重扫重连）
#include <string.h>
#include <stdio.h>
#include <stdarg.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_timer.h"
#include "nvs_flash.h"
#include "driver/usb_serial_jtag.h"
#include "nimble/nimble_port.h"
#include "nimble/nimble_port_freertos.h"
#include "host/ble_hs.h"
#include "host/util/util.h"

#define TARGET_NAME "MAKO-V12-ADS-2K"
// 7b24c101-3948-4f03-9d11-12bb9d0000NN（与 F05 同一服务；NN = 01 服务、02 数据、03 元数据、04 状态、05 控制）
#define MAKO_UUID(nn) BLE_UUID128_INIT(nn, 0x00, 0x00, 0x9d, 0xbb, 0x12, 0x11, 0x9d, 0x03, 0x4f, 0x48, 0x39, 0x01, 0xc1, 0x24, 0x7b)
static const ble_uuid128_t SVC = MAKO_UUID(0x01), DATA = MAKO_UUID(0x02), META = MAKO_UUID(0x03),
                           STATUS = MAKO_UUID(0x04), CONTROL = MAKO_UUID(0x05);

static uint8_t own_addr_type;
static volatile uint16_t conn = BLE_HS_CONN_HANDLE_NONE;
static volatile bool ready = false;
static uint16_t svc_start, svc_end, h_data, h_meta, h_status, h_control, h_cccd;
static volatile uint16_t want_ci = 6, dl_tx = 27;
static volatile uint32_t connects = 0, notifies = 0, ring_drops = 0, ring_peak = 0;

// 环形缓冲：生产者是 NimBLE host 任务（通知、GATT 应答）和 USB 读任务（即时应答），用自旋锁串行；唯一消费者是 USB 写任务
#define RING 32768u
static uint8_t ring[RING];
static volatile uint32_t head = 0, tail = 0;
static portMUX_TYPE ring_lock = portMUX_INITIALIZER_UNLOCKED;

static uint32_t now_us(void) { return (uint32_t)esp_timer_get_time(); }

static void put_frame(uint8_t kind, uint32_t t, const uint8_t *p, uint16_t len) {
    taskENTER_CRITICAL(&ring_lock);
    uint32_t need = 8u + len, h = head, used = h - tail;
    if (RING - used < need) { ring_drops++; taskEXIT_CRITICAL(&ring_lock); return; }  // 满了丢整帧，电脑据序号缺口和 ring_drops 都能看见
    uint8_t hdr[8] = {0xA5, kind, (uint8_t)len, (uint8_t)(len >> 8), (uint8_t)t, (uint8_t)(t >> 8), (uint8_t)(t >> 16), (uint8_t)(t >> 24)};
    for (uint32_t i = 0; i < 8; i++) ring[(h + i) % RING] = hdr[i];
    for (uint32_t i = 0; i < len; i++) ring[(h + 8 + i) % RING] = p[i];
    __sync_synchronize();
    head = h + need;
    if (head - tail > ring_peak) ring_peak = head - tail;
    taskEXIT_CRITICAL(&ring_lock);
}

static void reply(uint8_t op, uint8_t status, const uint8_t *data, uint16_t n) {
    uint8_t r[600];  // 局部：host 任务和 reader 任务都会调 reply，共用静态缓冲会互相覆盖
    if (n > sizeof r - 1) n = sizeof r - 1;
    r[0] = status;
    if (n) memcpy(r + 1, data, n);
    put_frame(0x80 | op, now_us(), r, 1 + n);
}

static void logf_(const char *fmt, ...) {
    char s[160];
    va_list ap; va_start(ap, fmt); int n = vsnprintf(s, sizeof s, fmt, ap); va_end(ap);
    put_frame(0x10, now_us(), (const uint8_t *)s, n < 0 ? 0 : (n < (int)sizeof s ? n : sizeof s - 1));
}

static void scan(void);
static int gap_event(struct ble_gap_event *e, void *arg);

// ---- 连上后依次：找服务 → 找特征 → 找数据特征的 CCCD → 写 0x0001 订阅 → ready（MTU 由 R01 开采时发起）
static int on_subscribed(uint16_t c, const struct ble_gatt_error *err, struct ble_gatt_attr *a, void *arg) {
    if (err->status == 0) { ready = true; logf_("connected %s", TARGET_NAME); }
    else { logf_("subscribe fail %d", err->status); ble_gap_terminate(c, BLE_ERR_REM_USER_CONN_TERM); }
    return 0;
}

static int on_dsc(uint16_t c, const struct ble_gatt_error *err, uint16_t chr_val_handle, const struct ble_gatt_dsc *d, void *arg) {
    if (err->status == 0) {
        if (ble_uuid_u16(&d->uuid.u) == BLE_GATT_DSC_CLT_CFG_UUID16 && !h_cccd) h_cccd = d->handle;
        return 0;
    }
    if (err->status == BLE_HS_EDONE && h_cccd) {
        static const uint8_t on[2] = {1, 0};
        ble_gattc_write_flat(c, h_cccd, on, 2, on_subscribed, NULL);
    } else {
        logf_("no cccd %d", err->status); ble_gap_terminate(c, BLE_ERR_REM_USER_CONN_TERM);
    }
    return 0;
}

static int on_chr(uint16_t c, const struct ble_gatt_error *err, const struct ble_gatt_chr *ch, void *arg) {
    if (err->status == 0) {
        if (!ble_uuid_cmp(&ch->uuid.u, &DATA.u)) h_data = ch->val_handle;
        else if (!ble_uuid_cmp(&ch->uuid.u, &META.u)) h_meta = ch->val_handle;
        else if (!ble_uuid_cmp(&ch->uuid.u, &STATUS.u)) h_status = ch->val_handle;
        else if (!ble_uuid_cmp(&ch->uuid.u, &CONTROL.u)) h_control = ch->val_handle;
        return 0;
    }
    if (err->status == BLE_HS_EDONE && h_data && h_meta && h_status && h_control) {
        h_cccd = 0;  // CCCD 在数据特征值句柄之后、下一个特征之前；范围放到服务结尾，第一个 CCCD 就是它的
        ble_gattc_disc_all_dscs(c, h_data, svc_end, on_dsc, NULL);
    } else {
        logf_("chr missing %d", err->status); ble_gap_terminate(c, BLE_ERR_REM_USER_CONN_TERM);
    }
    return 0;
}

static int on_svc(uint16_t c, const struct ble_gatt_error *err, const struct ble_gatt_svc *s, void *arg) {
    if (err->status == 0) { svc_start = s->start_handle; svc_end = s->end_handle; return 0; }
    if (err->status == BLE_HS_EDONE && svc_start) {
        h_data = h_meta = h_status = h_control = 0;
        ble_gattc_disc_all_chrs(c, svc_start, svc_end, on_chr, NULL);
    } else {
        logf_("svc missing %d", err->status); ble_gap_terminate(c, BLE_ERR_REM_USER_CONN_TERM);
    }
    return 0;
}

static int on_mtu(uint16_t c, const struct ble_gatt_error *err, uint16_t mtu, void *arg) {
    svc_start = svc_end = 0;
    ble_gattc_disc_svc_by_uuid(c, &SVC.u, on_svc, NULL);  // MTU 失败也照样继续，按 23 走
    return 0;
}

// ---- 命令：长读 / 写控制
static uint8_t rd_buf[599];  // 应答 = 状态 1 B + 599，正好是电脑端切帧上限 600
static uint16_t rd_len;
static volatile bool rd_busy;  // 上一条长读没结束时拒绝新读，防止两次读拼进同一缓冲
static int on_read(uint16_t c, const struct ble_gatt_error *err, struct ble_gatt_attr *a, void *arg) {
    if (err->status == 0 && a) {
        uint16_t n = OS_MBUF_PKTLEN(a->om);
        if (rd_len + n > sizeof rd_buf) n = sizeof rd_buf - rd_len;
        os_mbuf_copydata(a->om, 0, n, rd_buf + rd_len);
        rd_len += n;
        return 0;
    }
    rd_busy = false;
    if (err->status == BLE_HS_EDONE) reply('R', 0, rd_buf, rd_len);
    else reply('R', 1, NULL, 0);
    return 0;
}
static int on_write(uint16_t c, const struct ble_gatt_error *err, struct ble_gatt_attr *a, void *arg) {
    reply('W', err->status == 0 ? 0 : 1, NULL, 0);
    return 0;
}

static void handle(uint8_t op, const uint8_t *p, uint16_t len) {
    if (op == 'W' && ready) {
        if (ble_gattc_write_flat(conn, h_control, p, len, on_write, NULL)) reply('W', 1, NULL, 0);
    } else if (op == 'R' && ready && !rd_busy && len == 1 && (p[0] == 3 || p[0] == 4)) {
        rd_len = 0; rd_busy = true;
        if (ble_gattc_read_long(conn, p[0] == 3 ? h_meta : h_status, 0, on_read, NULL)) { rd_busy = false; reply('R', 1, NULL, 0); }
    } else if (op == 'I' && len == 2 && (p[0] | p[1] << 8) >= 6 && (p[0] | p[1] << 8) <= 3200) {  // 蓝牙规范范围 7.5 ms–4 s，越界会导致连不上
        memcpy((void *)&want_ci, p, 2);
        reply('I', 0, NULL, 0);
    } else if (op == 'Q') {
        reply('Q', 0, NULL, 0);  // 链路帧由写任务每秒发；Q 只确认收到
    } else if (op == 'D') {
        // 每次采集前断开重连：F05 只在新连接时从头开始数据流（同一连接第二次采集会被新主机会话拒收）
        if (conn != BLE_HS_CONN_HANDLE_NONE) ble_gap_terminate(conn, BLE_ERR_REM_USER_CONN_TERM);
        reply('D', 0, NULL, 0);
    } else {
        reply(op, 1, NULL, 0);
    }
}

// ---- 扫描、连接、事件
static void scan(void) {
    struct ble_gap_disc_params dp = {0};
    dp.passive = 0;  // 名字在扫描应答里，要主动扫描
    dp.itvl = 160; dp.window = 80; dp.filter_duplicates = 0;
    ble_gap_disc(own_addr_type, BLE_HS_FOREVER, &dp, gap_event, NULL);
}

static int gap_event(struct ble_gap_event *e, void *arg) {
    switch (e->type) {
    case BLE_GAP_EVENT_DISC: {
        struct ble_hs_adv_fields f;
        if (ble_hs_adv_parse_fields(&f, e->disc.data, e->disc.length_data)) return 0;
        if (f.name_len == strlen(TARGET_NAME) && !memcmp(f.name, TARGET_NAME, f.name_len)) {
            ble_gap_disc_cancel();
            struct ble_gap_conn_params cp = {0};
            cp.scan_itvl = 16; cp.scan_window = 16;
            cp.itvl_min = want_ci; cp.itvl_max = want_ci; cp.latency = 0;
            cp.supervision_timeout = 400;  // 4 s
            cp.min_ce_len = 0; cp.max_ce_len = 24;
            if (ble_gap_connect(own_addr_type, &e->disc.addr, 5000, &cp, gap_event, NULL)) scan();
        }
        return 0;
    }
    case BLE_GAP_EVENT_CONNECT:
        if (e->connect.status) { scan(); return 0; }
        conn = e->connect.conn_handle; connects++; ready = false; rd_busy = false; dl_tx = 27;
        ble_gap_set_prefered_le_phy(conn, BLE_GAP_LE_PHY_2M_MASK, BLE_GAP_LE_PHY_2M_MASK, BLE_GAP_LE_PHY_CODED_ANY);
        ble_gap_set_data_len(conn, 251, 2120);
        // 不主动协商 MTU：F05 开始采集时自己会发起一次；两边都发起时，R01 的 SoftDevice 一直认为“MTU 协商进行中”，
        // 每次发通知都返回 NRF_ERROR_INVALID_STATE（2026-10-24 实测 last_hvx_error=8）。直接进入服务发现
        on_mtu(conn, &(struct ble_gatt_error){0}, 23, NULL);
        return 0;
    case BLE_GAP_EVENT_DISCONNECT:
        logf_("disconnected reason 0x%02x", e->disconnect.reason);
        conn = BLE_HS_CONN_HANDLE_NONE; ready = false;
        scan();
        return 0;
    case BLE_GAP_EVENT_DISC_COMPLETE:
        if (conn == BLE_HS_CONN_HANDLE_NONE) scan();
        return 0;
    case BLE_GAP_EVENT_CONN_UPDATE_REQ:
    case BLE_GAP_EVENT_L2CAP_UPDATE_REQ:
        // 外设会请求更长的间隔；中心按 want_ci 回，不照收
        e->conn_update_req.self_params->itvl_min = want_ci;
        e->conn_update_req.self_params->itvl_max = want_ci;
        return 0;
    case BLE_GAP_EVENT_DATA_LEN_CHG:
        dl_tx = e->data_len_chg.max_rx_octets;  // 外设实际肯发多长
        return 0;
    case BLE_GAP_EVENT_NOTIFY_RX:
        if (e->notify_rx.attr_handle == h_data) {
            static uint8_t buf[256];
            uint16_t n = OS_MBUF_PKTLEN(e->notify_rx.om);
            if (n > sizeof buf) n = sizeof buf;
            os_mbuf_copydata(e->notify_rx.om, 0, n, buf);
            notifies++;
            put_frame(2, now_us(), buf, n);
        }
        return 0;
    default:
        return 0;
    }
}

static void on_sync(void) {
    ble_hs_util_ensure_addr(0);
    ble_hs_id_infer_auto(0, &own_addr_type);
    scan();
}

static void host_task(void *arg) { nimble_port_run(); nimble_port_freertos_deinit(); }

// ---- USB：写任务（排空环形缓冲 + 每秒链路帧）、读任务（收命令）
static void send_link(void) {
    uint8_t b[26] = {0};
    struct ble_gap_conn_desc d;
    uint16_t ci = 0, mtu = 0, dl = 0;
    uint8_t phy = 0, tx = 0, rx = 0;
    if (conn != BLE_HS_CONN_HANDLE_NONE && !ble_gap_conn_find(conn, &d)) {
        ci = d.conn_itvl; mtu = ble_att_mtu(conn); dl = dl_tx;
        if (!ble_gap_read_le_phy(conn, &tx, &rx)) phy = rx;
    }
    uint32_t rd = ring_drops, nt = notifies, pk = ring_peak, cn = connects;
    uint16_t w = want_ci;
    b[0] = ready;
    memcpy(b + 1, &ci, 2); b[3] = phy; memcpy(b + 4, &mtu, 2); memcpy(b + 6, &dl, 2); memcpy(b + 8, &w, 2);
    memcpy(b + 10, &rd, 4); memcpy(b + 14, &nt, 4); memcpy(b + 18, &pk, 4); memcpy(b + 22, &cn, 4);
    // 必须走环形缓冲：直接写串口时，若环里的数据帧只写出一半，链路帧会插进数据帧中间（2026-10-24 实测坏包）
    put_frame(0x11, now_us(), b, 26);
}

static void writer_task(void *arg) {
    int64_t last = 0;
    for (;;) {
        uint32_t t = tail, h = head;
        if (t != h) {
            uint32_t off = t % RING, n = h - t;
            if (n > RING - off) n = RING - off;  // 回绕处分两段写
            int w = usb_serial_jtag_write_bytes(ring + off, n, pdMS_TO_TICKS(20));
            if (w > 0) { __sync_synchronize(); tail = t + (uint32_t)w; }
        } else {
            vTaskDelay(1);
        }
        int64_t now = esp_timer_get_time();
        if (now - last > 1000000) {
            last = now; send_link();
            // 连上后间隔不到位就补请求（外设可能自己改过）
            struct ble_gap_conn_desc d;
            if (ready && !ble_gap_conn_find(conn, &d) && d.conn_itvl != want_ci) {
                struct ble_gap_upd_params up = {.itvl_min = want_ci, .itvl_max = want_ci, .latency = 0,
                                                .supervision_timeout = 400, .min_ce_len = 0, .max_ce_len = 24};
                ble_gap_update_params(conn, &up);
            }
        }
    }
}

static void reader_task(void *arg) {
    static uint8_t cmd[608];
    uint16_t len = 0;
    uint8_t c;
    for (;;) {
        if (usb_serial_jtag_read_bytes(&c, 1, portMAX_DELAY) != 1) continue;
        if (len == 0 && c != 0xA5) continue;  // 帧外字节丢弃，靠 A5 重新对齐
        cmd[len++] = c;
        if (len >= 4) {
            uint16_t n = cmd[2] | cmd[3] << 8;
            if (n > sizeof cmd - 4) { len = 0; continue; }
            if (len == 4u + n) { handle(cmd[1], cmd + 4, n); len = 0; }
        }
    }
}

void app_main(void) {
    nvs_flash_init();
    usb_serial_jtag_driver_config_t uc = {.tx_buffer_size = 4096, .rx_buffer_size = 1024};
    usb_serial_jtag_driver_install(&uc);
    nimble_port_init();
    ble_hs_cfg.sync_cb = on_sync;
    ble_att_set_preferred_mtu(247);
    nimble_port_freertos_init(host_task);
    xTaskCreate(writer_task, "usb_tx", 4096, NULL, 5, NULL);
    xTaskCreate(reader_task, "usb_rx", 4096, NULL, 5, NULL);
}

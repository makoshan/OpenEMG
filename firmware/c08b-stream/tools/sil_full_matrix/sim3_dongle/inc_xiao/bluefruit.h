#pragma once
#include <cstdint>
#include <cstring>

#define BLE_CONN_HANDLE_INVALID                 0xFFFFu
#define BLE_GAP_AD_TYPE_COMPLETE_LOCAL_NAME     0x09u
#define BLE_GAP_EVT_DATA_LENGTH_UPDATE          0x24u
#define BLE_GAP_PHY_2MBPS                       2u
#define BLE_GATTC_WRITE_CMD_TX_QUEUE_SIZE_DEFAULT 1u
#define BLE_COMMON_OPT_CONN_EVT_EXT             1u

struct ble_gap_evt_adv_report_t {
    char     adv_name[32];
    bool     has_service_uuid;
};

struct ble_gap_data_length_params_t {
    uint16_t max_tx_octets;
    uint16_t max_tx_time_us;
    uint16_t max_rx_octets;
    uint16_t max_rx_time_us;
};

struct ble_evt_t {
    struct { uint16_t evt_id; } header;
    struct {
        struct {
            struct {
                struct {
                    ble_gap_data_length_params_t effective_params;
                } data_length_update;
            } params;
        } gap_evt;
    } evt;
};

struct ble_opt_t {
    struct {
        struct { uint8_t enable; } conn_evt_ext;
    } common_opt;
};

inline uint32_t sd_ble_opt_set(uint32_t, const ble_opt_t *) { return 0; }
inline uint32_t sd_clock_hfclk_request(void) { return 0; }

struct BLEUuid {
    const char *str;
    BLEUuid(const char *s = "") : str(s) {}
};

struct BLEClientService {
    BLEUuid uuid;
    bool present = true;
    explicit BLEClientService(const char *u) : uuid(u) {}
    void begin(void) {}
    bool discover(uint16_t conn_h);
};

struct BLEClientCharacteristic {
    using notify_cb_t = void (*)(BLEClientCharacteristic *, uint8_t *, uint16_t);
    const char *uuid_str;
    uint8_t suffix;
    bool present = true;
    bool notify_enabled = false;
    notify_cb_t notify_cb = nullptr;

    explicit BLEClientCharacteristic(const char *u);
    void begin(void) {}
    bool discover(void);
    bool enableNotify(void);
    void setNotifyCallback(notify_cb_t cb, bool use_ada = true) { (void)use_ada; notify_cb = cb; }
    uint16_t write_resp(const void *data, uint16_t len);
    uint16_t read(void *buf, uint16_t max_len);
};

struct BLEConnection {
    bool is_conn = false;
    uint16_t ci = 24;
    uint16_t mtu = 23;
    uint16_t dl = 27;
    uint8_t  phy = 1;

    bool connected(void) const { return is_conn; }
    uint16_t getConnectionInterval(void) const { return ci; }
    uint16_t getMtu(void) const { return mtu; }
    uint16_t getDataLength(void) const { return dl; }
    uint8_t  getPHY(void) const { return phy; }
    void requestPHY(uint8_t p) { phy = p; }
    void requestDataLengthUpdate(void);
    void requestMtuExchange(uint16_t m);
    void requestConnectionParameter(uint16_t target_ci) { ci = target_ci; }
};

struct SimBluefruit {
    using evt_cb_t = void (*)(ble_evt_t *);
    using conn_cb_t = void (*)(uint16_t);
    using disc_cb_t = void (*)(uint16_t, uint8_t);
    using scan_cb_t = void (*)(ble_gap_evt_adv_report_t *);

    evt_cb_t  evt_cb = nullptr;
    conn_cb_t conn_cb = nullptr;
    disc_cb_t disc_cb = nullptr;
    scan_cb_t rx_cb = nullptr;
    bool scanning = false;

    void configUuid128Count(int) {}
    void configCentralConn(uint16_t, uint16_t, uint8_t, uint8_t) {}
    void begin(int, int) {}
    void setName(const char *) {}
    void setEventCallback(evt_cb_t cb) { evt_cb = cb; }
    void disconnect(uint16_t h);
    BLEConnection *Connection(uint16_t h);

    struct CentralApi {
        uint16_t min_ci = 6, max_ci = 6;
        void setConnInterval(uint16_t a, uint16_t b) { min_ci = a; max_ci = b; }
        void setConnectCallback(conn_cb_t cb);
        void setDisconnectCallback(disc_cb_t cb);
        bool connect(ble_gap_evt_adv_report_t *r);
    } Central;

    struct ScannerApi {
        void setRxCallback(scan_cb_t cb);
        void restartOnDisconnect(bool) {}
        void useActiveScan(bool) {}
        void setInterval(uint16_t, uint16_t) {}
        void start(uint16_t);
        void resume(void) {}
        bool checkReportForUuid(ble_gap_evt_adv_report_t *r, const BLEUuid &) { return r->has_service_uuid; }
        int  parseReportByType(ble_gap_evt_adv_report_t *r, uint8_t type, uint8_t *buf, int max_len) {
            if (type != BLE_GAP_AD_TYPE_COMPLETE_LOCAL_NAME || r->adv_name[0] == '\0') return 0;
            int n = (int)std::strlen(r->adv_name);
            if (n > max_len) n = max_len;
            std::memcpy(buf, r->adv_name, (size_t)n);
            return n;
        }
    } Scanner;
};

extern SimBluefruit Bluefruit;

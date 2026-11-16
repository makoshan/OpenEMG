#pragma once
#include <cstdint>
#include <cstring>

#define BLE_CONN_HANDLE_INVALID               0xFFFFu
#define BLE_GAP_EVT_CONNECTED                 0x10u
#define BLE_GAP_EVT_DISCONNECTED              0x11u
#define BLE_GATTS_EVT_EXCHANGE_MTU_REQUEST    0x55u
#define BLE_GATTC_EVT_EXCHANGE_MTU_RSP        0x3Au
#define CHR_PROPS_NOTIFY                      0x10u
#define CHR_PROPS_READ                        0x02u
#define CHR_PROPS_WRITE                       0x08u
#define SECMODE_OPEN                          1u
#define SECMODE_NO_ACCESS                     0u
#define BANDWIDTH_MAX                         3u
#define BLE_GAP_ADV_FLAGS_LE_ONLY_GENERAL_DISC_MODE 0x06u
#define BLE_GATT_HVX_NOTIFICATION             1u
#define NRF_SUCCESS                           0u
#define NRF_ERROR_INVALID_STATE               8u
#define BLE_HCI_REMOTE_USER_TERMINATED_CONNECTION 0x13u

struct ble_evt_t {
    struct { uint16_t evt_id; } header;
    struct {
        struct { uint16_t conn_handle; } common_evt;
    } evt;
};

struct ble_gatts_hvx_params_t {
    uint16_t handle;
    uint8_t  type;
    uint16_t offset;
    uint16_t *p_len;
    uint8_t  *p_data;
};

uint32_t sd_ble_gattc_exchange_mtu_request(uint16_t conn_h, uint16_t client_rx_mtu);
uint32_t sd_ble_gatts_hvx(uint16_t conn_h, const ble_gatts_hvx_params_t *p);
uint32_t sd_ble_gap_disconnect(uint16_t conn_h, uint8_t hci_status_code);

struct BLEService {
    const char *uuid_str;
    explicit BLEService(const char *u) : uuid_str(u) {}
    void begin(void) {}
};

struct BLECharacteristic {
    using write_cb_t = void (*)(uint16_t, BLECharacteristic *, uint8_t *, uint16_t);
    struct Handles { uint16_t value_handle; };
    const char *uuid_str;
    uint8_t  suffix;
    uint16_t val_handle;
    bool     notify_en = false;
    write_cb_t write_cb = nullptr;

    explicit BLECharacteristic(const char *u);
    void setProperties(uint8_t) {}
    void setPermission(uint8_t, uint8_t) {}
    void setMaxLen(uint16_t) {}
    void setFixedLen(uint16_t) {}
    void setWriteCallback(write_cb_t cb, bool use_ada = true) { (void)use_ada; write_cb = cb; }
    void begin(void) {}
    size_t write(const void *data, size_t len);
    size_t write(const char *str) { return write(str, std::strlen(str)); }
    bool notifyEnabled(uint16_t conn_h) const;
    Handles handles(void) const { return Handles{val_handle}; }
};

struct BLEConnection {
    uint16_t mtu = 23;
    uint16_t getMtu(void) const { return mtu; }
};

struct SimX2Bluefruit {
    using evt_cb_t = void (*)(ble_evt_t *);
    evt_cb_t evt_cb = nullptr;
    char dev_name[32] = {0};

    void configUuid128Count(int) {}
    void configPrphBandwidth(int) {}
    void begin(int, int) {}
    void setName(const char *n) { std::strncpy(dev_name, n, sizeof(dev_name) - 1); }
    void setEventCallback(evt_cb_t cb) { evt_cb = cb; }
    BLEConnection *Connection(uint16_t h);

    struct PeriphApi { void setConnInterval(uint16_t, uint16_t) {} } Periph;
    struct AdvApi {
        void addFlags(uint8_t) {}
        void addService(BLEService &) {}
        void restartOnDisconnect(bool) {}
        void setInterval(uint16_t, uint16_t) {}
        void start(uint16_t) {}
    } Advertising;
    struct ScanRspApi { void addName(void) {} } ScanResponse;
};

extern SimX2Bluefruit Bluefruit;

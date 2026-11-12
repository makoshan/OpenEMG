#pragma once
#include "Arduino.h"
#include <string>
inline std::string mock_metadata;
#include <vector>
inline std::vector<uint8_t> mock_status;
#define BLE_CONN_HANDLE_INVALID 65535
#define NRF_SUCCESS 0
#define NRF_ERROR_RESOURCES 19
#define NRF_ERROR_BUSY 17
#define BLE_GATTS_EVT_HVN_TX_COMPLETE 5
#define BLE_GAP_PHY_2MBPS 2
#define BLE_GATTC_WRITE_CMD_TX_QUEUE_SIZE_DEFAULT 1
struct ble_gap_phys_t {int tx_phys,rx_phys;};
inline int sd_ble_gap_phy_update(uint16_t,ble_gap_phys_t*){return 0;}
#define BLE_GAP_EVT_CONNECTED 1
#define BLE_GAP_EVT_DISCONNECTED 2
#define BLE_GATTS_EVT_EXCHANGE_MTU_REQUEST 3
#define BLE_GATTC_EVT_EXCHANGE_MTU_RSP 4
#define BLE_HCI_REMOTE_USER_TERMINATED_CONNECTION 0
#define BLE_GATT_HVX_NOTIFICATION 1
#define BANDWIDTH_MAX 0
#define CHR_PROPS_NOTIFY 1
#define CHR_PROPS_READ 2
#define CHR_PROPS_WRITE 3
#define SECMODE_OPEN 1
#define SECMODE_NO_ACCESS 0
#define BLE_GAP_ADV_FLAGS_LE_ONLY_GENERAL_DISC_MODE 1
struct ble_evt_t { struct {uint16_t evt_id;} header; struct {struct {uint16_t conn_handle;} common_evt; struct {struct {struct {uint16_t count;} hvn_tx_complete;} params;} gatts_evt;} evt; };
struct ble_gatts_hvx_params_t { uint16_t handle, type, *p_len; const uint8_t *p_data; };
inline uint32_t mock_hvx_rc = NRF_SUCCESS;
inline unsigned mock_hvx_calls = 0;
inline uint32_t sd_ble_gatts_hvx(uint16_t, ble_gatts_hvx_params_t *) { ++mock_hvx_calls; return mock_hvx_rc; }
inline void sd_ble_gap_disconnect(uint16_t, int) {}
inline void sd_ble_gattc_exchange_mtu_request(uint16_t, int) {}
struct BLEConnection { uint16_t getMtu() {return 247;} };
struct BLEService { BLEService(const char *) {} void begin() {} };
struct BLECharacteristic {
 BLECharacteristic(const char *) {} struct Handles {uint16_t value_handle=1;}; Handles handles() {return {};}
 bool notifyEnabled(uint16_t) {return mock_subscribed;}
 void setProperties(int) {} void setPermission(int,int) {} void setMaxLen(int) {} void setFixedLen(int) {} void begin() {}
 template<class T> void setWriteCallback(T, bool) {}
 int write(const char *s) {mock_metadata=s;return int(strlen(s));} int write(const uint8_t *p, size_t n) {mock_status.assign(p,p+n);return int(n);}
};
struct MockAdvertising {
 void addFlags(int) {} void addService(BLEService &) {} void addName() {}
 void restartOnDisconnect(bool) {} void setInterval(int,int) {} void start(int) {}
};
struct MockBluefruit {
 struct {void setConnInterval(int,int){}} Periph;
 MockAdvertising Advertising, ScanResponse;
 void configPrphConn(int,int,int,int){}
 void configUuid128Count(int) {} void configPrphBandwidth(int) {} void begin(int,int) {} void setName(const char *) {}
 template<class T> void setEventCallback(T) {}
 BLEConnection *Connection(uint16_t) {static BLEConnection c;return &c;}
};
inline MockBluefruit Bluefruit;

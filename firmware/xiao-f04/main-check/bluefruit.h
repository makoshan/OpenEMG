
#pragma once
#include <stdint.h>
#include <stddef.h>
#include <string.h>
#include <assert.h>
#include <vector>
#define BLE_CONN_HANDLE_INVALID 65535
#define BLE_GAP_EVT_CONNECTED 1
#define BLE_GAP_EVT_DISCONNECTED 2
#define BLE_GATTS_EVT_EXCHANGE_MTU_REQUEST 3
#define BLE_GATTC_EVT_EXCHANGE_MTU_RSP 4
#define BLE_GATT_HVX_NOTIFICATION 1
#define BLE_HCI_REMOTE_USER_TERMINATED_CONNECTION 19
#define BANDWIDTH_MAX 3
#define CHR_PROPS_NOTIFY 1
#define CHR_PROPS_READ 2
#define SECMODE_OPEN 1
#define SECMODE_NO_ACCESS 0
#define BLE_GAP_ADV_FLAGS_LE_ONLY_GENERAL_DISC_MODE 2
#define NRF_SUCCESS 0
#define NRF_ERROR_RESOURCES 19
struct ble_evt_t{struct{uint16_t evt_id;}header;struct{struct{uint16_t conn_handle;}common_evt;}evt;};
struct ble_gatts_char_handles_t{uint16_t value_handle=7;};
struct ble_gatts_hvx_params_t{uint16_t handle;uint8_t type;uint16_t offset;uint16_t*p_len;uint8_t*p_data;};
extern bool fake_subscribed,resource_next;
extern std::vector<std::vector<uint8_t>> attempts,queued;
struct BLEConnection{uint16_t mtu=247;uint16_t getMtu(){return mtu;}};
struct BLEService{BLEService(const char*){}void begin(){}};
struct BLECharacteristic{BLECharacteristic(const char*){}void setProperties(int){}void setPermission(int,int){}void setMaxLen(size_t){}void setFixedLen(size_t){}void begin(){}void write(const void*,size_t){}void write(const char*x){assert(strlen(x)<160);}bool notifyEnabled(uint16_t){return fake_subscribed;}ble_gatts_char_handles_t handles(){return {};}};
struct FakePeriph{void setConnInterval(unsigned,unsigned){}};
struct FakeAdv{void addFlags(int){}void addService(BLEService&){}void addName(){}void restartOnDisconnect(bool){}void setInterval(unsigned,unsigned){}void start(unsigned){}};
struct FakeBluefruit{BLEConnection*connection=nullptr;void(*callback)(ble_evt_t*)=nullptr;FakePeriph Periph;FakeAdv Advertising,ScanResponse;void configUuid128Count(unsigned){}void configPrphBandwidth(int){}void begin(int,int){}void setName(const char*){}void setEventCallback(void(*cb)(ble_evt_t*)){callback=cb;}BLEConnection*Connection(uint16_t){return connection;}};
extern FakeBluefruit Bluefruit;
uint32_t sd_ble_gatts_hvx(uint16_t,const ble_gatts_hvx_params_t*);
inline uint32_t sd_ble_gattc_exchange_mtu_request(uint16_t,uint16_t){return NRF_SUCCESS;}
inline uint32_t sd_ble_gap_disconnect(uint16_t,uint8_t){return NRF_SUCCESS;}

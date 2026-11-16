#pragma once
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <string.h>

typedef int portMUX_TYPE;
#define portMUX_INITIALIZER_UNLOCKED 0
#define portMAX_DELAY 0xFFFFFFFFu
#define pdMS_TO_TICKS(ms) (ms)
typedef void (*TaskFunction_t)(void *);

void taskENTER_CRITICAL(portMUX_TYPE *mux);
void taskEXIT_CRITICAL(portMUX_TYPE *mux);
void vTaskDelay(uint32_t ticks);
int  xTaskCreate(TaskFunction_t fn, const char *name, uint32_t stack, void *arg, int prio, void *out_h);
int64_t esp_timer_get_time(void);
int  nvs_flash_init(void);

typedef struct { uint32_t tx_buffer_size; uint32_t rx_buffer_size; } usb_serial_jtag_driver_config_t;
int  usb_serial_jtag_driver_install(const usb_serial_jtag_driver_config_t *cfg);
int  usb_serial_jtag_write_bytes(const void *src, size_t size, uint32_t ticks);
int  usb_serial_jtag_read_bytes(void *buf, uint32_t length, uint32_t ticks);

#define BLE_HS_CONN_HANDLE_NONE     0xFFFFu
#define BLE_HS_FOREVER              (-1)
#define BLE_HS_EDONE                14
#define BLE_ERR_REM_USER_CONN_TERM  0x13u
#define BLE_GATT_DSC_CLT_CFG_UUID16 0x2902u
#define BLE_GAP_LE_PHY_2M_MASK      2u
#define BLE_GAP_LE_PHY_CODED_ANY    0u

enum {
    BLE_GAP_EVENT_CONNECT = 0,
    BLE_GAP_EVENT_DISCONNECT = 1,
    BLE_GAP_EVENT_CONN_UPDATE_REQ = 2,
    BLE_GAP_EVENT_L2CAP_UPDATE_REQ = 3,
    BLE_GAP_EVENT_DISC = 4,
    BLE_GAP_EVENT_DISC_COMPLETE = 5,
    BLE_GAP_EVENT_NOTIFY_RX = 6,
    BLE_GAP_EVENT_DATA_LEN_CHG = 7,
};

typedef struct { uint8_t type; } ble_uuid_t;
typedef struct { ble_uuid_t u; uint16_t value; } ble_uuid16_t;
typedef struct { ble_uuid_t u; uint8_t value[16]; } ble_uuid128_t;

#define BLE_UUID128_INIT(b0,b1,b2,b3,b4,b5,b6,b7,b8,b9,b10,b11,b12,b13,b14,b15) \
    { .u = { .type = 128 }, .value = { b0,b1,b2,b3,b4,b5,b6,b7,b8,b9,b10,b11,b12,b13,b14,b15 } }

int      ble_uuid_cmp(const ble_uuid_t *a, const ble_uuid_t *b);
uint16_t ble_uuid_u16(const ble_uuid_t *u);

struct os_mbuf { const uint8_t *data; uint16_t len; };
#define OS_MBUF_PKTLEN(om) ((om) ? (om)->len : 0u)
int os_mbuf_copydata(const struct os_mbuf *om, int off, int len, void *dst);

struct ble_gatt_error { uint16_t status; };
struct ble_gatt_attr  { uint16_t handle; uint16_t offset; struct os_mbuf *om; };
struct ble_gatt_svc   { uint16_t start_handle; uint16_t end_handle; };
struct ble_gatt_chr   { uint16_t def_handle; uint16_t val_handle; ble_uuid128_t uuid; };
struct ble_gatt_dsc   { uint16_t handle; ble_uuid16_t uuid; };

typedef int (*ble_gatt_mtu_fn)(uint16_t, const struct ble_gatt_error *, uint16_t, void *);
typedef int (*ble_gatt_disc_svc_fn)(uint16_t, const struct ble_gatt_error *, const struct ble_gatt_svc *, void *);
typedef int (*ble_gatt_chr_fn)(uint16_t, const struct ble_gatt_error *, const struct ble_gatt_chr *, void *);
typedef int (*ble_gatt_dsc_fn)(uint16_t, const struct ble_gatt_error *, uint16_t, const struct ble_gatt_dsc *, void *);
typedef int (*ble_gatt_attr_fn)(uint16_t, const struct ble_gatt_error *, struct ble_gatt_attr *, void *);

int ble_gattc_exchange_mtu(uint16_t conn_h, ble_gatt_mtu_fn cb, void *arg);
int ble_gattc_disc_svc_by_uuid(uint16_t conn_h, const ble_uuid_t *uuid, ble_gatt_disc_svc_fn cb, void *arg);
int ble_gattc_disc_all_chrs(uint16_t conn_h, uint16_t start_h, uint16_t end_h, ble_gatt_chr_fn cb, void *arg);
int ble_gattc_disc_all_dscs(uint16_t conn_h, uint16_t start_h, uint16_t end_h, ble_gatt_dsc_fn cb, void *arg);
int ble_gattc_write_flat(uint16_t conn_h, uint16_t attr_h, const void *data, uint16_t len, ble_gatt_attr_fn cb, void *arg);
int ble_gattc_read_long(uint16_t conn_h, uint16_t attr_h, uint16_t offset, ble_gatt_attr_fn cb, void *arg);

typedef struct { uint8_t type; uint8_t val[6]; } ble_addr_t;
struct ble_gap_disc_params { uint16_t itvl; uint16_t window; uint8_t filter_policy; uint8_t limited; uint8_t passive; uint8_t filter_duplicates; };
struct ble_gap_conn_params { uint16_t scan_itvl; uint16_t scan_window; uint16_t itvl_min; uint16_t itvl_max; uint16_t latency; uint16_t supervision_timeout; uint16_t min_ce_len; uint16_t max_ce_len; };
struct ble_gap_upd_params  { uint16_t itvl_min; uint16_t itvl_max; uint16_t latency; uint16_t supervision_timeout; uint16_t min_ce_len; uint16_t max_ce_len; };
struct ble_gap_conn_desc   { uint16_t conn_itvl; };

struct ble_gap_event {
    int type;
    union {
        struct { uint8_t length_data; const uint8_t *data; ble_addr_t addr; } disc;
        struct { int status; uint16_t conn_handle; } connect;
        struct { int reason; } disconnect;
        struct { struct ble_gap_upd_params *self_params; } conn_update_req;
        struct { uint16_t max_rx_octets; } data_len_chg;
        struct { uint16_t attr_handle; struct os_mbuf *om; } notify_rx;
    };
};

struct ble_hs_adv_fields { const uint8_t *name; uint8_t name_len; };
typedef int (*ble_gap_event_fn)(struct ble_gap_event *, void *);

int ble_hs_adv_parse_fields(struct ble_hs_adv_fields *f, const uint8_t *data, uint8_t len);
int ble_gap_disc(uint8_t own_addr_type, int32_t dur, const struct ble_gap_disc_params *p, ble_gap_event_fn cb, void *arg);
int ble_gap_disc_cancel(void);
int ble_gap_connect(uint8_t own_addr_type, const ble_addr_t *addr, int32_t dur, const struct ble_gap_conn_params *p, ble_gap_event_fn cb, void *arg);
int ble_gap_terminate(uint16_t conn_h, uint8_t hci_reason);
int ble_gap_set_prefered_le_phy(uint16_t conn_h, uint8_t tx_mask, uint8_t rx_mask, uint16_t opts);
int ble_gap_set_data_len(uint16_t conn_h, uint16_t tx_octets, uint16_t tx_time);
int ble_gap_conn_find(uint16_t conn_h, struct ble_gap_conn_desc *out);
int ble_gap_read_le_phy(uint16_t conn_h, uint8_t *tx_phy, uint8_t *rx_phy);
int ble_gap_update_params(uint16_t conn_h, const struct ble_gap_upd_params *p);
uint16_t ble_att_mtu(uint16_t conn_h);
int ble_att_set_preferred_mtu(uint16_t mtu);
int ble_hs_util_ensure_addr(int prefer_random);
int ble_hs_id_infer_auto(int privacy, uint8_t *out_addr_type);

struct ble_hs_cfg_s { void (*sync_cb)(void); };
extern struct ble_hs_cfg_s ble_hs_cfg;

void nimble_port_init(void);
void nimble_port_run(void);
void nimble_port_freertos_init(void (*host_task_fn)(void *));
void nimble_port_freertos_deinit(void);

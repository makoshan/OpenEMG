#pragma once
#include <stdint.h>
#include <stddef.h>
#include "../hw_twin/v001_board.hpp"

extern uint32_t nrf_SystemCoreClock;
uint32_t nrf_SysTick_Config(uint32_t ticks);
inline void NVIC_SystemReset(void) { sim_nrf_system_reset(); }

/* ---------- NRF GPIO ---------- */
struct SimNrfOutSetReg {
    int port_idx;
    uint32_t operator=(uint32_t v) volatile { sim_nrf_gpio_outset(port_idx, v); return v; }
};
struct SimNrfOutClrReg {
    int port_idx;
    uint32_t operator=(uint32_t v) volatile { sim_nrf_gpio_outclr(port_idx, v); return v; }
};
struct SimNrfInReg {
    int port_idx;
    operator uint32_t() const volatile { return sim_nrf_gpio_in(port_idx); }
};
struct SimNrfPinCnfReg {
    int port_idx;
    int pin;
    uint32_t val;
    operator uint32_t() const volatile { return val; }
    uint32_t operator=(uint32_t v) volatile { val = v; sim_nrf_gpio_cnf_write(port_idx, pin, v); return v; }
};

typedef struct {
    SimNrfOutSetReg OUTSET;
    SimNrfOutClrReg OUTCLR;
    SimNrfInReg     IN;
    SimNrfPinCnfReg PIN_CNF[32];
} NRF_GPIO_Type;

#define GPIO_PIN_CNF_DIR_Pos          0u
#define GPIO_PIN_CNF_DIR_Input        0u
#define GPIO_PIN_CNF_DIR_Output       1u
#define GPIO_PIN_CNF_INPUT_Pos        1u
#define GPIO_PIN_CNF_INPUT_Connect    0u
#define GPIO_PIN_CNF_INPUT_Disconnect 1u
#define GPIO_PIN_CNF_PULL_Pos         2u
#define GPIO_PIN_CNF_PULL_Disabled    0u
#define GPIO_PIN_CNF_PULL_Pulldown    1u
#define GPIO_PIN_CNF_PULL_Pullup      3u

extern NRF_GPIO_Type g_sim_nrf_p0;
extern NRF_GPIO_Type g_sim_nrf_p1;
#define NRF_P0 (&g_sim_nrf_p0)
#define NRF_P1 (&g_sim_nrf_p1)

/* ---------- Generic Task Trigger ---------- */
template <void (*Fn)()>
struct SimTaskReg {
    uint32_t operator=(uint32_t v) volatile { if (v) Fn(); return v; }
};

/* ---------- UARTE0 ---------- */
typedef struct {
    struct { volatile uint32_t TXD; volatile uint32_t RXD; } PSEL;
    volatile uint32_t BAUDRATE;
    volatile uint32_t CONFIG;
    volatile uint32_t ENABLE;
    struct { volatile uint32_t PTR; volatile uint32_t MAXCNT; } TXD;
    volatile uint32_t EVENTS_ENDTX;
    SimTaskReg<sim_nrf_uarte_task_starttx> TASKS_STARTTX;
} NRF_UARTE_Type;

#define UARTE_BAUDRATE_BAUDRATE_Baud115200 0x01D7E000u
#define UARTE_ENABLE_ENABLE_Enabled        8u
extern NRF_UARTE_Type g_sim_nrf_uarte0;
#define NRF_UARTE0 (&g_sim_nrf_uarte0)

/* ---------- SAADC ---------- */
typedef struct {
    volatile uint32_t RESOLUTION;
    struct { volatile uint32_t PSELP; volatile uint32_t PSELN; volatile uint32_t CONFIG; } CH[8];
    struct { volatile uint32_t PTR; volatile uint32_t MAXCNT; } RESULT;
    volatile uint32_t ENABLE;
    volatile uint32_t EVENTS_STARTED;
    SimTaskReg<sim_nrf_saadc_task_start>  TASKS_START;
    volatile uint32_t EVENTS_END;
    SimTaskReg<sim_nrf_saadc_task_sample> TASKS_SAMPLE;
    volatile uint32_t EVENTS_STOPPED;
    SimTaskReg<sim_nrf_saadc_task_stop>   TASKS_STOP;
} NRF_SAADC_Type;

#define SAADC_RESOLUTION_VAL_12bit         2u
#define SAADC_CH_PSELP_PSELP_AnalogInput2  3u
#define SAADC_CH_PSELN_PSELN_NC            0u
#define SAADC_CH_CONFIG_GAIN_Gain1_6       0u
#define SAADC_CH_CONFIG_GAIN_Pos           8u
#define SAADC_CH_CONFIG_REFSEL_Internal    0u
#define SAADC_CH_CONFIG_REFSEL_Pos         12u
#define SAADC_CH_CONFIG_TACQ_40us          5u
#define SAADC_CH_CONFIG_TACQ_Pos           16u
#define SAADC_CH_CONFIG_MODE_SE            0u
#define SAADC_CH_CONFIG_MODE_Pos           20u
extern NRF_SAADC_Type g_sim_nrf_saadc;
#define NRF_SAADC (&g_sim_nrf_saadc)

/* ---------- SPIS1 ---------- */
typedef struct {
    struct { volatile uint32_t SCK; volatile uint32_t MOSI; volatile uint32_t MISO; volatile uint32_t CSN; } PSEL;
    volatile uint32_t CONFIG;
    volatile uint32_t DEF;
    volatile uint32_t ORC;
    volatile uint32_t SHORTS;
    volatile uint32_t ENABLE;
    struct { volatile uint32_t PTR; volatile uint32_t MAXCNT; volatile uint32_t AMOUNT; } RXD;
    struct { volatile uint32_t PTR; volatile uint32_t MAXCNT; volatile uint32_t AMOUNT; } TXD;
    volatile uint32_t EVENTS_ACQUIRED;
    volatile uint32_t EVENTS_END;
    SimTaskReg<sim_nrf_spis_task_release> TASKS_RELEASE;
    SimTaskReg<sim_nrf_spis_task_acquire> TASKS_ACQUIRE;
} NRF_SPIS_Type;

#define SPIS_SHORTS_END_ACQUIRE_Msk (1u << 2)
#define SPIS_ENABLE_ENABLE_Enabled  2u
extern NRF_SPIS_Type g_sim_nrf_spis1;
#define NRF_SPIS1 (&g_sim_nrf_spis1)

/* ---------- RADIO ---------- */
typedef struct {
    volatile uint32_t MODE;
    volatile uint32_t TXPOWER;
    volatile uint32_t PCNF0;
    volatile uint32_t PCNF1;
    volatile uint32_t BASE0;
    volatile uint32_t PREFIX0;
    volatile uint32_t TXADDRESS;
    volatile uint32_t RXADDRESSES;
    volatile uint32_t CRCCNF;
    volatile uint32_t CRCPOLY;
    volatile uint32_t CRCINIT;
    volatile uint32_t PACKETPTR;
    volatile uint32_t SHORTS;
    volatile uint32_t FREQUENCY;
    volatile uint32_t DATAWHITEIV;
    volatile uint32_t EVENTS_DISABLED;
    SimTaskReg<sim_nrf_radio_task_txen> TASKS_TXEN;
} NRF_RADIO_Type;

#define RADIO_MODE_MODE_Ble_1Mbit      3u
#define RADIO_TXPOWER_TXPOWER_0dBm     0u
#define RADIO_PCNF0_LFLEN_Pos          0u
#define RADIO_PCNF0_S0LEN_Pos          8u
#define RADIO_PCNF0_S1LEN_Pos          16u
#define RADIO_PCNF1_MAXLEN_Pos         0u
#define RADIO_PCNF1_STATLEN_Pos        8u
#define RADIO_PCNF1_BALEN_Pos          16u
#define RADIO_PCNF1_ENDIAN_Little      0u
#define RADIO_PCNF1_ENDIAN_Pos         24u
#define RADIO_PCNF1_WHITEEN_Enabled    1u
#define RADIO_PCNF1_WHITEEN_Pos        25u
#define RADIO_CRCCNF_LEN_Three         3u
#define RADIO_CRCCNF_LEN_Pos           0u
#define RADIO_CRCCNF_SKIPADDR_Skip     1u
#define RADIO_CRCCNF_SKIPADDR_Pos      8u
#define RADIO_SHORTS_READY_START_Msk   (1u << 0)
#define RADIO_SHORTS_END_DISABLE_Msk   (1u << 1)
extern NRF_RADIO_Type g_sim_nrf_radio;
#define NRF_RADIO (&g_sim_nrf_radio)

/* ---------- FICR / UICR / POWER / NVMC / CLOCK / TIMER2 ---------- */
typedef struct { volatile uint32_t DEVICEADDR[2]; } NRF_FICR_Type;
typedef struct { volatile uint32_t APPROTECT; } NRF_UICR_Type;
typedef struct { volatile uint32_t GPREGRET2; } NRF_POWER_Type;
typedef struct { volatile uint32_t CONFIG; volatile uint32_t READY; } NRF_NVMC_Type;
typedef struct {
    volatile uint32_t EVENTS_HFCLKSTARTED;
    SimTaskReg<sim_nrf_clock_task_hfclkstart> TASKS_HFCLKSTART;
} NRF_CLOCK_Type;

struct SimTimerCaptureReg {
    int idx;
    uint32_t operator=(uint32_t v) volatile { if (v) sim_nrf_timer2_task_capture(idx); return v; }
};

typedef struct {
    volatile uint32_t TASKS_STOP;
    SimTaskReg<sim_nrf_timer2_task_clear> TASKS_CLEAR;
    volatile uint32_t TASKS_START;
    SimTimerCaptureReg TASKS_CAPTURE[6];
    volatile uint32_t CC[6];
    volatile uint32_t MODE;
    volatile uint32_t BITMODE;
    volatile uint32_t PRESCALER;
} NRF_TIMER_Type;

#define NVMC_CONFIG_WEN_Ren 0u
#define NVMC_CONFIG_WEN_Wen 1u
#define TIMER_MODE_MODE_Timer          0u
#define TIMER_BITMODE_BITMODE_32Bit    3u

extern NRF_FICR_Type  g_sim_nrf_ficr;
extern NRF_UICR_Type  g_sim_nrf_uicr;
extern NRF_POWER_Type g_sim_nrf_power;
extern NRF_NVMC_Type  g_sim_nrf_nvmc;
extern NRF_CLOCK_Type g_sim_nrf_clock;
extern NRF_TIMER_Type g_sim_nrf_timer2;

#define NRF_FICR   (&g_sim_nrf_ficr)
#define NRF_UICR   (&g_sim_nrf_uicr)
#define NRF_POWER  (&g_sim_nrf_power)
#define NRF_NVMC   (&g_sim_nrf_nvmc)
#define NRF_CLOCK  (&g_sim_nrf_clock)
#define NRF_TIMER2 (&g_sim_nrf_timer2)

/* ==================== S140 v7.3.0 BLE GATT Mock Definitions ==================== */
#define NRF_SUCCESS            0u
#define NRF_ERROR_NOT_FOUND    5u
#define NRF_ERROR_RESOURCES    19u

#define BLE_CONN_HANDLE_INVALID        0xFFFFu
#define BLE_GAP_ADV_SET_HANDLE_NOT_SET 0xFFu

#define NRF_CLOCK_LF_SRC_RC            0u
#define NRF_CLOCK_LF_SRC_XTAL          1u
#define NRF_CLOCK_LF_ACCURACY_500_PPM  1u

typedef struct {
    uint8_t source;
    uint8_t rc_ctiv;
    uint8_t rc_temp_ctiv;
    uint8_t accuracy;
} nrf_clock_lf_cfg_t;

typedef void (*nrf_fault_handler_t)(uint32_t id, uint32_t pc, uint32_t info);

#define BLE_COMMON_CFG_VS_UUID 1u
#define BLE_CONN_CFG_GAP       2u
#define BLE_CONN_CFG_GATT      3u
#define BLE_CONN_CFG_GATTS     4u

typedef struct {
    struct { struct { uint8_t vs_uuid_count; } vs_uuid_cfg; } common_cfg;
    struct {
        uint8_t conn_cfg_tag;
        struct {
            struct { uint16_t att_mtu; } gatt_conn_cfg;
            struct { uint8_t conn_count; uint16_t event_length; } gap_conn_cfg;
            struct { uint8_t hvn_tx_queue_size; } gatts_conn_cfg;
        } params;
    } conn_cfg;
} ble_cfg_t;

typedef struct { uint8_t uuid128[16]; } ble_uuid128_t;
typedef struct { uint16_t uuid; uint8_t type; } ble_uuid_t;
typedef struct { uint8_t sm : 4; uint8_t lv : 4; } ble_gap_conn_sec_mode_t;
#define BLE_GAP_CONN_SEC_MODE_SET_OPEN(ptr)      do { (ptr)->sm = 1; (ptr)->lv = 1; } while (0)
#define BLE_GAP_CONN_SEC_MODE_SET_NO_ACCESS(ptr) do { (ptr)->sm = 0; (ptr)->lv = 0; } while (0)

#define BLE_GATTS_SRVC_TYPE_PRIMARY 1u
#define BLE_GATTS_VLOC_STACK        1u
#define BLE_GATT_HVX_NOTIFICATION   1u

typedef struct {
    uint16_t value_handle;
    uint16_t user_desc_handle;
    uint16_t cccd_handle;
    uint16_t sccd_handle;
} ble_gatts_char_handles_t;

typedef struct {
    uint16_t len;
    uint16_t offset;
    uint8_t *p_value;
} ble_gatts_value_t;

typedef struct {
    ble_gap_conn_sec_mode_t read_perm;
    ble_gap_conn_sec_mode_t write_perm;
    uint8_t vlen;
    uint8_t vloc;
} ble_gatts_attr_md_t;

typedef struct {
    struct { uint8_t read; uint8_t write; uint8_t notify; } char_props;
    ble_gatts_attr_md_t *p_cccd_md;
} ble_gatts_char_md_t;

typedef struct {
    ble_uuid_t          *p_uuid;
    ble_gatts_attr_md_t *p_attr_md;
    uint16_t             init_len;
    uint16_t             max_len;
    uint8_t             *p_value;
} ble_gatts_attr_t;

typedef struct {
    uint16_t       handle;
    uint8_t        type;
    uint16_t       offset;
    uint16_t      *p_len;
    const uint8_t *p_data;
} ble_gatts_hvx_params_t;

#define BLE_GAP_ADV_TYPE_CONNECTABLE_SCANNABLE_UNDIRECTED 0x01u
#define BLE_GAP_ADV_FP_ANY                                0x00u
#define BLE_GAP_PHY_AUTO                                  0x00u
#define BLE_GAP_PHY_1MBPS                                 0x01u
#define BLE_GAP_PHY_2MBPS                                 0x02u

#define BLE_GAP_AD_TYPE_FLAGS                             0x01u
#define BLE_GAP_ADV_FLAGS_LE_ONLY_GENERAL_DISC_MODE       0x06u
#define BLE_GAP_AD_TYPE_128BIT_SERVICE_UUID_COMPLETE      0x07u
#define BLE_GAP_AD_TYPE_COMPLETE_LOCAL_NAME               0x09u

typedef struct { uint8_t *p_data; uint16_t len; } ble_data_t;
typedef struct { ble_data_t adv_data; ble_data_t scan_rsp_data; } ble_gap_adv_data_t;
typedef struct {
    struct { uint8_t type; } properties;
    uint32_t interval;
    uint16_t duration;
    uint8_t  filter_policy;
    uint8_t  primary_phy;
} ble_gap_adv_params_t;
typedef struct { uint8_t tx_phys; uint8_t rx_phys; } ble_gap_phys_t;

enum {
    BLE_GAP_EVT_CONNECTED = 0x10,
    BLE_GAP_EVT_DISCONNECTED,
    BLE_GAP_EVT_PHY_UPDATE_REQUEST,
    BLE_GAP_EVT_DATA_LENGTH_UPDATE_REQUEST,
    BLE_GATTS_EVT_WRITE = 0x50,
    BLE_GATTS_EVT_EXCHANGE_MTU_REQUEST,
    BLE_GATTS_EVT_SYS_ATTR_MISSING,
};

typedef struct {
    uint16_t handle;
    uint16_t len;
    uint8_t  data[32];
} ble_gatts_evt_write_t;

typedef struct {
    struct { uint16_t evt_id; uint16_t evt_len; } header;
    union {
        struct {
            uint16_t conn_handle;
        } gap_evt;
        struct {
            uint16_t conn_handle;
            union {
                struct { uint16_t client_rx_mtu; } exchange_mtu_request;
                ble_gatts_evt_write_t write;
            } params;
        } gatts_evt;
    } evt;
} ble_evt_t;

uint32_t sd_softdevice_enable(const nrf_clock_lf_cfg_t *p_clock_lf_cfg, nrf_fault_handler_t fault_handler);
uint32_t sd_ble_cfg_set(uint32_t cfg_id, const ble_cfg_t *p_cfg, uint32_t app_ram_base);
uint32_t sd_ble_enable(uint32_t *p_app_ram_base);
uint32_t sd_ble_gap_device_name_set(const ble_gap_conn_sec_mode_t *p_write_perm, const uint8_t *p_dev_name, uint16_t len);
uint32_t sd_ble_uuid_vs_add(const ble_uuid128_t *p_vs_uuid, uint8_t *p_uuid_type);
uint32_t sd_ble_gatts_service_add(uint8_t type, const ble_uuid_t *p_uuid, uint16_t *p_handle);
uint32_t sd_ble_gatts_characteristic_add(uint16_t service_handle, const ble_gatts_char_md_t *p_char_md,
                                         const ble_gatts_attr_t *p_attr_char_value, ble_gatts_char_handles_t *p_handles);
uint32_t sd_ble_gatts_value_set(uint16_t conn_handle, uint16_t handle, ble_gatts_value_t *p_value);
uint32_t sd_ble_gap_adv_set_configure(uint8_t *p_adv_handle, const ble_gap_adv_data_t *p_adv_data, const ble_gap_adv_params_t *p_adv_params);
uint32_t sd_ble_gap_adv_start(uint8_t adv_handle, uint8_t conn_cfg_tag);
uint32_t sd_ble_evt_get(uint8_t *p_dest, uint16_t *p_len);
uint32_t sd_ble_gap_phy_update(uint16_t conn_handle, const ble_gap_phys_t *p_gap_phys);
uint32_t sd_ble_gap_data_length_update(uint16_t conn_handle, const void *p_dl_params, void *p_dl_limitation);
uint32_t sd_ble_gatts_exchange_mtu_reply(uint16_t conn_handle, uint16_t server_rx_mtu);
uint32_t sd_ble_gatts_sys_attr_set(uint16_t conn_handle, const uint8_t *p_sys_attr_data, uint16_t len, uint32_t flags);
uint32_t sd_ble_gatts_hvx(uint16_t conn_handle, const ble_gatts_hvx_params_t *p_hvx_params);

#include "inc/Arduino.h"
#include "inc/SPI.h"
#include "inc/bluefruit.h"
#include <cmath>
#include <deque>
#include <vector>

namespace {
uint64_t g_x2_now_us = 1000;
uint32_t g_x2_primask = 0;
uint32_t g_x2_pin_mode[16] = {0};
uint32_t g_x2_pin_out[16]  = {0};
void   (*g_x2_drdy_isr)(void) = nullptr;
bool     g_x2_drdy_irq_en = false;
uint32_t g_x2_saadc_tacq_us = 3;
float    g_x2_avdd_volts = 3.00f;
uint32_t g_x2_hazard_mask = 0;

/* 危险位定义：
 * bit0 = SAADC TACQ < 20us (R26=100k 源阻抗失准)
 * bit1 = D0/D2 被驱成 OUTPUT LOW 漏电
 * bit2 = SCLK > 1.024 MHz
 * bit3 = VCAP1 未等满 512ms tPOR 或 PWDN 复位脉冲 >= 4000us 掉电
 * bit4 = RLD 未两步预热 >=150ms 即直接写 0x23
 * bit5 = 对端已协商 MTU>=247 后外设又重复发起 sd_ble_gattc_exchange_mtu_request 导致 S140 INVALID_STATE(8) */
enum {
    X2_HAZ_SAADC_TACQ   = 1u << 0,
    X2_HAZ_PIN_LEAK     = 1u << 1,
    X2_HAZ_SPI_OVER_1M  = 1u << 2,
    X2_HAZ_POR_OR_PWDN  = 1u << 3,
    X2_HAZ_RLD_WARMUP   = 1u << 4,
    X2_HAZ_DUP_MTU_REQ  = 1u << 5,
};

/* ADS1292 硅级模型 */
struct X2AdsChip {
    uint8_t  regs[0x0C];
    bool     in_rdatac;
    bool     converting;
    uint8_t  spi_state; /* 0=IDLE, 1=RREG_CNT, 2=RREG_DATA, 3=WREG_CNT, 4=WREG_DATA */
    uint8_t  cmd_reg;
    uint8_t  cmd_cnt;
    uint8_t  shift_buf[9];
    int      shift_pos;
    uint64_t pwdn_high_since_us;
    uint64_t pwdn_low_since_us;
    bool     prev_pwdn;
    bool     rld_pdb_on;
    uint64_t rld_pdb_since_us;
    uint64_t next_drdy_us;
    uint64_t sample_idx;
    uint32_t stall_inject_us;
} g_ads1292;

bool          g_ble_conn = false;
BLEConnection g_ble_conn_obj;
bool          g_peer_already_exchanged_mtu = false;
bool          g_mtu_conflict_invalid_state = false;
uint32_t      g_periph_mtu_req_count = 0;

std::vector<uint8_t> g_chr_val[8];
BLECharacteristic   *g_chr_ptr[8] = {nullptr};
struct X2NotifyPkt { uint8_t suffix; uint64_t ts_us; std::vector<uint8_t> data; };
std::deque<X2NotifyPkt> g_notify_q;

void reset_ads1292_regs() {
    std::memset(g_ads1292.regs, 0, sizeof(g_ads1292.regs));
    g_ads1292.regs[0x00] = 0x53u; /* ADS1292 ID */
    g_ads1292.regs[0x01] = 0x02u;
    g_ads1292.regs[0x02] = 0x80u;
    g_ads1292.regs[0x04] = 0x01u;
    g_ads1292.regs[0x05] = 0x01u;
    g_ads1292.regs[0x09] = 0x02u;
    g_ads1292.regs[0x0A] = 0x01u;
    g_ads1292.regs[0x0B] = 0x0Cu;
    g_ads1292.in_rdatac = true;
    g_ads1292.converting = false;
    g_ads1292.spi_state = 0;
    g_ads1292.shift_pos = 0;
    g_ads1292.rld_pdb_on = false;
}

uint64_t ads1292_period_us() {
    uint8_t dr = g_ads1292.regs[0x01] & 0x07u;
    if (dr == 2u) return 2000ull;
    if (dr == 3u) return 1000ull;
    if (dr == 4u) return 500ull;
    if (dr == 5u) return 250ull;
    return 500ull;
}

void synthesize_ads1292_frame() {
    double fs = 1e6 / (double)ads1292_period_us();
    double t_s = (double)(g_ads1292.sample_idx++) / fs;
    bool rld_closed = (g_ads1292.regs[0x06] & 0x23u) == 0x23u;
    double cm_uv = 350.0 * std::sin(2.0 * M_PI * 50.0 * t_s) * (rld_closed ? 0.05 : 1.0);

    g_ads1292.shift_buf[0] = 0xC0u;
    g_ads1292.shift_buf[1] = 0x00u;
    g_ads1292.shift_buf[2] = 0x00u;
    static const double k_gain[8] = {6.0, 1.0, 2.0, 3.0, 4.0, 8.0, 12.0, 6.0};
    for (int ch = 0; ch < 2; ch++) {
        uint8_t chset = g_ads1292.regs[0x04 + ch];
        double gain = k_gain[(chset >> 4) & 7u];
        double lsb_uv = 2.0 * 2.42e6 / gain / 16777215.0;
        uint8_t mux = chset & 0x07u;
        double uv = (ch == 0 ? 0.8 : -0.6); /* 确定性微伏底噪偏置 */
        if (mux == 0x05u) {
            bool int_test = (g_ads1292.regs[0x02] & 0x02u) != 0;
            bool freq_1hz = (g_ads1292.regs[0x02] & 0x01u) != 0;
            if (int_test) {
                double sign = freq_1hz ? ((std::fmod(t_s, 1.0) < 0.5) ? 1.0 : -1.0) : 1.0;
                uv += sign * (2420000.0 / 2400.0);
            }
        } else if (mux == 0x01u) {
            uv = (ch == 0 ? 1.1 : -1.1);
        } else if (mux == 0x00u) {
            uv += 80.0 * std::sin(2.0 * M_PI * (ch == 0 ? 45.0 : 90.0) * t_s) + cm_uv;
        } else if (mux == 0x02u) {
            uv += rld_closed ? (12.0 * std::sin(2.0 * M_PI * 50.0 * t_s)) : 0.0;
        }
        long code = std::lround(uv / lsb_uv);
        if (code > 8388607L) code = 8388607L;
        if (code < -8388608L) code = -8388608L;
        uint32_t u24 = (uint32_t)code & 0xFFFFFFu;
        g_ads1292.shift_buf[3 + ch * 3 + 0] = (uint8_t)(u24 >> 16);
        g_ads1292.shift_buf[3 + ch * 3 + 1] = (uint8_t)(u24 >> 8);
        g_ads1292.shift_buf[3 + ch * 3 + 2] = (uint8_t)(u24);
    }
    g_ads1292.shift_pos = 0;
}

void advance_x2_time(uint64_t delta_us) {
    uint64_t end_us = g_x2_now_us + delta_us;
    while (g_x2_now_us < end_us) {
        if (g_ads1292.converting && g_x2_pin_out[D4] == HIGH && (g_x2_power.USBREGSTATUS & 1u) == 0u &&
            g_ads1292.next_drdy_us <= end_us) {
            g_x2_now_us = g_ads1292.next_drdy_us;
            g_ads1292.next_drdy_us += ads1292_period_us();
            synthesize_ads1292_frame();
            if (g_x2_drdy_irq_en && g_x2_drdy_isr && g_x2_primask == 0u) {
                g_x2_drdy_isr();
            }
        } else {
            g_x2_now_us = end_us;
        }
    }
}
} // namespace

SimNrfPower g_x2_power = {0};
SimX2Timer  g_x2_timer2;
SimSpiMaster SPI;
SimX2Bluefruit Bluefruit;

SimX2Timer::CapProxy &SimX2Timer::CapProxy::operator=(uint32_t v) {
    if (v) g_x2_timer2.CC[idx] = (uint32_t)g_x2_now_us;
    return *this;
}

uint32_t __get_PRIMASK(void) { return g_x2_primask; }
void __disable_irq(void) { g_x2_primask = 1u; }
void __set_PRIMASK(uint32_t m) { g_x2_primask = m; }
void vTaskSuspendAll(void) {}
void xTaskResumeAll(void) {}

void pinMode(uint32_t pin, uint32_t mode) {
    if (pin < 16) {
        g_x2_pin_mode[pin] = mode;
        if ((pin == D0 || pin == D2) && mode == OUTPUT && g_x2_pin_out[pin] == LOW) {
            g_x2_hazard_mask |= X2_HAZ_PIN_LEAK;
        }
    }
}
void digitalWrite(uint32_t pin, uint32_t val) {
    if (pin >= 16) return;
    g_x2_pin_out[pin] = val;
    if ((pin == D0 || pin == D2) && g_x2_pin_mode[pin] == OUTPUT && val == LOW) {
        g_x2_hazard_mask |= X2_HAZ_PIN_LEAK;
    }
    if (pin == D4) { /* ADS_PWDN / RESET_N */
        bool high = (val != LOW);
        if (high && !g_ads1292.prev_pwdn) {
            if (g_ads1292.pwdn_high_since_us == 0) {
                g_ads1292.pwdn_high_since_us = g_x2_now_us;
                reset_ads1292_regs();
            } else {
                uint64_t low_dur = g_x2_now_us - g_ads1292.pwdn_low_since_us;
                if (low_dur >= 4000ull) {
                    /* >= 4ms 进入硬掉电，VCAP1 泄放需重等 POR */
                    g_ads1292.pwdn_high_since_us = g_x2_now_us;
                    reset_ads1292_regs();
                } else if (low_dur >= 8ull) {
                    /* 20us 合法数字复位脉冲 */
                    reset_ads1292_regs();
                } else {
                    g_x2_hazard_mask |= X2_HAZ_POR_OR_PWDN;
                }
            }
        } else if (!high && g_ads1292.prev_pwdn) {
            g_ads1292.pwdn_low_since_us = g_x2_now_us;
            g_ads1292.converting = false;
        }
        g_ads1292.prev_pwdn = high;
    }
}
uint32_t digitalPinToInterrupt(uint32_t pin) { return pin; }
void attachInterrupt(uint32_t, void (*fn)(void), uint32_t) { g_x2_drdy_isr = fn; g_x2_drdy_irq_en = true; }
void detachInterrupt(uint32_t) { g_x2_drdy_irq_en = false; }

void analogReadResolution(int) {}
void analogReference(uint32_t) {}
void analogSampleTime(uint32_t us) { g_x2_saadc_tacq_us = us; }
unsigned analogRead(uint32_t pin) {
    if (g_x2_saadc_tacq_us < 20u) g_x2_hazard_mask |= X2_HAZ_SAADC_TACQ;
    advance_x2_time(g_x2_saadc_tacq_us + 2u);
    if (pin != D5) return 0u;
    float v = g_x2_avdd_volts;
    if (v < 0.0f) v = 0.0f;
    if (v > 3.6f) v = 3.6f;
    return (unsigned)std::lround(v / 3.6f * 4095.0f);
}

void delay(uint32_t ms) { advance_x2_time((uint64_t)ms * 1000ull); }
void delayMicroseconds(uint32_t us) { advance_x2_time(us); }
void yield(void) { advance_x2_time(50ull); }

void SimSpiMaster::begin(void) {}
void SimSpiMaster::beginTransaction(const SPISettings &s) {
    if (s.hz > 1024000u) g_x2_hazard_mask |= X2_HAZ_SPI_OVER_1M;
}
void SimSpiMaster::endTransaction(void) {}
void SimSpiMaster::end(void) {}
uint8_t SimSpiMaster::transfer(uint8_t mosi) {
    advance_x2_time(8ull); /* 8 bits @ 1 MHz = 8 us */
    /* P44e 硬件 Q1 互锁：VBUS=1 时 Q1 硬拉低 ADS_RESET_N，SPI 不响应 */
    if (g_x2_pin_out[D7] != LOW || g_x2_pin_out[D4] == LOW || (g_x2_power.USBREGSTATUS & 1u) != 0u) {
        return 0x00u;
    }
    if (g_x2_now_us - g_ads1292.pwdn_high_since_us < 512000ull) {
        g_x2_hazard_mask |= X2_HAZ_POR_OR_PWDN;
        return 0x00u;
    }
    if (g_ads1292.in_rdatac) {
        if (mosi == 0x11u && g_ads1292.shift_pos == 0) {
            g_ads1292.in_rdatac = false;
            return 0x00u;
        }
        if (mosi == 0x08u && !g_ads1292.converting) {
            g_ads1292.converting = true;
            g_ads1292.sample_idx = 0;
            g_ads1292.next_drdy_us = g_x2_now_us + ads1292_period_us();
            return 0x00u;
        }
        uint8_t out = (g_ads1292.shift_pos < 9) ? g_ads1292.shift_buf[g_ads1292.shift_pos] : 0x00u;
        g_ads1292.shift_pos++;
        return out;
    }
    switch (g_ads1292.spi_state) {
    case 0:
        if (mosi == 0x11u) { g_ads1292.in_rdatac = false; return 0x00u; }
        if (mosi == 0x10u) { g_ads1292.in_rdatac = true; g_ads1292.shift_pos = 0; return 0x00u; }
        if (mosi == 0x08u) {
            g_ads1292.converting = true;
            g_ads1292.sample_idx = 0;
            g_ads1292.next_drdy_us = g_x2_now_us + ads1292_period_us();
            return 0x00u;
        }
        if ((mosi & 0xE0u) == 0x20u) { g_ads1292.cmd_reg = mosi & 0x1Fu; g_ads1292.spi_state = 1; return 0x00u; }
        if ((mosi & 0xE0u) == 0x40u) { g_ads1292.cmd_reg = mosi & 0x1Fu; g_ads1292.spi_state = 3; return 0x00u; }
        return 0x00u;
    case 1:
        g_ads1292.cmd_cnt = (mosi & 0x1Fu) + 1u;
        g_ads1292.spi_state = 2;
        return 0x00u;
    case 2: {
        uint8_t r = g_ads1292.cmd_reg++;
        uint8_t v = (r < 0x0Cu) ? g_ads1292.regs[r] : 0x00u;
        if (--g_ads1292.cmd_cnt == 0u) g_ads1292.spi_state = 0;
        return v;
    }
    case 3:
        g_ads1292.cmd_cnt = (mosi & 0x1Fu) + 1u;
        g_ads1292.spi_state = 4;
        return 0x00u;
    case 4: {
        uint8_t r = g_ads1292.cmd_reg++;
        uint8_t val = mosi;
        if (r > 0u && r < 0x0Cu && r != 0x08u) {
            if (r == 0x01u) val &= 0x87u;
            if (r == 0x02u) val = (val & 0x7Bu) | 0x80u;
            if (r == 0x0Au) val &= 0x87u;
            if (r == 0x0Bu) val &= 0x0Cu;
            if (r == 0x06u) {
                if ((val & 0x20u) && !g_ads1292.rld_pdb_on) {
                    g_ads1292.rld_pdb_on = true;
                    g_ads1292.rld_pdb_since_us = g_x2_now_us;
                }
                if ((val & 0x0Fu) != 0u) {
                    if (!g_ads1292.rld_pdb_on || (g_x2_now_us - g_ads1292.rld_pdb_since_us) < 145000ull) {
                        g_x2_hazard_mask |= X2_HAZ_RLD_WARMUP;
                    }
                }
            }
            g_ads1292.regs[r] = val;
        }
        if (--g_ads1292.cmd_cnt == 0u) g_ads1292.spi_state = 0;
        return 0x00u;
    }
    }
    return 0x00u;
}

BLECharacteristic::BLECharacteristic(const char *u) : uuid_str(u) {
    size_t n = std::strlen(u);
    suffix = (n >= 2) ? (uint8_t)std::strtoul(u + n - 2, nullptr, 16) : 0;
    val_handle = 10u + suffix;
    if (suffix < 8) g_chr_ptr[suffix] = this;
}
size_t BLECharacteristic::write(const void *data, size_t len) {
    if (suffix < 8) {
        g_chr_val[suffix].assign((const uint8_t *)data, (const uint8_t *)data + len);
    }
    return len;
}
bool BLECharacteristic::notifyEnabled(uint16_t conn_h) const {
    return g_ble_conn && conn_h == 1u && notify_en;
}
BLEConnection *SimX2Bluefruit::Connection(uint16_t h) {
    return (g_ble_conn && h == 1u) ? &g_ble_conn_obj : nullptr;
}

uint32_t sd_ble_gattc_exchange_mtu_request(uint16_t conn_h, uint16_t client_rx_mtu) {
    if (!g_ble_conn || conn_h != 1u) return NRF_ERROR_INVALID_STATE;
    g_periph_mtu_req_count++;
    /* 2026-10-24 / 10-29 实测硬件定律（ble-dongle/README.md §A3/§A4）：
     * 若中心在连接建立时已主动完成 MTU=247 协商，外设再重复发起 GATTC_EXCHANGE_MTU 会导致 S140 HVX 返回 8 (INVALID_STATE)！ */
    if (g_peer_already_exchanged_mtu) {
        g_mtu_conflict_invalid_state = true;
        g_x2_hazard_mask |= X2_HAZ_DUP_MTU_REQ;
        return NRF_ERROR_INVALID_STATE;
    }
    g_ble_conn_obj.mtu = client_rx_mtu;
    if (Bluefruit.evt_cb) {
        ble_evt_t ev{};
        ev.header.evt_id = BLE_GATTC_EVT_EXCHANGE_MTU_RSP;
        ev.evt.common_evt.conn_handle = 1u;
        Bluefruit.evt_cb(&ev);
    }
    return NRF_SUCCESS;
}

uint32_t sd_ble_gatts_hvx(uint16_t conn_h, const ble_gatts_hvx_params_t *p) {
    if (!g_ble_conn || conn_h != 1u || g_mtu_conflict_invalid_state) {
        return NRF_ERROR_INVALID_STATE;
    }
    if (!p || !p->p_len || !p->p_data) return NRF_ERROR_INVALID_STATE;
    X2NotifyPkt pkt;
    pkt.suffix = 2u;
    pkt.ts_us = g_x2_now_us;
    pkt.data.assign(p->p_data, p->p_data + *p->p_len);
    g_notify_q.push_back(std::move(pkt));
    return NRF_SUCCESS;
}

uint32_t sd_ble_gap_disconnect(uint16_t conn_h, uint8_t) {
    if (g_ble_conn && conn_h == 1u) {
        g_ble_conn = false;
        if (Bluefruit.evt_cb) {
            ble_evt_t ev{};
            ev.header.evt_id = BLE_GAP_EVT_DISCONNECTED;
            ev.evt.common_evt.conn_handle = 1u;
            Bluefruit.evt_cb(&ev);
        }
    }
    return NRF_SUCCESS;
}

/* 直接编译未经修改的真实固件源码 xiao-ads1292-2ch/src/main.cpp */
#include FW_XIAO_2CH_CPP

extern "C" {
void x2_init(float avdd_volts, bool vbus_on) {
    g_x2_now_us = 1000;
    g_x2_primask = 0;
    std::memset(g_x2_pin_mode, 0, sizeof(g_x2_pin_mode));
    std::memset(g_x2_pin_out, 0, sizeof(g_x2_pin_out));
    g_x2_drdy_isr = nullptr;
    g_x2_drdy_irq_en = false;
    g_x2_saadc_tacq_us = 3;
    g_x2_avdd_volts = avdd_volts;
    g_x2_hazard_mask = 0;
    g_x2_power.USBREGSTATUS = vbus_on ? 1u : 0u;
    for (int i = 0; i < 6; i++) g_x2_timer2.TASKS_CAPTURE[i].idx = i;

    g_ads1292 = X2AdsChip{};
    reset_ads1292_regs();

    g_ble_conn = false;
    g_ble_conn_obj = BLEConnection{};
    g_peer_already_exchanged_mtu = false;
    g_mtu_conflict_invalid_state = false;
    g_periph_mtu_req_count = 0;
    g_notify_q.clear();
    for (int i = 0; i < 8; i++) {
        g_chr_val[i].clear();
        if (g_chr_ptr[i]) g_chr_ptr[i]->notify_en = false;
    }

    edge_count = 0; edge_us = 0;
    v12::reset_drdy(drdy_stats);
    requested_mode = 0; request_epoch = 0;
    used_edge = 0; last_edge_us = 0; capture_started = 0;
    ads_status = 0; next_rail_check_us = 0; have_edge = false;
    arm_epoch = 0; arm_handle = BLE_CONN_HANDLE_INVALID;
    link_handle = BLE_CONN_HANDLE_INVALID; link_mtu = 23; link_epoch = 0;
    observed_epoch = 0; pending_request = 0; pending_epoch = 0;
    next_status = 0; notify_failures = 0;
    ads.active = false; ads.fault = v12::Fault::None;

    setup();
}

void x2_ble_connect(bool central_initiates_mtu_247) {
    g_ble_conn = true;
    g_ble_conn_obj.mtu = 23;
    g_peer_already_exchanged_mtu = false;
    g_mtu_conflict_invalid_state = false;
    if (Bluefruit.evt_cb) {
        ble_evt_t ev{};
        ev.header.evt_id = BLE_GAP_EVT_CONNECTED;
        ev.evt.common_evt.conn_handle = 1u;
        Bluefruit.evt_cb(&ev);
    }
    if (central_initiates_mtu_247) {
        g_ble_conn_obj.mtu = 247;
        g_peer_already_exchanged_mtu = true;
        if (Bluefruit.evt_cb) {
            ble_evt_t mev{};
            mev.header.evt_id = BLE_GATTS_EVT_EXCHANGE_MTU_REQUEST;
            mev.evt.common_evt.conn_handle = 1u;
            Bluefruit.evt_cb(&mev);
        }
    }
}

void x2_ble_disconnect(void) { sd_ble_gap_disconnect(1u, 0x13u); }

int x2_ble_subscribe(uint8_t suffix, bool en) {
    if (suffix < 8 && g_chr_ptr[suffix]) {
        g_chr_ptr[suffix]->notify_en = en;
        return 0;
    }
    return -1;
}

int x2_ble_write_ctrl(const uint8_t *data, uint16_t len) {
    if (!g_ble_conn || !g_chr_ptr[5] || !g_chr_ptr[5]->write_cb) return -1;
    g_chr_ptr[5]->write_cb(1u, g_chr_ptr[5], const_cast<uint8_t *>(data), len);
    return 0;
}

int x2_ble_read_char(uint8_t suffix, uint8_t *out, int max_len) {
    if (suffix >= 8 || g_chr_val[suffix].empty()) return -1;
    int n = (int)g_chr_val[suffix].size();
    if (n > max_len) n = max_len;
    std::memcpy(out, g_chr_val[suffix].data(), (size_t)n);
    return n;
}

int x2_ble_pop_notify(uint8_t *out_suffix, uint8_t *out_pkt, int max_len, uint64_t *out_ts) {
    if (g_notify_q.empty()) return 0;
    X2NotifyPkt item = std::move(g_notify_q.front());
    g_notify_q.pop_front();
    int n = ((int)item.data.size() < max_len) ? (int)item.data.size() : max_len;
    if (out_suffix) *out_suffix = item.suffix;
    if (out_ts)     *out_ts     = item.ts_us;
    std::memcpy(out_pkt, item.data.data(), (size_t)n);
    return n;
}

void x2_set_avdd(float volts) { g_x2_avdd_volts = volts; }
void x2_set_vbus(bool on) { g_x2_power.USBREGSTATUS = on ? 1u : 0u; }
void x2_inject_stall_us(uint32_t stall_us) { advance_x2_time(stall_us); }

void x2_step_us(uint64_t total_us) {
    uint64_t target = g_x2_now_us + total_us;
    while (g_x2_now_us < target) {
        uint64_t before = g_x2_now_us;
        loop();
        if (g_x2_now_us == before) advance_x2_time(100ull);
    }
}

void x2_get_telemetry(uint32_t *out_haz, uint16_t *out_mtu, uint32_t *out_mtu_reqs,
                      bool *out_pwdn, char *out_name_32) {
    if (out_haz)      *out_haz      = g_x2_hazard_mask;
    if (out_mtu)      *out_mtu      = link_mtu;
    if (out_mtu_reqs) *out_mtu_reqs = g_periph_mtu_req_count;
    if (out_pwdn)     *out_pwdn     = (g_x2_pin_out[D4] != LOW);
    if (out_name_32)  std::memcpy(out_name_32, Bluefruit.dev_name, 32);
}
}

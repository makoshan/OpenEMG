#include <Arduino.h>
#include <bluefruit.h>
#include <SPI.h>
#include "ads1292.h"
#include "ads1292_pins.h"
#include "bench_release.h"
#include "capture_guard.h"
#include "diagnostics.h"
#include "timebase_board.h"
using v12::clock_us;
#include <v12_build_id.h>
extern "C" {
#include "v12_stream.h"
}

#if MAKO_V12_AFE_ENABLED != 0
#error "只使用 bench_release.h 的实测门，不允许绕过当前硬件锁"
#endif
#if MAKO_V12_FS != 2000 && MAKO_V12_FS != 4000
#error "采样率只允许 2000 或 4000 SPS"
#endif
#ifndef MAKO_V12_SPI_HZ
#define MAKO_V12_SPI_HZ 1000000
#endif
#if MAKO_V12_SPI_HZ != 1000000
#error "TI SBAS502C §7.6 规定内部 512 kHz 下寄存器读写 SCLK <= 1.024 MHz，固定使用 1 MHz"
#endif

static_assert(PIN_SPI_SCK == v12_p44e::XIAO_PIN_SCLK &&
                  PIN_SPI_MISO == v12_p44e::XIAO_PIN_MISO &&
                  PIN_SPI_MOSI == v12_p44e::XIAO_PIN_MOSI,
              "SPI 板包映射与 P44e 契约不一致");
static_assert(D0 == v12_p44e::PIN_UNUSED_D0 && D1 == v12_p44e::PIN_UNUSED_D1 &&
                  D2 == v12_p44e::PIN_UNUSED_D2 && D3 == v12_p44e::PIN_ADS_START &&
                  D4 == v12_p44e::PIN_ADS_PWDN && D5 == v12_p44e::PIN_AVDD_ADC &&
                  D6 == v12_p44e::PIN_ADS_DRDY && D7 == v12_p44e::PIN_ADS_CS,
              "XIAO D0-D7 映射与 P44e 契约不一致");
static_assert(POWER_USBREGSTATUS_VBUSDETECT_Msk == 1u, "USBREGSTATUS VBUSDETECT 掩码异常");

static BLEService service("7b24c101-3948-4f03-9d11-12bb9d000001");
static BLECharacteristic data_chr("7b24c101-3948-4f03-9d11-12bb9d000002");
static BLECharacteristic meta_chr("7b24c101-3948-4f03-9d11-12bb9d000003");
static BLECharacteristic status_chr("7b24c101-3948-4f03-9d11-12bb9d000004");
static BLECharacteristic control_chr("7b24c101-3948-4f03-9d11-12bb9d000005");

static v12_stream stream;
static volatile uint32_t edge_count = 0, edge_us = 0;
static volatile v12::DrdyStats drdy_stats = {0, 0, UINT32_MAX, false};
static volatile uint8_t requested_mode = 0;
static volatile uint32_t request_epoch = 0;
static uint32_t used_edge = 0, last_edge_us = 0, capture_started = 0;
static uint32_t ads_status = 0;
static uint64_t next_rail_check_us = 0;
static bool have_edge = false;
static bool start_session_valid();
static uint32_t arm_epoch = 0;
static uint16_t arm_handle = BLE_CONN_HANDLE_INVALID;

static void on_drdy() {
  const uint32_t now = v12::timer_us(0);
  edge_us = now;
  ++edge_count;
  v12::record_drdy(drdy_stats, now);
}

static float read_avdd_volts() {
  // J2.3 AVDD_SENSE 串联 R26 = 100 kΩ；先丢弃一次 mux 切换读数，再取第二次 12 位 SAADC（3.6 V 满量程）。
  (void)analogRead(D5);
  const unsigned raw = analogRead(D5);
  return float(raw) * 3.6f / 4095.0f;
}

struct BoardHal final : v12::Ads1292Hal {
  bool spi_on = false;
  void spi_bus(bool on) override {
    if (on) {
      SPI.begin();
      SPI.beginTransaction(SPISettings(MAKO_V12_SPI_HZ, MSBFIRST, SPI_MODE1));
      spi_on = true;
    } else {
      if (spi_on) {
        SPI.endTransaction();
        SPI.end();
        spi_on = false;
      }
      const uint8_t low_pins[] = {D8, D10};
      for (uint8_t p : low_pins) {
        digitalWrite(p, LOW);
        pinMode(p, OUTPUT);
      }
    }
  }
  void pwdn(bool high) override { digitalWrite(D4, high ? HIGH : LOW); }
  void start_pin(bool high) override { digitalWrite(D3, high ? HIGH : LOW); }
  void cs(bool high) override { digitalWrite(D7, high ? HIGH : LOW); }
  uint8_t transfer(uint8_t value) override { return SPI.transfer(value); }
  void wait(uint32_t us) override {
    while (us >= 1000u && session_valid() && !vbus_present()) {
      delay(1);
      us -= 1000u;
    }
    if (us < 1000u && us) delayMicroseconds(us);
  }
  bool vbus_present() override {
    return (NRF_POWER->USBREGSTATUS & POWER_USBREGSTATUS_VBUSDETECT_Msk) != 0u;
  }
  bool rails_good() override {
    if (vbus_present()) return false;
    const float avdd = read_avdd_volts();
    return avdd >= 2.75f && avdd <= 3.25f;
  }
  bool session_valid() override { return start_session_valid(); }
  void capture(bool on) override {
    detachInterrupt(digitalPinToInterrupt(D6));
    if (on) {
      const uint32_t mask = __get_PRIMASK();
      __disable_irq();
      edge_count = 0;
      edge_us = 0;
      v12::reset_drdy(drdy_stats);
      __set_PRIMASK(mask);
    }
    used_edge = 0;
    last_edge_us = 0;
    have_edge = false;
    capture_started = v12::timer_us(2);
    next_rail_check_us = clock_us() + 50000u;
    if (on) attachInterrupt(digitalPinToInterrupt(D6), on_drdy, FALLING);
  }
} board_hal;

static v12::Ads1292 ads(board_hal);
static volatile uint16_t link_handle = BLE_CONN_HANDLE_INVALID;
static volatile uint16_t link_mtu = 23;
static volatile uint32_t link_epoch = 0;
static uint32_t observed_epoch = 0;
static uint8_t pending_request = 0;
static uint32_t pending_epoch = 0;
static uint64_t next_status = 0;
static uint64_t notify_failures = 0;

static bool start_session_valid() {
  vTaskSuspendAll();
  const bool valid = arm_handle != BLE_CONN_HANDLE_INVALID &&
                     link_handle == arm_handle && link_epoch == arm_epoch &&
                     requested_mode == 0 && data_chr.notifyEnabled(arm_handle);
  xTaskResumeAll();
  return valid;
}

static void ble_event(ble_evt_t *event) {
  const uint16_t handle = event->evt.common_evt.conn_handle;
  if (event->header.evt_id == BLE_GAP_EVT_CONNECTED) {
    link_handle = handle;
    link_mtu = 23;
    ++link_epoch;
  } else if (event->header.evt_id == BLE_GAP_EVT_DISCONNECTED) {
    link_handle = BLE_CONN_HANDLE_INVALID;
    link_mtu = 23;
    ++link_epoch;
  } else if (handle == link_handle &&
             (event->header.evt_id == BLE_GATTS_EVT_EXCHANGE_MTU_REQUEST ||
              event->header.evt_id == BLE_GATTC_EVT_EXCHANGE_MTU_RSP)) {
    BLEConnection *connection = Bluefruit.Connection(handle);
    if (connection) link_mtu = connection->getMtu();
  }
}

static void hold_afe_off() {
  // P44e 专属安全态：
  // - D0、D2 带 10 kΩ 上拉到常开 3V3，D1 未用 -> 全部保持 INPUT 零漏电（禁驱 LOW）。
  // - D7(CS_A) 带 10 kΩ 上拉到常开 3V3 -> 先置 HIGH 再设 OUTPUT 零漏电且不选中芯片。
  // - D3(START)、D4(PWDN_N) 带 10 kΩ 下拉 -> 先置 LOW 再设 OUTPUT 零漏电且压住硬掉电。
  // - D5(AVDD_SENSE) 设 INPUT 供 SAADC 采样，严禁调用任何 I2C/双线外设初始化。
  pinMode(D0, INPUT);
  pinMode(D1, INPUT);
  pinMode(D2, INPUT);
  digitalWrite(D7, HIGH);
  pinMode(D7, OUTPUT);
  const uint8_t low_outputs[] = {D3, D4, D8, D10};
  for (uint8_t pin : low_outputs) {
    digitalWrite(pin, LOW);
    pinMode(pin, OUTPUT);
  }
  pinMode(D5, INPUT);
  pinMode(D6, INPUT);
  pinMode(D9, INPUT);
  analogReadResolution(12);
  analogReference(AR_INTERNAL);
  // Nordic nRF52840 §6.23.2：默认 TACQ=3 µs 仅支持源阻抗 <=10 kΩ；J2.3 AVDD_SENSE 串 R26=100 kΩ，必须设 >=20 µs（支持 <=400 kΩ）。
  analogSampleTime(20);
}

static void status_update() {
  const uint32_t mask = __get_PRIMASK();
  __disable_irq();
  const uint64_t raw_edges = drdy_stats.raw_edges;
  const uint32_t min_interval = drdy_stats.min_interval_us;
  __set_PRIMASK(mask);
  const v12::StatusSnapshot snapshot = {
      stream.produced,
      stream.ring_dropped,
      stream.scheduler_skipped,
      stream.sent_samples,
      notify_failures,
      uint8_t(ads.fault),
      ads.active,
      bool(MAKO_BENCH_MEASURED),
      ads_status,
      raw_edges,
      min_interval,
      MAKO_V12_SPI_HZ,
  };
  uint8_t bytes[v12::STATUS_BYTES];
  v12::encode_status(bytes, snapshot);
  status_chr.write(bytes, sizeof(bytes));
}

static void control_write(uint16_t handle, BLECharacteristic *, uint8_t *data, uint16_t len) {
  if (handle != link_handle || len != 4) return;
  uint8_t mode = 0;
  if (!memcmp(data, "STOP", 4)) mode = 4;
  else if (!memcmp(data, "TST1", 4)) mode = 1;  // 1 Hz 内部测试方波
  else if (!memcmp(data, "SHT1", 4)) mode = 2;  // 内部输入短接测底噪
  else if (!memcmp(data, "EXT1", 4)) mode = 3;  // 外部电极（不开 RLD；无偏置下拉时仅作对照）
  else if (!memcmp(data, "EXR1", 4)) mode = 5;  // 外部电极 + RLD（首测仅选 CH1）
  else if (!memcmp(data, "RLD1", 4)) mode = 7;  // CH1 外部电极 + CH2 路由 29 脚监测 RLD 环路波形
  if (mode) {
    request_epoch = link_epoch;
    requested_mode = mode;
  }
}

void setup() {
  hold_afe_off();
  v12::timebase_begin();
  if (v12_stream_init(&stream, MAKO_V12_FS)) return;
  Bluefruit.configUuid128Count(5);
  Bluefruit.configPrphBandwidth(BANDWIDTH_MAX);
  Bluefruit.begin(1, 0);
  Bluefruit.setName(MAKO_V12_FS == 2000 ? "MAKO-V12-1292-2K" : "MAKO-V12-1292-4K");
  Bluefruit.Periph.setConnInterval(6, 12);
  Bluefruit.setEventCallback(ble_event);
  service.begin();
  data_chr.setProperties(CHR_PROPS_NOTIFY);
  data_chr.setPermission(SECMODE_OPEN, SECMODE_NO_ACCESS);
  data_chr.setMaxLen(V12_STREAM_PACKET);
  data_chr.begin();
  meta_chr.setProperties(CHR_PROPS_READ);
  meta_chr.setPermission(SECMODE_OPEN, SECMODE_NO_ACCESS);
  meta_chr.setMaxLen(440);
  meta_chr.begin();
  char metadata[440];
  snprintf(metadata, sizeof(metadata),
           "{\"profile\":\"F05_ADS1292_2CH_CANDIDATE\",\"board\":\"ADS1292_2CH_P44E\","
           "\"afe\":\"ADS1292\",\"build_id\":\"%s\",\"fs_Hz\":%u,\"spi_Hz\":%u,"
           "\"channels\":8,\"active_channels\":2,\"vref_mV\":2420,\"gain\":6,"
           "\"bench_measured\":%s,\"protocol\":1,\"clock_tolerance_pct\":2.0,"
           "\"usb_interlock\":\"HW_Q1_AND_SW_USBREGSTATUS\",\"clock_source\":\"TIMER2_1MHz\"}",
           MAKO_V12_BUILD_ID, MAKO_V12_FS, MAKO_V12_SPI_HZ,
           MAKO_BENCH_MEASURED ? "true" : "false");
  meta_chr.write(metadata);
  status_chr.setProperties(CHR_PROPS_READ);
  status_chr.setPermission(SECMODE_OPEN, SECMODE_NO_ACCESS);
  status_chr.setFixedLen(v12::STATUS_BYTES);
  status_chr.begin();
  control_chr.setProperties(CHR_PROPS_WRITE);
  control_chr.setPermission(SECMODE_NO_ACCESS, SECMODE_OPEN);
  control_chr.setMaxLen(4);
  control_chr.setWriteCallback(control_write, false);
  control_chr.begin();
  status_update();
  Bluefruit.Advertising.addFlags(BLE_GAP_ADV_FLAGS_LE_ONLY_GENERAL_DISC_MODE);
  Bluefruit.Advertising.addService(service);
  Bluefruit.ScanResponse.addName();
  Bluefruit.Advertising.restartOnDisconnect(true);
  Bluefruit.Advertising.setInterval(32, 244);
  Bluefruit.Advertising.start(0);
}

void loop() {
  const uint64_t now = clock_us();
  // 任何时刻检测到 USB VBUS 立即把 D4 拉低停机（配合板上 R32+Q1 形成双互锁）。
  if (ads.active && board_hal.vbus_present()) {
    ads.stop(v12::Fault::UsbInterlock);
    status_update();
  }

  vTaskSuspendAll();
  const uint32_t epoch = link_epoch;
  const uint16_t handle = link_handle;
  const bool subscribed = handle != BLE_CONN_HANDLE_INVALID && data_chr.notifyEnabled(handle);
  xTaskResumeAll();

  if (epoch != observed_epoch) {
    observed_epoch = epoch;
    ads.stop();
    pending_request = 0;
    requested_mode = 0;
    notify_failures = 0;
    v12_stream_init(&stream, MAKO_V12_FS);
  }

  vTaskSuspendAll();
  uint8_t request = requested_mode;
  const uint32_t command_epoch = request_epoch;
  requested_mode = 0;
  xTaskResumeAll();

  if (request && command_epoch == epoch) {
    ads.stop();
    pending_request = (request == 4) ? 0 : request;
    pending_epoch = epoch;
    v12_stream_restart(&stream, MAKO_V12_FS);
    status_update();
  }

  if (handle == BLE_CONN_HANDLE_INVALID) {
    if (ads.active) ads.stop();
    pending_request = 0;
    delay(1);
    return;
  }

  if (pending_request && pending_epoch == epoch) {
    request = pending_request;
    pending_request = 0;
    if (subscribed) {
      arm_epoch = epoch;
      arm_handle = handle;
      const v12::BenchProof proof = {bool(MAKO_BENCH_MEASURED), MAKO_BENCH_POR_US, MAKO_BENCH_REFERENCE_US};
      const bool started = ads.start(MAKO_V12_FS, v12::Input(request), proof);
      if (!start_session_valid()) {
        ads.stop(v12::Fault::Cancelled);
      } else if (started) {
        sd_ble_gattc_exchange_mtu_request(handle, 247);
      }
    }
    status_update();
  }

  if (!subscribed && ads.active) {
    ads.stop(v12::Fault::Cancelled);
  }

  if (ads.active) {
    const uint32_t mask = __get_PRIMASK();
    __disable_irq();
    const uint32_t count = edge_count, edge = edge_us;
    __set_PRIMASK(mask);

    if (board_hal.vbus_present()) {
      ads.stop(v12::Fault::UsbInterlock);
    } else if (count != used_edge) {
      const uint32_t delta = edge - last_edge_us;
      if (v12::uncertain_edge(have_edge, count, used_edge, delta, MAKO_V12_FS)) {
        ads.stop(v12::Fault::Overrun);
      } else {
        uint8_t frame9[v12::Ads1292::FRAME_BYTES];
        int32_t raw[8];
        if (ads.read(frame9)) {
          if (edge_count != count) {
            ads.stop(v12::Fault::Overrun);
          } else if (!v12::Ads1292::decode(frame9, sizeof(frame9), raw, &ads_status)) {
            ads.stop(v12::Fault::Frame);
          } else {
            uint64_t current = clock_us(), stamp = (current & ~UINT64_C(0xffffffff)) | edge;
            if (stamp > current) stamp -= UINT64_C(1) << 32;
            const unsigned slot = (stream.head + stream.count) % V12_STREAM_RING;
            const bool room = stream.count < V12_STREAM_RING;
            if (v12_stream_push(&stream, raw, stamp) != V12_STREAM_OK) {
              ads.stop(v12::Fault::Frame);
            } else {
              // 把 ADS1292 原生 LOFF/GPIO 位序映射为统一 F01 8 通道状态头（status_chr 仍保留原生 ads_status 含 RLD_STAT）。
              if (room) v12::Ads1292::map_f01_status(ads_status, stream.ring[slot].frame);
              used_edge = count;
              last_edge_us = edge;
              have_edge = true;
              // 紧接帧读取完成后的安全空档（距下一帧 >=160 µs）每 50 ms 复检一次 AVDD 3.0V 电源轨。
              if (current >= next_rail_check_us) {
                next_rail_check_us = current + 50000u;
                if (!board_hal.rails_good()) ads.stop(v12::Fault::Rails);
              }
            }
          }
        }
      }
    } else if (v12::capture_timeout(
                   have_edge,
                   uint32_t(v12::timer_us(2) - (have_edge ? last_edge_us : capture_started)),
                   MAKO_V12_FS)) {
      ads.stop(v12::Fault::Timeout);
    }
  }

  vTaskSuspendAll();
  if (ads.active && subscribed && epoch == link_epoch && handle == link_handle) {
    const uint8_t *bytes;
    size_t length;
    if (v12_stream_peek(&stream, link_mtu, &bytes, &length) == V12_STREAM_OK) {
      uint16_t sent = (uint16_t)length;
      ble_gatts_hvx_params_t params = {};
      params.handle = data_chr.handles().value_handle;
      params.type = BLE_GATT_HVX_NOTIFICATION;
      params.p_len = &sent;
      params.p_data = const_cast<uint8_t *>(bytes);
      const uint32_t result = sd_ble_gatts_hvx(handle, &params);
      if (result == NRF_SUCCESS && sent == length) {
        v12_stream_commit(&stream);
      } else {
        ++notify_failures;
        if (result == NRF_SUCCESS) {
          sd_ble_gap_disconnect(handle, BLE_HCI_REMOTE_USER_TERMINATED_CONNECTION);
        }
      }
    }
  }
  xTaskResumeAll();

  if (now >= next_status) {
    status_update();
    next_status = now + 1000000u;
  }
  yield();
}

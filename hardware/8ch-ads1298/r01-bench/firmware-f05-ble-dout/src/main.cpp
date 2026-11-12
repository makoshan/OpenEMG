// R01离体电池+BLE候选：专用DRDY未修复，使用DOUT镜像；仅内部测试源/输入短接。
// 不修改共享F05；不推算补帧。LATCH合并事件，BLE抢占超出安全窗口即停。
#include <Arduino.h>
#include <bluefruit.h>
#include <SPI.h>
#include "ads1298.h"
#include "bench_release.h"
#include "diagnostics.h"
#include "timebase_board.h"
#include "dout_guard.h"
#include <v12_build_id.h>
extern "C" {
#include "v12_stream.h"
}
static_assert(MAKO_V12_FS == 2000 && MAKO_V12_SPI_HZ == 2000000, "只允许2kHz/2MHz候选");
static_assert(PIN_SPI_SCK == 8 && PIN_SPI_MISO == 9 && PIN_SPI_MOSI == 10, "SPI映射变化");
static_assert(MAKO_V12_AFE_ENABLED == 0, "共享F05默认锁不可修改");
static BLEService service("7b24c101-3948-4f03-9d11-12bb9d000001");
static BLECharacteristic data_chr("7b24c101-3948-4f03-9d11-12bb9d000002");
static BLECharacteristic meta_chr("7b24c101-3948-4f03-9d11-12bb9d000003");
static BLECharacteristic status_chr("7b24c101-3948-4f03-9d11-12bb9d000004");
static BLECharacteristic control_chr("7b24c101-3948-4f03-9d11-12bb9d000005");
static v12_stream stream;
static volatile uint16_t link_handle = BLE_CONN_HANDLE_INVALID, link_mtu = 23;
static volatile uint32_t link_epoch = 0, request_epoch = 0;
static volatile uint8_t requested = 0;
static uint32_t observed_epoch = 0, arm_epoch = 0;
static uint16_t arm_handle = BLE_CONN_HANDLE_INVALID;
static uint32_t low_before = 0, started_us = 0, last_observed = 0, ads_status = 0;
static bool baseline = false, have_frame = false, armed = false, saw_high = false;
static uint64_t observed_edges = 0, notify_failures = 0;
static uint32_t min_interval = UINT32_MAX, next_status = 0, drain_start = 0;
static bool draining = false;
static bool start_session_valid();
static bool usb_present() { return (NRF_POWER->USBREGSTATUS & POWER_USBREGSTATUS_VBUSDETECT_Msk) != 0; }
static NRF_GPIO_Type *port() { return g_ADigitalPinMap[D9] >= 32 ? NRF_P1 : NRF_P0; }
static uint32_t mask() { return 1u << (g_ADigitalPinMap[D9] & 31); }
static bool level() { return (port()->IN & mask()) != 0; }
static uint32_t saved_sense = 0, saved_detectmode = 0;
static void sense(bool on) {
  volatile uint32_t &cnf = port()->PIN_CNF[g_ADigitalPinMap[D9] & 31];
  if (on) {
    saved_sense = cnf & GPIO_PIN_CNF_SENSE_Msk;
    saved_detectmode = port()->DETECTMODE;
    cnf = (cnf & ~GPIO_PIN_CNF_SENSE_Msk) | (GPIO_PIN_CNF_SENSE_High << GPIO_PIN_CNF_SENSE_Pos);
    port()->DETECTMODE = GPIO_DETECTMODE_DETECTMODE_LDETECT;
  } else {
    cnf = (cnf & ~GPIO_PIN_CNF_SENSE_Msk) | saved_sense;
    port()->DETECTMODE = saved_detectmode;
  }
  port()->LATCH = mask();
}
struct BoardHal final : v12::AdsHal {
  bool spi_on = false;
  void power(bool on) override {
    if (on) { SPI.begin(); SPI.beginTransaction(SPISettings(MAKO_V12_SPI_HZ, MSBFIRST, SPI_MODE1)); spi_on = true; digitalWrite(D0, HIGH); }
    else { digitalWrite(D0, LOW); if (spi_on) { SPI.endTransaction(); SPI.end(); spi_on = false; }
      const uint8_t outputs[] = {D8, D10}; for (uint8_t p : outputs) { digitalWrite(p, LOW); pinMode(p, OUTPUT); } }
  }
  void pwdn(bool on) override { digitalWrite(D4, on ? HIGH : LOW); }
  void reset(bool on) override { digitalWrite(D2, on ? HIGH : LOW); }
  void clocksel(bool on) override { digitalWrite(D1, on ? HIGH : LOW); }
  void cs(bool on) override { digitalWrite(D7, on ? HIGH : LOW); }
  uint8_t transfer(uint8_t v) override { return SPI.transfer(v); }
  void wait(uint32_t us) override { while (us >= 1000 && session_valid()) { delay(1); us -= 1000; } if (us < 1000 && us) delayMicroseconds(us); }
  bool session_valid() override { return start_session_valid(); }
  bool rails_good() override {
    const float avdd = float(analogRead(D3)) * 14.4f / 4095.0f;
    return !usb_present() && digitalRead(D5) == LOW && avdd >= 4.6f && avdd <= 5.4f;
  }
  void capture(bool on) override {
    // 此处发生在START命令前，DOUT锁存只在START完成后启用，不能把命令位当采样沿。
    if (armed) { sense(false); armed = false; }
    baseline = saw_high = have_frame = false;
    if (on) { observed_edges = 0; min_interval = UINT32_MAX; }
  }
} board;
static v12::Ads1298 ads(board);
static bool start_session_valid() {
  vTaskSuspendAll();
  const bool valid = !usb_present() && arm_handle != BLE_CONN_HANDLE_INVALID && link_handle == arm_handle &&
    link_epoch == arm_epoch && requested == 0 && data_chr.notifyEnabled(arm_handle);
  xTaskResumeAll(); return valid;
}
static void status_update() {
  const v12::StatusSnapshot s = {stream.produced, stream.ring_dropped, stream.scheduler_skipped,
    stream.sent_samples, notify_failures, uint8_t(ads.fault), ads.active || draining, bool(MAKO_BENCH_MEASURED),
    ads_status, observed_edges, min_interval, MAKO_V12_SPI_HZ};
  uint8_t b[v12::STATUS_BYTES]; v12::encode_status(b, s); status_chr.write(b, sizeof b);
}
static void fail(v12::Fault f, bool drain = true) {
  const v12::Fault why = ads.fault == v12::Fault::None ? f : ads.fault;
  ads.stop(why); // 保留首个故障，停止命令不能把失败洗成成功。
  draining = drain && stream.count != 0;
  if (draining) drain_start = v12::timer_us(2);
  status_update();
}
static void ble_event(ble_evt_t *e) {
  const uint16_t h = e->evt.common_evt.conn_handle;
  if (e->header.evt_id == BLE_GAP_EVT_CONNECTED) { link_handle = h; link_mtu = 23; ++link_epoch; }
  else if (e->header.evt_id == BLE_GAP_EVT_DISCONNECTED) { link_handle = BLE_CONN_HANDLE_INVALID; link_mtu = 23; ++link_epoch; }
  else if (h == link_handle && (e->header.evt_id == BLE_GATTS_EVT_EXCHANGE_MTU_REQUEST || e->header.evt_id == BLE_GATTC_EVT_EXCHANGE_MTU_RSP)) {
    BLEConnection *c = Bluefruit.Connection(h); if (c) link_mtu = c->getMtu();
  }
}
static void control_write(uint16_t h, BLECharacteristic *, uint8_t *p, uint16_t n) {
  if (h != link_handle || n != 4) return;
  uint8_t mode = 0;
  if (!memcmp(p, "STOP", 4)) mode = 4;
  else if (!memcmp(p, "TST1", 4)) mode = 1;
  else if (!memcmp(p, "SHT1", 4)) mode = 2;
  else mode = 7; // 外部输入/IMU/未知命令拒绝，并停止已有采集。
  request_epoch = link_epoch; requested = mode;
}
static void poll_frame() {
  const uint32_t t0 = v12::timer_us(2);
  if (uint32_t(t0 - (have_frame ? last_observed : started_us)) >
      (have_frame ? 2000u : dout::FIRST_TIMEOUT_US)) { fail(v12::Fault::Timeout); return; }
  const bool hit = (port()->LATCH & mask()) != 0;
  const bool high = level();
  if (!baseline) {
    // 初始不接受已有高电平：必须先确认低，再等一次新的高→低。
    port()->LATCH = mask();
    if (!high) { low_before = t0; baseline = true; }
    if (uint32_t(v12::timer_us(2) - started_us) > dout::FIRST_TIMEOUT_US) fail(v12::Fault::Timeout);
    return;
  }
  if (!dout::window_ok(low_before, v12::timer_us(2))) { fail(v12::Fault::Overrun); return; }
  if (!saw_high && !hit && !high) { low_before = t0; }
  if (hit || high) saw_high = true;
  if (!saw_high || high) return;
  const uint32_t edge = v12::timer_us(2); // 观察时刻，不冒充真实DRDY时刻。
  if (!dout::interval_ok(have_frame, last_observed, edge)) { fail(v12::Fault::Overrun); return; }
  if (!start_session_valid()) { fail(v12::Fault::Cancelled); return; }
  // 在传输前和传输后都检查整个不确定窗口；BLE抢占期间不能继续猜样本。
  if (!dout::window_ok(low_before, v12::timer_us(2))) { fail(v12::Fault::Overrun); return; }
  sense(false); armed = false; // SPI数据位不能进入下一帧的事件锁存。
  static uint8_t zeros[27]; // EasyDMA发送缓冲必须在RAM，不能const。
  uint8_t frame[27]; SPI.transfer(zeros, frame, sizeof frame);
  const uint32_t rearm_before = v12::timer_us(2);
  sense(true); armed = true;
  const bool quiet = !level();
  const uint32_t done = v12::timer_us(2);
  if (!quiet || !dout::window_ok(low_before, done)) { fail(v12::Fault::Overrun); return; }
  low_before = rearm_before; baseline = true; saw_high = false;
  if (!start_session_valid() || digitalRead(D5) != LOW) { fail(v12::Fault::Cancelled); return; }
  int32_t raw[8];
  if (!v12::Ads1298::decode(frame, 27, raw, &ads_status)) { fail(v12::Fault::Frame); return; }
  if (stream.count == V12_STREAM_RING) { ++stream.ring_dropped; fail(v12::Fault::Overrun); return; }
  const uint32_t interval = edge - last_observed;
  if (have_frame && interval < min_interval) min_interval = interval;
  ++observed_edges; last_observed = edge; have_frame = true;
  const uint64_t now = v12::clock_us(); uint64_t stamp = (now & ~UINT64_C(0xffffffff)) | edge;
  if (stamp > now) stamp -= UINT64_C(1) << 32;
  const unsigned slot = (stream.head + stream.count) % V12_STREAM_RING;
  if (v12_stream_push(&stream, raw, stamp) != V12_STREAM_OK) { fail(v12::Fault::Frame); return; }
  memcpy(stream.ring[slot].frame, frame, 27);
}
void setup() {
  const uint8_t outputs[] = {D0, D1, D2, D4, D7, D8, D10};
  for (uint8_t p : outputs) { digitalWrite(p, LOW); pinMode(p, OUTPUT); }
  pinMode(D5, INPUT); pinMode(D6, INPUT); pinMode(D9, INPUT);
  analogReadResolution(12); analogReference(AR_INTERNAL); v12::timebase_begin();
  if (v12_stream_init(&stream, MAKO_V12_FS)) return;
  Bluefruit.configUuid128Count(5); Bluefruit.configPrphBandwidth(BANDWIDTH_MAX); Bluefruit.begin(1, 0);
  Bluefruit.setName("MAKO-R01-DOUT-2K"); Bluefruit.Periph.setConnInterval(6, 12); Bluefruit.setEventCallback(ble_event);
  service.begin(); data_chr.setProperties(CHR_PROPS_NOTIFY); data_chr.setPermission(SECMODE_OPEN, SECMODE_NO_ACCESS);
  data_chr.setMaxLen(V12_STREAM_PACKET); data_chr.begin();
  meta_chr.setProperties(CHR_PROPS_READ); meta_chr.setPermission(SECMODE_OPEN, SECMODE_NO_ACCESS); meta_chr.setMaxLen(512); meta_chr.begin();
  char meta[512];
  const int n = snprintf(meta, sizeof meta,
    "{\"profile\":\"F05_ADS_CANDIDATE\",\"build_id\":\"%s\",\"fs_Hz\":2000,\"spi_Hz\":2000000,\"channels\":8,\"protocol\":1,\"bench_measured\":true,\"bench_basis\":\"%s\",\"off_body_only\":true,\"drdy_source\":\"dout_latch\",\"inferred_samples\":0,\"time\":\"packet_first_observation_then_nominal\",\"sequence\":\"observed_frames\",\"imu_enabled\":false,\"clock_source\":\"TIMER2_1MHz\",\"min_period_assumed_us\":450}",
    MAKO_V12_BUILD_ID, MAKO_BENCH_BASIS);
  if (n <= 0 || n >= int(sizeof meta) || !meta_chr.write(meta)) { ads.stop(v12::Fault::Argument); return; }
  status_chr.setProperties(CHR_PROPS_READ); status_chr.setPermission(SECMODE_OPEN, SECMODE_NO_ACCESS);
  status_chr.setFixedLen(v12::STATUS_BYTES); status_chr.begin();
  control_chr.setProperties(CHR_PROPS_WRITE); control_chr.setPermission(SECMODE_NO_ACCESS, SECMODE_OPEN);
  control_chr.setMaxLen(4); control_chr.setWriteCallback(control_write, false); control_chr.begin(); status_update();
  Bluefruit.Advertising.addFlags(BLE_GAP_ADV_FLAGS_LE_ONLY_GENERAL_DISC_MODE);
  Bluefruit.Advertising.addService(service); Bluefruit.ScanResponse.addName();
  Bluefruit.Advertising.restartOnDisconnect(true); Bluefruit.Advertising.setInterval(32, 244); Bluefruit.Advertising.start(0);
}
void loop() {
  vTaskSuspendAll(); const uint32_t epoch = link_epoch; const uint16_t h = link_handle;
  const bool subscribed = h != BLE_CONN_HANDLE_INVALID && data_chr.notifyEnabled(h);
  const uint8_t command = requested; const uint32_t ce = request_epoch; requested = 0; xTaskResumeAll();
  if (epoch != observed_epoch) { observed_epoch = epoch; ads.stop(); draining = false; v12_stream_init(&stream, MAKO_V12_FS); notify_failures = 0; }
  if (command && ce == epoch) {
    const v12::Fault previous_fault = ads.fault;
    ads.stop(command == 4 ? previous_fault : v12::Fault::None); draining = false;
    if (command == 4) { draining = stream.count != 0; drain_start = v12::timer_us(2); }
    else if ((command == 1 || command == 2) && subscribed && !usb_present()) {
      v12_stream_restart(&stream, MAKO_V12_FS); arm_epoch = epoch; arm_handle = h;
      const v12::BenchProof proof = {bool(MAKO_BENCH_MEASURED), MAKO_BENCH_POR_US, MAKO_BENCH_REFERENCE_US};
      if (ads.start(MAKO_V12_FS, v12::Input(command), proof)) {
        if (!start_session_valid()) fail(v12::Fault::Cancelled);
        else { board.cs(false); started_us = v12::timer_us(2); sense(true); armed = true;
          baseline = saw_high = have_frame = false; sd_ble_gattc_exchange_mtu_request(h, 247); }
      }
    } else ads.stop(v12::Fault::Argument);
    status_update();
  }
  if (usb_present() || !subscribed || h != arm_handle || epoch != arm_epoch) {
    if (ads.active || draining) { ads.stop(v12::Fault::Cancelled); draining = false; status_update(); }
  }
  if (ads.active) {
    if (digitalRead(D5) != LOW) fail(v12::Fault::Rails);
    else poll_frame();
  }
  // 聚合8帧再通知，避免每帧单独notify耗尽BLE队列；STOP时发完尾包后才报告inactive。
  if ((ads.active || draining) && subscribed && (stream.count >= V12_MAX_FRAMES || stream.pending_len || draining)) {
    vTaskSuspendAll();
    if (epoch == link_epoch && h == link_handle && requested == 0 && data_chr.notifyEnabled(h)) {
      const uint8_t *b; size_t len;
      if (v12_stream_peek(&stream, link_mtu, &b, &len) == V12_STREAM_OK) {
        uint16_t sent = uint16_t(len); ble_gatts_hvx_params_t params = {};
        params.handle = data_chr.handles().value_handle; params.type = BLE_GATT_HVX_NOTIFICATION;
        params.p_len = &sent; params.p_data = const_cast<uint8_t *>(b);
        const uint32_t rc = sd_ble_gatts_hvx(h, &params);
        if (rc == NRF_SUCCESS && sent == len) v12_stream_commit(&stream);
        else { ++notify_failures; if (rc == NRF_SUCCESS) sd_ble_gap_disconnect(h, BLE_HCI_REMOTE_USER_TERMINATED_CONNECTION); }
      }
    }
    xTaskResumeAll();
  }
  if (draining && !stream.count) { draining = false; status_update(); }
  if (draining && uint32_t(v12::timer_us(2) - drain_start) > 1000000u) fail(v12::Fault::Overrun, false);
  const uint32_t now = v12::timer_us(2);
  // 状态写入也算采集黑窗；下一轮guard覆盖它，不能悄悄忽略BLE抢占。
  if (uint32_t(now - next_status) < 0x80000000u) { status_update(); next_status = now + 1000000u; }
  yield();
}

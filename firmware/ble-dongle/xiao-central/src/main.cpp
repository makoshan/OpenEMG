// 蓝牙接收器：XIAO nRF52840 当中心（主机），连 MAKO-CH585-TPUT，主动定连接间隔 / 2M PHY / DLE / MTU 247。
// 收到的通知原样加 8 字节帧头经 USB CDC 送给 Mac；Mac 发来的命令转成 GATT 读写。只用开发板，不接 AFE，不上人体。
//
// 设备→电脑帧：A5 | kind u8 | len u16 LE | t_us u32 LE（TIMER2 1 MHz，收到通知的时刻）| payload
//   kind 2 = 数据特征通知，6 = IMU 特征通知（同 UUID 末字节），0x10 = 文本日志，0x11 = 链路信息，
//   0x80|op = 命令应答（payload 首字节 0 成功 / 非 0 失败，后跟数据），0x7F = USB 带宽测试填充
// 电脑→设备帧：A5 | op u8 | len u16 LE | payload
//   'W' 写控制特征（带应答），'R' 读特征（payload 1 字节：3 元数据 / 4 状态），'I' 设连接间隔（u16，1.25 ms 单位），
//   'Q' 立刻回链路信息，'B' USB 带宽测试（u16 秒，期间不转发通知），'D' 断开当前连接（之后自动重扫重连）
#include <Arduino.h>
#include <bluefruit.h>
#include <v12_build_id.h>
#include "timebase_board.h"

#define UUID(n) "7b24c101-3948-4f03-9d11-12bb9d0000" n
static BLEClientService service(UUID("01"));
static BLEClientCharacteristic data_chr(UUID("02")), meta_chr(UUID("03")), status_chr(UUID("04")),
    control_chr(UUID("05")), imu_chr(UUID("06"));
// 默认只连吞吐测试固件；真 F05 用同一服务 UUID，按名字挡掉。dongle_r01 档改连 R01（F05 蓝牙版，没开 IMU）
#ifndef DONGLE_TARGET
#define DONGLE_TARGET "MAKO-CH585-TPUT"
#endif
static const char NAME[] = DONGLE_TARGET;

static volatile uint16_t conn = BLE_CONN_HANDLE_INVALID;
static volatile bool ready = false;              // 已发现服务并订阅
static uint16_t want_ci = 6;                     // 7.5 ms；外设 1 s 后会请求 15–30 ms，Bluefruit 默认照收，主循环再改回来
static uint32_t last_param_req = 0;
static uint8_t tries[3];

// BLE 回调任务（on_notify）与主循环应答/链路帧（send_now）统一经 vTaskSuspendAll 串行入环，
// 由唯一消费者 drain() 分片写入 TinyUSB 256B CDC FIFO，杜绝半帧插队撕裂与 >256B 长 META 截断。
static const uint32_t RING = 32768;  // 16CH 2 kHz 约 120 KB/s，够顶 >0.25 s USB 卡顿
static uint8_t ring[RING];
static volatile uint32_t head = 0, tail = 0;
static uint32_t pkt_end = 0;  // drain() 当前在发帧的帧尾偏移，用于超时丢弃积压时对齐整帧边界防半帧撕裂
static volatile uint32_t ring_drops = 0, notifies = 0, ring_peak = 0;
static volatile uint32_t svc_reports = 0, name_reports = 0, connects = 0, discover_fail = 0;
static void drain();

static void put_frame(uint8_t kind, uint32_t t, const uint8_t *p, uint16_t len) {
  vTaskSuspendAll();
  uint32_t need = 8u + len, h = head, used = h - tail;
  if (RING - used < need) { ring_drops++; xTaskResumeAll(); return; }  // 满了丢整帧，电脑据序号缺口和 ring_drops 都能看见
  uint8_t hdr[8] = {0xA5, kind, uint8_t(len), uint8_t(len >> 8), uint8_t(t), uint8_t(t >> 8), uint8_t(t >> 16), uint8_t(t >> 24)};
  for (uint32_t i = 0; i < 8; i++) ring[(h + i) % RING] = hdr[i];
  for (uint32_t i = 0; i < len; i++) ring[(h + 8 + i) % RING] = p[i];
  __DMB();
  head = h + need;
  if (head - tail > ring_peak) ring_peak = head - tail;
  xTaskResumeAll();
}

static void on_notify(BLEClientCharacteristic *chr, uint8_t *data, uint16_t len) {
  notifies++;
  put_frame(chr == &imu_chr ? 6 : 2, v12::timer_us(0), data, len);
}

static void send_now(uint8_t kind, const void *p, uint16_t len) {
  put_frame(kind, v12::timer_us(1), (const uint8_t *)p, len);
  drain();
}

static void logf(const char *fmt, ...) {
  char s[160];
  va_list ap; va_start(ap, fmt); int n = vsnprintf(s, sizeof s, fmt, ap); va_end(ap);
  send_now(0x10, s, n < 0 ? 0 : (n < (int)sizeof s ? n : sizeof s - 1));
}

static void send_link() {
  BLEConnection *c = conn != BLE_CONN_HANDLE_INVALID ? Bluefruit.Connection(conn) : nullptr;
  uint8_t b[28] = {0};
  b[0] = ready;
  uint16_t ci = c ? c->getConnectionInterval() : 0, mtu = c ? c->getMtu() : 0, dl = c ? c->getDataLength() : 0;
  uint8_t phy = c ? c->getPHY() : 0;
  uint32_t rd = ring_drops, nt = notifies, pk = ring_peak;
  memcpy(b + 1, &ci, 2); b[3] = phy; memcpy(b + 4, &mtu, 2); memcpy(b + 6, &dl, 2); memcpy(b + 8, &want_ci, 2);
  uint32_t cn = connects;  // 连上次数：电脑据此发现测量中断开又自动重连，不拼接
  memcpy(b + 10, &rd, 4); memcpy(b + 14, &nt, 4); memcpy(b + 18, &pk, 4); memcpy(b + 22, &cn, 4);
  send_now(0x11, b, 26);
}

static char last_name[32];  // 带 F05 服务 UUID 的广播数，排查「没连上」是没扫到还是名字不对
static void scan_cb(ble_gap_evt_adv_report_t *r) {
  char name[32] = {0};
  if (Bluefruit.Scanner.checkReportForUuid(r, service.uuid)) svc_reports++;
  if (Bluefruit.Scanner.parseReportByType(r, BLE_GAP_AD_TYPE_COMPLETE_LOCAL_NAME, (uint8_t *)name, sizeof name - 1)) {
    name_reports++;
    if (!strncmp(name, "MAKO", 4) || !strncmp(name, "YUANLI", 6)) memcpy(last_name, name, sizeof last_name);
  }
  if (!strcmp(name, NAME)) {
    connects++;
    Bluefruit.Central.connect(r);
  } else {
    Bluefruit.Scanner.resume();
  }
}

static void connect_cb(uint16_t h) {
  conn = h;
  // 先发现服务：MTU 交换和发现都是 GATT 客户端过程，同时发会 BUSY。PHY / DLE / MTU / 间隔交给主循环逐项补
  if (!service.discover(h) || !data_chr.discover() || !meta_chr.discover() ||
#ifndef DONGLE_NO_CTRL  // xiao-synth 只有数据和元数据特征
      !status_chr.discover() || !control_chr.discover() ||
#endif
      !data_chr.enableNotify()) {
    discover_fail++;
    Bluefruit.disconnect(h);
    return;
  }
  // IMU 特征可选：F05 不开 IMU 时没有它，不能因此断开（CH585 吞吐固件有就照常订阅）
  if (imu_chr.discover()) imu_chr.enableNotify();
  memset(tries, 0, sizeof tries);
  ready = true;
}

static volatile uint8_t last_reason = 0;
// DLE 生效值（SoftDevice 事件里给的四个数）：rx 那一半就是外设实际肯发多长、多久的链路包
static volatile uint16_t dle[4];
static volatile uint32_t dle_seq = 0;
static void ble_evt(ble_evt_t *e) {
  if (e->header.evt_id == BLE_GAP_EVT_DATA_LENGTH_UPDATE) {
    const ble_gap_data_length_params_t &d = e->evt.gap_evt.params.data_length_update.effective_params;
    dle[0] = d.max_tx_octets; dle[1] = d.max_tx_time_us; dle[2] = d.max_rx_octets; dle[3] = d.max_rx_time_us;
    dle_seq++;
  }
}
static void disconnect_cb(uint16_t h, uint8_t reason) {
  (void)h;
  ready = false;
  conn = BLE_CONN_HANDLE_INVALID;
  last_reason = reason;  // 不在这里写环形缓冲（回调任务不是唯一生产者），主循环发日志
}

void setup() {
  v12::timebase_begin();
  Serial.begin(115200);
  Bluefruit.configUuid128Count(8);
  // MTU 247；事件长度 24×1.25 ms，比任何测试间隔都长，让一个连接事件能收满（开着事件扩展）
#ifndef DONGLE_EVT_LEN
#define DONGLE_EVT_LEN 24  // 4k 瓶颈实验可改：6 = 7.5 ms
#endif
  Bluefruit.configCentralConn(247, DONGLE_EVT_LEN, 3, BLE_GATTC_WRITE_CMD_TX_QUEUE_SIZE_DEFAULT);
  Bluefruit.begin(0, 1);
#ifdef DONGLE_NO_EXT  // 4k 瓶颈实验：关掉连接事件扩展，看中心是不是在提前收事件
  ble_opt_t opt = {};
  opt.common_opt.conn_evt_ext.enable = 0;
  sd_ble_opt_set(BLE_COMMON_OPT_CONN_EVT_EXT, &opt);
#endif
  sd_clock_hfclk_request();  // TIMER2 时间戳跟外部 32 MHz 晶振走，不落到内部 RC
  Bluefruit.setName("MAKO-DONGLE");
  Bluefruit.setEventCallback(ble_evt);
  Bluefruit.Central.setConnInterval(want_ci, want_ci);
  service.begin();
  BLEClientCharacteristic *chrs[] = {&data_chr, &meta_chr, &status_chr, &control_chr, &imu_chr};
  for (BLEClientCharacteristic *c : chrs) c->begin();
  data_chr.setNotifyCallback(on_notify, false);  // false：在 BLE 任务里直接回调，不另起回调任务
  imu_chr.setNotifyCallback(on_notify, false);
  Bluefruit.Central.setConnectCallback(connect_cb);
  Bluefruit.Central.setDisconnectCallback(disconnect_cb);
  Bluefruit.Scanner.setRxCallback(scan_cb);
  Bluefruit.Scanner.restartOnDisconnect(true);
  Bluefruit.Scanner.useActiveScan(true);  // 名字在扫描应答里
  Bluefruit.Scanner.setInterval(160, 80);
  Bluefruit.Scanner.start(0);
}

static void drain() {
  uint32_t t = tail, h = head;
  while (t != h) {
    if (t == pkt_end) {
      uint16_t plen = uint16_t(ring[(t + 2) % RING]) | (uint16_t(ring[(t + 3) % RING]) << 8);
      pkt_end = t + 8u + plen;
    }
    uint32_t step = min(h - t, pkt_end - t);  // 模 2^32 无符号差值比较，跨 0xFFFFFFFF->0 回绕不失步
    uint32_t off = t % RING, n = min(step, RING - off);
    size_t w = Serial.write(ring + off, n);
    if (!w) break;
    t += w;
    __DMB();
    tail = t;
  }
}

static void bench(uint16_t seconds) {
  static uint8_t fill[240];
  for (unsigned i = 0; i < sizeof fill; i++) fill[i] = i;
  uint32_t end = millis() + seconds * 1000u, frames = 0;
  bool aborted = false;
  while ((int32_t)(millis() - end) < 0) {
    if (!Serial) { aborted = true; break; }
    if (RING - (head - tail) >= 8u + sizeof(fill) + 32u) {
      put_frame(0x7F, v12::timer_us(1), fill, sizeof fill);
      frames++;
    }
    drain();
    yield();
  }
  // 收尾排空设 200 ms 滑动有进展看门狗：主机持续读取时完整排空，主机停读或拔线时按整帧边界截断积压填充帧，绝不卡死主循环或撕裂半帧
  uint32_t prev_tail = tail, stall_deadline = millis() + 200u;
  while (tail != head) {
    if (!Serial) { aborted = true; break; }
    drain();
    uint32_t cur_tail = tail;
    if (cur_tail != prev_tail) {
      prev_tail = cur_tail;
      stall_deadline = millis() + 200u;
    } else if ((int32_t)(millis() - stall_deadline) >= 0) {
      aborted = true;
      break;
    }
    yield();
  }
  if (aborted) {
    vTaskSuspendAll();
    if (!Serial) {
      tail = head;
      pkt_end = head;
    } else {
      head = (pkt_end - tail <= head - tail) ? pkt_end : tail;
    }
    xTaskResumeAll();
  }
  uint8_t r[5] = { uint8_t(aborted ? 2 : 0) };
  memcpy(r + 1, &frames, 4);
  if (Serial) send_now(0x80 | 'B', r, 5);
}

static uint8_t cmd[300];
static uint16_t cmd_len = 0;

static void handle(uint8_t op, const uint8_t *p, uint16_t len) {
  uint8_t r[600];  // F05 元数据 JSON 超过 260 字节（长读），260 会截断
  r[0] = 1;
  uint16_t n = 1;
  if (op == 'W' && ready) {
    r[0] = control_chr.write_resp(p, len) == len ? 0 : 1;
  } else if (op == 'R' && ready && len == 1 && (p[0] == 3 || p[0] == 4)) {
    uint16_t got = (p[0] == 3 ? meta_chr : status_chr).read(r + 1, sizeof r - 1);
    if (got) { r[0] = 0; n += got; }
  } else if (op == 'I' && len == 2) {
    memcpy(&want_ci, p, 2);
    Bluefruit.Central.setConnInterval(want_ci, want_ci);
    last_param_req = 0;
    r[0] = 0;
  } else if (op == 'D') {
    // 每次采集前断开重连：F05 只在新连接时从头开始数据流，同一连接上第二次采集发的是“重新配置”边界，新开的主机会话会拒收
    if (conn != BLE_CONN_HANDLE_INVALID) Bluefruit.disconnect(conn);
    r[0] = 0;
  } else if (op == 'Q') {
    send_link();
    r[0] = 0;
  } else if (op == 'B' && len == 2) {
    uint16_t s; memcpy(&s, p, 2);
    bench(s);
    return;
  }
  send_now(0x80 | op, r, n);
}

static void poll_serial() {
  while (Serial.available()) {
    int c = Serial.read();
    if (cmd_len == 0 && c != 0xA5) continue;  // 帧外字节丢弃，靠 A5 重新对齐
    cmd[cmd_len++] = c;
    if (cmd_len >= 4) {
      uint16_t len = cmd[2] | cmd[3] << 8;
      if (len > sizeof cmd - 4) { cmd_len = 0; continue; }
      if (cmd_len == 4u + len) { handle(cmd[1], cmd + 4, len); cmd_len = 0; }
    }
  }
}

void loop() {
  drain();
  poll_serial();
  // 中心定链路参数：哪项不到位就每 0.5 s 补请求一项（同时发多项会撞 BUSY）。
  // 外设连上 1 s 后会自己请求 15–30 ms，Bluefruit 照收，这里再改回 want_ci。
  BLEConnection *c = ready && conn != BLE_CONN_HANDLE_INVALID ? Bluefruit.Connection(conn) : nullptr;
  if (c && c->connected() && millis() - last_param_req > 500) {
    last_param_req = millis();
    // PHY / DLE / MTU 各最多试 4 次（对端不支持就别卡住后面的间隔），实际值照报在链路信息里
    if (c->getPHY() != BLE_GAP_PHY_2MBPS && tries[0] < 4) { tries[0]++; c->requestPHY(BLE_GAP_PHY_2MBPS); }
    else if (c->getDataLength() < 251 && tries[1] < 4) { tries[1]++; c->requestDataLengthUpdate(); }
#ifndef DONGLE_PEER_MTU
    else if (c->getMtu() < 247 && tries[2] < 4) { tries[2]++; c->requestMtuExchange(247); }
#endif  // R01 开采时自己发起 MTU；两边都发起时 R01 发通知一直返回 8（INVALID_STATE），同 c6-central（2026-10-29 实测故障 9）
    else if (c->getConnectionInterval() != want_ci) c->requestConnectionParameter(want_ci);
  }
  static uint32_t last_link = 0, n_link = 0;
  if (millis() - last_link > 1000) {
    last_link = millis(); send_link();
    // 串口没开时日志会丢，DLE 生效值每 5 s 重报一次
    if (ready && ++n_link % 5 == 0 && dle_seq) logf("dle tx %u B/%u us rx %u B/%u us", dle[0], dle[1], dle[2], dle[3]);
    if (!ready && ++n_link % 5 == 0) logf("scanning: svc adverts %lu, named reports %lu, last MAKO name '%s', connects %lu, discover fail %lu",
                                              (unsigned long)svc_reports, (unsigned long)name_reports, last_name,
                                              (unsigned long)connects, (unsigned long)discover_fail);
  }
  static bool said = false, was_ready = false;
  if (!said && Serial) { said = true; logf("dongle build %s", MAKO_V12_BUILD_ID); }
  if (ready != was_ready) { was_ready = ready; ready ? logf("connected %s", NAME) : logf("disconnected reason 0x%02x", last_reason); }
  yield();
}

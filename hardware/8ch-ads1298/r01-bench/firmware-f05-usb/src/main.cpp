// F05-USB：离体台架用，USB 串口完全取代蓝牙（2026-10-21 Mako 定）。
// ADS 驱动、上电/复位/解锁门、电源粗筛全部复用 firmware-f05 的 ads1298.cpp；这里只换“谁发命令、数据往哪送”。
// 只在 J1-12（VBUS 互锁线）拔掉时才能打开模拟电源：互锁失效，只许离体、J3 空、不接电极、不上人体。
#include <Arduino.h>
#include <Adafruit_TinyUSB.h>
#include <SPI.h>
#include "ads1298.h"
#include "capture_guard.h"
#include "bench_release.h"
#include "usb_frame.h"
#include "timebase_board.h"  // F05 的 TIMER2 1µs 时基（钉哈希借用）；本核自带的微秒函数只有约 1ms 分辨率，不能用
#include <v12_build_id.h>

#if defined(MAKO_V12_AFE_ENABLED) && MAKO_V12_AFE_ENABLED != 0
#error "只使用 bench_release.h 的门，不允许绕过"
#endif
static_assert(PIN_SPI_SCK == 8 && PIN_SPI_MISO == 9 && PIN_SPI_MOSI == 10, "SPI 板包映射变化");
#if MAKO_V12_FS != 2000 && MAKO_V12_FS != 4000
#error "采样率只允许2000或4000"
#endif
#ifndef MAKO_V12_SPI_HZ
#define MAKO_V12_SPI_HZ 1000000
#endif
#if MAKO_V12_SPI_HZ != 1000000 && MAKO_V12_SPI_HZ != 2000000 && MAKO_V12_SPI_HZ != 4000000
#error "SPI 只允许 1、2 或 4 MHz（4 MHz 只给 4kSPS 用：杜邦线台架，信号完整性未测）"
#endif

static volatile uint32_t edge_count = 0, edge_us = 0;
static uint32_t used_edge = 0, last_edge_us = 0, capture_started = 0, seq = 0, usb_full = 0, ads_status = 0;
static bool have_edge = false, stop_req = false;
static uint8_t last_oe_n = 0xFF;      // 最近一次电源粗筛看到的 D5；0xFF=还没查过
static uint16_t last_avdd_mv = 0xFFFF; // 最近一次电源粗筛读到的 AVDD（mV）
static uint8_t start_req = 0;
static char line[16];
static uint8_t line_len = 0;
static bool meta_req = false;
// PWR1：只开模拟电源（ADS 保持 PWDN/RESET 低），30 秒后或 STOP/断开时关，用来量 AVDD/TP9；不采样
static bool pwr_req = false, pwr_on = false, diag_req = false, blind = false, hold_req = false, holding = false;
static uint32_t hold_until = 0;
static uint32_t pwr_until = 0;

static void on_drdy() { edge_us = v12::timer_us(0); ++edge_count; }
// DRDY_MODE=3：DOUT 下降沿走硬件中断（CS 常低，D9 挂 GPIOTE）。读帧期间 MISO 在传数据，那些沿不计。
// 给蓝牙版用：主循环要跑无线，不能卡在轮询里；中断时间戳也不怕主循环被抢。
static volatile bool dout_isr = false, reading_frame = false;
static void on_dout_fall() { if (reading_frame) return; edge_us = v12::timer_us(0); ++edge_count; }
// R01 实测：DRDY 专用线（U1 第47脚→U3→D6）一直为低，原因未定；但 CS 拉低且不给时钟时，
// ADS 的 DOUT 会跟着 DRDY 变化（2026-10-22 盲读诊断：20ms 内 MISO 上下各 40 次 = 2kHz）。
// 所以采样时 CS 常低，主循环轮询 MISO(D9) 的下降沿代替 DRDY 中断；判停规则不变。
// DRDY_MODE：0=启动自检（默认）、1=强制 DOUT 轮询、2=强制 DRDY 脚、3=DOUT 下降沿中断。自检见 select_drdy_source()。
#ifndef DRDY_MODE
#define DRDY_MODE 0
#endif
#if DRDY_MODE != 0 && DRDY_MODE != 1 && DRDY_MODE != 2 && DRDY_MODE != 3
#error "DRDY_MODE 只允许 0/1/2/3"
#endif
static bool dout_mode = DRDY_MODE != 2;  // 本次采集用 DOUT 代 DRDY；自检后定
static int last_dout = 1;
static uint32_t edge_log[8]; static uint32_t edge_log_n = 0;  // 诊断：本次采集前 8 个 DRDY 时刻
static uint32_t last_poll_us = 0, max_gap_us = 0, gap_at_sample = 0;
static uint32_t inferred_edges = 0; static uint8_t inferred_run = 0;  // 推算出的沿：总数、连续次数
// 诊断 diag:4：每帧读完重新拉低 CS 时 DOUT 的电平、从沿到读完并发出的耗时（rd_max）、上升沿离上一帧多久、高电平宽度；推算帧前有没有见过上升
struct DoutStats { uint32_t relow_hi, relow_lo, rd_max, rise_min, rise_max, hiw_min, hiw_max, inf_rise, inf_norise, rise_us, d6_hits; };
static DoutStats ds;
static void ds_reset() { ds = {}; ds.rise_min = ds.hiw_min = 0xFFFFFFFFu; }
static bool edge_inferred = false, late_overrun = false;  // 当前这一沿是推算的：样本帧序号最高位置 1，主机逐帧可见
// max_gap_us：上一个沿（或推算沿）到下一次进入轮询的最长间隔，超过 1.4 个周期就说明可能漏帧
// 新帧前 DOUT 有一个高脉冲（上一帧后 223–503µs 出现，宽度最窄不到 1µs），先见高、再见低就记一次“DRDY”。
// 在这里紧凑轮询，最多等 1.5 个采样周期，等不到就交给超时判停。
// 漏沿的两个来源都已去掉（2026-10-22 diag:4）：F05 驱动逐字节读帧加 CS 翻转太慢（改 dout_read 一次 DMA），
// 窄脉冲轮询看不到（改 GPIO 锁存）。之后 2 分钟 240036 帧推算 0。推算逻辑留作兜底：上一帧后 1.2 个周期仍没看到沿、
// 且 DOUT 已是低，就按“上一帧+1 个周期”记时间戳、序号最高位标推算；连续 20 次推算就停机，不盲跑。
// MISO(D9) 开 SENSE=High + LATCH：脚上出现过高电平（哪怕不到 1µs）硬件都会记住，轮询再慢也不漏高脉冲
static NRF_GPIO_Type *dout_port() { return g_ADigitalPinMap[D9] >= 32 ? NRF_P1 : NRF_P0; }
static uint32_t dout_mask() { return 1u << (g_ADigitalPinMap[D9] & 31); }
static void dout_latch(bool on) {
  NRF_GPIO_Type *const port = dout_port(); volatile uint32_t &cnf = port->PIN_CNF[g_ADigitalPinMap[D9] & 31];
  cnf = (cnf & ~GPIO_PIN_CNF_SENSE_Msk) | ((on ? GPIO_PIN_CNF_SENSE_High : GPIO_PIN_CNF_SENSE_Disabled) << GPIO_PIN_CNF_SENSE_Pos);
  if (on) port->DETECTMODE = GPIO_DETECTMODE_DETECTMODE_LDETECT;  // ponytail: 整个端口改成锁存检测；本固件不用 PORT 唤醒，别处要用时再分开
  port->LATCH = dout_mask();  // 写 1 清除
  // 诊断：D6（DRDY 专用线）也开锁存。DRDY 不被读时只有约 2µs 高脉冲，轮询会漏；锁存到过高电平就计一次（diag:4 d6_hits）
  const uint32_t p6 = g_ADigitalPinMap[D6]; NRF_GPIO_Type *const port6 = p6 >= 32 ? NRF_P1 : NRF_P0;
  volatile uint32_t &cnf6 = port6->PIN_CNF[p6 & 31];
  cnf6 = (cnf6 & ~GPIO_PIN_CNF_SENSE_Msk) | ((on ? GPIO_PIN_CNF_SENSE_High : GPIO_PIN_CNF_SENSE_Disabled) << GPIO_PIN_CNF_SENSE_Pos);
  if (on) port6->DETECTMODE = GPIO_DETECTMODE_DETECTMODE_LDETECT;
  port6->LATCH = 1u << (p6 & 31);
}
static void d6_check() {
  const uint32_t p6 = g_ADigitalPinMap[D6]; NRF_GPIO_Type *const port6 = p6 >= 32 ? NRF_P1 : NRF_P0; const uint32_t m = 1u << (p6 & 31);
  if (port6->LATCH & m) { ++ds.d6_hits; port6->LATCH = m; }
}
static bool infer_ok() { return inferred_run < 20; }  // 只限时间戳误差（0.24µs/帧）；读到的是不是该帧，由下面的 1.4T 上限保证
static void poll_dout_drdy() {
  const uint32_t period = 1000000u / MAKO_V12_FS;
  const uint32_t t0 = v12::timer_us(2), limit = 1500000u / MAKO_V12_FS;
  if (last_poll_us && t0 - last_poll_us > max_gap_us) { max_gap_us = t0 - last_poll_us; gap_at_sample = seq; }
  // 直接读 GPIO 寄存器和锁存：高脉冲最窄不到 1µs（diag:4 实测），digitalRead 轮询会漏；内圈 16 次只读引脚，再看一次时间
  NRF_GPIO_Type *const port = dout_port(); const uint32_t mask = dout_mask();
  while (uint32_t(v12::timer_us(2) - t0) < limit) {
    int lvl = last_dout;
    for (int i = 0; i < 16; ++i) {
    const bool latched = port->LATCH & mask;  // 先读锁存再读电平：锁存为 1、电平为 0 = 高脉冲已经结束
    lvl = (port->IN & mask) ? 1 : 0;
    if (!last_dout && (lvl || latched)) { last_dout = 1; port->LATCH = mask; }
    if (last_dout && !ds.rise_us) { ds.rise_us = v12::timer_us(2); const uint32_t r = ds.rise_us - last_edge_us; if (have_edge) { if (r < ds.rise_min) ds.rise_min = r; if (r > ds.rise_max) ds.rise_max = r; } }
    if (last_dout && !lvl) { edge_us = v12::timer_us(2); if (ds.rise_us) { const uint32_t w = edge_us - ds.rise_us; if (w < ds.hiw_min) ds.hiw_min = w; if (w > ds.hiw_max) ds.hiw_max = w; } ds.rise_us = 0; ++edge_count; edge_inferred = false; edge_log[edge_log_n++ % 8] = edge_us; /* 环形：保留最后 8 个 */ last_dout = lvl; last_poll_us = v12::timer_us(2); inferred_run = 0; return; }
    last_dout = lvl;
    }
    const uint32_t since = uint32_t(v12::timer_us(2) - last_edge_us);
    if (have_edge && !lvl && since > period * 6 / 5) {
      // 超过 1.4 个周期：剩下的时间不够在下一次转换（2T）前读完一帧（约 150–200µs，估算未实测），可能漏帧或读到半新半旧，直接停机
      if (since >= period * 7 / 5) { late_overrun = true; return; }
      if (!infer_ok()) return;  // 连续推算太多：不再补，交给 Overrun/超时停机
      edge_us = last_edge_us + period; ++edge_count; ++inferred_edges; ++inferred_run; edge_inferred = true; ++(ds.rise_us ? ds.inf_rise : ds.inf_norise); ds.rise_us = 0;
      edge_log[edge_log_n++ % 8] = edge_us; last_poll_us = v12::timer_us(2); return;
    }
  }
}

// 诊断：采集中改寄存器（Waavv，十六进制地址+值），标定增益/参考用。只放行芯片内部信号：
// CONFIG2（测试源幅度/频率）和 CHnSET 的 MUX 为 001 短接、011 电源测量、100 温度、101 测试源；外部输入一律拒绝。
static uint8_t reg_q[8][2]; static uint8_t reg_n = 0;
static bool reg_allowed(uint8_t a, uint8_t v) {
  if (a == 0x02) return (v & 0x10) && !(v & 0xC8);  // INT_TEST 必须开着；保留位 7/6/3 不许动
  if (a < 0x05 || a > 0x0C) return false;
  if ((v & 0x08) || (v & 0x70) == 0x70) return false;  // SRB2 会把 INxP 接到外部 SRB2 网；增益 111 是保留值
  const uint8_t mux = v & 0x07;
  return mux == 1 || mux == 3 || mux == 4 || mux == 5;
}
static void queue_reg(const char *hex) {
  char *end; const unsigned long x = strtoul(hex, &end, 16);
  const uint8_t a = uint8_t(x >> 8), v = uint8_t(x);
  if (*end || !reg_allowed(a, v) || reg_n >= 8) return;
  reg_q[reg_n][0] = a; reg_q[reg_n][1] = v; ++reg_n;
}

// 非阻塞读串口命令：TST1/SHT1 开始，STOP 停，META 回元数据。启动等待期间也会被调用，STOP 能打断等待。
static void poll_commands() {
  while (Serial.available()) {
    const char c = char(Serial.read());
    if (c == '\n' || c == '\r') {
      line[line_len] = 0;
      if (!strcmp(line, "STOP")) stop_req = true;
      else if (!strcmp(line, "META")) meta_req = true;
      else if (!strcmp(line, "PWR1")) pwr_req = true;
      else if (!strcmp(line, "DIAG")) diag_req = true;
      else if (!strcmp(line, "BLND")) { start_req = 1; blind = true; }  // 内部测试源启动后盲读，诊断用
      else if (!strcmp(line, "HOLD")) { start_req = 1; hold_req = true; }  // 内部测试源连续盲读 30 秒，给万用表量 DRDY 两端
      else if (!strcmp(line, "TST1")) start_req = 1;
      else if (!strcmp(line, "SHT1")) start_req = 2;
      else if (line[0] == 'W' && strlen(line) == 5) queue_reg(line + 1);
      else if (!strcmp(line, "EXR1")) start_req = 5;  // 与 F05 同名：外部输入+RLD：只接信号发生器做频响/串扰（2026-10-22 Mako 要求）；互锁失效时绝不接人体
      line_len = 0;
    } else if (line_len < sizeof line - 1) line[line_len++] = c;
    else line_len = 0;  // 超长行丢弃，不猜
  }
}

struct BoardHal final : v12::AdsHal {
  bool spi_on = false;
  void power(bool on) override {
    if (on) { SPI.begin(); SPI.beginTransaction(SPISettings(MAKO_V12_SPI_HZ, MSBFIRST, SPI_MODE1)); spi_on = true; digitalWrite(D0, HIGH); }
    else {
      digitalWrite(D0, LOW);
      if (spi_on) { SPI.endTransaction(); SPI.end(); spi_on = false; }
      const uint8_t pins[] = {D8, D10};
      for (uint8_t p : pins) { digitalWrite(p, LOW); pinMode(p, OUTPUT); }
    }
  }
  void pwdn(bool on) override { digitalWrite(D4, on ? HIGH : LOW); }
  void reset(bool on) override { digitalWrite(D2, on ? HIGH : LOW); }
  void clocksel(bool on) override { digitalWrite(D1, on ? HIGH : LOW); }
  void cs(bool on) override { digitalWrite(D7, on ? HIGH : LOW); }
  uint8_t transfer(uint8_t v) override { return SPI.transfer(v); }
  void wait(uint32_t us) override { while (us >= 1000 && session_valid()) { delay(1); us -= 1000; } if (us < 1000 && us) delayMicroseconds(us); }
  // 会话有效 = 串口被主机打开（DTR）且没收到 STOP；与 F05 一样，任何时候失效都会让 start() 断电退出。
  bool session_valid() override { poll_commands(); return bool(Serial) && !stop_req; }
  bool rails_good() override {
    // 与 F05 相同的粗筛：0.6V×6 量程再×板上 1:4 分压
    const float avdd = float(analogRead(D3)) * 14.4f / 4095.0f;
    const bool oe_low = digitalRead(D5) == LOW;
    last_oe_n = oe_low ? 0 : 1; last_avdd_mv = uint16_t(avdd * 1000.0f);  // 只记录诊断，不改判定
    return oe_low && avdd >= 4.6f && avdd <= 5.4f;
  }
  void capture(bool on) override {
    detachInterrupt(digitalPinToInterrupt(D6)); detachInterrupt(digitalPinToInterrupt(D9));  // dout_isr 不在这清：停机后 diag:7 还要报来源
    if (on) { noInterrupts(); edge_count = 0; edge_us = 0; interrupts(); }
    used_edge = 0; last_edge_us = 0; have_edge = false; capture_started = v12::timer_us(2);
  }
} board;
static v12::Ads1298 ads(board);

// DOUT 代 DRDY 时的读帧：一次 DMA 读 27 字节（约 110µs），CS 全程保持低、不翻转。
// F05 驱动逐字节 SPI.transfer 加 CS 翻转要 300–400µs（2026-10-22 diag:4 实测读+发最长 414µs），
// 会错过下一帧前 DOUT 的上升沿（上一帧后 223–503µs 出现），这是推算帧的来源。帧头检查与驱动一致。
// 采集中改寄存器：SDATAC → WREG → RREG 回读 → RDATAC，CS 一直低；每条命令后等 4µs（> 4 tCLK）。回读结果用 diag:5 报。
// 每帧只改一个：逐字节 SPI 慢，一次改 2 个就要 770µs，会触发漏帧停机。
static bool send(const uint8_t *b, size_t n);
// DRDY 自检：先按 DOUT 代 DRDY 开采（CS 常低），同时用 D6 硬件锁存看 DRDY 专用线。
// 读帧会把 DRDY 拉高、新数据再拉低，线通的话 D6 每帧都会锁到高电平。前 40 帧锁到过 → 线通，在帧间切回中断（F05 原路径）；
// 一次没锁到 → 线不通（R01 实测如此），继续 DOUT。不在开头停下来等：4k 下开头空等 5 个周期会让 DOUT 跟丢（实测几帧内停机）。
// 选错的后果是采不到帧、按 Timeout/Overrun 停机，不会读到错帧。结果用 diag:7 报。
static bool drdy_decided = true;
static uint32_t drdy_hits = 0, drdy_seq = 0;  // 判定时记下，停机时随 diag:3/4 一起报：采集中发 JSON 会超 4k 的 250µs 周期（实测第 40 帧停机）
static void report_drdy_source() {
  char json[112]; const int n = snprintf(json, sizeof json, "{\"diag\":7,\"drdy_source\":\"%s\",\"d6_hits\":%lu,\"mode\":%d,\"seq\":%lu,\"decided\":%s}",
    dout_isr ? "dout_isr" : dout_mode ? "dout_mirror" : "drdy_pin", (unsigned long)drdy_hits, DRDY_MODE, (unsigned long)drdy_seq, drdy_decided ? "true" : "false");
  uint8_t out[sizeof json + 6]; if (n > 0 && n < int(sizeof json)) send(out, usbf::encode(usbf::META, reinterpret_cast<const uint8_t *>(json), size_t(n), out));
}
static void use_drdy_pin() {
  board.cs(true); dout_latch(false); dout_mode = false;
  noInterrupts(); edge_count = used_edge; interrupts();  // 中断从这里接着计数
  // have_edge/last_edge_us 保留：切换时若漏掉一个沿，下一沿间隔约 2T，照常按 Overrun 停机（同一个 TIMER2，通道不同可直接比）
  attachInterrupt(digitalPinToInterrupt(D6), on_drdy, FALLING);
}
static void select_drdy_source() {
  drdy_decided = DRDY_MODE != 0;
  drdy_hits = 0; drdy_seq = 0; dout_isr = false;
  if (DRDY_MODE == 2) { dout_mode = true; use_drdy_pin(); return; }
  if (DRDY_MODE == 3) {
    dout_mode = false; board.cs(false); dout_latch(false);
    noInterrupts(); edge_count = used_edge; interrupts();
    dout_isr = true; attachInterrupt(digitalPinToInterrupt(D9), on_dout_fall, FALLING);
    return;
  }
  dout_mode = true; board.cs(false); last_dout = 0; dout_latch(true);  // CS 常低，DOUT 才反映 DRDY；必须先见上升再见下降
}
static void decide_drdy_source() {  // 每读完一帧调用（DOUT 模式）
  if (drdy_decided || seq < 40) return;
  drdy_decided = true; drdy_hits = ds.d6_hits; drdy_seq = seq;
  if (drdy_hits) use_drdy_pin();
}
static void apply_regs() {
  board.transfer(0x11); delayMicroseconds(4);
  {
    const uint8_t a = reg_q[0][0], v = reg_q[0][1];
    board.transfer(0x40 | a); delayMicroseconds(4); board.transfer(0); delayMicroseconds(4); board.transfer(v); delayMicroseconds(4);
    board.transfer(0x20 | a); delayMicroseconds(4); board.transfer(0); delayMicroseconds(4); const uint8_t rb = board.transfer(0); delayMicroseconds(4);
    char json[64]; const int n = snprintf(json, sizeof json, "{\"diag\":5,\"addr\":%u,\"val\":%u,\"read\":%u,\"seq\":%lu}", a, v, rb, (unsigned long)seq);
    uint8_t out[sizeof json + 6]; if (n > 0 && n < int(sizeof json)) send(out, usbf::encode(usbf::META, reinterpret_cast<const uint8_t *>(json), size_t(n), out));
  }
  --reg_n; memmove(reg_q[0], reg_q[1], 2 * reg_n);
  board.transfer(0x10); delayMicroseconds(4);
  dout_port()->LATCH = dout_mask(); last_dout = 0;  // 命令期间 DOUT 的翻转不算沿
  // 改一个寄存器约 540µs，超过一个周期：这里重置帧间隔基准，下一沿不做间隔检查（诊断用，改寄存器前后的帧本来就不连续，diag:5 报了在哪一帧改的）
  have_edge = false; capture_started = v12::timer_us(2);
}

static bool dout_read(uint8_t frame[27]) {
  static uint8_t zeros[27];  // DIN 保持低，216 个时钟；必须在 RAM（EasyDMA 读不了 Flash，const 会被放进 Flash）
  SPI.transfer(zeros, frame, 27);
  if ((frame[0] & 0xF0) != 0xC0) { ads.stop(v12::Fault::Frame); return false; }
  return true;
}

// 绝不阻塞：缓冲不够时，采集中就停机（不丢包冒充正常），不在采就丢掉这一帧状态/元数据。
// （Serial.write 在已连接且缓冲满时会一直 yield 等待，ADS 上电时卡住就没有任何检查了）
static bool send(const uint8_t *b, size_t n) {
  if (size_t(Serial.availableForWrite()) < n) {
    if (ads.active) { ++usb_full; ads.stop(v12::Fault::Overrun); }  // 只统计采集中的缓冲不足
    return false;
  }
  Serial.write(b, n);
  return true;
}

// XIAO 自带电池分压（P0.31，VBAT_ENABLE=P0.14 拉低接通；Seeed 资料为 1M/510k，未实测）。
// P0.14 只拉低、从不拉高：资料提醒拉高时 P0.31 可能直接承受电池电压。
static uint16_t vbat_cache = 0xFFFF;
// 采集中不做 ADC（每次几十到上百 µs，会让 DOUT 代 DRDY 漏沿），直接用上次的值
static uint16_t vbat_mv() {
  if (!ads.active) vbat_cache = uint16_t(float(analogRead(PIN_VBAT)) * 3.6f / 4095.0f * 1510.0f / 510.0f * 1000.0f);
  return vbat_cache;
}

// DIAG：只在模拟电源关着时做。D3/D5 依次读“原样/内部下拉/内部上拉”，用来判断线是否接上、接到哪里；
// nRF52 内部上下拉约 13k（数据手册典型值，未实测）。读完恢复成普通输入。
static void send_diag() {
  if (ads.active || pwr_on) return;
  auto mv = [](uint8_t pin, uint32_t mode) { pinMode(pin, mode); delay(20); const int v = int(float(analogRead(pin)) * 3600.0f / 4095.0f); pinMode(pin, INPUT); return v; };
  auto lv = [](uint8_t pin, uint32_t mode) { pinMode(pin, mode); delay(20); const int v = digitalRead(pin); pinMode(pin, INPUT); return v; };
  const int d3 = mv(D3, INPUT), d3_dn = mv(D3, INPUT_PULLDOWN), d3_up = mv(D3, INPUT_PULLUP);
  const int d5 = lv(D5, INPUT), d5_dn = lv(D5, INPUT_PULLDOWN), d5_up = lv(D5, INPUT_PULLUP);
  // 输出脚接线检查：临时改成内部上拉读电压，再恢复成输出低。按原理图：
  // D0→R24 47k→U7_EN(R25 100k 到地)：接着≈3.0V、悬空≈3.3V；D1/D4 在 XIAO 侧有 10k 下拉(R38/R39)：接着≈1.4V、悬空≈3.3V。
  // D0 上拉期间 U7_EN 约 2V，模拟电源可能短暂打开约 20ms（与 PWR1 同属离体诊断）。
  auto out_pu = [](uint8_t pin) { pinMode(pin, INPUT_PULLUP); delay(20); const int v = int(float(analogRead(pin)) * 3600.0f / 4095.0f); digitalWrite(pin, LOW); pinMode(pin, OUTPUT); return v; };
  const int d1_pu = out_pu(D1), d4_pu = out_pu(D4), d0_pu = out_pu(D0);
  // D6（DRDY）：模拟电源关着时 U3 高阻，线接好应能被内部上/下拉拉动
  const int d6_up = lv(D6, INPUT_PULLUP), d6_dn = lv(D6, INPUT_PULLDOWN);
  // 锁存对照（pinMode 会重写 PIN_CNF、清掉 SENSE，所以先设上下拉再开锁存）：上拉时应锁到 1，下拉时应为 0
  pinMode(D6, INPUT_PULLUP); delay(2); dout_latch(true); ds.d6_hits = 0; delayMicroseconds(10); d6_check(); const int d6_pos = int(ds.d6_hits);
  pinMode(D6, INPUT_PULLDOWN); delay(2); dout_latch(true); ds.d6_hits = 0; delayMicroseconds(10); d6_check(); const int d6_neg = int(ds.d6_hits);
  dout_latch(false); pinMode(D6, INPUT);
  char json[usbf::MAX_PAYLOAD];
  const int n = snprintf(json, sizeof json,
    "{\"diag\":1,\"d3_pin_mV\":%d,\"d3_pulldown_mV\":%d,\"d3_pullup_mV\":%d,\"d5\":%d,\"d5_pulldown\":%d,\"d5_pullup\":%d,\"d0_pullup_mV\":%d,\"d1_pullup_mV\":%d,\"d4_pullup_mV\":%d,\"vbat_mV\":%u,\"xiao_vdd_mV\":%d,\"d5_mV\":%d,\"d6_pullup\":%d,\"d6_pulldown\":%d}",
    d3, d3_dn, d3_up, d5, d5_dn, d5_up, d0_pu, d1_pu, d4_pu, unsigned(vbat_mv()),
    int(float(analogReadVDD()) * 3600.0f / 4095.0f),  // 芯片自身 VDD=XIAO 3V3，经 J1-1 送板上 U12 检测（门限 3.07V）
    mv(D5, INPUT), d6_up, d6_dn);  // D5：OE_N 高电平由 U10 输出，约等于板上 3V3
  if (n <= 0 || n >= int(sizeof json)) return;
  uint8_t out[usbf::MAX_PAYLOAD + 6];
  send(out, usbf::encode(usbf::META, reinterpret_cast<const uint8_t *>(json), size_t(n), out));
  const int n6 = snprintf(json, sizeof json, "{\"diag\":6,\"d6_latch_pullup\":%d,\"d6_latch_pulldown\":%d}", d6_pos, d6_neg);  // 单独一帧：diag:1 已接近负载上限
  send(out, usbf::encode(usbf::META, reinterpret_cast<const uint8_t *>(json), size_t(n6), out));
}

static void report_drdy_source();
static void send_edge_report() {
  dout_latch(false);  // 停机即关锁存检测
  report_drdy_source();
      // 停机时报前几个 DRDY 间隔（µs），用来判断 DOUT 代替 DRDY 的时序对不对
  char json[usbf::MAX_PAYLOAD]; int n = snprintf(json, sizeof json, "{\"diag\":3,\"fault\":%u,\"edges\":%u,\"last_dt_us\":[", unsigned(ads.fault), unsigned(edge_log_n));
  const uint8_t k = edge_log_n < 8 ? edge_log_n : 8;
  for (uint8_t i = 1; i < k && n < 200; ++i) {
    const uint8_t a = uint8_t(edge_log_n - k + i - 1) % 8, b = uint8_t(edge_log_n - k + i) % 8;
    n += snprintf(json + n, sizeof json - n, "%s%lu", i > 1 ? "," : "", (unsigned long)(edge_log[b] - edge_log[a]));
  }
  n += snprintf(json + n, sizeof json - n, "],\"max_gap_us\":%lu,\"gap_at_seq\":%lu,\"inferred_edges\":%lu,\"samples\":%lu}", (unsigned long)max_gap_us, (unsigned long)gap_at_sample, (unsigned long)inferred_edges, (unsigned long)seq);
  if (n > 0 && n < int(sizeof json)) { uint8_t out[usbf::MAX_PAYLOAD + 6]; send(out, usbf::encode(usbf::META, reinterpret_cast<const uint8_t *>(json), size_t(n), out)); }
  n = snprintf(json, sizeof json, "{\"diag\":4,\"relow_hi\":%lu,\"relow_lo\":%lu,\"rd_max_us\":%lu,\"rise_us\":[%lu,%lu],\"hi_width_us\":[%lu,%lu],\"inferred_after_rise\":%lu,\"inferred_no_rise\":%lu,\"d6_hits\":%lu}",
    (unsigned long)ds.relow_hi, (unsigned long)ds.relow_lo, (unsigned long)ds.rd_max, (unsigned long)ds.rise_min, (unsigned long)ds.rise_max,
    (unsigned long)ds.hiw_min, (unsigned long)ds.hiw_max, (unsigned long)ds.inf_rise, (unsigned long)ds.inf_norise, (unsigned long)ds.d6_hits);
  if (n > 0 && n < int(sizeof json)) { uint8_t out[usbf::MAX_PAYLOAD + 6]; send(out, usbf::encode(usbf::META, reinterpret_cast<const uint8_t *>(json), size_t(n), out)); }
}

static void send_status() {
  if (!ads.active && !pwr_on) board.rails_good();  // 模拟电源关着时也刷新 D3 读数：线好应≈0V，悬空才会读出 1V 以上
  uint8_t out[usbf::STATUS_PAYLOAD + 6];
  noInterrupts(); const uint32_t edges = edge_count; interrupts();
  send(out, usbf::status(uint8_t(ads.fault), ads.active, bool(MAKO_BENCH_MEASURED), edges, seq, usb_full, out, last_oe_n, last_avdd_mv, vbat_mv()));
}

static void send_meta() {
  char json[usbf::MAX_PAYLOAD];
  const int n = snprintf(json, sizeof json,
    "{\"profile\":\"F05_USB_BENCH\",\"build_id\":\"%s\",\"fs_Hz\":%u,\"spi_Hz\":%u,\"channels\":8,"
    "\"bench_measured\":%s,\"bench_basis\":\"%s\",\"transport\":\"usb_cdc\",\"drdy_source\":\"%s\",\"off_body_only\":true}",
    MAKO_V12_BUILD_ID, MAKO_V12_FS, MAKO_V12_SPI_HZ, MAKO_BENCH_MEASURED ? "true" : "false", MAKO_BENCH_BASIS, DRDY_MODE == 0 ? "auto" : DRDY_MODE == 1 ? "dout_mirror" : "drdy_pin");
  if (n <= 0 || n >= int(sizeof json)) return;  // 截断就不发，宁缺不错
  uint8_t out[usbf::MAX_PAYLOAD + 6];
  send(out, usbf::encode(usbf::META, reinterpret_cast<const uint8_t *>(json), size_t(n), out));
}

void setup() {
  // 先置低再设输出，避免初始化瞬间拉高 ANA_EN 或 ADS 控制脚（同 F05 hold_afe_off）
  const uint8_t outputs[] = {D0, D1, D2, D4, D7, D8, D10};
  for (uint8_t p : outputs) { digitalWrite(p, LOW); pinMode(p, OUTPUT); }
  pinMode(D5, INPUT); pinMode(D6, INPUT); pinMode(D9, INPUT);
  digitalWrite(VBAT_ENABLE, LOW); pinMode(VBAT_ENABLE, OUTPUT);
  analogReadResolution(12); analogReference(AR_INTERNAL);
  v12::timebase_begin();
  Serial.begin(115200);  // USB CDC，波特率不起作用
}

static uint32_t next_status = 0;

void loop() {
  poll_commands();
  if (!Serial) { reg_n = 0; if (ads.active) ads.stop(v12::Fault::Cancelled); if (pwr_on) { pwr_on = false; ads.stop(); } stop_req = false; start_req = 0; pwr_req = false; delay(1); return; }
  if (meta_req) { meta_req = false; send_meta(); }
  if (diag_req) { diag_req = false; send_diag(); }
  if (stop_req) { stop_req = false; start_req = 0; reg_n = 0; pwr_req = false; if (ads.active) { ads.stop(); send_edge_report(); } if (pwr_on) { pwr_on = false; ads.stop(); } send_status(); }
  if (pwr_req) {
    pwr_req = false;
    if (!ads.active && !pwr_on) { board.power(true); pwr_on = true; pwr_until = millis() + 30000; }
  }
  if (pwr_on) {
    board.rails_good();  // 只为刷新 AVDD/OE_N 读数
    if (int32_t(millis() - pwr_until) >= 0 || start_req) { pwr_on = false; ads.stop(); send_status(); }
  }  // 启动中已记的 Cancelled 不被抹掉
  if (start_req && ads.active) { start_req = 0; blind = false; hold_req = false; }  // 采集中再收到开始命令直接丢弃，避免故障停机后自动重新上电
  if (start_req && !ads.active) {
    const uint8_t mode = start_req; start_req = 0; seq = 0; usb_full = 0;
    const v12::BenchProof proof = {bool(MAKO_BENCH_MEASURED), MAKO_BENCH_POR_US, MAKO_BENCH_REFERENCE_US};
    ads.start(MAKO_V12_FS, v12::Input(mode), proof);  // 失败时 fault 已记下，状态帧会报
    if (blind && ads.active) {
      // 盲读诊断：不等 DRDY，每 1ms 直接读 27 字节，同时看 D6 电平和 ISR 计数；200 次后断电回报。
      // 数据在变=ADS 在转换（问题在 DRDY 到 XIAO 这一段）；不变=ADS 没转换（查时钟/启动）。
      uint8_t first[27] = {0}, prev[27] = {0}, f[27];
      int hdr_c0 = 0, changed = 0, d6_high = 0;
      for (int i = 0; i < 200 && ads.active; ++i) {
        delay(1);
        if (digitalRead(D5) != LOW) { ads.stop(v12::Fault::Rails); break; }
        d6_high += digitalRead(D6) == HIGH;
        board.cs(false); for (int k = 0; k < 27; ++k) f[k] = board.transfer(0); board.cs(true);
        hdr_c0 += (f[0] & 0xF0) == 0xC0;
        if (i == 0) memcpy(first, f, 27); else changed += memcmp(f, prev, 27) != 0;
        memcpy(prev, f, 27);
      }
      noInterrupts(); const uint32_t edges = edge_count; interrupts();
      // 轮询对照（不用中断）：100ms 内高速看 D6，一变低就读走 27 字节；DRDY 正常则约 2kSPS×2 次跳变/秒
      int poll_rise = 0, poll_fall = 0, poll_reads = 0;
      if (ads.active) {
        int last = digitalRead(D6);
        const uint32_t t0 = v12::timer_us(2);
        while (uint32_t(v12::timer_us(2) - t0) < 100000u) {
          const int now = digitalRead(D6);
          if (now != last) { if (now) ++poll_rise; else ++poll_fall; last = now; }
          if (!now) { board.cs(false); for (int k = 0; k < 27; ++k) f[k] = board.transfer(0); board.cs(true); ++poll_reads;
                      last = digitalRead(D6); }
        }
      }
      noInterrupts(); const uint32_t edges_after_poll = edge_count; interrupts();
      // DOUT 代替 DRDY 的试验：CS 拉低、不给时钟，20ms 内轮询 MISO(D9) 电平跳变；
      // 若 ADS 在 CS 低时把 DRDY 反映到 DOUT，2kSPS 下应看到约 40 次下降沿（是否有此特性未查实，以实测为准）
      int dout_rise = 0, dout_fall = 0, dout_high = 0;
      if (ads.active) {
        board.cs(false);
        int last = digitalRead(D9);
        const uint32_t t0 = v12::timer_us(2);
        while (uint32_t(v12::timer_us(2) - t0) < 20000u) {
          const int now = digitalRead(D9); dout_high += now;
          if (now != last) { if (now) ++dout_rise; else ++dout_fall; last = now; }
        }
        board.cs(true);
      }
      // D6 上下拉对比（ADS 仍在运行、不再读数据，DRDY 应稳定为低）：被 U3 驱动则上下拉都读低；悬空则跟着上下拉走
      int pu_high = 0, pd_high = 0, pu_mv = 0;
      if (ads.active) {
        detachInterrupt(digitalPinToInterrupt(D6));
        pinMode(D6, INPUT_PULLUP); delay(5); for (int i = 0; i < 10; ++i) { pu_high += digitalRead(D6); delay(1); }
        pu_mv = int(float(analogRead(D6)) * 3600.0f / 4095.0f);
        pinMode(D6, INPUT_PULLDOWN); delay(5); for (int i = 0; i < 10; ++i) { pd_high += digitalRead(D6); delay(1); }
        pinMode(D6, INPUT);
      }
      if (ads.active) ads.stop();
      char hex[55]; for (int k = 0; k < 27; ++k) snprintf(hex + 2 * k, 3, "%02x", first[k]);
      char json[usbf::MAX_PAYLOAD];
      const int n = snprintf(json, sizeof json, "{\"diag\":2,\"reads\":200,\"hdr_c0\":%d,\"changed\":%d,\"d6_high\":%d,\"isr_edges\":%lu,\"d6_pullup_high\":%d,\"d6_pulldown_high\":%d,\"poll_rise\":%d,\"poll_fall\":%d,\"poll_reads\":%d,\"isr_edges_after_poll\":%lu,\"dout_rise\":%d,\"dout_fall\":%d,\"dout_high_samples\":%d}",
                             hdr_c0, changed, d6_high, (unsigned long)edges, pu_high, pd_high, poll_rise, poll_fall, poll_reads, (unsigned long)edges_after_poll, dout_rise, dout_fall, dout_high);
      if (n > 0 && n < int(sizeof json)) { uint8_t out[usbf::MAX_PAYLOAD + 6]; send(out, usbf::encode(usbf::META, reinterpret_cast<const uint8_t *>(json), size_t(n), out)); }
    }
    blind = false;
    if (hold_req && ads.active) { holding = true; hold_until = millis() + 30000; }
    edge_log_n = 0; last_poll_us = 0; max_gap_us = 0; gap_at_sample = 0; inferred_edges = 0; inferred_run = 0; ds_reset();
    if (ads.active && !holding) select_drdy_source();
    hold_req = false;
    start_req = 0;  // 6 秒等待里主机重复发的开始命令一律作废，失败后不自动重新上电
    send_status();
  }
  if (holding) {
    // 连续盲读：每次读完 ADS 的 DRDY 会变高、下一帧再变低，DRDY 脚上应是约 2kHz 的方波，万用表直流档读到零点几伏
    if (!ads.active || int32_t(millis() - hold_until) >= 0) { holding = false; if (ads.active) ads.stop(); send_status(); }
    else if (digitalRead(D5) != LOW) { holding = false; ads.stop(v12::Fault::Rails); send_status(); }
    else { uint8_t f[27]; board.cs(false); for (int k = 0; k < 27; ++k) f[k] = board.transfer(0); board.cs(true); delayMicroseconds(200); }
    const uint32_t now2 = millis();
    if (int32_t(now2 - next_status) >= 0) { next_status = now2 + 200; send_status(); }
    return;
  }
  if (ads.active) {
    if (dout_mode) poll_dout_drdy();
    if (late_overrun) { late_overrun = false; ads.stop(v12::Fault::Overrun); send_status(); send_edge_report(); return; }  // 迟到超过 1.4T：可能漏帧
    noInterrupts(); const uint32_t count = edge_count, edge = edge_us; interrupts();
    if (digitalRead(D5) != LOW) ads.stop(v12::Fault::Rails);
    else if (count != used_edge) {
      // 与 F05 一致：沿数不对或间隔异常就停机，不补造样本
      if (v12::uncertain_edge(have_edge, count, used_edge, edge - last_edge_us, MAKO_V12_FS)) ads.stop(v12::Fault::Overrun);
      else {
        uint8_t frame[27]; int32_t raw[8];
        bool got;
        if (dout_isr) { reading_frame = true; got = dout_read(frame); reading_frame = false; }  // CS 不翻转，读完 DOUT 留在末位，下一帧前的下降沿照常进中断
        else got = dout_mode ? dout_read(frame) : ads.read(frame);
        if (got) {
          noInterrupts(); const uint32_t after = edge_count; interrupts();
          if (after != count) ads.stop(v12::Fault::Overrun);
          else if (!v12::Ads1298::decode(frame, 27, raw, &ads_status)) ads.stop(v12::Fault::Frame);
          else {
            uint8_t out[usbf::SAMPLE_PAYLOAD + 6];
            const size_t n = usbf::sample(seq | (edge_inferred ? 0x80000000u : 0u), edge, frame, out);  // 最高位=推算帧
            if (send(out, n)) ++seq;  // 主机读不过来，send 内部已停机
            used_edge = count; last_edge_us = edge; have_edge = true;
            if (reg_n && dout_mode) apply_regs();  // 刚读完一帧，离下一帧还有约 300µs
          }
          if (dout_mode && ads.active) { board.cs(false); last_dout = 0; d6_check(); dout_port()->LATCH = dout_mask(); /* 读帧时钟留下的锁存清掉 */ decide_drdy_source(); const uint32_t rd = v12::timer_us(2) - edge; if (rd > ds.rd_max) ds.rd_max = rd; ++(digitalRead(D9) ? ds.relow_hi : ds.relow_lo); }  // CS 本来就低（dout_read 不翻转）；同样要求先升后降
        }
      }
    } else if (v12::capture_timeout(have_edge, v12::timer_us(2) - (have_edge ? last_edge_us : capture_started), MAKO_V12_FS)) ads.stop(v12::Fault::Timeout);
    if (!ads.active) { send_status(); send_edge_report(); }
  }
  const uint32_t now = millis();
  // 采集中不发周期状态帧：样本自带序号；状态帧那一下会让本轮超过 500µs、漏掉下一个 DOUT 沿（实测约每 200ms 漏一次）
  if (!ads.active && int32_t(now - next_status) >= 0) { next_status = now + 200; send_status(); }
}

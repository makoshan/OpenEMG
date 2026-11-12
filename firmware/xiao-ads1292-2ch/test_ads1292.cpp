#include "src/ads1292.h"
#include "src/ads1292_pins.h"
#include "src/bench_release.h"
#include "src/capture_guard.h"
extern "C" {
#include "src/v12_stream.h"
}

#include <algorithm>
#include <array>
#include <cassert>
#include <cstring>
#include <iostream>
#include <utility>
#include <vector>

using namespace v12;

struct Mock1292 final : Ads1292Hal {
  std::array<uint8_t, 12> regs{};
  std::array<uint8_t, 9> frame{};
  std::vector<uint8_t> packet;
  std::vector<uint32_t> waits;
  std::vector<std::pair<bool, uint32_t>> pwdn_pulses; // (level, duration_after_it)
  std::vector<std::pair<int, int>> writes;
  std::vector<int> stop_trace;

  bool spi_on = false;
  bool pwdn_high = false;
  bool start_high = false;
  bool cs_high = true;
  bool rail = true;
  bool vbus = false;
  bool continuous = true;
  bool started = false;
  bool capturing = false;
  int spi_begin_count = 0;
  int transfers = 0;
  int bad_read = -1;
  bool bad_rld_second_write = false;
  uint8_t gpio_input_bits = 0x03; // 模拟 GPIOD[2:1] 浮动输入位，验证掩码只比 bit3:2
  uint32_t elapsed = 0;
  uint32_t cancel_at = 0;
  uint32_t vbus_plug_at = 0;

  Mock1292() {
    regs[0x00] = 0x53; // ADS1292 ID
    regs[0x01] = 0x02;
    regs[0x02] = 0x80;
    regs[0x03] = 0x10;
    regs[0x0A] = 0x02;
    regs[0x0B] = 0x0C;
    frame = {0xC0, 0x00, 0x00, 0x12, 0x34, 0x56, 0xFE, 0xDC, 0xBA};
  }

  void spi_bus(bool on) override {
    spi_on = on;
    if (on) ++spi_begin_count;
    else stop_trace.push_back(5);
  }
  void pwdn(bool high) override {
    pwdn_high = high;
    pwdn_pulses.push_back({high, 0u});
    if (!high) stop_trace.push_back(3);
  }
  void start_pin(bool high) override {
    start_high = high;
    if (!high) stop_trace.push_back(2);
  }
  void cs(bool high) override {
    cs_high = high;
    if (!high) {
      packet.clear();
      return;
    }
    stop_trace.push_back(4);
    if (packet.empty()) return;
    if (packet[0] == 0x11u) {
      continuous = false;
    } else if (packet[0] == 0x10u) {
      continuous = true;
    } else if (packet[0] == 0x08u) {
      started = true;
    } else if ((packet[0] & 0xE0u) == 0x40u) {
      assert(!continuous && packet.size() == 3u && packet[1] == 0u);
      const int addr = packet[0] & 0x1Fu;
      assert(addr >= 0x01 && addr <= 0x0B && addr != 0x08); // 绝不允许写只读 LOFF_STAT(0x08)
      regs[addr] = packet[2];
      writes.push_back({addr, packet[2]});
    }
  }
  uint8_t transfer(uint8_t v) override {
    ++transfers;
    packet.push_back(v);
    if (continuous && started && packet[0] == 0u) {
      assert(v == 0u && packet.size() <= Ads1292::FRAME_BYTES);
      return frame[packet.size() - 1u];
    }
    if ((packet[0] & 0xE0u) == 0x20u && packet.size() == 3u) {
      assert(!continuous && packet[1] == 0u);
      const int addr = packet[0] & 0x1Fu;
      assert(addr >= 0x00 && addr <= 0x0B);
      uint8_t val = regs[addr] | (addr == 0x0B ? gpio_input_bits : 0u);
      if (addr == bad_read || (bad_rld_second_write && addr == 0x06 && regs[0x06] == 0x23u)) {
        val ^= 0x04u;
      }
      return val;
    }
    return 0u;
  }
  void wait(uint32_t us) override {
    waits.push_back(us);
    if (!pwdn_pulses.empty()) pwdn_pulses.back().second += us;
    elapsed += us;
  }
  bool vbus_present() override {
    return vbus || (vbus_plug_at && elapsed >= vbus_plug_at);
  }
  bool rails_good() override { return rail && !vbus_present(); }
  bool session_valid() override { return !cancel_at || elapsed < cancel_at; }
  void capture(bool on) override {
    capturing = on;
    if (!on) stop_trace.push_back(1);
  }
};

int main() {
  unsigned cases = 0;

  // 1. 默认编译头必须锁死真实 AFE（MAKO_BENCH_MEASURED == 0）
  {
    assert(MAKO_BENCH_MEASURED == 0);
    assert(MAKO_BENCH_POR_US >= 1000000u);
    assert(MAKO_BENCH_REFERENCE_US == 0u);
    Mock1292 h;
    Ads1292 a(h);
    const BenchProof default_proof = {bool(MAKO_BENCH_MEASURED), MAKO_BENCH_POR_US, MAKO_BENCH_REFERENCE_US};
    assert(!a.start(2000, Input::Test, default_proof));
    assert(a.fault == Fault::Locked && h.spi_begin_count == 0 && h.transfers == 0 && !h.pwdn_high && h.cs_high);
    ++cases;
  }

  // 2. 四类不完整台架证据（measured=false / por<1s / ref=0 / ref<150ms）全部必须被硬件锁拦截
  const BenchProof proof = {true, 1000000u, 200000u};
  for (BenchProof denied : {BenchProof{false, 1000000u, 200000u},
                            BenchProof{true, 999999u, 200000u},
                            BenchProof{true, 1000000u, 0u},
                            BenchProof{true, 1000000u, 149999u}}) {
    Mock1292 h;
    Ads1292 a(h);
    assert(!a.start(2000, Input::Test, denied));
    assert(a.fault == Fault::Locked && h.spi_begin_count == 0 && h.transfers == 0);
    ++cases;
  }

  // 3. 全模式（Test / Shorted / External / ExternalRld / RldMeasure）× 四档采样率（500 / 1k / 2k / 4k）正例与手册不变量检查
  for (unsigned fs : {500u, 1000u, 2000u, 4000u}) {
    for (Input input : {Input::Test, Input::Shorted, Input::External, Input::ExternalRld, Input::RldMeasure}) {
      const bool use_rld = (input == Input::ExternalRld || input == Input::RldMeasure);
      Mock1292 h;
      Ads1292 a(h);
      assert(a.start(fs, input, proof));
      assert(a.active && a.fault == Fault::None && h.capturing && h.spi_on && h.pwdn_high && !h.start_high && h.cs_high);

      // 核对 TI SBAS502C 全部关键寄存器终值
      const uint8_t want_c1 = (fs == 500u) ? 0x02u : (fs == 1000u ? 0x03u : (fs == 2000u ? 0x04u : 0x05u));
      assert(h.regs[0x01] == want_c1);
      assert(h.regs[0x02] == (input == Input::Test ? 0xA3u : 0xA0u)); // Test 必须开 TEST_FREQ=1(方波)，非 DC(0xA2)
      assert(h.regs[0x03] == 0x10u);
      const uint8_t want_mux = (input == Input::Test) ? 0x05u : (input == Input::Shorted ? 0x01u : 0x00u);
      assert(h.regs[0x04] == want_mux);
      assert(h.regs[0x05] == (input == Input::RldMeasure ? 0x02u : want_mux));
      assert(h.regs[0x06] == (use_rld ? 0x23u : 0x00u)); // 首测严格只选 CH1 进 RLD(0x23)，禁写双路(0x2F)
      assert(h.regs[0x07] == 0x00u);
      assert(h.regs[0x09] == 0x02u);                     // SBAS502C p.60 必写 0x02
      assert(h.regs[0x0A] == 0x07u);                     // SBAS502C 表 24：bit2=1, RLDREF_INT=1, bit0=1
      assert(h.regs[0x0B] == 0x0Cu);

      // 核对 RLD 两步开启顺序：第 1 步写 0x20 预热 PDB_RLD 运放等 >=150ms，最后一步才写 0x23 闭合 CH1 开关
      std::vector<int> rld_writes;
      for (const auto &kv : h.writes) {
        if (kv.first == 0x06) rld_writes.push_back(kv.second);
      }
      if (use_rld) {
        assert((rld_writes == std::vector<int>{0x20, 0x23}));
        assert(h.writes.back() == std::make_pair(0x06, 0x23));
      } else {
        assert((rld_writes == std::vector<int>{0x00}));
      }

      // 核对复位低脉冲严格落在 [8 µs, 100 µs]（绝不触发 >=4000 µs 硬掉电）
      bool saw_reset_low = false;
      for (size_t i = 1; i + 1 < h.pwdn_pulses.size(); ++i) {
        if (h.pwdn_pulses[i - 1].first && !h.pwdn_pulses[i].first && h.pwdn_pulses[i + 1].first) {
          assert(h.pwdn_pulses[i].second >= 8u && h.pwdn_pulses[i].second <= 100u);
          assert(h.pwdn_pulses[i + 1].second >= 36u); // >= 18 t_CLK
          saw_reset_low = true;
        }
      }
      assert(saw_reset_low);

      // 核对 9 字节读取与停机安全引脚状态（CS=HIGH 零上拉漏电，PWDN=LOW，START=LOW）
      uint8_t raw_bytes[9] = {};
      const int before = h.transfers;
      assert(a.read(raw_bytes));
      assert(h.transfers - before == 9 && std::memcmp(raw_bytes, h.frame.data(), 9) == 0 && h.cs_high);
      h.stop_trace.clear();
      a.stop();
      assert(!a.active && !h.capturing && !h.pwdn_high && !h.start_high && h.cs_high && !h.spi_on);
      assert((h.stop_trace == std::vector<int>{1, 2, 3, 4, 5}));
      ++cases;
    }
  }

  // 4. USB VBUS 互锁：启动前有 VBUS 或启动中途插入 USB 均必须立即拉低 PWDN 并报 Fault::UsbInterlock
  {
    Mock1292 h;
    h.vbus = true;
    Ads1292 a(h);
    assert(!a.start(2000, Input::Test, proof));
    assert(a.fault == Fault::UsbInterlock && !a.active && !h.pwdn_high && h.cs_high && h.spi_begin_count == 0);
    ++cases;
  }
  for (uint32_t plug_us : {15000u, 500000u, 1150000u}) {
    Mock1292 h;
    h.vbus_plug_at = plug_us;
    Ads1292 a(h);
    assert(!a.start(2000, Input::ExternalRld, proof));
    assert(a.fault == Fault::UsbInterlock && !a.active && !h.pwdn_high && !h.started);
    ++cases;
  }

  // 5. 非法参数、AVDD_SENSE 掉轨、ID 正反例（0x53/0x73 放行；0x51 1ch / 0x92 8ch / 0x00 / 0xFF 拒绝）
  {
    Mock1292 h;
    Ads1292 a(h);
    assert(!a.start(250, Input::Test, proof) && a.fault == Fault::Argument);
    assert(!a.start(8000, Input::Test, proof) && a.fault == Fault::Argument);
    assert(!a.start(2000, Input(4), proof) && a.fault == Fault::Argument);
    assert(!a.start(2000, Input(6), proof) && a.fault == Fault::Argument);
    ++cases;
  }
  {
    Mock1292 h;
    h.rail = false;
    Ads1292 a(h);
    assert(!a.start(2000, Input::Test, proof) && a.fault == Fault::Rails && !h.pwdn_high && !h.spi_on);
    ++cases;
  }
  for (uint8_t ok_id : {uint8_t(0x53), uint8_t(0x73)}) {
    Mock1292 h;
    h.regs[0x00] = ok_id;
    Ads1292 a(h);
    assert(a.start(2000, Input::Shorted, proof) && a.device_id == ok_id);
    a.stop();
    ++cases;
  }
  for (uint8_t bad_id : {uint8_t(0x51), uint8_t(0x71), uint8_t(0x92), uint8_t(0xD2), uint8_t(0x00), uint8_t(0xFF)}) {
    Mock1292 h;
    h.regs[0x00] = bad_id;
    Ads1292 a(h);
    assert(!a.start(2000, Input::Shorted, proof) && a.fault == Fault::Identity && !h.pwdn_high);
    ++cases;
  }

  // 6. 寄存器回读错（含 RESP2、GPIO 方向位与第二步开 RLD）必须全部报 Fault::Readback 并断电
  for (int reg : {0x01, 0x02, 0x04, 0x09, 0x0A, 0x0B}) {
    Mock1292 h;
    h.bad_read = reg;
    Ads1292 a(h);
    assert(!a.start(2000, Input::Test, proof) && a.fault == Fault::Readback && !h.pwdn_high && !h.started);
    ++cases;
  }
  {
    Mock1292 h;
    h.bad_rld_second_write = true;
    Ads1292 a(h);
    assert(!a.start(2000, Input::ExternalRld, proof) && a.fault == Fault::Readback && !h.pwdn_high && !h.started);
    ++cases;
  }

  // 7. 帧头损坏拦截 + 9B 解码至 V12 8 通道 F01 包完整编码往返校验
  {
    Mock1292 h;
    Ads1292 a(h);
    assert(a.start(2000, Input::Test, proof));
    h.frame[0] = 0x80; // 破坏 0xC0 状态头
    uint8_t bad_frame[9] = {};
    assert(!a.read(bad_frame) && a.fault == Fault::Frame && !a.active && !h.pwdn_high);
    ++cases;
  }
  {
    // raw_status: 1100(23:20) | RLD_STAT=1(19) | IN2N=0(18) | IN2P=1(17) | IN1N=1(16) | IN1P=0(15) | GPIO=10b(14:13) -> 0xCB4000
    const uint8_t f9[9] = {0xCB, 0x40, 0x00, 0x7F, 0xFF, 0xFF, 0x80, 0x00, 0x00};
    int32_t raw8[8] = {-1, -1, -1, -1, -1, -1, -1, -1};
    uint32_t st = 0;
    assert(Ads1292::decode(f9, 9, raw8, &st));
    assert(st == 0xCB4000u && raw8[0] == 8388607 && raw8[1] == -8388608);
    for (int ch = 2; ch < 8; ++ch) assert(raw8[ch] == 0);
    assert(!Ads1292::decode(f9, 8, raw8, &st));

    // 验证 ADS1292 原生状态位 -> F01 统一 8 通道 LOFF_STATP/N + GPIO 位序无损映射（对齐 host/ads1298_regs.py:decode_ads_status）
    for (uint32_t mask5 = 0; mask5 < 64u; ++mask5) {
      const uint32_t in1p = (mask5 >> 0) & 1u;
      const uint32_t in1n = (mask5 >> 1) & 1u;
      const uint32_t in2p = (mask5 >> 2) & 1u;
      const uint32_t in2n = (mask5 >> 3) & 1u;
      const uint32_t gpio = (mask5 >> 4) & 3u;
      const uint32_t raw_st = 0xC80000u | (in2n << 18) | (in2p << 17) | (in1n << 16) | (in1p << 15) | (gpio << 13);
      uint8_t out3[3] = {};
      Ads1292::map_f01_status(raw_st, out3);
      const uint32_t w = (uint32_t(out3[0]) << 16) | (uint32_t(out3[1]) << 8) | uint32_t(out3[2]);
      assert((w >> 20) == 0xCu);
      assert(((w >> 12) & 0xFFu) == ((in2p << 1) | in1p)); // LOFF_STATP[1:0]
      assert(((w >> 4) & 0xFFu) == ((in2n << 1) | in1n));  // LOFF_STATN[1:0]
      assert((w & 0x0Fu) == gpio);
    }

    v12_stream stream{};
    assert(v12_stream_init(&stream, 2000) == V12_STREAM_OK);
    assert(v12_stream_push(&stream, raw8, 1000000u) == V12_STREAM_OK);
    uint8_t mapped_hdr[3] = {};
    Ads1292::map_f01_status(st, mapped_hdr);
    Ads1292::map_f01_status(st, stream.ring[0].frame);
    const uint8_t *pkt_bytes = nullptr;
    size_t pkt_len = 0;
    assert(v12_stream_peek(&stream, 247, &pkt_bytes, &pkt_len) == V12_STREAM_OK);
    assert(pkt_len == V12_HEADER + V12_FRAME);
    v12_packet decoded{};
    assert(v12_decode(pkt_bytes, pkt_len, 247, &decoded) == 0);
    assert(decoded.count == 1u && (decoded.flags & 2u) != 0u && decoded.sequence == 0u);
    assert(std::memcmp(decoded.frames, mapped_hdr, 3) == 0);
    assert(std::memcmp(decoded.frames + 3, f9 + 3, 6) == 0);
    for (size_t z = 9; z < V12_FRAME; ++z) assert(decoded.frames[z] == 0u);
    assert(v12_stream_commit(&stream) == V12_STREAM_OK);
    ++cases;
  }

  std::cout << "ADS1292+P44e 驱动与 V12 协议正反例全部通过：" << cases << " 项；未接真板，不是实物验收\n";
  return 0;
}

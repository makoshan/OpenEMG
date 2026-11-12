#pragma once
#include <stddef.h>
#include <stdint.h>

namespace v12 {

// 与 R01 F05 控制码保持一致：1=TST1, 2=SHT1, 3=EXT1, (4=STOP), 5=EXR1(CH1进RLD), 7=RLD1(CH2路由29脚测RLD波形)。
enum class Input : uint8_t {
  Test = 1,
  Shorted = 2,
  External = 3,
  ExternalRld = 5,
  RldMeasure = 7,
};

// 前 10 项与 R01 Fault 编码完全对齐；10=UsbInterlock 专指检测到 USB VBUS 触发软件第二道互锁。
enum class Fault : uint8_t {
  None = 0,
  Locked = 1,
  Argument = 2,
  Rails = 3,
  Identity = 4,
  Readback = 5,
  Frame = 6,
  Overrun = 7,
  Timeout = 8,
  Cancelled = 9,
  UsbInterlock = 10,
};

struct BenchProof {
  bool measured;
  uint32_t por_wait_us;
  uint32_t reference_wait_us;
};

struct Ads1292Hal {
  virtual ~Ads1292Hal() = default;
  virtual void spi_bus(bool on) = 0;
  virtual void pwdn(bool high) = 0;
  virtual void start_pin(bool high) = 0;
  virtual void cs(bool high) = 0;
  virtual uint8_t transfer(uint8_t value) = 0;
  virtual void wait(uint32_t us) = 0;
  virtual bool vbus_present() = 0;
  virtual bool rails_good() = 0;
  virtual bool session_valid() = 0;
  virtual void capture(bool on) = 0;
};

class Ads1292 {
  Ads1292Hal &h;
  void command(uint8_t cmd);
  uint8_t read_reg(uint8_t address);
  bool write_checked(uint8_t address, uint8_t value);

 public:
  static constexpr size_t FRAME_BYTES = 9u;            // 24 位状态 + 2 × 24 位通道
  static constexpr uint32_t MIN_POR_WAIT_US = 1000000u; // TI SBAS502C §8.5.1.8：VCAP1=1 µF 需 >=1 s 建立
  static constexpr uint32_t MIN_REF_WAIT_US = 150000u;  // VREFP 接 C7=10 µF + C6=100 nF，2.42V 基准与 RLD 预热需 >=150 ms
  static constexpr uint32_t RESET_LOW_US = 20u;        // >= 1 t_MOD(7.81 µs) 且 << 2^9 t_MOD(4000 µs 硬掉电门限)
  static constexpr uint32_t RESET_RECOVER_US = 40u;    // >= 18 t_CLK(35.2 µs)
  static constexpr uint32_t CMD_DECODE_US = 10u;       // >= 4 t_CLK(7.81 µs) t_SDECODE / t_SCCS

  bool active = false;
  Fault fault = Fault::None;
  uint8_t device_id = 0u;

  explicit Ads1292(Ads1292Hal &hal) : h(hal) {}
  void stop(Fault why = Fault::None);
  bool start(unsigned fs, Input input, const BenchProof &proof);
  bool read(uint8_t frame[FRAME_BYTES]);
  static bool decode(const uint8_t *frame, size_t n, int32_t out[8], uint32_t *status);
  static void map_f01_status(uint32_t raw_status, uint8_t out3[3]);
};

}  // namespace v12

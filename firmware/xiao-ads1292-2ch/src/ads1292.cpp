#include "ads1292.h"

namespace v12 {

void Ads1292::stop(Fault why) {
  active = false;
  h.capture(false);
  h.start_pin(false);
  h.pwdn(false);   // P44e 上 PWDN_N 有 10 kΩ 下拉，置 LOW 零静态漏电并让 ADS1292 进入硬掉电
  h.cs(true);      // P44e 上 CS_A 有 10 kΩ 上拉到常开 3V3，停机保持 HIGH 避免 0.33 mA 漏电
  h.spi_bus(false);
  fault = why;
}

void Ads1292::command(uint8_t cmd) {
  h.cs(false);
  h.transfer(cmd);
  h.wait(CMD_DECODE_US);
  h.cs(true);
  h.wait(CMD_DECODE_US);
}

uint8_t Ads1292::read_reg(uint8_t address) {
  h.cs(false);
  h.transfer(uint8_t(0x20u | (address & 0x1fu)));
  h.wait(CMD_DECODE_US);
  h.transfer(0x00u);
  h.wait(CMD_DECODE_US);
  const uint8_t value = h.transfer(0x00u);
  h.wait(CMD_DECODE_US);
  h.cs(true);
  h.wait(CMD_DECODE_US);
  return value;
}

bool Ads1292::write_checked(uint8_t address, uint8_t value) {
  h.cs(false);
  h.transfer(uint8_t(0x40u | (address & 0x1fu)));
  h.wait(CMD_DECODE_US);
  h.transfer(0x00u);
  h.wait(CMD_DECODE_US);
  h.transfer(value);
  h.wait(CMD_DECODE_US);
  h.cs(true);
  h.wait(CMD_DECODE_US);
  // GPIO(0x0B) bit3:2 为方向配置 GPIOC[2:1]，bit1:0 为实时引脚电平 GPIOD[2:1]，只校验方向位。
  const uint8_t mask = (address == 0x0Bu) ? 0x0Cu : 0xFFu;
  return (read_reg(address) & mask) == (value & mask);
}

bool Ads1292::start(unsigned fs, Input input, const BenchProof &proof) {
  stop();
  // 没有实板 TPS7A2030、VCAP1(>=1s) 与 2.42V 基准建立时间(>=150ms)证据，默认拒绝开启真实 AFE。
  if (!proof.measured || proof.por_wait_us < MIN_POR_WAIT_US || proof.reference_wait_us < MIN_REF_WAIT_US) {
    fault = Fault::Locked;
    return false;
  }
  const bool valid_input = (input == Input::Test || input == Input::Shorted ||
                            input == Input::External || input == Input::ExternalRld ||
                            input == Input::RldMeasure);
  const bool valid_fs = (fs == 500u || fs == 1000u || fs == 2000u || fs == 4000u);
  if (!valid_fs || !valid_input) {
    fault = Fault::Argument;
    return false;
  }
  if (!h.session_valid()) {
    fault = Fault::Cancelled;
    return false;
  }
  if (h.vbus_present()) {
    stop(Fault::UsbInterlock);
    return false;
  }

  // 检查常开 3.0 V AVDD（经 R26 100 kΩ 至 D5）连续 10 次稳定在 2.75–3.25 V 窗内。
  unsigned stable = 0u;
  for (unsigned i = 0u; i < 100u && stable < 10u; ++i) {
    h.wait(5000u);
    if (!h.session_valid()) {
      stop(Fault::Cancelled);
      return false;
    }
    if (h.vbus_present()) {
      stop(Fault::UsbInterlock);
      return false;
    }
    stable = h.rails_good() ? (stable + 1u) : 0u;
  }
  if (stable < 10u) {
    stop(Fault::Rails);
    return false;
  }

  h.cs(true);
  h.start_pin(false);  // START 脚全程保持低，统一用 SPI START 命令启动
  h.spi_bus(true);
  h.pwdn(true);        // 释放掉电，等待 VCAP1(1 µF) 建立 >= 1 s
  h.wait(proof.por_wait_us);
  if (!h.session_valid()) {
    stop(Fault::Cancelled);
    return false;
  }
  if (h.vbus_present()) {
    stop(Fault::UsbInterlock);
    return false;
  }
  if (!h.rails_good()) {
    stop(Fault::Rails);
    return false;
  }

  // TI SBAS502C 图 44 & §8.5.1.8：发 20 µs 低脉冲复位（>=7.81 µs，且远小于 4000 µs 掉电阈值），等 40 µs (>=18 t_CLK)。
  h.pwdn(false);
  h.wait(RESET_LOW_US);
  h.pwdn(true);
  h.wait(RESET_RECOVER_US);

  command(0x11u);  // SDATAC：芯片复位后默认处于连续读模式，必须先退出才能读写寄存器
  device_id = read_reg(0x00u);
  // ADS1292 = 0x53 (010_1_00_11)，ADS1292R = 0x73 (011_1_00_11)；拒绝 1 通道 ADS1291(0x51/0x71) 与 8 通道 ADS1298(0x92)。
  if ((device_id & 0xDFu) != 0x53u) {
    stop(Fault::Identity);
    return false;
  }

  const bool use_rld = (input == Input::ExternalRld || input == Input::RldMeasure);
  uint8_t regs[0x0C] = {};
  // CONFIG1(0x01)：SINGLE_SHOT=0，512 kHz 内部时钟下 500->0x02, 1k->0x03, 2k->0x04, 4k->0x05。
  regs[0x01] = (fs == 500u) ? 0x02u : ((fs == 1000u) ? 0x03u : ((fs == 2000u) ? 0x04u : 0x05u));
  // CONFIG2(0x02)：bit7=1，PDB_REFBUF=1(开 2.42 V 内部基准)，VREF_4V=0；Test 模式另置 INT_TEST=1, TEST_FREQ=1(1 Hz 方波；0 为直流)。
  regs[0x02] = (input == Input::Test) ? 0xA3u : 0xA0u;
  // LOFF(0x03)：手册要求 bit4=1。
  regs[0x03] = 0x10u;
  // CH1SET(0x04), CH2SET(0x05)：GAIN=000(增益 6)；MUX=0000(电极) / 0001(内部短接) / 0101(测试方波) / 0010(RLD_MEASURE)。
  const uint8_t ch_mux = (input == Input::Test) ? 0x05u : ((input == Input::Shorted) ? 0x01u : 0x00u);
  regs[0x04] = ch_mux;
  regs[0x05] = (input == Input::RldMeasure) ? 0x02u : ch_mux;
  // RLD_SENS(0x06)：两步开启第 1 步——需 RLD 时先写 0x20 开启 PDB_RLD 预热运放与 AVDD/2，保持电极反馈开关断开。
  regs[0x06] = use_rld ? 0x20u : 0x00u;
  regs[0x07] = 0x00u;
  // 0x08 LOFF_STAT 为只读状态寄存器，循环中跳过。
  // RESP1(0x09)：TI SBAS502C p.60 明文规定 ADS1292 必须写 0x02（复位值 0x00 不满足）。
  regs[0x09] = 0x02u;
  // RESP2(0x0A)：TI SBAS502C 表 24 明文规定 ADS1292 bit2 必须写 1，bit1(RLDREF_INT)=1 选内部 AVDD/2，bit0=1 -> 0x07。
  regs[0x0A] = 0x07u;
  // GPIO(0x0B)：GPIOC[2:1]=11 两脚全设输入（板上 R21/R22 47 kΩ 下拉接地）。
  regs[0x0B] = 0x0Cu;

  for (uint8_t a = 0x01u; a <= 0x0Bu; ++a) {
    if (!h.session_valid()) {
      stop(Fault::Cancelled);
      return false;
    }
    if (h.vbus_present()) {
      stop(Fault::UsbInterlock);
      return false;
    }
    if (a == 0x08u) continue;  // LOFF_STAT 只读
    if (!write_checked(a, regs[a])) {
      stop(Fault::Readback);
      return false;
    }
  }

  // 等待内部 2.42 V 基准电容（C7 10 µF + C6 100 nF）与 RLD 运放（0x20）建立稳定（>=150 ms）。
  h.wait(proof.reference_wait_us);
  if (!h.session_valid()) {
    stop(Fault::Cancelled);
    return false;
  }
  if (h.vbus_present()) {
    stop(Fault::UsbInterlock);
    return false;
  }
  if (!h.rails_good()) {
    stop(Fault::Rails);
    return false;
  }

  // 基准稳定后，仅在需要 RLD 的模式下第 2 步闭合 CH1 反馈开关(RLD1N=1, RLD1P=1 -> 0x23，相位裕度 65–89°)。
  if (use_rld && !write_checked(0x06u, 0x23u)) {
    stop(Fault::Readback);
    return false;
  }

  command(0x10u);  // RDATAC
  if (!h.session_valid()) {
    stop(Fault::Cancelled);
    return false;
  }
  if (h.vbus_present()) {
    stop(Fault::UsbInterlock);
    return false;
  }
  h.capture(true);
  command(0x08u);  // START 命令启动连续转换
  if (!h.session_valid()) {
    stop(Fault::Cancelled);
    return false;
  }
  if (h.vbus_present()) {
    stop(Fault::UsbInterlock);
    return false;
  }
  active = true;
  fault = Fault::None;
  return true;
}

bool Ads1292::read(uint8_t frame[FRAME_BYTES]) {
  if (!active || !frame) return false;
  h.cs(false);
  for (size_t i = 0u; i < FRAME_BYTES; ++i) {
    frame[i] = h.transfer(0x00u);  // DIN 保持低，整帧移出 72 个时钟
  }
  h.wait(CMD_DECODE_US);           // t_SCCS >= 4 t_CLK = 7.81 µs 后才允许拉高 CS
  h.cs(true);
  if ((frame[0] & 0xF0u) != 0xC0u) {
    stop(Fault::Frame);
    return false;
  }
  return true;
}

bool Ads1292::decode(const uint8_t *frame, size_t n, int32_t out[8], uint32_t *status) {
  if (!frame || !out || !status || n != FRAME_BYTES || (frame[0] & 0xF0u) != 0xC0u) {
    return false;
  }
  *status = (uint32_t(frame[0]) << 16) | (uint32_t(frame[1]) << 8) | uint32_t(frame[2]);
  for (unsigned ch = 0u; ch < 2u; ++ch) {
    const unsigned j = 3u + ch * 3u;
    const uint32_t code = (uint32_t(frame[j]) << 16) | (uint32_t(frame[j + 1u]) << 8) | uint32_t(frame[j + 2u]);
    out[ch] = (code & 0x800000u) ? (int32_t(code) - 0x1000000) : int32_t(code);
  }
  for (unsigned ch = 2u; ch < 8u; ++ch) {
    out[ch] = 0;  // 补齐为 V12 统一 8 通道帧（CH3–CH8 恒置 0）
  }
  return true;
}

void Ads1292::map_f01_status(uint32_t raw_status, uint8_t out3[3]) {
  // ADS1292 原生 24 位状态：1100 | RLD_STAT(19) | IN2N(18) | IN2P(17) | IN1N(16) | IN1P(15) | GPIO2:1(14:13) | 13x0
  // 统一 V12 F01 24 位状态：1100 | LOFF_STATP[7:0](19:12) | LOFF_STATN[7:0](11:4) | GPIO[3:0](3:0)
  const uint32_t in1p = (raw_status >> 15) & 1u;
  const uint32_t in1n = (raw_status >> 16) & 1u;
  const uint32_t in2p = (raw_status >> 17) & 1u;
  const uint32_t in2n = (raw_status >> 18) & 1u;
  const uint32_t gpio = (raw_status >> 13) & 0x03u;
  const uint32_t f01 = 0xC00000u | (in2p << 13) | (in1p << 12) | (in2n << 5) | (in1n << 4) | gpio;
  out3[0] = uint8_t(f01 >> 16);
  out3[1] = uint8_t(f01 >> 8);
  out3[2] = uint8_t(f01);
}

}  // namespace v12

#pragma once
#include <stdint.h>
#include <stddef.h>
// USB 串口帧：A5 5A | 类型 | 负载长度 | 负载 | CRC16-CCITT（小端，覆盖类型+长度+负载）
// 类型 1=样本（序号u32、DRDY时刻µs u32、ADS原始27字节），2=状态，3=元数据JSON。
namespace usbf {
enum : uint8_t { SAMPLE = 1, STATUS = 2, META = 3 };
constexpr size_t SAMPLE_PAYLOAD = 4 + 4 + 27;
constexpr size_t STATUS_PAYLOAD = 20;
constexpr size_t MAX_PAYLOAD = 250;

inline uint16_t crc16(const uint8_t *p, size_t n, uint16_t crc = 0xFFFF) {
  for (size_t i = 0; i < n; ++i) {
    crc ^= uint16_t(p[i]) << 8;
    for (int b = 0; b < 8; ++b) crc = (crc & 0x8000) ? uint16_t((crc << 1) ^ 0x1021) : uint16_t(crc << 1);
  }
  return crc;
}
inline void put32(uint8_t *p, uint32_t v) { p[0] = v; p[1] = v >> 8; p[2] = v >> 16; p[3] = v >> 24; }

// 把一帧写进 out（容量至少 len+6），返回总字节数；负载超长返回 0。
inline size_t encode(uint8_t type, const uint8_t *payload, size_t len, uint8_t *out) {
  if (len > MAX_PAYLOAD) return 0;
  out[0] = 0xA5; out[1] = 0x5A; out[2] = type; out[3] = uint8_t(len);
  for (size_t i = 0; i < len; ++i) out[4 + i] = payload[i];
  const uint16_t c = crc16(out + 2, len + 2);
  out[4 + len] = uint8_t(c); out[5 + len] = uint8_t(c >> 8);
  return len + 6;
}
inline size_t sample(uint32_t seq, uint32_t t_us, const uint8_t frame[27], uint8_t *out) {
  uint8_t p[SAMPLE_PAYLOAD];
  put32(p, seq); put32(p + 4, t_us);
  for (int i = 0; i < 27; ++i) p[8 + i] = frame[i];
  return encode(SAMPLE, p, sizeof p, out);
}
// 状态：故障码、是否在采、台架锁放行、最近一次电源粗筛时D5(OE_N)电平、DRDY原始沿数、已发样本、
// 采集中USB缓冲不足次数、最近一次电源粗筛读到的AVDD(mV，D3经1:4分压换算)、XIAO电池电压(mV)
inline size_t status(uint8_t fault, bool active, bool released, uint32_t edges, uint32_t sent,
                     uint32_t usb_full, uint8_t *out, uint8_t oe_n = 0xFF, uint16_t avdd_mv = 0xFFFF,
                     uint16_t vbat_mv = 0xFFFF) {
  uint8_t p[STATUS_PAYLOAD] = {fault, uint8_t(active), uint8_t(released), oe_n};
  put32(p + 4, edges); put32(p + 8, sent); put32(p + 12, usb_full);
  p[16] = uint8_t(avdd_mv); p[17] = uint8_t(avdd_mv >> 8);
  p[18] = uint8_t(vbat_mv); p[19] = uint8_t(vbat_mv >> 8);
  return encode(STATUS, p, sizeof p, out);
}
}  // namespace usbf

#pragma once
#include <stdint.h>
namespace dout {
// 名义周期500us；取450us作为候选的保守下界（假设时钟偏差不超过10%，实物未验）。
// LATCH不计次数：必须从最后一次确认低电平开始，覆盖观察、DMA、清锁存和重新布防整段。
static constexpr uint32_t MIN_PERIOD_US = 450;
static constexpr uint32_t FIRST_TIMEOUT_US = 10000;
inline bool window_ok(uint32_t low_before, uint32_t now) {
  return uint32_t(now - low_before) < MIN_PERIOD_US;
}
inline bool interval_ok(bool have, uint32_t previous, uint32_t now) {
  const uint32_t dt = now - previous;
  return !have || (dt >= 350 && dt <= 650);
}
}

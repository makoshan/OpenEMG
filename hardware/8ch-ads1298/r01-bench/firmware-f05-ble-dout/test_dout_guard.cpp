#include "src/dout_guard.h"
#include <cassert>
#include <cstdio>
int main() {
  // 正常窗口、严格边界、DMA前/中/后抢占、多个脉冲合并的长黑窗都不得接受。
  assert(dout::window_ok(1000, 1110));
  assert(dout::window_ok(1000, 1449));
  assert(!dout::window_ok(1000, 1450));
  assert(!dout::window_ok(1000, 1501)); // DMA前已迟到
  assert(!dout::window_ok(1000, 1700)); // DMA中抢占
  assert(!dout::window_ok(1000, 2001)); // 清锁存前抢占/多个脉冲合并
  assert(dout::window_ok(0xffffffd0u, 60)); // TIMER2回绕
  assert(!dout::window_ok(0xffffff00u, 300));
  assert(dout::interval_ok(false, 0, 10000));
  assert(dout::interval_ok(true, 1000, 1500));
  assert(!dout::interval_ok(true, 1000, 1349));
  assert(!dout::interval_ok(true, 1000, 1651));
  assert(!dout::interval_ok(true, 1000, 2000)); // 缺一个周期，不补帧
  assert(dout::interval_ok(true, 0xfffffff0u, 484));
  puts("DOUT时间窗口14项通过；只验证软件判停，不代替实物时序。");
}

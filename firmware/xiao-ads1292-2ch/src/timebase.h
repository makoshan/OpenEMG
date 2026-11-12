#pragma once
#include <stdint.h>
namespace v12 {
// 仅主循环扩展，至少每个32位周期读一次；不在ISR中修改64位状态。
struct Timebase {
 uint32_t previous=0;
 uint64_t epoch=0;
 uint64_t extend(uint32_t current) {
  if(current<previous)epoch+=UINT64_C(1)<<32;
  previous=current;return epoch+current;
 }
};
}

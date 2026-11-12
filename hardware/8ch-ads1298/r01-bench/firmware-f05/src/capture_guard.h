#pragma once
#include <stdint.h>
namespace v12 {
// ADS首帧还要等待数字滤波器稳定，不能套用稳态4个采样周期的超时。
inline bool capture_timeout(bool have_frame,uint32_t elapsed,unsigned fs) {
 return elapsed>(have_frame?4000000u/fs:10000u);
}
inline bool uncertain_edge(bool have_frame,uint32_t count,uint32_t used,uint32_t delta,unsigned fs) {
 const uint32_t period=1000000u/fs;
 return count-used!=1u || (have_frame && (delta<period*7/10 || delta>period*13/10));
}
}

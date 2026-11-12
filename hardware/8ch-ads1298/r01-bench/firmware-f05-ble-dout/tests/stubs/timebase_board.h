#pragma once
#include "Arduino.h"
namespace v12 {
inline void timebase_begin() {}
inline uint32_t timer_us(unsigned) {
 if (mock_after_dma) {mock_us += mock_after_dma_us;mock_after_dma = false;}
 return mock_us++;
}
inline uint64_t clock_us() {return timer_us(2);}
}

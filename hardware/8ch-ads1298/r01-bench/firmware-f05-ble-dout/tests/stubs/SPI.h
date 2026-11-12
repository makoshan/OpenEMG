#pragma once
#include "Arduino.h"
#define MSBFIRST 0
#define SPI_MODE1 1
struct SPISettings { SPISettings(int, int, int) {} };
struct MockSPI {
 void begin() {} void end() {} void beginTransaction(SPISettings) {} void endTransaction() {}
 uint8_t transfer(uint8_t) { return 0; }
 void transfer(const void *, void *dst, size_t len) {
  ++mock_dma_calls; mock_us += mock_dma_us; mock_after_dma = true;
  memset(dst, 0, len); static_cast<uint8_t *>(dst)[0] = 0xc0;
  p1.IN = 0; p1.LATCH.value |= 1u << 14; // DMA期间数据1置锁存，必须清掉。
 }
};
inline MockSPI SPI;

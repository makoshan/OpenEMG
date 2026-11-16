#pragma once
#include <cstdint>

#define MSBFIRST  1u
#define SPI_MODE1 1u

struct SPISettings {
    uint32_t hz;
    uint8_t  order;
    uint8_t  mode;
    SPISettings(uint32_t h = 1000000u, uint8_t o = MSBFIRST, uint8_t m = SPI_MODE1)
        : hz(h), order(o), mode(m) {}
};

struct SimSpiMaster {
    void begin(void);
    void beginTransaction(const SPISettings &s);
    uint8_t transfer(uint8_t b);
    void endTransaction(void);
    void end(void);
};

extern SimSpiMaster SPI;

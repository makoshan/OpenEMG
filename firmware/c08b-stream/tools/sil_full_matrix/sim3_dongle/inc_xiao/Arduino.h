#pragma once
#include <cstdarg>
#include <cstdbool>
#include <cstddef>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <algorithm>

using std::min;

struct SimNrfTimer {
    volatile uint32_t TASKS_STOP;
    volatile uint32_t INTENCLR;
    volatile uint32_t SHORTS;
    volatile uint32_t MODE;
    volatile uint32_t BITMODE;
    volatile uint32_t PRESCALER;
    volatile uint32_t TASKS_CLEAR;
    volatile uint32_t TASKS_START;
    struct CaptureProxy {
        int idx;
        CaptureProxy &operator=(uint32_t v);
    } TASKS_CAPTURE[6];
    volatile uint32_t CC[6];
};

#define TIMER_MODE_MODE_Timer      0u
#define TIMER_BITMODE_BITMODE_32Bit 3u

extern SimNrfTimer g_xd_timer2;
#define NRF_TIMER2 (&g_xd_timer2)

inline void __DMB(void) {}

void vTaskSuspendAll(void);
void xTaskResumeAll(void);
uint32_t millis(void);
void yield(void);

struct SimUsbCdcSerial {
    void begin(uint32_t baud);
    size_t write(const uint8_t *buf, size_t len);
    int available(void);
    int read(void);
    explicit operator bool() const;
};

extern SimUsbCdcSerial Serial;

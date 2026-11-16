#pragma once
#include <cstdbool>
#include <cstddef>
#include <cstdint>
#include <cstdio>
#include <cstring>

#define D0  0u
#define D1  1u
#define D2  2u
#define D3  3u
#define D4  4u
#define D5  5u
#define D6  6u
#define D7  7u
#define D8  8u
#define D9  9u
#define D10 10u

#define PIN_SPI_SCK  8u
#define PIN_SPI_MISO 9u
#define PIN_SPI_MOSI 10u

#define INPUT       0u
#define OUTPUT      1u
#define LOW         0u
#define HIGH        1u
#define FALLING     2u
#define AR_INTERNAL 0u

#define POWER_USBREGSTATUS_VBUSDETECT_Msk 1u
struct SimNrfPower { volatile uint32_t USBREGSTATUS; };
extern SimNrfPower g_x2_power;
#define NRF_POWER (&g_x2_power)

struct SimX2Timer {
    volatile uint32_t TASKS_STOP;
    volatile uint32_t INTENCLR;
    volatile uint32_t SHORTS;
    volatile uint32_t MODE;
    volatile uint32_t BITMODE;
    volatile uint32_t PRESCALER;
    volatile uint32_t TASKS_CLEAR;
    volatile uint32_t TASKS_START;
    struct CapProxy {
        int idx;
        CapProxy &operator=(uint32_t v);
    } TASKS_CAPTURE[6];
    volatile uint32_t CC[6];
};
#define TIMER_MODE_MODE_Timer       0u
#define TIMER_BITMODE_BITMODE_32Bit 3u
extern SimX2Timer g_x2_timer2;
#define NRF_TIMER2 (&g_x2_timer2)

inline void __DMB(void) {}
uint32_t __get_PRIMASK(void);
void __disable_irq(void);
void __set_PRIMASK(uint32_t m);
void vTaskSuspendAll(void);
void xTaskResumeAll(void);

void pinMode(uint32_t pin, uint32_t mode);
void digitalWrite(uint32_t pin, uint32_t val);
uint32_t digitalPinToInterrupt(uint32_t pin);
void attachInterrupt(uint32_t irq, void (*fn)(void), uint32_t mode);
void detachInterrupt(uint32_t irq);

void analogReadResolution(int bits);
void analogReference(uint32_t ref);
void analogSampleTime(uint32_t us);
unsigned analogRead(uint32_t pin);

void delay(uint32_t ms);
void delayMicroseconds(uint32_t us);
void yield(void);

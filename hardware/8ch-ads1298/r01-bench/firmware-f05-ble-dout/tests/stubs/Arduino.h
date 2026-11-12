#pragma once
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <cstddef>
#include <initializer_list>
#define D0 0
#define D1 1
#define D2 2
#define D3 3
#define D4 4
#define D5 5
#define D6 6
#define D7 7
#define D8 8
#define D9 9
#define D10 10
#define PIN_SPI_SCK 8
#define PIN_SPI_MISO 9
#define PIN_SPI_MOSI 10
#define MAKO_V12_FS 2000
#define MAKO_V12_SPI_HZ 2000000
#define MAKO_V12_AFE_ENABLED 0
#define LOW 0
#define HIGH 1
#define INPUT 0
#define OUTPUT 1
#define AR_INTERNAL 0
#define GPIO_PIN_CNF_SENSE_Msk 3u
#define GPIO_PIN_CNF_SENSE_Pos 0
#define GPIO_PIN_CNF_SENSE_High 2u
#define GPIO_DETECTMODE_DETECTMODE_LDETECT 1u
#define POWER_USBREGSTATUS_VBUSDETECT_Msk 1u
struct Latch {
 uint32_t value = 0;
 operator uint32_t() volatile const { return value; }
 void operator=(uint32_t bits) volatile { value &= ~bits; } // 模拟真实W1C，而非普通赋值。
};
struct NRF_GPIO_Type { uint32_t IN = 0, DETECTMODE = 0, PIN_CNF[32] = {}; Latch LATCH; };
struct MockPower { uint32_t USBREGSTATUS = 0; };
inline NRF_GPIO_Type p0, p1;
inline NRF_GPIO_Type *NRF_P0 = &p0, *NRF_P1 = &p1;
inline MockPower power_reg;
inline MockPower *NRF_POWER = &power_reg;
inline uint32_t g_ADigitalPinMap[11] = {2,3,28,29,4,5,43,44,45,46,47};
inline uint32_t mock_us = 0, mock_dma_us = 110, mock_after_dma_us = 0;
inline bool mock_after_dma = false, mock_subscribed = true;
inline unsigned mock_dma_calls = 0;
inline int analogRead(int) { return 1422; }
inline void analogReadResolution(int) {}
inline void analogReference(int) {}
inline void digitalWrite(int, int) {}
inline void pinMode(int, int) {}
inline int digitalRead(int p) { return p == D5 ? LOW : HIGH; }
inline void delay(unsigned n) { mock_us += n * 1000; }
inline void delayMicroseconds(unsigned n) { mock_us += n; }
inline void yield() {}
inline void vTaskSuspendAll() {}
inline void xTaskResumeAll() {}

#define FALLING 2
inline uint32_t __get_PRIMASK(){return 0;}
inline void __disable_irq(){}
inline void __set_PRIMASK(uint32_t){}
inline void __DMB(){}
inline int digitalPinToInterrupt(int p){return p;}
inline void attachInterrupt(int,void(*)(),int){}
inline bool mock_stop_race=false;
inline void (*mock_stop_hook)()=nullptr;
inline void detachInterrupt(int p){if(p==D9 && mock_stop_race){mock_stop_race=false;mock_stop_hook();}}

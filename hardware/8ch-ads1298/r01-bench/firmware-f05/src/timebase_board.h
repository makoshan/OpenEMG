#pragma once
#include <Arduino.h>
#include "timebase.h"
namespace v12 {
// TIMER0属于SoftDevice；TIMER2只在SDK初始化时保存过bootloader版本。
// 采集期间保持运行，不复用CC，不把1µs分辨率写成实测精度。
static void timebase_begin() {
 NRF_TIMER2->TASKS_STOP=1;
 NRF_TIMER2->INTENCLR=0xffffffff;
 NRF_TIMER2->SHORTS=0;
 NRF_TIMER2->MODE=TIMER_MODE_MODE_Timer;
 NRF_TIMER2->BITMODE=TIMER_BITMODE_BITMODE_32Bit;
 NRF_TIMER2->PRESCALER=4; // 16MHz/16=1MHz，回绕周期2^32µs。
 NRF_TIMER2->TASKS_CLEAR=1;
 NRF_TIMER2->TASKS_START=1;
}
static uint32_t timer_us(unsigned channel) {
 // ADS ISR=0、IMU ISR=1、主循环=2，互不覆盖捕获寄存器。
 NRF_TIMER2->TASKS_CAPTURE[channel]=1;
 __DMB();return NRF_TIMER2->CC[channel];
}
static uint64_t clock_us() {
 static Timebase time;
 return time.extend(timer_us(2));
}
}

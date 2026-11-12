
#pragma once
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <assert.h>
#define D0 0
#define D1 1
#define D2 2
#define D6 6
#define D7 7
#define D8 8
#define D9 9
#define D10 10
#define PIN_SPI_SCK 8
#define PIN_SPI_MISO 9
#define PIN_SPI_MOSI 10
#define LOW 0
#define OUTPUT 1
#define INPUT_PULLDOWN 2
extern uint64_t fake_now;
extern int suspend_depth;
extern void (*resume_hook)();
extern unsigned output_lows;
inline uint32_t micros(){return (uint32_t)fake_now;}
inline void delay(unsigned){}
inline void yield(){}
inline void digitalWrite(uint8_t pin,int value){assert(value==LOW);output_lows|=1u<<pin;}
inline void pinMode(uint8_t pin,int mode){if(mode==OUTPUT)assert(output_lows&(1u<<pin));}
inline void vTaskSuspendAll(){++suspend_depth;}
inline int xTaskResumeAll(){assert(suspend_depth>0);--suspend_depth;if(resume_hook&&!suspend_depth){auto f=resume_hook;resume_hook=nullptr;f();}return 0;}

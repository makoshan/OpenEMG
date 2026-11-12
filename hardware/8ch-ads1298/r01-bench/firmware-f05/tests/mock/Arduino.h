#pragma once
#include <stdint.h>
struct TwimRegs {volatile uint32_t EVENTS_STOPPED=0,EVENTS_ERROR=0,EVENTS_LASTTX=0,EVENTS_LASTRX=0,TASKS_RESUME=0,TASKS_STOP=0,TASKS_STARTTX=0,ENABLE=0,INTENCLR=0,FREQUENCY=0,ADDRESS=0,ERRORSRC=0,SHORTS=0;struct Pins{volatile uint32_t SDA=0,SCL=0;}PSEL;struct Dma{volatile uint32_t PTR=0,MAXCNT=0,AMOUNT=0;}TXD,RXD;};
extern TwimRegs regs;
#define NRF_TWIM1 (&regs)
constexpr unsigned PIN_LSM6DS3TR_C_POWER=15,LOW=0,HIGH=1,OUTPUT_H0H1=1,NRF_GPIO_PIN_DIR_INPUT=0,NRF_GPIO_PIN_INPUT_CONNECT=0,NRF_GPIO_PIN_PULLUP=3,NRF_GPIO_PIN_S0D1=0,NRF_GPIO_PIN_NOSENSE=0,TWIM_FREQUENCY_FREQUENCY_K400=0x06400000,TWIM_ENABLE_ENABLE_Enabled=6,TWIM_SHORTS_LASTTX_STARTRX_Msk=1u<<7,TWIM_SHORTS_LASTRX_STOP_Msk=1u<<12,TWIM_SHORTS_LASTTX_STOP_Msk=1u<<9;
extern unsigned power_value;
inline void digitalWrite(unsigned,unsigned value){power_value=value;}
inline void pinMode(unsigned,unsigned){}
inline void nrf_gpio_cfg(unsigned,unsigned,unsigned,unsigned,unsigned,unsigned){}
inline void __DMB(){}

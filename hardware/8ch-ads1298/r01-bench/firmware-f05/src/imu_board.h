#pragma once
#include <Arduino.h>
#include "imu.h"

namespace v12 {
struct ImuBoard:ImuHal {
 bool busy=false,owns=false,stopping=false;
 uint8_t tx[2]={},rx[16]={};unsigned tx_length=0,rx_length=0;
 // 固定生命周期的RAM缓冲；只有STOPPED后才能复制读数或启动下一事务。
 bool power(bool on) override {
  if(!on) {
   if(!owns)return true;
   if(busy && !NRF_TWIM1->EVENTS_STOPPED) {
    // 异步停DMA；STOPPED前保持外设、供电与缓冲，不伪报已停止。
    stopping=true;NRF_TWIM1->TASKS_RESUME=1;NRF_TWIM1->TASKS_STOP=1;
    return false;
   }
   __DMB();NRF_TWIM1->ENABLE=0;
   NRF_TWIM1->PSEL.SDA=0xffffffff;NRF_TWIM1->PSEL.SCL=0xffffffff;
   digitalWrite(PIN_LSM6DS3TR_C_POWER,LOW);
   owns=busy=stopping=false;return true;
  }
  if(owns || busy || stopping || NRF_TWIM1->ENABLE)return false;
  pinMode(PIN_LSM6DS3TR_C_POWER,OUTPUT_H0H1);digitalWrite(PIN_LSM6DS3TR_C_POWER,HIGH);
  nrf_gpio_cfg(7,NRF_GPIO_PIN_DIR_INPUT,NRF_GPIO_PIN_INPUT_CONNECT,NRF_GPIO_PIN_PULLUP,NRF_GPIO_PIN_S0D1,NRF_GPIO_PIN_NOSENSE);
  nrf_gpio_cfg(27,NRF_GPIO_PIN_DIR_INPUT,NRF_GPIO_PIN_INPUT_CONNECT,NRF_GPIO_PIN_PULLUP,NRF_GPIO_PIN_S0D1,NRF_GPIO_PIN_NOSENSE);
  NRF_TWIM1->PSEL.SDA=7;NRF_TWIM1->PSEL.SCL=27;
  NRF_TWIM1->INTENCLR=0xffffffff;NRF_TWIM1->FREQUENCY=TWIM_FREQUENCY_FREQUENCY_K400;
  NRF_TWIM1->ENABLE=TWIM_ENABLE_ENABLE_Enabled;owns=true;return true;
 }
 void address(uint8_t value) override {NRF_TWIM1->ADDRESS=value;}
 bool transfer(unsigned tx_count,unsigned rx_count) {
  if(!owns || busy || stopping)return false;
  tx_length=tx_count;rx_length=rx_count;
  NRF_TWIM1->EVENTS_STOPPED=NRF_TWIM1->EVENTS_ERROR=NRF_TWIM1->EVENTS_LASTTX=NRF_TWIM1->EVENTS_LASTRX=0;
  NRF_TWIM1->ERRORSRC=NRF_TWIM1->ERRORSRC;
  NRF_TWIM1->TXD.PTR=uint32_t(uintptr_t(tx));NRF_TWIM1->TXD.MAXCNT=tx_count;
  NRF_TWIM1->RXD.PTR=uint32_t(uintptr_t(rx));NRF_TWIM1->RXD.MAXCNT=rx_count;
  NRF_TWIM1->SHORTS=rx_count?(TWIM_SHORTS_LASTTX_STARTRX_Msk|TWIM_SHORTS_LASTRX_STOP_Msk):TWIM_SHORTS_LASTTX_STOP_Msk;
  __DMB();busy=true;NRF_TWIM1->TASKS_STARTTX=1;return true;
 }
 bool read(uint8_t reg,unsigned length) override {
  if(busy || length>sizeof(rx) || !length)return false;
  tx[0]=reg;return transfer(1,length);
 }
 bool write(uint8_t reg,uint8_t value) override {
  if(busy)return false;
  tx[0]=reg;tx[1]=value;return transfer(2,0);
 }
 int poll(uint8_t *out,unsigned length) override {
  if(!busy)return -1;
  if(NRF_TWIM1->EVENTS_ERROR){NRF_TWIM1->TASKS_RESUME=1;NRF_TWIM1->TASKS_STOP=1;}
  if(!NRF_TWIM1->EVENTS_STOPPED)return 0;
  __DMB();busy=false;
  // 写事务未启动RX，RXD.AMOUNT可保留上次读数，不能要求它变为0。
  if(NRF_TWIM1->EVENTS_ERROR || NRF_TWIM1->TXD.AMOUNT!=tx_length || (rx_length && NRF_TWIM1->RXD.AMOUNT!=rx_length) || length!=rx_length)return -1;
  if(length)memcpy(out,rx,length);
  return 1;
 }
};
}

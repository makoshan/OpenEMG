#include <Arduino.h>
#include <Adafruit_TinyUSB.h> // 本核的Serial/USB栈在这个库里，不引用就链接失败
#include "power_seq.h"
// 阶段3只开电源固件：电池供电上电后跑一次，跑完常关。没有SPI、BLE和采样。
#if defined(MAKO_V12_AFE_ENABLED) || defined(MAKO_BENCH_MEASURED)
#error "P03不参与F05解锁，不接受F05的锁宏"
#endif
#ifndef P03_HOLD_MS
#define P03_HOLD_MS 10000
#endif
#ifndef P03_ARM_MS
#define P03_ARM_MS 3000
#endif

// 板包LED_STATE_ON写1，但initVariant用HIGH熄灯，实物是低电平亮。灭灯改成断开引脚，不依赖极性。
static void led(uint8_t pin,bool on){if(on){digitalWrite(pin,LOW);pinMode(pin,OUTPUT);}else pinMode(pin,INPUT);}

struct BoardHal final: p03::Hal {
 void ana_en(bool on) override {digitalWrite(D0,on?HIGH:LOW);}
 void pwdn(bool on) override {digitalWrite(D4,on?HIGH:LOW);}
 void reset(bool on) override {digitalWrite(D2,on?HIGH:LOW);}
 void clocksel(bool on) override {digitalWrite(D1,on?HIGH:LOW);}
 void cs(bool on) override {digitalWrite(D7,on?HIGH:LOW);}
 void wait_us(uint32_t us) override {if(us>=1000)delay(us/1000);if(us%1000)delayMicroseconds(us%1000);}
 float avdd() {return float(analogRead(D3))*14.4f/4095.0f;} // 0.6V×6量程再×板上1:4分压，与F05同
 bool rails_good() override {const float v=avdd();return digitalRead(D5)==LOW && v>=4.6f && v<=5.4f;}
 bool rails_idle() override {return digitalRead(D5)==HIGH && avdd()<1.0f;}
 // 蓝灯常亮=开电源到复位前（万用表在这段读VCAP1）；绿灯常亮=复位后保持
 void stage(uint8_t n) override {led(LED_BLUE,n==1);led(LED_GREEN,n==2);}
} board;

void setup() {
 // 先置低再设输出，避免初始化瞬间拉高ANA_EN或ADS控制脚；SPI脚D8/D10同样钉低。
 const uint8_t outputs[]={D0,D1,D2,D4,D7,D8,D10};
 for(uint8_t p:outputs){digitalWrite(p,LOW);pinMode(p,OUTPUT);}
 pinMode(D5,INPUT);pinMode(D6,INPUT);pinMode(D9,INPUT);
 analogReadResolution(12);analogReference(AR_INTERNAL);
 const uint8_t leds[]={LED_RED,LED_GREEN,LED_BLUE};
 for(uint8_t p:leds)led(p,false);
 // 蓝灯闪：留时间给示波器布防，建议单次触发在TP9上升沿。
 for(uint32_t t=0;t<P03_ARM_MS;t+=250){led(LED_BLUE,(t/250)%2==0);delay(250);}
 led(LED_BLUE,false);
 const p03::Fault f=p03::run(board,uint32_t(P03_HOLD_MS)*1000u);
 led(LED_BLUE,false);led(LED_GREEN,false);
 // 结果：绿灯每2秒闪一下=正常跑完；红灯连闪N下=故障码N（见README）。
 for(;;){
  if(f==p03::Fault::None){led(LED_GREEN,true);delay(100);led(LED_GREEN,false);delay(1900);}
  else{for(uint8_t i=0;i<uint8_t(f);++i){led(LED_RED,true);delay(200);led(LED_RED,false);delay(300);}delay(1500);}
 }
}
void loop() {}

#pragma once
#include <stdint.h>
// 阶段3专用：只走模拟电源与ADS上电/复位时序，给示波器看。
// 不含SPI、不读ID、不写寄存器、不采样；时序与F05 Ads1298::start()在复位脉冲之前的部分一致。
namespace p03 {
enum class Fault : uint8_t { None=0, AlreadyOn=1, RailsNeverStable=2, RailsAfterPor=3, RailsDuringHold=4 };
struct Hal {
 virtual ~Hal()=default;
 virtual void ana_en(bool)=0;   // D0 → R24 → U7_EN
 virtual void pwdn(bool)=0;     // D4
 virtual void reset(bool)=0;    // D2
 virtual void clocksel(bool)=0; // D1
 virtual void cs(bool)=0;       // D7
 virtual void wait_us(uint32_t)=0;
 virtual bool rails_good()=0;   // OE_N低且AVDD在4.6–5.4V，与F05同一粗筛
 virtual bool rails_idle()=0;   // 关断状态应有：OE_N高且AVDD<1V
 // 阶段提示（给指示灯用）：1=开模拟电源到复位前，2=复位之后保持。
 virtual void stage(uint8_t){}
};
// 默认与F05 bench_release.h的MAKO_BENCH_POR_US相同：数据手册2^18个tCLK≈128ms，留余量。
// 万用表验收版加长到5s，并且整个等待期亮蓝灯：只有蓝灯还亮时读到VCAP1>1.1V才算数，
// 说明复位前的等待够用；绿灯（复位后保持期）里的读数只说明“最后到了”，不能用来定等待时间。
#ifndef P03_POR_US
#define P03_POR_US 132000u
#endif
constexpr uint32_t POR_US=P03_POR_US;
static_assert(POR_US>=132000u,"POR等待不能短于数据手册最小值");
static_assert(POR_US<=10000000u,"POR等待过长，t+=POLL_US可能回绕");
constexpr uint32_t POLL_US=5000u;
inline void all_off(Hal &h) {
 // 与F05 stop()同序：先撤ADS控制脚，最后关模拟电源。
 h.pwdn(false);h.reset(false);h.clocksel(false);h.cs(false);h.ana_en(false);
}
inline Fault run(Hal &h,uint32_t hold_us) {
 all_off(h);
 if(!h.rails_idle())return Fault::AlreadyOn; // 没开就已经有电：USB/硬件问题，不继续
 h.stage(1);h.ana_en(true);
 unsigned stable=0;
 for(unsigned i=0;i<100 && stable<10;++i){h.wait_us(POLL_US);stable=h.rails_good()?stable+1:0;}
 if(stable<10){all_off(h);return Fault::RailsNeverStable;}
 h.cs(true);h.clocksel(true);h.reset(true);h.pwdn(true);
 // 等待期间每5ms查一次电源；等待加长到秒级后，不能等到最后才发现掉电。
 for(uint32_t t=0;t<POR_US;t+=POLL_US){h.wait_us(POLL_US);if(!h.rails_good()){all_off(h);return Fault::RailsAfterPor;}}
 h.reset(false);h.wait_us(3);h.reset(true);h.wait_us(10); // 复位脉冲，示波器看TP6
 h.stage(2);
 for(uint32_t t=0;t<hold_us;t+=POLL_US){h.wait_us(POLL_US);if(!h.rails_good()){all_off(h);return Fault::RailsDuringHold;}}
 all_off(h);
 return Fault::None;
}
}

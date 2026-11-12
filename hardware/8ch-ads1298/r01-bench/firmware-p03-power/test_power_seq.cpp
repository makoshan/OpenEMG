// 主机自检：c++ -std=c++17 -Wall -Wextra -Werror -Isrc test_power_seq.cpp -o /tmp/p03 && /tmp/p03
#include "power_seq.h"
#include <cstdio>
#include <cstdlib>
#include <string>
#include <vector>
#define CHECK(x) do{if(!(x)){std::printf("FAIL %s:%d %s\n",__FILE__,__LINE__,#x);std::exit(1);}}while(0)
struct Fake: p03::Hal {
 bool en=false,pd=false,rst=false,clk=false,csn=false,idle=true;
 uint64_t t=0,pd_at=0,rst_low_at=0,rst_low_width=0,ready_at=UINT64_MAX;
 int fail_after_us=-1;unsigned good_from_poll=1,polls=0,streak=0;bool order_ok=true;
 std::vector<std::string> log;
 void ctl(bool v,bool &pin,const char *name){
  // 任何ADS控制脚拉高都必须在“电源连续10次合格”之后
  if(v && (!en || t<ready_at))order_ok=false;
  pin=v;log.push_back(std::string(name)+(v?"1":"0"));
 }
 void ana_en(bool v) override {en=v;if(!v){streak=0;ready_at=UINT64_MAX;}log.push_back(v?"EN1":"EN0");}
 void pwdn(bool v) override {ctl(v,pd,"PD");if(v)pd_at=t;}
 // 只记PWDN开着时的复位脉冲，关断时的RESET拉低不算
 void reset(bool v) override {if(!v&&rst&&pd)rst_low_at=t;if(v&&!rst&&pd)rst_low_width=t-rst_low_at;ctl(v,rst,"R");}
 void clocksel(bool v) override {ctl(v,clk,"C");}
 void cs(bool v) override {ctl(v,csn,"S");}
 void wait_us(uint32_t us) override {t+=us;}
 bool rails_good() override {
  ++polls;bool g=en && polls>=good_from_poll;
  if(fail_after_us>=0 && pd && t-pd_at>=uint64_t(fail_after_us))g=false;
  streak=g?streak+1:0;if(streak==10 && ready_at==UINT64_MAX)ready_at=t;return g;
 }
 bool rails_idle() override {return idle;}
 void stage(uint8_t n) override {log.push_back("ST"+std::to_string(n));if(n==2 && !stage2_at)stage2_at=t;}  // 记第一次换绿灯的时刻
 uint64_t stage2_at=0;
};
static void check_off(const Fake &f){
 CHECK(!f.en&&!f.pd&&!f.rst&&!f.clk&&!f.csn);
 const size_t n=f.log.size();CHECK(n>=5);
 // 每条路径最后一次关断都是：先撤 PWDN/RESET/CLKSEL/CS，最后关 EN
 CHECK(f.log[n-5]=="PD0"&&f.log[n-4]=="R0"&&f.log[n-3]=="C0"&&f.log[n-2]=="S0"&&f.log[n-1]=="EN0");
 CHECK(f.order_ok);
}
static bool has(const Fake &f,const char *s){for(auto &x:f.log)if(x==s)return true;return false;}
int main(){
 {Fake f;CHECK(p03::run(f,10000000)==p03::Fault::None);check_off(f);
  CHECK(f.rst_low_at-f.pd_at>=p03::POR_US);  // 复位前等足POR
  CHECK(f.rst_low_width>=3);
  CHECK(has(f,"ST1") && f.stage2_at>f.rst_low_at);}   // 蓝灯段一直持续到复位脉冲之后才换绿灯                 // 复位低电平≥3µs
 {Fake f;f.idle=false;CHECK(p03::run(f,1000)==p03::Fault::AlreadyOn);check_off(f);CHECK(!has(f,"EN1"));}
 {Fake f;f.good_from_poll=1000;CHECK(p03::run(f,1000)==p03::Fault::RailsNeverStable);check_off(f);CHECK(!has(f,"PD1"));}
 {Fake f;f.fail_after_us=0;CHECK(p03::run(f,1000)==p03::Fault::RailsAfterPor);check_off(f);}
 // 等待中途掉电要立刻停，不能等满POR才发现（加长版等2s时这一点才要紧）
 {Fake f;f.fail_after_us=int(p03::POR_US/2);CHECK(p03::run(f,1000)==p03::Fault::RailsAfterPor);check_off(f);CHECK(f.t-f.pd_at<=p03::POR_US/2+p03::POLL_US);}
 {Fake f;f.fail_after_us=int(p03::POR_US+50000);CHECK(p03::run(f,10000000)==p03::Fault::RailsDuringHold);check_off(f);}
 std::puts("p03 power_seq: 6 cases ok");
}

#include "src/ads1298.h"
#include "src/capture_guard.h"
#include <array>
#include <algorithm>
#include <cassert>
#include <cstring>
#include <iostream>
#include <vector>
using namespace v12;
struct Mock final:AdsHal {
 std::array<uint8_t,26> regs{};
 std::array<uint8_t,27> frame{};
 std::vector<uint8_t> packet;
 std::vector<uint32_t> waits;
 std::vector<int> stops;
 std::vector<std::pair<int,int>> writes; // 寄存器写入顺序（地址, 值）
 bool power_on=false,rail=true,continuous=true,started=false,capturing=false;
 int power_count=0,transfers=0,bad_read=-1;uint8_t gpio_levels=0;
 bool bad_rld=false; // 只让最后开 RLD 那次读回出错
 uint32_t elapsed=0,cancel_at=0;
 Mock(){regs[0]=0x92;frame[0]=0xca;frame[1]=0xbc;frame[2]=0xde;}
 void power(bool on)override{power_on=on;if(on)++power_count;else stops.push_back(6);}
 void pwdn(bool on)override{if(!on)stops.push_back(2);}
 void reset(bool on)override{if(!on)stops.push_back(3);}
 void clocksel(bool on)override{if(!on)stops.push_back(4);}
 void cs(bool high)override {
  if(!high){packet.clear();stops.push_back(5);return;}
  if(packet.empty())return;
  if(packet[0]==0x11)continuous=false;
  else if(packet[0]==0x10)continuous=true;
  else if(packet[0]==0x08)started=true;
  else if((packet[0]&0xe0)==0x40){assert(!continuous && packet.size()==3 && packet[1]==0);regs[packet[0]&31]=packet[2];writes.push_back({packet[0]&31,packet[2]});}
 }
 uint8_t transfer(uint8_t v)override {
  ++transfers;packet.push_back(v);
  if(continuous && started && packet[0]==0){assert(v==0 && packet.size()<=27);return frame[packet.size()-1];}
  if((packet[0]&0xe0)==0x20 && packet.size()==3){assert(!continuous && packet[1]==0);int a=packet[0]&31;return (regs[a]|(a==0x14?gpio_levels:0))^(a==bad_read || (bad_rld && a==3 && regs[3]==0xe4)?1:0);}
  return 0;
 }
 void wait(uint32_t us)override{waits.push_back(us);elapsed+=us;}
 bool session_valid()override{return !cancel_at || elapsed<cancel_at;}
 bool rails_good()override{return rail;}
 void capture(bool on)override{capturing=on;if(!on)stops.push_back(1);}
};
int main(){
 unsigned cases=0;
 {Mock h;h.gpio_levels=0xf0;Ads1298 a(h);assert(a.start(2000,Input::Test,{true,132000,300000}));++cases;}
 {Mock h;h.gpio_levels=0xf0;h.bad_read=0x14;Ads1298 a(h);assert(!a.start(2000,Input::Test,{true,132000,300000})&&a.fault==Fault::Readback);++cases;}
const BenchProof proof={true,132000,300000};
 for(BenchProof denied: {BenchProof{false,132000,300000},BenchProof{true,131999,300000},BenchProof{true,132000,0}}){Mock h;Ads1298 a(h);assert(!a.start(2000,Input::Test,denied));assert(a.fault==Fault::Locked && h.power_count==0 && h.transfers==0);++cases;}
 for(unsigned fs:{2000u,4000u})for(Input input:{Input::Test,Input::Shorted,Input::External,Input::ExternalRld}){
  const bool rld=input==Input::ExternalRld;
  Mock h;Ads1298 a(h);assert(a.start(fs,input,proof));assert(a.active && h.capturing && h.power_on);
  assert(h.regs[1]==(fs==2000?0x84:0x83));assert(h.regs[2]==(input==Input::Test?0x10:0));assert(h.regs[3]==(rld?0xe4:0xe0) && h.regs[0x16]==0x20 && h.regs[0x14]==0x0f);
  for(int ch=5;ch<=12;++ch)assert(h.regs[ch]==(input==Input::Test?5:input==Input::Shorted?1:0));
  for(int r=0xd;r<=0x11;++r)assert(h.regs[r]==(rld && r<=0xe?0xff:0));
  // RLD 只在最后一次写入打开：之前 CONFIG3 一直是 0xe0，非 RLD 模式从不写 0xe4。
  auto on=std::find(h.writes.begin(),h.writes.end(),std::make_pair(3,0xe4));
  assert(rld?on==h.writes.end()-1:on==h.writes.end());
  assert(h.waits.end()!=std::find(h.waits.begin(),h.waits.end(),132000));assert(h.waits.end()!=std::find(h.waits.begin(),h.waits.end(),300000));
  uint8_t bytes[27];int n=h.transfers;assert(a.read(bytes));assert(h.transfers-n==27 && !memcmp(bytes,h.frame.data(),27));
  h.stops.clear();a.stop();assert((h.stops==std::vector<int>{1,2,3,4,5,6}));assert(!a.active && !h.power_on && !h.capturing);++cases;
 }
 {Mock h;h.bad_rld=true;Ads1298 a(h);assert(!a.start(2000,Input::ExternalRld,proof)&&a.fault==Fault::Readback&&!h.power_on&&!h.started);++cases;}
 {Mock h;Ads1298 a(h);assert(!a.start(2000,Input(4),proof)&&a.fault==Fault::Argument&&h.power_count==0);++cases;}
 {Mock h;Ads1298 a(h);assert(!a.start(1000,Input::Test,proof)&&a.fault==Fault::Argument&&h.power_count==0);++cases;}
 {Mock h;h.rail=false;Ads1298 a(h);assert(!a.start(2000,Input::Test,proof)&&a.fault==Fault::Rails&&!h.power_on&&!a.active);++cases;}
 // 反例：0x91 是 6 通道 ADS1296（通道码不对）；0xB2 的 bit5=1（防止掩码漏掉 bit5）；0x00/0xFF 是 SPI 总线全低/全高。都必须拒绝并断电
 for(uint8_t id:{uint8_t(0x91),uint8_t(0xb2),uint8_t(0x00),uint8_t(0xff)}){Mock h;h.regs[0]=id;Ads1298 a(h);assert(!a.start(2000,Input::Test,proof)&&a.fault==Fault::Identity&&!h.power_on);++cases;}
 // 正例：类比 AFE948 读回 0x12、ADS1298R 读回 0xD2，高 2 位不参与判断
 for(uint8_t id:{uint8_t(0x12),uint8_t(0xd2)}){Mock h;h.regs[0]=id;Ads1298 a(h);assert(a.start(2000,Input::Test,proof)&&a.active&&a.fault==Fault::None);a.stop();assert(!h.power_on);++cases;}
 {Mock h;h.bad_read=0x16;Ads1298 a(h);assert(!a.start(2000,Input::Test,proof)&&a.fault==Fault::Readback&&!h.power_on);++cases;}
 {Mock h;Ads1298 a(h);assert(a.start(2000,Input::Test,proof));h.frame[0]=0;uint8_t bytes[27];assert(!a.read(bytes)&&a.fault==Fault::Frame&&!h.power_on);++cases;}
 {Mock h;uint32_t code[]={0,0x7fffff,0x800000,0xffffff};int32_t want[]={0,8388607,-8388608,-1};for(unsigned ch=0;ch<8;++ch)for(unsigned byte=0;byte<3;++byte)h.frame[3+ch*3+byte]=uint8_t(code[ch%4]>>(16-byte*8));int32_t out[8];uint32_t status=0;assert(Ads1298::decode(h.frame.data(),27,out,&status)&&status==0xcabcde);for(unsigned i=0;i<8;++i)assert(out[i]==want[i%4]);assert(!Ads1298::decode(h.frame.data(),26,out,&status));++cases;}
 for(uint32_t time:{10000u,100000u,200000u}){Mock h;h.cancel_at=time;Ads1298 a(h);assert(!a.start(2000,Input::Test,proof)&&a.fault==Fault::Cancelled&&!h.power_on&&!h.started&&!h.capturing);++cases;}
 // RevK表12的最慢首帧应被接收；旧period*4逻辑会在首帧前误停。
 assert(!capture_timeout(false,2312,2000));assert(!capture_timeout(false,1158,4000));
 assert(capture_timeout(false,10001,2000));assert(capture_timeout(true,2001,2000));assert(capture_timeout(true,1001,4000));
 assert(!uncertain_edge(true,0,0xffffffffu,500,2000));assert(uncertain_edge(true,3,1,1000,2000));assert(uncertain_edge(true,2,1,1000,2000));
 ++cases;
 std::cout<<"ADS驱动主机正反例通过："<<cases<<"；未接设备，不是物理验收\n";
}

#include "ads1298.h"
namespace v12 {
void Ads1298::stop(Fault why) {
 active=false;h.capture(false);h.pwdn(false);h.reset(false);h.clocksel(false);h.cs(false);h.power(false);fault=why;
}
void Ads1298::command(uint8_t c) {h.cs(false);h.transfer(c);h.wait(3);h.cs(true);h.wait(3);}
uint8_t Ads1298::read_reg(uint8_t address) {
 h.cs(false);h.transfer(0x20|address);h.wait(3);h.transfer(0);h.wait(3);
 uint8_t value=h.transfer(0);h.wait(3);h.cs(true);h.wait(3);return value;
}
bool Ads1298::write_checked(uint8_t address,uint8_t value) {
 h.cs(false);h.transfer(0x40|address);h.wait(3);h.transfer(0);h.wait(3);h.transfer(value);h.wait(3);h.cs(true);h.wait(3);
 const uint8_t mask=address==0x14?0x0f:0xff; // GPIO输入电平不是可写配置。
 return (read_reg(address)&mask)==(value&mask);
}
bool Ads1298::start(unsigned fs,Input input,const BenchProof &proof) {
 stop();
 // DVDD、VCAP1与参考稳定时间不能由NOT_READY代替；没有真实台架证据就保持关闭。
 if(!proof.measured || proof.por_wait_us<132000 || !proof.reference_wait_us) {fault=Fault::Locked;return false;}
 if((fs!=2000 && fs!=4000) || (input!=Input::Test && input!=Input::Shorted && input!=Input::External && input!=Input::ExternalRld)) {fault=Fault::Argument;return false;}
 if(!h.session_valid()){fault=Fault::Cancelled;return false;}
 h.power(true);
 unsigned stable=0;
 for(unsigned i=0;i<100 && stable<10;++i) {h.wait(5000);if(!h.session_valid()){stop(Fault::Cancelled);return false;}stable=h.rails_good()?stable+1:0;}
 if(stable<10) {stop(Fault::Rails);return false;}
 h.cs(true);h.clocksel(true);h.reset(true);h.pwdn(true);h.wait(proof.por_wait_us);
 if(!h.session_valid()){stop(Fault::Cancelled);return false;}
 if(!h.rails_good()){stop(Fault::Rails);return false;}
 h.reset(false);h.wait(3);h.reset(true);h.wait(10);
 command(0x11); // 上电默认连续读模式，必须退出后才访问寄存器。
 // 只比低 6 位（bit5=0、bit4=1、bit3=0、通道码 010=8 路），不看 bit7:6：TI 的 bit7:5 是器件系列（ADS1298=0x92、ADS1298R=0xD2）；
 // 类比 AFE948=0x12 出自厂家 2026-10-22 邮件答复与其手册第 69 页（Mako 读），未实测。顺带放行 TI 未定义的 0x52。
 if((read_reg(0)&0x3f)!=0x12){stop(Fault::Identity);return false;}
 uint8_t regs[26]={};
 regs[1]=fs==2000?0x84:0x83;regs[2]=input==Input::Test?0x10:0;regs[3]=0xe0;
 for(unsigned n=5;n<=12;++n)regs[n]=input==Input::Test?0x05:(input==Input::Shorted?0x01:0x00);
 regs[0x14]=0x0f;regs[0x16]=0x20;
 const bool rld=input==Input::ExternalRld;
 if(rld)regs[0xd]=regs[0xe]=0xff; // 8 路 P/N 都进 RLD 平均；PD_RLD 仍为 0，放大器未开。
 for(uint8_t a=1;a<=0x19;++a) {
  if(!h.session_valid()){stop(Fault::Cancelled);return false;}
  if(a==0x12 || a==0x13)continue; // 导联状态只读，不写入。
  if(!write_checked(a,regs[a])){stop(Fault::Readback);return false;}
 }
 h.wait(proof.reference_wait_us);
 if(!h.session_valid()){stop(Fault::Cancelled);return false;}
 if(!h.rails_good()){stop(Fault::Rails);return false;}
 // PLAN 第 4 步：参考稳定、其余配置读回后才开 RLD（CONFIG3.PD_RLD=1，RLDREF 仍用外部分压）。
 if(rld && !write_checked(3,0xe4)){stop(Fault::Readback);return false;}
 command(0x10);if(!h.session_valid()){stop(Fault::Cancelled);return false;}
 h.capture(true);command(0x08);if(!h.session_valid()){stop(Fault::Cancelled);return false;}active=true;fault=Fault::None;return true;
}
bool Ads1298::read(uint8_t frame[27]) {
 if(!active || !frame)return false;
 h.cs(false);
 for(unsigned i=0;i<27;++i)frame[i]=h.transfer(0); // DIN保持低，每帧恰好216个时钟。
 h.wait(3);h.cs(true);h.wait(3);
 if((frame[0]&0xf0)!=0xc0){stop(Fault::Frame);return false;}
 return true;
}
bool Ads1298::decode(const uint8_t *frame,size_t n,int32_t out[8],uint32_t *status) {
 if(!frame || !out || !status || n!=27 || (frame[0]&0xf0)!=0xc0)return false;
 *status=(uint32_t(frame[0])<<16)|(uint32_t(frame[1])<<8)|frame[2];
 for(unsigned i=0;i<8;++i) {unsigned j=3+i*3;uint32_t code=(uint32_t(frame[j])<<16)|(uint32_t(frame[j+1])<<8)|frame[j+2];out[i]=code&0x800000?int32_t(code)-0x1000000:int32_t(code);}
 return true;
}
}

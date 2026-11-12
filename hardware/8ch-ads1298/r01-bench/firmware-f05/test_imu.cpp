#include "src/imu.h"
#include "src/timebase.h"
#include <cassert>
#include <cstdio>
#include <map>
struct Hal:v12::ImuHal {
 bool powered=false,busy=false,ready=true,nack=false,stop_ready=true;
 uint32_t *inject_edge=nullptr;
 uint8_t reg=0,addr=0;unsigned length=0,writes=0;
 std::map<unsigned,uint8_t> registers={{0x0f,0x6a}};
 uint8_t sample[16]={3,0,0,0,0,0x80,0xff,0x7f,0xff,0xff,1,0,2,0,3,0};
 bool power(bool on)override {
  if(!on && busy && !stop_ready)return false;
  powered=on;if(!on)busy=false;return true;
 }
 void address(uint8_t a)override{addr=a;}
 bool read(uint8_t r,unsigned n)override{assert(!busy);reg=r;length=n;busy=true;return true;}
 bool write(uint8_t r,uint8_t v)override{
  assert(!busy);reg=r;length=0;registers[r]=v;++writes;busy=true;return true;
 }
 int poll(uint8_t *out,unsigned n)override{
  assert(busy);if(!ready)return 0;busy=false;assert(n==length);
  if(nack){nack=false;return -1;}
  if(n==16){memcpy(out,sample,16);if(inject_edge)++*inject_edge;return 1;}
  if(n==1){if(reg==0x12 && registers[reg]==1)registers[reg]=0;out[0]=registers[reg];}
  return 1;
 }
};
static void boot(v12::Imu &i,uint64_t &now) {
 assert(i.start(now,true));
 for(unsigned k=0;k<100 && !i.active;++k){now+=10000;i.tick(now,0,0);}
 assert(i.active && i.fault==v12::ImuFault::None);
}
int main(){
 v12::Timebase time;
 assert(time.extend(1)==1 && time.extend(2)==2);
 assert(time.extend(0xfffffffe)==0xfffffffe);
 assert(time.extend(3)==UINT64_C(0x100000003));
 assert(time.extend(4)==UINT64_C(0x100000004));
 Hal h;v12::Imu i(h);uint64_t now=UINT64_C(0xffffff00);boot(i,now);
 assert(h.registers[0x12]==0x44 && h.registers[0x0b]==0x80);
 now+=9615;i.tick(now,1,uint32_t(now));assert(h.busy && !i.pending);
 i.tick(now+500,1,uint32_t(now));assert(i.pending && i.produced==1 && i.packet[3]==2);
 for(auto b:i.packet){printf("%02x",b);}puts("");
 i.commit();assert(i.sent==1 && !i.pending);
 i.stop();assert(!i.active && !h.powered);
 boot(i,now);now+=9615;i.tick(now,1,uint32_t(now));i.tick(now+500,1,uint32_t(now));
 assert(i.packet[3]==6);i.commit();i.stop();
 // 读数中新沿：无历史FIFO，必须拒绝，不能给旧数据换上新时间。
 {Hal x;v12::Imu m(x);uint64_t t=0;boot(m,t);t+=9615;m.tick(t,1,uint32_t(t));m.tick(t+500,2,uint32_t(t+500));assert(m.fault==v12::ImuFault::Overrun && !m.pending);}
 // 两种新鲜度都要满足；XLDA未到不能冒充新加速度。
 {Hal x;v12::Imu m(x);uint64_t t=0;boot(m,t);t+=9615;uint32_t live=1;m.tick(t,live,uint32_t(t));x.inject_edge=&live;m.tick(t+500,1,uint32_t(t));assert(!m.validate_pending(live) && m.fault==v12::ImuFault::Overrun && !m.pending && m.sent==0);}
 {Hal x;v12::Imu m(x);uint64_t t=0;boot(m,t);x.sample[0]=2;t+=9615;m.tick(t,1,uint32_t(t));m.tick(t+500,1,uint32_t(t));assert(m.fault==v12::ImuFault::Stale);}
 // DMA中STOP：不停等，停止超时仍活动；晚到STOPPED后才能关电与释放。
 {Hal x;v12::Imu m(x);uint64_t t=0;boot(m,t);t+=9615;m.tick(t,1,uint32_t(t));x.stop_ready=false;m.stop();assert(m.active && x.powered && !m.start(t,true));m.tick(t+1,1,uint32_t(t));m.tick(t+6000,1,uint32_t(t));assert(m.fault==v12::ImuFault::StopTimeout && m.active);x.stop_ready=true;m.tick(t+7000,1,uint32_t(t));assert(!m.active && !x.powered && !m.start(t+8000,true));}
 // 异步读超时与NACK同样走STOP；未完成数据不得输出。
 {Hal x;v12::Imu m(x);uint64_t t=0;boot(m,t);t+=9615;m.tick(t,1,uint32_t(t));x.ready=false;x.stop_ready=false;m.tick(t+6000,1,uint32_t(t));assert(m.fault==v12::ImuFault::Timeout && m.active && !m.pending);x.stop_ready=true;m.tick(t+7000,1,uint32_t(t));assert(!m.active);}
 {Hal x;v12::Imu m(x);uint64_t t=0;boot(m,t);t+=9615;m.tick(t,1,uint32_t(t));x.nack=true;m.tick(t+500,1,uint32_t(t));assert(m.fault==v12::ImuFault::Bus && !m.pending);}
 // 对端拥塞保留一个完整包；下一沿不得静默覆盖。
 {Hal x;v12::Imu m(x);uint64_t t=0;boot(m,t);t+=9615;m.tick(t,1,uint32_t(t));m.tick(t+500,1,uint32_t(t));m.tick(t+9615,2,uint32_t(t+9615));assert(m.fault==v12::ImuFault::Overrun && m.dropped && m.sent==0);}
 {Hal x;x.registers[0x0f]=0;v12::Imu m(x);assert(m.start(0,true));m.tick(100000,0,0);m.tick(100100,0,0);assert(x.addr==0x6b);m.tick(100200,0,0);assert(m.fault==v12::ImuFault::Identity);}
 {Hal x;v12::Imu m(x);assert(m.start(0,true));m.tick(100000,0,0);x.nack=true;m.tick(100100,0,0);assert(x.addr==0x6b);uint64_t t=100100;for(unsigned k=0;k<100&&!m.active;++k){t+=10000;m.tick(t,0,0);}assert(m.active);}
 {Hal x;v12::Imu m(x);assert(m.start(0,true));uint64_t t=0;for(unsigned k=0;k<100 && m.stage!=v12::Imu::Stage::ConfigRead;++k){t+=10000;m.tick(t,0,0);}x.registers[0x12]=0;m.tick(t+1,0,0);assert(m.fault==v12::ImuFault::Readback);}
 {Hal x;v12::Imu m(x);uint64_t t=0;boot(m,t);m.tick(t+60000,0,0);assert(m.fault==v12::ImuFault::Timeout);}
 uint8_t status[64];i.status(status,true);for(auto b:status){printf("%02x",b);}puts("");
 puts("PASS: 计时回绕、IMU异步状态机、配置/新鲜度、停止/迟到/背压边界；未实物验收");
}

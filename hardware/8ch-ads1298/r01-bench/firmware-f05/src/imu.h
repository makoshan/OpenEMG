#pragma once
#include <stddef.h>
#include <stdint.h>
#include <string.h>
#include "diagnostics.h"

namespace v12 {
// 每次tick只推进一步。I2C由独立TWIM1做DMA，绝不在ADS主循环等待传输。
struct ImuHal {
 virtual ~ImuHal()=default;
 virtual bool power(bool on)=0;
 virtual void address(uint8_t value)=0;
 virtual bool read(uint8_t reg,unsigned length)=0;
 virtual bool write(uint8_t reg,uint8_t value)=0;
 // 0=未完成，1=完整完成，-1=出错；完成之前不得改DMA缓冲。
 virtual int poll(uint8_t *out,unsigned length)=0;
};
enum class ImuFault:uint8_t {None=0,Bus=1,Identity=2,Readback=3,Timeout=4,Overrun=5,Stale=6,StopTimeout=7};
struct Imu {
 static constexpr unsigned PACKET_BYTES=36,STATUS_BYTES=64;
 static constexpr uint8_t CONFIG[][2]={{0x12,0x44},{0x10,0x4c},{0x11,0x48},
                                      {0x13,0},{0x14,0},{0x0b,0x80}};
 enum class Stage {Off,PowerWait,Probe,ResetWrite,ResetRead,ConfigWrite,ConfigRead,Settle,
                   EnableWrite,EnableRead,Ready,Sample,Stopping};
 ImuHal &h;
 Stage stage=Stage::Off;
 ImuFault fault=ImuFault::None;
 bool active=false,pending=false,reconfigure=false,had_session=false;
 uint8_t chip=0,address_value=0x6a,config_index=0;
 uint32_t used_edges=0,sample_edge_us=0,next_sequence=0;
 uint64_t raw_edges=0,produced=0,sent=0,dropped=0,notify_failures=0,last_timestamp=0;
 uint64_t deadline=0,reset_deadline=0,wait_until=0,stop_deadline=0;
 uint8_t packet[PACKET_BYTES]={};
 explicit Imu(ImuHal &hal):h(hal){}

 void stop(ImuFault why=ImuFault::None) {
  if(stage==Stage::Stopping)return;
  if(pending)++dropped;
  pending=false;stop_deadline=0;
  if(why!=ImuFault::None)fault=why;
  if(h.power(false)){active=false;stage=Stage::Off;}
  else {active=true;stage=Stage::Stopping;}
 }
 bool start(uint64_t now,bool same_connection) {
  if(stage!=Stage::Off || fault!=ImuFault::None)return false;
  reconfigure=same_connection && had_session;
  chip=0;address_value=0x6a;config_index=0;used_edges=0;next_sequence=0;
  raw_edges=produced=sent=dropped=notify_failures=last_timestamp=0;
  if(!h.power(true)){fault=ImuFault::Bus;return false;}
  h.address(address_value);stage=Stage::PowerWait;wait_until=now+100000;return true;
 }
 void disconnected(){stop();had_session=false;}
 bool begin_read(uint8_t reg,unsigned length,Stage target,uint64_t now) {
  if(!h.read(reg,length)){stop(ImuFault::Bus);return false;}
  deadline=now+5000;stage=target;return true;
 }
 bool begin_write(uint8_t reg,uint8_t value,Stage target,uint64_t now) {
  if(!h.write(reg,value)){stop(ImuFault::Bus);return false;}
  deadline=now+5000;stage=target;return true;
 }
 void tick(uint64_t now,uint32_t edges,uint32_t edge_us) {
  uint8_t data[16]={};int completed=0;
  if(stage==Stage::Off)return;
  if(stage==Stage::Stopping) {
   if(h.power(false)){active=false;stage=Stage::Off;return;}
   if(!stop_deadline)stop_deadline=now+5000;
   if(now>=stop_deadline)fault=ImuFault::StopTimeout;
   return; // 停止超时仍报告活动，直到收到硬件STOPPED。
  }
  if(stage==Stage::PowerWait) {
   if(now>=wait_until)begin_read(0x0f,1,Stage::Probe,now);
   return;
  }
  if(stage==Stage::Settle) {
   if(now>=wait_until)begin_write(0x0d,2,Stage::EnableWrite,now);
   return;
  }
  if(stage==Stage::Ready) {
   raw_edges=edges;
   if(edges==used_edges) {
    if(now>=wait_until)stop(ImuFault::Timeout);
    return;
   }
   // 寄存器不保存历史样本；多沿或读数跨下一沿都不能冒充精确历史数据。
   if(uint32_t(edges-used_edges)!=1 || pending) {++dropped;stop(ImuFault::Overrun);return;}
   sample_edge_us=edge_us;used_edges=edges;
   begin_read(0x1e,16,Stage::Sample,now);return;
  }
  completed=h.poll(data,stage==Stage::Sample?16:
                        (stage==Stage::Probe || stage==Stage::ResetRead || stage==Stage::ConfigRead || stage==Stage::EnableRead)?1:0);
  if(completed==0) {
   if(now>=deadline)stop(ImuFault::Timeout);
   return;
  }
  if(stage==Stage::Probe && (completed<0 || data[0]!=0x6a)) {
   if(address_value==0x6a){address_value=0x6b;h.address(address_value);begin_read(0x0f,1,Stage::Probe,now);}
   else stop(completed<0?ImuFault::Bus:ImuFault::Identity);
   return;
  }
  if(completed<0){stop(ImuFault::Bus);return;}
  switch(stage) {
   case Stage::Probe:
    chip=data[0];reset_deadline=now+50000;begin_write(0x12,1,Stage::ResetWrite,now);break;
   case Stage::ResetWrite:begin_read(0x12,1,Stage::ResetRead,now);break;
   case Stage::ResetRead:
    if(data[0]&1) {
     if(now>=reset_deadline)stop(ImuFault::Timeout);
     else begin_read(0x12,1,Stage::ResetRead,now);
    } else begin_write(CONFIG[0][0],CONFIG[0][1],Stage::ConfigWrite,now);
    break;
   case Stage::ConfigWrite:begin_read(CONFIG[config_index][0],1,Stage::ConfigRead,now);break;
   case Stage::ConfigRead:
    if(data[0]!=CONFIG[config_index][1]){stop(ImuFault::Readback);break;}
    if(++config_index<sizeof(CONFIG)/sizeof(CONFIG[0]))
     begin_write(CONFIG[config_index][0],CONFIG[config_index][1],Stage::ConfigWrite,now);
    else {stage=Stage::Settle;wait_until=now+100000;}
    break;
   case Stage::EnableWrite:begin_read(0x0d,1,Stage::EnableRead,now);break;
   case Stage::EnableRead:
    if(data[0]!=2){stop(ImuFault::Readback);break;}
    active=true;stage=Stage::Ready;used_edges=edges;raw_edges=edges;wait_until=now+50000;break;
   case Stage::Sample: {
    raw_edges=edges;
    if(edges!=used_edges){++dropped;stop(ImuFault::Overrun);break;}
    if((data[0]&3)!=3){stop(ImuFault::Stale);break;}
    const uint32_t latency=uint32_t(now)-sample_edge_us;
    if(latency>=9000){stop(ImuFault::Stale);break;}
    // 32位ISR时间按同一个MCU扩展时钟归位；ISR延迟未测，不声称传感器精确同步。
    uint64_t stamp=(now&~UINT64_C(0xffffffff))|sample_edge_us;
    if(stamp>now)stamp-=UINT64_C(1)<<32;
    if(produced && stamp<=last_timestamp){stop(ImuFault::Stale);break;}
    memset(packet,0,sizeof(packet));packet[0]=1;packet[1]=2;packet[2]=1;
    packet[3]=produced?0:uint8_t(2|(reconfigure?4:0));
    status_le(packet+4,next_sequence++,4);status_le(packet+8,stamp,8);
    memcpy(packet+16,data+4,12);packet[28]=data[0]&3;status_le(packet+32,latency,4);
    ++produced;last_timestamp=stamp;pending=true;stage=Stage::Ready;wait_until=now+50000;break;
   }
   default:stop(ImuFault::Bus);break;
  }
 }
 bool validate_pending(uint32_t live_edges) {
  // poll复制RAM时ISR仍能发生；入口快照不足以证明读取没有跨下一沿。
  if(pending && live_edges!=used_edges){++dropped;stop(ImuFault::Overrun);return false;}
  return true;
 }
 void commit(){if(pending){pending=false;++sent;had_session=true;}}
 void status(uint8_t out[STATUS_BYTES],bool enabled) const {
  memset(out,0,STATUS_BYTES);out[0]=1;out[1]=enabled;out[2]=active;out[3]=uint8_t(fault);
  out[4]=chip;out[5]=8;status_le(out+6,1000,2);status_le(out+8,104,4);
  out[12]=1; // 时标是INT1的ISR时刻，非传感器内部时间；13=实测对齐证明，保持0。
  const uint64_t counters[]={raw_edges,produced,sent,dropped,notify_failures,last_timestamp};
  for(unsigned i=0;i<6;++i)status_le(out+16+8*i,counters[i],8);
 }
};
constexpr uint8_t Imu::CONFIG[][2];
}

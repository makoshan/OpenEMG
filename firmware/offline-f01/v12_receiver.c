#include "v12_receiver.h"
void v12_receiver_init(v12_receiver *r,int allow_real){
 if(!r)return;
 *r=(v12_receiver){0};r->allow_real=allow_real!=0;
}
void v12_receiver_disconnect(v12_receiver *r){
 if(!r)return;
 r->connected=0;r->expected=0;r->last_timestamp=0;r->synthetic=0;
}
int v12_receiver_receive(v12_receiver *r,const uint8_t *data,size_t len,uint16_t mtu,v12_packet *out){
 if(!r||!out)return V12_ARGUMENT;
 v12_packet p;
 if(v12_decode(data,len,mtu,&p)){r->malformed++;return V12_MALFORMED;}
 uint8_t synthetic=(p.flags&1u)!=0;
 if(!synthetic&&!r->allow_real)return V12_REAL_DISABLED;
 uint32_t delta=0;
 const int boundary=(p.flags&4u)!=0;
 if(boundary){
  if(!r->connected)return V12_RESTART;
  if(r->synthetic!=synthetic)return V12_SOURCE_MIX;
  if(p.timestamp_us<=r->last_timestamp)return V12_TIMESTAMP;
 }

 if(!r->connected){
  if(!(p.flags&2u))return V12_START_REQUIRED;
 }else if(!boundary){
  if(p.flags&2u)return V12_RESTART;
  if(r->synthetic!=synthetic)return V12_SOURCE_MIX;
  delta=p.sequence-r->expected;
  if(delta>=UINT32_C(0x80000000)){r->reordered++;return V12_REORDERED;}
  if(p.timestamp_us<=r->last_timestamp)return V12_TIMESTAMP;
 }
 if(!r->connected || boundary)r->sessions++;
 r->missing_samples+=delta;r->accepted_samples+=p.count;
 r->expected=p.sequence+p.count;r->last_timestamp=p.timestamp_us;
 r->synthetic=synthetic;r->connected=1;*out=p;return V12_ACCEPTED;
}

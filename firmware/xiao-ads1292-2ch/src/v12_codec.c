#include "v12_codec.h"
#include <string.h>
static unsigned capacity(uint16_t mtu){if(mtu<23||mtu>517)return 0;unsigned n=(mtu-3-V12_HEADER)/V12_FRAME;return n>V12_MAX_FRAMES?V12_MAX_FRAMES:n;}
static uint64_t getle(const uint8_t *p,unsigned n){uint64_t v=0;for(unsigned i=0;i<n;i++)v|=(uint64_t)p[i]<<(8*i);return v;}
static void putle(uint8_t *p,uint64_t v,unsigned n){for(unsigned i=0;i<n;i++)p[i]=(uint8_t)(v>>(8*i));}
int v12_decode(const uint8_t *data,size_t len,uint16_t mtu,v12_packet *out){
 if(!data||!out||mtu<23||mtu>517||len<V12_HEADER||len>(size_t)mtu-3)return -1;
 if(data[0]!=1||data[1]!=1||!data[2]||data[2]>capacity(mtu)||(data[3]&~7u)||len!=V12_HEADER+(size_t)data[2]*V12_FRAME)return -1;
 if((data[3]&4u)&&!(data[3]&2u))return -1;
 uint32_t seq=(uint32_t)getle(data+4,4);if((data[3]&2u)&&seq)return -1;
 *out=(v12_packet){data[2],data[3],seq,getle(data+8,8),data+V12_HEADER};return 0;
}
int v12_encode(const v12_packet *p,uint16_t mtu,uint8_t *data,size_t cap,size_t *written){
 if(!p||!data||!written||!p->frames||!p->count||p->count>capacity(mtu)||(p->flags&~7u)||((p->flags&2u)&&p->sequence))return -1;
 if((p->flags&4u)&&!(p->flags&2u))return -1;
 size_t len=V12_HEADER+(size_t)p->count*V12_FRAME;if(cap<len)return -1;
 data[0]=1;data[1]=1;data[2]=p->count;data[3]=p->flags;putle(data+4,p->sequence,4);putle(data+8,p->timestamp_us,8);memcpy(data+V12_HEADER,p->frames,(size_t)p->count*V12_FRAME);*written=len;return 0;
}
int32_t v12_signed24(const uint8_t p[3]){uint32_t v=((uint32_t)p[0]<<16)|((uint32_t)p[1]<<8)|p[2];return v&0x800000u?(int32_t)(v&0x7fffffu)-8388608:(int32_t)v;}

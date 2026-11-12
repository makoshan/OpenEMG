#ifndef V12_RECEIVER_H
#define V12_RECEIVER_H
#include "v12_codec.h"
typedef struct {
 uint64_t accepted_samples,missing_samples,reordered,malformed,sessions,last_timestamp;
 uint32_t expected;
 uint8_t connected,synthetic,allow_real;
} v12_receiver;
enum v12_receive_result { V12_ACCEPTED=0,V12_MALFORMED=1,V12_REAL_DISABLED=2,V12_START_REQUIRED=3,V12_RESTART=4,V12_SOURCE_MIX=5,V12_REORDERED=6,V12_TIMESTAMP=7,V12_ARGUMENT=8 };
void v12_receiver_init(v12_receiver *r,int allow_real);
void v12_receiver_disconnect(v12_receiver *r);
/* On success out borrows data. On rejection out and sample/session state stay unchanged;
   malformed/reordered diagnostic counters may increment. No heap/device access. */
int v12_receiver_receive(v12_receiver *r,const uint8_t *data,size_t len,uint16_t mtu,v12_packet *out);
#endif

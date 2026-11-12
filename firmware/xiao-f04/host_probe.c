/* 主机合成队列探针；不链接Arduino、不访问硬件。 */
#include "src/v12_stream.h"
#include <stdio.h>
#include <stdlib.h>
int main(int argc,char **argv) {
 v12_stream s;
 if(argc!=2 || v12_stream_init(&s,(unsigned)atoi(argv[1]))) return 2;
 char line[128];
 while(fgets(line,sizeof(line),stdin)) {
  char op; unsigned n; unsigned long long timestamp; int value,rc=-1;
  const uint8_t *bytes=NULL; size_t length=0;
  if(sscanf(line," %c",&op)!=1) return 3;
  if(op=='P' && sscanf(line,"P %llu %d",&timestamp,&value)==2) {
   int32_t raw[8]; for(unsigned ch=0;ch<8;++ch) raw[ch]=value+(int32_t)ch;
   rc=v12_stream_push(&s,raw,(uint64_t)timestamp);
  } else if(op=='K' && sscanf(line,"K %u",&n)==1) rc=v12_stream_skip(&s,n);
  else if(op=='N' && sscanf(line,"N %u",&n)==1) rc=v12_stream_peek(&s,(uint16_t)n,&bytes,&length);
  else if(op=='C') rc=v12_stream_commit(&s);
  else if(op=='I') rc=v12_stream_init(&s,(unsigned)atoi(argv[1]));
  printf("%d,%u,%llu,%llu,%llu,%llu,%llu,%u,%d,",rc,s.count,(unsigned long long)s.produced,
         (unsigned long long)s.ring_dropped,(unsigned long long)s.scheduler_skipped,
         (unsigned long long)s.sent_packets,(unsigned long long)s.sent_samples,s.dsp.processed,s.latest_ready);
  if(bytes) for(size_t i=0;i<length;++i) printf("%02x",bytes[i]);
  putchar('\n');
 }
 return 0;
}

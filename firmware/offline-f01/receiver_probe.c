#include "v12_receiver.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <inttypes.h>
int main(int argc,char **argv){
 if(argc!=2)return 2;
 v12_receiver r;v12_receiver_init(&r,atoi(argv[1]));char line[1100];
 while(fgets(line,sizeof(line),stdin)){
  if(line[0]=='D'){v12_receiver_disconnect(&r);continue;}
  unsigned mtu;char hex[1040];if(sscanf(line,"%u %1039s",&mtu,hex)!=2||mtu>65535)return 2;
  size_t n=strlen(hex);if(n%2||n/2>517)return 2;
  uint8_t data[517];for(size_t i=0;i<n/2;i++){unsigned x;if(sscanf(hex+2*i,"%2x",&x)!=1)return 2;data[i]=(uint8_t)x;}
  v12_packet out={0};int result=v12_receiver_receive(&r,data,n/2,(uint16_t)mtu,&out);
  if(result&&out.frames)return 3;
  printf("%d,%u,%" PRIu32 ",%" PRIu64 ",%u,%" PRIu64 ",%" PRIu64 ",%" PRIu64 ",%" PRIu64 ",%" PRIu64 "\n",
   result==0,r.connected,r.expected,r.last_timestamp,r.synthetic,r.accepted_samples,r.missing_samples,r.reordered,r.malformed,r.sessions);
 }
 return 0;
}

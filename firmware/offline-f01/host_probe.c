#include "v12_codec.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
int main(int argc,char **argv){
 if(argc!=3){return 2;}size_t n=strlen(argv[1]);if(n%2||n/2>232){return 2;}
 uint8_t data[232],out[232];for(size_t i=0;i<n/2;i++){unsigned v;if(sscanf(argv[1]+i*2,"%2x",&v)!=1)return 2;data[i]=(uint8_t)v;}
 v12_packet p;if(v12_decode(data,n/2,(uint16_t)atoi(argv[2]),&p))return 1;
 size_t written=0;if(v12_encode(&p,(uint16_t)atoi(argv[2]),out,sizeof(out),&written))return 3;
 for(size_t i=0;i<written;i++){printf("%02x",out[i]);}printf("\n");
 for(unsigned i=0;i<8;i++)printf("%d%s",v12_signed24(p.frames+3+3*i),i==7?"\n":",");
 return 0;
}

#include "src/diagnostics.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>

int main() {
 unsigned cases=0;
 volatile v12::DrdyStats s;
 v12::reset_drdy(s);assert(s.raw_edges==0 && s.min_interval_us==UINT32_MAX);++cases;
 v12::record_drdy(s,100);assert(s.raw_edges==1 && s.min_interval_us==UINT32_MAX);++cases;
 v12::record_drdy(s,600);v12::record_drdy(s,1100);assert(s.raw_edges==3 && s.min_interval_us==500);++cases;
 v12::record_drdy(s,1110);assert(s.raw_edges==4 && s.min_interval_us==10);++cases;
 v12::record_drdy(s,1610);assert(s.min_interval_us==10);++cases;
 v12::record_drdy(s,1610);assert(s.min_interval_us==0);++cases;
 v12::reset_drdy(s);v12::record_drdy(s,UINT32_MAX-99);v12::record_drdy(s,400);
 assert(s.raw_edges==2 && s.min_interval_us==500);++cases;
 s.raw_edges=UINT32_MAX;v12::record_drdy(s,900);assert(s.raw_edges==UINT64_C(0x100000000));++cases;
 v12::reset_drdy(s);assert(s.raw_edges==0 && !s.have_edge && s.min_interval_us==UINT32_MAX);++cases;
 const v12::StatusSnapshot snapshot={9,2,0,7,1,3,false,false,0xc00007,UINT64_C(0x100000003),10,4000000};
 uint8_t bytes[v12::STATUS_BYTES];memset(bytes,0xff,sizeof(bytes));v12::encode_status(bytes,snapshot);
 assert(sizeof(bytes)==64 && bytes[0]==9 && bytes[8]==2 && bytes[24]==7 && bytes[32]==1);
 assert(bytes[40]==3 && bytes[41]==0 && bytes[42]==0 && bytes[43]==1);
 assert(bytes[44]==7 && bytes[46]==0xc0 && bytes[47]==0);
 assert(bytes[48]==3 && bytes[52]==1 && bytes[56]==10);
 assert(bytes[60]==0 && bytes[61]==9 && bytes[62]==61 && bytes[63]==0);++cases;
 fprintf(stderr,"PASS: DRDY与状态编码 %u 项（均为主机合成输入）\n",cases);
 // 把真实固件编码函数的输出交给Python接收端，避免两边都只测自己的假样本。
 for(unsigned i=0;i<sizeof(bytes);++i)printf("%02x",bytes[i]);
 puts("");                                        // 换行单独一行：同一行写在 for 后面，g++ -Werror=misleading-indentation 会报错（CI 用 Linux g++）
 return 0;
}

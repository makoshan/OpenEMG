#include "src/v12_stream.h"
#include <assert.h>
#include <stdio.h>
int main(void){
 v12_stream s;const uint8_t *b;size_t n;int32_t raw[8]={0};
 assert(!v12_stream_init(&s,2000));
 for(unsigned mode=0;mode<3;++mode){
  if(mode)assert(!v12_stream_restart(&s,2000));
  assert(!v12_stream_push(&s,raw,1000+mode*10000));
  assert(!v12_stream_peek(&s,247,&b,&n));
  assert(b[3]==(mode?6:2)); // 真实来源；配置切换首包增加bit2。
  for(size_t i=0;i<n;++i){printf("%02x",b[i]);}puts("");
  assert(!v12_stream_peek(&s,247,&b,&n));assert(b[3]==(mode?6:2));
  assert(!v12_stream_commit(&s));
 }
 assert(!v12_stream_restart(&s,2000));assert(!v12_stream_restart(&s,2000));
 assert(s.reconfigure); // STOP之后再启动也不能丢失边界。
 return 0;
}

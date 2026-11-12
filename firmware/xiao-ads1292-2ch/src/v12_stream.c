#include "v12_stream.h"
#include <string.h>

int v12_stream_init(v12_stream *s,unsigned fs) {
 if(!s) return V12_STREAM_ARGUMENT;
 memset(s,0,sizeof(*s));
 if(v12_dsp_init(&s->dsp,fs,0)) return V12_STREAM_ARGUMENT;
 s->fs=fs;
 return V12_STREAM_OK;
}

/* 配置重启丢弃旧队列；标记随首包重试保留，直到完整发送成功。 */
int v12_stream_restart(v12_stream *s,unsigned fs) {
 if(!s)return V12_STREAM_ARGUMENT;
 int boundary=s->started || s->reconfigure;
 int result=v12_stream_init(s,fs);
 if(!result)s->reconfigure=boundary;
 return result;
}

int v12_stream_push(v12_stream *s,const int32_t raw[8],uint64_t timestamp) {
 unsigned ch;
 if(!s || !s->fs || !raw) return V12_STREAM_ARGUMENT;
 if(v12_dsp_frame(&s->dsp,raw,s->latest_filtered,&s->latest_ready)) return V12_STREAM_ARGUMENT;
 uint32_t sequence=s->next_sequence++;
 ++s->produced;
 /* 满队列丢新样本，保留未发送的会话首包/重试包；序号仍递增。 */
 if(s->count==V12_STREAM_RING) { ++s->ring_dropped; return V12_STREAM_OK; }
 v12_sample *sample=&s->ring[(s->head+s->count)%V12_STREAM_RING];
 sample->sequence=sequence; sample->timestamp=timestamp;
 sample->frame[0]=0xc0; sample->frame[1]=0; sample->frame[2]=0;
 for(ch=0;ch<8;++ch) {
  uint32_t code=(uint32_t)raw[ch]&0xffffffu;
  sample->frame[3+ch*3]=(uint8_t)(code>>16);
  sample->frame[4+ch*3]=(uint8_t)(code>>8);
  sample->frame[5+ch*3]=(uint8_t)code;
 }
 ++s->count;
 return V12_STREAM_OK;
}

int v12_stream_skip(v12_stream *s,uint32_t count) {
 if(!s || !s->fs || (!s->produced && count)) return V12_STREAM_ARGUMENT;
 if(!count) return V12_STREAM_OK;
 s->next_sequence+=count; s->scheduler_skipped+=count;
 v12_dsp_reset(&s->dsp); s->latest_ready=0;
 return V12_STREAM_OK;
}

int v12_stream_peek(v12_stream *s,uint16_t mtu,const uint8_t **bytes,size_t *length) {
 if(!s || !s->fs || !bytes || !length) return V12_STREAM_ARGUMENT;
 if(mtu<46 || mtu>517) return V12_STREAM_MTU;
 if(s->pending_len) {
  if(s->pending_len>(size_t)mtu-3) return V12_STREAM_MTU;
  *bytes=s->pending; *length=s->pending_len; return V12_STREAM_OK;
 }
 if(!s->count) return V12_STREAM_EMPTY;
 unsigned capacity=(mtu-3-V12_HEADER)/V12_FRAME;
 if(capacity>V12_MAX_FRAMES) capacity=V12_MAX_FRAMES;
 unsigned count=s->count<capacity?s->count:capacity;
 unsigned i;
 /* F01包内没有逐帧序号，不能跨队列缺口拼包。 */
 for(i=1;i<count;++i) {
  const v12_sample *previous=&s->ring[(s->head+i-1)%V12_STREAM_RING];
  const v12_sample *current=&s->ring[(s->head+i)%V12_STREAM_RING];
  if(current->sequence!=previous->sequence+1u || current->timestamp<=previous->timestamp || current->timestamp-previous->timestamp>1300000u/s->fs) { count=i; break; }
 }
 uint8_t frames[V12_MAX_FRAMES*V12_FRAME];
 for(i=0;i<count;++i) memcpy(frames+i*V12_FRAME,s->ring[(s->head+i)%V12_STREAM_RING].frame,V12_FRAME);
 const v12_sample *first=&s->ring[s->head];
 v12_packet packet={(uint8_t)count,(uint8_t)(s->started?0u:(2u|(s->reconfigure?4u:0u))),first->sequence,first->timestamp,frames};
 size_t written;
 if(v12_encode(&packet,mtu,s->pending,sizeof(s->pending),&written)) return V12_STREAM_ARGUMENT;
 s->pending_count=count; s->pending_len=written;
 *bytes=s->pending; *length=written;
 return V12_STREAM_OK;
}

int v12_stream_commit(v12_stream *s) {
 if(!s || !s->pending_len || s->pending_count>s->count) return V12_STREAM_ARGUMENT;
 s->head=(s->head+s->pending_count)%V12_STREAM_RING;
 s->count-=s->pending_count; s->sent_samples+=s->pending_count; ++s->sent_packets;
 s->pending_count=0; s->pending_len=0; s->started=1;
 return V12_STREAM_OK;
}

"""16 位差分打包（协议 2/3），只在 build.py --pack16 时叠加；默认构建与 check_flow 不变。

为什么：2k×8 路×24 位要 250 包/s，R01 经接收器实测每秒最多约 274 包（7.5 ms 每事件约 2.05 包），余量约 10%。
做法（无损）：每包首帧照发 27 字节（3 字节状态 + 8×24 位），之后每帧只发 8 个 int16 差值（对上一帧）。
差值超出 int16、状态字变化、序号/时间不连续时提前收包，下一包重新带完整首帧，所以不丢精度、不造样本。
copies=2 是 C07 负载仿真：首帧多带一份 24 字节、每个差值帧发两份，字节数等于 16 路；主机核对两份一致。
包头版本号：2 = 一份，3 = 两份。最大通知 244 字节（MTU 247）。
"""

def once(text, old, new):
    if text.count(old) != 1:
        raise SystemExit('pack16 补丁锚点变化：' + old[:70])
    return text.replace(old, new)


PEEK = r'''
/* pack16（firmware-f05-ble-dout/pack16_patch.py）：首帧完整、后续帧 int16 差值；放不下就提前收包，无损。 */
#define V12_PACK16_ANCHOR (V12_HEADER+V12_FRAME+(V12_PACK16_COPIES-1)*24u)
#define V12_PACK16_STEP (16u*V12_PACK16_COPIES)
unsigned v12_pack16_capacity(uint16_t mtu) {
 size_t room=(size_t)mtu-3;if(room>V12_STREAM_PACKET)room=V12_STREAM_PACKET;
 return room<V12_PACK16_ANCHOR?0u:1u+(unsigned)((room-V12_PACK16_ANCHOR)/V12_PACK16_STEP);
}
int v12_stream_peek(v12_stream *s,uint16_t mtu,const uint8_t **bytes,size_t *length) {
 if(!s || !s->fs || !bytes || !length) return V12_STREAM_ARGUMENT;
 if(mtu<46 || mtu>517) return V12_STREAM_MTU;
 if(s->pending_len) {
  if(s->pending_len>(size_t)mtu-3) return V12_STREAM_MTU;
  *bytes=s->pending; *length=s->pending_len; return V12_STREAM_OK;
 }
 if(!s->count) return V12_STREAM_EMPTY;
 unsigned capacity=v12_pack16_capacity(mtu);
 if(!capacity) return V12_STREAM_MTU;
 const v12_sample *first=&s->ring[s->head];
 uint8_t *d=s->pending;unsigned i,c,k;
 d[0]=1u+V12_PACK16_COPIES;d[1]=1;d[3]=(uint8_t)(s->started?0u:(2u|(s->reconfigure?4u:0u)));
 for(k=0;k<4;++k)d[4+k]=(uint8_t)(first->sequence>>(8*k));
 for(k=0;k<8;++k)d[8+k]=(uint8_t)(first->timestamp>>(8*k));
 size_t len=V12_HEADER;memcpy(d+len,first->frame,V12_FRAME);len+=V12_FRAME;
 for(c=1;c<V12_PACK16_COPIES;++c){memcpy(d+len,first->frame+3,24);len+=24;}
 unsigned count=1;
 for(i=1;i<capacity && i<s->count;++i) {
  const v12_sample *previous=&s->ring[(s->head+i-1)%V12_STREAM_RING];
  const v12_sample *current=&s->ring[(s->head+i)%V12_STREAM_RING];
  /* 和 v1 一样不跨序号/时间缺口拼包；另外状态字变了或差值超 int16 也收包。 */
  if(current->sequence!=previous->sequence+1u || current->timestamp<=previous->timestamp || current->timestamp-previous->timestamp>1300000u/s->fs) break;
  if(memcmp(current->frame,first->frame,3)) break;
  int16_t delta[8];int fits=1;
  for(k=0;k<8;++k){int32_t v=v12_signed24(current->frame+3+3*k)-v12_signed24(previous->frame+3+3*k);if(v<-32768||v>32767){fits=0;break;}delta[k]=(int16_t)v;}
  if(!fits) break;
  for(c=0;c<V12_PACK16_COPIES;++c)for(k=0;k<8;++k){d[len++]=(uint8_t)((uint16_t)delta[k]);d[len++]=(uint8_t)((uint16_t)delta[k]>>8);}
  ++count;
 }
 d[2]=(uint8_t)count;
 s->pending_count=count; s->pending_len=len;
 *bytes=s->pending; *length=len;
 return V12_STREAM_OK;
}
'''


def apply(out, copies):
    if copies not in (1, 2):
        raise SystemExit('pack16 只支持 1 或 2 份')
    h = out / 'src/v12_stream.h'
    text = once(h.read_text(), '#define V12_STREAM_PACKET (V12_HEADER+V12_MAX_FRAMES*V12_FRAME)',
                f'#define V12_STREAM_PACKET 244u  /* pack16：MTU 247 的最大通知 */\n#define V12_PACK16_COPIES {copies}u')
    text = once(text, 'int v12_stream_commit(v12_stream *s);', 'int v12_stream_commit(v12_stream *s);\nunsigned v12_pack16_capacity(uint16_t mtu);')
    h.write_text(text)
    c = out / 'src/v12_stream.c'
    text = c.read_text()
    start = text.index('int v12_stream_peek(')
    end = text.index('int v12_stream_commit(', start)
    c.write_text(text[:start] + PEEK.lstrip('\n') + '\n' + text[end:])
    m = out / 'src/main.cpp'
    text = once(m.read_text(), r'\"protocol\":1,', rf'\"protocol\":{1 + copies},\"pack16_copies\":{copies},')
    m.write_text(text)
    f = out / 'src/flow_control.h'
    # 攒满一包（13 帧或 6 帧）再发，否则仍按 8 帧发包，包数省不下来。
    f.write_text(once(f.read_text(), 'stream.count<V12_MAX_FRAMES)return;', 'stream.count<v12_pack16_capacity(link_mtu))return;'))

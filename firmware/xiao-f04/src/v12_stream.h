#ifndef V12_STREAM_H
#define V12_STREAM_H
#include "../../offline-f01/v12_codec.h"
#include "../../dsp-f03/v12_dsp.h"
#define V12_STREAM_RING 128u
#define V12_STREAM_PACKET (V12_HEADER+V12_MAX_FRAMES*V12_FRAME)
typedef struct { uint32_t sequence; uint64_t timestamp; uint8_t frame[V12_FRAME]; } v12_sample;
typedef struct {
 v12_dsp dsp;
 v12_sample ring[V12_STREAM_RING];
 uint8_t pending[V12_STREAM_PACKET];
 float latest_filtered[8];
 unsigned fs, head, count, pending_count;
 size_t pending_len;
 uint32_t next_sequence;
 uint64_t produced, ring_dropped, scheduler_skipped, sent_samples, sent_packets;
 int started, latest_ready;
} v12_stream;
enum { V12_STREAM_OK=0, V12_STREAM_ARGUMENT=-1, V12_STREAM_MTU=-2, V12_STREAM_EMPTY=-3 };
int v12_stream_init(v12_stream *s,unsigned fs);
int v12_stream_push(v12_stream *s,const int32_t raw[8],uint64_t timestamp);
int v12_stream_skip(v12_stream *s,uint32_t count);
/* peek借用缓存；只有一次完整notify成功才commit，失败时重试同一字节串。 */
int v12_stream_peek(v12_stream *s,uint16_t mtu,const uint8_t **bytes,size_t *length);
int v12_stream_commit(v12_stream *s);
#endif

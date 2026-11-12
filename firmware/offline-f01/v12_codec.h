#ifndef V12_CODEC_H
#define V12_CODEC_H
#include <stddef.h>
#include <stdint.h>
#define V12_HEADER 16u
#define V12_FRAME 27u
#define V12_MAX_FRAMES 8u
typedef struct { uint8_t count,flags; uint32_t sequence; uint64_t timestamp_us; const uint8_t *frames; } v12_packet;
int v12_decode(const uint8_t *data,size_t len,uint16_t mtu,v12_packet *out);
int v12_encode(const v12_packet *p,uint16_t mtu,uint8_t *data,size_t cap,size_t *written);
int32_t v12_signed24(const uint8_t p[3]);
#endif

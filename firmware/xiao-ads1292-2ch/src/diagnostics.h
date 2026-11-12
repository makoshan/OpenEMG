#pragma once
#include <stddef.h>
#include <stdint.h>

namespace v12 {
// ISR只记原始下降沿；即使本帧最终因假沿被拒，也保留诊断。不是逻辑分析仪实测。
struct DrdyStats {
 uint64_t raw_edges;
 uint32_t last_us,min_interval_us;
 bool have_edge;
};
inline void reset_drdy(volatile DrdyStats &s) {
 s.raw_edges=0;s.last_us=0;s.min_interval_us=UINT32_MAX;s.have_edge=false;
}
inline void record_drdy(volatile DrdyStats &s,uint32_t now) {
 if(s.have_edge) {
  const uint32_t interval=now-s.last_us; // 无符号差支持micros的32位回绕。
  if(interval<s.min_interval_us)s.min_interval_us=interval;
 }
 s.last_us=now;s.have_edge=true;s.raw_edges=s.raw_edges+1;
}
struct StatusSnapshot {
 uint64_t produced,ring_dropped,scheduler_skipped,sent_samples,notify_failures;
 uint8_t fault;
 bool active,bench_measured;
 uint32_t ads_status;
 uint64_t drdy_raw_edges;
 uint32_t drdy_min_interval_us,spi_hz;
};
static constexpr size_t STATUS_BYTES=64;
inline void status_le(uint8_t *p,uint64_t value,unsigned width) {
 for(unsigned b=0;b<width;++b)p[b]=uint8_t(value>>(8*b));
}
inline void encode_status(uint8_t out[STATUS_BYTES],const StatusSnapshot &s) {
 const uint64_t counts[]={s.produced,s.ring_dropped,s.scheduler_skipped,s.sent_samples,s.notify_failures};
 for(unsigned f=0;f<5;++f)status_le(out+f*8,counts[f],8);
 out[40]=s.fault;out[41]=s.active;out[42]=s.bench_measured;out[43]=1;
 status_le(out+44,s.ads_status,4);
 status_le(out+48,s.drdy_raw_edges,8);
 status_le(out+56,s.drdy_min_interval_us,4);
 status_le(out+60,s.spi_hz,4);
}
}

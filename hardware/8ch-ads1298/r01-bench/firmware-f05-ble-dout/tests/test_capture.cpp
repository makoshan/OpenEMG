// 直接执行固件main.cpp中的采集、故障、STOP与会话代码；替身仅替硬件/BLE边界。
#include "../src/main.cpp"
#include <cassert>
#include <cstdio>
static void fresh() {
 p0 = {}; p1.IN = 0; p1.DETECTMODE = 0; p1.LATCH.value = 0;
 for (auto &c : p1.PIN_CNF) c = 0;
 power_reg = {}; mock_us = 1000; mock_dma_us = 110; mock_after_dma_us = 0; mock_after_dma = false;
 mock_subscribed = true; mock_dma_calls = mock_hvx_calls = 0; mock_hvx_rc = NRF_SUCCESS;
 link_handle = arm_handle = 1; link_epoch = arm_epoch = observed_epoch = 1; link_mtu = 247;
 requested = 0; request_epoch = 1; draining = false; next_status = 10000000;
 v12_stream_init(&stream, 2000); ads.active = true; ads.fault = v12::Fault::None;
 board.spi_on = true; armed = false; sense(true); armed = true;
 baseline = true; saw_high = have_frame = false; low_before = mock_us; started_us = mock_us;
 observed_edges = notify_failures = 0; min_interval = UINT32_MAX;
}
static void candidate(uint32_t at, uint32_t low) {
 mock_us = at; low_before = low; p1.LATCH.value |= mask(); p1.IN = 0; poll_frame();
}
static void add_frame() { int32_t raw[8] = {}; assert(v12_stream_push(&stream, raw, 1000 + stream.count * 500) == 0); }
int main() {
 fresh(); candidate(1500,1490); assert(ads.active && stream.produced == 1 && mock_dma_calls == 1); assert(!(p1.LATCH.value & mask()));
 fresh(); candidate(1500,1000); assert(!ads.active && stream.produced == 0 && mock_dma_calls == 0); // DMA前抢占
 fresh(); mock_dma_us = 500; candidate(1500,1490); assert(!ads.active && !stream.produced); // DMA中抢占
 fresh(); mock_after_dma_us = 500; candidate(1500,1490); assert(!ads.active && !stream.produced); // 重布防前抢占
 fresh(); candidate(2500,1000); assert(!ads.active && !stream.produced); // LATCH合并多次不能变一帧
 fresh(); have_frame = true; last_observed = 1000; mock_us = 3100; poll_frame(); assert(ads.fault == v12::Fault::Timeout);
 fresh(); for (unsigned i=0;i<V12_STREAM_RING;++i) add_frame(); candidate(1500,1490); assert(ads.fault==v12::Fault::Overrun && stream.produced==128 && stream.ring_dropped==1);
 fresh(); p1.DETECTMODE = 7; sense(false); p1.DETECTMODE = 7; p1.PIN_CNF[14] = 1; armed = false; sense(true); armed = true;
 ads.stop(); assert(!armed && p1.DETECTMODE == 7 && (p1.PIN_CNF[14] & 3) == 1); // SENSE/DETECTMODE恢复
 fresh(); add_frame(); fail(v12::Fault::Frame); assert(draining && ads.fault==v12::Fault::Frame);
 requested = 4; loop(); assert(ads.fault==v12::Fault::Frame && stream.sent_samples==1 && !draining); // 故障后STOP尾包
 fresh(); add_frame(); requested = 4; loop(); assert(!ads.active && !draining && stream.sent_samples==1 && ads.fault==v12::Fault::None);
 fresh(); for(unsigned i=0;i<8;++i)add_frame(); mock_hvx_rc = 19; requested=4; loop(); assert(draining && stream.sent_samples==0 && stream.count==8);
 mock_us += 1000001; loop(); assert(!draining && ads.fault==v12::Fault::Overrun); // 通知持续背压
 fresh(); power_reg.USBREGSTATUS = 1; loop(); assert(!ads.active && ads.fault==v12::Fault::Cancelled); // USB接入关断
 fresh(); uint8_t ext[]={'E','X','T','1'}; control_write(1,nullptr,ext,4); loop(); assert(!ads.active && ads.fault==v12::Fault::Argument);
 fresh(); add_frame(); link_handle=BLE_CONN_HANDLE_INVALID; ++link_epoch; loop(); assert(!ads.active && stream.count==0);
 link_handle=2; ++link_epoch; loop(); assert(!ads.active && stream.produced==0); // 重连不自动续接
 fresh(); mock_subscribed=false; loop(); assert(!ads.active); // 取消订阅关断
 fresh(); setup(); assert(!mock_metadata.empty() && mock_metadata.size()<512);
 printf("META:%s\n",mock_metadata.c_str());
 puts("实际采集状态机16组通过（硬件/BLE替身），未连接设备。");
}

// 直接编译生成的main.cpp；GPIO/SPI/BLE/时钟边界由离线替身提供。
#include "main.cpp"
#include <cassert>
static void fresh(){
 mock_stop_race=false;mock_stop_hook=nullptr;mock_us=1000;mock_subscribed=true;mock_hvx_rc=0;mock_hvx_calls=0;
 link_handle=arm_handle=1;link_epoch=observed_epoch=arm_epoch=1;link_mtu=247;
 requested_mode=0;request_epoch=1;next_status=10000000;
 v12_stream_init(&stream,2000);ads.active=true;ads.fault=v12::Fault::None;
 isr_w=isr_r=0;isr_gap=isr_overflow=isr_rails=isr_have=false;
 v12::reset_drdy(drdy_stats);flow_reset_metrics();flow_phase=FlowPhase::Running;
 have_edge=true;last_edge_us=mock_us;
}
static void frames(unsigned n){
 for(unsigned i=0;i<n;++i){mock_us=isr_have?isr_last+500:mock_us+500;on_dout_fall();}
}
static void done(unsigned n){
 ble_evt_t e={};e.header.evt_id=BLE_GATTS_EVT_HVN_TX_COMPLETE;
 e.evt.common_evt.conn_handle=1;e.evt.gatts_evt.params.hvn_tx_complete.count=n;ble_event(&e);
}
int main(){
 fresh();frames(3);requested_mode=4;loop();
 assert(!ads.active && flow_phase==FlowPhase::Draining);
 assert(stream.produced==3 && stream.sent_samples==3 && isr_w==3 && flow_hvn_pending==1);
 done(1);loop();assert(flow_phase==FlowPhase::Stopped && stream.produced==3);
 requested_mode=4;loop();assert(stream.sent_samples==3 && ads.fault==v12::Fault::None);
 flow_status_update();assert(mock_status.size()==136 && mock_status[43]==2);
 fresh();frames(3);isr_gap=true;requested_mode=4;loop();assert(ads.fault==v12::Fault::Overrun);
 fresh();mock_stop_hook=[](){isr_gap=true;};mock_stop_race=true;requested_mode=4;loop();
 assert(ads.fault==v12::Fault::Overrun); // 标志初读与摘中断之间发生故障也必须锁住。
 fresh();flow_stop();flow_stop(v12::Fault::Frame);assert(ads.fault==v12::Fault::Frame);
 flow_stop(v12::Fault::Cancelled);assert(ads.fault==v12::Fault::Frame);
 fresh();frames(8);flow_stage_frames();mock_hvx_rc=NRF_ERROR_RESOURCES;
 flow_notify(1,1,true);assert(flow_resources==1 && stream.count==8);
 flow_notify(1,1,true);assert(mock_hvx_calls==1); // 资源失败不忙重试
 mock_us+=1001;mock_hvx_rc=0;flow_notify(1,1,true);assert(flow_hvn_pending==1 && stream.sent_samples==8);
 frames(8);flow_stage_frames();mock_hvx_rc=NRF_ERROR_RESOURCES;flow_notify(1,1,true);
 mock_hvx_rc=0;mock_us+=2000;flow_notify(1,1,true);assert(stream.count==8); // 有在途包必须等完成事件
 done(1);flow_notify(1,1,true);assert(!stream.count && flow_hvn_pending==1);
 // 以实际226丢帧那次需要的354帧积压为量级，模拟400帧背压后恢复。
 fresh();mock_hvx_rc=NRF_ERROR_RESOURCES;
 for(unsigned i=0;i<50;++i){frames(8);flow_stage_frames();flow_notify(1,1,true);}
 assert(stream.produced==400 && stream.count==400 && stream.ring_dropped==0);
 flow_stop();mock_hvx_rc=0;mock_us+=1001;
 for(unsigned i=0;i<50;++i){flow_notify(1,1,true);done(1);}
 loop();assert(flow_phase==FlowPhase::Stopped && stream.sent_samples==400 && !stream.count);
 fresh();frames(7);flow_stage_frames();flow_notify(1,1,true);assert(!mock_hvx_calls);
 frames(1);flow_stage_frames();flow_notify(1,1,true);assert(mock_hvx_calls==1);
 fresh();for(unsigned i=0;i<V12_STREAM_RING;++i){int32_t raw[8]={};assert(v12_stream_push(&stream,raw,i*500)==0);}
 frames(4);flow_stage_frames();assert(isr_r==0 && stream.ring_dropped==0 && stream.produced==V12_STREAM_RING);
 // 队列满时 STOP：按实测最差 222 包/s（每包 4.5 ms）排空，必须在 FLOW_DRAIN_US 内到 Stopped，否则队列选大了。
 fresh();for(unsigned i=0;i<V12_STREAM_RING;++i){int32_t raw[8]={};assert(v12_stream_push(&stream,raw,i*500)==0);}
 flow_stop();
 for(unsigned i=0;i<V12_STREAM_RING/8+4 && flow_phase==FlowPhase::Draining;++i){loop();if(flow_hvn_pending)done(1);mock_us+=4505;}
 loop();assert(flow_phase==FlowPhase::Stopped && stream.sent_samples==V12_STREAM_RING && ads.fault==v12::Fault::None);
 fresh();frames(17);requested_mode=4;loop();assert(ads.fault==v12::Fault::Overrun && stream.ring_dropped==0);
 fresh();frames(8);flow_stage_frames();flow_notify(1,1,true);flow_stop();
 mock_us+=FLOW_DRAIN_US+1;loop();assert(flow_phase==FlowPhase::Incomplete && flow_hvn_pending==1);
 requested_mode=2;loop();assert(flow_phase==FlowPhase::Incomplete && flow_hvn_pending==1 && stream.produced==8);
 fresh();done(1);loop();assert(flow_phase==FlowPhase::Incomplete && ads.fault==v12::Fault::Overrun);
 fresh();frames(2);isr_ring[0].frame[0]=0;requested_mode=4;loop();assert(ads.fault==v12::Fault::Frame && flow_rejected==1);
 fresh();frames(2);link_handle=BLE_CONN_HANDLE_INVALID;++link_epoch;loop();
 assert(flow_phase==FlowPhase::Incomplete && isr_w==2);
 link_handle=2;++link_epoch;loop();assert(flow_phase==FlowPhase::Idle && !isr_w && !stream.produced);
 fresh();mock_subscribed=false;loop();assert(flow_phase==FlowPhase::Incomplete && !ads.active);
 fresh();setup();assert(mock_metadata.find("stop_snapshot")!=std::string::npos && mock_metadata.size()<512);
 puts("PASS: 实际DOUT固件状态机17组：STOP保计数/首故障、尾包与完成事件、资源背压、满队列、满队列限时排空、异常重启、断连；未接设备");
}

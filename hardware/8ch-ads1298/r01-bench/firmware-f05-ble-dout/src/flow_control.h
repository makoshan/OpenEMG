#pragma once
// 只供R01蓝牙DOUT副本使用。共享F05与其默认硬件锁不改。
static_assert(MAKO_V12_IMU_ENABLED == 0, "本轮只验证ADC，不混用IMU通知队列");
enum class FlowPhase : uint32_t { Idle, Running, Draining, Stopped, Incomplete };
static FlowPhase flow_phase=FlowPhase::Idle;
static constexpr size_t FLOW_STATUS_BYTES=136;
static constexpr uint32_t FLOW_DRAIN_US=2000000u;
static volatile uint32_t flow_hvn_pending=0,flow_hvn_done=0;
static volatile bool flow_hvn_blocked=false;
static uint32_t flow_stop_us=0,flow_last_loop=0,flow_max_loop_gap=0,flow_ring_peak=0;
static uint32_t flow_last_hvx_error=0,flow_rejected=0,flow_last_send=0,flow_max_send_gap=0,flow_retry_us=0;
static uint64_t flow_resources=0,flow_other_errors=0;
static bool flow_terminal=false;
static volatile bool flow_credit_error=false;
static void status_update();
static v12::Fault flow_first_fault(v12::Fault why) {return ads.fault==v12::Fault::None?why:ads.fault;}

static void flow_stop(v12::Fault why=v12::Fault::None) {
 // 重复STOP不能清故障、清队列或延长已经超时的排空。
 if(ads.fault==v12::Fault::None && why!=v12::Fault::None)ads.fault=why;
 if(flow_phase==FlowPhase::Draining || flow_terminal)return;
 ads.stop(flow_first_fault(why));running=false;joint_mode=false;pending_request=0;imu_stop();
 // 先摘D9中断停止生产者，再折入稳定的ISR标志，不能在读标志与摘中断之间漏记故障。
 if(ads.fault==v12::Fault::None) {
  if(isr_rails)ads.fault=v12::Fault::Rails;
  else if(isr_gap || isr_overflow)ads.fault=v12::Fault::Overrun;
 }
 flow_stop_us=v12::timer_us(2);flow_phase=FlowPhase::Draining;
}
static void flow_abort(v12::Fault why) {
 ads.stop(flow_first_fault(why));running=false;joint_mode=false;pending_request=0;imu_stop();
 flow_phase=FlowPhase::Incomplete;flow_terminal=true;
}
static void flow_reset_metrics() {
 uint32_t m=__get_PRIMASK();__disable_irq();
 flow_hvn_pending=flow_hvn_done=0;flow_hvn_blocked=false;flow_credit_error=false;isr_peak=0;
 __set_PRIMASK(m);
 flow_resources=flow_other_errors=0;flow_last_hvx_error=flow_rejected=0;
 flow_last_loop=v12::timer_us(2);flow_max_loop_gap=flow_ring_peak=0;
 flow_last_send=flow_max_send_gap=flow_retry_us=0;flow_terminal=false;notify_failures=0;
}
static void flow_tx_complete(uint16_t count) {
 // Bluefruit同步事件回调运行在BLE任务；主循环提交区用vTaskSuspendAll隔离它。
 flow_hvn_done+=count;
 if(count>flow_hvn_pending) {flow_credit_error=true;return;}
 flow_hvn_pending-=count;flow_hvn_blocked=false;
}
static void flow_status_update() {
 uint32_t m=__get_PRIMASK();__disable_irq();
 const uint64_t edges=drdy_stats.raw_edges;
 const uint32_t interval=drdy_stats.min_interval_us,w=isr_w,r=isr_r,peak=isr_peak;
 const uint32_t hvn_pending=flow_hvn_pending,hvn_done=flow_hvn_done;
 __set_PRIMASK(m);
 const v12::StatusSnapshot snapshot={stream.produced,stream.ring_dropped,stream.scheduler_skipped,
  stream.sent_samples,notify_failures,uint8_t(ads.fault),ads.active || flow_phase==FlowPhase::Draining,
  bool(MAKO_BENCH_MEASURED),ads_status,edges,interval,MAKO_V12_SPI_HZ};
 uint8_t bytes[FLOW_STATUS_BYTES]={};v12::encode_status(bytes,snapshot);bytes[43]=2;
 v12::status_le(bytes+64,w,8);v12::status_le(bytes+72,w-r,4);
 v12::status_le(bytes+76,stream.count,4);v12::status_le(bytes+80,hvn_pending,4);
 v12::status_le(bytes+84,flow_ring_peak,4);v12::status_le(bytes+88,peak,4);
 v12::status_le(bytes+92,flow_max_loop_gap,4);v12::status_le(bytes+96,flow_resources,8);
 v12::status_le(bytes+104,flow_other_errors,8);v12::status_le(bytes+112,hvn_done,8);
 v12::status_le(bytes+120,flow_last_hvx_error,4);v12::status_le(bytes+124,flow_rejected,4);
 v12::status_le(bytes+128,uint32_t(flow_phase),4);v12::status_le(bytes+132,flow_max_send_gap,4);
 status_chr.write(bytes,sizeof(bytes));
}
static void flow_stage_frames() {
 // 每轮最多8帧，随后让发送端推进；满队列时保留ISR原帧，不调用会丢新帧的push。
 for(unsigned n=0;n<8 && isr_r!=isr_w && stream.count<V12_STREAM_RING;++n) {
  const IsrFrame &f=isr_ring[isr_r%ISR_RING];int32_t raw[8];
  if(!v12::Ads1298::decode(f.frame,27,raw,&ads_status)) {
   ++isr_r;++flow_rejected;flow_stop(v12::Fault::Frame);return;
  }
  uint64_t current=clock_us(),stamp=(current&~UINT64_C(0xffffffff))|f.t;
  if(stamp>current)stamp-=UINT64_C(1)<<32;
  const unsigned slot=(stream.head+stream.count)%V12_STREAM_RING;
  if(v12_stream_push(&stream,raw,stamp)!=V12_STREAM_OK){flow_abort(v12::Fault::Frame);return;}
  memcpy(stream.ring[slot].frame,f.frame,27);last_edge_us=f.t;have_edge=true;
  __DMB();++isr_r;
  if(stream.count>flow_ring_peak)flow_ring_peak=stream.count;
 }
}
static void flow_notify(uint16_t handle,uint32_t epoch,bool subscribed) {
 // 正常采集中攒满8帧；STOP时允许发送不足8帧的尾包。资源不足等TX_COMPLETE，不忙重试数百万次。
 if(!subscribed || !stream.count)return;
 if(flow_phase==FlowPhase::Running && !stream.pending_len && stream.count<V12_MAX_FRAMES)return;
 if(flow_hvn_pending>=16 || (flow_hvn_blocked && flow_hvn_pending))return;
 const uint32_t now=v12::timer_us(2);
 if(flow_hvn_blocked && uint32_t(now-flow_retry_us)<1000u)return;
 vTaskSuspendAll();
 if(epoch==link_epoch && handle==link_handle && data_chr.notifyEnabled(handle)) {
  const uint8_t *bytes;size_t length;
  if(v12_stream_peek(&stream,link_mtu,&bytes,&length)==V12_STREAM_OK) {
   uint16_t sent=uint16_t(length);ble_gatts_hvx_params_t p={};
   p.handle=data_chr.handles().value_handle;p.type=BLE_GATT_HVX_NOTIFICATION;
   p.p_len=&sent;p.p_data=const_cast<uint8_t*>(bytes);
   const uint32_t rc=sd_ble_gatts_hvx(handle,&p);flow_last_hvx_error=rc;
   if(rc==NRF_SUCCESS && sent==length) {
    ++flow_hvn_pending;flow_hvn_blocked=false;v12_stream_commit(&stream);
    if(flow_last_send && uint32_t(now-flow_last_send)>flow_max_send_gap)flow_max_send_gap=now-flow_last_send;
    flow_last_send=now;
   } else {
    ++notify_failures;
    if(rc==NRF_ERROR_RESOURCES || rc==NRF_ERROR_BUSY) {++flow_resources;flow_hvn_blocked=true;flow_retry_us=now;}
    else {++flow_other_errors;flow_abort(v12::Fault::Cancelled);}
    if(rc==NRF_SUCCESS)sd_ble_gap_disconnect(handle,BLE_HCI_REMOTE_USER_TERMINATED_CONNECTION);
   }
  }
 }
 xTaskResumeAll();
}
static void r01_flow_loop() {
 vTaskSuspendAll();const uint32_t epoch=link_epoch;const uint16_t handle=link_handle;
 const bool subscribed=handle!=BLE_CONN_HANDLE_INVALID && data_chr.notifyEnabled(handle);
 uint8_t request=requested_mode;const uint32_t command_epoch=request_epoch;requested_mode=0;xTaskResumeAll();
 if(epoch!=observed_epoch) {
  observed_epoch=epoch;ads.stop(flow_first_fault(v12::Fault::Cancelled));pending_request=0;imu_stop(true);
  if(handle!=BLE_CONN_HANDLE_INVALID) {
   // 新连接是新会话，绝不跨连接续传旧尾包。STOP在同一连接内不重置这些值。
   ads.stop();v12_stream_init(&stream,MAKO_V12_FS);flow_reset_metrics();flow_phase=FlowPhase::Idle;
   uint32_t m=__get_PRIMASK();__disable_irq();isr_w=isr_r=0;v12::reset_drdy(drdy_stats);__set_PRIMASK(m);
  } else {flow_phase=FlowPhase::Incomplete;flow_terminal=true;}
  request=0;status_update();
 }
 if(request && command_epoch==epoch) {
  if(request==4)flow_stop();
  else if(flow_phase==FlowPhase::Running || flow_phase==FlowPhase::Draining)flow_stop(v12::Fault::Argument);
  else if(flow_phase==FlowPhase::Incomplete || flow_hvn_pending || flow_credit_error) {
   // 异常退出后必须新建连接，禁止旧TX完成事件污染下一段。
   flow_abort(v12::Fault::Cancelled);
  }
  else if(request==1 || request==2 || request==3 || request==5) {
   v12_stream_restart(&stream,MAKO_V12_FS);flow_reset_metrics();flow_phase=FlowPhase::Idle;
   arm_epoch=epoch;arm_handle=handle;
   const v12::BenchProof proof={bool(MAKO_BENCH_MEASURED),MAKO_BENCH_POR_US,MAKO_BENCH_REFERENCE_US};
   running=ads.start(MAKO_V12_FS,v12::Input(request),proof);
   if(!start_session_valid()){ads.stop(flow_first_fault(v12::Fault::Cancelled));running=false;}
   if(running) {
    board_hal.cs(false);uint32_t m=__get_PRIMASK();__disable_irq();
    edge_count=edge_us=isr_w=isr_r=0;isr_have=isr_gap=isr_overflow=isr_rails=false;
    v12::reset_drdy(drdy_stats);__set_PRIMASK(m);
    attachInterrupt(digitalPinToInterrupt(D9),on_dout_fall,FALLING);
    flow_phase=FlowPhase::Running;flow_last_loop=v12::timer_us(2);
    sd_ble_gattc_exchange_mtu_request(handle,247);
    ble_gap_phys_t phy={BLE_GAP_PHY_2MBPS,BLE_GAP_PHY_2MBPS};(void)sd_ble_gap_phy_update(handle,&phy);
   } else {flow_phase=FlowPhase::Stopped;flow_terminal=true;}
  } else {flow_abort(v12::Fault::Argument);}
  status_update();
 }
 if(handle==BLE_CONN_HANDLE_INVALID)return;
 if(flow_credit_error)flow_abort(v12::Fault::Overrun);
 if(!subscribed && (flow_phase==FlowPhase::Running || flow_phase==FlowPhase::Draining))flow_abort(v12::Fault::Cancelled);
 const uint32_t now=v12::timer_us(2);
 if(flow_phase==FlowPhase::Running) {
  if(uint32_t(now-flow_last_loop)>flow_max_loop_gap)flow_max_loop_gap=now-flow_last_loop;
  flow_last_loop=now;
  if(digitalRead(D5)!=LOW || isr_rails)flow_stop(v12::Fault::Rails);
  else if(isr_gap || isr_overflow)flow_stop(v12::Fault::Overrun);
  else if(isr_r==isr_w && v12::capture_timeout(have_edge,now-(have_edge?last_edge_us:capture_started),MAKO_V12_FS))flow_stop(v12::Fault::Timeout);
 }
 if(flow_phase==FlowPhase::Running || flow_phase==FlowPhase::Draining) {
  flow_stage_frames();flow_notify(handle,epoch,subscribed);
  if(flow_phase==FlowPhase::Draining) {
   if(isr_r==isr_w && !stream.count && !flow_hvn_pending) {flow_phase=FlowPhase::Stopped;flow_terminal=true;status_update();}
   else if(uint32_t(v12::timer_us(2)-flow_stop_us)>FLOW_DRAIN_US) {flow_abort(v12::Fault::Overrun);status_update();}
  }
 }
 const uint64_t clock=clock_us();if(clock>=next_status){status_update();next_status=clock+1000000;}
 yield();
}

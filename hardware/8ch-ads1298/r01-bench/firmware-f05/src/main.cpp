#include <Arduino.h>
#include <bluefruit.h>
#include <SPI.h>
#include "ads1298.h"
#include "capture_guard.h"
#include "bench_release.h"
#include "diagnostics.h"
#include "timebase_board.h"
using v12::clock_us;
#include <v12_build_id.h>
extern "C" {
#include "v12_stream.h"
}

#if MAKO_V12_AFE_ENABLED != 0
#error "只使用bench_release.h的实测门，不允许绕过当前硬件锁"
#endif
#if MAKO_V12_FS != 2000 && MAKO_V12_FS != 4000
#error "采样率候选只允许2000或4000"
#endif
#ifndef MAKO_V12_SPI_HZ
#define MAKO_V12_SPI_HZ 2000000
#endif
#if MAKO_V12_SPI_HZ != 1000000 && MAKO_V12_SPI_HZ != 2000000 && MAKO_V12_SPI_HZ != 4000000 && MAKO_V12_SPI_HZ != 8000000
#error "SPI台架候选只允许1/2/4/8MHz"
#endif
static_assert(PIN_SPI_SCK==8 && PIN_SPI_MISO==9 && PIN_SPI_MOSI==10,"SPI板包映射变化");

static BLEService service("7b24c101-3948-4f03-9d11-12bb9d000001");
static BLECharacteristic data_chr("7b24c101-3948-4f03-9d11-12bb9d000002");
static BLECharacteristic meta_chr("7b24c101-3948-4f03-9d11-12bb9d000003");
static BLECharacteristic status_chr("7b24c101-3948-4f03-9d11-12bb9d000004");
static BLECharacteristic control_chr("7b24c101-3948-4f03-9d11-12bb9d000005");
static v12_stream stream;
static volatile uint32_t edge_count=0,edge_us=0;
static volatile v12::DrdyStats drdy_stats={0,0,UINT32_MAX,false};
static volatile uint8_t requested_mode=0;
static volatile uint32_t request_epoch=0;
static uint32_t used_edge=0,last_edge_us=0,capture_started=0;
static uint32_t ads_status=0;
static bool have_edge=false;
static bool start_session_valid();
static uint32_t arm_epoch=0;
static uint16_t arm_handle=BLE_CONN_HANDLE_INVALID;
static void on_drdy() {const uint32_t now=v12::timer_us(0);edge_us=now;++edge_count;v12::record_drdy(drdy_stats,now);}
struct BoardHal final: v12::AdsHal {
 bool spi_on=false;
 void power(bool on) override {
  if(on) {SPI.begin();SPI.beginTransaction(SPISettings(MAKO_V12_SPI_HZ,MSBFIRST,SPI_MODE1));spi_on=true;digitalWrite(D0,HIGH);}
  else {digitalWrite(D0,LOW);if(spi_on){SPI.endTransaction();SPI.end();spi_on=false;}const uint8_t pins[]={D8,D10};for(uint8_t p:pins){digitalWrite(p,LOW);pinMode(p,OUTPUT);}}
 }
 void pwdn(bool on) override {digitalWrite(D4,on?HIGH:LOW);}
 void reset(bool on) override {digitalWrite(D2,on?HIGH:LOW);}
 void clocksel(bool on) override {digitalWrite(D1,on?HIGH:LOW);}
 void cs(bool on) override {digitalWrite(D7,on?HIGH:LOW);}
 uint8_t transfer(uint8_t value) override {return SPI.transfer(value);}
 void wait(uint32_t us) override {while(us>=1000 && session_valid()){delay(1);us-=1000;}if(us<1000 && us)delayMicroseconds(us);}
 bool session_valid() override {return start_session_valid();}
 bool rails_good() override {
  // 内部0.6V参考×6为3.6V量程，再乘板上1:4分压；只作粗筛，不能替代台架。
  unsigned raw=analogRead(D3);float avdd=float(raw)*14.4f/4095.0f;
  return digitalRead(D5)==LOW && avdd>=4.6f && avdd<=5.4f;
 }
 void capture(bool on) override {
  detachInterrupt(digitalPinToInterrupt(D6));
  // 停采保留最后一次原始沿统计，避免故障处理抹掉假沿证据；重新启动才清零。
  if(on){uint32_t mask=__get_PRIMASK();__disable_irq();edge_count=0;edge_us=0;v12::reset_drdy(drdy_stats);__set_PRIMASK(mask);}
  used_edge=0;last_edge_us=0;have_edge=false;capture_started=v12::timer_us(2);
  if(on)attachInterrupt(digitalPinToInterrupt(D6),on_drdy,FALLING);
 }
} board_hal;
static v12::Ads1298 ads(board_hal);
static volatile uint16_t link_handle=BLE_CONN_HANDLE_INVALID;
static volatile uint16_t link_mtu=23;
static volatile uint32_t link_epoch=0;
static uint32_t observed_epoch=0;
static bool running=false;
static uint8_t pending_request=0;
static uint32_t pending_epoch=0;
static bool joint_mode=false;
static bool start_session_valid() {
 vTaskSuspendAll();
 bool valid=arm_handle!=BLE_CONN_HANDLE_INVALID && link_handle==arm_handle && link_epoch==arm_epoch && requested_mode==0 && data_chr.notifyEnabled(arm_handle);
 xTaskResumeAll();return valid;
}
static uint64_t next_status=0;
static uint64_t notify_failures=0;
#include "imu_bridge.h"

// 同步BLE事件回调；异步应用回调可能滞后于连接句柄的删除/复用。
static void ble_event(ble_evt_t *event) {
 uint16_t handle=event->evt.common_evt.conn_handle;
 if(event->header.evt_id==BLE_GAP_EVT_CONNECTED) {
  link_handle=handle; link_mtu=23; ++link_epoch;
 } else if(event->header.evt_id==BLE_GAP_EVT_DISCONNECTED) {
  link_handle=BLE_CONN_HANDLE_INVALID; link_mtu=23; ++link_epoch;
 } else if(handle==link_handle && (event->header.evt_id==BLE_GATTS_EVT_EXCHANGE_MTU_REQUEST || event->header.evt_id==BLE_GATTC_EVT_EXCHANGE_MTU_RSP)) {
  // 该事件任务已更新MTU，读取后只保存值，不把连接指针带回loop。
  BLEConnection *connection=Bluefruit.Connection(handle);
  if(connection) link_mtu=connection->getMtu();
 }
}

static void hold_afe_off() {
 // 先置低再配置输出，避免初始化过程中短暂拉高模拟电源/ADS输入。
 const uint8_t outputs[]={D0,D1,D2,D4,D7,D8,D10};
 for(uint8_t pin:outputs) { digitalWrite(pin,LOW); pinMode(pin,OUTPUT); }
 pinMode(D5,INPUT); pinMode(D6,INPUT); pinMode(D9,INPUT);
 analogReadResolution(12);analogReference(AR_INTERNAL);
}

static void status_update() {
 // 64位ISR计数在32位MCU上不能直接读；短临界区只复制，再恢复中断编码。
 const uint32_t mask=__get_PRIMASK();__disable_irq();
 const uint64_t raw_edges=drdy_stats.raw_edges;
 const uint32_t min_interval=drdy_stats.min_interval_us;
 __set_PRIMASK(mask);
 const v12::StatusSnapshot snapshot={stream.produced,stream.ring_dropped,stream.scheduler_skipped,
                    stream.sent_samples,notify_failures,uint8_t(ads.fault),ads.active,bool(MAKO_BENCH_MEASURED),
                    ads_status,raw_edges,min_interval,MAKO_V12_SPI_HZ};
 uint8_t bytes[v12::STATUS_BYTES];v12::encode_status(bytes,snapshot);
 status_chr.write(bytes,sizeof(bytes));imu_status_update();
}

static void control_write(uint16_t handle,BLECharacteristic*,uint8_t *data,uint16_t len) {
 if(handle!=link_handle || len!=4)return;
 uint8_t mode=0;
 if(!memcmp(data,"STOP",4))mode=4;
 else if(!memcmp(data,"TST1",4))mode=1;
 else if(!memcmp(data,"SHT1",4))mode=2;
 else if(!memcmp(data,"EXT1",4))mode=3;
 else if(!memcmp(data,"IMU1",4))mode=6; // IMU独立模式始终保持ADS关闭。
 else if(!memcmp(data,"EXR1",4))mode=5; // 外部输入 + RLD
 if(mode){request_epoch=link_epoch;requested_mode=mode;}
}
void setup() {
 hold_afe_off();
 v12::timebase_begin();
 if(v12_stream_init(&stream,MAKO_V12_FS)) return;
 Bluefruit.configUuid128Count(MAKO_V12_IMU_ENABLED?7:5);
 Bluefruit.configPrphBandwidth(BANDWIDTH_MAX);
 Bluefruit.begin(1,0);
 Bluefruit.setName(MAKO_V12_FS==2000?"MAKO-V12-ADS-2K":"MAKO-V12-ADS-4K");
 Bluefruit.Periph.setConnInterval(6,12);
 Bluefruit.setEventCallback(ble_event);
 service.begin();
 data_chr.setProperties(CHR_PROPS_NOTIFY);
 data_chr.setPermission(SECMODE_OPEN,SECMODE_NO_ACCESS);
 data_chr.setMaxLen(V12_STREAM_PACKET); data_chr.begin();
 meta_chr.setProperties(CHR_PROPS_READ);
 meta_chr.setPermission(SECMODE_OPEN,SECMODE_NO_ACCESS);
 meta_chr.setMaxLen(400); meta_chr.begin();
 char metadata[400];
 snprintf(metadata,sizeof(metadata),"{\"profile\":\"F05_ADS_CANDIDATE\",\"build_id\":\"%s\",\"fs_Hz\":%u,\"spi_Hz\":%u,\"channels\":8,\"bench_measured\":%s,\"protocol\":1,\"clock_tolerance_pct\":2.5,\"ISR_latency_measured\":false,\"time\":\"first_ISR_time_then_nominal\",\"imu_enabled\":%s,\"clock_source\":\"TIMER2_1MHz\",\"clock_resolution_us\":1}",MAKO_V12_BUILD_ID,MAKO_V12_FS,MAKO_V12_SPI_HZ,MAKO_BENCH_MEASURED?"true":"false",MAKO_V12_IMU_ENABLED?"true":"false");
 meta_chr.write(metadata);
 status_chr.setProperties(CHR_PROPS_READ);
 status_chr.setPermission(SECMODE_OPEN,SECMODE_NO_ACCESS);
 status_chr.setFixedLen(v12::STATUS_BYTES); status_chr.begin();
 control_chr.setProperties(CHR_PROPS_WRITE);
 control_chr.setPermission(SECMODE_NO_ACCESS,SECMODE_OPEN);
 control_chr.setMaxLen(4);control_chr.setWriteCallback(control_write,false);control_chr.begin();
 imu_setup();status_update();
 Bluefruit.Advertising.addFlags(BLE_GAP_ADV_FLAGS_LE_ONLY_GENERAL_DISC_MODE);
 Bluefruit.Advertising.addService(service);
 Bluefruit.ScanResponse.addName();
 Bluefruit.Advertising.restartOnDisconnect(true);
 Bluefruit.Advertising.setInterval(32,244); Bluefruit.Advertising.start(0);
}

void loop() {
 uint64_t now=clock_us();
 // 只暂停任务切换；SoftDevice中断仍工作。区间内没有延时或队列等待。
 vTaskSuspendAll();
 uint32_t epoch=link_epoch;
 uint16_t handle=link_handle;
 bool subscribed=handle!=BLE_CONN_HANDLE_INVALID && data_chr.notifyEnabled(handle);
 xTaskResumeAll();
 if(epoch!=observed_epoch) {observed_epoch=epoch;ads.stop();imu_stop(true);running=false;pending_request=0;joint_mode=false;requested_mode=0;notify_failures=0;v12_stream_init(&stream,MAKO_V12_FS);}
 vTaskSuspendAll();uint8_t request=requested_mode;uint32_t command_epoch=request_epoch;requested_mode=0;xTaskResumeAll();
 if(request && command_epoch==epoch) {
  ads.stop();imu_stop();running=false;joint_mode=false;
  pending_request=request==4?0:request;pending_epoch=epoch;
  v12_stream_restart(&stream,MAKO_V12_FS);status_update();
 }
 // 先推进停止，再重新配置；未收到STOPPED时不复用DMA或开始新会话。
 imu_tick(clock_us(),handle,epoch);
 if(handle==BLE_CONN_HANDLE_INVALID){if(ads.active)ads.stop();imu_stop(true);running=false;pending_request=0;joint_mode=false;delay(1);return;}
 if(pending_request && pending_epoch==epoch && imu_stopped()) {
  request=pending_request;pending_request=0;
  if(request==6 && imu_subscribed(handle) && !imu_faulted()) {
   imu_start(clock_us());sd_ble_gattc_exchange_mtu_request(handle,247);
  } else if(request!=6 && subscribed && !imu_faulted()) {
   arm_epoch=epoch;arm_handle=handle;
   const v12::BenchProof proof={bool(MAKO_BENCH_MEASURED),MAKO_BENCH_POR_US,MAKO_BENCH_REFERENCE_US};
   running=ads.start(MAKO_V12_FS,v12::Input(request),proof);
   if(!start_session_valid()){ads.stop(v12::Fault::Cancelled);running=false;}
   if(running){joint_mode=imu_subscribed(handle);if(joint_mode)imu_start(clock_us());sd_ble_gattc_exchange_mtu_request(handle,247);}
  }
  status_update();
 }
 if(!subscribed || (joint_mode && !imu_subscribed(handle))) {
  if(ads.active)ads.stop(v12::Fault::Cancelled);
  if(joint_mode)imu_stop();
  running=false;joint_mode=false;
 }
 if(ads.active) {
  uint32_t mask=__get_PRIMASK();__disable_irq();uint32_t count=edge_count,edge=edge_us;__set_PRIMASK(mask);
  
  if(digitalRead(D5)!=LOW)ads.stop(v12::Fault::Rails);
  else if(count!=used_edge) {
   // ADC没有历史FIFO；任何不确定缺口立即停机，绝不补造样本或估一个精确丢帧数。
   uint32_t delta=edge-last_edge_us;
   if(v12::uncertain_edge(have_edge,count,used_edge,delta,MAKO_V12_FS))ads.stop(v12::Fault::Overrun);
   else {
    uint8_t frame[27];int32_t raw[8];
    if(ads.read(frame)) {
     if(edge_count!=count)ads.stop(v12::Fault::Overrun);
     else if(!v12::Ads1298::decode(frame,27,raw,&ads_status))ads.stop(v12::Fault::Frame);
     else {
      uint64_t current=clock_us(),stamp=(current&~UINT64_C(0xffffffff))|edge;
      if(stamp>current)stamp-=UINT64_C(1)<<32;
      unsigned slot=(stream.head+stream.count)%V12_STREAM_RING;bool room=stream.count<V12_STREAM_RING;
      if(v12_stream_push(&stream,raw,stamp)!=V12_STREAM_OK)ads.stop(v12::Fault::Frame);
      else if(room)memcpy(stream.ring[slot].frame,frame,27); // 保留真实三字节状态，不能伪造0xC00000。
      used_edge=count;last_edge_us=edge;have_edge=true;
     }
    }
   }
  } else if(v12::capture_timeout(have_edge,uint32_t(v12::timer_us(2)-(have_edge?last_edge_us:capture_started)),MAKO_V12_FS))ads.stop(v12::Fault::Timeout);
  running=ads.active;
  if(joint_mode && !ads.active){imu_stop();joint_mode=false;}
 }
 // 每次只提交一个完整F01包；拥塞立即返回并保留重试，不进入库的分片/阻塞路径。
 vTaskSuspendAll();
 if(ads.active && subscribed && epoch==link_epoch && handle==link_handle) {
  const uint8_t *bytes; size_t length;
  if(v12_stream_peek(&stream,link_mtu,&bytes,&length)==V12_STREAM_OK) {
   uint16_t sent=(uint16_t)length;
   ble_gatts_hvx_params_t params={};
   params.handle=data_chr.handles().value_handle; params.type=BLE_GATT_HVX_NOTIFICATION;
   params.p_len=&sent; params.p_data=const_cast<uint8_t*>(bytes);
   uint32_t result=sd_ble_gatts_hvx(handle,&params);
   if(result==NRF_SUCCESS && sent==length) v12_stream_commit(&stream);
   else {
    ++notify_failures;
    // 异常部分提交不能重发成重复包；结束会话，由重连显式开启新序列。
    if(result==NRF_SUCCESS) sd_ble_gap_disconnect(handle,BLE_HCI_REMOTE_USER_TERMINATED_CONNECTION);
   }
  }
 }
 xTaskResumeAll();
 if(!imu_tick(clock_us(),handle,epoch)){if(ads.active)ads.stop(v12::Fault::Cancelled);running=false;joint_mode=false;}
 if(now>=next_status) { status_update(); next_status=now+1000000; }
 yield();
}

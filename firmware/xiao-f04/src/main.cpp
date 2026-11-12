#include <Arduino.h>
#include <bluefruit.h>
#include <math.h>
#include <v12_build_id.h>
extern "C" {
#include "v12_stream.h"
}

#if MAKO_V12_AFE_ENABLED != 0
#error "电气时序P0未关闭；F04不得启用真实AFE"
#endif
#if MAKO_V12_FS != 2000 && MAKO_V12_FS != 4000
#error "采样率候选只允许2000或4000"
#endif
static_assert(PIN_SPI_SCK==8 && PIN_SPI_MISO==9 && PIN_SPI_MOSI==10,"SPI板包映射变化");

static BLEService service("7b24c101-3948-4f03-9d11-12bb9d000001");
static BLECharacteristic data_chr("7b24c101-3948-4f03-9d11-12bb9d000002");
static BLECharacteristic meta_chr("7b24c101-3948-4f03-9d11-12bb9d000003");
static BLECharacteristic status_chr("7b24c101-3948-4f03-9d11-12bb9d000004");
static v12_stream stream;
static volatile uint16_t link_handle=BLE_CONN_HANDLE_INVALID;
static volatile uint16_t link_mtu=23;
static volatile uint32_t link_epoch=0;
static uint32_t observed_epoch=0;
static bool running=false;
static uint64_t deadline=0, next_status=0;
static uint64_t notify_failures=0;

/* 仅合成调度使用；loop须至少每次micros回卷前运行一次。 */
static uint64_t clock_us() {
 static uint32_t previous=0;
 static uint64_t epoch=0;
 uint32_t current=micros();
 if(current<previous) epoch+=UINT64_C(1)<<32;
 previous=current; return epoch+current;
}

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
 const uint8_t outputs[]={D0,D1,D2,D7,D8,D10};
 for(uint8_t pin:outputs) { digitalWrite(pin,LOW); pinMode(pin,OUTPUT); }
 pinMode(D6,INPUT_PULLDOWN); pinMode(D9,INPUT_PULLDOWN);
}

static void status_update() {
 uint64_t fields[]={stream.produced,stream.ring_dropped,stream.scheduler_skipped,
                    stream.sent_samples,notify_failures};
 uint8_t bytes[40];
 for(unsigned f=0;f<5;++f) for(unsigned b=0;b<8;++b) bytes[f*8+b]=(uint8_t)(fields[f]>>(8*b));
 status_chr.write(bytes,sizeof(bytes));
}

void setup() {
 hold_afe_off();
 if(v12_stream_init(&stream,MAKO_V12_FS)) return;
 Bluefruit.configUuid128Count(4);
 Bluefruit.configPrphBandwidth(BANDWIDTH_MAX);
 Bluefruit.begin(1,0);
 Bluefruit.setName(MAKO_V12_FS==2000?"MAKO-V12-SYN-2K":"MAKO-V12-SYN-4K");
 Bluefruit.Periph.setConnInterval(6,12);
 Bluefruit.setEventCallback(ble_event);
 service.begin();
 data_chr.setProperties(CHR_PROPS_NOTIFY);
 data_chr.setPermission(SECMODE_OPEN,SECMODE_NO_ACCESS);
 data_chr.setMaxLen(V12_STREAM_PACKET); data_chr.begin();
 meta_chr.setProperties(CHR_PROPS_READ);
 meta_chr.setPermission(SECMODE_OPEN,SECMODE_NO_ACCESS);
 meta_chr.setMaxLen(160); meta_chr.begin();
 char metadata[160];
 snprintf(metadata,sizeof(metadata),"{\"profile\":\"F04_SYNTHETIC\",\"build_id\":\"%s\",\"fs_Hz\":%u,\"channels\":8,\"afe_enabled\":false,\"protocol\":1,\"notch\":false}",MAKO_V12_BUILD_ID,MAKO_V12_FS);
 meta_chr.write(metadata);
 status_chr.setProperties(CHR_PROPS_READ);
 status_chr.setPermission(SECMODE_OPEN,SECMODE_NO_ACCESS);
 status_chr.setFixedLen(40); status_chr.begin(); status_update();
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
 if(epoch!=observed_epoch) { observed_epoch=epoch; running=false; notify_failures=0; v12_stream_init(&stream,MAKO_V12_FS); }
 if(handle==BLE_CONN_HANDLE_INVALID) { delay(1); return; }
 if(!running && subscribed) {
  running=true; deadline=now;
  sd_ble_gattc_exchange_mtu_request(handle,247);
 }
 if(!running) { delay(1); return; }
 const unsigned period=1000000u/MAKO_V12_FS;
 if(now>=deadline) {
  uint64_t due=(now-deadline)/period+1;
  if(due>32 && stream.produced) {
   uint64_t skipped=due-32;
   // 单次很久停顿时分段计数，避免uint32窄化把丢样吞掉。
   while(skipped) { uint32_t part=skipped>UINT32_MAX?UINT32_MAX:(uint32_t)skipped; v12_stream_skip(&stream,part); deadline+=(uint64_t)part*period; skipped-=part; }
  }
  unsigned budget=32;
  while(deadline<=now && budget--) {
   int32_t raw[8];
   for(unsigned ch=0;ch<8;++ch) {
    float phase=(float)(stream.next_sequence%MAKO_V12_FS)/MAKO_V12_FS;
    raw[ch]=(int32_t)(100000.0f+40000.0f*sinf(6.28318530718f*(100.0f+ch*20.0f)*phase));
   }
   v12_stream_push(&stream,raw,deadline); deadline+=period;
  }
 }
 // 每次只提交一个完整F01包；拥塞立即返回并保留重试，不进入库的分片/阻塞路径。
 vTaskSuspendAll();
 if(subscribed && epoch==link_epoch && handle==link_handle) {
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
 if(now>=next_status) { status_update(); next_status=now+1000000; }
 yield();
}

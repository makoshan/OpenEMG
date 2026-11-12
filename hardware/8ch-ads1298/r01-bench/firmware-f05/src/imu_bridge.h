#pragma once
#ifndef MAKO_V12_IMU_ENABLED
#define MAKO_V12_IMU_ENABLED 0
#endif
#if MAKO_V12_IMU_ENABLED != 0 && MAKO_V12_IMU_ENABLED != 1
#error "IMU候选只接受0或1"
#endif
#if MAKO_V12_IMU_ENABLED
#include "imu_board.h"
static BLECharacteristic imu_chr("7b24c101-3948-4f03-9d11-12bb9d000006");
static BLECharacteristic imu_status_chr("7b24c101-3948-4f03-9d11-12bb9d000007");
static v12::ImuBoard imu_board;
static v12::Imu imu(imu_board);
static volatile uint32_t imu_edges=0,imu_edge_us=0;
static bool imu_requested=false;
static void imu_irq(){imu_edge_us=v12::timer_us(1);++imu_edges;}
static void imu_stop(bool disconnect=false) {
 detachInterrupt(digitalPinToInterrupt(PIN_LSM6DS3TR_C_INT1));
 if(disconnect)imu.disconnected();else imu.stop();
 imu_requested=false;
}
static void imu_setup() {
 imu_chr.setProperties(CHR_PROPS_NOTIFY);imu_chr.setPermission(SECMODE_OPEN,SECMODE_NO_ACCESS);
 imu_chr.setFixedLen(v12::Imu::PACKET_BYTES);imu_chr.begin();
 imu_status_chr.setProperties(CHR_PROPS_READ);imu_status_chr.setPermission(SECMODE_OPEN,SECMODE_NO_ACCESS);
 imu_status_chr.setFixedLen(v12::Imu::STATUS_BYTES);imu_status_chr.begin();
}
static void imu_status_update() {
 uint8_t data[v12::Imu::STATUS_BYTES];imu.status(data,true);imu_status_chr.write(data,sizeof(data));
}
static bool imu_stopped(){return imu.stage==v12::Imu::Stage::Off;}
static bool imu_faulted(){return imu.fault!=v12::ImuFault::None;}
static bool imu_subscribed(uint16_t handle){return imu_chr.notifyEnabled(handle);}
static void imu_start(uint64_t now) {
 const uint32_t mask=__get_PRIMASK();__disable_irq();imu_edges=imu_edge_us=0;__set_PRIMASK(mask);
 pinMode(PIN_LSM6DS3TR_C_INT1,INPUT_PULLDOWN);
 attachInterrupt(digitalPinToInterrupt(PIN_LSM6DS3TR_C_INT1),imu_irq,RISING);
 imu_requested=imu.start(now,true);
 if(!imu_requested)detachInterrupt(digitalPinToInterrupt(PIN_LSM6DS3TR_C_INT1));
}
static bool imu_tick(uint64_t now,uint16_t handle,uint32_t epoch) {
 if(!imu_requested) {
  imu.tick(now,0,0); // STOP/断连后仍推进异步DMA停止。
  return !imu_faulted();
 }
 vTaskSuspendAll();
 const bool valid=handle!=BLE_CONN_HANDLE_INVALID && handle==link_handle && epoch==link_epoch && imu_subscribed(handle);
 xTaskResumeAll();
 if(!valid){imu_stop();imu.tick(now,0,0);return false;}
 const uint32_t mask=__get_PRIMASK();__disable_irq();const uint32_t count=imu_edges,stamp=imu_edge_us;__set_PRIMASK(mask);
 imu.tick(now,count,stamp);
 const uint32_t after_mask=__get_PRIMASK();__disable_irq();const uint32_t live_edges=imu_edges;__set_PRIMASK(after_mask);
 imu.validate_pending(live_edges);
 if(imu.fault!=v12::ImuFault::None){detachInterrupt(digitalPinToInterrupt(PIN_LSM6DS3TR_C_INT1));imu_requested=false;return false;}
 if(imu.pending) {
  vTaskSuspendAll();
  if(handle==link_handle && epoch==link_epoch && link_mtu>=v12::Imu::PACKET_BYTES+3 && imu_subscribed(handle)) {
   uint16_t length=v12::Imu::PACKET_BYTES;ble_gatts_hvx_params_t params={};
   params.handle=imu_chr.handles().value_handle;params.type=BLE_GATT_HVX_NOTIFICATION;
   params.p_len=&length;params.p_data=imu.packet;
   const uint32_t rc=sd_ble_gatts_hvx(handle,&params);
   if(rc==NRF_SUCCESS && length==v12::Imu::PACKET_BYTES)imu.commit();
   else {++imu.notify_failures;if(rc==NRF_SUCCESS)sd_ble_gap_disconnect(handle,BLE_HCI_REMOTE_USER_TERMINATED_CONNECTION);}
  }
  xTaskResumeAll();
 }
 return true;
}
#else
static void imu_stop(bool=false){}
static void imu_setup(){}
static void imu_status_update(){}
static bool imu_stopped(){return true;}
static bool imu_faulted(){return false;}
static bool imu_subscribed(uint16_t){return false;}
static void imu_start(uint64_t){}
static bool imu_tick(uint64_t,uint16_t,uint32_t){return true;}
#endif

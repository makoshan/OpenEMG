// R01 一镜像两通道入口：开机按 VBUS 选 USB 串口版或蓝牙 DOUT 版，两边代码原样（见 build.py）。
#include <Arduino.h>
#include <nrf_sdm.h>
#include <nrf_soc.h>

void ble_setup();
void ble_loop();
void usb_setup();
void usb_loop();
extern "C" void tusb_hal_nrf_power_event(uint32_t event);

static bool usb_mode = false;
static bool vbus() {
  // SoftDevice 开着（蓝牙模式）时 POWER 外设归它管，走 SVC 读；没开时直接读寄存器（板包 TinyUSB 也是这样）
  uint8_t on = 0;
  if (sd_softdevice_is_enabled(&on) == NRF_SUCCESS && on) {
    uint32_t status = 0;
    if (sd_power_usbregstatus_get(&status) != NRF_SUCCESS) return true;  // 读不到就当插着 USB：宁可复位，不可漏判
    return (status & POWER_USBREGSTATUS_VBUSDETECT_Msk) != 0;
  }
  return (NRF_POWER->USBREGSTATUS & POWER_USBREGSTATUS_VBUSDETECT_Msk) != 0;
}

void setup() {
  usb_mode = vbus();
  if (usb_mode) {
    usb_setup();
    // 引导程序（如 1200bps 串口 DFU 0x4e 3s 超时退回）已清过 EVENTS_USBPWRRDY 时，
    // 板包 Adafruit_TinyUSB_nrf.cpp:132 只发 DETECTED(0) 不发 READY(2)，致 USBPULLUP=0 从 Mac 消失；
    // 按 bluefruit.cpp:88 同款条件补发 USB_EVT_READY(2) 拉起 D+ 上拉。
    if ((NRF_POWER->USBREGSTATUS & POWER_USBREGSTATUS_OUTPUTRDY_Msk) && (NRF_USBD->USBPULLUP == 0)) {
      tusb_hal_nrf_power_event(2);
    }
  } else {
    ble_setup();
  }
}

void loop() {
  // 运行中插拔 USB：不在两套程序之间热切换，直接整片复位。
  // 复位后 GPIO 回到输入、ANA_EN 由 R25 下拉，模拟电源关；重启再按新的供电选通道，不续采。
  if (vbus() != usb_mode) { NVIC_SystemReset(); return; }  // return 只给主机替身用，真机复位不返回
  if (usb_mode) usb_loop(); else ble_loop();
}

// 主机替身：只提供 dispatch.cpp 用到的 VBUS 读取（寄存器 / SoftDevice 两路）、USB 上拉状态和复位。
#pragma once
#include <cstdint>
#define POWER_USBREGSTATUS_VBUSDETECT_Msk 1u
#define POWER_USBREGSTATUS_OUTPUTRDY_Msk 2u
#define NRF_SUCCESS 0u
struct FakePower { uint32_t USBREGSTATUS; };
struct FakeUsbd { uint32_t USBPULLUP; };
inline FakePower fake_power{0};
inline FakeUsbd fake_usbd{0};
#define NRF_POWER (&fake_power)
#define NRF_USBD (&fake_usbd)
inline int resets = 0, usb_ready_events = 0;
inline uint8_t sd_on = 0;
inline uint32_t sd_status = 0, sd_rc = 0;
inline void NVIC_SystemReset() { ++resets; }
inline uint32_t sd_softdevice_is_enabled(uint8_t *on) { *on = sd_on; return NRF_SUCCESS; }
inline uint32_t sd_power_usbregstatus_get(uint32_t *s) { *s = sd_status; return sd_rc; }
extern "C" inline void tusb_hal_nrf_power_event(uint32_t event) {
  if (event == 2) { ++usb_ready_events; fake_usbd.USBPULLUP = 1; }
}

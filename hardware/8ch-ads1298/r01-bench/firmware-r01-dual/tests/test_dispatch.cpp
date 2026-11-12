// 直接编译 src/dispatch.cpp：开机按 VBUS 选通道，运行中 VBUS 变化必须复位且不再跑旧通道；
// 从引导程序跳回或软复位后若 OUTPUTRDY=1 且 USBPULLUP=0，必须补发 USB_EVT_READY(2) 拉起 D+ 上拉。
#include "../src/dispatch.cpp"
#include <cassert>
#include <cstdio>
static int bs, bl, us, ul;
void ble_setup() { ++bs; sd_on = 1; } void ble_loop() { ++bl; } void usb_setup() { ++us; } void usb_loop() { ++ul; }
static void boot(uint32_t v, uint32_t pullup = 0) {
  bs = bl = us = ul = resets = usb_ready_events = 0;
  sd_on = 0; sd_rc = 0;
  fake_power.USBREGSTATUS = sd_status = v;
  fake_usbd.USBPULLUP = pullup;
  setup();
}
int main() {
  boot(0); loop(); loop();
  assert(bs == 1 && bl == 2 && !us && !ul && !resets && !usb_ready_events); // 只接电池 → 蓝牙，不动 USB
  fake_power.USBREGSTATUS = 1; loop();
  assert(!resets && bl == 3);                                   // 蓝牙模式 SoftDevice 开着：不读寄存器
  sd_status = 1; loop();
  assert(resets == 1 && bl == 3 && !ul);                        // 插 USB（SoftDevice 报告）→ 复位，不再跑旧通道
  boot(0); sd_rc = 1; loop();
  assert(resets == 1 && !bl);                                   // SoftDevice 读失败 → 当插着 USB，复位
  boot(1); loop();
  assert(us == 1 && ul == 1 && !bs && !bl && !resets && !usb_ready_events); // 仅 VBUSDETECT=1、OUTPUTRDY=0 → 等硬件中断，不抢发 READY
  boot(3, 0); loop();
  assert(us == 1 && ul == 1 && usb_ready_events == 1 && fake_usbd.USBPULLUP == 1); // 引导程序跳回：VBUSDETECT|OUTPUTRDY=3 且 USBPULLUP=0 → 必须补发 READY(2) 拉起上拉
  boot(3, 1); loop();
  assert(us == 1 && ul == 1 && usb_ready_events == 0 && fake_usbd.USBPULLUP == 1); // 中断已拉起 USBPULLUP=1 → 不重复发 READY(2)
  fake_power.USBREGSTATUS = 0; loop();
  assert(resets == 1 && ul == 1);                               // 拔 USB → 复位
  puts("PASS: 一镜像两通道入口 8 例：电池开机走蓝牙、USB 开机走 USB、引导程序退回补拉 USBPULLUP、已拉起不重发、插/拔 USB 都复位、蓝牙下经 SoftDevice 读 VBUS、读失败按插着处理；未接设备");
}

// TI 计划 S3+S4：直接编译 dual 暂存副本里的蓝牙半边（ble_app.cpp + flow_control.h），GPIO/SPI/BLE 用 ble-dout 的替身。
// 查：状态 v3 是 163 字节、版本 3、带快照；LOF1 命令和流控模式白名单只在 MAKO_R01_LOFF=1 时放行。
#include "ble_app.cpp"
#include <cassert>
#include <cstdio>

static void idle() {
  link_handle = arm_handle = 1; link_epoch = observed_epoch = arm_epoch = request_epoch = 1;
  requested_mode = 0; next_status = 10000000; mock_subscribed = true;
  flow_phase = FlowPhase::Idle; flow_hvn_pending = 0; flow_credit_error = false;
  ads.active = false; ads.fault = v12::Fault::None;
}

int main() {
  ble_setup();  // 元数据：要带 lof1 和快照格式，而且不能因为超长被丢掉（超长时固件静默不写）
#if MAKO_R01_LOFF
  assert(mock_metadata.find("\"lof1\":true,\"regs_snapshot\":\"status_v3\"}") != std::string::npos);
#else
  assert(mock_metadata.find("\"lof1\":false,\"regs_snapshot\":\"status_v3\"}") != std::string::npos);
#endif
  std::printf("元数据 %zu 字节（上限 511）\n", mock_metadata.size());
  for (unsigned i = 0; i < 26; ++i) ads.readback[i] = uint8_t(0xa0 + i);
  ads.readback_valid = true; flow_status_update();
  assert(mock_status.size() == 163 && mock_status[43] == 3 && mock_status[136] == 1);
  for (unsigned i = 0; i < 26; ++i) assert(mock_status[137 + i] == uint8_t(0xa0 + i));
  ads.readback_valid = false; flow_status_update(); assert(mock_status[136] == 0);

  idle();
  uint8_t lof[4] = {'L', 'O', 'F', '1'}, exr[4] = {'E', 'X', 'R', '1'};
  control_write(1, nullptr, lof, 4);
#if MAKO_R01_LOFF
  assert(requested_mode == 7);
#else
  assert(requested_mode == 0);  // 默认镜像不认这个命令
#endif
  control_write(1, nullptr, exr, 4); assert(requested_mode == 5);

  idle(); requested_mode = 7; ble_loop();  // 绕过命令解析直接塞模式 7：流控白名单也要按开关拦
#if MAKO_R01_LOFF
  assert(ads.fault != v12::Fault::Argument);
  std::printf("PASS: 蓝牙状态 v3（163 字节带快照）；LOF1 命令与模式白名单放行（MAKO_R01_LOFF=1）\n");
#else
  assert(ads.fault == v12::Fault::Argument && flow_phase == FlowPhase::Incomplete);
  std::printf("PASS: 蓝牙状态 v3（163 字节带快照）；默认镜像不认 LOF1，模式 7 被流控拒绝\n");
#endif
  return 0;
}

// TI 计划 S3+S4：直接编译 dual 暂存副本里打过补丁的 ads1298.cpp，用一个会记寄存器的替身 ADS 跑 start()。
// 查：配置完读回的 26 字节快照和替身里的寄存器逐字节一致；快照到下一次 start 才清；LOF1 只在 MAKO_R01_LOFF=1 时放行。
// 每个成功的快照打印一行 "SNAP 名字 十六进制"，check.py 再交给 host/ads1298_regs.py 按手册查保留位。
#include "ads1298.h"
#include <cassert>
#include <cstdio>
#include <cstring>

struct Emu : v12::AdsHal {
  uint8_t reg[26] = {};
  unsigned pos = 0; uint8_t op = 0;
  bool rdatac = true;                              // 上电默认连续读：这时芯片不理 RREG/WREG（手册 9.5.3.10）
  Emu() { reg[0] = 0x92; reg[0x12] = 0x5a; reg[0x13] = 0xa5; }  // ADS1298 的 ID；导联状态只读，给非零值
  void power(bool) override {} void pwdn(bool) override {} void reset(bool) override {} void clocksel(bool) override {}
  void cs(bool high) override { if (!high) pos = 0; }
  uint8_t transfer(uint8_t b) override {           // 只模拟 RREG/WREG 各读写一个寄存器（驱动只这样用）
    const unsigned p = pos++;
    if (p == 0) { op = b; if (b == 0x10) rdatac = true; if (b == 0x11) rdatac = false; return 0; }
    const uint8_t a = op & 0x1f;
    if (rdatac) return 0;                          // 连续读期间读写寄存器无效：快照必须在 RDATAC（0x10）之前
    if ((op & 0xe0) == 0x20 && p == 2 && a < 26) return reg[a];
    if ((op & 0xe0) == 0x40 && p == 2 && a < 26 && a != 0x12 && a != 0x13) reg[a] = b;
    return 0;
  }
  void wait(uint32_t) override {} bool rails_good() override { return true; } bool session_valid() override { return true; }
  void capture(bool) override {}
};

static const v12::BenchProof proof = {true, 132000, 1};

static void snap(const char *name, const v12::Ads1298 &ads) {
  std::printf("SNAP %s ", name);
  for (unsigned i = 0; i < 26; ++i) std::printf("%02x", ads.readback[i]);
  std::printf("\n");
}

int main() {
  {  // 短路噪声：快照 = 替身里的寄存器（先把快照填满 0xEE，26 个都得被覆盖）
    Emu e; v12::Ads1298 ads(e);
    std::memset(ads.readback, 0xee, 26);
    assert(ads.start(2000, v12::Input::Shorted, proof) && ads.readback_valid && e.rdatac);
    assert(!std::memcmp(ads.readback, e.reg, 26) && ads.readback[1] == 0x84 && ads.readback[3] == 0xe0 && ads.readback[5] == 0x01);
    assert(ads.readback[0x16] == 0x20 && ads.readback[0x4] == 0 && ads.readback[0x17] == 0 && ads.readback[0x12] == 0x5a);
    snap("sht", ads);
    ads.stop();
    assert(ads.readback_valid && ads.readback[1] == 0x84);  // 停机后快照还在
    assert(!ads.start(2000, v12::Input(4), proof) && ads.fault == v12::Fault::Argument && !ads.readback_valid);  // 新一次 start 先清
  }
  {  // 外部输入 + RLD：RLD 最后开，快照里是 0xE4；只让 CH1 进 RLD（dual 的 RLD_SENS）
    Emu e; v12::Ads1298 ads(e);
    assert(ads.start(2000, v12::Input::ExternalRld, proof));
    assert(ads.readback[3] == 0xe4 && ads.readback[0xd] == 0x01 && ads.readback[0xe] == 0x01 && ads.readback[0x4] == 0);
    assert(!std::memcmp(ads.readback, e.reg, 26));
    snap("exr", ads);
  }
  {  // 读回 ID 不对：不留快照
    Emu e; e.reg[0] = 0x00; v12::Ads1298 ads(e);
    assert(!ads.start(2000, v12::Input::Shorted, proof) && ads.fault == v12::Fault::Identity && !ads.readback_valid);
  }
  {  // LOF1（模式 7）
    Emu e; v12::Ads1298 ads(e);
    std::memset(ads.readback, 0xee, 26);
    const bool ok = ads.start(2000, v12::Input::ExternalRldLoff, proof);
#if MAKO_R01_LOFF
    assert(ok && ads.readback_valid && !std::memcmp(ads.readback, e.reg, 26));
    assert(ads.readback[0x4] == 0x03 && ads.readback[0xf] == 0x01 && ads.readback[0x10] == 0x01 && ads.readback[0x17] == 0x02);
    assert(ads.readback[3] == 0xe4 && ads.readback[0xd] == 0x01 && ads.readback[0xe] == 0x01 && ads.readback[5] == 0x00);
    snap("lof", ads);
    std::printf("PASS: 驱动快照与 LOF1（MAKO_R01_LOFF=1）\n");
#else
    assert(!ok && ads.fault == v12::Fault::Argument && !ads.readback_valid && e.reg[0x4] == 0 && e.reg[0x17] == 0);  // 默认镜像不认，也没碰导联寄存器
    std::printf("PASS: 驱动快照；默认镜像拒绝 LOF1\n");
#endif
  }
  return 0;
}

"""TI 计划 S3+S4（docs/ti-evm-to-openemg-plan-20261109.md）：打在 dual 暂存副本上的补丁，firmware-f05 等原文件不动。

S3 寄存器快照：驱动在写完寄存器、开连续读（RDATAC）之前读回 0x00–0x19，存在 Ads1298::readback；
   蓝牙半边随状态特征上报（状态 v3 = v2 的 136 字节 + 有效标志 1 字节 + 26 字节寄存器 = 163 字节），
   USB 半边在停机报告里多发一帧 META {"diag":8,...}（采集中发 JSON 会挤占采样周期，所以放停机时）。
   快照到下一次 start 才清掉，停机后还能读到。USB 半边采集中用 Waavv 改过寄存器的，以 diag:5 为准。
S4 LOF1：外部输入 + RLD + 直流导联检测（LOFF=0x03：比较阈值 95%、电流源、6 nA、直流；LOFF_SENSP/N 同 RLD_SENS；
   CONFIG4=0x02 开比较器）。只加在蓝牙半边，而且只有 build.py --loff（编译开关 MAKO_R01_LOFF=1）时才认；
   默认镜像里驱动和蓝牙流控都拒绝模式 7。带 LOF1 的镜像只用于离体台架：SINGLE-FAULT-R01.md 的前提是导联电流为 0。
"""

LOFF_REGS = 'if(loff){regs[0x4]=0x03;regs[0xf]=regs[0x10]=regs[0xd];regs[0x17]=0x02;}'


def once(text, old, new, what):
    if text.count(old) != 1:
        raise SystemExit(f'S3/S4 补丁锚点不是正好一处（{what}），停止：{old[:70]}')
    return text.replace(old, new)


def apply(out, loff=False):
    src = out / 'src'
    h = src / 'ads1298.h'
    t = h.read_text()
    t = once(t, '#include <stddef.h>\n',
             '#include <stddef.h>\n'
             '#ifndef MAKO_R01_LOFF\n#define MAKO_R01_LOFF 0  // 1 = 认 LOF1（直流导联检测，只离体）；只由 build.py --loff 打开\n#endif\n', 'ads1298.h 开关')
    t = once(t, 'ExternalRld=5 };', 'ExternalRld=5, ExternalRldLoff=7 };  // 6 是 IMU1 的模式号', 'Input 枚举')
    t = once(t, ' Fault fault=Fault::None;\n',
             ' Fault fault=Fault::None;\n'
             ' uint8_t readback[26]={};  // 配置完、开连续读前读回的 0x00–0x19（TI 计划 S3）\n'
             ' bool readback_valid=false;  // 到下一次 start 才清，停机后仍可读\n', 'Ads1298 成员')
    h.write_text(t)

    c = src / 'ads1298.cpp'
    t = c.read_text()
    t = once(t, 'bool Ads1298::start(unsigned fs,Input input,const BenchProof &proof) {\n stop();\n',
             'bool Ads1298::start(unsigned fs,Input input,const BenchProof &proof) {\n stop();readback_valid=false;\n', 'start 清快照')
    t = once(t, 'input!=Input::External && input!=Input::ExternalRld))',
             'input!=Input::External && input!=Input::ExternalRld && !(MAKO_R01_LOFF && input==Input::ExternalRldLoff)))', '输入白名单')
    t = once(t, ' const bool rld=input==Input::ExternalRld;\n',
             ' const bool loff=MAKO_R01_LOFF && input==Input::ExternalRldLoff;\n const bool rld=input==Input::ExternalRld || loff;\n', 'rld/loff')
    rld = 'if(rld)regs[0xd]=regs[0xe]='
    if t.count(rld) != 1:
        raise SystemExit('S3/S4 补丁锚点不是正好一处（RLD 通道行），停止')
    i = t.index(rld)
    j = t.index('\n', i)
    t = t[:j + 1] + (' ' + LOFF_REGS + '  // LOF1（TI 计划 S4）：直流导联 6 nA、阈值 95%，只开 RLD_SENS 那几路；CONFIG4.PD_LOFF_COMP=1\n') + t[j + 1:]
    t = once(t, ' command(0x10);if(!h.session_valid()){stop(Fault::Cancelled);return false;}\n',
             ' for(uint8_t a=0;a<26;++a)readback[a]=read_reg(a);readback_valid=true;  // TI 计划 S3：读回实际寄存器，随状态上报\n'
             ' command(0x10);if(!h.session_valid()){stop(Fault::Cancelled);return false;}\n', 'RDATAC 前快照')
    c.write_text(t)

    b = src / 'ble_app.cpp'
    t = b.read_text()
    t = once(t, ' else if(!memcmp(data,"EXR1",4))mode=5; // 外部输入 + RLD\n',
             ' else if(!memcmp(data,"EXR1",4))mode=5; // 外部输入 + RLD\n'
             '#if MAKO_R01_LOFF\n else if(!memcmp(data,"LOF1",4))mode=7; // TI 计划 S4：外部输入 + RLD + 直流导联检测，只离体\n#endif\n', '蓝牙命令')
    # 元数据带上 lof1 和快照格式，归档能机读这块镜像认不认 LOF1
    t = once(t, r'\"queue_slots\":%u}",MAKO_V12_BUILD_ID,MAKO_V12_FS,MAKO_V12_SPI_HZ,MAKO_BENCH_BASIS,V12_STREAM_RING);',
             r'\"queue_slots\":%u,\"lof1\":%s,\"regs_snapshot\":\"status_v3\"}",MAKO_V12_BUILD_ID,MAKO_V12_FS,MAKO_V12_SPI_HZ,MAKO_BENCH_BASIS,V12_STREAM_RING,MAKO_R01_LOFF?"true":"false");',
             '蓝牙元数据')
    b.write_text(t)

    f = src / 'flow_control.h'
    t = f.read_text()
    t = once(t, 'static constexpr size_t FLOW_STATUS_BYTES=136;', 'static constexpr size_t FLOW_STATUS_BYTES=163;  // 状态 v3：v2 的 136 + 有效标志 1 + 寄存器 26', '状态长度')
    t = once(t, 'v12::encode_status(bytes,snapshot);bytes[43]=2;', 'v12::encode_status(bytes,snapshot);bytes[43]=3;', '状态版本')
    t = once(t, 'v12::status_le(bytes+132,flow_max_send_gap,4);\n',
             'v12::status_le(bytes+132,flow_max_send_gap,4);\n'
             ' bytes[136]=ads.readback_valid;memcpy(bytes+137,ads.readback,26);  // 状态 v3（TI 计划 S3）：配置时读回的寄存器\n', '状态快照')
    t = once(t, 'else if(request==1 || request==2 || request==3 || request==5) {',
             'else if(request==1 || request==2 || request==3 || request==5 || (MAKO_R01_LOFF && request==7)) {', '流控模式白名单')
    f.write_text(t)

    u = src / 'usb_app.cpp'
    t = u.read_text()
    t = once(t, 'static void send_edge_report() {\n',
             'static void send_regs() {  // TI 计划 S3：配置时读回的 0x00–0x19；采集中用 Waavv 改过的以 diag:5 为准\n'
             '  char json[96]; int n = snprintf(json, sizeof json, "{\\"diag\\":8,\\"valid\\":%d,\\"regs\\":\\"", ads.readback_valid ? 1 : 0);\n'
             '  for (int a = 0; a < 26 && n > 0 && n < int(sizeof json) - 3; ++a) n += snprintf(json + n, sizeof json - n, "%02x", ads.readback[a]);\n'
             '  if (n > 0 && n < int(sizeof json) - 2) n += snprintf(json + n, sizeof json - n, "\\"}");\n'
             '  uint8_t out[sizeof json + 6]; if (n > 0 && n < int(sizeof json)) send(out, usbf::encode(usbf::META, reinterpret_cast<const uint8_t *>(json), size_t(n), out));\n'
             '}\n'
             'static void send_edge_report() {\n', 'USB 快照函数')
    # 放在停机报告最后：先发更关键的 diag:3/4，发送缓冲紧时不被挤掉
    t = once(t, '\n}\n\nstatic void send_status() {', '\n  send_regs();  // 放最后\n}\n\nstatic void send_status() {', 'USB 停机报告')
    # 纵深防御：USB 半边只许内部信号（1 = 测试方波、2 = 输入短路），--loff 镜像的驱动白名单放行了模式 7 也进不来
    t = once(t, '    ads.start(MAKO_V12_FS, v12::Input(mode), proof);  // 失败时 fault 已记下，状态帧会报\n',
             '    if (mode == 1 || mode == 2) ads.start(MAKO_V12_FS, v12::Input(mode), proof);  // 失败时 fault 已记下，状态帧会报\n'
             '    else ads.stop(v12::Fault::Argument);  // USB 半边只许内部信号（TI 计划 S4）\n', 'USB 模式护栏')
    u.write_text(t)

    if loff:
        ini = out / 'platformio.ini'
        t = ini.read_text()
        old = ' -DMAKO_V12_FS=2000 -DMAKO_V12_SPI_HZ=2000000\n'
        ini.write_text(once(t, old, old.rstrip('\n') + ' -DMAKO_R01_LOFF=1\n', 'platformio.ini 开关'))


EXTERNAL_MODES = ('"EXT1"', '"EXR1"', '"LOF1"')


def usb_has_external(usb_text):
    """USB 半边不许出现任何外部输入模式（插 USB 时 J1-12 互锁被跨接，见 README B 节）。"""
    return [m for m in EXTERNAL_MODES if m in usb_text]

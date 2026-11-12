"""F05 蓝牙版 + DOUT 代 DRDY（R01 的 DRDY 专用线不通，2026-10-22 Mako 选方案 B：电池加蓝牙）。

在豁免版副本（firmware-f05-waiver/build.py 的 stage()：钉 F05 整组哈希、换锁头、标 bench_basis）上再打 4 处补丁：
1. 新增 on_dout_fall：DOUT（MISO，D9）下降沿中断里直接一次 DMA 读 27 字节、CS 不翻转，放进 16 帧环形缓冲；
   中断里按 0.7–1.3T 查间隔，异常或缓冲满就置标志，主循环据此停机（Overrun）；
2. capture() 不再挂 D6 中断，并且同时摘掉 D9；
3. ads.start 成功后 CS 拉低并保持，清零计数和缓冲，再挂 D9 中断；
4. 主循环的读帧块换成“从环形缓冲取帧 → 解码 → 入 F01 流”；元数据加 "drdy_source":"dout_isr"。
为什么读帧放中断：主循环读帧时，蓝牙任务把它卡住到 391µs（2026-10-22 调试版实测），48ms 内就漏帧停机。
firmware-f05 一个字节都不改；F05 一变，豁免版 stage() 就会停。镜像只留本地 artifacts/。仅离体测试与过安全门后的贴肤，按 README 的顺序。
用法：python build.py [--env ads_2k] [--pio pio路径] [--toolchain 包规格]
"""
from pathlib import Path
import argparse, hashlib, importlib.util, json, shutil, subprocess

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location('waiver_build', HERE.parent / 'firmware-f05-waiver' / 'build.py')
waiver = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(waiver)
SOURCE_TAG = 'dout_isr'

OLD_READ_BLOCK = '  else if(count!=used_edge) {\n   // ADC没有历史FIFO；任何不确定缺口立即停机，绝不补造样本或估一个精确丢帧数。\n   uint32_t delta=edge-last_edge_us;\n   if(v12::uncertain_edge(have_edge,count,used_edge,delta,MAKO_V12_FS))ads.stop(v12::Fault::Overrun);\n   else {\n    uint8_t frame[27];int32_t raw[8];\n    if(ads.read(frame)) {\n     if(edge_count!=count)ads.stop(v12::Fault::Overrun);\n     else if(!v12::Ads1298::decode(frame,27,raw,&ads_status))ads.stop(v12::Fault::Frame);\n     else {\n      uint64_t current=clock_us(),stamp=(current&~UINT64_C(0xffffffff))|edge;\n      if(stamp>current)stamp-=UINT64_C(1)<<32;\n      unsigned slot=(stream.head+stream.count)%V12_STREAM_RING;bool room=stream.count<V12_STREAM_RING;\n      if(v12_stream_push(&stream,raw,stamp)!=V12_STREAM_OK)ads.stop(v12::Fault::Frame);\n      else if(room)memcpy(stream.ring[slot].frame,frame,27); // 保留真实三字节状态，不能伪造0xC00000。\n      used_edge=count;last_edge_us=edge;have_edge=true;\n     }\n    }\n   }\n  } else if(v12::capture_timeout(have_edge,uint32_t(v12::timer_us(2)-(have_edge?last_edge_us:capture_started)),MAKO_V12_FS))ads.stop(v12::Fault::Timeout);'

NEW_READ_BLOCK = (
    '  else if(isr_rails)ads.stop(v12::Fault::Rails);  // 中断里看到 OE_N 变高\n'
    '  else if(isr_gap || isr_overflow)ads.stop(v12::Fault::Overrun);  // 间隔异常或环形缓冲满：停机，不补造样本\n'
    '  else if(isr_r!=isr_w) {\n'
    '   while(isr_r!=isr_w && ads.active) {\n'
    '    const IsrFrame &f=isr_ring[isr_r%ISR_RING];int32_t raw[8];\n'
    '    if(isr_gap || isr_overflow || isr_rails){ads.stop(isr_rails?v12::Fault::Rails:v12::Fault::Overrun);break;}  // 缺口后的帧中断不读；这里拦住循环中途来的停机标志\n'
    '    if((f.frame[0]&0xf0)!=0xc0 || !v12::Ads1298::decode(f.frame,27,raw,&ads_status)){ads.stop(v12::Fault::Frame);break;}\n'
    '    uint64_t current=clock_us(),stamp=(current&~UINT64_C(0xffffffff))|f.t;\n'
    '    if(stamp>current)stamp-=UINT64_C(1)<<32;\n'
    '    unsigned slot=(stream.head+stream.count)%V12_STREAM_RING;bool room=stream.count<V12_STREAM_RING;\n'
    '    if(v12_stream_push(&stream,raw,stamp)!=V12_STREAM_OK){ads.stop(v12::Fault::Frame);break;}\n'
    '    if(room)memcpy(stream.ring[slot].frame,f.frame,27); // 保留真实三字节状态\n'
    '    last_edge_us=f.t;have_edge=true;++isr_r;\n'
    '   }\n'
    '  } else if(v12::capture_timeout(have_edge,uint32_t(v12::timer_us(2)-(have_edge?last_edge_us:capture_started)),MAKO_V12_FS))ads.stop(v12::Fault::Timeout);'
)

PATCHES = [
    ('static void on_drdy() {const uint32_t now=v12::timer_us(0);edge_us=now;++edge_count;v12::record_drdy(drdy_stats,now);}',
     'static void on_drdy() {const uint32_t now=v12::timer_us(0);edge_us=now;++edge_count;v12::record_drdy(drdy_stats,now);}\n'
     '// DOUT 代 DRDY（firmware-f05-ble-dout 补丁）：CS 低、不给时钟时 DOUT 跟着 DRDY，D9 下降沿进中断。\n'
     '// 读帧放在中断里做：蓝牙任务会把主循环卡住 400µs 以上（2026-10-22 实测），主循环读帧会漏帧。\n'
     '// 读帧时 MISO 上的跳变也会置 GPIOTE 事件，板包在回调返回后才清事件，所以不会被当成新沿。\n'
     'struct IsrFrame {uint8_t frame[27];uint32_t t;};\n'
     'static constexpr uint32_t ISR_RING=16;\n'
     'static IsrFrame isr_ring[ISR_RING];\n'
     'static volatile uint32_t isr_w=0,isr_r=0,isr_last=0;\n'
     'static volatile bool isr_have=false,isr_gap=false,isr_overflow=false,isr_rails=false;\n'
     'static uint8_t dout_zeros[27];  // DIN 保持低；必须在 RAM（const 会进 Flash，EasyDMA 读不了，实测帧头错）\n'
     'static void on_dout_fall() {\n'
     ' const uint32_t now=v12::timer_us(0),period=1000000u/MAKO_V12_FS;edge_us=now;++edge_count;v12::record_drdy(drdy_stats,now);\n'
     ' // 任何异常都先摘掉 D9 中断再返回：模拟电源被互锁切断后 MISO 悬空乱跳，不摘会中断风暴，主循环跑不到停机、蓝牙断开（2026-10-22 插 USB 实测）\n'
     ' if(digitalRead(D5)!=LOW){isr_rails=true;detachInterrupt(digitalPinToInterrupt(D9));return;}  // OE_N 高：模拟电源已断\n'
     ' if(isr_have){const uint32_t d=now-isr_last;if(d<period*7/10||d>period*13/10){isr_gap=true;detachInterrupt(digitalPinToInterrupt(D9));return;}}  // 同 capture_guard 的 0.7–1.3T；缺口后的帧不读\n'
     ' isr_last=now;isr_have=true;\n'
     ' if(isr_w-isr_r>=ISR_RING){isr_overflow=true;detachInterrupt(digitalPinToInterrupt(D9));return;}\n'
     ' IsrFrame &f=isr_ring[isr_w%ISR_RING];SPI.transfer(dout_zeros,f.frame,27);f.t=now;++isr_w;  // 一次 DMA，CS 不翻转\n'
     '}'),
    ('  detachInterrupt(digitalPinToInterrupt(D6));',
     '  detachInterrupt(digitalPinToInterrupt(D6));detachInterrupt(digitalPinToInterrupt(D9));'),
    ('  if(on)attachInterrupt(digitalPinToInterrupt(D6),on_drdy,FALLING);',
     '  // D9 中断在 ads.start 成功、CS 拉低之后才挂：START 命令会翻转 CS，先挂会把 CS 翻转当成 DRDY'),
    ('   running=ads.start(MAKO_V12_FS,v12::Input(request),proof);',
     '   running=ads.start(MAKO_V12_FS,v12::Input(request),proof);\n'
     '   if(running){board_hal.cs(false);uint32_t m=__get_PRIMASK();__disable_irq();edge_count=0;edge_us=0;isr_w=0;isr_r=0;isr_have=false;isr_gap=false;isr_overflow=false;isr_rails=false;__set_PRIMASK(m);'
     'attachInterrupt(digitalPinToInterrupt(D9),on_dout_fall,FALLING);}'),
    (OLD_READ_BLOCK, NEW_READ_BLOCK),
    (' Bluefruit.configPrphBandwidth(BANDWIDTH_MAX);',
     ' Bluefruit.configPrphConn(247,100,16,BLE_GATTC_WRITE_CMD_TX_QUEUE_SIZE_DEFAULT);  // 发送队列 3→16：Mac 一个连接间隔要 4–8 包，3 包排不下（2026-10-22 蓝牙丢约 10%）'),
    ('if(joint_mode)imu_start(clock_us());sd_ble_gattc_exchange_mtu_request(handle,247);}',
     'if(joint_mode)imu_start(clock_us());sd_ble_gattc_exchange_mtu_request(handle,247);'
     '{ble_gap_phys_t phy={BLE_GAP_PHY_2MBPS,BLE_GAP_PHY_2MBPS};(void)sd_ble_gap_phy_update(handle,&phy);}}  // 请求 2M 物理层，对方不支持就留在 1M（Mac 实测接受）'),
    ('\\"ISR_latency_measured\\":false,', f'\\"ISR_latency_measured\\":false,\\"drdy_source\\":\\"{SOURCE_TAG}\\",'),
]


def stage(toolchain=None, pack16=0):
    src = waiver.stage(toolchain)  # 豁免版副本：哈希钉住、锁头已换、bench_basis 已加
    out = HERE / '.pio' / 'stage'
    shutil.rmtree(out, ignore_errors=True)
    shutil.copytree(src, out, ignore=shutil.ignore_patterns('.pio'))
    main = (out / 'src/main.cpp').read_text()
    for old, new in PATCHES:
        if main.count(old) != 1:
            raise SystemExit(f'补丁锚点不是正好一处，停止：{old[:60]}')
        main = main.replace(old, new)
    (out / 'src/main.cpp').write_text(main)
    spec = importlib.util.spec_from_file_location('r01_flow_patch', HERE / 'flow_patch.py')
    patch = importlib.util.module_from_spec(spec); spec.loader.exec_module(patch)
    patch.apply(out, HERE)
    if pack16:  # 16 位差分打包，见 pack16_patch.py；默认 0 时镜像与之前完全相同
        spec = importlib.util.spec_from_file_location('r01_pack16', HERE / 'pack16_patch.py')
        p16 = importlib.util.module_from_spec(spec); spec.loader.exec_module(p16)
        p16.apply(out, pack16)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--env', default='ads_2k', choices=['ads_2k', 'ads_4k_spi4'])
    ap.add_argument('--pio', default='pio')
    ap.add_argument('--toolchain')
    ap.add_argument('--pack16', type=int, default=0, choices=[0, 1, 2], help='0=原 24 位；1=16 位差分；2=差分且每帧两份（C07 16 路负载仿真）')
    a = ap.parse_args()
    out = stage(a.toolchain, a.pack16)
    subprocess.run([a.pio, 'run', '-d', str(out), '-e', a.env], check=True)
    build = out / '.pio' / 'build' / a.env
    meta = json.loads((build / 'generated' / 'build-inputs.json').read_text())
    payload = waiver.hex_payload(build / 'firmware.hex')
    for tag in (waiver.BASIS, SOURCE_TAG):
        if tag.encode() not in payload:
            raise SystemExit(f'烧录镜像里没有 {tag}，停止')
    art = HERE / 'artifacts'
    art.mkdir(exist_ok=True)
    stem = f'f05-ble-dout-{a.env}{f"-pack16x{a.pack16}" if a.pack16 else ""}-{meta["build_id"]}'
    shutil.copy2(build / 'firmware.hex', art / f'{stem}.hex')
    shutil.copy2(build / 'firmware.zip', art / f'{stem}-dfu.zip')
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    manifest = dict(profile='F05_ADS_BENCH_WAIVED_DOUT', bench_basis=waiver.BASIS, drdy_source=SOURCE_TAG, env=a.env, pack16=a.pack16,
                    build_id=meta['build_id'], toolchain=a.toolchain or 'platformio.ini 默认',
                    f05_bundle_sha256=waiver.F05_BUNDLE_SHA256, patches=len(PATCHES),
                    hex_sha256=sha(art / f'{stem}.hex'), dfu_sha256=sha(art / f'{stem}-dfu.zip'))
    (art / f'{stem}.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()

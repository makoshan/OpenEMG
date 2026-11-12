"""对已经钉源的DOUT副本叠加STOP/背压修复；不改共享F05。"""
from pathlib import Path
import shutil

# F01 队列帧数：2 kHz 下 2048 帧≈1 s，扛手/手机靠近时 BLE 吞吐短时掉到 222–238 包/s（需 250）。
# 上限两条：STOP 时满队列 256 包在最差 222 包/s 下≈1.15 s，须小于 FLOW_DRAIN_US（2 s，test_flow 有用例）；
# 每帧 48 B，4096 帧约 192 KB 会把堆挤到约 5–6 KB（2026-10-24 独立复核按 elf 推算），故不用 4096。
QUEUE_SLOTS=2048

def once(text,old,new):
    if text.count(old)!=1:raise SystemExit('STOP补丁锚点变化：'+old[:70])
    return text.replace(old,new)

def apply(out, here):
    path=out/'src/main.cpp';main=path.read_text()
    main=once(main,'static constexpr uint32_t ISR_RING=16;', 'static constexpr uint32_t ISR_RING=16;\nstatic volatile uint32_t isr_peak=0;')
    main=once(main,'SPI.transfer(dout_zeros,f.frame,27);f.t=now;++isr_w;',
              'SPI.transfer(dout_zeros,f.frame,27);f.t=now;__DMB();++isr_w;if(isr_w-isr_r>isr_peak)isr_peak=isr_w-isr_r;')
    main=once(main,'#include "imu_bridge.h"','#include "imu_bridge.h"\n#include "flow_control.h"')
    main=once(main,' uint16_t handle=event->evt.common_evt.conn_handle;',
              ' uint16_t handle=event->evt.common_evt.conn_handle;\n if(event->header.evt_id==BLE_GATTS_EVT_HVN_TX_COMPLETE && handle==link_handle){flow_tx_complete(event->evt.gatts_evt.params.hvn_tx_complete.count);return;}')
    start=main.index('static void status_update() {');end=main.index('static void control_write(',start)
    main=main[:start]+'static void status_update() {flow_status_update();}\n\n'+main[end:]
    main=once(main,'meta_chr.setMaxLen(400)', 'meta_chr.setMaxLen(512)')
    main=once(main,'char metadata[400]', 'char metadata[512]')
    start=main.index(' snprintf(metadata,sizeof(metadata),');end=main.index(' meta_chr.write(metadata);',start)+len(' meta_chr.write(metadata);')
    main=main[:start]+r''' const int meta_len=snprintf(metadata,sizeof(metadata),"{\"profile\":\"F05_ADS_CANDIDATE\",\"build_id\":\"%s\",\"fs_Hz\":%u,\"spi_Hz\":%u,\"channels\":8,\"bench_measured\":true,\"bench_basis\":\"%s\",\"protocol\":1,\"drdy_source\":\"dout_isr\",\"clock_source\":\"TIMER2_1MHz\",\"clock_resolution_us\":1,\"imu_enabled\":false,\"time\":\"first_ISR_time_then_nominal\",\"stop_snapshot\":2,\"off_body_only\":true,\"queue_slots\":%u}",MAKO_V12_BUILD_ID,MAKO_V12_FS,MAKO_V12_SPI_HZ,MAKO_BENCH_BASIS,V12_STREAM_RING);
 if(meta_len<=0 || meta_len>=int(sizeof(metadata)))return;
 meta_chr.write(metadata);''' + main[end:]
    main=once(main,'status_chr.setFixedLen(v12::STATUS_BYTES)','status_chr.setFixedLen(FLOW_STATUS_BYTES)')
    start=main.index('void loop() {');main=main[:start]+'void loop() {r01_flow_loop();}\n'
    path.write_text(main)
    stream=out/'src/v12_stream.h';stream.write_text(once(stream.read_text(),'#define V12_STREAM_RING 128u',f'#define V12_STREAM_RING {QUEUE_SLOTS}u'))
    shutil.copy2(here/'src/flow_control.h',out/'src/flow_control.h')

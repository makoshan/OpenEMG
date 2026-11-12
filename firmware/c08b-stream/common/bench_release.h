/* C08B 共用双核主控（R4U6 / R4U6N）台架安全门与默认双硬件锁。
 *
 * 铁律（AGENTS.md）：
 *   默认硬件锁保持关闭（0）。没有实物台架供电纹波、ANA_EN->OE_N 互锁波形、
 *   ADS_PWDN/ADS_RESET 复位脉宽与 VBUS 插入急停的示波器实测证据前，禁止在仓内解锁！
 *   未解锁状态下：
 *   - 任何开启真实 AFE 的命令（TST1/SHT1/EXT1/EXR1/RLD1/PRB1）均在 L432 与 nRF 双侧拒绝，
 *     置故障码 C08B_FAULT_LOCKED(1)，ANA_EN / ADS_PWDN / ADS_START 保持低电平；
 *   - 仅允许无需开启 AFE 供电的双核合成流链路测试命令 SYN1（全部数据包强制带 SYNTHETIC=1 标记）。
 */
#pragma once

#ifndef MAKO_C08B_AFE_ENABLED
#define MAKO_C08B_AFE_ENABLED 0
#endif

#ifndef MAKO_BENCH_MEASURED
#define MAKO_BENCH_MEASURED 0
#endif

/* 两个开关必须同时显式置 1 才算台架放行；只开一半编译期直接报错拦截。 */
#if (MAKO_C08B_AFE_ENABLED != 0 && MAKO_C08B_AFE_ENABLED != 1) || \
    (MAKO_BENCH_MEASURED != 0 && MAKO_BENCH_MEASURED != 1)
#error "MAKO_C08B_AFE_ENABLED 与 MAKO_BENCH_MEASURED 只允许为 0 或 1"
#endif

#if MAKO_C08B_AFE_ENABLED != MAKO_BENCH_MEASURED
#error "双硬件锁必须成对放行（不能只开其中一个而绕过台架实测门）"
#endif

#ifndef MAKO_C08B_BUILD_ID
#define MAKO_C08B_BUILD_ID "c08b261112000001"
#endif

/* C08B V12 BLE 广播名与 GAP 设备名（严格对齐 host/devices/c08b-*.json name_prefix） */
#define C08B_BLE_DEV_NAME "YUANLI-C08B"

/* ADS1292 外部 VCAP1=1 µF 上电基准建立最低等待时间（>= 1000 ms，TI SBAS502C §9.4.2.1） */
#define C08B_ADS1292_POR_WAIT_MS 1050u
#if C08B_ADS1292_POR_WAIT_MS < 1000u
#error "ADS1292 VCAP1=1uF 上电建立等待严禁低于 1000 ms"
#endif

/* ADS1292 Pin 15(PWDN/RESET) 纯数字复位低脉宽与恢复时间（TI SBAS502C §10.1 Fig.74 & §8.5.1.8）：
 * 必须满足 >= 1 t_MOD (7.81 µs) 且 << 2^9 t_MOD (4000 µs 硬掉电门限)，取 20 µs 不泄放 VCAP1；
 * 释放后需等待 >= 18 t_CLK (35.2 µs)，取 100 µs。仅在确认 id_a != 0x92 后对 PA1 发出！ */
#define C08B_ADS1292_RESET_LOW_US 20u
#define C08B_ADS1292_RESET_SETTLE_US 100u
#if C08B_ADS1292_RESET_LOW_US < 10u || C08B_ADS1292_RESET_LOW_US > 100u
#error "ADS1292 PWDN/RESET 数字复位脉宽必须介于 10..100 us（严禁逼近 4000 us 掉电门限）"
#endif
#if C08B_ADS1292_RESET_SETTLE_US < 40u
#error "ADS1292 复位释放恢复等待严禁低于 40 us (>= 18 t_CLK)"
#endif

/* ADS1298 内部 2.40V 基准 / ADS1292 RLD 运放与外部 10 µF 两步建立最低等待时间（>= 150 ms） */
#define C08B_ADS_RLD_WARMUP_US 150000u
#define C08B_ADS1292_RLD_WARMUP_US C08B_ADS_RLD_WARMUP_US
#if C08B_ADS_RLD_WARMUP_US < 150000u
#error "ADS 内部基准与 RLD 两步预热严禁低于 150 ms"
#endif

/* ADS1292 PA4(AVDD_SENSE) 前置下拉泄放寄生残荷脉宽（>= 10 µs） */
#define C08B_PA4_BLEED_US 10u

/* ADS1292 512 kHz 内部时钟下命令/片选最小间隔（>= 4 t_CLK = 7.81 µs，取 10 µs） */
#define C08B_ADS_TSCCS_US 10u

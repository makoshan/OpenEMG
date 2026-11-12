#pragma once
// 实物 TPS7A2030 AVDD 建立、VCAP1(1 µF) 上电稳定（手册 §8.5.1.8 需 >=1 s）与 2.42 V 内部基准建立时间尚未在实板上测得。
// 所有默认构建均保持真实 AFE 锁定（MAKO_BENCH_MEASURED = 0）；仅在台架示波器证据闭合并经独立复核后，方可填写实测等待时间并解锁。
#define MAKO_BENCH_MEASURED 0
#define MAKO_BENCH_POR_US 1000000u
#define MAKO_BENCH_REFERENCE_US 0u

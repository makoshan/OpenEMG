/* C08B 共用双核主控（R4U6 / R4U6N：STM32L432KCU6 + nRF52840-QFAA）流式采集共享契约。
 *
 * 同时被三处编译验证：
 *   1. L432 裸机固件（Cortex-M4，SPI1 采 AFE + I2C1 采 IMU + SPI3 主机发包）
 *   2. nRF52840 无线固件（Cortex-M4，SPIS1 从机收包 + BLE GATT F01 v1/v4 通知发送）
 *   3. 主机端 C11 自检与变异单测（host_test/test_stream_host.c）
 */
#pragma once
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#if defined(__STDC_HOSTED__) && (__STDC_HOSTED__ == 1) && (!defined(__has_include) || __has_include(<string.h>))
#include <string.h>
#define C08B_MEMSET memset
#define C08B_MEMCPY memcpy
#define C08B_MEMCMP memcmp
#else
static inline void *c08b_memset_(void *dst, int v, size_t n) {
    uint8_t *p = (uint8_t *)dst;
    for (size_t i = 0; i < n; i++) p[i] = (uint8_t)v;
    return dst;
}
static inline void *c08b_memcpy_(void *dst, const void *src, size_t n) {
    uint8_t *d = (uint8_t *)dst;
    const uint8_t *s = (const uint8_t *)src;
    for (size_t i = 0; i < n; i++) d[i] = s[i];
    return dst;
}
static inline int c08b_memcmp_(const void *a, const void *b, size_t n) {
    const uint8_t *pa = (const uint8_t *)a, *pb = (const uint8_t *)b;
    for (size_t i = 0; i < n; i++) {
        if (pa[i] != pb[i]) return (int)pa[i] - (int)pb[i];
    }
    return 0;
}
#define C08B_MEMSET c08b_memset_
#define C08B_MEMCPY c08b_memcpy_
#define C08B_MEMCMP c08b_memcmp_
#endif

#include "bench_release.h"

/* ---------- 1. 采集板自动识别（零跳线） ---------- */
#define C08B_ADS1298_ID_OK(id) (((uint8_t)(id) & 0x1Fu) == 0x12u) /* 0x92(ADS1298) / 0xD2(ADS1298R) */
#define C08B_ADS1292_ID_OK(id) (((uint8_t)(id) & 0xDFu) == 0x53u) /* 0x53(ADS1292) / 0x73(ADS1292R) */
#define C08B_ADS_B_ABSENT(id)  ((uint8_t)(id) == 0x00u || (uint8_t)(id) == 0xFFu)

typedef enum {
    AFE_NONE = 0,
    AFE_2CH  = 2,   /* ADS1292-2ch-R9 六触点底板（单颗 ADS1292，PA4 兼读 3.0V AVDD_SENSE） */
    AFE_8CH  = 8,   /* D20-8CH / D20N-8CH 纯单面 8 通道板（U1 ADS1298，U2 未贴，LM27762 ±2.5V 双极供电） */
    AFE_16CH = 16,  /* D20 / D20N 双面 16 通道板（U1 + U2 双片 ADS1298 共用 2.048MHz 晶振，LM27762 ±2.5V） */
} c08b_afe_mode_t;

static inline c08b_afe_mode_t c08b_afe_detect(uint8_t id_a, uint8_t id_b)
{
    if (C08B_ADS1298_ID_OK(id_a) && C08B_ADS1298_ID_OK(id_b)) return AFE_16CH;
    if (C08B_ADS1298_ID_OK(id_a) && C08B_ADS_B_ABSENT(id_b))  return AFE_8CH;
    if (C08B_ADS1292_ID_OK(id_a) && C08B_ADS_B_ABSENT(id_b))  return AFE_2CH;
    return AFE_NONE;
}

/* ---------- 2. 采集控制模式与故障码（对齐 V12 BLE CONTROL / STATUS 契约） ---------- */
typedef enum {
    C08B_MODE_IDLE = 0,
    C08B_MODE_TST1 = 1,  /* 1 Hz 内部测试方波（需解锁台架安全门） */
    C08B_MODE_SHT1 = 2,  /* 内部输入短接测底噪（需解锁台架安全门） */
    C08B_MODE_EXT1 = 3,  /* 外部电极不开 RLD（需解锁台架安全门） */
    C08B_MODE_STOP = 4,  /* 停止采集并关断 ANA_EN / ADS_START / ADS_PWDN */
    C08B_MODE_EXR1 = 5,  /* 外部电极 + 右腿驱动 RLD（需解锁台架安全门；两步预热） */
    C08B_MODE_SYN1 = 6,  /* 免开 AFE 供电的双核合成流测试（锁定状态下允许，强制打 SYNTHETIC=1） */
    C08B_MODE_RLD1 = 7,  /* RLD 环路监测（ADS1292 CH2=RLD_MEASURE；ADS1298 U1 PD_RLD=1，禁置 RLD_MEAS/MUX=0x02） */
    C08B_MODE_PRB1 = 8,  /* 只读子板 ID 探测（需解锁台架安全门；读完 ID 更新 afe_mode 后立即关断 AFE） */
} c08b_req_mode_t;

typedef enum {
    C08B_FAULT_NONE      = 0,
    C08B_FAULT_LOCKED    = 1,  /* 台架安全门未解锁（默认锁关闭） */
    C08B_FAULT_ARG       = 2,  /* 采样率或命令参数无效 */
    C08B_FAULT_INTERLOCK = 3,  /* USB VBUS 插入、OE_N 未拉低或 2CH AVDD_SENSE 掉电急停 */
    C08B_FAULT_AFE_ID    = 4,  /* 采集板未接或 A/B 片 ID 损坏不匹配 */
    C08B_FAULT_READBACK  = 5,  /* ADS 寄存器写后回读不一致 */
    C08B_FAULT_BAD_FRAME = 6,  /* ADS 状态字高 4 位非 0xC 或双片 DRDY 失步 */
    C08B_FAULT_LINK_DROP = 7,  /* 发送环形缓冲或 BLE 通知积压丢帧 */
    C08B_FAULT_DRDY_TO   = 8,  /* DRDY 转换完成脉冲超时 */
    C08B_FAULT_CANCELLED = 9,  /* BLE 断连触发会话终止 */
} c08b_fault_t;

static inline uint8_t c08b_parse_ctrl4(const uint8_t cmd[4])
{
    if (!C08B_MEMCMP(cmd, "STOP", 4)) return C08B_MODE_STOP;
    if (!C08B_MEMCMP(cmd, "TST1", 4)) return C08B_MODE_TST1;
    if (!C08B_MEMCMP(cmd, "SHT1", 4)) return C08B_MODE_SHT1;
    if (!C08B_MEMCMP(cmd, "EXT1", 4)) return C08B_MODE_EXT1;
    if (!C08B_MEMCMP(cmd, "EXR1", 4)) return C08B_MODE_EXR1;
    if (!C08B_MEMCMP(cmd, "SYN1", 4)) return C08B_MODE_SYN1;
    if (!C08B_MEMCMP(cmd, "RLD1", 4)) return C08B_MODE_RLD1;
    if (!C08B_MEMCMP(cmd, "PRB1", 4)) return C08B_MODE_PRB1;
    return 0;
}

/* 判断请求模式在当前硬件锁与互锁状态下是否允许启动 */
static inline c08b_fault_t c08b_gate_mode_request(
    uint8_t req_mode, uint16_t fs_hz, bool afe_unlocked, bool vbus_present)
{
    if (req_mode == C08B_MODE_STOP || req_mode == C08B_MODE_IDLE) return C08B_FAULT_NONE;
    if (fs_hz != 500u && fs_hz != 1000u && fs_hz != 2000u) return C08B_FAULT_ARG;
    if (req_mode == C08B_MODE_SYN1) {
        return C08B_FAULT_NONE;
    }
    if (req_mode != C08B_MODE_TST1 && req_mode != C08B_MODE_SHT1 &&
        req_mode != C08B_MODE_EXT1 && req_mode != C08B_MODE_EXR1 &&
        req_mode != C08B_MODE_RLD1 && req_mode != C08B_MODE_PRB1) {
        return C08B_FAULT_ARG;
    }
    if (!afe_unlocked) return C08B_FAULT_LOCKED;
    if (vbus_present)  return C08B_FAULT_INTERLOCK;
    return C08B_FAULT_NONE;
}

/* ---------- 3. ADS1298 / ADS1292 寄存器表与状态位映射 ---------- */

/* 将 ADS1292 原生 24 位状态字（1100 | LOFF_STAT[4:0] | GPIO[1:0] | 13'b0）
 * 映射为统一 V12 F01 24 位状态头（1100 | LOFF_STATP[7:0] | LOFF_STATN[7:0] | GPIO[3:0]），
 * 对齐 host/ads1298_regs.py:decode_ads_status 与 xiao-ads1292-2ch。
 * ADS1292 原生位（TI SBAS502C §9.5.3）：
 *   byte0: [7:4]=1100, [3]=RLD_STAT, [2]=IN2N_OFF, [1]=IN2P_OFF, [0]=IN1N_OFF
 *   byte1: [7]=IN1P_OFF, [6]=GPIO2, [5]=GPIO1, [4:0]=0
 *   byte2: [7:0]=0
 */
static inline void c08b_ads1292_map_f01_status(const uint8_t raw3[3], uint8_t out3[3])
{
    if ((raw3[0] & 0xF0u) != 0xC0u) {
        out3[0] = raw3[0]; out3[1] = raw3[1]; out3[2] = raw3[2];
        return;
    }
    uint8_t in1p = (raw3[1] >> 7) & 1u;
    uint8_t in1n = (raw3[0] >> 0) & 1u;
    uint8_t in2p = (raw3[0] >> 1) & 1u;
    uint8_t in2n = (raw3[0] >> 2) & 1u;
    uint8_t gpio = (raw3[1] >> 5) & 3u;
    uint8_t statp = (uint8_t)((in2p << 1) | in1p);
    uint8_t statn = (uint8_t)((in2n << 1) | in1n);
    out3[0] = (uint8_t)(0xC0u | ((statp >> 4) & 0x0Fu));
    out3[1] = (uint8_t)(((statp & 0x0Fu) << 4) | ((statn >> 4) & 0x0Fu));
    out3[2] = (uint8_t)(((statn & 0x0Fu) << 4) | (gpio & 0x0Fu));
}

/* 生成 C08B v0.01 AFE-30P / D20 / D20-8CH（LM27762 ±2.5V 双极模拟供电）下 ADS1298 寄存器配置（0x01..0x19）。
 * 关键硬件铁律（核自 OpenEMG_v0.01_DualBoard.epro2 & hardware/16ch-c08b-round/schematics-afe/page1.py）：
 *   1. AVDD=+2.5V, AVSS=-2.5V（跨度 5.0V，对 AGND 单边 2.5V），CONFIG3(0x03) bit5 VREF_4V 必须为 0
 *      （锁定内部 2.40 V 基准，相对于 AVSS=-2.5V 建立）！
 *   2. 两片 Pin 60 (RLDREF) 在 PCB 上直接硬连 AGND (0V)！
 *      因此 CONFIG3 bit3 RLDREF_INT(0x08) 必须严格为 0（使用外部 AGND 参考），严禁写 0xCC 让内部缓冲顶牛短路！
 *   3. 人工审核定版 v0.01 AFE-30P 的两片 Pin 62 (RLDIN) 直接接 +2.5V (AVDD)，D20 的 Pin 62 接 AGND（均未连 RLDOUT）！
 *      根据 TI ADS1298 手册 SBAS459K 图 39 与表 21，RLD_MEAS(bit4=0x10) 会将 Pin 62(RLDIN) 接入 MUX=010 总线；
 *      在 v0.01 上置 RLD_MEAS=1 或 CHnSET.MUX=010 会把 +2.5V 电源轨直接灌入内部 RLD/PGA 测量总线！
 *      因此 ADS1298 的 CONFIG3 严禁置 VREF_4V(0x20)、RLD_MEAS(0x10) 或 RLDREF_INT(0x08)，即 (CONFIG3 & 0x38)==0，
 *      且任何通道严禁设 MUX=0x02(RLD_MEASURE)！
 *   4. 两步开 RLD（仅 chip_idx=0 主片 U1 负责使能偏置运放 BIAS_DRV1，U2 永远保持 0xC0 不开 RLD）：
 *      - Step 1：先写 cfg[0x03]=0xC0、cfg[0x0D]=0x00、cfg[0x0E]=0x00，等待 >=150 ms 让 2.40V 基准稳定；
 *      - Step 2：EXR1 / RLD1 下写 RLD_SENSP/N=0xFF 且 CONFIG3=0xC4（PD_RLD=1, RLD_MEAS=0, RLDREF_INT=0）。
 *   5. GPIO1/2/4 在板上硬连 GND，GPIO(0x14) 低 4 位必须全为 1（输入 = 0x0F），严禁设推挽输出！
 *   6. 16CH 测试方波（TST1）下：v0.01 AFE-30P 的 U1.17/18 与 U2.17/18 独立悬空，且 PACE(0x15)=0x00 (PD_PACE=0)
 *      不向 17/18 脚外驱，因此 U1 与 U2 均置 CONFIG2(0x02)=0x10 (INT_TEST=1)，确保 CH1..16 全 16 路均有 1 Hz 方波。
 */
static inline bool c08b_build_ads1298_regs(
    uint8_t req_mode, uint16_t fs_hz, int chip_idx,
    uint8_t cfg[0x1A], uint8_t mask[0x1A],
    uint8_t *cfg3_step2, uint8_t *rld_sens_step2)
{
    C08B_MEMSET(cfg, 0, 0x1A);
    C08B_MEMSET(mask, 0, 0x1A);
    if (cfg3_step2) *cfg3_step2 = 0x00u;
    if (rld_sens_step2) *rld_sens_step2 = 0x00u;

    uint8_t dr;
    if (fs_hz == 500u)       dr = 0x86u; /* HR=1, DR=110 -> 500 SPS */
    else if (fs_hz == 1000u) dr = 0x85u; /* HR=1, DR=101 -> 1000 SPS */
    else if (fs_hz == 2000u) dr = 0x84u; /* HR=1, DR=100 -> 2000 SPS */
    else return false;

    uint8_t ch_mux;
    bool use_rld = false;
    bool int_test = false;
    switch (req_mode) {
    case C08B_MODE_TST1: ch_mux = 0x05u; int_test = true; break;
    case C08B_MODE_SHT1: ch_mux = 0x01u; break;
    case C08B_MODE_EXT1: ch_mux = 0x00u; break;
    case C08B_MODE_EXR1: ch_mux = 0x00u; use_rld = true; break;
    case C08B_MODE_RLD1: ch_mux = 0x00u; use_rld = true; break;
    default: return false;
    }

    cfg[0x01] = dr;
    cfg[0x02] = int_test ? 0x10u : 0x00u; /* 1 Hz 测试方波（U1/U2 均开启片内测试源，兼容 v0.01 独立悬空 17/18 脚） */
    cfg[0x03] = 0xC0u;                    /* Step 1：仅开 2.40V 内部基准，VREF_4V=0，RLD_MEAS=0，RLDREF_INT=0，PD_RLD=0 */
    for (int a = 0x05; a <= 0x0C; a++) cfg[a] = ch_mux; /* 增益 6（000），按模式选 MUX（严禁 0x02 RLD_MEASURE） */
    cfg[0x0D] = 0x00u;                    /* Step 1 先断开 RLD_SENSP/N，等基准稳定后再合上 */
    cfg[0x0E] = 0x00u;
    cfg[0x14] = 0x0Fu;                    /* GPIO1..4 全输入（防接地脚短路） */
    cfg[0x16] = 0x20u;                    /* RESP bit5 必写 1 */

    if (use_rld && chip_idx == 0) {
        /* Step 2：严禁置 VREF_4V(0x20)/RLD_MEAS(0x10)/RLDREF_INT(0x08)！恒为 0xC4 (PD_REFBUF=1 | PD_RLD=1) */
        if (cfg3_step2) *cfg3_step2 = 0xC4u;
        if (rld_sens_step2) *rld_sens_step2 = 0xFFu;
    }

    mask[0x01] = 0xFFu;
    mask[0x02] = 0x3Fu;
    mask[0x03] = 0xFEu;                   /* bit0 RLD_STAT 只读 */
    for (int a = 0x04; a <= 0x11; a++) mask[a] = 0xFFu;
    mask[0x14] = 0x0Fu;                   /* 低 4 位为方向控制位，高 4 位是引脚电平只读 */
    for (int a = 0x15; a <= 0x19; a++) mask[a] = 0xFFu;
    return true;
}

/* 生成 ADS1292 寄存器配置（0x01..0x0B，TI SBAS502C §9.6.1）。
 * 关键规则：
 *   - RESP1(0x09)=0x02，RESP2(0x0A)=0x07（表 24 非 R 版 bit2 必写 1，RLDREF_INT=1，bit0=1）
 *   - GPIO(0x0B)=0x0C（两脚全输入，板上 R21/R22 47k 下拉）
 *   - EXR1 / RLD1 两步开 RLD：cfg[0x06] 先给第 1 步 0x20（仅开 PDB_RLD 预热 >=150ms），
 *     *rld_sens_step2 返回第 2 步 0x23（仅把 CH1 接入 RLD 反馈保证相位裕度）。
 */
static inline bool c08b_build_ads1292_regs(
    uint8_t req_mode, uint16_t fs_hz, uint8_t cfg[0x0C], uint8_t mask[0x0C], uint8_t *rld_sens_step2)
{
    C08B_MEMSET(cfg, 0, 0x0C);
    C08B_MEMSET(mask, 0, 0x0C);
    if (rld_sens_step2) *rld_sens_step2 = 0x00u;

    uint8_t dr;
    if (fs_hz == 500u)       dr = 0x02u; /* 500 SPS */
    else if (fs_hz == 1000u) dr = 0x03u; /* 1000 SPS */
    else if (fs_hz == 2000u) dr = 0x04u; /* 2000 SPS */
    else return false;

    uint8_t cfg2 = 0xA0u; /* bit7=1, PDB_REFBUF=1(内部 2.42V 基准) */
    uint8_t ch1 = 0x00u, ch2 = 0x00u, rld1 = 0x00u, rld2 = 0x00u;
    switch (req_mode) {
    case C08B_MODE_TST1: cfg2 = 0xA3u; ch1 = 0x05u; ch2 = 0x05u; break; /* TEST_FREQ=1 (1 Hz 方波；写 0xA2 是直流) */
    case C08B_MODE_SHT1: ch1 = 0x01u; ch2 = 0x01u; break;
    case C08B_MODE_EXT1: ch1 = 0x00u; ch2 = 0x00u; break;
    case C08B_MODE_EXR1: ch1 = 0x00u; ch2 = 0x00u; rld1 = 0x20u; rld2 = 0x23u; break;
    case C08B_MODE_RLD1: ch1 = 0x00u; ch2 = 0x02u; rld1 = 0x20u; rld2 = 0x23u; break;
    default: return false;
    }

    cfg[0x01] = dr;
    cfg[0x02] = cfg2;
    cfg[0x03] = 0x10u; /* LOFF bit4=1 */
    cfg[0x04] = ch1;
    cfg[0x05] = ch2;
    cfg[0x06] = rld1;  /* 第 1 步只开运放不接电极开关 */
    cfg[0x07] = 0x00u;
    cfg[0x09] = 0x02u; /* RESP1 bit1=1 */
    cfg[0x0A] = 0x07u; /* RESP2 = 0x07 (bit2=1, RLDREF_INT=1, bit0=1) */
    cfg[0x0B] = 0x0Cu; /* GPIO 全输入 */
    if (rld_sens_step2) *rld_sens_step2 = rld2;

    mask[0x01] = 0x87u;
    mask[0x02] = 0x7Bu;
    mask[0x03] = 0xFFu;
    mask[0x04] = 0xFFu;
    mask[0x05] = 0xFFu;
    mask[0x06] = 0x3Fu;
    mask[0x07] = 0x3Fu;
    /* 0x08 LOFF_STAT 只读，mask=0 不写不核 */
    mask[0x09] = 0xFFu;
    mask[0x0A] = 0x87u;
    mask[0x0B] = 0x0Cu;
    return true;
}

/* ---------- 4. CRC16-CCITT（初值 0xFFFF，多项式 0x1021） ---------- */
static inline uint16_t c08b_crc16(const void *p, size_t n)
{
    const uint8_t *b = (const uint8_t *)p;
    uint16_t c = 0xFFFFu;
    while (n--) {
        c ^= (uint16_t)(*b++) << 8;
        for (int i = 0; i < 8; i++)
            c = (c & 0x8000u) ? (uint16_t)((c << 1) ^ 0x1021u) : (uint16_t)(c << 1);
    }
    return c;
}

/* ---------- 5. L432 <-> nRF52840 SPI3/SPIS1 双向流式帧 ---------- */
#define C08B_LINK_TX_MAGIC   0xC853u
#define C08B_LINK_RX_MAGIC   0x53C8u
#define C08B_LINK_VERSION    1u
#define C08B_LINK_MAX_BATCH  4u
#define C08B_RAW_SLOT_BYTES  54u  /* 16CH: status_a[3]+ch1..8[24]+status_b[3]+ch9..16[24]；8CH/2CH 用前 27B */

/* state_flags 位定义 */
enum {
    C08B_SF_ACTIVE        = 1u << 0,
    C08B_SF_BENCH_MEAS    = 1u << 1,
    C08B_SF_L432_VBUS     = 1u << 2,
    C08B_SF_AVDD_OK       = 1u << 3,
    C08B_SF_IMU_OK        = 1u << 4,
};

/* F01 flags 位定义（对齐 offline-f01/codec.py） */
enum {
    C08B_F01_SYNTHETIC     = 1u << 0,
    C08B_F01_SESSION_START = 1u << 1,
    C08B_F01_RECONFIGURE   = 1u << 2,
};

/* nRF -> L432 状态位 */
enum {
    C08B_NF_VBUS_INTERLOCK = 1u << 0,
    C08B_NF_OE_OFF         = 1u << 1,
    C08B_NF_BLE_SUBSCRIBED = 1u << 2,
};

typedef struct __attribute__((packed)) {
    uint16_t magic;               /* 0xC853 */
    uint8_t  version;             /* 1 */
    uint8_t  afe_mode;            /* c08b_afe_mode_t: 0 / 2 / 8 / 16 */
    uint8_t  state_flags;         /* C08B_SF_* */
    uint8_t  fault;               /* c08b_fault_t */
    uint8_t  sample_count;        /* 本帧携带样本数：0（心跳）.. 4 */
    uint8_t  f01_flags;           /* C08B_F01_*（应用于本批第 1 个包） */
    uint32_t seq_first;           /* 本批首个样本序号 */
    uint64_t timestamp_us;        /* 本批首个样本微秒时间戳（L432_DWT_1MHz） */
    uint32_t produced;            /* 会话累计产出样本数 */
    uint32_t dropped;             /* 会话累计因 LINK 未就绪丢弃样本数 */
    uint16_t bad_status;          /* 状态头错误计数 */
    uint16_t drdy_desync;         /* 16CH 双片 DRDY 失步计数 */
    uint16_t min_interval_us_sat; /* 最短 DRDY 间隔 µs（未满 2 沿时置 0xFFFF） */
    uint8_t  id_a;
    uint8_t  id_b;
    uint8_t  active_mode;         /* 当前运行 c08b_req_mode_t */
    uint8_t  imu_fresh;           /* 1 = 本帧携带新采到的 6 轴 IMU 样本 */
    uint16_t imu_read_us;         /* L432 I2C 读取耗时 µs（< 9000） */
    uint16_t ack_epoch_lo;        /* L432 已生效的 cmd_epoch 低 16 位（供 nRF 过滤在线切档时的异步在途旧帧） */
    uint64_t imu_timestamp_us;    /* 同源 L432_DWT_1MHz 64 位 IMU 采样微秒时间戳 */
    int16_t  imu_raw[6];          /* gx, gy, gz, ax, ay, az（对齐 host/v12_imu.py 顺序） */
    uint8_t  samples[C08B_LINK_MAX_BATCH][C08B_RAW_SLOT_BYTES];
    uint16_t crc;                 /* 覆盖前面全部 278 字节 */
} c08b_link_tx_t;

#define C08B_LINK_TX_CRC_LEN offsetof(c08b_link_tx_t, crc)
_Static_assert(sizeof(c08b_link_tx_t) == 280, "c08b_link_tx_t 尺寸固定 280 字节（4字节对齐）");

typedef struct __attribute__((packed)) {
    uint16_t magic;            /* 0x53C8 */
    uint8_t  version;          /* 1 */
    uint8_t  req_mode;         /* c08b_req_mode_t */
    uint8_t  nrf_flags;        /* C08B_NF_* */
    uint8_t  synth_channels;   /* SYN1 请求的模拟通道档位：2 / 8 / 16（默认 16） */
    uint16_t fs_hz;            /* 请求采样率：500 / 1000 / 2000 */
    uint32_t cmd_epoch;        /* 每次新命令递增，防重复触发 */
    uint16_t reserved;
    uint16_t crc;
} c08b_link_rx_t;

#define C08B_LINK_RX_CRC_LEN offsetof(c08b_link_rx_t, crc)
_Static_assert(sizeof(c08b_link_rx_t) == 16, "c08b_link_rx_t 尺寸固定 16 字节");

static inline void c08b_link_tx_seal(c08b_link_tx_t *f)
{
    f->magic = C08B_LINK_TX_MAGIC;
    f->version = C08B_LINK_VERSION;
    f->crc = c08b_crc16(f, C08B_LINK_TX_CRC_LEN);
}

static inline bool c08b_link_tx_ok(const c08b_link_tx_t *f)
{
    if (f->magic != C08B_LINK_TX_MAGIC || f->version != C08B_LINK_VERSION) return false;
    if (f->sample_count > C08B_LINK_MAX_BATCH) return false;
    if (f->afe_mode != AFE_NONE && f->afe_mode != AFE_2CH &&
        f->afe_mode != AFE_8CH && f->afe_mode != AFE_16CH) return false;
    if (f->f01_flags & ~7u) return false;
    if (f->imu_fresh && f->imu_read_us >= 9000u) return false;
    return f->crc == c08b_crc16(f, C08B_LINK_TX_CRC_LEN);
}

static inline void c08b_link_rx_seal(c08b_link_rx_t *c)
{
    c->magic = C08B_LINK_RX_MAGIC;
    c->version = C08B_LINK_VERSION;
    c->crc = c08b_crc16(c, C08B_LINK_RX_CRC_LEN);
}

static inline bool c08b_link_rx_ok(const c08b_link_rx_t *c)
{
    if (c->magic != C08B_LINK_RX_MAGIC || c->version != C08B_LINK_VERSION) return false;
    return c->crc == c08b_crc16(c, C08B_LINK_RX_CRC_LEN);
}

/* 递增 32 位命令纪元并跳过低 16 位 0x0000 回绕值，保证 await_epoch_lo 判别标志始终非 0 */
static inline uint32_t c08b_next_cmd_epoch(uint32_t cur)
{
    cur++;
    if ((uint16_t)cur == 0u) cur++;
    return cur;
}

/* 判断 L432 发来的 280B 帧是否属于当前生效的控制命令纪元（cmd_epoch）。
 * 在同一条连接上热切通道档位或采样率（如 16CH@1000 -> 8CH@2000）时，nRF 先推进 cmd_epoch 并置 *await_epoch_lo != 0；
 * 此时 SPI3 流水线上尚未感知新命令的旧会话在途帧（f->ack_epoch_lo != *await_epoch_lo）必须被丢弃，
 * 直至 L432 确认新纪元（或主动带 SESSION_START 且纪元匹配）才放行，杜绝旧 16CH 槽位混入新 8CH 包或抢占 IMU seq=0。 */
static inline bool c08b_bridge_accept_frame(const c08b_link_tx_t *f, uint16_t *await_epoch_lo)
{
    if (!await_epoch_lo || *await_epoch_lo == 0u) return true;
    if (f->ack_epoch_lo != *await_epoch_lo) return false;
    *await_epoch_lo = 0u;
    return true;
}

/* ---------- 6. BLE GATT F01 数据包与 64B 状态特征编码器 ----------
 *
 * 16B 公共包头（小端，完全对齐 offline-f01/codec.py）：
 *   [0] version : 1（8CH/2CH 27B 帧 或 IMU）| 4（16CH 54B 双片无损帧）
 *   [1] kind    : 1（EMG ADC）| 2（6 轴 IMU）
 *   [2] count   : 样本帧数（v1 ADC: 1..8；v4 16CH ADC: 1..4；IMU: 1）
 *   [3] flags   : bit0=SYNTHETIC, bit1=SESSION_START, bit2=RECONFIGURE
 *   [4..7]  seq : uint32 LE（首帧样本序号；SESSION_START 时必为 0）
 *   [8..15] ts  : uint64 LE（微秒时间戳，同源 L432_DWT_1MHz）
 */
#define C08B_F01_HEADER_BYTES   16u
#define C08B_F01_FRAME_8CH      27u
#define C08B_F01_FRAME_16CH     54u
#define C08B_F01_MAX_PKT_BYTES  232u /* 16 + 8*27 == 16 + 4*54 == 232 <= 244 (MTU 247) */
#define C08B_IMU_PKT_BYTES      36u  /* 对齐 host/v12_imu.py：16B 头 + 20B 帧 */
#define C08B_STATUS_BYTES       64u  /* 对齐 host/v12_status.py version=1 */

static inline void c08b_put_u16_le(uint8_t *p, uint16_t v)
{
    p[0] = (uint8_t)v; p[1] = (uint8_t)(v >> 8);
}

static inline void c08b_put_u32_le(uint8_t *p, uint32_t v)
{
    p[0] = (uint8_t)v; p[1] = (uint8_t)(v >> 8);
    p[2] = (uint8_t)(v >> 16); p[3] = (uint8_t)(v >> 24);
}

static inline void c08b_put_u64_le(uint8_t *p, uint64_t v)
{
    c08b_put_u32_le(p, (uint32_t)v);
    c08b_put_u32_le(p + 4, (uint32_t)(v >> 32));
}

static inline void c08b_put_s24_be(uint8_t *p, int32_t v)
{
    p[0] = (uint8_t)((uint32_t)v >> 16);
    p[1] = (uint8_t)((uint32_t)v >> 8);
    p[2] = (uint8_t)((uint32_t)v);
}

static inline int32_t c08b_get_s24_be(const uint8_t *p)
{
    int32_t v = ((int32_t)p[0] << 16) | ((int32_t)p[1] << 8) | (int32_t)p[2];
    return (v << 8) >> 8;
}

static inline size_t c08b_pack_f01_header(
    uint8_t out[16], uint8_t version, uint8_t kind, uint8_t count,
    uint8_t flags, uint32_t seq, uint64_t ts_us)
{
    if (flags & ~7u) return 0;
    if ((flags & C08B_F01_SESSION_START) && seq != 0u) return 0;
    if ((flags & C08B_F01_RECONFIGURE) && !(flags & C08B_F01_SESSION_START)) return 0;
    out[0] = version;
    out[1] = kind;
    out[2] = count;
    out[3] = flags;
    c08b_put_u32_le(out + 4, seq);
    c08b_put_u64_le(out + 8, ts_us);
    return C08B_F01_HEADER_BYTES;
}

/* 打包 8CH / 2CH 标准 F01 v1 数据包（16 + count*27 字节，100% 兼容 offline-f01/codec.py） */
static inline size_t c08b_pack_f01_v1_8ch(
    uint8_t *out, size_t cap, uint8_t count, uint8_t flags,
    uint32_t seq, uint64_t ts_us, const uint8_t frames[][27])
{
    if (count < 1u || count > 8u) return 0;
    size_t need = C08B_F01_HEADER_BYTES + (size_t)count * C08B_F01_FRAME_8CH;
    if (cap < need) return 0;
    if (!c08b_pack_f01_header(out, 1u, 1u, count, flags, seq, ts_us)) return 0;
    for (uint8_t i = 0; i < count; i++) {
        C08B_MEMCPY(out + C08B_F01_HEADER_BYTES + (size_t)i * 27u, frames[i], 27u);
    }
    return need;
}

/* 打包 16CH 扩展 F01 v4 无损双片数据包（16 + count*54 字节，count=1..4，最大 232 字节） */
static inline size_t c08b_pack_f01_v4_16ch(
    uint8_t *out, size_t cap, uint8_t count, uint8_t flags,
    uint32_t seq, uint64_t ts_us, const uint8_t frames[][54])
{
    if (count < 1u || count > 4u) return 0;
    size_t need = C08B_F01_HEADER_BYTES + (size_t)count * C08B_F01_FRAME_16CH;
    if (cap < need) return 0;
    if (!c08b_pack_f01_header(out, 4u, 1u, count, flags, seq, ts_us)) return 0;
    for (uint8_t i = 0; i < count; i++) {
        C08B_MEMCPY(out + C08B_F01_HEADER_BYTES + (size_t)i * 54u, frames[i], 54u);
    }
    return need;
}

/* 打包 36 字节 IMU 数据包（100% 对齐 host/v12_imu.py:decode） */
static inline size_t c08b_pack_imu_pkt(
    uint8_t out[36], uint8_t flags, uint32_t seq, uint64_t ts_us,
    const int16_t gyro_accel[6], uint32_t read_latency_us)
{
    if (read_latency_us >= 9000u) return 0;
    if (!c08b_pack_f01_header(out, 1u, 2u, 1u, flags, seq, ts_us)) return 0;
    for (int i = 0; i < 6; i++) {
        c08b_put_u16_le(out + 16 + i * 2, (uint16_t)gyro_accel[i]);
    }
    out[28] = 3u; /* XLDA|GDA 新鲜度位 = 3 */
    out[29] = 0u; out[30] = 0u; out[31] = 0u;
    c08b_put_u32_le(out + 32, read_latency_us);
    return C08B_IMU_PKT_BYTES;
}

/* 编码 64 字节 STATUS 特征（100% 对齐 host/v12_status.py version=1） */
typedef struct {
    uint64_t produced;
    uint64_t ring_dropped;
    uint64_t scheduler_skipped;
    uint64_t sent_samples;
    uint64_t notify_failures;
    uint8_t  fault;
    bool     active;
    bool     bench_measured;
    uint32_t ads_status;
    uint64_t drdy_raw_edges;
    uint32_t drdy_min_interval_us;
    uint32_t spi_hz;
} c08b_ble_status_t;

static inline void c08b_encode_ble_status(uint8_t out[64], const c08b_ble_status_t *s)
{
    C08B_MEMSET(out, 0, 64);
    c08b_put_u64_le(out + 0,  s->produced);
    c08b_put_u64_le(out + 8,  s->ring_dropped);
    c08b_put_u64_le(out + 16, s->scheduler_skipped);
    c08b_put_u64_le(out + 24, s->sent_samples);
    c08b_put_u64_le(out + 32, s->notify_failures);
    out[40] = s->fault;
    out[41] = s->active ? 1u : 0u;
    out[42] = s->bench_measured ? 1u : 0u;
    out[43] = 1u; /* status_version = 1 (64 bytes) */
    c08b_put_u32_le(out + 44, s->ads_status);
    c08b_put_u64_le(out + 48, s->drdy_raw_edges);
    uint32_t min_iv = (s->drdy_raw_edges < 2u) ? 0xFFFFFFFFu :
                      (s->drdy_min_interval_us == 0xFFFFFFFFu ? 0xFFFFFFFEu : s->drdy_min_interval_us);
    c08b_put_u32_le(out + 56, min_iv);
    c08b_put_u32_le(out + 60, s->spi_hz);
}

/* 生成确定性合成帧（SYN1 链路测试用，不开 ANA_EN / AFE 供电） */
static inline void c08b_fill_synth_slot(
    uint8_t slot[54], c08b_afe_mode_t mode, uint32_t sample_seq)
{
    C08B_MEMSET(slot, 0, 54);
    slot[0] = 0xC0u; slot[1] = 0x00u; slot[2] = 0x00u;
    int ch_a = (mode == AFE_2CH) ? 2 : 8;
    for (int ch = 0; ch < ch_a; ch++) {
        int32_t code = (int32_t)((sample_seq & 0x3FFu) - 512) * (ch + 1) * 16;
        c08b_put_s24_be(&slot[3 + ch * 3], code);
    }
    if (mode == AFE_16CH) {
        slot[27] = 0xC0u; slot[28] = 0x00u; slot[29] = 0x00u;
        for (int ch = 0; ch < 8; ch++) {
            int32_t code = (int32_t)((sample_seq & 0x3FFu) - 512) * (ch + 9) * 16;
            c08b_put_s24_be(&slot[30 + ch * 3], code);
        }
    }
}

/* ---------- 7. V12 BLE 128-bit UUID 与 META JSON 生成器（固件与主机单测共用） ----------
 * V12 统一 UUID：7b24c101-3948-4f03-9d11-12bb9d0000XX（XX = 01..06）
 * Nordic S140 sd_ble_uuid_vs_add 使用小端 16 字节，且用 16-bit uuid 覆盖 bytes[12..13]（即 0xC101）。
 */
#define C08B_V12_UUID_BYTES12_13 0xC101u

static inline void c08b_v12_uuid128_le(uint8_t suffix, uint8_t out16[16])
{
    static const uint8_t tmpl[16] = {
        0x00u, 0x00u, 0x00u, 0x9du, 0xbbu, 0x12u, 0x11u, 0x9du,
        0x03u, 0x4fu, 0x48u, 0x39u, 0x01u, 0xc1u, 0x24u, 0x7bu
    };
    C08B_MEMCPY(out16, tmpl, 16);
    out16[0] = suffix;
}

static inline size_t c08b_append_str(char *buf, size_t cap, size_t pos, const char *s)
{
    while (*s) {
        if (pos + 1u < cap) buf[pos] = *s;
        pos++;
        s++;
    }
    return pos;
}

static inline size_t c08b_append_u32(char *buf, size_t cap, size_t pos, uint32_t v)
{
    char tmp[12];
    int n = 0;
    if (v == 0u) {
        tmp[n++] = '0';
    } else {
        while (v > 0u) {
            tmp[n++] = (char)('0' + (v % 10u));
            v /= 10u;
        }
    }
    while (n > 0) {
        if (pos + 1u < cap) buf[pos] = tmp[--n];
        else --n;
        pos++;
    }
    return pos;
}

static inline uint32_t c08b_spi_hz_for_mode(c08b_afe_mode_t mode)
{
    return (mode == AFE_NONE || mode == AFE_2CH) ? 1000000u : 4000000u;
}

static inline int c08b_format_meta_json(
    char *buf, size_t cap, c08b_afe_mode_t mode, uint16_t fs_hz,
    bool bench_measured, bool imu_enabled)
{
    if (cap == 0u) return 0;
    /* 16CH 走无损双片协议 4（channels=16）；8CH / 2CH / 未探测 NONE 走协议 1（channels=8，active_channels=8/2/0） */
    uint32_t proto   = (mode == AFE_16CH) ? 4u : 1u;
    uint32_t ch_wire = (mode == AFE_16CH) ? 16u : 8u;
    uint32_t ch_act  = (mode == AFE_NONE) ? 0u : (mode == AFE_2CH) ? 2u : (mode == AFE_8CH) ? 8u : 16u;
    uint32_t vref_mv = (mode == AFE_2CH) ? 2420u : 2400u;
    uint32_t spi_hz  = c08b_spi_hz_for_mode(mode);
    const char *afe_str = (mode == AFE_NONE) ? "NONE" :
                          (mode == AFE_2CH)  ? "ADS1292" :
                          (mode == AFE_8CH)  ? "ADS1298_SINGLE" : "ADS1298_DUAL";

    size_t p = 0;
    p = c08b_append_str(buf, cap, p, "{\"profile\":\"C08B_DUAL_STREAM_CANDIDATE\",\"board\":\"C08B_R4U6\",\"afe\":\"");
    p = c08b_append_str(buf, cap, p, afe_str);
    p = c08b_append_str(buf, cap, p, "\",\"build_id\":\"" MAKO_C08B_BUILD_ID "\",\"protocol\":");
    p = c08b_append_u32(buf, cap, p, proto);
    p = c08b_append_str(buf, cap, p, ",\"channels\":");
    p = c08b_append_u32(buf, cap, p, ch_wire);
    p = c08b_append_str(buf, cap, p, ",\"active_channels\":");
    p = c08b_append_u32(buf, cap, p, ch_act);
    p = c08b_append_str(buf, cap, p, ",\"fs_Hz\":");
    p = c08b_append_u32(buf, cap, p, fs_hz);
    p = c08b_append_str(buf, cap, p, ",\"spi_Hz\":");
    p = c08b_append_u32(buf, cap, p, spi_hz);
    p = c08b_append_str(buf, cap, p, ",\"vref_mV\":");
    p = c08b_append_u32(buf, cap, p, vref_mv);
    p = c08b_append_str(buf, cap, p, ",\"gain\":6,\"bench_measured\":");
    p = c08b_append_str(buf, cap, p, bench_measured ? "true" : "false");
    p = c08b_append_str(buf, cap, p, ",\"imu_enabled\":");
    p = c08b_append_str(buf, cap, p, imu_enabled ? "true" : "false");
    p = c08b_append_str(buf, cap, p, ",\"clock_source\":\"L432_DWT_1MHz\",\"clock_resolution_us\":1,"
                                     "\"usb_interlock\":\"HW_U10_OE_N_AND_SW_DUAL_MCU\"}");
    buf[p < cap ? p : cap - 1u] = '\0';
    return (p < cap) ? (int)p : -1;
}

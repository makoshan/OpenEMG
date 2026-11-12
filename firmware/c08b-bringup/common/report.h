/* L432 自检报告：L432 经 LINK SPI（SPI3 主机）发给 nRF52840（SPIS 从机），两边共用这一个定义。 */
#pragma once
#include <stddef.h>
#include <stdint.h>

#define REPORT_MAGIC   0xC08Bu
#define REPORT_VERSION 1u

/* 自检项编号：done_mask / fail_mask 的位号。LED 闪码 = 第一个失败项编号 + 1。 */
enum {
    T_ADS_A_ID = 0,  /* U1（CS_A）ID == 0x92 */
    T_ADS_B_ID,      /* U2（CS_B）ID == 0x92 */
    T_REG_A,         /* U1 写寄存器后逐个回读一致 */
    T_REG_B,         /* U2 同上 */
    T_DRDY,          /* 两片 DRDY 按时出现、采样率 500 Hz ±2%、两片同步 */
    T_STATUS,        /* 每帧状态字高 4 位 = 0xC */
    T_TEST_SIG,      /* 内部方波：16 路峰峰值都在 0.5–5 mV，且都在中位数 ±20% 内 */
    T_NOISE,         /* 输入短接：16 路 RMS 都 < 5 µV */
    T_IMU_ID,        /* LSM6DS3TR-C WHO_AM_I == 0x6A */
    T_IMU_G,         /* 静止加速度模长 0.8–1.2 g */
    T_COUNT
};

typedef struct __attribute__((packed)) {
    uint16_t magic;
    uint16_t version;
    uint32_t seq;               /* 第几次发送 */
    uint16_t done_mask;         /* 做过的项 */
    uint16_t fail_mask;         /* 没过的项 */
    uint8_t  id_a, id_b;        /* 读到的 ID 原值 */
    uint8_t  reg_bad_a, reg_bad_b;  /* 回读不一致的寄存器个数 */
    uint16_t rate_hz_x10;       /* 实测 DRDY 频率 ×10 */
    uint16_t drdy_desync;       /* DRDY_A 来时 DRDY_B 不是低电平的帧数 */
    uint16_t bad_status;        /* 状态字不对的帧数 */
    uint16_t frames;            /* 方波阶段采到的帧数 */
    uint16_t sig_pp_uv[16];     /* 方波峰峰值，µV；CH1–8 = U1，CH9–16 = U2 */
    uint16_t noise_rms_nv[16];  /* 短接底噪 RMS，nV（饱和到 65535） */
    uint8_t  imu_id;
    int16_t  imu_mg[3];         /* 加速度 x/y/z，mg */
    uint16_t crc;               /* CRC16-CCITT（初值 0xFFFF），覆盖前面所有字节 */
} c08b_report_t;

#define REPORT_CRC_LEN offsetof(c08b_report_t, crc)
_Static_assert(sizeof(c08b_report_t) == 97, "报告结构尺寸变了：L432、nRF 两边要一起改");

static inline uint16_t crc16_ccitt(const void *p, size_t n)
{
    const uint8_t *b = (const uint8_t *)p;
    uint16_t c = 0xFFFF;
    while (n--) {
        c ^= (uint16_t)(*b++) << 8;
        for (int i = 0; i < 8; i++) c = (c & 0x8000) ? (uint16_t)((c << 1) ^ 0x1021) : (uint16_t)(c << 1);
    }
    return c;
}

static inline void report_seal(c08b_report_t *r) { r->crc = crc16_ccitt(r, REPORT_CRC_LEN); }
static inline int report_ok(const c08b_report_t *r)
{
    return r->magic == REPORT_MAGIC && r->version == REPORT_VERSION && r->crc == crc16_ccitt(r, REPORT_CRC_LEN);
}

static const char *const TEST_NAME[T_COUNT] = {
    "ADS_A_ID", "ADS_B_ID", "REG_A", "REG_B", "DRDY", "STATUS", "TEST_SIG", "NOISE", "IMU_ID", "IMU_G",
};

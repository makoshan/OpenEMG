/* L432 自检报告：L432 经 LINK SPI（SPI3 主机）发给 nRF52840（SPIS 从机），两边共用这一个定义。
   支持共用主控（R4U6 / R4U6N）零跳线自动识别三档下层采集板：
   - 16CH：双片 ADS1298/R（D20 / D20N）
   - 8CH ：单面单片 ADS1298/R（D20-8CH / D20N-8CH，B 片未贴）
   - 2CH ：双通道六触点 ADS1292/R（ADS1292-2ch-R9，B 片未贴） */
#pragma once
#include <stddef.h>
#include <stdint.h>

#define REPORT_MAGIC   0xC08Bu
#define REPORT_VERSION 1u

/* 芯片 ID 判别：ADS1298/R 低 5 位固定 0x12（0x92/0xD2）；ADS1292/R 固定 0x53/0x73 */
#define ADS1298_ID_OK(id) (((id) & 0x1Fu) == 0x12u)
#define ADS1292_ID_OK(id) (((id) & 0xDFu) == 0x53u)
#define ADS_B_ABSENT(id)  ((id) == 0x00u || (id) == 0xFFu)

typedef enum {
    AFE_NONE = 0,
    AFE_2CH  = 2,
    AFE_8CH  = 8,
    AFE_16CH = 16,
} afe_mode_t;

/* 自检项编号：done_mask / fail_mask 的位号。LED 闪码 = 第一个失败项编号 + 1。 */
enum {
    T_ADS_A_ID = 0,  /* U1（CS_A）ID：ADS1298(0x92/0xD2) 或 ADS1292(0x53/0x73) */
    T_ADS_B_ID,      /* U2（CS_B）ID：16CH 下要求 ADS1298；8CH/2CH 未贴跳过 */
    T_REG_A,         /* U1 写寄存器后逐个回读一致 */
    T_REG_B,         /* U2 同上（16CH 下执行；8CH/2CH 跳过） */
    T_DRDY,          /* DRDY 按时出现、采样率 500 Hz 达标（16CH 另核双片同步） */
    T_STATUS,        /* 每帧状态字高 4 位 = 0xC（2CH 另核 AVDD_SENSE 高电平） */
    T_TEST_SIG,      /* 内部方波：有效通道峰峰值都在 0.5–5 mV，且在中位数 ±20% 内 */
    T_NOISE,         /* 输入短接：有效通道底噪 RMS 在 100 nV–5 µV */
    T_IMU_ID,        /* LSM6DS3TR-C WHO_AM_I == 0x6A */
    T_IMU_G,         /* 静止加速度模长 0.8–1.2 g */
    T_COUNT
};

static inline afe_mode_t afe_detect(uint8_t id_a, uint8_t id_b)
{
    if (ADS1298_ID_OK(id_a) && ADS1298_ID_OK(id_b)) return AFE_16CH;
    if (ADS1298_ID_OK(id_a) && ADS_B_ABSENT(id_b))  return AFE_8CH;
    if (ADS1292_ID_OK(id_a) && ADS_B_ABSENT(id_b))  return AFE_2CH;
    return AFE_NONE;
}

static inline uint16_t report_expected_done(uint8_t id_a, uint8_t id_b)
{
    afe_mode_t m = afe_detect(id_a, id_b);
    uint16_t all = (uint16_t)((1u << T_COUNT) - 1u);
    if (m == AFE_8CH || m == AFE_2CH)
        return (uint16_t)(all & ~((1u << T_ADS_B_ID) | (1u << T_REG_B))); /* 0x03F5 */
    return all;                                                            /* 0x03FF */
}

static inline const char *afe_mode_name(afe_mode_t m)
{
    switch (m) {
    case AFE_16CH: return "16CH 双片ADS1298";
    case AFE_8CH:  return "8CH 单面ADS1298";
    case AFE_2CH:  return "2CH 六触点ADS1292";
    default:       return "未识别或未接采集板";
    }
}

typedef struct __attribute__((packed)) {
    uint16_t magic;
    uint16_t version;
    uint32_t seq;               /* 第几次发送 */
    uint16_t done_mask;         /* 做过的项 */
    uint16_t fail_mask;         /* 没过的项 */
    uint8_t  id_a, id_b;        /* 读到的 ID 原值 */
    uint8_t  reg_bad_a, reg_bad_b;  /* 回读不一致的寄存器个数 */
    uint16_t rate_hz_x10;       /* 实测 DRDY 频率 ×10 */
    uint16_t drdy_desync;       /* DRDY_A 来时 DRDY_B 不是低电平的帧数（仅 16CH） */
    uint16_t bad_status;        /* 状态字不对的帧数（2CH 含 AVDD_SENSE 低电平计数） */
    uint16_t frames;            /* 方波阶段采到的帧数 */
    uint16_t sig_pp_uv[16];     /* 方波峰峰值，µV；按有效通道 2/8/16 填入前 N 项 */
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

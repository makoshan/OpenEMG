/* 主机端自检：两颗芯片共用的报告结构、CRC、三档板型自动判别（16CH / 8CH / 2CH）、广播包构造。每条断言都配反例。 */
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "report.h"

#define ADV_ONLY
#include "../nrf/adv_build.inc"

int main(void)
{
    /* 1. CRC16-CCITT（初值 0xFFFF）标准检验值："123456789" → 0x29B1 */
    assert(crc16_ccitt("123456789", 9) == 0x29B1);
    assert(crc16_ccitt("123456780", 9) != 0x29B1);

    /* 2. 报告布局固定：两边都是小端 Cortex-M4，packed 结构 97 字节，CRC 在最后 */
    assert(sizeof(c08b_report_t) == 97);
    assert(REPORT_CRC_LEN == 95);
    assert(T_COUNT <= 16);

    /* 3. 封口后校验通过；改任意一个字节必须校验失败 */
    c08b_report_t r; memset(&r, 0, sizeof r);
    r.magic = REPORT_MAGIC; r.version = REPORT_VERSION; r.done_mask = 0x3FF; r.sig_pp_uv[3] = 1900;
    report_seal(&r);
    assert(report_ok(&r));
    for (size_t i = 0; i < REPORT_CRC_LEN; i++) {
        c08b_report_t t = r; ((unsigned char *)&t)[i] ^= 0x01;
        assert(!report_ok(&t));
    }
    c08b_report_t bad = r; bad.magic = 0x1234; report_seal(&bad); assert(!report_ok(&bad));

    /* 4. 三档采集板自动识别与期望掩码（含损坏 ID 反例） */
    assert(afe_detect(0x92, 0x92) == AFE_16CH && report_expected_done(0x92, 0x92) == 0x03FF);
    assert(afe_detect(0xD2, 0x92) == AFE_16CH && report_expected_done(0xD2, 0x92) == 0x03FF);
    assert(afe_detect(0x92, 0x00) == AFE_8CH  && report_expected_done(0x92, 0x00) == 0x03F5);
    assert(afe_detect(0x92, 0xFF) == AFE_8CH  && report_expected_done(0x92, 0xFF) == 0x03F5);
    assert(afe_detect(0x53, 0x00) == AFE_2CH  && report_expected_done(0x53, 0x00) == 0x03F5);
    assert(afe_detect(0x73, 0xFF) == AFE_2CH  && report_expected_done(0x73, 0xFF) == 0x03F5);
    /* 反例：未接板、A 片死而 B 片活、B 片返回半截乱码、2CH 配有 B 片，均必须判 AFE_NONE 并要求全掩码 0x03FF 触发告警 */
    assert(afe_detect(0x00, 0x00) == AFE_NONE && report_expected_done(0x00, 0x00) == 0x03FF);
    assert(afe_detect(0xFF, 0xFF) == AFE_NONE && report_expected_done(0xFF, 0xFF) == 0x03FF);
    assert(afe_detect(0x00, 0x92) == AFE_NONE && report_expected_done(0x00, 0x92) == 0x03FF);
    assert(afe_detect(0x92, 0x80) == AFE_NONE && report_expected_done(0x92, 0x80) == 0x03FF);
    assert(afe_detect(0x53, 0x92) == AFE_NONE && report_expected_done(0x53, 0x92) == 0x03FF);

    /* 5. 广播包：PDU 头 0x42，长度 = 6 + 23 = 29（≤ 37），AD 结构逐项能走通，厂商数据字段位置正确 */
    uint8_t p[2 + 37]; const uint8_t addr[6] = {1, 2, 3, 4, 5, 0xC6};
    uint8_t n = adv_build(p, addr, 0x03F5, 0x0000, 0x05, 185, 7, 0x92, 0x00);
    assert(n == 2 + 29 && p[0] == 0x42 && p[1] == 29);
    assert(memcmp(p + 2, addr, 6) == 0);
    int off = 8, total = 0;
    while (off < n) { int len = p[off]; assert(len > 0 && off + 1 + len <= n); total += len + 1; off += len + 1; }
    assert(off == n && total == 23 && total <= 31);
    assert(p[8] == 2 && p[9] == 0x01 && p[10] == 0x06);
    assert(p[11] == 5 && p[12] == 0x09 && memcmp(p + 13, "C08B", 4) == 0);
    assert(p[17] == 13 && p[18] == 0xFF && p[19] == 0xFF && p[20] == 0xFF);
    assert(p[21] == 1 && p[22] == 0xF5 && p[23] == 0x03 && p[24] == 0x00 && p[25] == 0x00);
    assert(p[26] == 0x05 && p[27] == 185 && p[28] == 7 && p[29] == 0x92 && p[30] == 0x00);
    puts("主机端测试通过：CRC、报告布局（97 字节）、16CH/8CH/2CH 板型识别与反例、改字节必报错、广播包 29 字节");
    return 0;
}

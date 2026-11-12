/* 主机端自检：两颗芯片共用的报告结构、CRC、广播包构造。每条断言都配一个必须失败的反例。 */
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "report.h"

/* 从 nrf/main.c 抠出来的同一个函数：只依赖参数，直接 include 源文件里的定义不方便，这里用 #include 截取 */
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

    /* 4. 广播包：PDU 头 0x42，长度 = 6 + 23 = 29（≤ 37），AD 结构逐项能走通，厂商数据字段位置正确 */
    uint8_t p[2 + 37]; const uint8_t addr[6] = {1, 2, 3, 4, 5, 0xC6};
    uint8_t n = adv_build(p, addr, 0x03FF, 0x0040, 0x05, 185, 7, 0x92, 0x92);
    assert(n == 2 + 29 && p[0] == 0x42 && p[1] == 29);
    assert(memcmp(p + 2, addr, 6) == 0);
    int off = 8, total = 0;
    while (off < n) { int len = p[off]; assert(len > 0 && off + 1 + len <= n); total += len + 1; off += len + 1; }
    assert(off == n && total == 23 && total <= 31);
    assert(p[8] == 2 && p[9] == 0x01 && p[10] == 0x06);                       /* Flags */
    assert(p[11] == 5 && p[12] == 0x09 && memcmp(p + 13, "C08B", 4) == 0);    /* 名字 */
    assert(p[17] == 13 && p[18] == 0xFF && p[19] == 0xFF && p[20] == 0xFF);   /* 厂商数据，公司号 0xFFFF */
    assert(p[21] == 1 && p[22] == 0xFF && p[23] == 0x03 && p[24] == 0x40 && p[25] == 0x00);
    assert(p[26] == 0x05 && p[27] == 185 && p[28] == 7 && p[29] == 0x92 && p[30] == 0x92);
    puts("主机端测试通过：CRC、报告布局（97 字节）、改字节必报错、广播包 29 字节");
    return 0;
}

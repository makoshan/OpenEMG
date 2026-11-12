/* 广播包构造：nrf/main.c 和 host_test/test_host.c 共用这一份。 */
#include <stdint.h>
/* 厂商数据（公司号 0xFFFF 测试用）：版本、done、fail、nRF 状态位、VBAT/20 mV、报告序号低 8 位、两片 ADS ID */
static uint8_t adv_build(uint8_t *p, const uint8_t addr[6], uint16_t done, uint16_t fail, uint8_t nflags, uint8_t vbat20, uint8_t seq, uint8_t ida, uint8_t idb)
{
    uint8_t n = 0;
    p[n++] = 0x42;                         /* ADV_NONCONN_IND，TxAdd = 随机地址 */
    p[n++] = 0;                            /* 长度，最后填 */
    for (int i = 0; i < 6; i++) p[n++] = addr[i];
    p[n++] = 2; p[n++] = 0x01; p[n++] = 0x06;                  /* Flags */
    p[n++] = 5; p[n++] = 0x09; p[n++] = 'C'; p[n++] = '0'; p[n++] = '8'; p[n++] = 'B';
    p[n++] = 13; p[n++] = 0xFF; p[n++] = 0xFF; p[n++] = 0xFF;  /* 厂商数据，公司号 0xFFFF */
    p[n++] = 1;
    p[n++] = (uint8_t)done; p[n++] = (uint8_t)(done >> 8);
    p[n++] = (uint8_t)fail; p[n++] = (uint8_t)(fail >> 8);
    p[n++] = nflags; p[n++] = vbat20; p[n++] = seq; p[n++] = ida; p[n++] = idb;
    p[1] = (uint8_t)(n - 2);
    return n;
}


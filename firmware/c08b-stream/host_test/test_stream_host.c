/* C08B 双核流式协议、安全门、寄存器表与 BLE F01 v1/v4 打包器主机端 C11 单测（每条配必败反例）。 */
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "stream_proto.h"

static void format_uuid_str(const uint8_t le[16], char out[37])
{
    snprintf(out, 37,
             "%02x%02x%02x%02x-%02x%02x-%02x%02x-%02x%02x-%02x%02x%02x%02x%02x%02x",
             le[15], le[14], le[13], le[12],
             le[11], le[10],
             le[9],  le[8],
             le[7],  le[6],
             le[5],  le[4], le[3], le[2], le[1], le[0]);
}

int main(void)
{
    /* 1. 默认双硬件锁必须全为 0，上电/预热时序与广播名常量核对 */
    assert(MAKO_C08B_AFE_ENABLED == 0);
    assert(MAKO_BENCH_MEASURED == 0);
    assert(C08B_ADS1292_POR_WAIT_MS >= 1000u);
    assert(C08B_ADS_RLD_WARMUP_US >= 150000u);
    assert(strcmp(C08B_BLE_DEV_NAME, "YUANLI-C08B") == 0);

    /* 2. CRC16-CCITT 标准向量与反例 */
    assert(c08b_crc16("123456789", 9) == 0x29B1u);
    assert(c08b_crc16("123456780", 9) != 0x29B1u);

    /* 3. 三档采集板自动识别正反例 */
    assert(c08b_afe_detect(0x92, 0x92) == AFE_16CH);
    assert(c08b_afe_detect(0xD2, 0x92) == AFE_16CH);
    assert(c08b_afe_detect(0x92, 0x00) == AFE_8CH);
    assert(c08b_afe_detect(0x92, 0xFF) == AFE_8CH);
    assert(c08b_afe_detect(0x53, 0x00) == AFE_2CH);
    assert(c08b_afe_detect(0x73, 0xFF) == AFE_2CH);
    assert(c08b_afe_detect(0x00, 0x00) == AFE_NONE);
    assert(c08b_afe_detect(0x00, 0x92) == AFE_NONE); /* 半死 16CH 板绝不能误降级为 8CH */
    assert(c08b_afe_detect(0x92, 0x80) == AFE_NONE); /* B 片乱码绝不能误判为未贴 */
    assert(c08b_afe_detect(0x53, 0x92) == AFE_NONE); /* 混装异常必拒 */

    /* 4. 硬件锁与 VBUS 互锁门禁正反例（含 PRB1 只读探测） */
    assert(c08b_parse_ctrl4((const uint8_t *)"PRB1") == C08B_MODE_PRB1);
    assert(c08b_gate_mode_request(C08B_MODE_SYN1, 1000, false, false) == C08B_FAULT_NONE);
    assert(c08b_gate_mode_request(C08B_MODE_STOP, 1000, false, true)  == C08B_FAULT_NONE);
    /* 锁定态下所有真实 AFE 模式（含 PRB1）必须报 FAULT_LOCKED */
    assert(c08b_gate_mode_request(C08B_MODE_TST1, 1000, false, false) == C08B_FAULT_LOCKED);
    assert(c08b_gate_mode_request(C08B_MODE_SHT1, 1000, false, false) == C08B_FAULT_LOCKED);
    assert(c08b_gate_mode_request(C08B_MODE_EXT1, 1000, false, false) == C08B_FAULT_LOCKED);
    assert(c08b_gate_mode_request(C08B_MODE_EXR1, 1000, false, false) == C08B_FAULT_LOCKED);
    assert(c08b_gate_mode_request(C08B_MODE_RLD1, 1000, false, false) == C08B_FAULT_LOCKED);
    assert(c08b_gate_mode_request(C08B_MODE_PRB1, 1000, false, false) == C08B_FAULT_LOCKED);
    /* 解锁后插着 USB VBUS 必须报 FAULT_INTERLOCK(3) */
    assert(c08b_gate_mode_request(C08B_MODE_TST1, 1000, true, true)   == C08B_FAULT_INTERLOCK);
    assert(c08b_gate_mode_request(C08B_MODE_PRB1, 1000, true, true)   == C08B_FAULT_INTERLOCK);
    assert(c08b_gate_mode_request(C08B_MODE_PRB1, 1000, true, false)  == C08B_FAULT_NONE);
    assert(c08b_gate_mode_request(C08B_MODE_EXR1, 2000, true, false)  == C08B_FAULT_NONE);
    /* 非法采样率必拒 */
    assert(c08b_gate_mode_request(C08B_MODE_TST1, 4000, true, false)  == C08B_FAULT_ARG);

    /* 5. ADS1298 (±2.5V 双电源 + Pin60 RLDREF 硬连 AGND + v0.01 Pin62 RLDIN 硬连 +2.5V + Pin17/18 独立悬空) 寄存器核对：
     *    严禁置 VREF_4V(0x20)、RLD_MEAS(0x10) 与 RLDREF_INT(0x08)（即 (CONFIG3 & 0x38)==0），严禁设 MUX=0x02！
     *    TST1 下 U1 与 U2 均置 CONFIG2=0x10；Step1=0xC0；Step2 EXR1/RLD1=0xC4 */
    uint8_t cfg98_a[0x1A], mask98_a[0x1A], cfg98_b[0x1A], mask98_b[0x1A];
    uint8_t c3_s2_a = 0xFFu, rld_s2_a = 0xFFu, c3_s2_b = 0xFFu, rld_s2_b = 0xFFu;
    assert(c08b_build_ads1298_regs(C08B_MODE_TST1, 1000, 0, cfg98_a, mask98_a, &c3_s2_a, &rld_s2_a));
    assert(c08b_build_ads1298_regs(C08B_MODE_TST1, 1000, 1, cfg98_b, mask98_b, &c3_s2_b, &rld_s2_b));
    assert(cfg98_a[0x01] == 0x85u && cfg98_b[0x01] == 0x85u);
    assert(cfg98_a[0x02] == 0x10u && cfg98_b[0x02] == 0x10u); /* U1 与 U2 均开片内 1 Hz 方波，确保 v0.01 CH9..16 有信号 */
    assert(cfg98_a[0x03] == 0xC0u && cfg98_b[0x03] == 0xC0u);
    assert(c3_s2_a == 0x00u && rld_s2_a == 0x00u && c3_s2_b == 0x00u && rld_s2_b == 0x00u);
    assert(cfg98_a[0x14] == 0x0Fu && cfg98_b[0x14] == 0x0Fu); /* GPIO1..4 输入 */

    /* EXR1：Step 1 先写 0xC0 + 0x00，Step 2 仅 U1 升为 0xC4(PD_RLD=1, RLD_MEAS=0, RLDREF_INT=0) + 0xFF，U2 保持关 RLD */
    assert(c08b_build_ads1298_regs(C08B_MODE_EXR1, 2000, 0, cfg98_a, mask98_a, &c3_s2_a, &rld_s2_a));
    assert(c08b_build_ads1298_regs(C08B_MODE_EXR1, 2000, 1, cfg98_b, mask98_b, &c3_s2_b, &rld_s2_b));
    assert(cfg98_a[0x03] == 0xC0u && cfg98_a[0x0D] == 0x00u && cfg98_a[0x0E] == 0x00u);
    assert(c3_s2_a == 0xC4u && (c3_s2_a & 0x38u) == 0u && rld_s2_a == 0xFFu);
    assert(cfg98_b[0x03] == 0xC0u && c3_s2_b == 0x00u && rld_s2_b == 0x00u);

    /* RLD1：v0.01 Pin 62(RLDIN) 接 +2.5V，严禁置 CONFIG3.RLD_MEAS(0x10) 或 CH8 MUX=0x02，保持 0xC4 + CH8=0x00 */
    assert(c08b_build_ads1298_regs(C08B_MODE_RLD1, 1000, 0, cfg98_a, mask98_a, &c3_s2_a, &rld_s2_a));
    assert(c08b_build_ads1298_regs(C08B_MODE_RLD1, 1000, 1, cfg98_b, mask98_b, &c3_s2_b, &rld_s2_b));
    assert(cfg98_a[0x0C] == 0x00u && c3_s2_a == 0xC4u && (c3_s2_a & 0x38u) == 0u && rld_s2_a == 0xFFu);
    for (int r = 0x05; r <= 0x0C; ++r) {
        assert((cfg98_a[r] & 0x07u) != 0x02u && (cfg98_b[r] & 0x07u) != 0x02u);
    }
    assert(cfg98_b[0x0C] == 0x00u && c3_s2_b == 0x00u && rld_s2_b == 0x00u);
    assert(!c08b_build_ads1298_regs(C08B_MODE_EXR1, 999, 0, cfg98_a, mask98_a, &c3_s2_a, &rld_s2_a));

    /* 6. ADS1292 寄存器与两步 RLD 检查：RESP2=0x07，TST1=0xA3(非直流 0xA2)，EXR1 两步 0x20->0x23 */
    uint8_t cfg92[0x0C], mask92[0x0C], step2 = 0xFFu;
    assert(c08b_build_ads1292_regs(C08B_MODE_TST1, 1000, cfg92, mask92, &step2));
    assert(cfg92[0x01] == 0x03u && cfg92[0x02] == 0xA3u);
    assert(cfg92[0x09] == 0x02u && cfg92[0x0A] == 0x07u && cfg92[0x0B] == 0x0Cu);
    assert(mask92[0x08] == 0x00u && step2 == 0x00u);
    assert(c08b_build_ads1292_regs(C08B_MODE_EXR1, 2000, cfg92, mask92, &step2));
    assert(cfg92[0x06] == 0x20u && step2 == 0x23u && C08B_ADS1292_RLD_WARMUP_US >= 150000u);
    assert(c08b_build_ads1292_regs(C08B_MODE_RLD1, 500, cfg92, mask92, &step2));
    assert(cfg92[0x05] == 0x02u && cfg92[0x06] == 0x20u && step2 == 0x23u);

    /* 7. ADS1292 -> F01 24 位状态头映射（IN1P, IN2P, IN1N, IN2N, GPIO） */
    const uint8_t raw_st[3] = { 0xC0u | 0x05u /* IN2N=1, IN1N=1 */, 0x80u | 0x40u /* IN1P=1, GPIO2=1 */, 0x00u };
    uint8_t mapped[3] = {0};
    c08b_ads1292_map_f01_status(raw_st, mapped);
    assert((mapped[0] & 0xF0u) == 0xC0u);
    uint8_t statp = (uint8_t)(((mapped[0] & 0x0Fu) << 4) | (mapped[1] >> 4));
    uint8_t statn = (uint8_t)(((mapped[1] & 0x0Fu) << 4) | (mapped[2] >> 4));
    uint8_t gpio  = mapped[2] & 0x0Fu;
    assert(statp == 0x01u && statn == 0x03u && gpio == 0x02u);

    /* 8. L432 <-> nRF 双向 SPI 280B/16B 帧密封（含同源 64位 IMU 时间戳）与全字节篡改拒绝 */
    c08b_link_tx_t tx;
    memset(&tx, 0, sizeof(tx));
    tx.afe_mode = AFE_16CH;
    tx.sample_count = 4;
    tx.f01_flags = C08B_F01_SYNTHETIC | C08B_F01_SESSION_START;
    tx.imu_fresh = 1;
    tx.imu_read_us = 320u;
    tx.imu_timestamp_us = 0x0000000200001234ull; /* > 32-bit 不截断 */
    for (uint8_t i = 0; i < 4; i++) c08b_fill_synth_slot(tx.samples[i], AFE_16CH, i);
    c08b_link_tx_seal(&tx);
    assert(c08b_link_tx_ok(&tx));
    for (size_t i = 0; i < C08B_LINK_TX_CRC_LEN; i++) {
        c08b_link_tx_t bad = tx;
        ((uint8_t *)&bad)[i] ^= 0x01u;
        assert(!c08b_link_tx_ok(&bad));
    }
    tx.imu_read_us = 9000u;
    c08b_link_tx_seal(&tx);
    assert(!c08b_link_tx_ok(&tx)); /* IMU 读延迟超限必拒 */
    tx.imu_read_us = 320u;
    tx.sample_count = 5;
    c08b_link_tx_seal(&tx);
    assert(!c08b_link_tx_ok(&tx)); /* 超出批上限必拒 */

    c08b_link_rx_t rx;
    memset(&rx, 0, sizeof(rx));
    rx.req_mode = C08B_MODE_SYN1;
    rx.fs_hz = 1000;
    rx.cmd_epoch = 1;
    c08b_link_rx_seal(&rx);
    assert(c08b_link_rx_ok(&rx));
    for (size_t i = 0; i < C08B_LINK_RX_CRC_LEN; i++) {
        c08b_link_rx_t bad = rx;
        ((uint8_t *)&bad)[i] ^= 0x80u;
        assert(!c08b_link_rx_ok(&bad));
    }

    /* 9. F01 v1(8CH 27B) / v4(16CH 54B) / IMU(36B) 打包与会话边界拦截 */
    uint8_t pkt[C08B_F01_MAX_PKT_BYTES];
    uint8_t slots4[4][54];
    for (int i = 0; i < 4; i++) c08b_fill_synth_slot(slots4[i], AFE_16CH, (uint32_t)i);
    assert(c08b_pack_f01_v4_16ch(pkt, sizeof(pkt), 4, C08B_F01_SESSION_START, 0, 10000, (const uint8_t (*)[54])slots4) == 232u);
    assert(pkt[0] == 4u && pkt[1] == 1u && pkt[2] == 4u && pkt[3] == C08B_F01_SESSION_START);
    /* 同连接重配边界 SESSION_START | RECONFIGURE 合法通过 */
    assert(c08b_pack_f01_v4_16ch(pkt, sizeof(pkt), 4, C08B_F01_SESSION_START | C08B_F01_RECONFIGURE, 0, 20000, (const uint8_t (*)[54])slots4) == 232u);
    /* 反例：SESSION_START 但 seq != 0、RECONFIGURE 未带 SESSION_START、count=5 超限均必须返回 0 */
    assert(c08b_pack_f01_v4_16ch(pkt, sizeof(pkt), 4, C08B_F01_SESSION_START, 1, 10000, (const uint8_t (*)[54])slots4) == 0u);
    assert(c08b_pack_f01_v4_16ch(pkt, sizeof(pkt), 4, C08B_F01_RECONFIGURE,   0, 10000, (const uint8_t (*)[54])slots4) == 0u);
    assert(c08b_pack_f01_v4_16ch(pkt, sizeof(pkt), 5, 0,                      4, 14000, (const uint8_t (*)[54])slots4) == 0u);

    uint8_t imu_pkt[36];
    const int16_t ga[6] = { -10, 20, -30, 100, -200, 4096 };
    assert(c08b_pack_imu_pkt(imu_pkt, C08B_F01_SESSION_START, 0, 0x0000000200005000ull, ga, 350u) == 36u);
    assert(imu_pkt[0] == 1u && imu_pkt[1] == 2u && imu_pkt[2] == 1u && imu_pkt[28] == 3u);
    assert(c08b_pack_imu_pkt(imu_pkt, 0, 1, 15000, ga, 9000u) == 0u); /* 读延迟 >=9000 µs 必拒 */

    /* 10. V12 128-bit UUID 字节序逐项核对（01..06） */
    for (uint8_t sfx = 1; sfx <= 6; sfx++) {
        uint8_t le[16];
        char got[37], exp[37];
        c08b_v12_uuid128_le(sfx, le);
        assert(((uint16_t)le[12] | ((uint16_t)le[13] << 8)) == C08B_V12_UUID_BYTES12_13);
        format_uuid_str(le, got);
        snprintf(exp, sizeof(exp), "7b24c101-3948-4f03-9d11-12bb9d0000%02x", sfx);
        assert(strcmp(got, exp) == 0);
    }

    /* 11. 64 字节 STATUS 编码与 META JSON（含未探测 AFE_NONE 真实暴露，不伪装成 16CH） */
    uint8_t st_raw[64];
    c08b_ble_status_t st = { .produced = 1, .drdy_raw_edges = 1, .drdy_min_interval_us = 1000, .spi_hz = c08b_spi_hz_for_mode(AFE_NONE) };
    c08b_encode_ble_status(st_raw, &st);
    assert(st_raw[43] == 1u && st_raw[42] == 0u);
    assert(st_raw[56] == 0xFFu && st_raw[57] == 0xFFu && st_raw[58] == 0xFFu && st_raw[59] == 0xFFu);

    char meta[440];
    int m0 = c08b_format_meta_json(meta, sizeof(meta), AFE_NONE, 1000, false, true);
    assert(m0 > 100 && strstr(meta, "\"afe\":\"NONE\"") && strstr(meta, "\"protocol\":1") &&
           strstr(meta, "\"active_channels\":0") && strstr(meta, "\"spi_Hz\":1000000"));
    int mlen = c08b_format_meta_json(meta, sizeof(meta), AFE_16CH, 1000, false, true);
    assert(mlen > 100 && strstr(meta, "\"afe\":\"ADS1298_DUAL\"") && strstr(meta, "\"protocol\":4") &&
           strstr(meta, "\"channels\":16") && strstr(meta, "\"spi_Hz\":4000000"));

    /* 12. 双核在线切档（16CH -> 8CH -> 2CH）ack_epoch_lo 异步在途旧会话帧过滤（反例拦截 + 正例放行） */
    {
        c08b_link_tx_t stale16, fresh8;
        memset(&stale16, 0, sizeof(stale16));
        stale16.afe_mode = AFE_16CH;
        stale16.sample_count = 4u;
        stale16.seq_first = 400u;
        stale16.ack_epoch_lo = 3u; /* 旧命令纪元 3 */
        c08b_link_tx_seal(&stale16);
        assert(c08b_link_tx_ok(&stale16));

        uint16_t await_ep = 4u; /* nRF 已推进到新命令纪元 4（例如切 8CH@2000Hz） */
        /* 反例：在途旧纪元帧必须被拦截，且 await_ep 保持为 4 不被误清 */
        assert(!c08b_bridge_accept_frame(&stale16, &await_ep));
        assert(await_ep == 4u);

        memset(&fresh8, 0, sizeof(fresh8));
        fresh8.afe_mode = AFE_8CH;
        fresh8.sample_count = 2u;
        fresh8.f01_flags = C08B_F01_SYNTHETIC | C08B_F01_SESSION_START;
        fresh8.seq_first = 0u;
        fresh8.ack_epoch_lo = 4u; /* L432 已执行新命令纪元 4 */
        c08b_link_tx_seal(&fresh8);
        assert(c08b_link_tx_ok(&fresh8));

        /* 正例：匹配纪元 4 的首帧放行，并自动清零 await_ep 放行后续流式帧 */
        assert(c08b_bridge_accept_frame(&fresh8, &await_ep));
        assert(await_ep == 0u);
        assert(c08b_bridge_accept_frame(&fresh8, &await_ep));

        /* 16 位纪元回绕测试：0x0000FFFF -> 0x00010001（低 16 位跳过 0x0000 变为 0x0001） */
        uint32_t ep_before_wrap = 0x0000FFFFu;
        uint32_t ep_after_wrap  = c08b_next_cmd_epoch(ep_before_wrap);
        assert(ep_after_wrap == 0x00010001u && (uint16_t)ep_after_wrap == 1u);
        assert(c08b_next_cmd_epoch(0xFFFFFFFFu) == 1u);

        uint16_t wrap_await = (uint16_t)ep_after_wrap;
        stale16.ack_epoch_lo = 0xFFFFu;
        c08b_link_tx_seal(&stale16);
        assert(!c08b_bridge_accept_frame(&stale16, &wrap_await));
        assert(wrap_await == 1u);

        fresh8.ack_epoch_lo = 1u;
        c08b_link_tx_seal(&fresh8);
        assert(c08b_bridge_accept_frame(&fresh8, &wrap_await));
        assert(wrap_await == 0u);
    }

    puts("主机端 C11 流式固件测试全部通过（双硬件锁、3档识别与AFE_NONE如实暴露、ADS1298 ±2.5V RLDREF_INT=0两步RLD、ADS1292 1050ms POR、280B/16B全字节防篡改、双核热重配防串扰、F01 v1/v4/IMU 64位同源时钟与UUID字节序）");
    return 0;
}

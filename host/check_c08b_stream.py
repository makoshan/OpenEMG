"""C08B 共用双核主控 2/8/16ch 实时流式契约端到端门禁：
1. C11 stream_proto.h ↔ Python c08b_stream / v12_status / v12_imu / ads1298_regs 跨语言逐字节对拍；
2. 协议 v4 (16ch 54B) / v1 (8ch/2ch 27B) / META 校验必败反例（10 条）；
3. BLE 外部传输边界（冷启动 afe="NONE" 如实暴露、默认双锁关闭拒收真采与 PRB1、放行 SYN1 16/8/2ch 合成流；
   解锁后 PRB1 只读探测与 16/8/2ch 从 afe="NONE" 动态切换协议 v4/v1 落盘与离线回放）；
4. Studio device_desc + AcqHandler + take_file (.h5/.txt) 2/8/16ch 全链路、同连接 RECONFIGURE 与断连切段自检。
"""
import asyncio
import json
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
import threading
import time

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import ads1298_regs  # noqa: E402
import c08b_stream as cs  # noqa: E402
import device_desc as dd  # noqa: E402
from rig import AcqHandler, Block, build_rig  # noqa: E402
import take_file  # noqa: E402
import v12_imu  # noqa: E402
import v12_status  # noqa: E402

BUILD_ID = 'c08b261112000001'


def _find_fw_common():
    for rel in ('firmware/c08b-stream/common', 'v12/c08b-stream-fw-20261112/common'):
        cand = ROOT / rel
        if (cand / 'stream_proto.h').exists():
            return cand
    raise FileNotFoundError('未找到 c08b-stream/common/stream_proto.h')


def _expect_fail(fn, why, exc_types=(ValueError, RuntimeError, PermissionError)):
    try:
        fn()
    except exc_types as err:
        print(f'  红 ✓ {why}: {str(err)[:64]}')
        return
    raise AssertionError(f'必败反例未报错：{why}')


def test_c_firmware_parity(tmp: Path):
    """编译运行 C11 片段直接调用固件 stream_proto.h，验证与 Python 解码器逐字节一致。"""
    fw_common = _find_fw_common()
    c_src = tmp / 'emit_c08b_vectors.c'
    c_bin = tmp / 'emit_c08b_vectors'
    c_src.write_text(
        r"""
#include <assert.h>
#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include "bench_release.h"
#include "stream_proto.h"

static void hex_line(const char *tag, const uint8_t *buf, size_t n) {
    printf("%s:", tag);
    for (size_t i = 0; i < n; ++i) printf("%02x", buf[i]);
    printf("\n");
}

int main(void) {
    assert(strcmp(C08B_BLE_DEV_NAME, "YUANLI-C08B") == 0);
    assert(C08B_ADS1292_POR_WAIT_MS >= 1000u);

    /* 核对 ADS1298 ±2.5V 双电源寄存器快照同时通过 host/ads1298_regs.py:check() */
    uint8_t cfg98[0x1A], mask98[0x1A], c3_s2 = 0, rld_s2 = 0;
    assert(c08b_build_ads1298_regs(C08B_MODE_RLD1, 1000u, 0, cfg98, mask98, &c3_s2, &rld_s2));
    cfg98[0x00] = 0x92u;
    cfg98[0x03] = c3_s2; /* 0xC4: RLD_MEAS=0 (v0.01 Pin62=+2.5V 禁置 RLD_MEAS), PD_RLD=1, RLDREF_INT=0 */
    cfg98[0x0D] = rld_s2;
    cfg98[0x0E] = rld_s2;
    hex_line("REGS98_RLD1", cfg98, sizeof(cfg98));

    char meta[512];
    int n;
    n = c08b_format_meta_json(meta, sizeof(meta), AFE_NONE, 1000u, false, true);
    hex_line("META_NONE", (const uint8_t *)meta, (size_t)n);
    n = c08b_format_meta_json(meta, sizeof(meta), AFE_16CH, 1000u, true, true);
    hex_line("META_16", (const uint8_t *)meta, (size_t)n);
    n = c08b_format_meta_json(meta, sizeof(meta), AFE_8CH, 1000u, true, true);
    hex_line("META_8", (const uint8_t *)meta, (size_t)n);
    n = c08b_format_meta_json(meta, sizeof(meta), AFE_2CH, 1000u, true, true);
    hex_line("META_2", (const uint8_t *)meta, (size_t)n);

    uint8_t st[64];
    c08b_ble_status_t st_in = {
        .produced = 128u, .ring_dropped = 0u, .scheduler_skipped = 0u,
        .sent_samples = 124u, .notify_failures = 0u, .fault = 0u,
        .active = true, .bench_measured = true, .ads_status = 0x00C00000u,
        .drdy_raw_edges = 129u, .drdy_min_interval_us = 988u, .spi_hz = 4000000u
    };
    c08b_encode_ble_status(st, &st_in);
    hex_line("STATUS", st, sizeof(st));

    /* 4 帧 × 54B 16ch 极值测试帧 */
    uint8_t frames54[4][54];
    int32_t vec[16] = {
        -8388608, -123456, -1, 0, 1, 123456, 8388607, -42,
        42, -7000000, 7000000, -256, 256, -65535, 65535, 314159
    };
    for (int f = 0; f < 4; ++f) {
        uint8_t *dst = frames54[f];
        dst[0] = 0xC0u; dst[1] = 0x00u; dst[2] = (uint8_t)f;
        for (int c = 0; c < 8; ++c) {
            int32_t v = vec[c] + (c >= 2 && c <= 5 ? f : 0);
            uint32_t u = (uint32_t)v & 0xFFFFFFu;
            dst[3 + c * 3 + 0] = (uint8_t)(u >> 16);
            dst[3 + c * 3 + 1] = (uint8_t)(u >> 8);
            dst[3 + c * 3 + 2] = (uint8_t)u;
        }
        dst[27] = 0xC0u; dst[28] = 0x00u; dst[29] = (uint8_t)(0x10u + f);
        for (int c = 0; c < 8; ++c) {
            int32_t v = vec[8 + c] - f;
            uint32_t u = (uint32_t)v & 0xFFFFFFu;
            dst[30 + c * 3 + 0] = (uint8_t)(u >> 16);
            dst[30 + c * 3 + 1] = (uint8_t)(u >> 8);
            dst[30 + c * 3 + 2] = (uint8_t)u;
        }
    }
    uint8_t pkt16[244];
    size_t n16 = c08b_pack_f01_v4_16ch(pkt16, sizeof(pkt16), 4u, C08B_F01_SESSION_START, 0u, 50000ull, (const uint8_t (*)[54])frames54);
    hex_line("PKT16", pkt16, n16);

    /* ADS1292 24-bit 状态字映射 + F01 v1 打包 */
    uint8_t raw9[9] = {0};
    uint32_t st92 = (0xCu << 20) | (0x15u << 15) | (1u << 13);
    raw9[0] = (uint8_t)(st92 >> 16);
    raw9[1] = (uint8_t)(st92 >> 8);
    raw9[2] = (uint8_t)st92;
    raw9[3] = 0x00; raw9[4] = 0x08; raw9[5] = 0x00;
    raw9[6] = 0xFF; raw9[7] = 0xF8; raw9[8] = 0x00;
    uint8_t f27[1][27];
    memset(f27, 0, sizeof(f27));
    c08b_ads1292_map_f01_status(raw9, f27[0]);
    memcpy(&f27[0][3], &raw9[3], 6);
    uint8_t pkt2[244];
    size_t n2 = c08b_pack_f01_v1_8ch(pkt2, sizeof(pkt2), 1u, C08B_F01_SESSION_START | C08B_F01_SYNTHETIC, 0u, 1000ull, (const uint8_t (*)[27])f27);
    hex_line("PKT2", pkt2, n2);

    /* 36B IMU 包（64 位同源微秒时间戳 > 2^32） */
    int16_t imu6[6] = {-300, 150, -45, 12, -24, 4096};
    uint8_t pkt_imu[36];
    size_t nimu = c08b_pack_imu_pkt(pkt_imu, C08B_F01_SESSION_START, 0u, 0x0000000200013001ull, imu6, 185u);
    hex_line("PKTIMU", pkt_imu, nimu);
    return 0;
}
""",
        encoding='utf-8',
    )
    cc = shutil.which('cc') or shutil.which('clang') or shutil.which('gcc')
    assert cc, '未找到宿主 C 编译器'
    subprocess.run(
        [cc, '-std=c11', '-O2', '-Wall', '-Wextra', '-Werror', f'-I{fw_common}', str(c_src), '-o', str(c_bin)],
        check=True,
    )
    out = subprocess.check_output([str(c_bin)], text=True)
    kv = {}
    for ln in out.strip().splitlines():
        k, v = ln.split(':', 1)
        kv[k] = bytes.fromhex(v)

    # C11 生成的 ADS1298 RLD1 快照必须 0 违规通过 ads1298_regs.check，且 RLDREF_INT==0, RLD_MEAS==0(v0.01 Pin62=+2.5V), VREF==2.4V
    assert ads1298_regs.check(kv['REGS98_RLD1']) == [], ads1298_regs.check(kv['REGS98_RLD1'])
    dec98 = ads1298_regs.decode(kv['REGS98_RLD1'])
    assert dec98['CONFIG3']['RLDREF_INT'] == 0 and dec98['CONFIG3']['RLD_MEAS'] == 0 and dec98['CONFIG3']['PD_RLD'] == 1
    assert ads1298_regs.vref_v(kv['REGS98_RLD1']) == 2.4 and dec98['CH8SET']['MUX'] == 0x00

    m_none = cs.validate_c08b_metadata(kv['META_NONE'], expected=BUILD_ID)
    assert m_none['afe'] == 'NONE' and not m_none['bench_measured'] and m_none['active_channels'] == 0 and m_none['spi_Hz'] == 1_000_000
    m16 = cs.validate_c08b_metadata(kv['META_16'], expected=BUILD_ID)
    assert (m16['protocol'], m16['channels'], m16['active_channels'], m16['vref_mV']) == (4, 16, 16, 2400)
    m8 = cs.validate_c08b_metadata(kv['META_8'], expected=BUILD_ID)
    assert (m8['protocol'], m8['channels'], m8['active_channels'], m8['vref_mV']) == (1, 8, 8, 2400)
    m2 = cs.validate_c08b_metadata(kv['META_2'], expected=BUILD_ID)
    assert (m2['protocol'], m2['channels'], m2['active_channels'], m2['vref_mV'], m2['spi_Hz']) == (1, 8, 2, 2420, 1_000_000)

    st = v12_status.decode_status(kv['STATUS'])
    assert st['produced'] == 128 and st['sent_samples'] == 124 and st['active'] and st['bench_measured']
    assert st['drdy_raw_edges'] == 129 and st['drdy_min_interval_us'] == 988 and st['spi_Hz'] == 4_000_000

    p16 = cs.decode_16ch(kv['PKT16'], mtu=247)
    assert len(kv['PKT16']) == 232 and p16.sequence == 0 and p16.timestamp_us == 50000 and len(p16.frames) == 4
    base_vec = [-8388608, -123456, -1, 0, 1, 123456, 8388607, -42, 42, -7000000, 7000000, -256, 256, -65535, 65535, 314159]
    for f_idx, frame in enumerate(p16.frames):
        assert cs.frame_status_valid(frame, 4)
        st_a, st_b, vals = cs.decode_frame_16ch(frame)
        assert st_a == (0xC00000 | f_idx) and st_b == (0xC00010 | f_idx)
        expected_vals = tuple(
            (base_vec[c] + (f_idx if 2 <= c <= 5 else 0)) if c < 8 else (base_vec[c] - f_idx)
            for c in range(16)
        )
        assert vals == expected_vals, (f_idx, vals, expected_vals)

    codec = cs.load_codec()
    p2 = codec.decode(kv['PKT2'], mtu=247)
    st_u24, ch8 = codec.decode_frame(p2.frames[0])
    assert ch8[:2] == (2048, -2048) and ch8[2:] == (0, 0, 0, 0, 0, 0)
    loff_p, loff_n, gpio = ads1298_regs.decode_ads_status(*st_u24.to_bytes(3, 'big'))
    assert (loff_p, loff_n, gpio) == (0x03, 0x00, 0x01)

    p_imu = v12_imu.decode(kv['PKTIMU'], mtu=247)
    assert p_imu.timestamp_us == 0x0000000200013001
    s_imu = v12_imu.sample(p_imu.frames[0])
    assert s_imu['gyro_raw'] == (-300, 150, -45) and s_imu['accel_raw'] == (12, -24, 4096) and s_imu['read_latency_us'] == 185
    print('  跨语言对拍 ✓ C11 stream_proto.h ↔ Python ADS1298(RLDREF_INT=0) / META / STATUS / F01 v4 / ADS1292 / IMU 64位时钟全通过')


def test_protocol_negatives():
    """协议与元数据 10 条必败反例。"""
    codec = cs.load_codec()
    good_f54 = cs.encode_frame_16ch(range(16))
    good_pkt = cs.encode_16ch(cs.Packet(0, 1000, cs.SESSION_START | cs.SYNTHETIC, (good_f54,) * 4), mtu=247)
    good_v1 = codec.encode(codec.Packet(0, 1000, cs.SESSION_START | cs.SYNTHETIC, (cs.ADS_STATUS_OK + bytes(24),)))

    _expect_fail(lambda: cs.encode_16ch(cs.Packet(0, 1000, cs.SESSION_START, (good_f54,) * 5), mtu=247), '16ch 5 帧超 MTU=247')
    _expect_fail(lambda: cs.encode_16ch(cs.Packet(0, 1000, cs.SESSION_START, (good_f54,) * 2), mtu=100), '16ch 2 帧超 MTU=100')
    _expect_fail(lambda: cs.encode_16ch(cs.Packet(4, 1000, cs.SESSION_START, (good_f54,))), 'SESSION_START 但 seq!=0')
    _expect_fail(lambda: cs.encode_16ch(cs.Packet(0, 1000, cs.RECONFIGURE, (good_f54,))), 'RECONFIGURE 缺 SESSION_START')
    _expect_fail(lambda: cs.decode_16ch(good_pkt[:-1], mtu=247), '16ch 载荷截断 1 字节')
    _expect_fail(lambda: cs.decode_16ch(good_v1, mtu=247), '拿 v1 包喂 v4 解码器')
    _expect_fail(lambda: codec.decode(good_pkt, mtu=247), '拿 v4 包喂 v1 解码器')

    bad_u2 = cs.encode_frame_16ch(range(16), status_a=b'\xC0\x00\x00', status_b=b'\x00\x00\x00')
    assert not cs.frame_status_valid(bad_u2, 4), 'U2 状态字损坏未被检出'
    rig = cs.C08BRig(n_channels=16, fs_Hz=1000)
    got = []
    rig.chunk_subscribers.append(lambda emg, *_: got.append(emg))
    rig.feed_packet(cs.encode_16ch(cs.Packet(0, 1000, cs.SESSION_START | cs.SYNTHETIC, (bad_u2, good_f54))))
    assert len(rig.bad_status) == 1 and len(got) == 1 and got[0].shape == (1, 16), 'U2 坏帧应被剔除且好帧保留'
    print('  红 ✓ 16ch 第二片 ADS1298 (U2) 状态头损坏精准剔除')

    base_meta = dict(
        profile='C08B_DUAL_STREAM_CANDIDATE', protocol=4, channels=16, active_channels=16,
        afe='ADS1298_DUAL', fs_Hz=1000, spi_Hz=4_000_000, vref_mV=2400, gain=6,
        bench_measured=True, imu_enabled=True, clock_source='L432_DWT_1MHz',
        clock_resolution_us=1, build_id=BUILD_ID,
    )
    _expect_fail(
        lambda: cs.validate_c08b_metadata(json.dumps({**base_meta, 'vref_mV': 4000}).encode()),
        'C08B ±2.5V ADS1298 错标 4.0V 基准',
    )
    _expect_fail(
        lambda: cs.validate_c08b_metadata(
            json.dumps({**base_meta, 'afe': 'ADS1292', 'protocol': 1, 'channels': 8, 'active_channels': 2, 'vref_mV': 2400, 'spi_Hz': 1_000_000}).encode()
        ),
        'ADS1292 错标 2400mV 基准',
    )
    _expect_fail(
        lambda: cs.validate_c08b_metadata(json.dumps(base_meta).encode(), expected='0000000000000000'),
        'build_id 与预期不一致',
    )


class _FakeChar:
    def __init__(self, uuid):
        self.uuid = uuid


class _FakeService:
    def __init__(self, uuids):
        self.characteristics = [_FakeChar(u) for u in uuids]


class _FakeServices:
    def __init__(self, service):
        self._svc = service

    def get_service(self, uuid):
        return self._svc if uuid.lower() == cs.SERVICE else None


class FakeC08BBleClient:
    """模拟 C08B 真机冷启动行为：
    初始待机一律报 afe='NONE' (protocol=1, active_channels=0, spi_Hz=1MHz)，
    只有在收到解锁后的 PRB1/TST1/...（切换为 board_afe）或收到 SYN1（切换为第 7 字节指定的 2/8/16ch）时，
    才在发出第 1 条通知前刷新 GATT META！
    """

    def __init__(self, board_afe='ADS1298_DUAL', initial_afe='NONE', bench_measured=False, fs_Hz=1000, corrupt_synth_flag=None):
        self.mtu_size = 247
        self.board_afe = board_afe
        self.bench_measured = bench_measured
        self.fs_Hz = fs_Hz
        self.corrupt_synth_flag = corrupt_synth_flag
        self.services = _FakeServices(_FakeService([cs.SERVICE, cs.DATA, cs.META, cs.STATUS, cs.CONTROL, cs.IMU_DATA]))
        self.notify_cbs = {}
        self.written_commands = []
        self.active = False
        self.fault = 0
        self.produced = 0
        self.sent = 0
        self._pump_task = None
        self._apply_afe(initial_afe)

    def _apply_afe(self, afe):
        self.afe = afe
        if afe == 'ADS1298_DUAL':
            self.protocol, self.channels, self.active_channels, self.vref_mV, self.spi_Hz = 4, 16, 16, 2400, 4_000_000
        elif afe == 'ADS1298_SINGLE':
            self.protocol, self.channels, self.active_channels, self.vref_mV, self.spi_Hz = 1, 8, 8, 2400, 4_000_000
        elif afe == 'ADS1292':
            self.protocol, self.channels, self.active_channels, self.vref_mV, self.spi_Hz = 1, 8, 2, 2420, 1_000_000
        else:
            self.protocol, self.channels, self.active_channels, self.vref_mV, self.spi_Hz = 1, 8, 0, 2400, 1_000_000

    async def read_gatt_char(self, uuid):
        u = str(uuid).lower()
        if u == cs.META:
            return json.dumps(dict(
                profile='C08B_DUAL_STREAM_CANDIDATE',
                protocol=self.protocol,
                channels=self.channels,
                active_channels=self.active_channels,
                afe=self.afe,
                fs_Hz=self.fs_Hz,
                spi_Hz=self.spi_Hz,
                vref_mV=self.vref_mV,
                gain=6,
                bench_measured=self.bench_measured,
                imu_enabled=True,
                clock_source='L432_DWT_1MHz',
                clock_resolution_us=1,
                build_id=BUILD_ID,
            )).encode()
        if u == cs.STATUS:
            edges = self.produced + 1 if self.produced >= 2 else 0
            min_iv = 1_000_000 // self.fs_Hz if edges >= 2 else 0xFFFFFFFF
            buf = bytearray(64)
            struct.pack_into('<5Q', buf, 0, self.produced, 0, 0, self.sent, 0)
            buf[40] = self.fault
            buf[41] = 1 if self.active else 0
            buf[42] = 1 if self.bench_measured else 0
            buf[43] = 1
            struct.pack_into('<I', buf, 44, 0x00C00000)
            struct.pack_into('<QII', buf, 48, edges, min_iv, self.spi_Hz)
            return bytes(buf)
        raise KeyError(u)

    async def start_notify(self, uuid, callback):
        self.notify_cbs[str(uuid).lower()] = callback

    async def stop_notify(self, uuid):
        self.notify_cbs.pop(str(uuid).lower(), None)

    async def write_gatt_char(self, uuid, data, response=True):
        assert str(uuid).lower() == cs.CONTROL
        cmd = bytes(data)
        self.written_commands.append(cmd)
        verb = cmd[:4]
        if verb == b'STOP':
            self.active = False
            if self._pump_task is not None:
                self._pump_task.cancel()
                try:
                    await self._pump_task
                except asyncio.CancelledError:
                    pass
                self._pump_task = None
            return

        is_synth = (verb == b'SYN1')
        if not is_synth and not self.bench_measured:
            self.fault = 1
            return

        if verb == b'PRB1':
            if self.board_afe == 'NONE':
                self.fault = 4
            else:
                self._apply_afe(self.board_afe)
            self.active = False
            return

        if is_synth:
            sc = cmd[6] if len(cmd) >= 7 else 16
            self._apply_afe('ADS1292' if sc == 2 else 'ADS1298_SINGLE' if sc == 8 else 'ADS1298_DUAL')
        else:
            if self.board_afe == 'NONE':
                self.fault = 4
                return
            self._apply_afe(self.board_afe)

        self.active = True
        self._pump_task = asyncio.create_task(self._pump(is_synth))

    async def _pump(self, is_synth):
        codec = cs.load_codec()
        n_ch = self.active_channels
        prof = cs.C08BAdcProfile.for_n_channels(n_ch, fs_Hz=self.fs_Hz)
        step = 4 if prof.transport_protocol == 4 else 8
        seq = 0
        imu_seq = 0
        while self.active:
            t = np.arange(seq, seq + step, dtype=np.float64)[:, None]
            ch_idx = np.arange(1, n_ch + 1, dtype=np.float64)[None, :]
            uv = np.sin(t * 0.05) * (10.0 * ch_idx)
            counts = np.round(uv / prof.uv_per_count).astype(np.int64)
            use_synth_flag = is_synth if self.corrupt_synth_flag is None else self.corrupt_synth_flag
            flags = (cs.SYNTHETIC if use_synth_flag else 0) | (cs.SESSION_START if seq == 0 else 0)
            ts_us = 1000 + seq * 1_000_000 // self.fs_Hz
            if prof.transport_protocol == 4:
                frames = tuple(cs.encode_frame_16ch(row) for row in counts)
                pkt = cs.encode_16ch(cs.Packet(seq, ts_us, flags, frames))
            else:
                batch = counts if n_ch == 8 else np.concatenate([counts, np.zeros((step, 8 - n_ch), dtype=np.int64)], axis=1)
                frames = tuple(cs.ADS_STATUS_OK + b''.join(int(v).to_bytes(3, 'big', signed=True) for v in row) for row in batch)
                pkt = codec.encode(codec.Packet(seq, ts_us, flags, frames))

            cb = self.notify_cbs.get(cs.DATA)
            if cb is not None:
                cb(1, pkt)
            seq += step
            self.produced = seq
            self.sent = seq

            imu_cb = self.notify_cbs.get(cs.IMU_DATA)
            if imu_cb is not None:
                imu_flags = (cs.SYNTHETIC if use_synth_flag else 0) | (cs.SESSION_START if imu_seq == 0 else 0)
                imu_ts = 1000 + imu_seq * 1_000_000 // 104
                imu_cb(2, cs.pack_c08b_imu_packet(imu_seq, imu_ts, (10, -20, 30, 0, 0, 4096), flags=imu_flags))
                imu_seq += 1

            await asyncio.sleep(0.01)


async def _run_ble_tests(tmp: Path):
    # 1. 默认双锁关闭：只读诊断通过（初始 afe='NONE'）
    locked = FakeC08BBleClient(board_afe='ADS1298_DUAL', initial_afe='NONE', bench_measured=False)
    r_status = await cs.capture_c08b(locked, tmp / 'cap-status', mode=None)
    assert r_status['mode'] == 'status' and r_status['afe'] == 'NONE' and locked.written_commands == []

    # 2. 默认双锁关闭：SYN1 双核无电合成流分别测 16ch(v4) / 8ch(v1) / 2ch(v1) + IMU
    for syn_ch, exp_proto in ((16, 4), (8, 1), (2, 1)):
        locked_syn = FakeC08BBleClient(board_afe='NONE', initial_afe='NONE', bench_measured=False)
        out_syn = tmp / f'cap-syn-{syn_ch}'
        r_syn = await cs.capture_c08b(locked_syn, out_syn, seconds=0.06, mode='synth', with_imu=True, synth_channels=syn_ch)
        assert r_syn['protocol'] == exp_proto and r_syn['active_channels'] == syn_ch and r_syn['stop_confirmed']
        rep_syn = cs.replay_c08b(out_syn, allow_real=False)
        assert rep_syn['uv'].shape == (r_syn['valid_samples'], syn_ch) and rep_syn['imu']['samples'] == r_syn['imu_samples']
    print('  BLE 锁定态 ✓ SYN1 双核无电合成流 (16ch v4 / 8ch v1 / 2ch v1 + IMU) 从 afe=NONE 动态切协议落盘回放全过')

    # 3. 安全红线必败：锁定态请求 TST1 或 PRB1 必拒且零写命令
    for deny_mode in ('test', 'probe'):
        locked_real = FakeC08BBleClient(board_afe='ADS1298_DUAL', initial_afe='NONE', bench_measured=False)
        try:
            await cs.capture_c08b(locked_real, tmp / f'cap-deny-{deny_mode}', seconds=0.05, mode=deny_mode, allow_real=True, expected=BUILD_ID)
            raise AssertionError(f'锁定固件放行了 {deny_mode}')
        except ValueError as err:
            assert locked_real.written_commands == []
            print(f'  红 ✓ 锁定固件拒发 {deny_mode}（零写特征）: {err}')

    # 4. 安全红线必败：未传 allow_real 或未传 expected 必拒
    unlocked_check = FakeC08BBleClient(board_afe='ADS1298_DUAL', initial_afe='NONE', bench_measured=True)
    try:
        await cs.capture_c08b(unlocked_check, tmp / 'cap-deny2', seconds=0.05, mode='test', allow_real=False, expected=BUILD_ID)
        raise AssertionError('allow_real=False 放行了真实采集')
    except ValueError as err:
        assert unlocked_check.written_commands == []
        print(f'  红 ✓ allow_real=False 拒发真实命令: {err}')

    # 5. 安全红线必败：真实模式混入 SYNTHETIC 包必拒
    spoof = FakeC08BBleClient(board_afe='ADS1298_DUAL', initial_afe='NONE', bench_measured=True, corrupt_synth_flag=True)
    try:
        await cs.capture_c08b(spoof, tmp / 'cap-spoof', seconds=0.05, mode='test', allow_real=True, expected=BUILD_ID)
        raise AssertionError('真实采集接受了 SYNTHETIC 包')
    except ValueError as err:
        print(f'  红 ✓ 真实采集拒绝 SYNTHETIC 混入: {err}')

    # 6. 解锁台架：PRB1 只读子板探测 + 16ch/8ch/2ch 冷启动 afe='NONE' 动态识别采集闭环
    for board_afe, exp_ch, exp_proto, exp_vat in (
        ('ADS1298_DUAL', 16, 4, 'ADS1298 PGA input'),
        ('ADS1298_SINGLE', 8, 1, 'ADS1298 PGA input'),
        ('ADS1292', 2, 1, 'ADS1292 PGA input'),
    ):
        # 6a. PRB1 只读探测：从 afe='NONE' 识别子板后保持 active=False
        probe_cli = FakeC08BBleClient(board_afe=board_afe, initial_afe='NONE', bench_measured=True)
        r_prb = await cs.capture_c08b(probe_cli, tmp / f'prb-{board_afe.lower()}', seconds=0.1, mode='probe', allow_real=True, expected=BUILD_ID)
        assert r_prb['afe'] == board_afe and r_prb['active_channels'] == exp_ch and r_prb['stop_confirmed']
        assert probe_cli.written_commands == [b'PRB1']

        # 6b. 冷启动 afe='NONE' 直接发 TST1：重读 META 动态锁定 v4(16ch) / v1(8ch/2ch) 解码器！
        cli = FakeC08BBleClient(board_afe=board_afe, initial_afe='NONE', bench_measured=True)
        out_dir = tmp / f'cap-{board_afe.lower()}'
        res = await cs.capture_c08b(
            cli, out_dir, seconds=0.08, mode='test', allow_real=True, expected=BUILD_ID, with_imu=True
        )
        assert res['afe'] == board_afe and res['protocol'] == exp_proto and res['active_channels'] == exp_ch and res['stop_confirmed']
        meta_saved = json.loads((out_dir / 'metadata.json').read_text())
        assert meta_saved['voltage_at'] == exp_vat, (board_afe, meta_saved['voltage_at'])
        _expect_fail(lambda d=out_dir: cs.replay_c08b(d, allow_real=False), f'{board_afe} 真实归档未带 allow_real 回放')
        rep = cs.replay_c08b(out_dir, allow_real=True)
        assert rep['uv'].shape == (res['valid_samples'], exp_ch) and rep['missing_samples'] == 0
        expected_row1 = np.sin(0.05) * (10.0 * np.arange(1, exp_ch + 1))
        assert np.max(np.abs(rep['uv'][1] - expected_row1)) < 0.05
        print(f'  BLE 冷启动动态识别 ✓ NONE -> {board_afe}: proto=v{exp_proto}, shape={rep["uv"].shape}, voltage_at="{exp_vat}"')


def test_studio_acq_and_recording(tmp: Path):
    """验证 Studio device_desc + AcqHandler + OpenSignals .h5/.txt 三档 (16/8/2ch) 全链路。"""
    for did, exp_ch in (('c08b-16ch', 16), ('c08b-8ch', 8), ('c08b-2ch', 2)):
        desc = dd.load(did)
        assert desc.n_channels == exp_ch and desc.decoder == 'c08b' and not desc.cap('record')
        assert desc.transport.get('match', {}).get('name_prefix') == 'YUANLI-C08B'
        rig = build_rig(desc, seed=7)
        assert dd.for_rig(rig).id == did
        acq = AcqHandler(rig, desc)
        _expect_fail(lambda a=acq: a.record(0.2), f'{did} 默认 record=false 拒录真训练集', (PermissionError,))

        got = []
        acq.subscribe(got.append)
        acq.start()
        t0 = time.monotonic()
        while time.monotonic() - t0 < 1.2 and sum(len(b.uv) for b in got) < 120:
            time.sleep(0.03)
        st = acq.status()
        acq.stop()

        emg_blocks = [b for b in got if len(b.uv)]
        imu_blocks = [b for b in got if b.imu is not None and len(b.imu)]
        assert emg_blocks and imu_blocks, f'{did} 缺少 EMG 或 IMU 数据块'
        b0 = emg_blocks[0]
        assert isinstance(b0, Block) and b0.uv.shape[1] == exp_ch and b0.uv.dtype == np.float32
        gain = np.asarray(desc.gains())
        assert np.array_equal(b0.raw, np.round(b0.uv / gain).astype(np.int32))
        seqs = np.concatenate([b.seq for b in emg_blocks])
        assert np.array_equal(seqs, np.arange(len(seqs), dtype=np.uint32))
        assert imu_blocks[0].imu.shape[1] == 6 and imu_blocks[0].imu.dtype == np.int16
        assert st['dropped'] == 0

        unlocked_desc = dd.validate({**desc.to_json(), 'capabilities': {**desc.capabilities, 'record': True}})
        real_rig = build_rig(unlocked_desc)
        real_acq = AcqHandler(real_rig, unlocked_desc)
        rec = real_acq.record(1.0)
        rec.mark('fist', 'ui')
        prof = real_rig.profile
        t = np.arange(1000, dtype=np.float64)[:, None]
        uv_src = np.cos(2.0 * np.pi * 85.0 * t / 1000.0) * (15.0 * np.arange(1, exp_ch + 1)[None, :])
        counts = np.round(uv_src / prof.uv_per_count).astype(np.int64)
        codec = cs.load_codec()
        step = 4 if prof.transport_protocol == 4 else 8
        for i in range(0, 1000, step):
            flags = cs.SESSION_START if i == 0 else 0
            ts_us = 1000 + i * 1000
            batch = counts[i:i + step]
            if prof.transport_protocol == 4:
                pkt = cs.encode_16ch(cs.Packet(i, ts_us, flags, tuple(cs.encode_frame_16ch(r) for r in batch)))
            else:
                pad_b = batch if exp_ch == 8 else np.concatenate([batch, np.zeros((len(batch), 8 - exp_ch), dtype=np.int64)], axis=1)
                frames = tuple(cs.ADS_STATUS_OK + b''.join(int(v).to_bytes(3, 'big', signed=True) for v in r) for r in pad_b)
                pkt = codec.encode(codec.Packet(i, ts_us, flags, frames))
            real_rig.feed_packet(pkt)
            if i == 0:
                real_rig.feed_imu_packet(cs.pack_c08b_imu_packet(0, 1000, (5, -5, 10, 0, 0, 4096), flags=cs.SESSION_START))
        assert rec.done
        arr = rec.arrays()
        real_acq.stop()

        sess_root = tmp / f'sess-{did}'
        smeta, sdir = take_file.new_session(sess_root, unlocked_desc, subject='BENCH', donning=1, placement='离体台架')
        h5_path, gate = take_file.write(sdir, unlocked_desc, arr, 'fist', session_meta=smeta, seconds=1.0, dropped=real_acq.dropped)
        assert gate['ok'] and gate['frames'] == 1000, (did, gate)
        back = take_file.read(h5_path, ('uv', 'raw', 'seq', 'imu'))
        assert back['uv'].shape == (1000, exp_ch) and back['imu'].shape == (1, 6)
        txt_path = take_file.export_txt(h5_path, sess_root / f'{did}.txt', converted=False)
        lines = txt_path.read_text().splitlines()
        hdr = next(iter(json.loads(lines[1][2:]).values()))
        assert hdr['column'] == ['nSeq', 'DI', *unlocked_desc.labels()]
        print(f'  Studio 全链路 ✓ {did}: 合成流 + 录制 1s -> {h5_path.name} ({exp_ch}ch) + OpenSignals .txt 往返通过')

    # 跨档通道数错配防呆 + 丢包计数 + 同连接 RECONFIGURE 切段 + 断连切段防拼接
    _expect_fail(
        lambda: AcqHandler(cs.C08BRig(n_channels=8), dd.load('c08b-16ch')),
        '8ch C08BRig 误配 c08b-16ch 描述',
    )
    rig16 = cs.C08BRig(n_channels=16, fs_Hz=1000)
    acq16 = AcqHandler(rig16, dd.load('c08b-16ch'))
    acq16.open()
    f54 = cs.encode_frame_16ch([100] * 16)
    rig16.feed_packet(cs.encode_16ch(cs.Packet(0, 1000, cs.SESSION_START | cs.SYNTHETIC, (f54,) * 4)))
    rig16.feed_packet(cs.encode_16ch(cs.Packet(7, 8000, cs.SYNTHETIC, (f54,) * 4)))
    assert acq16.dropped == 3, f'预期丢样计数为 3，实得 {acq16.dropped}'
    seg0 = acq16.segment
    # 同连接不断连重开新一轮会话（带 SESSION_START | RECONFIGURE），必须接受且自动切新段
    rig16.feed_packet(cs.encode_16ch(cs.Packet(0, 20000, cs.SESSION_START | cs.RECONFIGURE | cs.SYNTHETIC, (f54,) * 4)))
    assert acq16.segment == seg0 + 1 and rig16.rx.sessions == 2
    seg1 = acq16.segment
    rig16.disconnect()
    assert acq16.segment == seg1 + 1, '断连未自动切新段（违反不拼接铁律）'
    print('  边界铁律 ✓ 16ch 缺口计入 dropped=3、同连接 RECONFIGURE 自动切段且断连 segment+1 不拼接')


class FakeDongleSerial:
    """模拟刷了 dongle_c08b 档的 XIAO nRF52840 USB 接收器串口字节流（0xA5 帧头）：
    把 DongleClient 发来的 Q/D/R/W 串口命令转给 FakeC08BBleClient，并把 DATA/IMU_DATA 通知封装为 kind=2/6 串口帧。
    """

    def __init__(self, ble_dev: FakeC08BBleClient, loop: asyncio.AbstractEventLoop, can_reconnect=True, inject_mid_reconnect=False):
        self.ble = ble_dev
        self.loop = loop
        self.can_reconnect = can_reconnect
        self.inject_mid_reconnect = inject_mid_reconnect
        self._lock = threading.Lock()
        self._rx = bytearray()
        self._tx_cmd = bytearray()
        self.dtr = False
        self.rts = False
        self.closed = False
        self.ready = True
        self.connects = 1
        self.notifies = 0
        # 接收器 connect_cb 默认同时订阅 DATA 与 IMU_DATA
        self.ble.notify_cbs[cs.DATA] = lambda _h, pkt: self._push_frame(2, bytes(pkt))
        self.ble.notify_cbs[cs.IMU_DATA] = lambda _h, pkt: self._push_frame(6, bytes(pkt))

    def _push_frame(self, kind: int, payload: bytes):
        if kind in (2, 6):
            self.notifies += 1
            if self.inject_mid_reconnect and self.notifies == 3:
                # 模拟第 3 包到达后 BLE 闪断并被接收器自动重连（connects 自增），主机必须识别并拒收拼接！
                self.connects += 1
                self._send_link()
        hdr = bytes((0xA5, kind)) + struct.pack('<HI', len(payload), 12345)
        with self._lock:
            self._rx += hdr + payload

    def _send_link(self):
        payload = bytearray(26)
        payload[0] = 1 if self.ready else 0
        struct.pack_into('<HBHHH', payload, 1, 6, 2, 247 if self.ready else 23, 251, 6)
        struct.pack_into('<IIII', payload, 10, 0, self.notifies, 512, self.connects)
        self._push_frame(0x11, bytes(payload))

    def write(self, data: bytes):
        self._tx_cmd += data
        while len(self._tx_cmd) >= 4:
            if self._tx_cmd[0] != 0xA5:
                del self._tx_cmd[:1]
                continue
            plen = self._tx_cmd[2] | (self._tx_cmd[3] << 8)
            if len(self._tx_cmd) < 4 + plen:
                break
            op = self._tx_cmd[1]
            body = bytes(self._tx_cmd[4:4 + plen])
            del self._tx_cmd[:4 + plen]
            self.loop.call_soon_threadsafe(asyncio.create_task, self._handle_op(op, body))
        return len(data)

    async def _handle_op(self, op: int, body: bytes):
        if op == ord('Q'):
            self._send_link()
            self._push_frame(0x80 | op, b'\x00')
        elif op == ord('D'):
            if self.can_reconnect:
                self.ready = True
                self.connects += 1
            else:
                self.ready = False
            self._push_frame(0x80 | op, b'\x00')
        elif op == ord('R') and len(body) == 1 and body[0] in (3, 4):
            uuid = cs.META if body[0] == 3 else cs.STATUS
            val = await self.ble.read_gatt_char(uuid)
            self._push_frame(0x80 | op, b'\x00' + bytes(val))
        elif op == ord('W'):
            await self.ble.write_gatt_char(cs.CONTROL, body)
            self._push_frame(0x80 | op, b'\x00')
        else:
            self._push_frame(0x80 | op, b'\x01')

    def read(self, n: int) -> bytes:
        if self.closed:
            raise OSError('closed')
        with self._lock:
            if self._rx:
                out = bytes(self._rx[:n])
                del self._rx[:n]
                return out
        time.sleep(0.002)
        return b''

    def close(self):
        self.closed = True


async def _run_dongle_usb_e2e(tmp: Path):
    """验证 Mac 主机经 MAKO-DONGLE (dongle_c08b) 0xA5 串口帧跑通 16ch/8ch/2ch + IMU 全链路及断连防拼接反例。"""
    loop = asyncio.get_running_loop()

    # 1. 正向全链路：解锁台架 16ch(v4) / 8ch(v1) / 2ch(v1) + IMU_DATA 从冷启动 NONE 动态识别、落盘 dongle.json 并回放
    for board_afe, exp_ch, exp_proto in (
        ('ADS1298_DUAL', 16, 4),
        ('ADS1298_SINGLE', 8, 1),
        ('ADS1292', 2, 1),
    ):
        ble_dev = FakeC08BBleClient(board_afe=board_afe, initial_afe='NONE', bench_measured=True)
        fake_ser = FakeDongleSerial(ble_dev, loop)
        out_dir = tmp / f'dongle-{board_afe.lower()}'
        res = await cs.run_dongle_c08b(
            '/dev/cu.fake_c08b',
            out_dir,
            seconds=0.07,
            mode='test',
            allow_real=True,
            expected=BUILD_ID,
            with_imu=True,
            open_ser=lambda _p, s=fake_ser: s,
            reconnect_timeout=1.0,
        )
        assert res['transport'] == 'xiao_dongle' and res['afe'] == board_afe and res['protocol'] == exp_proto
        assert res['active_channels'] == exp_ch and res['imu_samples'] >= 1 and res['stop_confirmed']
        dongle_ev = json.loads((out_dir / 'dongle.json').read_text())
        assert dongle_ev['link']['mtu'] == 247 and dongle_ev['junk_bytes'] == 0
        rep = cs.replay_c08b(out_dir, allow_real=True)
        assert rep['uv'].shape == (res['valid_samples'], exp_ch) and rep['imu']['samples'] == res['imu_samples']
    print('  Dongle USB 全链路 ✓ 16ch(v4) / 8ch(v1) / 2ch(v1) + IMU_DATA 经 0xA5 串口帧动态切协议落盘回放全过')

    # 2. 必败反例 A：采集中途 BLE 闪断并被接收器自动重连（connects 自增），必须当场中断报错防跨段拼接！
    ble_drop = FakeC08BBleClient(board_afe='ADS1298_DUAL', initial_afe='NONE', bench_measured=True)
    ser_drop = FakeDongleSerial(ble_drop, loop, inject_mid_reconnect=True)
    drop_dir = tmp / 'dongle-mid-reconnect'
    try:
        await cs.run_dongle_c08b(
            '/dev/cu.fake_drop',
            drop_dir,
            seconds=0.5,
            mode='test',
            allow_real=True,
            expected=BUILD_ID,
            with_imu=True,
            open_ser=lambda _p: ser_drop,
            reconnect_timeout=1.0,
        )
        raise AssertionError('接收器中途自动重连未被拦截（发生跨连接拼接风险）')
    except RuntimeError as err:
        assert '连接中断或重连' in str(err), err
        assert (drop_dir / 'dongle.json').exists()
        print(f'  红 ✓ 接收器中途闪断重连(connects+1)当场拒收防拼接: {err}')

    # 3. 必败反例 B：断开旧连接后未扫到 YUANLI-C08B 广播，按超时干净报错退出
    ble_unseen = FakeC08BBleClient(board_afe='ADS1298_DUAL', initial_afe='NONE', bench_measured=False)
    ser_unseen = FakeDongleSerial(ble_unseen, loop, can_reconnect=False)
    try:
        await cs.run_dongle_c08b(
            '/dev/cu.fake_unseen',
            tmp / 'dongle-unseen',
            seconds=0.1,
            mode='synth',
            open_ser=lambda _p: ser_unseen,
            reconnect_timeout=0.08,
        )
        raise AssertionError('未扫到 YUANLI-C08B 未超时报错')
    except RuntimeError as err:
        assert '未连上 YUANLI-C08B' in str(err), err
        print(f'  红 ✓ 接收器未扫到 YUANLI-C08B 干净超时退出: {err}')


def main():
    with tempfile.TemporaryDirectory(prefix='c08b-stream-check-') as td:
        tmp = Path(td)
        test_c_firmware_parity(tmp)
        test_protocol_negatives()
        asyncio.run(_run_ble_tests(tmp))
        asyncio.run(_run_dongle_usb_e2e(tmp))
        test_studio_acq_and_recording(tmp)
    print('check_c08b_stream: C08B 2/8/16ch 跨语言对拍、安全锁红线、冷启动动态识别、BLE/Dongle 双通道归档回放与 Studio 全链路全部通过')


if __name__ == '__main__':
    main()

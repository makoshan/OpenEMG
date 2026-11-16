#!/usr/bin/env python3
"""Sim-2: OpenEMG v0.01 c08b-stream (S140=1) 双核全硅在环测试（锁死构建 + 台架全模态 + DSP-F03 + 互锁竞态与故障反例）。"""
from __future__ import annotations

import asyncio
import ctypes
import json
import math
import shutil
import struct
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from sim_ctypes import (
    HAZ_NONE,
    REPO_DIR,
    SIM_DIR,
    SIM_MAINBOARD_MCU_U9_V001,
    SIM_MAINBOARD_R4U6,
    SIM_SUBBOARD_ADS1292_2CH,
    SIM_SUBBOARD_AFE30P_16CH,
    SIM_SUBBOARD_D20_8CH,
    SIM_WAVE_SEMG_PHYSIOL,
    SIM_WAVE_SINGLE_CH,
    SIM_WAVE_TONE_SWEEP,
    SimConfig,
    get_tel,
    load_twin,
)

sys.path.insert(0, str(REPO_DIR / "host"))
sys.path.insert(0, str(REPO_DIR / "firmware" / "dsp-f03"))

import ads1292_regs  # noqa: E402
import ads1298_regs  # noqa: E402
import c08b_stream  # noqa: E402
import device_desc  # noqa: E402
from c08b_stream import (  # noqa: E402
    CONTROL,
    DATA,
    IMU_DATA,
    META,
    SERVICE,
    STATUS,
    SYNTHETIC,
    C08BRig,
    capture_c08b,
    decode_16ch,
    decode_frame_16ch,
    decode_status,
    replay_c08b,
)
from rig.acq import AcqHandler  # noqa: E402
from runtime import DSP, compile_library  # noqa: E402


def extract_16ch_raw_codes(capture_dir: Path) -> np.ndarray:
    """从 RawArchive events.jsonl 解出精确 24 位有符号整数码矩阵 (N, 16)，供 C99 DSP-F03 零损输入。"""
    rows = []
    for line in (capture_dir / "events.jsonl").read_text(encoding="utf-8").splitlines():
        ev = json.loads(line)
        if ev == {"disconnect": True}:
            continue
        pkt = decode_16ch(bytes.fromhex(ev["packet_hex"]), ev["mtu"])
        for f in pkt.frames:
            rows.append(decode_frame_16ch(f)[2])
    return np.asarray(rows, dtype=np.int32)


UUID_TO_SUFFIX = {
    DATA: 2,
    META: 3,
    STATUS: 4,
    CONTROL: 5,
    IMU_DATA: 6,
}


@dataclass(frozen=True)
class _FakeChar:
    uuid: str


class _FakeService:
    def __init__(self):
        self.characteristics = [_FakeChar(u) for u in (DATA, META, STATUS, CONTROL, IMU_DATA)]


class _FakeServices:
    def get_service(self, uuid: str):
        return _FakeService() if str(uuid).lower() == SERVICE else None


class _SimClockProxy:
    """将 c08b_stream 内的 time.monotonic 映射到双核硬件孪生的微秒时钟，消除 OS 调度抖动。"""

    def __init__(self, lib: ctypes.CDLL, real_time_mod):
        self._lib = lib
        self._real = real_time_mod

    def monotonic(self) -> float:
        return get_tel(self._lib).sim_time_us * 1e-6

    def monotonic_ns(self) -> int:
        return int(get_tel(self._lib).sim_time_us) * 1000

    def __getattr__(self, name: str):
        return getattr(self._real, name)


class SilBleClient:
    """实现 BleakClient 异步契约并直接驱动编译后的 C 固件双核硬件孪生。"""

    def __init__(self, lib: ctypes.CDLL, mtu: int = 247, step_hook=None):
        self.lib = lib
        self.mtu_size = mtu
        self.services = _FakeServices()
        self.is_connected = False
        self._cbs: dict[int, callable] = {}
        self._step_hook = step_hook
        self._orig_sleep = None
        self._orig_time = None

    def connect(self):
        self.lib.sim_ble_connect(self.mtu_size)
        self.is_connected = True

    def disconnect_now(self):
        self.lib.sim_ble_disconnect()
        self.is_connected = False
        self.pump_notifications()

    def pump_notifications(self):
        sfx = ctypes.c_uint8(0)
        buf = (ctypes.c_uint8 * 512)()
        ts = ctypes.c_uint64(0)
        while True:
            n = self.lib.sim_ble_pop_notify(ctypes.byref(sfx), buf, 512, ctypes.byref(ts))
            if n <= 0:
                break
            cb = self._cbs.get(int(sfx.value))
            if cb is not None:
                cb(int(sfx.value), bytearray(buf[:n]))

    async def __aenter__(self):
        self.connect()
        self._orig_sleep = asyncio.sleep
        self._orig_time = c08b_stream.time
        c08b_stream.time = _SimClockProxy(self.lib, self._orig_time)

        async def _sim_sleep(delay: float, result=None):
            us = max(200, int(round(delay * 1_000_000)))
            # 按 2 ms 切片推进双核硅时钟，实时派发 BLE HVX 通知与故障钩子
            rem = us
            while rem > 0:
                chunk = min(2000, rem)
                self.lib.sim_step_us(chunk)
                rem -= chunk
                if self._step_hook is not None:
                    self._step_hook(self)
                self.pump_notifications()
            await self._orig_sleep(0)
            return result

        asyncio.sleep = _sim_sleep
        return self

    async def __aexit__(self, exc_type, exc, tb):
        if self._orig_sleep is not None:
            asyncio.sleep = self._orig_sleep
        if self._orig_time is not None:
            c08b_stream.time = self._orig_time
        if self.is_connected:
            self.disconnect_now()

    async def read_gatt_char(self, uuid: str) -> bytearray:
        sfx = UUID_TO_SUFFIX[str(uuid).lower()]
        buf = (ctypes.c_uint8 * 512)()
        n = self.lib.sim_ble_read_char(sfx, buf, 512)
        self.pump_notifications()
        if n < 0:
            raise RuntimeError(f"GATT read failed for suffix {sfx}")
        return bytearray(buf[:n])

    async def write_gatt_char(self, uuid: str, data: bytes, response: bool = True):
        assert str(uuid).lower() == CONTROL
        arr = (ctypes.c_uint8 * len(data))(*data)
        rc = self.lib.sim_ble_write_ctrl(arr, len(data))
        assert rc == 0
        self.lib.sim_step_us(1000)
        self.pump_notifications()

    async def start_notify(self, uuid: str, callback):
        sfx = UUID_TO_SUFFIX[str(uuid).lower()]
        self._cbs[sfx] = callback
        rc = self.lib.sim_ble_subscribe(sfx, True)
        assert rc == 0
        self.pump_notifications()

    async def stop_notify(self, uuid: str):
        sfx = UUID_TO_SUFFIX[str(uuid).lower()]
        if self.is_connected:
            self.lib.sim_ble_subscribe(sfx, False)
        self._cbs.pop(sfx, None)


def boot_board(lib: ctypes.CDLL, **overrides) -> SimConfig:
    cfg = SimConfig()
    lib.sim_default_config(ctypes.byref(cfg))
    for k, v in overrides.items():
        setattr(cfg, k, v)
    lib.sim_init(ctypes.byref(cfg))
    # 冷启动推进 260 ms：完成 Errata 249 单次复位、S140 协议栈初始化与 L432<->nRF 初始心跳同步
    lib.sim_step_us(260_000)
    return cfg


def read_build_id(lib: ctypes.CDLL) -> str:
    buf = (ctypes.c_uint8 * 512)()
    n = lib.sim_ble_read_char(3, buf, 512)
    meta = json.loads(bytes(buf[:n]))
    return meta["build_id"]


async def async_main() -> int:
    lib_locked = load_twin("libsim2_stream_locked.dylib")
    lib_bench = load_twin("libsim2_stream_bench.dylib")
    cases_out = []

    with tempfile.TemporaryDirectory(prefix="v001-sim2-") as tmp_str:
        tmp = Path(tmp_str)
        dsp_dir = tmp / "dsp_build"
        dsp_dir.mkdir(parents=True, exist_ok=True)
        dsp_lib = compile_library(dsp_dir)

        # =====================================================================
        # A. 仓库默认双锁关闭构建（MAKO_C08B_AFE_ENABLED=0, MAKO_BENCH_MEASURED=0）
        # =====================================================================
        boot_board(lib_locked, subboard_kind=SIM_SUBBOARD_AFE30P_16CH)
        adv_name_buf = ctypes.create_string_buffer(32)
        lib_locked.sim_ble_get_adv_name(adv_name_buf, 32)
        adv_name = adv_name_buf.value.decode("utf-8")
        assert adv_name == "YUANLI-C08B", f"expected YUANLI-C08B, got {adv_name!r}"

        async with SilBleClient(lib_locked) as cli:
            raw_meta = json.loads(bytes(await cli.read_gatt_char(META)))
            assert raw_meta["afe"] == "NONE"
            assert raw_meta["protocol"] == 1 and raw_meta["active_channels"] == 0
            assert raw_meta["bench_measured"] is False
            locked_build_id = raw_meta["build_id"]

            # 主机侧门禁拒绝真采样；直接绕过主机门禁写 TST1 进固件 CONTROL 亦必须触发 FAULT_LOCKED(1) 且 ANA_EN 全程为 0！
            host_rejected = False
            try:
                await capture_c08b(
                    cli, tmp / "locked_tst1_host", seconds=0.2, mode="test",
                    allow_real=True, expected=locked_build_id,
                )
            except ValueError as e:
                host_rejected = "bench_measured=false" in str(e)
            assert host_rejected

            await cli.write_gatt_char(CONTROL, b"TST1")
            lib_locked.sim_step_us(260_000)  # 覆盖 L432 2×20ms 心跳回传 + nRF 200ms refresh_gatt_meta_and_status()
            st_locked = decode_status(bytes(await cli.read_gatt_char(STATUS)))
            tel_locked = get_tel(lib_locked)
            assert st_locked["fault"] == 1, st_locked  # C08B_FAULT_LOCKED = 1
            assert tel_locked.ana_en_level is False

        # 清故障重连跑 SYN1 16CH@1000Hz + IMU -> replay_c08b -> AcqHandler 全链路
        boot_board(lib_locked, subboard_kind=SIM_SUBBOARD_AFE30P_16CH)
        async with SilBleClient(lib_locked) as cli:
            syn_dir = tmp / "locked_syn16_imu"
            res_syn16 = await capture_c08b(
                cli, syn_dir, seconds=0.5, mode="synth", with_imu=True, synth_channels=16, poll_seconds=0.05
            )
            assert res_syn16["protocol"] == 4 and res_syn16["active_channels"] == 16
            assert res_syn16["valid_samples"] >= 480 and res_syn16["missing_samples"] == 0
            # 非阻塞硬件 I2C1 状态机消除批次量化：0.5s 原生 104 Hz 稳定送达 ~50-52 帧
            assert res_syn16["imu_samples"] >= 46 and res_syn16["imu_missing_samples"] == 0
            assert res_syn16["stop_confirmed"] is True
            tel_syn16 = get_tel(lib_locked)
            assert tel_syn16.ana_en_level is False
            assert tel_syn16.l432_hclk_hz == 64_000_000
            assert tel_syn16.spi3_sclk_hz == 8_000_000
            assert tel_syn16.hazard_mask == HAZ_NONE

            rep_syn16 = replay_c08b(syn_dir, allow_real=False)
            assert rep_syn16["samples"] == res_syn16["valid_samples"]
            assert rep_syn16["missing_samples"] == 0 and rep_syn16["bad_status_frames"] == 0

            # 验证 OpenEMG Studio C08BRig + AcqHandler 订阅链路可直接无损流式消费全部数据包与 IMU 包
            rig_16 = C08BRig(n_channels=16, fs_Hz=1000, allow_real=False)
            acq = AcqHandler(rig_16, device_desc.load("c08b-16ch"))
            acq_blocks = []
            acq.subscribe(lambda blk: acq_blocks.append(blk))
            acq.start()
            for line in (syn_dir / "events.jsonl").read_text(encoding="utf-8").splitlines():
                ev = json.loads(line)
                if ev != {"disconnect": True}:
                    rig_16.feed_packet(bytes.fromhex(ev["packet_hex"]), ev["mtu"])
            for line in (syn_dir / "imu-events.jsonl").read_text(encoding="utf-8").splitlines():
                ev = json.loads(line)
                if ev != {"disconnect": True}:
                    rig_16.feed_imu_packet(bytes.fromhex(ev["packet_hex"]), ev["mtu"])
            assert acq.n_samples == res_syn16["valid_samples"] and acq.dropped == 0
            assert rig_16.imu_rx.accepted_samples == res_syn16["imu_samples"]
            acq.stop()

        cases_out.append({
            "id": "L2-LOCKED-GATE-SYNTH",
            "title": "默认双锁关闭镜像（0/0）：冷启动诚实报告 NONE，主机+固件双重拦截 TST1(FAULT_LOCKED=1, ANA_EN=0)，SYN1 16CH+IMU 全链路通过",
            "pass": True,
            "adv_name": adv_name,
            "cold_meta_afe": "NONE",
            "fw_locked_fault": st_locked["fault"],
            "syn16_samples": res_syn16["valid_samples"],
            "syn16_imu_samples": res_syn16["imu_samples"],
        })

        # =====================================================================
        # B. 暂存区离体台架镜像（1/1 scratch-only）：PRB1 / TST1 / SHT1 / EXR1+DSP
        # =====================================================================
        # 1. P2-PRB1: 16CH / 8CH / 2CH 三种采集板只读探测与即刻断电验证
        prb_summary = {}
        for kind, exp_afe, exp_proto, exp_act, exp_spi in (
            (SIM_SUBBOARD_AFE30P_16CH, "ADS1298_DUAL", 4, 16, 4_000_000),
            (SIM_SUBBOARD_D20_8CH, "ADS1298_SINGLE", 1, 8, 4_000_000),
            (SIM_SUBBOARD_ADS1292_2CH, "ADS1292", 1, 2, 1_000_000),
        ):
            # 对 2CH 同时开启 strict_ads1292_por=True，证明 c08b-stream 1050ms 等待彻底通过冷启动 512ms tPOR 门禁！
            boot_board(lib_bench, subboard_kind=kind, strict_ads1292_por=True)
            bid = read_build_id(lib_bench)
            async with SilBleClient(lib_bench) as cli:
                res_p = await capture_c08b(
                    cli, tmp / f"prb_{exp_act}ch", seconds=2.0, mode="probe",
                    allow_real=True, expected=bid, poll_seconds=0.05,
                )
                tel_p = get_tel(lib_bench)
                assert res_p["afe"] == exp_afe and res_p["protocol"] == exp_proto
                assert res_p["active_channels"] == exp_act and res_p["spi_Hz"] == exp_spi
                assert res_p["stop_confirmed"] is True
                assert tel_p.ana_en_level is False
                assert tel_p.hazard_mask == HAZ_NONE, f"PRB1 hazard on {exp_afe}: 0x{tel_p.hazard_mask:X}"
                prb_summary[f"{exp_act}ch"] = {
                    "afe": res_p["afe"],
                    "protocol": res_p["protocol"],
                    "spi_Hz": res_p["spi_Hz"],
                    "ana_en_after": tel_p.ana_en_level,
                    "hazard_mask": f"0x{tel_p.hazard_mask:04X}",
                }
        cases_out.append({
            "id": "P2-PRB1-ALL",
            "title": "PRB1 子板只读探测（16CH v4 / 8CH v1 / 2CH v1 严格 512ms 冷启 POR）：动态识别并即刻关断 ANA_EN，零电气违规",
            "pass": True,
            "subboards": prb_summary,
        })

        # 2. P2-TST1 & P2-SHT1: 16CH@1000Hz, 8CH@2000Hz, 2CH@500Hz 真采样通路 + ads1298_regs 交叉核对
        stream_modes_out = {}
        for label, kind, fs_req, mode_name in (
            ("16ch_1k_test", SIM_SUBBOARD_AFE30P_16CH, 1000, "test"),
            ("16ch_1k_short", SIM_SUBBOARD_AFE30P_16CH, 1000, "short"),
            ("8ch_2k_short", SIM_SUBBOARD_D20_8CH, 2000, "short"),
            ("2ch_500_test", SIM_SUBBOARD_ADS1292_2CH, 500, "test"),
        ):
            boot_board(lib_bench, subboard_kind=kind, strict_ads1292_por=True)
            bid = read_build_id(lib_bench)
            async with SilBleClient(lib_bench) as cli:
                # 若采样率非默认 1000 Hz，先通过带采样率扩展字节的控制包设定 fs_Hz，再停回待机
                if fs_req != 1000:
                    await cli.write_gatt_char(CONTROL, b"SYN1" + struct.pack("<HB", fs_req, 8))
                    lib_bench.sim_step_us(30_000)
                    await cli.write_gatt_char(CONTROL, b"STOP")
                    lib_bench.sim_step_us(40_000)
                    cli.pump_notifications()

                # 在收到首包时抓取芯片真实在线寄存器镜像核对 ads1298_regs.check()
                live_reg_snap = {}

                def _snap_regs():
                    t_now = get_tel(lib_bench)
                    live_reg_snap["u1"] = list(t_now.ads_regs[0])
                    live_reg_snap["u2"] = list(t_now.ads_regs[1])
                    live_reg_snap["spi1_hz"] = t_now.spi1_sclk_hz

                out_d = tmp / f"cap_{label}"
                res_m = await capture_c08b(
                    cli, out_d, seconds=0.8, mode=mode_name,
                    allow_real=True, expected=bid, with_imu=True, poll_seconds=0.04,
                    on_first_data=_snap_regs,
                )
                tel_m = get_tel(lib_bench)
                assert tel_m.hazard_mask == HAZ_NONE
                assert res_m["missing_samples"] == 0 and res_m["bad_packets"] == 0
                assert res_m["bad_status_frames"] == 0 and res_m["stop_confirmed"] is True
                # 500 SPS 每批 4 帧(8ms < 9ms -> 量化为 16ms ≈ 62.5Hz, 0.8s ~48帧)；1k ~66帧；2k ~82帧
                min_imu_exp = 44 if fs_req == 500 else 60
                assert res_m["imu_samples"] >= min_imu_exp and res_m["imu_missing_samples"] == 0

                rep_m = replay_c08b(out_d, allow_real=True)
                # 反向校验证明真采样包绝未误打 SYNTHETIC 标志（allow_real=False 必须拒绝！）
                rejected_as_real = False
                try:
                    replay_c08b(out_d, allow_real=False)
                except ValueError:
                    rejected_as_real = True
                assert rejected_as_real, "Real capture packet unexpectedly carried SYNTHETIC flag!"
                arr_uv = rep_m["uv"]  # shape (N, active_channels)
                rms_uv = float(np.sqrt(np.mean(arr_uv ** 2)))
                pp_uv = float(np.median(np.ptp(arr_uv, axis=0)))

                if kind in (SIM_SUBBOARD_AFE30P_16CH, SIM_SUBBOARD_D20_8CH):
                    u1_bytes = bytes(live_reg_snap["u1"][:0x1A])
                    reg_errs = ads1298_regs.check(u1_bytes)
                    assert reg_errs == [], f"U1 ads1298_regs Violation: {reg_errs}"
                    assert (u1_bytes[0x03] & 0x38) == 0
                    if kind == SIM_SUBBOARD_AFE30P_16CH:
                        u2_bytes = bytes(live_reg_snap["u2"][:0x1A])
                        reg_errs_u2 = ads1298_regs.check(u2_bytes)
                        assert reg_errs_u2 == [], f"U2 ads1298_regs Violation: {reg_errs_u2}"
                        assert (u2_bytes[0x03] & 0x38) == 0
                elif kind == SIM_SUBBOARD_ADS1292_2CH:
                    u1_1292 = bytes(live_reg_snap["u1"][:0x0C])
                    reg_errs_1292 = ads1292_regs.check(u1_1292)
                    assert reg_errs_1292 == [], f"ADS1292 regs Violation: {reg_errs_1292}"

                if mode_name == "short":
                    assert 0.5 <= rms_uv <= 3.0, f"short noise out of TI spec: {rms_uv} uVrms"
                else:
                    assert 1850.0 <= pp_uv <= 2150.0, f"test square wave out of spec: {pp_uv} uVpp"

                stream_modes_out[label] = {
                    "fs_Hz": res_m["fs_Hz"],
                    "protocol": res_m["protocol"],
                    "spi1_hz": live_reg_snap["spi1_hz"],
                    "valid_samples": res_m["valid_samples"],
                    "imu_samples": res_m["imu_samples"],
                    "pp_uv": round(pp_uv, 1),
                    "rms_uv": round(rms_uv, 3),
                    "hazard_mask": f"0x{tel_m.hazard_mask:04X}",
                }
        cases_out.append({
            "id": "P2-TST1-SHT1-MATRIX",
            "title": "16CH@1k / 8CH@2k / 2CH@500 方波与输入短接底噪 + 104Hz 同源时间戳 IMU + ads1298_regs 零违规",
            "pass": True,
            "modes": stream_modes_out,
        })

        # 3. P2-EXR1-DSP & 16x16 串扰矩阵：2000 Hz 生理肌电 + 400 µV 50Hz 工频共模 -> RLD 26dB + DSP-F03 陷波联合抑制
        # 注：此处设 imu_present=False 以隔离验证纯 AFE+RLD+DSP 频响；imu_present=True 在 16MHz HSI 下引发的 2kSPS I2C 阻塞丢拍在 NC-2g 专门实证！
        cmrr_compare = {}
        for m_key in ("external", "rld"):
            boot_board(
                lib_bench,
                subboard_kind=SIM_SUBBOARD_AFE30P_16CH,
                imu_present=False,
                wave_mode=SIM_WAVE_TONE_SWEEP,
                tone_amp_uv=250.0,
                mains_50hz_cm_uv=400.0,
                crosstalk_ratio=1e-4,
            )
            bid = read_build_id(lib_bench)
            u1_cfg3_live = []

            def _snap_rld():
                t_now = get_tel(lib_bench)
                u1_cfg3_live.extend([t_now.ads_regs[0][0x03], t_now.ads_regs[1][0x03]])

            async with SilBleClient(lib_bench) as cli:
                await cli.write_gatt_char(CONTROL, b"SYN1" + struct.pack("<HB", 2000, 16))
                lib_bench.sim_step_us(30_000)
                await cli.write_gatt_char(CONTROL, b"STOP")
                lib_bench.sim_step_us(40_000)
                cli.pump_notifications()

                out_d = tmp / f"dsp_{m_key}"
                res_d = await capture_c08b(
                    cli, out_d, seconds=2.4, mode=m_key,
                    allow_real=True, expected=bid, poll_seconds=0.04,
                    on_first_data=_snap_rld,
                )
                tel_d = get_tel(lib_bench)
                assert tel_d.hazard_mask == HAZ_NONE, f"RLD warmup hazard: 0x{tel_d.hazard_mask:X}"
                assert res_d["missing_samples"] == 0

            rep_d = replay_c08b(out_d, allow_real=True)
            codes_16 = extract_16ch_raw_codes(out_d)  # int32 (N, 16)
            uv_raw = rep_d["uv"]

            # 送入真实编译的 firmware/dsp-f03 C99 滤波器（Q30 50Hz 陷波 guard=2639 样点 ≈ 1.32s）
            dsp_a = DSP(dsp_lib, 2000, notch=True)
            dsp_b = DSP(dsp_lib, 2000, notch=True)
            y_a, rdy_a = dsp_a.process(np.ascontiguousarray(codes_16[:, :8], dtype=np.int32))
            y_b, rdy_b = dsp_b.process(np.ascontiguousarray(codes_16[:, 8:16], dtype=np.int32))
            assert np.array_equal(rdy_a, rdy_b) and (not rdy_a[:2639].any()) and rdy_a[2639:].all()
            # DSP 输出为满量程归一化比例，换算回 µV（VREF=2.4V, Gain=6 -> 满量程 400,000 µV）
            uv_dsp = np.hstack([y_a, y_b])[rdy_a] * 400_000.0
            uv_steady = uv_raw[rdy_a]

            # 用 1600 点精确整周期 DFT (Δf=1.25Hz，50Hz=bin40，80Hz=bin64 零频谱泄漏) 提取工频与有效肌电分量
            n_fft = (len(uv_steady) // 1600) * 1600
            assert n_fft >= 1600, f"steady samples {len(uv_steady)} < 1600"
            freqs = np.fft.rfftfreq(n_fft, d=1.0 / 2000.0)
            idx_50 = int(np.argmin(np.abs(freqs - 50.0)))
            idx_80 = int(np.argmin(np.abs(freqs - 80.0)))
            spec_raw = np.abs(np.fft.rfft(uv_steady[:n_fft, 3])) * (2.0 / n_fft)
            spec_dsp = np.abs(np.fft.rfft(uv_dsp[:n_fft, 3])) * (2.0 / n_fft)

            cmrr_compare[m_key] = {
                "u1_u2_cfg3_hex": [f"0x{x:02X}" for x in u1_cfg3_live],
                "raw_50hz_peak_uv": round(float(spec_raw[idx_50]), 2),
                "dsp_50hz_peak_uv": round(float(spec_dsp[idx_50]), 4),
                "dsp_80hz_semg_uv": round(float(spec_dsp[idx_80]), 2),
            }

        # 验证 EXR1 下 U1 CONFIG3=0xC4, U2 CONFIG3=0xC0；RLD 硬件抑制 ~26 dB (400->20 µV)，叠加 DSP-F03 陷波后总抑制 > 65 dB！
        assert cmrr_compare["rld"]["u1_u2_cfg3_hex"] == ["0xC4", "0xC0"]
        rld_atten_db = 20.0 * math.log10(
            cmrr_compare["external"]["raw_50hz_peak_uv"] / cmrr_compare["rld"]["raw_50hz_peak_uv"]
        )
        total_atten_db = 20.0 * math.log10(
            cmrr_compare["external"]["raw_50hz_peak_uv"] / max(1e-6, cmrr_compare["rld"]["dsp_50hz_peak_uv"])
        )
        assert 24.0 <= rld_atten_db <= 28.0, (rld_atten_db, total_atten_db, cmrr_compare)
        assert total_atten_db >= 60.0, (rld_atten_db, total_atten_db, cmrr_compare)
        assert cmrr_compare["rld"]["dsp_80hz_semg_uv"] > 80.0, cmrr_compare

        # 单通道激励测定 16x16 邻道串扰（激励 CH5 = index 4，100 mV (-12 dBFS, 满量程 ±400 mV) @ 100 Hz，信噪比 >115 dB）
        boot_board(
            lib_bench,
            subboard_kind=SIM_SUBBOARD_AFE30P_16CH,
            wave_mode=SIM_WAVE_SINGLE_CH,
            active_single_ch=4,
            tone_amp_uv=100_000.0,
            mains_50hz_cm_uv=0.0,
            crosstalk_ratio=1e-4,
        )
        bid = read_build_id(lib_bench)
        async with SilBleClient(lib_bench) as cli:
            xt_dir = tmp / "xtalk_ch5"
            await capture_c08b(
                cli, xt_dir, seconds=0.6, mode="external", allow_real=True, expected=bid, poll_seconds=0.04
            )
        xt_uv = replay_c08b(xt_dir, allow_real=True)["uv"]
        n_xt = (len(xt_uv) // 10) * 10
        f_xt = np.fft.rfftfreq(n_xt, d=1.0 / 1000.0)
        i100 = int(np.argmin(np.abs(f_xt - 100.0)))
        amp100 = [float(np.abs(np.fft.rfft(xt_uv[:n_xt, c]))[i100] * (2.0 / n_xt)) for c in range(16)]
        adj_db = 20.0 * math.log10(amp100[3] / amp100[4])
        far_db = 20.0 * math.log10(max(amp100[0], amp100[12]) / amp100[4])
        assert -83.0 <= adj_db <= -77.0 and far_db < -95.0

        cases_out.append({
            "id": "P2-EXR1-DSP-XTALK",
            "title": "EXR1 两步法 RLD 预热闭环 + DSP-F03 C99 陷波级联频谱验证 & 16CH 邻道串扰测定",
            "pass": True,
            "rld_cmrr_db": round(rld_atten_db, 2),
            "rld_plus_dsp_50hz_rejection_db": round(total_atten_db, 2),
            "adjacent_crosstalk_db": round(adj_db, 2),
            "non_adjacent_crosstalk_db": round(far_db, 2),
            "cmrr_detail": cmrr_compare,
        })

        # =====================================================================
        # C. 实时故障注入与 MCU-U9 硬件互锁竞态实证套件（NC-2a .. NC-2f，含 Finding #2 实证）
        # =====================================================================
        # NC-2a: 采集中途热插 USB VBUS=1（对比 MCU-U9 PH3=0 与 R4U6 PH3=VBUS 关断延迟）
        race_results = {}
        for rev_name, rev_id in (("MCU_U9_v001", SIM_MAINBOARD_MCU_U9_V001), ("R4U6_ref", SIM_MAINBOARD_R4U6)):
            boot_board(lib_bench, mainboard_rev=rev_id, subboard_kind=SIM_SUBBOARD_AFE30P_16CH)
            bid = read_build_id(lib_bench)
            injected = {"done": False}

            def _inject_vbus_hook(cli_obj: SilBleClient):
                t_cur = get_tel(cli_obj.lib)
                if not injected["done"] and t_cur.ads_start_level and t_cur.sim_time_us > 1_650_000:
                    injected["done"] = True
                    cli_obj.lib.sim_set_vbus(True)

            fault_err = None
            async with SilBleClient(lib_bench, step_hook=_inject_vbus_hook) as cli:
                try:
                    await capture_c08b(
                        cli, tmp / f"nc2a_{rev_name}", seconds=0.8, mode="test",
                        allow_real=True, expected=bid, poll_seconds=0.02,
                    )
                except Exception as e:
                    fault_err = str(e)
                lib_bench.sim_step_us(250_000)
                st_end = decode_status(bytes(await cli.read_gatt_char(STATUS)))
                tel_end = get_tel(lib_bench)

            nrf_dt_us = int(tel_end.nrf_stop_us - tel_end.vbus_inject_us) if tel_end.nrf_stop_us else None
            ana_dt_us = int(tel_end.ana_en_off_us - tel_end.vbus_inject_us) if tel_end.ana_en_off_us else None
            assert tel_end.ana_en_level is False and tel_end.oe_n_level is True
            assert st_end["fault"] == 3, st_end  # C08B_FAULT_INTERLOCK = 3
            race_results[rev_name] = {
                "nrf_stop_latency_us": nrf_dt_us,
                "l432_ana_en_off_latency_us": ana_dt_us,
                "zero_frames_leaked_to_ble": tel_end.zero_frames_leaked,
                "final_fault": st_end["fault"],
                "host_exception": fault_err,
            }
        # 实证：R701 在 OE_N=1 瞬间拉低 PA2(DRDY_A)=0 使 read_one_afe_slot 内 while(GET(DRDY_A)) 被绕过，
        # 两版主板均在 <5 ms 内经 SPIS1/主循环切断 ANA_EN=0，且 nRF P0.01 VBUS 纪元屏障确保 0 帧零包漏进 BLE！
        for rk in ("MCU_U9_v001", "R4U6_ref"):
            assert race_results[rk]["l432_ana_en_off_latency_us"] is not None
            assert race_results[rk]["l432_ana_en_off_latency_us"] < 5000, race_results
            assert race_results[rk]["zero_frames_leaked_to_ble"] == 0, race_results
        cases_out.append({
            "id": "NC-2a",
            "title": "反例：采集中热插 USB VBUS=1 互锁急停竞态测定（MCU-U9 PH3=0 跨核关断 vs R4U6 本地关断）",
            "pass": True,
            "expected_red_caught": True,
            "race_comparison": race_results,
        })

        # NC-2b (Finding #2 已闭环修复): 模拟独立硬件互锁动作 OE_N=1 (而 VBUS=0，例如 U4/EN_RC 保护跳闸)
        # 验证：R701/R702 下拉产生 0x000000 首槽时，L432 与 nRF 双重 0xC0 状态头铁闸当场拦截，
        # 0 帧零包漏进 BLE HVX，L432 <2ms 内切断 ANA_EN=0 并锁存 C08B_FAULT_BAD_FRAME(6)！
        boot_board(lib_bench, mainboard_rev=SIM_MAINBOARD_MCU_U9_V001, subboard_kind=SIM_SUBBOARD_AFE30P_16CH)
        bid = read_build_id(lib_bench)
        oe_injected = {"done": False, "snapped": False, "inject_us": 0, "mid_fault": None, "mid_ana_en": None}

        def _inject_oe_high_hook(cli_obj: SilBleClient):
            t_cur = get_tel(cli_obj.lib)
            if not oe_injected["done"] and t_cur.ads_start_level and t_cur.sim_time_us > 1_650_000:
                oe_injected["done"] = True
                oe_injected["inject_us"] = int(t_cur.sim_time_us)
                cli_obj.lib.sim_set_force_oe_n_high(True)
            elif oe_injected["done"] and not oe_injected["snapped"] and t_cur.sim_time_us >= oe_injected["inject_us"] + 6_000:
                oe_injected["snapped"] = True
                sb = (ctypes.c_uint8 * 512)()
                sn = cli_obj.lib.sim_ble_read_char(4, sb, 512)
                oe_injected["mid_fault"] = decode_status(bytes(sb[:sn]))["fault"]
                oe_injected["mid_ana_en"] = get_tel(cli_obj.lib).ana_en_level

        oe_host_err = None
        async with SilBleClient(lib_bench, step_hook=_inject_oe_high_hook) as cli:
            try:
                await capture_c08b(
                    cli, tmp / "nc2b_oe_fault", seconds=0.6, mode="test",
                    allow_real=True, expected=bid, poll_seconds=0.02,
                )
            except Exception as e:
                oe_host_err = str(e)
            tel_oe = get_tel(lib_bench)

        oe_ana_off_dt_us = int(tel_oe.ana_en_off_us - tel_oe.vbus_inject_us)
        assert tel_oe.zero_frames_leaked == 0, f"Zero frames leaked: {tel_oe.zero_frames_leaked}"
        assert oe_injected["mid_fault"] == 6 and oe_injected["mid_ana_en"] is False, oe_injected
        assert oe_host_err is not None and "fault=6" in oe_host_err, oe_host_err
        assert tel_oe.ana_en_level is False and 0 <= oe_ana_off_dt_us < 2000, oe_ana_off_dt_us
        cases_out.append({
            "id": "NC-2b",
            "title": "反例（Finding #2 已修复）：独立拉高 OE_N=1 时双核 0xC0 铁闸 0 零帧泄漏，立即切断 ANA_EN=0 并报 FAULT_BAD_FRAME(6)",
            "pass": True,
            "expected_red_caught": True,
            "zero_frames_leaked_over_ble": tel_oe.zero_frames_leaked,
            "fw_fault_code": oe_injected["mid_fault"],
            "l432_ana_en_off_latency_us": oe_ana_off_dt_us,
            "host_caught_error": oe_host_err,
        })

        # NC-2c: DRDY_A 停振超时 -> FAULT_DRDY_TO(8)，ANA_EN 立即关断（capture_c08b 捕获 fault=8 后自动发 STOP 复位）
        boot_board(lib_bench, subboard_kind=SIM_SUBBOARD_AFE30P_16CH, drdy_a_timeout=True)
        bid = read_build_id(lib_bench)
        drdy_err = None
        async with SilBleClient(lib_bench) as cli:
            try:
                await capture_c08b(
                    cli, tmp / "nc2c_drdy_to", seconds=0.5, mode="test",
                    allow_real=True, expected=bid, poll_seconds=0.04,
                )
            except RuntimeError as e:
                drdy_err = str(e)
            tel_drdy = get_tel(lib_bench)
        assert drdy_err is not None and "fault=8" in drdy_err, drdy_err
        assert tel_drdy.ana_en_level is False
        cases_out.append({
            "id": "NC-2c",
            "title": "反例：DRDY_A 停振 >20ms -> 固件置 FAULT_DRDY_TO(8) 并切断 ANA_EN=0，主机准确捕获 fault=8",
            "pass": True,
            "expected_red_caught": True,
            "fault": 8,
            "host_error": drdy_err,
            "ana_en_after": tel_drdy.ana_en_level,
        })

        # NC-2d: ADS 寄存器回读篡改 1 bit -> FAULT_READBACK(5)，ANA_EN 立即关断
        boot_board(lib_bench, subboard_kind=SIM_SUBBOARD_AFE30P_16CH, reg_readback_fault=True)
        bid = read_build_id(lib_bench)
        rb_err = None
        async with SilBleClient(lib_bench) as cli:
            try:
                await capture_c08b(
                    cli, tmp / "nc2d_readback", seconds=0.5, mode="test",
                    allow_real=True, expected=bid, poll_seconds=0.04,
                )
            except RuntimeError as e:
                rb_err = str(e)
            tel_rb = get_tel(lib_bench)
        assert rb_err is not None and "fault=5" in rb_err, rb_err
        assert tel_rb.ana_en_level is False
        cases_out.append({
            "id": "NC-2d",
            "title": "反例：ADS1298 寄存器回读单比特翻转 -> 固件置 FAULT_READBACK(5) 并切断 ANA_EN=0，主机准确捕获 fault=5",
            "pass": True,
            "expected_red_caught": True,
            "fault": 5,
            "host_error": rb_err,
            "ana_en_after": tel_rb.ana_en_level,
        })

        # NC-2e: 2CH 采集中途 U3 3.0V LDO 欠压跌落 -> PA4 实时监测置 FAULT_INTERLOCK(3) 并立即断 ANA_EN=0，主机当场捕获 fault=3
        boot_board(lib_bench, subboard_kind=SIM_SUBBOARD_ADS1292_2CH, strict_ads1292_por=True)
        bid = read_build_id(lib_bench)
        avdd_dropped = {"done": False, "snapped": False, "inject_us": 0, "mid_fault": None, "mid_ana_en": None}

        def _drop_avdd_hook(cli_obj: SilBleClient):
            t_cur = get_tel(cli_obj.lib)
            if not avdd_dropped["done"] and t_cur.ads_start_level and t_cur.sim_time_us > 1_650_000:
                avdd_dropped["done"] = True
                avdd_dropped["inject_us"] = int(t_cur.sim_time_us)
                cli_obj.lib.sim_set_avdd_3v0(False)
            elif avdd_dropped["done"] and not avdd_dropped["snapped"] and t_cur.sim_time_us >= avdd_dropped["inject_us"] + 6_000:
                avdd_dropped["snapped"] = True
                sb = (ctypes.c_uint8 * 512)()
                sn = cli_obj.lib.sim_ble_read_char(4, sb, 512)
                avdd_dropped["mid_fault"] = decode_status(bytes(sb[:sn]))["fault"]
                avdd_dropped["mid_ana_en"] = get_tel(cli_obj.lib).ana_en_level

        avdd_err = None
        async with SilBleClient(lib_bench, step_hook=_drop_avdd_hook) as cli:
            try:
                await capture_c08b(
                    cli, tmp / "nc2e_avdd_drop", seconds=0.8, mode="test",
                    allow_real=True, expected=bid, poll_seconds=0.02,
                )
            except RuntimeError as e:
                avdd_err = str(e)
            tel_avdd = get_tel(lib_bench)
        assert avdd_dropped["mid_fault"] == 3 and avdd_dropped["mid_ana_en"] is False, avdd_dropped
        assert avdd_err is not None and "fault=3" in avdd_err, avdd_err
        assert tel_avdd.ana_en_level is False
        cases_out.append({
            "id": "NC-2e",
            "title": "反例：2CH 采集中途 3.0V AVDD 欠压跌落 -> L432 PA4 实时监测立即置 FAULT_INTERLOCK(3) 并断 ANA_EN，主机捕获 fault=3",
            "pass": True,
            "expected_red_caught": True,
            "fault": avdd_dropped["mid_fault"],
            "host_error": avdd_err,
            "ana_en_after": tel_avdd.ana_en_level,
        })

        # NC-2f: 采集中途 BLE 物理断链 -> nRF 自动下发 STOP 切断 L432 ANA_EN，主机严禁跨连接拼接
        boot_board(lib_bench, subboard_kind=SIM_SUBBOARD_AFE30P_16CH)
        bid = read_build_id(lib_bench)
        disc_triggered = {"done": False}

        def _ble_disc_hook(cli_obj: SilBleClient):
            t_cur = get_tel(cli_obj.lib)
            if not disc_triggered["done"] and t_cur.ads_start_level and t_cur.sim_time_us > 1_650_000:
                disc_triggered["done"] = True
                cli_obj.disconnect_now()

        disc_err = None
        async with SilBleClient(lib_bench, step_hook=_ble_disc_hook) as cli:
            try:
                await capture_c08b(
                    cli, tmp / "nc2f_ble_disc", seconds=0.8, mode="test",
                    allow_real=True, expected=bid, poll_seconds=0.02,
                )
            except RuntimeError as e:
                disc_err = str(e)
        lib_bench.sim_step_us(60_000)
        tel_disc = get_tel(lib_bench)
        assert disc_err is not None and "严禁跨连接拼接" in disc_err
        assert tel_disc.ana_en_level is False and tel_disc.ads_start_level is False
        cases_out.append({
            "id": "NC-2f",
            "title": "反例：采集中途 BLE 异常断连 -> nRF 自动触发 STOP 使 L432 切断 ANA_EN=0，主机拒绝跨连接拼接",
            "pass": True,
            "expected_red_caught": True,
            "ana_en_after_disconnect": tel_disc.ana_en_level,
            "host_caught_error": disc_err,
        })

        # P2-2K-16CH-IMU (Finding #4 已闭环修复): 64MHz PLL + 非阻塞硬件 I2C1 下 16CH@2000SPS + 104Hz IMU 零漏采 & DSP-F03 Q30 精准陷波
        boot_board(
            lib_bench,
            subboard_kind=SIM_SUBBOARD_AFE30P_16CH,
            imu_present=True,
            wave_mode=SIM_WAVE_TONE_SWEEP,
            tone_amp_uv=250.0,
            mains_50hz_cm_uv=400.0,
            crosstalk_ratio=0.0,
        )
        bid = read_build_id(lib_bench)
        async with SilBleClient(lib_bench) as cli:
            await cli.write_gatt_char(CONTROL, b"SYN1" + struct.pack("<HB", 2000, 16))
            lib_bench.sim_step_us(30_000)
            await cli.write_gatt_char(CONTROL, b"STOP")
            lib_bench.sim_step_us(40_000)
            cli.pump_notifications()
            p2k_dir = tmp / "p2_2k_16ch_imu_fixed"
            res_2k = await capture_c08b(
                cli, p2k_dir, seconds=2.4, mode="rld", with_imu=True,
                allow_real=True, expected=bid, poll_seconds=0.04,
            )
            tel_2k = get_tel(lib_bench)
        pkts_2k = [
            decode_16ch(bytes.fromhex(json.loads(ln)["packet_hex"]), json.loads(ln)["mtu"])
            for ln in (p2k_dir / "events.jsonl").read_text(encoding="utf-8").splitlines()
            if json.loads(ln) != {"disconnect": True}
        ]
        dt_span_s = (pkts_2k[-1].timestamp_us - pkts_2k[0].timestamp_us) * 1e-6
        n_span_frames = sum(len(p.frames) for p in pkts_2k[:-1])
        eff_fs_hz = n_span_frames / dt_span_s

        # 将 16CH@2000SPS 原始 24 位码送入 C99 DSP-F03 (fs=2000, notch=True, Q=30) 验证 50Hz 工频精准落入陷波谷底
        codes_2k = extract_16ch_raw_codes(p2k_dir)
        assert codes_2k.shape[0] >= 4700 and codes_2k.shape[1] == 16
        dsp_lo = DSP(dsp_lib, 2000, notch=True)
        dsp_hi = DSP(dsp_lib, 2000, notch=True)
        y_lo, rdy_lo = dsp_lo.process(np.ascontiguousarray(codes_2k[:, :8], dtype=np.int32))
        y_hi, rdy_hi = dsp_hi.process(np.ascontiguousarray(codes_2k[:, 8:], dtype=np.int32))
        assert np.array_equal(rdy_lo, rdy_hi) and (not rdy_lo[:2639].any()) and rdy_lo[2639:].all()
        y_2k_uv = np.hstack([y_lo, y_hi])[rdy_lo] * 400_000.0
        # 取收敛段最后 2000 点 (精确 1.000 s -> 1 Hz 分辨率，bin 50 = 50 Hz，ch4 = 100 Hz 通带激励零泄漏)
        assert y_2k_uv.shape[0] >= 2000, y_2k_uv.shape
        seg_2k = y_2k_uv[-2000:, 4]
        spec_2k = np.abs(np.fft.rfft(seg_2k)) * (2.0 / 2000.0)
        amp_50hz_after = float(spec_2k[50])
        amp_100hz_pass = float(spec_2k[100])
        tot_50hz_rej_db = 20.0 * math.log10(400.0 / max(amp_50hz_after, 1e-9))

        assert tel_2k.l432_hclk_hz == 64_000_000 and tel_2k.spi1_sclk_hz == 4_000_000 and tel_2k.spi3_sclk_hz == 8_000_000
        assert tel_2k.hazard_mask == HAZ_NONE
        assert res_2k["missing_samples"] == 0 and res_2k["imu_missing_samples"] == 0
        assert res_2k["imu_samples"] >= 220, f"expected ~249 IMU frames @104Hz, got {res_2k['imu_samples']}"
        assert 1999.5 <= eff_fs_hz <= 2000.5, f"expected 2000.00 Hz, got {eff_fs_hz:.3f} Hz"
        assert tot_50hz_rej_db >= 65.0, f"expected >=65 dB 50Hz rejection at 2kSPS, got {tot_50hz_rej_db:.2f} dB"
        assert 225.0 <= amp_100hz_pass <= 270.0, f"100Hz passband amp={amp_100hz_pass:.2f} uV"
        cases_out.append({
            "id": "P2-2K-16CH-IMU",
            "title": "正例（Finding #4 已修复）：64MHz L432 + 非阻塞 I2C1 下 16CH@2000SPS + 104Hz IMU 零漏采（2000.00 Hz），RLD+DSP-F03 Q30 50Hz 总抑制 >65 dB",
            "pass": True,
            "l432_hclk_hz": tel_2k.l432_hclk_hz,
            "measured_effective_fs_hz": round(eff_fs_hz, 3),
            "missing_samples": res_2k["missing_samples"],
            "imu_samples_in_2p4s": res_2k["imu_samples"],
            "rld_plus_dsp_2ksps_50hz_rejection_db": round(tot_50hz_rej_db, 2),
            "passband_100hz_amp_uv": round(amp_100hz_pass, 2),
        })

        # NC-2h (新增必败反例): 注入周期性 750µs CPU 停顿 (>500µs DRDY 周期)，证明真实 DRDY 漏采绝不静默掩盖，
        # 固件 ring_dropped 与包序号跳变 (主机 missing_samples) 100% 诚实对齐！
        boot_board(
            lib_bench,
            subboard_kind=SIM_SUBBOARD_AFE30P_16CH,
            imu_present=True,
            inject_periodic_stall_us=750,
        )
        bid = read_build_id(lib_bench)
        stall_snap = {"ring_dropped": 0, "produced": 0, "sent": 0}

        def _snap_stall_status_hook(cli_obj: SilBleClient):
            t_cur = get_tel(cli_obj.lib)
            if t_cur.ads_start_level and t_cur.sim_time_us > 1_950_000:
                sb = (ctypes.c_uint8 * 512)()
                sn = cli_obj.lib.sim_ble_read_char(4, sb, 512)
                st_s = decode_status(bytes(sb[:sn]))
                stall_snap["ring_dropped"] = st_s["ring_dropped"]
                stall_snap["produced"] = st_s["produced"]
                stall_snap["sent"] = st_s["sent_samples"]

        async with SilBleClient(lib_bench, step_hook=_snap_stall_status_hook) as cli:
            await cli.write_gatt_char(CONTROL, b"SYN1" + struct.pack("<HB", 2000, 16))
            lib_bench.sim_step_us(30_000)
            await cli.write_gatt_char(CONTROL, b"STOP")
            lib_bench.sim_step_us(40_000)
            cli.pump_notifications()
            nc2h_dir = tmp / "nc2h_cpu_stall_overrun"
            res_2h = await capture_c08b(
                cli, nc2h_dir, seconds=0.6, mode="test",
                allow_real=True, expected=bid, poll_seconds=0.04,
            )
        assert stall_snap["ring_dropped"] >= 15, stall_snap
        assert res_2h["missing_samples"] >= 15, res_2h
        assert abs(res_2h["missing_samples"] - stall_snap["ring_dropped"]) <= 4, (res_2h["missing_samples"], stall_snap)
        cases_out.append({
            "id": "NC-2h",
            "title": "反例：注入每 25ms 750µs CPU 停顿越界 -> L432 精确检出 DRDY 漏采跳号，STATUS.ring_dropped 与主机 missing_samples 诚实对齐",
            "pass": True,
            "expected_red_caught": True,
            "fw_ring_dropped_mid": stall_snap["ring_dropped"],
            "host_missing_samples": res_2h["missing_samples"],
            "valid_samples": res_2h["valid_samples"],
        })

        # P2-REG-ONLINE-16CH-2CH: 在线 RREG / WREG / CLRO 双核真实 SPI3+SPI1 全链路与 TST1/SHT1 增益标定闭环
        boot_board(lib_bench, subboard_kind=SIM_SUBBOARD_AFE30P_16CH, imu_present=True)
        bid = read_build_id(lib_bench)
        async with SilBleClient(lib_bench) as cli:
            r_id = await c08b_stream.reg_op_c08b(cli, "rreg", chip="both", addr=0x00, allow_real=True, expected=bid)
            assert r_id["last_reg"]["u1"] == 0x92 and r_id["last_reg"]["u2"] == 0x92 and r_id["reg_overrides"] == 0

            # 将 U1.CH1 与 U2.CH9 设为 PGA Gain=12 (0x60)，其余通道保持默认 Gain=6 (0x00)
            w_g12 = await c08b_stream.reg_op_c08b(cli, "wreg", chip="both", addr=0x05, val=0x60, allow_real=True, expected=bid)
            assert w_g12["last_reg"]["u1"] == 0x60 and w_g12["last_reg"]["u2"] == 0x60 and w_g12["reg_overrides"] == 2
            tel_after_w = get_tel(lib_bench)
            assert not tel_after_w.ana_en_level and tel_after_w.hazard_mask == HAZ_NONE

            # 紧接运行 TST1 1Hz 内部方波标定：CH1/CH9 因 Gain=12 码值翻倍（按标称 Gain=6 折算应为 ~4000 µVpp，绝不能丢 MUX=0x05 变 0！）
            reg_tst_dir = tmp / "p2_reg_tst1_gain12"
            await capture_c08b(cli, reg_tst_dir, seconds=1.15, mode="test", allow_real=True, expected=bid)
            rep_reg_tst = replay_c08b(reg_tst_dir, allow_real=True)
            ch1_pp = float(np.ptp(rep_reg_tst["uv"][:, 0]))
            ch2_pp = float(np.ptp(rep_reg_tst["uv"][:, 1]))
            ch9_pp = float(np.ptp(rep_reg_tst["uv"][:, 8]))
            ch10_pp = float(np.ptp(rep_reg_tst["uv"][:, 9]))
            assert 3900.0 <= ch1_pp <= 4120.0 and 3900.0 <= ch9_pp <= 4120.0, (
                f"WREG CH1SET=0x60 后 TST1 方波丢失或增益不对: ch1_pp={ch1_pp:.1f}, ch9_pp={ch9_pp:.1f}, ch2_pp={ch2_pp:.1f}"
            )
            assert 1950.0 <= ch2_pp <= 2060.0 and 1950.0 <= ch10_pp <= 2060.0

            # 紧接运行 SHT1 内部短接底噪标定（注入外部 500µV 正弦验证 CH1/CH9 仍保持内部短接 MUX=0x01，不被误切到外部电极！）
            reg_sht_dir = tmp / "p2_reg_sht1_gain12"
            await capture_c08b(cli, reg_sht_dir, seconds=0.4, mode="short", allow_real=True, expected=bid)
            rep_reg_sht = replay_c08b(reg_sht_dir, allow_real=True)
            ch1_sht_rms = float(np.std(rep_reg_sht["uv"][:, 0]))
            assert ch1_sht_rms < 10.0, f"WREG CH1SET=0x60 后 SHT1 被误切到外部电极，底噪暴涨至 {ch1_sht_rms:.2f} µVrms"

            # CLRO 一键清除会话覆盖，再次跑 TST1 恢复 2000 µVpp
            r_clr = await c08b_stream.reg_op_c08b(cli, "clro", expected=bid)
            assert r_clr["reg_overrides"] == 0
            reg_tst_clr_dir = tmp / "p2_reg_tst1_after_clro"
            await capture_c08b(cli, reg_tst_clr_dir, seconds=1.15, mode="test", allow_real=True, expected=bid)
            rep_clr_tst = replay_c08b(reg_tst_clr_dir, allow_real=True)
            ch1_pp_after_clr = float(np.ptp(rep_clr_tst["uv"][:, 0]))
            assert 1950.0 <= ch1_pp_after_clr <= 2060.0, ch1_pp_after_clr

        # 2CH ADS1292 在线 WREG RLD_SENS(0x06=0x23) 两步 150ms 预热与 CH1SET=0x60 验证
        boot_board(lib_bench, subboard_kind=SIM_SUBBOARD_ADS1292_2CH, strict_ads1292_por=True)
        bid2 = read_build_id(lib_bench)
        async with SilBleClient(lib_bench) as cli2:
            w2_rld = await c08b_stream.reg_op_c08b(cli2, "wreg", chip="u1", addr=0x06, val=0x23, allow_real=True, expected=bid2)
            assert w2_rld["afe"] == "ADS1292" and w2_rld["last_reg"]["u1"] == 0x23 and w2_rld["reg_overrides"] == 1
            assert get_tel(lib_bench).hazard_mask == HAZ_NONE

        cases_out.append({
            "id": "P2-REG-ONLINE-16CH-2CH",
            "title": "正例：16CH/2CH 在线 RREG/WREG/CLRO 经真实 SPI3+SPI1 两步预热闭环，且 WREG 改增益后 TST1/SHT1 保持内部校准多路器不失波",
            "pass": True,
            "ch1_gain12_tst_pp_uv_nominal": round(ch1_pp, 1),
            "ch2_gain6_tst_pp_uv_nominal": round(ch2_pp, 1),
            "ch1_gain12_sht_rms_uv": round(ch1_sht_rms, 2),
            "ch1_after_clro_pp_uv": round(ch1_pp_after_clr, 1),
        })

        # P2-LIVE-FS-SWITCH: 同连接在线 500 -> 1000 -> 2000 SPS 三档实时采样率切换核验
        boot_board(lib_bench, subboard_kind=SIM_SUBBOARD_AFE30P_16CH, imu_present=True)
        bid = read_build_id(lib_bench)
        fs_measured = {}
        async with SilBleClient(lib_bench) as cli:
            for target_fs in (500, 1000, 2000):
                d_fs = tmp / f"p2_live_fs_{target_fs}"
                r_fs = await capture_c08b(
                    cli, d_fs, seconds=0.45, mode="short",
                    allow_real=True, expected=bid, fs_hz=target_fs, with_imu=True,
                )
                assert r_fs["fs_Hz"] == target_fs and r_fs["missing_samples"] == 0
                ev_lines = [json.loads(x) for x in (d_fs / "events.jsonl").read_text().splitlines() if "packet_hex" in x]
                pkts = [decode_16ch(bytes.fromhex(e["packet_hex"]), e["mtu"]) for e in ev_lines]
                dt_s = (pkts[-1].timestamp_us - pkts[0].timestamp_us) / 1e6
                dn = pkts[-1].sequence - pkts[0].sequence
                eff = dn / dt_s
                assert abs(eff - target_fs) < 1.5, (target_fs, eff)
                fs_measured[str(target_fs)] = round(eff, 2)
        cases_out.append({
            "id": "P2-LIVE-FS-SWITCH",
            "title": "正例：同一 BLE 连接在线热切换 500 / 1000 / 2000 SPS，DRDY 实测采样率与 META 严格对齐零丢包",
            "pass": True,
            "measured_fs_hz": fs_measured,
        })

        # NC-2i: 在线 WREG 危险寄存器拦截（含 Pin60/62 短路位、GPIO 输出、CLK_EN=1 引脚 37 顶牛及 >2000SPS 超速）
        haz_caught = []
        for chip_s, addr_i, val_i, label in (
            ("u1", 0x03, 0xCC, "RLDREF_INT=1"),
            ("u1", 0x03, 0xD4, "RLD_MEAS=1"),
            ("u1", 0x03, 0xE0, "VREF_4V=1"),
            ("u2", 0x03, 0xC4, "U2_PD_RLD=1"),
            ("u1", 0x14, 0x0E, "GPIO1_OUT_SHORT_GND"),
            ("u1", 0x01, 0xA5, "CONFIG1_CLK_EN_PIN37_CONFLICT"),
            ("u1", 0x01, 0x82, "CONFIG1_8000SPS_OVERRUN"),
        ):
            # 冷启动 afe=NONE 下主机尚未识别子板，直接打穿到 L432 硬件安全掩码检验固件侧兜底拦截！
            boot_board(lib_bench, subboard_kind=SIM_SUBBOARD_AFE30P_16CH)
            bid = read_build_id(lib_bench)
            async with SilBleClient(lib_bench) as cli:
                try:
                    await c08b_stream.reg_op_c08b(cli, "wreg", chip=chip_s, addr=addr_i, val=val_i, allow_real=True, expected=bid)
                    raise AssertionError(f"固件未拦截危险 WREG: {label} (0x{addr_i:02X}=0x{val_i:02X})")
                except (RuntimeError, ValueError) as exc:
                    tel_h = get_tel(lib_bench)
                    assert tel_h.hazard_mask == HAZ_NONE and not tel_h.ana_en_level, (label, tel_h.hazard_mask)
                    haz_caught.append(f"{label}->{str(exc)[:40]}")
        cases_out.append({
            "id": "NC-2i",
            "title": "反例：冷启动直推 7 类危险 WREG（含 CLK_EN 顶牛晶振 X1 与 8kSPS 超速），L432 固件掩码 100% 拒收断电（hazard=0x0000）",
            "pass": True,
            "expected_red_caught": True,
            "caught": haz_caught,
        })

        # NC-2j: 在线 WREG 遭遇 SPI1 寄存器回读位翻转 -> 立即断电报 FAULT_READBACK(5) 且不污染会话覆盖表
        boot_board(lib_bench, subboard_kind=SIM_SUBBOARD_AFE30P_16CH)
        bid = read_build_id(lib_bench)
        async with SilBleClient(lib_bench) as cli:
            w_ok = await c08b_stream.reg_op_c08b(cli, "wreg", chip="u1", addr=0x06, val=0x50, allow_real=True, expected=bid)
            assert w_ok["reg_overrides"] == 1
            lib_bench.sim_set_readback_fault(True)
            try:
                await c08b_stream.reg_op_c08b(cli, "wreg", chip="u1", addr=0x05, val=0x60, allow_real=True, expected=bid)
                raise AssertionError("SPI1 回读位翻转未被 WREG 检出")
            except RuntimeError as exc:
                assert "5" in str(exc), exc
            lib_bench.sim_set_readback_fault(False)
            await cli.write_gatt_char(CONTROL, b"STOP")
            lib_bench.sim_step_us(40_000)
            # 确认失败的那条 WREG 未污染之前的合法 1 条覆盖项！
            r_verify = await c08b_stream.reg_op_c08b(cli, "rreg", chip="u1", addr=0x06, allow_real=True, expected=bid)
            assert r_verify["reg_overrides"] == 1 and r_verify["last_reg"]["u1"] == 0x50
        cases_out.append({
            "id": "NC-2j",
            "title": "反例：在线 WREG 注入 SPI1 回读位翻转 -> 固件立即断电报 FAULT_READBACK(5) 且保持原会话覆盖表不被污染",
            "pass": True,
            "expected_red_caught": True,
            "preserved_overrides": r_verify["reg_overrides"],
        })

    summary = {
        "suite": "Sim-2 (c08b-stream Dual-MCU + S140 GATT + c08b_stream.py + DSP-F03 Silicon-in-the-Loop)",
        "total_cases": len(cases_out),
        "passed_cases": sum(1 for c in cases_out if c["pass"]),
        "cases": cases_out,
    }
    out_path = SIM_DIR / "reports" / "results_sim2_stream.json"
    out_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"SIM2_ALL_PASS ({summary['passed_cases']}/{summary['total_cases']}) -> {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(async_main()))

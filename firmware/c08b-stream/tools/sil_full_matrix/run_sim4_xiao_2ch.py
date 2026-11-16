#!/usr/bin/env python3
"""Sim-4: Seeed XIAO nRF52840 + P44e + ADS1292 2CH 独立固件全硅在环测试（含直连 MTU 防撞与接收器联调）。"""
from __future__ import annotations

import asyncio
import ctypes
import json
import sys
import tempfile
import time
from pathlib import Path

import numpy as np

from sim_ctypes import BUILD_DIR, REPO_DIR, SIM_DIR

sys.path.insert(0, str(REPO_DIR / "host"))
import v12_ble  # noqa: E402
import v12_status  # noqa: E402


def load_x2(dylib_name: str) -> ctypes.CDLL:
    lib = ctypes.CDLL(str(BUILD_DIR / dylib_name), mode=ctypes.RTLD_LOCAL)
    lib.x2_init.argtypes = [ctypes.c_float, ctypes.c_bool]
    lib.x2_ble_connect.argtypes = [ctypes.c_bool]
    lib.x2_ble_disconnect.argtypes = []
    lib.x2_ble_subscribe.argtypes = [ctypes.c_uint8, ctypes.c_bool]
    lib.x2_ble_subscribe.restype = ctypes.c_int
    lib.x2_ble_write_ctrl.argtypes = [ctypes.POINTER(ctypes.c_uint8), ctypes.c_uint16]
    lib.x2_ble_write_ctrl.restype = ctypes.c_int
    lib.x2_ble_read_char.argtypes = [ctypes.c_uint8, ctypes.POINTER(ctypes.c_uint8), ctypes.c_int]
    lib.x2_ble_read_char.restype = ctypes.c_int
    lib.x2_ble_pop_notify.argtypes = [
        ctypes.POINTER(ctypes.c_uint8), ctypes.POINTER(ctypes.c_uint8),
        ctypes.c_int, ctypes.POINTER(ctypes.c_uint64),
    ]
    lib.x2_ble_pop_notify.restype = ctypes.c_int
    lib.x2_set_avdd.argtypes = [ctypes.c_float]
    lib.x2_set_vbus.argtypes = [ctypes.c_bool]
    lib.x2_inject_stall_us.argtypes = [ctypes.c_uint32]
    lib.x2_step_us.argtypes = [ctypes.c_uint64]
    lib.x2_get_telemetry.argtypes = [
        ctypes.POINTER(ctypes.c_uint32), ctypes.POINTER(ctypes.c_uint16),
        ctypes.POINTER(ctypes.c_uint32), ctypes.POINTER(ctypes.c_bool),
        ctypes.c_char_p,
    ]
    return lib


def get_x2_tel(lib: ctypes.CDLL) -> dict:
    haz, mtu, reqs, pwdn = ctypes.c_uint32(), ctypes.c_uint16(), ctypes.c_uint32(), ctypes.c_bool()
    name = ctypes.create_string_buffer(32)
    lib.x2_get_telemetry(ctypes.byref(haz), ctypes.byref(mtu), ctypes.byref(reqs), ctypes.byref(pwdn), name)
    return {
        "hazard_mask": haz.value,
        "mtu": mtu.value,
        "periph_mtu_reqs": reqs.value,
        "pwdn_high": pwdn.value,
        "dev_name": name.value.decode("utf-8", errors="ignore"),
    }


class X2BleClient:
    """将 libsim4_xiao_2ch 适配为 host/v12_ble.py:capture 标准 BleakClient 接口。"""

    class _Svc:
        class _Char:
            def __init__(self, u): self.uuid = u
        characteristics = [
            _Char(v12_ble.DATA), _Char(v12_ble.META),
            _Char(v12_ble.STATUS), _Char(v12_ble.CONTROL),
        ]

    class _Svcs:
        def get_service(self, u):
            return X2BleClient._Svc() if str(u).lower() == v12_ble.SERVICE else None

    def __init__(self, lib: ctypes.CDLL, central_initiates_mtu: bool = True, mid_hook=None):
        self.lib = lib
        self.central_initiates_mtu = central_initiates_mtu
        self.services = self._Svcs()
        self.is_connected = False
        self._cb = None
        self._mid_hook = mid_hook
        self._started = False
        self._last_wall = None

    @property
    def mtu_size(self) -> int:
        return get_x2_tel(self.lib)["mtu"]

    async def __aenter__(self):
        self.lib.x2_ble_connect(self.central_initiates_mtu)
        self.is_connected = True
        self.lib.x2_step_us(5000)
        return self

    async def __aexit__(self, *args):
        if self.is_connected:
            self.lib.x2_ble_disconnect()
            self.is_connected = False
            self.lib.x2_step_us(2000)

    def _pump(self):
        sfx = ctypes.c_uint8()
        pkt = (ctypes.c_uint8 * 256)()
        ts = ctypes.c_uint64()
        while True:
            n = self.lib.x2_ble_pop_notify(ctypes.byref(sfx), pkt, 256, ctypes.byref(ts))
            if n <= 0:
                break
            if self._cb is not None:
                self._cb(12, bytearray(pkt[:n]))

    async def start_notify(self, uuid, callback):
        assert str(uuid).lower() == v12_ble.DATA
        self._cb = callback
        self.lib.x2_ble_subscribe(2, True)

    async def stop_notify(self, uuid):
        self._cb = None
        self.lib.x2_ble_subscribe(2, False)

    async def read_gatt_char(self, uuid):
        u = str(uuid).lower()
        sfx = 3 if u == v12_ble.META else 4
        # 按真实挂钟流逝 1:1 推进虚拟硬件时间，消除 OS 调度抖动对采样点数的影响
        now_w = time.monotonic()
        dt_us = 52_000 if self._last_wall is None else max(52_000, min(250_000, int((now_w - self._last_wall) * 1e6)))
        self._last_wall = now_w
        self.lib.x2_step_us(dt_us)
        if self._mid_hook is not None and self._started:
            self._mid_hook(self)
        self._pump()
        buf = (ctypes.c_uint8 * 512)()
        n = self.lib.x2_ble_read_char(sfx, buf, 512)
        return bytearray(buf[: max(0, n)])

    async def write_gatt_char(self, uuid, data, response=True):
        assert str(uuid).lower() == v12_ble.CONTROL
        raw = bytes(data)
        arr = (ctypes.c_uint8 * len(raw))(*raw)
        self.lib.x2_ble_write_ctrl(arr, len(raw))
        # ADS1292 start() 需 50ms 稳压检测 + 1000ms POR + 150ms VREF 预热 ≈ 1.21s
        step = 1_300_000 if raw != b"STOP" else 20_000
        self.lib.x2_step_us(step)
        self._pump()
        self._started = (raw != b"STOP")
        self._last_wall = time.monotonic()



def decode_x2_archive_uv(cap_dir: Path) -> np.ndarray:
    codec = v12_ble.load_codec()
    uv_per_count = (2420.0 * 1e3) / (6.0 * (2 ** 23 - 1))
    rows = []
    for ln in (cap_dir / "events.jsonl").read_text(encoding="utf-8").splitlines():
        ev = json.loads(ln)
        if "packet_hex" not in ev:
            continue
        pkt = codec.decode(bytes.fromhex(ev["packet_hex"]), ev["mtu"])
        for fr in pkt.frames:
            _st, ch8 = codec.decode_frame(fr)
            rows.append([c * uv_per_count for c in ch8])
    return np.asarray(rows, dtype=np.float64)


async def async_main() -> int:
    lib_loc = load_x2("libsim4_xiao_2ch_locked.dylib")
    lib_ben = load_x2("libsim4_xiao_2ch_bench.dylib")

    cases_out = []
    with tempfile.TemporaryDirectory(prefix="sil_sim4_") as tmp_s:
        tmp = Path(tmp_s)

        # Case 1 (L4-LOCKED-DEFAULT): 默认 MAKO_BENCH_MEASURED=0 锁定镜像拒绝真采，保持 D4(PWDN)=LOW 且零电气违规
        lib_loc.x2_init(3.00, False)
        t0 = get_x2_tel(lib_loc)
        assert t0["dev_name"] == "MAKO-V12-1292-2K" and t0["hazard_mask"] == 0 and not t0["pwdn_high"]
        async with X2BleClient(lib_loc, central_initiates_mtu=True) as cli:
            meta_raw = await cli.read_gatt_char(v12_ble.META)
            meta = json.loads(meta_raw.decode("utf-8"))
            assert not meta["bench_measured"] and meta["active_channels"] == 2
            await cli.start_notify(v12_ble.DATA, lambda *_: None)
            await cli.write_gatt_char(v12_ble.CONTROL, b"TST1")
            st = v12_status.decode_status(bytes(await cli.read_gatt_char(v12_ble.STATUS)))
            assert st["fault"] == 1 and not st["active"] and not get_x2_tel(lib_loc)["pwdn_high"]
        cases_out.append({
            "id": "L4-LOCKED-DEFAULT",
            "title": "默认锁定镜像（MAKO_BENCH_MEASURED=0）：拒收 TST1 报 Fault::Locked(1)，D4(PWDN)=LOW 零漏电（hazard=0x00）",
            "pass": True,
            "fault": st["fault"],
        })

        # Case 2 (P4-DIRECT-BLE-MTU247-TST1):
        # 中心（Mac/iPhone）连上时已主动协商 MTU=247，随后跑 2000SPS TST1 方波采集与 v12_ble.replay 回放！
        # 修复前（Bug #8）：main.cpp 无条件再调 sd_ble_gattc_exchange_mtu_request(247) 撞出 S140 INVALID_STATE(8) 0 包失败！
        lib_ben.x2_init(3.00, False)
        bid = "a129261116000001"
        async with X2BleClient(lib_ben, central_initiates_mtu=True) as cli:
            d_tst = tmp / "x2_direct_tst1"
            res_tst = await v12_ble.capture(cli, d_tst, 1.15, "test", True, bid, poll_seconds=0.05)
        tel_tst = get_x2_tel(lib_ben)
        assert tel_tst["hazard_mask"] == 0 and tel_tst["periph_mtu_reqs"] == 0, tel_tst
        assert res_tst["missing_samples"] == 0 and res_tst["valid_samples"] >= 2000
        uv_tst = decode_x2_archive_uv(d_tst)
        ch1_pp = float(np.ptp(uv_tst[:, 0]))
        ch2_pp = float(np.ptp(uv_tst[:, 1]))
        ch3_max = float(np.max(np.abs(uv_tst[:, 2:])))
        assert 2000.0 <= ch1_pp <= 2035.0 and 2000.0 <= ch2_pp <= 2035.0 and ch3_max == 0.0
        cases_out.append({
            "id": "P4-DIRECT-BLE-MTU247-TST1",
            "title": "正例（Bug #8 已修复）：中心已协商 MTU=247 时外设跳过重复 MTU 请求（periph_mtu_reqs=0），2000SPS TST1 方波零丢包",
            "pass": True,
            "valid_samples": res_tst["valid_samples"],
            "ch1_pp_uv": round(ch1_pp, 1),
            "periph_mtu_reqs": tel_tst["periph_mtu_reqs"],
        })

        # Case 3 (P4-DONGLE-PEER-MTU-EXR1-RLD):
        # 接收器 dongle_1292_2k 模式（DONGLE_PEER_MTU，连接时保持 MTU=23），由外设主动协商升至 MTU=247 并完成 EXR1 两步 150ms RLD 预热！
        lib_ben.x2_init(3.00, False)
        async with X2BleClient(lib_ben, central_initiates_mtu=False) as cli:
            assert cli.mtu_size == 23
            d_exr = tmp / "x2_dongle_exr1"
            res_exr = await v12_ble.capture(cli, d_exr, 0.5, "rld", True, bid, poll_seconds=0.05)
            assert cli.mtu_size == 247
        tel_exr = get_x2_tel(lib_ben)
        assert tel_exr["hazard_mask"] == 0 and tel_exr["periph_mtu_reqs"] == 1
        uv_exr = decode_x2_archive_uv(d_exr)
        assert res_exr["missing_samples"] == 0 and uv_exr.shape[0] == res_exr["valid_samples"]
        cases_out.append({
            "id": "P4-DONGLE-PEER-MTU-EXR1-RLD",
            "title": "正例：配对 dongle_1292_2k(MTU=23) 时外设主动升至 MTU=247，EXR1 两步 150ms RLD 预热闭环（hazard=0x00）",
            "pass": True,
            "valid_samples": res_exr["valid_samples"],
            "periph_mtu_reqs": tel_exr["periph_mtu_reqs"],
        })

        # Case 4 (P4-SHT1-NOISE): SHT1 内部短接底噪模式 + 停止后 D4(PWDN)=LOW 安全态核验
        lib_ben.x2_init(3.00, False)
        async with X2BleClient(lib_ben, central_initiates_mtu=True) as cli:
            d_sht = tmp / "x2_sht1"
            res_sht = await v12_ble.capture(cli, d_sht, 0.35, "short", True, bid, poll_seconds=0.05)
        assert not get_x2_tel(lib_ben)["pwdn_high"] and get_x2_tel(lib_ben)["hazard_mask"] == 0
        uv_sht = decode_x2_archive_uv(d_sht)
        assert float(np.max(np.abs(uv_sht[:, :2]))) < 5.0
        cases_out.append({
            "id": "P4-SHT1-NOISE",
            "title": "正例：SHT1 内部短接底噪 < 5 µV 且 STOP 后 D4(PWDN) 立即归零断电",
            "pass": True,
            "valid_samples": res_sht["valid_samples"],
        })

        # Case 5 (NC-4a-VBUS-HOTPLUG): 采集中途插入 USB 5V (USBREGSTATUS=1 + Q1 硬拉低) -> 立即停机报 Fault::UsbInterlock(10)
        lib_ben.x2_init(3.00, False)
        tripped_vbus = {"done": False}

        def _inject_vbus(c: X2BleClient):
            if not tripped_vbus["done"]:
                tripped_vbus["done"] = True
                c.lib.x2_set_vbus(True)
                c.lib.x2_step_us(5000)

        async with X2BleClient(lib_ben, central_initiates_mtu=True, mid_hook=_inject_vbus) as cli:
            try:
                await v12_ble.capture(cli, tmp / "x2_nc_vbus", 0.5, "test", True, bid, poll_seconds=0.04)
                raise AssertionError("XIAO-2CH VBUS 插入未被拦截")
            except RuntimeError as exc:
                assert "10" in str(exc) and "UsbInterlock" in str(exc), exc
        assert not get_x2_tel(lib_ben)["pwdn_high"]
        cases_out.append({
            "id": "NC-4a",
            "title": "反例：采集中途插入 USB VBUS -> USBREGSTATUS 双互锁立即拉低 D4 停机报 Fault::UsbInterlock(10)",
            "pass": True,
            "expected_red_caught": True,
        })

        # Case 6 (NC-4b-AVDD-DROOP): 运行期每 50ms SAADC(TACQ=20µs) 复检 D5 AVDD_SENSE 跌落至 2.40V (<2.75V) -> 报 Fault::Rails(3)
        lib_ben.x2_init(3.00, False)
        tripped_rail = {"done": False}

        def _inject_droop(c: X2BleClient):
            if not tripped_rail["done"]:
                tripped_rail["done"] = True
                c.lib.x2_set_avdd(2.40)
                c.lib.x2_step_us(65_000)

        async with X2BleClient(lib_ben, central_initiates_mtu=True, mid_hook=_inject_droop) as cli:
            try:
                await v12_ble.capture(cli, tmp / "x2_nc_rail", 0.5, "test", True, bid, poll_seconds=0.04)
                raise AssertionError("AVDD 跌落至 2.40V 未被 50ms SAADC 巡检拦截")
            except RuntimeError as exc:
                assert "3" in str(exc) and "Rails" in str(exc), exc
        assert not get_x2_tel(lib_ben)["pwdn_high"] and get_x2_tel(lib_ben)["hazard_mask"] == 0
        cases_out.append({
            "id": "NC-4b",
            "title": "反例：采集中 D5 AVDD 3.0V 轨跌落至 2.40V -> 50ms SAADC(TACQ=20µs) 巡检立即停机报 Fault::Rails(3)",
            "pass": True,
            "expected_red_caught": True,
        })

        # Case 7 (NC-4c-DRDY-OVERRUN): 注入 1500µs CPU 中断阻塞 (>2.6 采样周期) -> uncertain_edge 立即刷新 status_chr 并报 Fault::Overrun(7)
        lib_ben.x2_init(3.00, False)
        tripped_ovr = {"done": False}

        def _inject_ovr(c: X2BleClient):
            if not tripped_ovr["done"]:
                tripped_ovr["done"] = True
                c.lib.x2_inject_stall_us(1500)
                c.lib.x2_step_us(5000)

        async with X2BleClient(lib_ben, central_initiates_mtu=True, mid_hook=_inject_ovr) as cli:
            try:
                await v12_ble.capture(cli, tmp / "x2_nc_ovr", 0.5, "test", True, bid, poll_seconds=0.04)
                raise AssertionError("DRDY 跨周期漏沿未被 uncertain_edge 拦截")
            except RuntimeError as exc:
                assert "设备故障码 7" in str(exc), exc
        ovr_summary = json.loads((tmp / "x2_nc_ovr" / "summary.json").read_text(encoding="utf-8"))
        assert ovr_summary["adc_final_status"]["fault"] == 7, ovr_summary
        assert not get_x2_tel(lib_ben)["pwdn_high"]
        cases_out.append({
            "id": "NC-4c",
            "title": "反例（Bug #9 已修复）：注入 1500µs CPU 停顿致 DRDY 漏沿 -> uncertain_edge 立即刷新 GATT 状态且 STOP 保留 Fault::Overrun(7)",
            "pass": True,
            "expected_red_caught": True,
        })

        # Case 8 (NC-4d-STARTUP-VBUS-BLOCK): 上电启动阶段已插着 USB VBUS -> ads.start() 拒绝拉高 D4(PWDN) 并报 UsbInterlock(10)
        lib_ben.x2_init(3.00, True)
        async with X2BleClient(lib_ben, central_initiates_mtu=True) as cli:
            await cli.start_notify(v12_ble.DATA, lambda *_: None)
            await cli.write_gatt_char(v12_ble.CONTROL, b"TST1")
            st_v = v12_status.decode_status(bytes(await cli.read_gatt_char(v12_ble.STATUS)))
            assert st_v["fault"] == 10 and not st_v["active"] and not get_x2_tel(lib_ben)["pwdn_high"]
        cases_out.append({
            "id": "NC-4d",
            "title": "反例：插着 USB VBUS 请求启动 TST1 -> 启动前即拦截报 Fault::UsbInterlock(10)，D4 全程保持低电平",
            "pass": True,
            "expected_red_caught": True,
        })

    summary = {
        "suite": "Sim-4 (Seeed XIAO nRF52840 + P44e + ADS1292 2CH Standalone Firmware Silicon-in-the-Loop)",
        "total_cases": len(cases_out),
        "passed_cases": sum(1 for c in cases_out if c["pass"]),
        "cases": cases_out,
    }
    out_path = SIM_DIR / "reports" / "results_sim4_xiao_2ch.json"
    out_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"SIM4_ALL_PASS ({summary['passed_cases']}/{summary['total_cases']}) -> {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(async_main()))

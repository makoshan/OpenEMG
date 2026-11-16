#!/usr/bin/env python3
"""Sim-3: USB BLE 无线接收器全硅在环测试（XIAO nRF52840 xiao-central + ESP32-C6 c6-central 四级硬件全栈闭环）。"""
from __future__ import annotations

import asyncio
import ctypes
import json
import sys
import tempfile
import threading
import time
from pathlib import Path

from sim_ctypes import (
    BUILD_DIR,
    HAZ_NONE,
    REPO_DIR,
    SIM_DIR,
    SIM_MAINBOARD_MCU_U9_V001,
    SIM_SUBBOARD_AFE30P_16CH,
    SimConfig,
    get_tel,
    load_twin,
)

sys.path.insert(0, str(REPO_DIR / "host"))
import c08b_stream  # noqa: E402
import v12_dongle  # noqa: E402

WRITE_CB = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.POINTER(ctypes.c_uint8), ctypes.c_uint16)
READ_CB  = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_uint8, ctypes.POINTER(ctypes.c_uint8), ctypes.c_uint16)
SUB_CB   = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_uint8, ctypes.c_bool)
MTU_CB   = ctypes.CFUNCTYPE(None, ctypes.c_uint16)


def load_xiao_dongle(dylib_name: str) -> ctypes.CDLL:
    lib = ctypes.CDLL(str(BUILD_DIR / dylib_name), mode=ctypes.RTLD_LOCAL)
    lib.xd_init.argtypes = [ctypes.c_uint32, ctypes.c_bool]
    lib.xd_set_peer_callbacks.argtypes = [WRITE_CB, READ_CB, SUB_CB, MTU_CB]
    lib.xd_feed_adv.argtypes = [ctypes.c_char_p, ctypes.c_bool]
    lib.xd_feed_notify.argtypes = [ctypes.c_uint8, ctypes.POINTER(ctypes.c_uint8), ctypes.c_uint16]
    lib.xd_peer_set_mtu.argtypes = [ctypes.c_uint16]
    lib.xd_peer_disconnect.argtypes = [ctypes.c_uint8]
    lib.xd_usb_host_send.argtypes = [ctypes.POINTER(ctypes.c_uint8), ctypes.c_int]
    lib.xd_usb_host_recv.argtypes = [ctypes.POINTER(ctypes.c_uint8), ctypes.c_int]
    lib.xd_usb_host_recv.restype = ctypes.c_int
    lib.xd_usb_tx_fifo_used.argtypes = []
    lib.xd_usb_tx_fifo_used.restype = ctypes.c_int
    lib.xd_step_loop.argtypes = [ctypes.c_uint32]
    lib.xd_now_us.argtypes = []
    lib.xd_now_us.restype = ctypes.c_uint64
    lib.xd_seed_ring_cursor.argtypes = [ctypes.c_uint32]
    lib.xd_seed_ring_cursor.restype = None
    lib.xd_config_usb_host_sim.argtypes = [ctypes.c_bool, ctypes.c_uint32, ctypes.c_uint64, ctypes.c_uint64]
    lib.xd_config_usb_host_sim.restype = None
    lib.xd_pop_auto_captured.argtypes = [ctypes.POINTER(ctypes.c_uint8), ctypes.c_int]
    lib.xd_pop_auto_captured.restype = ctypes.c_int
    lib.xd_get_stats.argtypes = [
        ctypes.POINTER(ctypes.c_uint32), ctypes.POINTER(ctypes.c_uint32),
        ctypes.POINTER(ctypes.c_uint32), ctypes.POINTER(ctypes.c_uint32),
        ctypes.POINTER(ctypes.c_uint32), ctypes.POINTER(ctypes.c_bool),
        ctypes.POINTER(ctypes.c_bool),
    ]
    return lib


def load_c6_dongle(dylib_name: str) -> ctypes.CDLL:
    lib = ctypes.CDLL(str(BUILD_DIR / dylib_name), mode=ctypes.RTLD_LOCAL)
    lib.c6_init.argtypes = [ctypes.c_uint32, ctypes.c_bool, ctypes.c_uint16]
    lib.c6_set_peer_callbacks.argtypes = [WRITE_CB, READ_CB, SUB_CB, MTU_CB]
    lib.c6_feed_adv.argtypes = [ctypes.c_char_p]
    lib.c6_feed_notify.argtypes = [ctypes.c_uint8, ctypes.POINTER(ctypes.c_uint8), ctypes.c_uint16]
    lib.c6_peer_disconnect.argtypes = [ctypes.c_uint8]
    lib.c6_usb_host_send.argtypes = [ctypes.POINTER(ctypes.c_uint8), ctypes.c_int]
    lib.c6_usb_host_recv.argtypes = [ctypes.POINTER(ctypes.c_uint8), ctypes.c_int]
    lib.c6_usb_host_recv.restype = ctypes.c_int
    lib.c6_step_io.argtypes = [ctypes.c_uint32]
    lib.c6_get_stats.argtypes = [
        ctypes.POINTER(ctypes.c_uint32), ctypes.POINTER(ctypes.c_uint32),
        ctypes.POINTER(ctypes.c_uint32), ctypes.POINTER(ctypes.c_uint32),
        ctypes.POINTER(ctypes.c_bool),
    ]
    return lib


class SingleThreadBoardExecutor:
    """macOS arm64 PAC 要求同一组协程上下文必须在固定单一 OS 线程切换；所有板级调用统一投递到此线程执行。"""
    def __init__(self):
        import queue
        self._q = queue.Queue()
        self._t = threading.Thread(target=self._loop, daemon=True)
        self._t.start()

    def _loop(self):
        while True:
            fn, ev, box = self._q.get()
            if fn is None:
                return
            try:
                box[0] = fn()
            except BaseException as exc:
                box[1] = exc
            finally:
                ev.set()

    def call(self, fn):
        if threading.current_thread() is self._t:
            return fn()
        ev = threading.Event()
        box = [None, None]
        self._q.put((fn, ev, box))
        ev.wait()
        if box[1] is not None:
            raise box[1]
        return box[0]


SIM_EXEC = SingleThreadBoardExecutor()


class SiliconDongleSerialBridge:
    """把真实编译的 xiao-central / c6-central 动态库与双核 C08B 孪生体连接成线程安全 pyserial 对象。"""

    def __init__(self, kind: str, dongle_lib: ctypes.CDLL, board_lib: ctypes.CDLL,
                 usb_tx_cap: int = 256, usb_sof_drain_bytes: int = 64, read_frag: int = 244):
        self.kind = kind  # 'xiao' or 'c6'
        self.dl = dongle_lib
        self.bl = board_lib
        self.lock = threading.RLock()
        self.dtr = False
        self.rts = False
        self.closed = False
        self.host_rx = bytearray()
        self.usb_sof_drain_bytes = usb_sof_drain_bytes
        self.peer_connected = False
        self._stream_wall_t0 = None
        self._stream_sim_t0 = None

        @WRITE_CB
        def _wcb(ptr, ln):
            raw = bytes(ptr[:ln])
            arr = (ctypes.c_uint8 * ln)(*raw)
            rc = self.bl.sim_ble_write_ctrl(arr, ln)
            self.bl.sim_step_us(2000)
            self._pump_air_notifications_locked()
            return rc

        @READ_CB
        def _rcb(suffix, out_ptr, max_len):
            self.bl.sim_step_us(500)
            buf = (ctypes.c_uint8 * max_len)()
            got = self.bl.sim_ble_read_char(suffix, buf, max_len)
            if got > 0:
                ctypes.memmove(out_ptr, buf, got)
            return got

        @SUB_CB
        def _scb(suffix, en):
            return self.bl.sim_ble_subscribe(suffix, en)

        @MTU_CB
        def _mcb(mtu):
            pass

        self._cbs = (_wcb, _rcb, _scb, _mcb)
        def _init_all():
            with self.lock:
                if self.kind == "xiao":
                    self.dl.xd_set_peer_callbacks(*self._cbs)
                    self.dl.xd_init(usb_tx_cap, True)
                else:
                    self.dl.c6_set_peer_callbacks(*self._cbs)
                    self.dl.c6_init(usb_tx_cap, True, read_frag)
                self._connect_air_locked()
        SIM_EXEC.call(_init_all)

    def _connect_air_locked(self):
        self.bl.sim_ble_connect(247)
        self.peer_connected = True
        if self.kind == "xiao":
            self.dl.xd_feed_adv(b"YUANLI-C08B", True)
            for _ in range(5):
                self.dl.xd_step_loop(550_000)
                self._drain_usb_sof_locked()
        else:
            self.dl.c6_feed_adv(b"YUANLI-C08B")
            self.dl.c6_step_io(1_100_000)
            self._drain_usb_sof_locked()

    def _pump_air_notifications_locked(self):
        sfx = ctypes.c_uint8()
        pkt = (ctypes.c_uint8 * 256)()
        ts = ctypes.c_uint64()
        while True:
            n = self.bl.sim_ble_pop_notify(ctypes.byref(sfx), pkt, 256, ctypes.byref(ts))
            if n <= 0:
                break
            if self.kind == "xiao":
                self.dl.xd_feed_notify(sfx.value, pkt, n)
            else:
                self.dl.c6_feed_notify(sfx.value, pkt, n)

    def _drain_usb_sof_locked(self):
        tmp = (ctypes.c_uint8 * self.usb_sof_drain_bytes)()
        if self.kind == "xiao":
            n = self.dl.xd_usb_host_recv(tmp, self.usb_sof_drain_bytes)
        else:
            n = self.dl.c6_usb_host_recv(tmp, self.usb_sof_drain_bytes)
        if n > 0:
            self.host_rx.extend(bytes(tmp[:n]))

    def _tick_world_locked(self, step_us: int = 4000):
        # 1) 推进双核手环固件，产生 BLE HVX 通知送入接收器环形缓冲
        self.bl.sim_step_us(step_us)
        self._pump_air_notifications_locked()
        # 2) 接收器主循环先把环形缓冲灌入 256B TinyUSB TX FIFO（高负载下必停在半帧边界！）
        #    并紧接处理刚收到的 USB 命令（如 'R' 读 STATUS）与 1Hz 链路帧！
        if self.kind == "xiao":
            self.dl.xd_step_loop(step_us)
        else:
            self.dl.c6_step_io(step_us)
        # 3) USB 主机按 SOF 从 256B TinyUSB TX FIFO 取走字节，腾出空间再跑一拍 drain
        for _ in range(8):
            self._drain_usb_sof_locked()
            if self.kind == "xiao":
                self.dl.xd_step_loop(100)
            else:
                self.dl.c6_step_io(100)
        self._drain_usb_sof_locked()

    def write(self, b: bytes):
        return SIM_EXEC.call(lambda: self._write_impl(b))

    def _write_impl(self, b: bytes):
        with self.lock:
            is_disc = len(b) >= 4 and b[0] == 0xA5 and b[1] == ord("D")
            arr = (ctypes.c_uint8 * len(b))(*b)
            if self.kind == "xiao":
                self.dl.xd_usb_host_send(arr, len(b))
            else:
                self.dl.c6_usb_host_send(arr, len(b))
            self._tick_world_locked(4000)
            if is_disc:
                self.bl.sim_ble_disconnect()
                self.bl.sim_step_us(5000)
                self._connect_air_locked()
            return len(b)

    def read(self, n: int) -> bytes:
        sleep_s = SIM_EXEC.call(self._step_read_impl)
        if sleep_s > 0:
            time.sleep(sleep_s)
        if not self.host_rx:
            time.sleep(0.0005)
            return b""
        with self.lock:
            out = bytes(self.host_rx[:n])
            del self.host_rx[:n]
            return out

    def _step_read_impl(self) -> float:
        sleep_s = 0.0
        with self.lock:
            if self.closed:
                raise OSError("closed")
            if not self.host_rx:
                tel = get_tel(self.bl)
                if not tel.ads_start_level:
                    self._stream_wall_t0 = None
                    self._tick_world_locked(10000 if tel.ana_en_level else 2000)
                else:
                    now_w = time.perf_counter()
                    if self._stream_wall_t0 is None:
                        self._stream_wall_t0 = now_w
                        self._stream_sim_t0 = tel.sim_time_us
                    target_sim = self._stream_sim_t0 + int((now_w - self._stream_wall_t0) * 1_000_000)
                    lag = target_sim - int(tel.sim_time_us)
                    if lag >= 1000:
                        self._tick_world_locked(min(lag, 12000))
                    else:
                        sleep_s = 0.0015
        return sleep_s

    def inject_air_flap_reconnect(self):
        return SIM_EXEC.call(self._inject_flap_impl)

    def _inject_flap_impl(self):
        with self.lock:
            if self.kind == "xiao":
                self.dl.xd_peer_disconnect(0x08)
            else:
                self.dl.c6_peer_disconnect(0x08)
            self.bl.sim_ble_disconnect()
            self.bl.sim_step_us(2000)
            self._connect_air_locked()

    def close(self):
        self.closed = True
        SIM_EXEC.call(lambda: None)
        time.sleep(0.01)
        SIM_EXEC.call(lambda: None)


def _boot_c08b_bench_impl(lib_board: ctypes.CDLL):
    cfg = SimConfig()
    lib_board.sim_default_config(ctypes.byref(cfg))
    cfg.mainboard_rev = SIM_MAINBOARD_MCU_U9_V001
    cfg.subboard_kind = SIM_SUBBOARD_AFE30P_16CH
    cfg.imu_present = True
    cfg.vbus_present = False
    lib_board.sim_init(ctypes.byref(cfg))
    lib_board.sim_step_us(65_000)
    mbuf = (ctypes.c_uint8 * 512)()
    n = lib_board.sim_ble_read_char(3, mbuf, 512)
    return json.loads(bytes(mbuf[:n]).decode("utf-8"))["build_id"]


def boot_c08b_bench(lib_board: ctypes.CDLL):
    return SIM_EXEC.call(lambda: _boot_c08b_bench_impl(lib_board))


async def async_main() -> int:
    lib_board = load_twin("libsim2_stream_bench.dylib")
    lib_xd = load_xiao_dongle("libsim3_xiao_dongle_c08b.dylib")
    lib_c6 = load_c6_dongle("libsim3_c6_dongle_c08b.dylib")
    lib_c6_r01 = load_c6_dongle("libsim3_c6_dongle_r01.dylib")

    cases_out = []
    with tempfile.TemporaryDirectory(prefix="sil_sim3_") as tmp_s:
        tmp = Path(tmp_s)

        # Case 1 (P3-XIAO-2K-16CH-IMU-256FIFO):
        # XIAO nRF52840 接收器在真实 256B TinyUSB CDC TX FIFO 下转发 16CH@2000SPS + 104Hz IMU + 运行期高频 STATUS 'R' 轮询！
        # 修复前：send_now() 绕过 ring 直写 256B FIFO，撕裂半帧并丢弃 'R'/META 字节！
        bid = boot_c08b_bench(lib_board)
        bridge_xd = SiliconDongleSerialBridge("xiao", lib_xd, lib_board, usb_tx_cap=256, usb_sof_drain_bytes=64)
        out_xd = tmp / "xd_16ch_2k"
        res_xd = await c08b_stream.run_dongle_c08b(
            "/dev/cu.sim_xiao_dongle", out_xd, seconds=0.55, mode="test",
            allow_real=True, expected=bid, with_imu=True, fs_hz=2000,
            open_ser=lambda _p: bridge_xd, reconnect_timeout=3.0,
        )
        dong_ev = json.loads((out_xd / "dongle.json").read_text())
        c_cnt, d_cnt, n_cnt, pk, mtu_rq, rdy, crit_bad = (
            ctypes.c_uint32(), ctypes.c_uint32(), ctypes.c_uint32(),
            ctypes.c_uint32(), ctypes.c_uint32(), ctypes.c_bool(), ctypes.c_bool(),
        )
        lib_xd.xd_get_stats(
            ctypes.byref(c_cnt), ctypes.byref(d_cnt), ctypes.byref(n_cnt),
            ctypes.byref(pk), ctypes.byref(mtu_rq), ctypes.byref(rdy), ctypes.byref(crit_bad),
        )
        assert not crit_bad.value, "vTaskSuspendAll/xTaskResumeAll 未配对平衡！"
        assert dong_ev["junk_bytes"] == 0, f"XIAO 接收器出现串口撕裂杂字节 junk_bytes={dong_ev['junk_bytes']}"
        assert res_xd["bad_packets"] == 0 and res_xd["imu_bad_packets"] == 0 and res_xd["missing_samples"] == 0
        assert res_xd["valid_samples"] >= 900 and res_xd["imu_samples"] >= 45 and d_cnt.value == 0
        assert mtu_rq.value >= 1
        cases_out.append({
            "id": "P3-XIAO-2K-16CH-IMU-256FIFO",
            "title": "正例（Bug #7 已修复）：XIAO nRF52840 接收器在 256B TinyUSB FIFO 满载下跑 16CH@2000SPS + IMU + STATUS 轮询零撕裂（junk_bytes=0）",
            "pass": True,
            "valid_samples": res_xd["valid_samples"],
            "imu_samples": res_xd["imu_samples"],
            "junk_bytes": dong_ev["junk_bytes"],
            "dongle_ring_peak": pk.value,
            "dongle_ring_drops": d_cnt.value,
        })

        # Case 2 (P3-XIAO-ONLINE-REG): 经 XIAO USB 接收器在线执行 WREG/RREG/CLRO（META >360B 超 256B FIFO 分块无损）
        bid = boot_c08b_bench(lib_board)
        bridge_xd_reg = SiliconDongleSerialBridge("xiao", lib_xd, lib_board, usb_tx_cap=256, usb_sof_drain_bytes=64)
        w_res = await c08b_stream.run_dongle_reg_c08b(
            "/dev/cu.sim_xiao_dongle", "wreg", chip="both", addr=0x05, val=0x60,
            allow_real=True, expected=bid, open_ser=lambda _p: bridge_xd_reg,
        )
        assert w_res["last_reg"]["u1"] == 0x60 and w_res["last_reg"]["u2"] == 0x60 and w_res["dongle_junk_bytes"] == 0
        c_res = await c08b_stream.run_dongle_reg_c08b(
            "/dev/cu.sim_xiao_dongle", "clro", expected=bid, open_ser=lambda _p: SiliconDongleSerialBridge("xiao", lib_xd, lib_board, usb_tx_cap=256),
        )
        assert c_res["reg_overrides"] == 0 and c_res["dongle_junk_bytes"] == 0
        cases_out.append({
            "id": "P3-XIAO-ONLINE-REG",
            "title": "正例：经 XIAO 接收器 0xA5 串口帧在线执行 WREG/CLRO，>360B 长 META 跨 256B TinyUSB FIFO 分片无损返回",
            "pass": True,
            "wreg_last_reg": w_res["last_reg"],
        })

        # Case 3 (P3-C6-2K-16CH-IMU-FRAG22): ESP32-C6 NimBLE 接收器（22B GATT 长读分片重组 + YUANLI-C08B 主动协商 MTU 247 + IMU kind=6）
        bid = boot_c08b_bench(lib_board)
        bridge_c6 = SiliconDongleSerialBridge("c6", lib_c6, lib_board, usb_tx_cap=256, usb_sof_drain_bytes=64, read_frag=22)
        out_c6 = tmp / "c6_16ch_2k"
        res_c6 = await c08b_stream.run_dongle_c08b(
            "/dev/cu.sim_c6_dongle", out_c6, seconds=0.5, mode="test",
            allow_real=True, expected=bid, with_imu=True, fs_hz=2000,
            open_ser=lambda _p: bridge_c6, reconnect_timeout=3.0,
        )
        c6_ev = json.loads((out_c6 / "dongle.json").read_text())
        cc, cd, cn, cmtu, crdy = ctypes.c_uint32(), ctypes.c_uint32(), ctypes.c_uint32(), ctypes.c_uint32(), ctypes.c_bool()
        lib_c6.c6_get_stats(ctypes.byref(cc), ctypes.byref(cd), ctypes.byref(cn), ctypes.byref(cmtu), ctypes.byref(crdy))
        assert c6_ev["junk_bytes"] == 0 and res_c6["missing_samples"] == 0 and res_c6["imu_samples"] >= 40
        assert cmtu.value >= 1, "ESP32-C6 连 YUANLI-C08B 必须主动发起 MTU 247 协商"
        cases_out.append({
            "id": "P3-C6-2K-16CH-IMU-FRAG22",
            "title": "正例：ESP32-C6 NimBLE 接收器主动协商 MTU=247、22B 分片重组长读 META/STATUS 并无损转发 16CH@2k + IMU(kind=6)",
            "pass": True,
            "valid_samples": res_c6["valid_samples"],
            "imu_samples": res_c6["imu_samples"],
            "c6_mtu_initiated": cmtu.value,
        })

        # Case 4 (P3-C6-R01-PASSIVE-MTU): ESP32-C6 编译为 MAKO-V12-ADS-2K 目标时严禁主动发起 MTU（防撞 R01 实测坑 #8）
        lib_c6_r01.c6_init(256, False, 244)
        lib_c6_r01.c6_feed_adv(b"YUANLI-C08B")  # 异名外设必须忽略不连
        cc0, cd0, cn0, cmtu0, crdy0 = ctypes.c_uint32(), ctypes.c_uint32(), ctypes.c_uint32(), ctypes.c_uint32(), ctypes.c_bool()
        lib_c6_r01.c6_get_stats(ctypes.byref(cc0), ctypes.byref(cd0), ctypes.byref(cn0), ctypes.byref(cmtu0), ctypes.byref(crdy0))
        assert cc0.value == 0 and not crdy0.value
        lib_c6_r01.c6_feed_adv(b"MAKO-V12-ADS-2K")
        lib_c6_r01.c6_get_stats(ctypes.byref(cc0), ctypes.byref(cd0), ctypes.byref(cn0), ctypes.byref(cmtu0), ctypes.byref(crdy0))
        assert cc0.value == 1 and crdy0.value and cmtu0.value == 0, (cc0.value, crdy0.value, cmtu0.value)
        cases_out.append({
            "id": "P3-C6-R01-PASSIVE-MTU",
            "title": "正例：ESP32-C6 在 MAKO-V12-ADS-2K 档过滤异名广播且保持 0 次主动 MTU 协商（兼容无 IMU 外设）",
            "pass": True,
            "connects": cc0.value,
            "c6_mtu_initiated_on_r01": cmtu0.value,
        })

        # Case 5 (P3-XIAO-BENCH-1S, PR #14 Finding #14 正例修复):
        # 真实运行正时长 seconds=1 (1000 ms) 的 'B' USB 带宽压测（主机每 1ms SOF 取 512B）：
        # 验证 256B TinyUSB FIFO 分片流控无损送达 >1000 个 0x7F 填充帧（256KB/s + 32KB 环形缓冲 ≈ 1164 帧），0 杂字节，0x80|'B' 报告帧数与实收 1:1 相等！
        SIM_EXEC.call(lambda: (lib_xd.xd_set_peer_callbacks(*(WRITE_CB(), READ_CB(), SUB_CB(), MTU_CB())), lib_xd.xd_init(256, True)))
        lib_xd.xd_config_usb_host_sim(True, 512, 0, 0)
        t0_b1 = lib_xd.xd_now_us()
        b1_cmd = bytes([0xA5, ord("B"), 2, 0, 1, 0])  # seconds = 1 (正时长 1000 ms)
        lib_xd.xd_usb_host_send((ctypes.c_uint8 * len(b1_cmd))(*b1_cmd), len(b1_cmd))
        lib_xd.xd_step_loop(1000)
        for _ in range(20):
            lib_xd.xd_step_loop(1000)
        dt_b1_us = int(lib_xd.xd_now_us() - t0_b1)
        cap_buf = (ctypes.c_uint8 * 1_048_576)()
        rx_b = bytearray()
        while True:
            gn = lib_xd.xd_pop_auto_captured(cap_buf, 1_048_576)
            if gn <= 0:
                break
            rx_b.extend(bytes(cap_buf[:gn]))
        tbuf = (ctypes.c_uint8 * 512)()
        while True:
            gn = lib_xd.xd_usb_host_recv(tbuf, 512)
            if gn <= 0:
                break
            rx_b.extend(bytes(tbuf[:gn]))
        ps_b1 = v12_dongle.Parser()
        frames_b = ps_b1.feed(bytes(rx_b))
        fill_cnt = sum(1 for k, _, p in frames_b if k == 0x7F and len(p) == 240)
        b_replies = [p for k, _, p in frames_b if k == (0x80 | ord("B"))]
        assert ps_b1.junk == 0, f"1s USB 带宽测试出现杂字节 junk={ps_b1.junk}"
        assert len(b_replies) == 1 and len(b_replies[0]) == 5 and b_replies[0][0] == 0, b_replies
        rep_frames = int.from_bytes(b_replies[0][1:5], "little")
        assert rep_frames == fill_cnt and fill_cnt >= 1000, (rep_frames, fill_cnt)
        assert 1_000_000 <= dt_b1_us <= 1_250_000, dt_b1_us
        cases_out.append({
            "id": "P3-XIAO-BENCH-1S",
            "title": "正例（PR #14 Finding #14 已修复）：XIAO 接收器运行 seconds=1 正时长 USB 带宽压测，跨 256B FIFO 零丢帧零撕裂（实收帧数==应答帧数）",
            "pass": True,
            "bench_seconds": 1,
            "intact_0x7f_frames": fill_cnt,
            "elapsed_sim_ms": round(dt_b1_us / 1000.0, 1),
            "junk_bytes": ps_b1.junk,
        })

        # Case 6 (NC-3a-MID-CAPTURE-RECONNECT): 采集中途 BLE 空口闪断自动重连 -> connects+1 被主机识别并拒绝拼接！
        bid = boot_c08b_bench(lib_board)
        bridge_flap = SiliconDongleSerialBridge("xiao", lib_xd, lib_board, usb_tx_cap=256, usb_sof_drain_bytes=64)
        out_flap = tmp / "xd_flap"

        async def _flap_task():
            await asyncio.sleep(0.18)
            bridge_flap.inject_air_flap_reconnect()

        ftask = asyncio.create_task(_flap_task())
        try:
            await c08b_stream.run_dongle_c08b(
                "/dev/cu.sim_flap", out_flap, seconds=0.6, mode="synth",
                open_ser=lambda _p: bridge_flap, reconnect_timeout=3.0,
            )
            raise AssertionError("采集中途接收器闪断重连未被拦截（违反严禁拼接铁律）")
        except RuntimeError as exc:
            await ftask
            cases_out.append({
                "id": "NC-3a",
                "title": "反例：采集中途 BLE 空口闪断并自动重连（connects 递增）-> 主机当场拒绝跨连接拼接并作废本段",
                "pass": True,
                "expected_red_caught": True,
                "error": str(exc)[:80],
            })

        # Case 7 (NC-3b-RING-OVERFLOW-ACCOUNTING): 主机停止读串口导致接收器 32KB 环形缓冲打满 -> 整帧丢弃计数诚实递增、零半帧损坏
        SIM_EXEC.call(lambda: (lib_xd.xd_set_peer_callbacks(*(WRITE_CB(), READ_CB(), SUB_CB(), MTU_CB())), lib_xd.xd_init(256, True)))
        lib_xd.xd_feed_adv(b"YUANLI-C08B", True)
        dummy232 = (ctypes.c_uint8 * 232)(*([0xC0] + [0x11] * 231))
        for _ in range(160):  # 160 * 240B = 38,400B > 32,768B RING
            lib_xd.xd_feed_notify(2, dummy232, 232)
        c_o, d_o, n_o, pk_o, mr_o, rd_o, cb_o = (
            ctypes.c_uint32(), ctypes.c_uint32(), ctypes.c_uint32(),
            ctypes.c_uint32(), ctypes.c_uint32(), ctypes.c_bool(), ctypes.c_bool(),
        )
        lib_xd.xd_get_stats(ctypes.byref(c_o), ctypes.byref(d_o), ctypes.byref(n_o), ctypes.byref(pk_o), ctypes.byref(mr_o), ctypes.byref(rd_o), ctypes.byref(cb_o))
        assert d_o.value > 0 and not cb_o.value
        # 排空全部已入环帧，Parser 必须 0 junk_bytes 解出整包！
        drained = bytearray()
        rb = (ctypes.c_uint8 * 256)()
        for _ in range(300):
            lib_xd.xd_step_loop(100)
            gn = lib_xd.xd_usb_host_recv(rb, 256)
            if gn > 0:
                drained.extend(bytes(rb[:gn]))
        ps = v12_dongle.Parser()
        parsed_ovf = ps.feed(bytes(drained))
        assert ps.junk == 0 and len([1 for k, _, p in parsed_ovf if k == 2 and len(p) == 232]) + d_o.value == 160
        cases_out.append({
            "id": "NC-3b",
            "title": "反例：USB 主机卡死致 32KB 环形缓冲溢出 -> 接收器按整帧丢弃记入 ring_drops，剩余入环帧 0 字节错位（junk=0）",
            "pass": True,
            "expected_red_caught": True,
            "ring_drops": d_o.value,
            "intact_frames": 160 - d_o.value,
            "junk_bytes": ps.junk,
        })

        # Case 8 (NC-3c-C6-INVALID-CMD): C6 接收器拒绝越界连接间隔 'I'(<6 或 >3200) 与非法特征读索引
        SIM_EXEC.call(lambda: (lib_c6.c6_set_peer_callbacks(*(WRITE_CB(), READ_CB(), SUB_CB(), MTU_CB())), lib_c6.c6_init(256, True, 244)))
        lib_c6.c6_feed_adv(b"YUANLI-C08B")
        bad_i = bytes([0xA5, ord("I"), 2, 0, 2, 0])  # ci=2 < 6 非法
        bad_r = bytes([0xA5, ord("R"), 1, 0, 99])    # 索引 99 非法
        for raw_c in (bad_i, bad_r):
            lib_c6.c6_usb_host_send((ctypes.c_uint8 * len(raw_c))(*raw_c), len(raw_c))
        rx_err = bytearray()
        tb = (ctypes.c_uint8 * 256)()
        for _ in range(10):
            lib_c6.c6_step_io(1000)
            gn = lib_c6.c6_usb_host_recv(tb, 256)
            if gn > 0:
                rx_err.extend(bytes(tb[:gn]))
        err_frames = [p for k, _, p in v12_dongle.Parser().feed(bytes(rx_err)) if k in (0x80 | ord("I"), 0x80 | ord("R"))]
        assert len(err_frames) == 2 and err_frames[0][0] == 1 and err_frames[1][0] == 1, err_frames
        cases_out.append({
            "id": "NC-3c",
            "title": "反例：ESP32-C6 接收器准确拦截越界连接间隔(ci<6)与非法特征读请求，返回非零错误码",
            "pass": True,
            "expected_red_caught": True,
        })

        # Case 9 (NC-3d-BENCH-HOST-STALL, PR #14 Finding #13 反例修复 A):
        # 运行 seconds=1 带宽压测，电脑在 +300 ms 停止读取串口（Serial 仍连接但 FIFO 满）：
        # 收尾 200 ms 滑动看门狗超时后自动清空积压填充帧并返回 status=2，绝不永久卡死主循环；恢复读取后 'Q' 立即正常应答！
        SIM_EXEC.call(lambda: (lib_xd.xd_set_peer_callbacks(*(WRITE_CB(), READ_CB(), SUB_CB(), MTU_CB())), lib_xd.xd_init(256, True)))
        lib_xd.xd_config_usb_host_sim(True, 512, 300_000, 0)
        t0_st = lib_xd.xd_now_us()
        lib_xd.xd_usb_host_send((ctypes.c_uint8 * len(b1_cmd))(*b1_cmd), len(b1_cmd))
        lib_xd.xd_step_loop(1000)  # 若无 200ms 看门狗此处将无限死循环！
        dt_st_ms = (lib_xd.xd_now_us() - t0_st) / 1000.0
        assert 1180.0 <= dt_st_ms <= 1350.0, f"停读超时边界异常: {dt_st_ms} ms"
        lib_xd.xd_config_usb_host_sim(True, 512, 0, 0)
        q_cmd = bytes([0xA5, ord("Q"), 0, 0])
        lib_xd.xd_usb_host_send((ctypes.c_uint8 * len(q_cmd))(*q_cmd), len(q_cmd))
        for _ in range(15):
            lib_xd.xd_step_loop(1000)
        rx_st = bytearray()
        while True:
            gn = lib_xd.xd_pop_auto_captured(cap_buf, 1_048_576)
            if gn <= 0:
                break
            rx_st.extend(bytes(cap_buf[:gn]))
        while True:
            gn = lib_xd.xd_usb_host_recv(tbuf, 512)
            if gn <= 0:
                break
            rx_st.extend(bytes(tbuf[:gn]))
        ps_st = v12_dongle.Parser()
        fr_st = ps_st.feed(bytes(rx_st))
        b_st_rep = [p for k, _, p in fr_st if k == (0x80 | ord("B"))]
        q_st_rep = [p for k, _, p in fr_st if k == (0x80 | ord("Q"))]
        assert ps_st.junk == 0, f"停读恢复后出现半帧撕裂 junk={ps_st.junk}"
        assert len(b_st_rep) == 1 and b_st_rep[0][0] == 2, b_st_rep
        assert len(q_st_rep) == 1 and q_st_rep[0][0] == 0, q_st_rep
        cases_out.append({
            "id": "NC-3d",
            "title": "反例（PR #14 Finding #13 已修复）：seconds=1 带宽测试中途电脑停止读取 -> 200ms 看门狗超时清空返回 status=2，恢复读取后 'Q' 零杂字节响应",
            "pass": True,
            "expected_red_caught": True,
            "abort_elapsed_ms": round(dt_st_ms, 1),
            "bench_reply_status": b_st_rep[0][0],
            "junk_bytes_after_resume": ps_st.junk,
        })

        # Case 10 (NC-3e-BENCH-USB-DISCONNECT, PR #14 Finding #13 反例修复 B):
        # 运行 seconds=1 带宽压测，+250 ms 时电脑断开 USB CDC (!Serial)：
        # bench() 当场检出 !Serial 立即退出（不等满 1s+200ms），重插 USB 后下发 'Q' 立即正常响应！
        SIM_EXEC.call(lambda: (lib_xd.xd_set_peer_callbacks(*(WRITE_CB(), READ_CB(), SUB_CB(), MTU_CB())), lib_xd.xd_init(256, True)))
        lib_xd.xd_config_usb_host_sim(True, 512, 0, 250_000)
        t0_dc = lib_xd.xd_now_us()
        lib_xd.xd_usb_host_send((ctypes.c_uint8 * len(b1_cmd))(*b1_cmd), len(b1_cmd))
        lib_xd.xd_step_loop(1000)
        dt_dc_ms = (lib_xd.xd_now_us() - t0_dc) / 1000.0
        assert 240.0 <= dt_dc_ms <= 320.0, f"USB 断开未当场跳出 bench(): {dt_dc_ms} ms"
        while lib_xd.xd_pop_auto_captured(cap_buf, 1_048_576) > 0:
            pass
        while lib_xd.xd_usb_host_recv(tbuf, 512) > 0:
            pass
        lib_xd.xd_config_usb_host_sim(True, 512, 0, 0)
        lib_xd.xd_usb_host_send((ctypes.c_uint8 * len(q_cmd))(*q_cmd), len(q_cmd))
        for _ in range(10):
            lib_xd.xd_step_loop(1000)
        rx_dc = bytearray()
        while True:
            gn = lib_xd.xd_pop_auto_captured(cap_buf, 1_048_576)
            if gn <= 0:
                break
            rx_dc.extend(bytes(cap_buf[:gn]))
        while True:
            gn = lib_xd.xd_usb_host_recv(tbuf, 512)
            if gn <= 0:
                break
            rx_dc.extend(bytes(tbuf[:gn]))
        ps_dc = v12_dongle.Parser()
        fr_dc = ps_dc.feed(bytes(rx_dc))
        q_dc_rep = [p for k, _, p in fr_dc if k == (0x80 | ord("Q"))]
        assert ps_dc.junk == 0 and len(q_dc_rep) == 1 and q_dc_rep[0][0] == 0, (ps_dc.junk, fr_dc)
        cases_out.append({
            "id": "NC-3e",
            "title": "反例（PR #14 Finding #13 已修复）：seconds=1 带宽测试中途 USB 拔线(!Serial) -> 250ms 当场跳出不挂死，重连后主循环正常响应 'Q'",
            "pass": True,
            "expected_red_caught": True,
            "disconnect_escape_ms": round(dt_dc_ms, 1),
            "junk_bytes_after_reconnect": ps_dc.junk,
        })

        # Case 11 (NC-3f-UINT32-WRAP-0xFFFFFF00):
        # 复现独立审计阻断场景：head/tail/pkt_end 位于 0xFFFFFF00u（距 2^32 回绕仅 256B），
        # 入队 34B 短帧(0xFFFFFF22) + 248B 长帧(跨零至 0x0000001A) 并在 64B 受限 FIFO 下触发 bench(1) 停读截断：
        # 验证模差 min(h - t, pkt_end - t) 严格守住单帧边界，不跨零下溢、不锁死 put_frame，恢复读取后 0 杂字节！
        SIM_EXEC.call(lambda: (lib_xd.xd_set_peer_callbacks(*(WRITE_CB(), READ_CB(), SUB_CB(), MTU_CB())), lib_xd.xd_init(64, True)))
        lib_xd.xd_feed_adv(b"YUANLI-C08B", True)
        lib_xd.xd_seed_ring_cursor(0xFFFFFF00)
        short26 = (ctypes.c_uint8 * 26)(*([0xC0] + [0x22] * 25))
        long240 = (ctypes.c_uint8 * 240)(*([0xC0] + [0x33] * 239))
        lib_xd.xd_feed_notify(2, short26, 26)   # +34B -> head = 0xFFFFFF22
        lib_xd.xd_feed_notify(2, long240, 240)  # +248B -> head = 0x0000001A (跨 2^32 回绕！)
        # FIFO 容量仅 64B，不自动排空，直接发 B(1) 触发 200ms 停读截断
        lib_xd.xd_config_usb_host_sim(True, 0, 0, 0)
        lib_xd.xd_usb_host_send((ctypes.c_uint8 * len(b1_cmd))(*b1_cmd), len(b1_cmd))
        lib_xd.xd_step_loop(1000)
        # 随后恢复高速读取并下发 'Q'，若发生跨零下溢则 ring 被永久锁死且出现半帧撕裂
        lib_xd.xd_config_usb_host_sim(True, 512, 0, 0)
        lib_xd.xd_usb_host_send((ctypes.c_uint8 * len(q_cmd))(*q_cmd), len(q_cmd))
        for _ in range(20):
            lib_xd.xd_step_loop(1000)
        rx_wr = bytearray()
        while True:
            gn = lib_xd.xd_pop_auto_captured(cap_buf, 1_048_576)
            if gn <= 0:
                break
            rx_wr.extend(bytes(cap_buf[:gn]))
        while True:
            gn = lib_xd.xd_usb_host_recv(tbuf, 512)
            if gn <= 0:
                break
            rx_wr.extend(bytes(tbuf[:gn]))
        ps_wr = v12_dongle.Parser()
        fr_wr = ps_wr.feed(bytes(rx_wr))
        b_wr_rep = [p for k, _, p in fr_wr if k == (0x80 | ord("B"))]
        q_wr_rep = [p for k, _, p in fr_wr if k == (0x80 | ord("Q"))]
        assert ps_wr.junk == 0, f"跨 2^32 回绕截断出现杂字节 junk={ps_wr.junk}"
        assert len(b_wr_rep) == 1 and b_wr_rep[0][0] == 2, b_wr_rep
        assert len(q_wr_rep) == 1 and q_wr_rep[0][0] == 0, q_wr_rep
        cases_out.append({
            "id": "NC-3f",
            "title": "反例（独立审计回绕边界）：0xFFFFFF00 跨 2^32 回绕 + 64B FIFO 停读截断 -> 模差比较零下溢、零撕裂，'Q' 正常恢复",
            "pass": True,
            "expected_red_caught": True,
            "junk_bytes": ps_wr.junk,
        })

    summary = {
        "suite": "Sim-3 (XIAO nRF52840 & ESP32-C6 USB BLE Central Dongles Silicon-in-the-Loop)",
        "total_cases": len(cases_out),
        "passed_cases": sum(1 for c in cases_out if c["pass"]),
        "cases": cases_out,
    }
    out_path = SIM_DIR / "reports" / "results_sim3_dongle.json"
    out_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"SIM3_ALL_PASS ({summary['passed_cases']}/{summary['total_cases']}) -> {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(async_main()))

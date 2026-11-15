#!/usr/bin/env python3
"""T1-d：C08B v0.01 双真机（STM32L432KBU6 + XIAO nRF52840 Sense）故障、互锁、断链与防拼接实测。

安全前提：
  - 全程保持默认双硬件锁关闭（MAKO_C08B_AFE_ENABLED=0, MAKO_BENCH_MEASURED=0）
  - 不焊接、不开模拟供电（ANA_EN 全程实测为 0）
  - 包含正例与必须报红的反例（丢包缺口必红、跨连接 connects+1 必拒、6 种真采指令必拒）
"""
from __future__ import annotations

import ctypes
import glob
import json
import os
from pathlib import Path
import queue
import struct
import subprocess
import sys
import tempfile
import threading
import time

ctypes.CDLL("/opt/homebrew/lib/libusb-1.0.dylib", mode=ctypes.RTLD_GLOBAL)

HERE = Path(__file__).resolve().parent
SIM_ROOT = Path(os.environ.get("C08B_HIL_WORKDIR", Path(tempfile.gettempdir()) / "c08b-dual-hil"))
FW_DIR = SIM_ROOT / "c08b-stream-hil"
ELF_PATH = FW_DIR / "build/l432.elf"
OPENEMG_REPO = HERE.parents[3]
_DEFAULT_VENV = OPENEMG_REPO / "host/.venv-emg/bin/python"
EMGPY = Path(os.environ.get("OPENEMG_PY", str(_DEFAULT_VENV if _DEFAULT_VENV.exists() else sys.executable)))
NM_BIN = Path.home() / ".platformio/packages/toolchain-gccarmnoneeabi/bin/arm-none-eabi-nm"
OUT_JSON = SIM_ROOT / "t1d_fault_injection_report.json"

GPIOA_ODR = 0x48000014
GPIOB_ODR = 0x48000414
GPIOC_ODR = 0x48000814
GPIOH_IDR = 0x48001C10


def crc16_ccitt(data: bytes) -> int:
    c = 0xFFFF
    for b in data:
        c ^= b << 8
        for _ in range(8):
            c = ((c << 1) ^ 0x1021) & 0xFFFF if (c & 0x8000) else (c << 1) & 0xFFFF
    return c


def pack_rx_cmd(req_mode: int, nrf_flags: int, synth_ch: int, fs_hz: int, epoch: int) -> bytes:
    body = struct.pack("<HBBBBHIH", 0x53C8, 1, req_mode, nrf_flags, synth_ch, fs_hz, epoch, 0)
    assert len(body) == 14
    return body + struct.pack("<H", crc16_ccitt(body))


def unpack_ble_status(raw64: bytes) -> dict:
    assert len(raw64) == 64, f"STATUS 长度异常: {len(raw64)}"
    produced, ring_dropped, sched_skip, sent_samples, notify_fail = struct.unpack_from("<5Q", raw64, 0)
    fault, active, bench_meas, ver = struct.unpack_from("<4B", raw64, 40)
    ads_status, drdy_edges, drdy_min_iv, spi_hz = struct.unpack_from("<IQI I".replace(" ", ""), raw64, 44)
    assert ver == 1, f"status_version 异常: {ver}"
    return {
        "produced": produced,
        "ring_dropped": ring_dropped,
        "scheduler_skipped": sched_skip,
        "sent_samples": sent_samples,
        "notify_failures": notify_fail,
        "fault": fault,
        "active": bool(active),
        "bench_measured": bool(bench_meas),
        "ads_status_hex": f"0x{ads_status:06X}",
        "drdy_edges": drdy_edges,
        "drdy_min_interval_us": drdy_min_iv,
        "spi_hz": spi_hz,
    }


def unpack_tx_header(raw280: bytes) -> dict:
    assert len(raw280) == 280
    (
        magic, ver, afe_mode, state_flags, fault, sample_count, f01_flags,
        seq_first, ts_us, produced, dropped, bad_status, drdy_desync,
        min_iv_sat, id_a, id_b, active_mode, imu_fresh, imu_read_us, _pad, imu_ts_us
    ) = struct.unpack_from("<HBBBBBBIQIIHHHBBBBHHQ", raw280, 0)
    crc_ok = (magic == 0xC853 and ver == 1 and crc16_ccitt(raw280[:278]) == struct.unpack_from("<H", raw280, 278)[0])
    return {
        "crc_ok": crc_ok,
        "afe_mode": afe_mode,
        "state_flags": state_flags,
        "fault": fault,
        "sample_count": sample_count,
        "f01_flags": f01_flags,
        "seq_first": seq_first,
        "produced": produced,
        "dropped": dropped,
        "active_mode": active_mode,
    }


def load_symbols(elf: Path) -> dict[str, int]:
    out = subprocess.check_output([str(NM_BIN), "-n", str(elf)], text=True)
    syms = {}
    for line in out.splitlines():
        parts = line.strip().split()
        if len(parts) == 3:
            syms[parts[2]] = int(parts[0], 16)
    return syms


class A5FramedSerial:
    def __init__(self, port: str):
        for sp in [str(p) for p in [*(HERE.parents[3] / "host/.venv-emg").glob("lib/python*/site-packages"), *Path.home().glob(".platformio/penv/lib/python*/site-packages")]]:
            if sp not in sys.path:
                sys.path.append(sp)
        import serial
        self.ser = serial.Serial(port, 115200, timeout=0.003)
        self.lock = threading.Lock()
        self.buf = bytearray()
        self.replies: dict[int, queue.Queue] = {}
        self.link_frames: list[bytes] = []
        self.emg_pkts: list[bytes] = []
        self.imu_pkts: list[bytes] = []
        self._stop = False
        self._thr = threading.Thread(target=self._reader, daemon=True)
        self._thr.start()

    def close(self):
        self._stop = True
        self._thr.join(timeout=0.5)
        try:
            self.ser.close()
        except Exception:
            pass

    def _reader(self):
        while not self._stop:
            try:
                n_wait = self.ser.in_waiting
                chunk = self.ser.read(n_wait if n_wait > 0 else 1)
            except Exception:
                break
            if not chunk:
                continue
            self.buf.extend(chunk)
            while True:
                idx = self.buf.find(0xA5)
                if idx < 0:
                    self.buf.clear()
                    break
                if idx > 0:
                    del self.buf[:idx]
                if len(self.buf) < 8:
                    break
                kind = self.buf[1]
                plen = self.buf[2] | (self.buf[3] << 8)
                if plen > 600:
                    del self.buf[:1]
                    continue
                if len(self.buf) < 8 + plen:
                    break
                pay = bytes(self.buf[8 : 8 + plen])
                del self.buf[: 8 + plen]
                if kind == 2:
                    self.emg_pkts.append(pay)
                elif kind == 6:
                    self.imu_pkts.append(pay)
                elif kind == 0x11:
                    self.link_frames.append(pay)
                elif kind & 0x80:
                    op = kind & 0x7F
                    q = self.replies.setdefault(op, queue.Queue())
                    q.put(pay)

    def transact(self, op_char: str, payload: bytes = b"", timeout: float = 1.5) -> bytes:
        op = ord(op_char)
        q = self.replies.setdefault(op, queue.Queue())
        with self.lock:
            while not q.empty():
                try:
                    q.get_nowait()
                except queue.Empty:
                    break
            hdr = struct.pack("<BBH", 0xA5, op, len(payload))
            self.ser.write(hdr + payload)
            return q.get(timeout=timeout)

    def transact_batch_L(self, payloads: list[bytes], timeout: float = 1.5) -> list[bytes]:
        op = ord("L")
        q = self.replies.setdefault(op, queue.Queue())
        with self.lock:
            while not q.empty():
                try:
                    q.get_nowait()
                except queue.Empty:
                    break
            blob = b"".join(struct.pack("<BBH", 0xA5, op, len(p)) + p for p in payloads)
            self.ser.write(blob)
            return [q.get(timeout=timeout) for _ in payloads]


def check_emg_sequence_gaps(pkts: list[bytes]) -> dict:
    """解析 F01 v4 (16ch) 包，逐包核对采样序号连续性，任何缺口立即计入 missing_samples。"""
    expected_seq = None
    total_samples = 0
    missing_samples = 0
    gap_events = []
    for idx, p in enumerate(pkts):
        assert len(p) >= 16 and p[0] == 4 and p[1] == 1, f"非 F01 v4 包: idx={idx}, hdr={p[:4].hex()}"
        n_frames = p[2]
        flags = p[3]
        seq = struct.unpack_from("<I", p, 4)[0]
        assert len(p) == 16 + n_frames * 54
        if expected_seq is None or (flags & 0x02):  # SESSION_START
            expected_seq = seq
        elif seq != expected_seq:
            gap = (seq - expected_seq) & 0xFFFFFFFF
            missing_samples += gap
            gap_events.append({"pkt_idx": idx, "expected_seq": expected_seq, "got_seq": seq, "gap": gap})
            expected_seq = seq
        expected_seq = (expected_seq + n_frames) & 0xFFFFFFFF
        total_samples += n_frames
    return {
        "packets": len(pkts),
        "received_samples": total_samples,
        "missing_samples": missing_samples,
        "gap_events": gap_events,
        "lossless": (missing_samples == 0 and len(gap_events) == 0),
    }


def run_host_gates_and_antisplice(captured_stall_pkts: list[bytes], clean_pkts: list[bytes]) -> dict:
    """调用 host/.venv-emg/bin/python 验证：
      1) C08BRig + AcqHandler 收到带硬件丢包缺口的真实帧时，dropped 精确捕获缺口且触发边界
      2) capture_c08b 在中途 connects+1（BLE 闪断重连）时当场抛异常拒收，禁止拼接佩戴段
      3) C11 c08b_gate_mode_request 解锁态下 VBUS=1 强制返回 C08B_FAULT_INTERLOCK(3)
    """
    with tempfile.TemporaryDirectory(prefix="t1d_host_") as td:
        td_path = Path(td)
        stall_file = td_path / "stall_pkts.json"
        clean_file = td_path / "clean_pkts.json"
        stall_file.write_text(json.dumps([p.hex() for p in captured_stall_pkts]))
        clean_file.write_text(json.dumps([p.hex() for p in clean_pkts]))

        # 1. C11 解锁态 VBUS=1 互锁门测试
        c_src = td_path / "probe_interlock.c"
        c_bin = td_path / "probe_interlock"
        c_src.write_text(
            """
#include <assert.h>
#include <stdio.h>
#include "stream_proto.h"
int main(void) {
    const uint8_t real_modes[6] = {
        C08B_MODE_TST1, C08B_MODE_SHT1, C08B_MODE_EXT1,
        C08B_MODE_EXR1, C08B_MODE_RLD1, C08B_MODE_PRB1
    };
    for (int i = 0; i < 6; i++) {
        /* 层1：未解锁时任何模式返回 FAULT_LOCKED(1) */
        assert(c08b_gate_mode_request(real_modes[i], 1000u, false, false) == C08B_FAULT_LOCKED);
        assert(c08b_gate_mode_request(real_modes[i], 1000u, false, true)  == C08B_FAULT_LOCKED);
        /* 层2：即便台架双锁解开，只要 VBUS=1（L432 PH3 或 nRF P0.02），全部 6 种真采必返 FAULT_INTERLOCK(3) */
        assert(c08b_gate_mode_request(real_modes[i], 1000u, true, true)   == C08B_FAULT_INTERLOCK);
        /* 正例对照：台架双锁解开且 VBUS=0 时放行 */
        assert(c08b_gate_mode_request(real_modes[i], 1000u, true, false)  == C08B_FAULT_NONE);
    }
    /* SYN1 不开 ANA_EN，VBUS=1 下仍允许跑无电链路自检 */
    assert(c08b_gate_mode_request(C08B_MODE_SYN1, 1000u, false, true) == C08B_FAULT_NONE);
    printf("C11_INTERLOCK_GATE_OK\\n");
    return 0;
}
""",
            encoding="utf-8",
        )
        subprocess.run(
            [
                "cc", "-std=c11", "-O2", "-Wall", "-Wextra", "-Werror",
                "-I", str(OPENEMG_REPO / "firmware/c08b-stream/common"),
                str(c_src), "-o", str(c_bin),
            ],
            check=True,
        )
        c_out = subprocess.check_output([str(c_bin)], text=True).strip()
        assert c_out == "C11_INTERLOCK_GATE_OK"

        # 2. Python C08BRig 丢包计数 + capture_c08b connects+1 防拼接必败反例
        py_script = td_path / "verify_host_redlines.py"
        py_script.write_text(
            f"""
import asyncio, json, sys
from pathlib import Path
sys.path.insert(0, {repr(str(OPENEMG_REPO / "host"))})
import c08b_stream as cs
import device_desc as dd
from rig import AcqHandler

stall_pkts = [bytes.fromhex(x) for x in json.loads(Path({repr(str(stall_file))}).read_text())]
clean_pkts = [bytes.fromhex(x) for x in json.loads(Path({repr(str(clean_file))}).read_text())]

# A. 喂入真实双机溢出的 F01 v4 包，核对 C08BRig / AcqHandler 捕获丢帧
rig = cs.C08BRig(n_channels=16, fs_Hz=1000, allow_real=False)
desc = dd.load("c08b-16ch")
acq = AcqHandler(rig, desc)
acq.open()
for p in stall_pkts:
    rig.feed_packet(p)
st_stall = acq.status()
assert st_stall["dropped"] > 0, f"AcqHandler 未抓到丢包缺口: {{st_stall}}"

# 正例对照：无溢出真实双机包 dropped 必须为 0
rig_ok = cs.C08BRig(n_channels=16, fs_Hz=1000, allow_real=False)
acq_ok = AcqHandler(rig_ok, desc)
acq_ok.open()
for p in clean_pkts:
    rig_ok.feed_packet(p)
st_ok = acq_ok.status()
assert st_ok["dropped"] == 0 and st_ok["samples"] > 80, f"干净流误报丢包: {{st_ok}}"

# B. 必败反例：1) 真实双机包流式采集中途 BLE 断连；2) 接收器中途闪断自动重连 (connects: 1 -> 2)，均必须抛 RuntimeError 作废
from check_c08b_stream import BUILD_ID, FakeC08BBleClient, FakeDongleSerial

class RealPktMidDropBleClient(FakeC08BBleClient):
    def __init__(self, real_pkts):
        super().__init__(board_afe="NONE", initial_afe="NONE", bench_measured=False)
        self._real_pkts = real_pkts
        self.is_connected = True

    async def _pump(self, is_synth):
        cb = self.notify_cbs.get(cs.DATA)
        for idx, pkt in enumerate(self._real_pkts[:16]):
            if not self.active:
                break
            if idx == 6:
                self.is_connected = False
            if cb is not None:
                cb(1, pkt)
            self.produced = (idx + 1) * 4
            self.sent = (idx + 1) * 4
            await asyncio.sleep(0.01)

async def run_splice_check():
    # B1: 真机包喂入 BLE capture_c08b，第 6 包断连
    out_ble = Path({repr(str(td_path / "splice_ble_out"))})
    c_ble = RealPktMidDropBleClient(clean_pkts)
    ble_err = None
    try:
        await cs.capture_c08b(c_ble, out_ble, seconds=0.35, mode="synth", synth_channels=16)
    except RuntimeError as e:
        ble_err = str(e)
    assert ble_err and "连接中断或重连" in ble_err, f"BLE 断连未被拒收: {{ble_err}}"

    # B2: Dongle 接收器中途 connects 自增 (1 -> 2)，run_dongle_c08b 必须当场中断报错防拼接
    loop = asyncio.get_running_loop()
    ble_drop = FakeC08BBleClient(board_afe="ADS1298_DUAL", initial_afe="NONE", bench_measured=True)
    ser_drop = FakeDongleSerial(ble_drop, loop, inject_mid_reconnect=True)
    out_dongle = Path({repr(str(td_path / "splice_dongle_out"))})
    dongle_err = None
    try:
        await cs.run_dongle_c08b(
            "/dev/cu.fake_drop", out_dongle, seconds=0.5, mode="test",
            allow_real=True, expected=BUILD_ID, with_imu=True,
            open_ser=lambda _p: ser_drop, reconnect_timeout=1.0,
        )
    except RuntimeError as e:
        dongle_err = str(e)
    assert dongle_err and "连接中断或重连" in dongle_err, f"Dongle connects+1 未被拒收: {{dongle_err}}"
    return {{"rejected": True, "error": f"{{ble_err}} | {{dongle_err}}", "ble_mid_drop_error": ble_err, "dongle_connects_inc_error": dongle_err}}

splice_res = asyncio.run(run_splice_check())
print(json.dumps({{
    "acq_stall_samples": st_stall["samples"],
    "acq_stall_dropped_seq8": st_stall["dropped"],
    "acq_clean_samples": st_ok["samples"],
    "acq_clean_dropped": st_ok["dropped"],
    "anti_splice": splice_res,
}}, ensure_ascii=False))
""",
            encoding="utf-8",
        )
        py_out = subprocess.check_output([str(EMGPY), "-B", str(py_script)], text=True).strip()
        host_res = json.loads(py_out)
        host_res["c11_unlocked_vbus_interlock"] = c_out
        return host_res


def main():
    from pyocd.core.helpers import ConnectHelper

    ports = sorted(glob.glob("/dev/cu.usbmodem*"))
    assert ports, "未找到 XIAO USB 串口 /dev/cu.usbmodem*"
    port = ports[0]
    print(f"=== T1-d 启动：XIAO ({port}) + ST-LINK V2 (STM32L432KBU6) ===")

    syms = load_symbols(ELF_PATH)
    hil_addr = syms["g_swd_hil"]
    tx_frame_addr = syms["g_tx_frame"]
    last_rx_addr = syms["g_last_rx"]
    RING_OFF = 40
    SLOTS = 128

    xiao = A5FramedSerial(port)
    tx_q: queue.Queue[bytes] = queue.Queue()
    rx_q: queue.Queue[bytes] = queue.Queue()
    usb_stop = False
    usb_pause = False

    def usb_relay_worker():
        last_rx = b""
        last_poll = 0.0
        while not usb_stop or not tx_q.empty():
            if usb_pause:
                time.sleep(0.005)
                continue
            batch: list[bytes] = []
            try:
                first = tx_q.get(timeout=0.006)
                batch.append(first)
                while len(batch) < 8:
                    try:
                        batch.append(tx_q.get_nowait())
                    except queue.Empty:
                        break
            except queue.Empty:
                pass

            if batch:
                reps = xiao.transact_batch_L(batch, timeout=1.5)
                for rep in reps:
                    rx16 = rep[1:17]
                    if len(rx16) == 16 and rx16 != last_rx:
                        last_rx = rx16
                        rx_q.put(rx16)
            elif not usb_stop:
                now = time.monotonic()
                if now - last_poll >= 0.012:
                    last_poll = now
                    rep = xiao.transact("L", b"", timeout=1.5)
                    rx16 = rep[1:17]
                    if len(rx16) == 16 and rx16 != last_rx:
                        last_rx = rx16
                        rx_q.put(rx16)

    report: dict = {"timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "port": port, "cases": {}}

    try:
        with ConnectHelper.session_with_chosen_probe(
            target_override="stm32l432kc",
            frequency=4_000_000,
        ) as sess:
            target = sess.target
            target.reset_and_halt()
            target.resume()
            time.sleep(0.08)

            assert target.read32(hil_addr + 0) == 0x48494C31
            target.write32(hil_addr + 4, 1)
            xiao.transact("D")

            u_thr = threading.Thread(target=usb_relay_worker, daemon=True)
            u_thr.start()

            def read_l432_afe_pins() -> dict[str, int]:
                odr_a = target.read32(GPIOA_ODR)
                odr_b = target.read32(GPIOB_ODR)
                odr_c = target.read32(GPIOC_ODR)
                idr_h = target.read32(GPIOH_IDR)
                return {
                    "ANA_EN_PC14": (odr_c >> 14) & 1,
                    "ADS_PWDN_PA1": (odr_a >> 1) & 1,
                    "ADS_START_PA3": (odr_a >> 3) & 1,
                    "ADS_RESET_PA8": (odr_a >> 8) & 1,
                    "CS_A_PB0": (odr_b >> 0) & 1,
                    "CS_B_PB1": (odr_b >> 1) & 1,
                    "BOOT0_S1_PH3": (idr_h >> 3) & 1,
                }

            def assert_afe_pins_safe(pins: dict[str, int], ctx: str):
                assert pins["ANA_EN_PC14"] == 0, f"{ctx}: ANA_EN 非 0! {pins}"
                assert pins["ADS_PWDN_PA1"] == 0, f"{ctx}: ADS_PWDN 非 0! {pins}"
                assert pins["ADS_START_PA3"] == 0, f"{ctx}: ADS_START 非 0! {pins}"
                assert pins["ADS_RESET_PA8"] == 0, f"{ctx}: ADS_RESET 非 0! {pins}"
                assert pins["CS_A_PB0"] == 1 and pins["CS_B_PB1"] == 1, f"{ctx}: CS 非高阻安全态! {pins}"

            def swd_pump_for(sec: float, deliver_rx: bool = True):
                t_end = time.monotonic() + sec
                while time.monotonic() < t_end:
                    if deliver_rx:
                        while not rx_q.empty():
                            rx16 = rx_q.get_nowait()
                            target.write_memory_block8(hil_addr + 24, list(rx16))
                            cur_wr = target.read32(hil_addr + 16)
                            target.write32(hil_addr + 16, cur_wr + 1)
                    h, t = target.read_memory_block32(hil_addr + 8, 2)
                    drained = 0
                    while t < h:
                        idx = t % SLOTS
                        contig = min(h - t, SLOTS - idx)
                        words = target.read_memory_block32(hil_addr + RING_OFF + idx * 280, contig * 70)
                        blk = struct.pack(f"<{len(words)}I", *words)
                        for k in range(contig):
                            tx_q.put(blk[k * 280 : (k + 1) * 280])
                        t += contig
                        drained += contig
                        target.write32(hil_addr + 12, t)
                    if drained == 0:
                        time.sleep(0.0004)

            def wait_tx_drained():
                t0 = time.monotonic()
                while not tx_q.empty() and (time.monotonic() - t0) < 2.0:
                    time.sleep(0.003)
                time.sleep(0.012)

            def read_xiao_status() -> dict:
                raw = xiao.transact("R", bytes([4]))
                assert raw[0] == 0 and len(raw) == 65
                return unpack_ble_status(raw[1:])

            # ------------------------------------------------------------------
            # Case 1d-1: 首包 SESSION_START 断链 -> C08B_FAULT_LINK_DROP (7)
            # ------------------------------------------------------------------
            swd_pump_for(0.08)
            wait_tx_drained()
            st0 = read_xiao_status()
            assert st0["fault"] == 0 and not st0["active"], f"初始状态非干净待机: {st0}"

            # 暂停 USB 转发，在 L432 环缓只留 1 个槽位接收空闲心跳中的 SYN1 启动命令，
            # 随后 4ms 产生的首包 SESSION_START 将立即撞满环缓（模拟 SPI3/LINK_RDY 排线脱落）！
            usb_pause = True
            while not rx_q.empty():
                rx_q.get_nowait()
            h_now = target.read32(hil_addr + 8)
            target.write32(hil_addr + 12, (h_now - (SLOTS - 1)) & 0xFFFFFFFF)
            # C08B_MODE_SYN1 = 6（stream_proto.h）
            syn_cmd = pack_rx_cmd(req_mode=6, nrf_flags=0x04, synth_ch=16, fs_hz=1000, epoch=701)
            target.write_memory_block8(hil_addr + 24, list(syn_cmd))
            cur_wr = target.read32(hil_addr + 16)
            target.write32(hil_addr + 16, cur_wr + 1)

            # 等满 1 次 20ms 心跳 + 4ms 首包生成与断链自停
            time.sleep(0.065)
            h_after = target.read32(hil_addr + 8)
            # 恢复链路并排空假满指针，让 L432 下一次心跳把故障态传给 XIAO
            target.write32(hil_addr + 12, h_after)
            usb_pause = False
            swd_pump_for(0.08, deliver_rx=False)
            wait_tx_drained()

            st_drop = read_xiao_status()
            l432_tx_drop = unpack_tx_header(bytes(target.read_memory_block8(tx_frame_addr, 280)))
            pins_drop = read_l432_afe_pins()
            assert_afe_pins_safe(pins_drop, "Case 1d-1 LINK_DROP")
            assert l432_tx_drop["fault"] == 7 and st_drop["fault"] == 7, (
                f"首包断链未触发 FAULT_LINK_DROP(7): l432={l432_tx_drop}, xiao={st_drop}"
            )
            assert not st_drop["active"] and st_drop["ring_dropped"] == 4, f"LINK_DROP 状态异常: {st_drop}"
            print(
                f"[1d-1 通过] 首包排线脱落注入 -> L432 硬件自停 FAULT_LINK_DROP=7, "
                f"XIAO STATUS.fault={st_drop['fault']}, ring_dropped={st_drop['ring_dropped']}, AFE 引脚全 0"
            )
            report["cases"]["1d_1_session_start_link_drop"] = {
                "l432_tx": l432_tx_drop,
                "xiao_status": st_drop,
                "l432_pins": pins_drop,
            }

            # ------------------------------------------------------------------
            # Case 1d-2: 流中排线阻塞 750ms -> 硬件环缓溢出 + 主机序号缺口必红拦截
            # ------------------------------------------------------------------
            xiao.transact("D")
            swd_pump_for(0.06)
            wait_tx_drained()
            xiao.emg_pkts.clear()
            xiao.imu_pkts.clear()

            # 启动 16CH @ 1000Hz 合成流（裸板无 I2C1 上拉时 imu_setup_stream 首次超时约 0.50s，先泵 0.85s 确认实包出流）
            ctrl_syn16 = b"SYN1" + struct.pack("<HB", 1000, 16)
            assert xiao.transact("W", ctrl_syn16)[0] == 0
            swd_pump_for(0.85)
            wait_tx_drained()
            assert len(xiao.emg_pkts) >= 40, f"阻塞前未进入稳定出流: pkts={len(xiao.emg_pkts)}"
            # 故意停摆 SWD 排空 0.80s（超过 128 槽 × 4 样本 = 512ms 硬件环缓容量，必溢出约 288 样本）
            time.sleep(0.80)
            # 恢复排空 0.30s
            swd_pump_for(0.30)
            wait_tx_drained()

            st_stall = read_xiao_status()
            l432_tx_stall = unpack_tx_header(bytes(target.read_memory_block8(tx_frame_addr, 280)))
            xiao.transact("D")
            swd_pump_for(0.06)
            wait_tx_drained()
            stall_pkts = list(xiao.emg_pkts)
            gap_audit = check_emg_sequence_gaps(stall_pkts)

            assert st_stall["ring_dropped"] >= 150, f"750ms 阻塞未溢出环缓: {st_stall}"
            assert not gap_audit["lossless"], "必败反例失效：硬件丢帧但主机序号检查未报红！"
            assert gap_audit["missing_samples"] == st_stall["ring_dropped"], (
                f"主机缺口样本数 ({gap_audit['missing_samples']}) 与硬件 ring_dropped ({st_stall['ring_dropped']}) 不一致！"
            )
            print(
                f"[1d-2 通过] 流中 750ms 阻塞注入 -> L432/XIAO ring_dropped={st_stall['ring_dropped']}，"
                f"主机序号门当场抓出 {len(gap_audit['gap_events'])} 处缺口、missing_samples={gap_audit['missing_samples']}（精确逐样本吻合）"
            )
            report["cases"]["1d_2_midstream_stall_overflow"] = {
                "xiao_status_before_stop": st_stall,
                "l432_tx": l432_tx_stall,
                "host_gap_audit": gap_audit,
            }

            # ------------------------------------------------------------------
            # Case 1d-3: 跨核 VBUS_INTERLOCK(0x01)|OE_OFF(0x02) 传播 + 6 种真采指令双锁拦截
            # ------------------------------------------------------------------
            real_modes = [
                ("TST1", 1), ("SHT1", 2), ("EXT1", 3),
                ("EXR1", 5), ("RLD1", 7), ("PRB1", 8),
            ]
            interlock_records = []
            usb_pause = True
            while not rx_q.empty():
                rx_q.get_nowait()
            for idx, (mname, mcode) in enumerate(real_modes):
                cmd16 = pack_rx_cmd(
                    req_mode=mcode,
                    nrf_flags=0x03,  # C08B_NF_VBUS_INTERLOCK | C08B_NF_OE_OFF
                    synth_ch=16,
                    fs_hz=1000,
                    epoch=800 + idx,
                )
                target.write_memory_block8(hil_addr + 24, list(cmd16))
                cur_wr = target.read32(hil_addr + 16)
                target.write32(hil_addr + 16, cur_wr + 1)
                time.sleep(0.035)
                # 清空心跳槽保持畅通
                h_cur = target.read32(hil_addr + 8)
                target.write32(hil_addr + 12, h_cur)
                time.sleep(0.025)
                h_cur2 = target.read32(hil_addr + 8)
                target.write32(hil_addr + 12, h_cur2)

                last_rx_raw = bytes(target.read_memory_block8(last_rx_addr, 16))
                rx_magic, rx_ver, rx_mode, rx_nflags, _sch, _fs, rx_ep, _rsv, _crc = struct.unpack("<HBBBBHIHH", last_rx_raw)
                tx_hdr = unpack_tx_header(bytes(target.read_memory_block8(tx_frame_addr, 280)))
                pins = read_l432_afe_pins()
                assert_afe_pins_safe(pins, f"Case 1d-3 {mname}")
                assert rx_magic == 0x53C8 and rx_mode == mcode and rx_nflags == 0x03, (
                    f"L432 未锁存跨核互锁位: mode={rx_mode}, flags=0x{rx_nflags:02X}"
                )
                assert tx_hdr["fault"] == 1 and tx_hdr["active_mode"] == 0, f"{mname} 未被编译期安全锁拦截: {tx_hdr}"
                interlock_records.append({
                    "mode": mname,
                    "l432_latched_nrf_flags_hex": f"0x{rx_nflags:02X}",
                    "l432_fault": tx_hdr["fault"],
                    "l432_vbus_flag": bool(tx_hdr["state_flags"] & 0x04),
                    "ph3_boot0_pad": pins["BOOT0_S1_PH3"],
                    "ana_en_pc14": pins["ANA_EN_PC14"],
                })
            usb_pause = False
            swd_pump_for(0.06, deliver_rx=False)
            wait_tx_drained()
            print(
                f"[1d-3 通过] 跨核 VBUS_INTERLOCK|OE_OFF (0x03) 注入 6/6 真采指令 -> "
                f"L432 实测锁存 nrf_flags=0x03、返回 FAULT_LOCKED=1、PH3={interlock_records[0]['ph3_boot0_pad']}、ANA_EN 全程 0"
            )
            report["cases"]["1d_3_vbus_interlock_and_lock_matrix"] = interlock_records

            # ------------------------------------------------------------------
            # Case 1d-4: 采集中断连 ('D') 干净停机 + 无丢包基线流 + 主机 connects+1 防拼接必败门
            # ------------------------------------------------------------------
            xiao.emg_pkts.clear()
            xiao.imu_pkts.clear()
            xiao.link_frames.clear()
            assert xiao.transact("W", ctrl_syn16)[0] == 0
            swd_pump_for(0.85)
            wait_tx_drained()
            st_mid = read_xiao_status()
            assert st_mid["active"] and st_mid["ring_dropped"] == 0, f"干净基线流异常: {st_mid}"

            # 流中发 'D' 模拟 BLE 断开收尾
            assert xiao.transact("D")[0] == 0
            swd_pump_for(0.08)
            wait_tx_drained()
            st_after_d = read_xiao_status()
            pins_after_d = read_l432_afe_pins()
            assert_afe_pins_safe(pins_after_d, "Case 1d-4 after D")
            assert not st_after_d["active"], f"'D' 断连后仍在采集中: {st_after_d}"

            clean_pkts = list(xiao.emg_pkts)
            clean_audit = check_emg_sequence_gaps(clean_pkts)
            assert clean_audit["lossless"] and clean_audit["received_samples"] >= 120, f"干净流审核未过: {clean_audit}"

            # 确认停机后继续泵 0.10s 不再产生任何残留包
            cnt_stopped = len(xiao.emg_pkts)
            swd_pump_for(0.10)
            wait_tx_drained()
            assert len(xiao.emg_pkts) == cnt_stopped, "停机后仍有残留 EMG 包发出！"

            assert xiao.transact("Q")[0] == 0
            time.sleep(0.03)
            assert len(xiao.link_frames) >= 1 and len(xiao.link_frames[-1]) == 26

            # 主机侧 C08BRig 丢包核验 + connects+1 防拼接必败门 + C11 解锁态互锁核验
            host_redlines = run_host_gates_and_antisplice(stall_pkts, clean_pkts)
            print(
                f"[1d-4 通过] 流中断连 'D' 干净停机（残留包=0, lossless 样本={clean_audit['received_samples']}）+ "
                f"主机 connects+1 必败反例拦截: {host_redlines['anti_splice']['error']}"
            )
            report["cases"]["1d_4_disconnect_and_antisplice"] = {
                "status_mid_stream": st_mid,
                "status_after_disconnect": st_after_d,
                "clean_stream_audit": clean_audit,
                "host_redlines": host_redlines,
            }

            usb_stop = True
            u_thr.join(timeout=1.0)
    finally:
        usb_stop = True
        xiao.close()

    report["all_passed"] = True
    OUT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"=== T1-d 全部 4 大项正反例实测通过，证据已写入 {OUT_JSON} ===")


if __name__ == "__main__":
    main()

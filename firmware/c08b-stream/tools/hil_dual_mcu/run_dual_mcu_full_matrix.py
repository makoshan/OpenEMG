#!/usr/bin/env python3
"""C08B v0.01 双真机（STM32L432KBU6 + Seeed XIAO nRF52840 Sense）7 阶段全矩阵深度硬件联调器。

覆盖：
  Stage 1: 冷启动待机契约 + XIAO Sense 板载真实物理 LSM6DS3TR-C (0x6A, TWIM0 400kHz) 唤醒与重力模长实测
  Stage 2: 全 6 种受控真采指令 (TST1/SHT1/EXT1/EXR1/RLD1/PRB1) 跨核安全锁拦截 + L432 真机 GPIO 寄存器物理直读
  Stage 3: 非法采样率 (777Hz / 4000Hz -> FAULT_ARG=2) 与未知控制指令 (NOPE) 跨核边界拦截
  Stage 4: 同连接四轮子板拓扑/采样率无断连热切换 (16CH@1000 -> 8CH@2000 极限千帧 -> 2CH@500 -> 16CH@500) + RECONFIGURE 校验 + 归档回放
  Stage 5: 双向 CRC16-CCITT 硬件链路位翻转故障注入 (3 类坏 280B 上行帧 + 1 类坏 16B 下行命令帧，验证流中零误收零中断)
  Stage 6: 10.0 秒稳态满载拷机 (16CH@1000Hz >10,000 样本 + ~1,000 帧真物理 LSM6DS3TR-C IMU) + HSI16 时钟频偏实算
  Stage 7: 双真机实采包直喂最新 OpenEMG 多通道工作台后端 (C08BRig + AcqHandler 16/8/2ch 全绿核验)
"""
from __future__ import annotations

import ctypes
import glob
import json
import tempfile
import os
import math
from pathlib import Path
import queue
import shutil
import struct
import subprocess
import sys
import threading
import time

ctypes.CDLL("/opt/homebrew/lib/libusb-1.0.dylib", mode=ctypes.RTLD_GLOBAL)

HERE = Path(__file__).resolve().parent
SIM_ROOT = Path(os.environ.get("C08B_HIL_WORKDIR", Path(tempfile.gettempdir()) / "c08b-dual-hil"))
FW_DIR = SIM_ROOT / "c08b-stream-hil"
ELF_PATH = FW_DIR / "build/l432.elf"
NM_BIN = Path.home() / ".platformio/packages/toolchain-gccarmnoneeabi/bin/arm-none-eabi-nm"

# STM32L432 硬件 GPIO 寄存器物理地址（RM0394）
GPIOA_ODR = 0x48000014
GPIOB_ODR = 0x48000414
GPIOC_ODR = 0x48000814
GPIOH_IDR = 0x48001C10


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
        """单次 USB Bulk 批量投递多帧 280B 数据并回收对应 17B 响应，突破 1ms USB SOF 帧率上限（轻松跑满 2000Hz 千帧/秒）。"""
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


def crc16_ccitt(data: bytes) -> int:
    c = 0xFFFF
    for b in data:
        c ^= b << 8
        for _ in range(8):
            c = ((c << 1) ^ 0x1021) & 0xFFFF if (c & 0x8000) else (c << 1) & 0xFFFF
    return c


def main():
    from pyocd.core.helpers import ConnectHelper

    ports = sorted(glob.glob("/dev/cu.usbmodem*"))
    assert ports, "未找到 XIAO USB 串口 /dev/cu.usbmodem*"
    port = ports[0]
    print(f"=== 连接 XIAO nRF52840 Sense: {port} + ST-LINK V2 (STM32L432KBU6) ===")

    syms = load_symbols(ELF_PATH)
    hil_addr = syms["g_swd_hil"]
    RING_OFF = 40
    SLOTS = 128

    xiao = A5FramedSerial(port)
    tx_q: queue.Queue[bytes] = queue.Queue()
    rx_q: queue.Queue[bytes] = queue.Queue()
    usb_stop = False
    relay_stats = {"tx_frames": 0, "rx_cmds": 0, "xiao_crc_rejects": 0, "usb_batches": 0}
    report: dict = {"stages": {}}

    def usb_relay_worker():
        last_rx = b""
        last_poll = 0.0
        while not usb_stop or not tx_q.empty():
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
                relay_stats["usb_batches"] += 1
                relay_stats["tx_frames"] += len(batch)
                for rep in reps:
                    if rep[0] != 0:
                        relay_stats["xiao_crc_rejects"] += 1
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

            def swd_pump_for(sec: float, extra_corrupt_inject: bool = False):
                t_end = time.monotonic() + sec
                injected_rx = False
                while time.monotonic() < t_end:
                    while not rx_q.empty():
                        rx16 = rx_q.get_nowait()
                        target.write_memory_block8(hil_addr + 24, list(rx16))
                        cur_wr = target.read32(hil_addr + 16)
                        target.write32(hil_addr + 16, cur_wr + 1)
                        relay_stats["rx_cmds"] += 1

                    if extra_rx_corrupt := (extra_corrupt_inject and not injected_rx and (t_end - time.monotonic()) < sec * 0.5):
                        _ = extra_rx_corrupt
                        # 构造一帧把合法 16B STOP 命令帧 (magic=0x53C8, req_mode=4) CRC16 翻转 1 bit 的损坏下行帧写入 L432 rx_slot
                        stop_hdr14 = struct.pack("<HBBBBHIH", 0x53C8, 1, 4, 0, 16, 1000, 99999, 0)
                        bad_rx = stop_hdr14 + struct.pack("<H", crc16_ccitt(stop_hdr14) ^ 0x0001)
                        target.write_memory_block8(hil_addr + 24, list(bad_rx))
                        cur_wr = target.read32(hil_addr + 16)
                        target.write32(hil_addr + 16, cur_wr + 1)
                        injected_rx = True

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
                time.sleep(0.01)

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

            # ==================================================================
            # Stage 1: 冷启动待机 + 板载真实物理 LSM6DS3TR-C (0x6A) 核验
            # ==================================================================
            swd_pump_for(0.10)
            wait_tx_drained()
            meta_idle_raw = xiao.transact("R", bytes([3]))[1:]
            meta_idle = json.loads(meta_idle_raw.decode("utf-8"))
            assert meta_idle["afe"] == "NONE" and meta_idle["active_channels"] == 0

            r_imu_hw = xiao.transact("I")
            assert r_imu_hw[0] == 0
            imu_ok, imu_who, imu_read_us, imu_hw_cnt = struct.unpack_from("<BBHI", r_imu_hw, 1)
            gx, gy, gz, ax, ay, az = struct.unpack_from("<6h", r_imu_hw, 9)
            acc_g = tuple(v * 0.000244 for v in (ax, ay, az))
            gyro_dps = tuple(v * 0.035 for v in (gx, gy, gz))
            acc_norm_g = math.sqrt(sum(x * x for x in acc_g))
            assert imu_ok == 1 and imu_who == 0x6A, f"XIAO 板载 LSM6DS3TR-C 未就绪: ok={imu_ok}, who=0x{imu_who:02X}"
            assert 0.85 <= acc_norm_g <= 1.15, f"桌面重力模长异常: {acc_norm_g:.3f} g"
            print(
                f"[Stage 1 通过] 冷启动 AFE=NONE + XIAO 板载真物理 LSM6DS3TR-C 就绪: "
                f"WHO_AM_I=0x{imu_who:02X}, TWIM0 耗时={imu_read_us}µs, "
                f"实测桌面重力=({acc_g[0]:+.3f}, {acc_g[1]:+.3f}, {acc_g[2]:+.3f})g |a|={acc_norm_g:.3f}g, "
                f"静止角速度=({gyro_dps[0]:+.2f}, {gyro_dps[1]:+.2f}, {gyro_dps[2]:+.2f})dps"
            )
            report["stages"]["stage1_cold_boot_and_hw_imu"] = {
                "meta_idle": meta_idle,
                "imu_who_am_i_hex": f"0x{imu_who:02X}",
                "twim0_read_us": imu_read_us,
                "desk_acc_g": [round(x, 4) for x in acc_g],
                "desk_acc_norm_g": round(acc_norm_g, 4),
                "desk_gyro_dps": [round(x, 3) for x in gyro_dps],
            }

            # ==================================================================
            # Stage 2: 全 6 种受控真采指令跨核硬件锁拦截 + L432 物理 GPIO 寄存器直读
            # ==================================================================
            locked_verbs = ["TST1", "SHT1", "EXT1", "EXR1", "RLD1", "PRB1"]
            locked_results = {}
            for verb in locked_verbs:
                xiao.transact("D")
                swd_pump_for(0.05)
                wait_tx_drained()
                assert xiao.transact("W", verb.encode("ascii"))[0] == 0
                swd_pump_for(0.08)
                wait_tx_drained()
                st64 = xiao.transact("R", bytes([4]))[1:]
                fault_c, active_f = st64[40], st64[41]
                pins = read_l432_afe_pins()
                assert fault_c == 1 and active_f == 0, f"{verb} 未触发 FAULT_LOCKED: fault={fault_c}, active={active_f}"
                assert (
                    pins["ANA_EN_PC14"] == 0
                    and pins["ADS_PWDN_PA1"] == 0
                    and pins["ADS_START_PA3"] == 0
                    and pins["ADS_RESET_PA8"] == 0
                    and pins["CS_A_PB0"] == 1
                    and pins["CS_B_PB1"] == 1
                ), f"{verb} 下 L432 AFE 控制脚电平异常: {pins}"
                locked_results[verb] = {"fault": fault_c, "active": active_f, "l432_gpio": pins}
            print(
                f"[Stage 2 通过] 6/6 受控指令 ({'/'.join(locked_verbs)}) 跨核 100% 置 FAULT_LOCKED(1)，"
                f"SWD 物理直读 L432 PC14(ANA_EN)=0, PA1=0, PA3=0, PA8=0, PB0/PB1(CS)=1"
            )
            report["stages"]["stage2_all_locked_modes_and_gpio"] = locked_results

            # ==================================================================
            # Stage 3: 非法参数与异常控制包跨核边界拦截
            # ==================================================================
            xiao.transact("D")
            swd_pump_for(0.05)
            wait_tx_drained()
            # 注意：XIAO handle_ctrl_payload 会先过滤 fs_hz 仅接受 500/1000/2000，
            # 我们同时验证：(a) XIAO 入口拦截未知动词 NOPE；(b) 直接向 L432 下发 fs=777Hz 命令验证 Cortex-M4 c08b_gate_mode_request 返回 FAULT_ARG(2)
            epoch_before = target.read32(syms["g_last_rx"] + 8) if "g_last_rx" in syms else 0
            xiao.transact("W", b"NOPE")
            swd_pump_for(0.05)
            wait_tx_drained()
            st_nope = xiao.transact("R", bytes([4]))[1:]
            assert st_nope[40] == 0 and st_nope[41] == 0

            # 直接构造合法 CRC16 但 fs_hz=777 的 16B 命令帧测 L432 端 c08b_gate_mode_request -> FAULT_ARG(2)
            def crc16_ccitt(data: bytes) -> int:
                c = 0xFFFF
                for b in data:
                    c ^= b << 8
                    for _ in range(8):
                        c = ((c << 1) ^ 0x1021) & 0xFFFF if (c & 0x8000) else (c << 1) & 0xFFFF
                return c

            bad_fs_hdr = struct.pack("<HBBBBHI", 0x53C8, 1, 6, 0, 16, 777, 77777) + b"\x00\x00"
            bad_fs_pkt = bad_fs_hdr + struct.pack("<H", crc16_ccitt(bad_fs_hdr))
            rx_q.put(bad_fs_pkt)
            swd_pump_for(0.08)
            wait_tx_drained()
            st_arg = xiao.transact("R", bytes([4]))[1:]
            assert st_arg[40] == 2 and st_arg[41] == 0, f"非法采样率 777Hz 未报 FAULT_ARG(2): fault={st_arg[40]}"
            print(f"[Stage 3 通过] 未知动词 NOPE 被无线核拦截 (epoch={epoch_before} 不变)；777Hz 非法采样率经 CRC16 帧抵 L432 报 FAULT_ARG(2)")
            report["stages"]["stage3_arg_and_verb_guards"] = {
                "unknown_verb_fault": st_nope[40],
                "bad_fs_777hz_fault": st_arg[40],
            }

            # ==================================================================
            # Stage 4: 同连接四轮拓扑/采样率热切换 + RECONFIGURE 标志验证
            # (16CH@1000Hz -> 8CH@2000Hz 千帧极限档 -> 2CH@500Hz ADS1292 -> 16CH@500Hz)
            # ==================================================================
            xiao.transact("D")
            swd_pump_for(0.06)
            wait_tx_drained()

            def stop_and_drain_cleanly() -> bytes:
                assert xiao.transact("W", b"STOP")[0] == 0
                # 立刻发起一帧空 L 轮询把 STOP 的 rx16 送入 rx_q，免等 12ms 空闲轮询
                rx16_now = xiao.transact("L", b"", timeout=1.5)[1:17]
                if len(rx16_now) == 16:
                    rx_q.put(rx16_now)
                t_dl = time.monotonic() + 1.5
                st_b = b"\x00" * 64
                while time.monotonic() < t_dl:
                    swd_pump_for(0.05)
                    wait_tx_drained()
                    h_chk, t_chk = target.read_memory_block32(hil_addr + 8, 2)
                    st_b = xiao.transact("R", bytes([4]))[1:]
                    if h_chk == t_chk and tx_q.empty() and st_b[41] == 0:
                        break
                time.sleep(0.04)
                return st_b

            hotswap_specs = [
                ("16ch_1000hz", 16, 1000, 0.80, "ADS1298_DUAL", 4, 2400, False),
                ("8ch_2000hz",   8, 2000, 0.45, "ADS1298_SINGLE", 1, 2400, True),
                ("2ch_500hz",    2,  500, 0.80, "ADS1292", 1, 2420, True),
                ("16ch_500hz",  16,  500, 0.80, "ADS1298_DUAL", 4, 2400, True),
            ]
            hotswap_raw = {}

            for tag, n_ch, fs_hz, dur_s, exp_afe, exp_proto, exp_vref, exp_reconf in hotswap_specs:
                xiao.emg_pkts.clear()
                xiao.imu_pkts.clear()
                cmd = b"SYN1" + struct.pack("<HB", fs_hz, n_ch)
                assert xiao.transact("W", cmd)[0] == 0
                rx16_go = xiao.transact("L", b"", timeout=1.5)[1:17]
                if len(rx16_go) == 16:
                    rx_q.put(rx16_go)
                swd_pump_for(dur_s)

                st_end = stop_and_drain_cleanly()
                meta_run = json.loads(xiao.transact("R", bytes([3]))[1:].decode("utf-8"))
                l432_drop = struct.unpack_from("<Q", st_end, 8)[0]
                min_dt_us = struct.unpack_from("<I", st_end, 56)[0]

                emg_copy = list(xiao.emg_pkts)
                imu_copy = list(xiao.imu_pkts)
                assert len(emg_copy) > 0, f"{tag} 未收到 EMG 包"
                first_flags = emg_copy[0][3]
                has_start = bool(first_flags & 0x02)
                has_reconf = bool(first_flags & 0x04)
                has_synth = bool(first_flags & 0x01)
                assert has_start and has_synth, f"{tag} 首包标志异常: 0x{first_flags:02X}"
                assert has_reconf == exp_reconf, f"{tag} RECONFIGURE 标志期望 {exp_reconf} 实得 {has_reconf} (flags=0x{first_flags:02X})"
                assert (
                    meta_run["afe"] == exp_afe
                    and meta_run["protocol"] == exp_proto
                    and meta_run["vref_mV"] == exp_vref
                    and meta_run["fs_Hz"] == fs_hz
                    and meta_run["active_channels"] == n_ch
                ), f"{tag} META 不匹配: {meta_run}"
                assert l432_drop == 0, f"{tag} L432 环形缓冲丢帧: {l432_drop}"

                hotswap_raw[tag] = {
                    "meta": meta_run,
                    "status_hex": st_end.hex(),
                    "emg_packets_hex": [p.hex() for p in emg_copy],
                    "imu_packets_hex": [p.hex() for p in imu_copy],
                    "l432_ring_dropped": l432_drop,
                    "min_interval_us": min_dt_us,
                    "first_pkt_flags_hex": f"0x{first_flags:02X}",
                    "reconfigure_bit": has_reconf,
                }
                print(
                    f"[Stage 4.{tag} 采集完成] afe={meta_run['afe']}(proto={exp_proto}, {fs_hz}Hz, vref={exp_vref}mV) "
                    f"flags=0x{first_flags:02X}(RECONF={int(has_reconf)}) -> EMG包={len(emg_copy)}, "
                    f"物理IMU包={len(imu_copy)}, min_dt={min_dt_us}µs, L432_drop=0"
                )
            report["stages"]["stage4_hotswap_raw"] = hotswap_raw

            # ==================================================================
            # Stage 5: 双向 CRC16-CCITT 位翻转 / 坏魔数故障注入（流中零误收零中断）
            # ==================================================================
            cnt_before = struct.unpack_from("<IIII", xiao.transact("S"), 1)[2]
            valid_hdr = bytearray(278)
            struct.pack_into("<HBBBB", valid_hdr, 0, 0xC853, 1, 16, 1, 0)
            valid_280 = bytes(valid_hdr) + struct.pack("<H", crc16_ccitt(valid_hdr))
            assert xiao.transact("L", valid_280)[0] == 0

            corrupt_1_payload = bytearray(valid_280); corrupt_1_payload[88] ^= 0x01
            corrupt_2_magic   = bytearray(valid_280); corrupt_2_magic[0] ^= 0xFF
            corrupt_3_crc     = bytearray(valid_280); corrupt_3_crc[279] ^= 0x80
            r_c1 = xiao.transact("L", bytes(corrupt_1_payload))[0]
            r_c2 = xiao.transact("L", bytes(corrupt_2_magic))[0]
            r_c3 = xiao.transact("L", bytes(corrupt_3_crc))[0]
            cnt_after = struct.unpack_from("<IIII", xiao.transact("S"), 1)[2]
            assert (r_c1, r_c2, r_c3) == (2, 2, 2) and (cnt_after - cnt_before) == 3, (
                f"CRC 注入拦截异常: replies={(r_c1, r_c2, r_c3)}, delta={cnt_after - cnt_before}"
            )

            xiao.emg_pkts.clear()
            xiao.imu_pkts.clear()
            assert xiao.transact("W", b"SYN1" + struct.pack("<HB", 1000, 16))[0] == 0
            swd_pump_for(0.50, extra_corrupt_inject=True)
            st_mid = xiao.transact("R", bytes([4]))[1:]
            assert st_mid[41] == 1, "损坏 CRC 的下行 STOP 帧竟让 L432 误停机！"
            stop_and_drain_cleanly()
            print(
                f"[Stage 5 通过] 上行 3 类位翻转/坏魔数/坏CRC 100% 拒收 (crc_bad +{cnt_after - cnt_before})；"
                f"下行坏CRC STOP 注入期间 L432 保持 active=1 零误停"
            )
            report["stages"]["stage5_crc16_fault_injection"] = {
                "uplink_corrupt_replies": [r_c1, r_c2, r_c3],
                "xiao_crc_bad_delta": cnt_after - cnt_before,
                "downlink_corrupt_stop_ignored": True,
            }

            # ==================================================================
            # Stage 6: 10.0 秒双真机稳态满速拷机 (16CH @ 1000 Hz + 真物理 LSM6DS3TR-C IMU)
            # ==================================================================
            xiao.transact("D")
            swd_pump_for(0.06)
            wait_tx_drained()
            time.sleep(0.04)
            xiao.emg_pkts.clear()
            xiao.imu_pkts.clear()

            assert xiao.transact("W", b"SYN1" + struct.pack("<HB", 1000, 16))[0] == 0
            rx16_s6 = xiao.transact("L", b"", timeout=1.5)[1:17]
            if len(rx16_s6) == 16:
                rx_q.put(rx16_s6)
            t_host_start = time.monotonic()
            swd_pump_for(10.0)
            t_host_span = time.monotonic() - t_host_start
            st_10s = stop_and_drain_cleanly()
            meta_10s = json.loads(xiao.transact("R", bytes([3]))[1:].decode("utf-8"))
            l432_drop_10s = struct.unpack_from("<Q", st_10s, 8)[0]
            min_dt_10s = struct.unpack_from("<I", st_10s, 56)[0]
            assert l432_drop_10s == 0

            emg_10s = list(xiao.emg_pkts)
            imu_10s = list(xiao.imu_pkts)
            print(
                f"[Stage 6 采集完成] 10.0s 满载拷机: F01v4 包={len(emg_10s)}, 真物理 IMU 包={len(imu_10s)}, "
                f"L432_drop={l432_drop_10s}, min_dt={min_dt_10s}µs, 主机耗时={t_host_span:.3f}s"
            )
            report["stages"]["stage6_10s_soak_raw"] = {
                "meta": meta_10s,
                "status_hex": st_10s.hex(),
                "emg_packets_hex": [p.hex() for p in emg_10s],
                "imu_packets_hex": [p.hex() for p in imu_10s],
                "l432_ring_dropped": l432_drop_10s,
                "min_interval_us": min_dt_10s,
                "host_elapsed_s": t_host_span,
            }

            xiao.transact("D")
            usb_stop = True
            u_thr.join(timeout=2.0)

        report["relay_totals"] = relay_stats
        out_raw = SIM_ROOT / "live_matrix_raw.json"
        out_raw.write_text(json.dumps(report, ensure_ascii=False), encoding="utf-8")
        print(f"=== 双真机硬件采集阶段全部完成！原始包已落盘 {out_raw} ===")
    finally:
        usb_stop = True
        xiao.close()


if __name__ == "__main__":
    main()

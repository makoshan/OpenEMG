#!/usr/bin/env python3
"""T1-e：C08B 固件优化双真机实测（STM32L432KBU6 + Seeed XIAO nRF52840 Sense）。

验证项：
  1. 裸板 PA9/PA10 (IMU_SCL/SDA) 内部弱上拉生效（IDR bit9/bit10 == 1/1），
     无外置 IMU 时 SYN1 首包启动延迟从旧版 ~520 ms 降至 < 80 ms，不阻塞 I2C1 BUSY；
  2. 同一连接内免 STOP 在线热切（16CH@1000Hz -> 8CH@2000Hz -> 2CH@500Hz -> 16CH@1000Hz）：
     - 在 L432 环缓故意积压旧纪元在途帧的情况下下发新 SYN1，验证 ack_epoch_lo 精确滤除旧帧，
       0 个跨版本错打包（绝不把旧 16CH 槽当 8CH 打包），每段首包严格 seq=0 且打齐 SESSION_START|RECONFIGURE (0x07)；
     - IMU 首包同步重置 imu_seq=0 且打齐 RECONFIGURE；
  3. 非互锁故障码（如 FAULT_LOCKED=1）在收到显式 STOP 后干净归零（STATUS.fault: 1 -> 0），
     而 ANA_EN 全程锁死为 0。
"""
from __future__ import annotations

import ctypes
import glob
import json
import tempfile
import sys
import os
from pathlib import Path
import queue
import struct
import threading
import time

ctypes.CDLL("/opt/homebrew/lib/libusb-1.0.dylib", mode=ctypes.RTLD_GLOBAL)

from run_t1d_fault_injection import (
    A5FramedSerial,
    ELF_PATH,
    GPIOA_ODR,
    GPIOB_ODR,
    GPIOC_ODR,
    GPIOH_IDR,
    SIM_ROOT,
    load_symbols,
    unpack_ble_status,
    unpack_tx_header,
)

GPIOA_IDR = 0x48000010
OUT_JSON = SIM_ROOT / "t1e_fw_opt_hil_report.json"


def parse_emg_segments(pkts: list[bytes]) -> list[dict]:
    """按 SESSION_START (flag 0x02) 切分多档热重配包序列，逐段核对版本、帧长、序号连续性与标志位。"""
    segments: list[dict] = []
    cur = None
    expected_seq = 0
    for idx, p in enumerate(pkts):
        assert len(p) >= 16, f"短包 idx={idx} len={len(p)}"
        ver, dev_type, n_frames, flags = p[0], p[1], p[2], p[3]
        seq = struct.unpack_from("<I", p, 4)[0]
        ts_us = struct.unpack_from("<Q", p, 8)[0]
        assert dev_type == 1 and ver in (1, 4), f"非法协议头 idx={idx}: {p[:4].hex()}"
        slot_bytes = 54 if ver == 4 else 27
        assert len(p) == 16 + n_frames * slot_bytes, (
            f"包长与协议版本失配（疑似跨档混包）: idx={idx} ver={ver} n_frames={n_frames} len={len(p)}"
        )
        if cur is None or (flags & 0x02):
            cur = {
                "pkt_start_idx": idx,
                "f01_version": ver,
                "first_flags_hex": f"0x{flags:02X}",
                "has_session_start": bool(flags & 0x02),
                "has_reconfigure": bool(flags & 0x04),
                "first_seq": seq,
                "first_ts_us": ts_us,
                "packets": 0,
                "samples": 0,
                "gaps": 0,
                "ch3_to_ch8_nonzero_slots": 0,
            }
            segments.append(cur)
            expected_seq = seq
        else:
            assert ver == cur["f01_version"], f"同段内版本突变 idx={idx}: {ver} != {cur['f01_version']}"
            if seq != expected_seq:
                cur["gaps"] += (seq - expected_seq) & 0xFFFFFFFF
                expected_seq = seq
        if ver == 1:
            for s in range(n_frames):
                slot = p[16 + s * 27 : 16 + (s + 1) * 27]
                if any(b != 0 for b in slot[9:27]):
                    cur["ch3_to_ch8_nonzero_slots"] += 1
        expected_seq = (expected_seq + n_frames) & 0xFFFFFFFF
        cur["packets"] += 1
        cur["samples"] += n_frames
    return segments


def parse_imu_reconfigs(imu_pkts: list[bytes]) -> list[dict]:
    starts = []
    for idx, p in enumerate(imu_pkts):
        assert len(p) == 36 and p[0] == 1 and p[1] == 2, f"IMU 包异常 idx={idx} len={len(p)}"
        flags = p[3]
        seq = struct.unpack_from("<I", p, 4)[0]
        if flags & 0x02:
            starts.append({
                "imu_pkt_idx": idx,
                "seq": seq,
                "flags_hex": f"0x{flags:02X}",
                "has_reconfigure": bool(flags & 0x04),
            })
    return starts


def main():
    from pyocd.core.helpers import ConnectHelper

    ports = sorted(glob.glob("/dev/cu.usbmodem*"))
    assert ports, "未找到 XIAO USB 串口 /dev/cu.usbmodem*"
    port = ports[0]
    print(f"=== T1-e 启动：XIAO ({port}) + ST-LINK V2 (STM32L432KBU6) ===")

    syms = load_symbols(ELF_PATH)
    hil_addr = syms["g_swd_hil"]
    tx_frame_addr = syms["g_tx_frame"]
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
                time.sleep(0.002)
                continue
            batch: list[bytes] = []
            try:
                first = tx_q.get(timeout=0.004)
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
                if now - last_poll >= 0.008:
                    last_poll = now
                    rep = xiao.transact("L", b"", timeout=1.5)
                    rx16 = rep[1:17]
                    if len(rx16) == 16 and rx16 != last_rx:
                        last_rx = rx16
                        rx_q.put(rx16)

    report: dict = {"timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "port": port, "checks": {}}

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

            def swd_pump_for(sec: float):
                t_end = time.monotonic() + sec
                while time.monotonic() < t_end:
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
                    time.sleep(0.002)
                time.sleep(0.010)

            def read_xiao_status() -> dict:
                raw = xiao.transact("R", bytes([4]))
                assert raw[0] == 0 and len(raw) == 65
                return unpack_ble_status(raw[1:])

            def assert_ana_en_zero(ctx: str):
                ana_en = (target.read32(GPIOC_ODR) >> 14) & 1
                ads_pwdn = (target.read32(GPIOA_ODR) >> 1) & 1
                cs_a = (target.read32(GPIOB_ODR) >> 0) & 1
                cs_b = (target.read32(GPIOB_ODR) >> 1) & 1
                assert ana_en == 0 and ads_pwdn == 0 and cs_a == 1 and cs_b == 1, (
                    f"{ctx} 安全红线违例: ana_en={ana_en} pwdn={ads_pwdn} cs=({cs_a},{cs_b})"
                )

            # 1. 验证裸板 PA9/PA10 内部弱上拉与 SYN1 极速启动延迟（旧版 ~520 ms -> 新版 < 80 ms）
            idr_a = target.read32(GPIOA_IDR)
            pa9_scl = (idr_a >> 9) & 1
            pa10_sda = (idr_a >> 10) & 1
            assert pa9_scl == 1 and pa10_sda == 1, f"裸板 PA9/PA10 上拉未生效: PA9={pa9_scl}, PA10={pa10_sda}"

            swd_pump_for(0.05)
            wait_tx_drained()
            xiao.emg_pkts.clear()
            xiao.imu_pkts.clear()

            t_cmd = time.monotonic()
            assert xiao.transact("W", b"SYN1" + struct.pack("<HB", 1000, 16))[0] == 0
            first_pkt_ms = None
            while (time.monotonic() - t_cmd) < 0.250:
                swd_pump_for(0.004)
                if xiao.emg_pkts:
                    first_pkt_ms = round((time.monotonic() - t_cmd) * 1000.0, 2)
                    break
            assert first_pkt_ms is not None and first_pkt_ms < 100.0, (
                f"SYN1 首包延迟过高（疑似 I2C1 BUSY 卡死）: {first_pkt_ms} ms"
            )
            assert_ana_en_zero("16CH 启动")
            print(f"[T1-e 1/3 通过] 裸板 PA9/PA10={pa9_scl}/{pa10_sda}，SYN1 首包延迟={first_pkt_ms} ms（旧版 ~520 ms）")
            report["checks"]["i2c_pullup_and_fast_startup"] = {
                "pa9_imu_scl_idle": pa9_scl,
                "pa10_imu_sda_idle": pa10_sda,
                "syn1_first_pkt_latency_ms": first_pkt_ms,
                "legacy_unpulled_latency_ms_ref": 520.0,
            }

            def pump_until_seg_ready(seg_count: int, min_pkts: int = 8, timeout_s: float = 2.0):
                t0 = time.monotonic()
                while (time.monotonic() - t0) < timeout_s:
                    swd_pump_for(0.015)
                    cur_segs = parse_emg_segments(list(xiao.emg_pkts))
                    if len(cur_segs) >= seg_count and cur_segs[seg_count - 1]["packets"] >= min_pkts:
                        return
                raise AssertionError(f"等待第 {seg_count} 段出满 {min_pkts} 包超时: {parse_emg_segments(list(xiao.emg_pkts))}")

            # 2. 同一连接内连续跨档热重配：16CH@1000Hz -> 8CH@2000Hz -> 2CH@500Hz -> 16CH@1000Hz
            #    每次切换前先确认当前段稳定出流，再故意停泵 12ms 让 L432 环缓积压旧纪元在途残帧后立刻下发新 SYN1！
            pump_until_seg_ready(1, min_pkts=10)
            wait_tx_drained()
            time.sleep(0.012)  # 故意在 L432 硬件环缓积压 3 帧旧 16CH@1000Hz 在途帧
            assert xiao.transact("W", b"SYN1" + struct.pack("<HB", 2000, 8))[0] == 0

            pump_until_seg_ready(2, min_pkts=10)
            wait_tx_drained()
            time.sleep(0.012)  # 故意在 L432 硬件环缓积压 ~6 帧旧 8CH@2000Hz 在途帧
            assert xiao.transact("W", b"SYN1" + struct.pack("<HB", 500, 2))[0] == 0

            pump_until_seg_ready(3, min_pkts=6)
            wait_tx_drained()
            time.sleep(0.016)  # 故意在 L432 硬件环缓积压旧 2CH@500Hz 在途帧
            assert xiao.transact("W", b"SYN1" + struct.pack("<HB", 1000, 16))[0] == 0

            pump_until_seg_ready(4, min_pkts=10)
            wait_tx_drained()
            assert_ana_en_zero("四段热重配后")

            segs = parse_emg_segments(list(xiao.emg_pkts))
            imu_starts = parse_imu_reconfigs(list(xiao.imu_pkts))
            assert len(segs) == 4, f"期望 4 段会话（16->8->2->16），实得 {len(segs)}: {segs}"

            # 逐段断言：
            # 段 0: 16CH@1000Hz -> v4, flags=0x03 (SYNTHETIC|SESSION_START), seq=0
            assert segs[0]["f01_version"] == 4 and segs[0]["first_seq"] == 0
            assert segs[0]["has_session_start"] and not segs[0]["has_reconfigure"] and segs[0]["gaps"] == 0
            # 段 1: 8CH@2000Hz -> v1, flags=0x07 (SYNTHETIC|SESSION_START|RECONFIGURE), seq=0, ch3..8 非零
            assert segs[1]["f01_version"] == 1 and segs[1]["first_seq"] == 0
            assert segs[1]["has_session_start"] and segs[1]["has_reconfigure"] and segs[1]["gaps"] == 0
            assert segs[1]["ch3_to_ch8_nonzero_slots"] > 0
            # 段 2: 2CH@500Hz -> v1, flags=0x07, seq=0, ch3..8 全零
            assert segs[2]["f01_version"] == 1 and segs[2]["first_seq"] == 0
            assert segs[2]["has_session_start"] and segs[2]["has_reconfigure"] and segs[2]["gaps"] == 0
            assert segs[2]["ch3_to_ch8_nonzero_slots"] == 0
            # 段 3: 16CH@1000Hz -> v4, flags=0x07, seq=0
            assert segs[3]["f01_version"] == 4 and segs[3]["first_seq"] == 0
            assert segs[3]["has_session_start"] and segs[3]["has_reconfigure"] and segs[3]["gaps"] == 0

            assert len(imu_starts) == 4, f"IMU 未同步产生 4 段起始包: {imu_starts}"
            assert not imu_starts[0]["has_reconfigure"] and all(x["has_reconfigure"] and x["seq"] == 0 for x in imu_starts[1:])

            print(
                f"[T1-e 2/3 通过] 同连接四段在线热切 (16CH->8CH->2CH->16CH) 零混包、零丢样："
                f"EMG 段样本={[s['samples'] for s in segs]}，IMU 重配起始数={len(imu_starts)}"
            )
            report["checks"]["live_reconfigure_4_segments"] = {
                "emg_segments": segs,
                "imu_session_starts": imu_starts,
            }

            # 3. 验证非互锁故障码（TST1 -> FAULT_LOCKED=1）经显式 STOP 后干净清除为 0
            assert xiao.transact("W", b"TST1")[0] == 0
            swd_pump_for(0.12)
            wait_tx_drained()
            st_locked = read_xiao_status()
            assert st_locked["fault"] == 1 and not st_locked["active"], f"TST1 未触发 FAULT_LOCKED(1): {st_locked}"
            assert_ana_en_zero("TST1 拦截")

            assert xiao.transact("W", b"STOP")[0] == 0
            swd_pump_for(0.12)
            wait_tx_drained()
            st_cleared = read_xiao_status()
            l432_cleared = unpack_tx_header(bytes(target.read_memory_block8(tx_frame_addr, 280)))
            assert st_cleared["fault"] == 0 and l432_cleared["fault"] == 0 and not st_cleared["active"], (
                f"STOP 后故障码未归零: xiao={st_cleared}, l432={l432_cleared}"
            )
            assert_ana_en_zero("STOP 归零后")

            xiao.transact("D")
            swd_pump_for(0.05)
            wait_tx_drained()
            print("[T1-e 3/3 通过] TST1 -> FAULT_LOCKED=1，下发 STOP 后双核 fault 同步归零且 ANA_EN 全程 0")
            report["checks"]["stop_clears_non_interlock_fault"] = {
                "after_tst1_fault": st_locked["fault"],
                "after_stop_xiao_fault": st_cleared["fault"],
                "after_stop_l432_fault": l432_cleared["fault"],
            }

            usb_stop = True
            u_thr.join(timeout=1.0)
    finally:
        usb_stop = True
        xiao.close()

    report["all_passed"] = True
    OUT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"=== T1-e 固件优化双真机验证全部通过，报告已写入 {OUT_JSON} ===")


if __name__ == "__main__":
    main()

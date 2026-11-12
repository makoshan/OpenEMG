#!/usr/bin/env python3
"""C08B 共用主控（R4U6 / R4U6N）首板上电自检主机端解码器（零第三方依赖）。

支持两种输入：
1. --ble-hex <HEX>：解析手机 nRF Connect 复制的厂商数据（10B 值 / 12B 含 FFFF / 23B AD 载荷 / 31B 完整 BLE PDU）；
2. --report-hex <HEX>：解析 SWD / GDB / RTT 导出的 97 字节 c08b_report_t 原始内存块（含 CRC16-CCITT 校验）；
3. --self-test：运行正反例自检（由 check.sh 自动调用）。

判据与 common/report.h 及 nrf/main.c 逐位同构：
- 16CH（D20 / D20N）：id_a 低 5 位 = 0x12 且 id_b 低 5 位 = 0x12，期望 done = 0x03FF；
- 8CH （D20-8CH / D20N-8CH）：id_a 低 5 位 = 0x12 且 id_b ∈ {0x00, 0xFF}，期望 done = 0x03F5；
- 2CH （ADS1292-2ch-R9）：(id_a & 0xDF) = 0x53 且 id_b ∈ {0x00, 0xFF}，期望 done = 0x03F5；
- 其它组合（含 B 片半截乱码 0x80、U1 死 U2 活）：一律判 AFE_NONE 并按 0x03FF 报红。
"""
from __future__ import annotations
import argparse
import json
import math
import re
import struct
import sys

REPORT_MAGIC = 0xC08B
REPORT_VERSION = 1
REPORT_FMT = "<HHIHHBBBBHHHH16H16HB3hH"
REPORT_SIZE = struct.calcsize(REPORT_FMT)
assert REPORT_SIZE == 97, f"c08b_report_t 长度错误：{REPORT_SIZE} != 97"

TEST_NAMES = (
    "ADS_A_ID",
    "ADS_B_ID",
    "REG_A",
    "REG_B",
    "DRDY",
    "STATUS",
    "TEST_SIG",
    "NOISE",
    "IMU_ID",
    "IMU_G",
)

NF_HFXO = 1 << 0
NF_LINK = 1 << 1
NF_VBUS = 1 << 2
NF_CHRG = 1 << 3
NF_BTN = 1 << 4
NF_OE_OFF = 1 << 5


def crc16_ccitt(data: bytes) -> int:
    c = 0xFFFF
    for b in data:
        c ^= b << 8
        for _ in range(8):
            c = ((c << 1) ^ 0x1021) & 0xFFFF if (c & 0x8000) else (c << 1) & 0xFFFF
    return c


def clean_hex(s: str) -> bytes:
    cleaned = re.sub(r"0x", "", s, flags=re.I)
    cleaned = re.sub(r"[^0-9a-fA-F]", "", cleaned)
    if len(cleaned) % 2 != 0 or not cleaned:
        raise ValueError(f"十六进制字节串长度非法（{len(cleaned)} 个半字节）")
    return bytes.fromhex(cleaned)


def ads1298_id_ok(v: int) -> bool:
    return (v & 0x1F) == 0x12


def ads1292_id_ok(v: int) -> bool:
    return (v & 0xDF) == 0x53


def ads_b_absent(v: int) -> bool:
    return v in (0x00, 0xFF)


def afe_detect(id_a: int, id_b: int) -> tuple[int, str]:
    if ads1298_id_ok(id_a) and ads1298_id_ok(id_b):
        return 16, "16CH 双片ADS1298（D20 / D20N）"
    if ads1298_id_ok(id_a) and ads_b_absent(id_b):
        return 8, "8CH 单面ADS1298（D20-8CH / D20N-8CH）"
    if ads1292_id_ok(id_a) and ads_b_absent(id_b):
        return 2, "2CH 六触点ADS1292（ADS1292-2ch-R9）"
    return 0, "未识别或未接采集板（AFE_NONE）"


def expected_done(id_a: int, id_b: int) -> int:
    mode, _ = afe_detect(id_a, id_b)
    all_bits = (1 << len(TEST_NAMES)) - 1
    if mode in (8, 2):
        return all_bits & ~((1 << 1) | (1 << 3))  # 0x03F5
    return all_bits                                # 0x03FF


def decode_masks(done_mask: int, fail_mask: int, id_a: int, id_b: int, have_report: bool = True) -> dict:
    mode, mode_label = afe_detect(id_a, id_b)
    exp_done = expected_done(id_a, id_b)
    items = []
    first_fail_idx = None
    for idx, name in enumerate(TEST_NAMES):
        done = bool((done_mask >> idx) & 1)
        fail = bool((fail_mask >> idx) & 1)
        if not have_report:
            state = "WAITING"
        elif not done:
            state = "SKIP" if not ((exp_done >> idx) & 1) else "MISSING"
        elif fail:
            state = "FAIL"
            if first_fail_idx is None:
                first_fail_idx = idx
        else:
            state = "PASS"
        items.append({"bit": idx, "name": name, "state": state})

    if not have_report or (done_mask == 0 and fail_mask == 0xFFFF):
        verdict = "WAITING_L432"
        led_pattern = "5 Hz 快闪（尚未收到 L432 报告）"
    elif mode != 0 and fail_mask == 0 and done_mask == exp_done:
        verdict = "PASS"
        led_pattern = "1 Hz 慢闪（当前板型自检全过）"
    else:
        verdict = "FAIL"
        k = first_fail_idx if first_fail_idx is not None else 0
        led_pattern = f"闪 {k + 1} 下停顿（首项异常：{TEST_NAMES[k]}）"

    return {
        "verdict": verdict,
        "afe_channels": mode,
        "afe_mode_label": mode_label,
        "done_mask_hex": f"0x{done_mask:04X}",
        "expected_done_hex": f"0x{exp_done:04X}",
        "fail_mask_hex": f"0x{fail_mask:04X}",
        "led_pattern": led_pattern,
        "items": items,
    }


def extract_mfg_from_ad(ad: bytes) -> tuple[bytes, str | None]:
    off = 0
    local_name = None
    mfg_payload = None
    while off < len(ad):
        ln = ad[off]
        if ln == 0 or off + 1 + ln > len(ad):
            raise ValueError(f"AD 结构长度越界：offset={off}, len={ln}, total={len(ad)}")
        ad_type = ad[off + 1]
        body = ad[off + 2 : off + 1 + ln]
        if ad_type == 0x09:
            local_name = body.decode("utf-8", errors="replace")
        elif ad_type == 0xFF:
            if len(body) < 2:
                raise ValueError("厂商数据 AD 段不足 2 字节")
            company = struct.unpack_from("<H", body, 0)[0]
            if company == 0xFFFF:
                mfg_payload = body[2:]
        off += 1 + ln
    if mfg_payload is None:
        raise ValueError("AD 载荷中未找到公司号 0xFFFF 的厂商数据")
    return mfg_payload, local_name


def decode_ble(raw: bytes) -> dict:
    adv_addr = None
    local_name = None
    input_kind = None
    if len(raw) == 10:
        mfg = raw
        input_kind = "mfg_value_10B"
    elif len(raw) == 12 and raw[:2] == b"\xff\xff":
        mfg = raw[2:]
        input_kind = "mfg_company_and_value_12B"
    elif len(raw) >= 14 and raw[0] == 0x42 and raw[1] == len(raw) - 2:
        adv_addr = ":".join(f"{b:02X}" for b in reversed(raw[2:8]))
        mfg, local_name = extract_mfg_from_ad(raw[8:])
        input_kind = f"ble_pdu_{len(raw)}B"
    else:
        mfg, local_name = extract_mfg_from_ad(raw)
        input_kind = f"ad_structures_{len(raw)}B"

    if len(mfg) != 10:
        raise ValueError(f"厂商数据载荷长度应为 10 字节，实际 {len(mfg)} 字节")
    ver, done_mask, fail_mask, nflags, vbat20, seq_lo, id_a, id_b = struct.unpack("<BHHBBBBB", mfg)
    if ver != REPORT_VERSION:
        raise ValueError(f"广播协议版本不支持：{ver} != {REPORT_VERSION}")

    flags = {
        "hfxo_ok": bool(nflags & NF_HFXO),
        "l432_link_received": bool(nflags & NF_LINK),
        "vbus_present": bool(nflags & NF_VBUS),
        "charging": bool(nflags & NF_CHRG),
        "button_pressed": bool(nflags & NF_BTN),
        "afe_oe_off": bool(nflags & NF_OE_OFF),
    }
    safety_alerts = []
    notes = []
    if flags["vbus_present"] and not flags["afe_oe_off"]:
        safety_alerts.append(
            "CRITICAL_USB_INTERLOCK_BYPASSED: 检测到 VBUS=1 但 OE_N=0（AFE 缓冲未切断：疑似贴了 JP701 或互锁故障，严禁接触人体！）"
        )
    if flags["vbus_present"] and flags["afe_oe_off"] and not flags["l432_link_received"]:
        notes.append("VBUS=1 且 OE_N=1：硬件互锁已正常切断 AFE；若插着 USB 冷开机，R4U6/R4U6N 的 L432 正处于 ROM USB DFU 烧录模式。")
    if not flags["hfxo_ok"]:
        safety_alerts.append("HFXO_NOT_RUNNING: nRF 32 MHz 晶振未起振")

    mask_info = decode_masks(done_mask, fail_mask, id_a, id_b, have_report=flags["l432_link_received"])
    return {
        "source": "ble_adv",
        "input_kind": input_kind,
        "adv_addr": adv_addr,
        "local_name": local_name,
        "format_version": ver,
        "seq_low8": seq_lo,
        "vbat_mv_approx": vbat20 * 20,
        "id_a_hex": f"0x{id_a:02X}",
        "id_b_hex": f"0x{id_b:02X}",
        "nrf_flags_hex": f"0x{nflags:02X}",
        "nrf_flags": flags,
        "safety_alerts": safety_alerts,
        "notes": notes,
        **mask_info,
    }


def decode_report(raw: bytes) -> dict:
    if len(raw) != REPORT_SIZE:
        raise ValueError(f"c08b_report_t 长度必须为 {REPORT_SIZE} 字节，实际 {len(raw)} 字节")
    unpacked = struct.unpack(REPORT_FMT, raw)
    magic, ver, seq, done_mask, fail_mask = unpacked[0:5]
    id_a, id_b, reg_bad_a, reg_bad_b = unpacked[5:9]
    rate_hz_x10, drdy_desync, bad_status, frames = unpacked[9:13]
    sig_pp_uv = list(unpacked[13:29])
    noise_rms_nv = list(unpacked[29:45])
    imu_id = unpacked[45]
    imu_mg = list(unpacked[46:49])
    crc_got = unpacked[49]
    crc_exp = crc16_ccitt(raw[:95])

    if magic != REPORT_MAGIC:
        raise ValueError(f"REPORT_MAGIC 不匹配：0x{magic:04X} != 0x{REPORT_MAGIC:04X}")
    if ver != REPORT_VERSION:
        raise ValueError(f"REPORT_VERSION 不匹配：{ver} != {REPORT_VERSION}")
    if crc_got != crc_exp:
        raise ValueError(f"CRC16-CCITT 校验失败：包内 0x{crc_got:04X} != 计算值 0x{crc_exp:04X}")

    mask_info = decode_masks(done_mask, fail_mask, id_a, id_b, have_report=True)
    nch = mask_info["afe_channels"] if mask_info["afe_channels"] > 0 else 16
    channels = [
        {"ch": i + 1, "sig_pp_uv": sig_pp_uv[i], "noise_rms_nv": noise_rms_nv[i]}
        for i in range(nch)
    ]
    imu_norm_g = round(math.sqrt(sum(v * v for v in imu_mg)) / 1000.0, 4)
    return {
        "source": "l432_report_97B",
        "crc_hex": f"0x{crc_got:04X}",
        "seq": seq,
        "id_a_hex": f"0x{id_a:02X}",
        "id_b_hex": f"0x{id_b:02X}",
        "reg_bad": {"a": reg_bad_a, "b": reg_bad_b},
        "drdy_rate_hz": round(rate_hz_x10 / 10.0, 1),
        "drdy_desync_frames": drdy_desync,
        "bad_status_frames": bad_status,
        "test_sig_frames": frames,
        "imu": {
            "who_am_i_hex": f"0x{imu_id:02X}",
            "accel_mg": imu_mg,
            "norm_g": imu_norm_g,
        },
        "channels": channels,
        **mask_info,
    }


def format_human(d: dict) -> str:
    lines = [
        f"判定结果: {d['verdict']} | 板型: {d['afe_mode_label']} | LED: {d['led_pattern']}",
        f"掩码核对: done={d['done_mask_hex']} (期望 {d['expected_done_hex']}) | fail={d['fail_mask_hex']} | ID: A={d['id_a_hex']} B={d['id_b_hex']}",
    ]
    if d["source"] == "ble_adv":
        fl = d["nrf_flags"]
        lines.append(
            f"nRF 状态: VBAT≈{d['vbat_mv_approx']} mV | 序号低8位={d['seq_low8']} | "
            f"HFXO={int(fl['hfxo_ok'])} LINK={int(fl['l432_link_received'])} VBUS={int(fl['vbus_present'])} "
            f"CHRG={int(fl['charging'])} OE_OFF={int(fl['afe_oe_off'])}"
        )
        for alert in d["safety_alerts"]:
            lines.append(f"[安全告警] {alert}")
        for note in d["notes"]:
            lines.append(f"[提示] {note}")
    else:
        lines.append(
            f"采样统计: 序号={d['seq']} | 采样率={d['drdy_rate_hz']} Hz | 不同步={d['drdy_desync_frames']} | "
            f"状态错={d['bad_status_frames']} | IMU={d['imu']['who_am_i_hex']} ({d['imu']['norm_g']} g)"
        )
        for ch in d["channels"]:
            lines.append(f"  CH{ch['ch']:02d}: 方波 {ch['sig_pp_uv']:5d} µVpp | 短接底噪 {ch['noise_rms_nv']:5d} nVrms")
    item_summary = " ".join(f"{it['name']}={it['state']}" for it in d["items"])
    lines.append(f"十项明细: {item_summary}")
    return "\n".join(lines)


def _pack_report_for_test(
    done_mask: int,
    fail_mask: int,
    id_a: int,
    id_b: int,
    sig_uv: int = 1950,
    noise_nv: int = 850,
    seq: int = 3,
) -> bytes:
    mode, _ = afe_detect(id_a, id_b)
    sig = [sig_uv if i < mode else 0 for i in range(16)]
    noi = [noise_nv if i < mode else 0 for i in range(16)]
    body = struct.pack(
        "<HHIHHBBBBHHHH16H16HB3h",
        REPORT_MAGIC,
        REPORT_VERSION,
        seq,
        done_mask,
        fail_mask,
        id_a,
        id_b,
        0,
        0,
        5000,
        0,
        0,
        2000,
        *sig,
        *noi,
        0x6A,
        12,
        -18,
        998,
    )
    return body + struct.pack("<H", crc16_ccitt(body))


def _build_pdu_for_test(done: int, fail: int, nflags: int, vbat20: int, seq: int, ida: int, idb: int) -> bytes:
    addr = bytes([1, 2, 3, 4, 5, 0xC6])
    ad = (
        bytes([2, 0x01, 0x06])
        + bytes([5, 0x09]) + b"C08B"
        + bytes([13, 0xFF, 0xFF, 0xFF])
        + struct.pack("<BHHBBBBB", 1, done, fail, nflags, vbat20, seq, ida, idb)
    )
    return bytes([0x42, len(addr) + len(ad)]) + addr + ad


def run_self_test() -> int:
    # 1. CRC16-CCITT 标准向量与反例
    assert crc16_ccitt(b"123456789") == 0x29B1
    assert crc16_ccitt(b"123456780") != 0x29B1

    # 2. 四种 BLE 输入格式（10B / 12B / 23B AD / 31B PDU）与三档板型全过验证
    pdu_8ch = _build_pdu_for_test(0x03F5, 0x0000, NF_HFXO | NF_LINK, 195, 7, 0x92, 0x00)
    assert len(pdu_8ch) == 31
    d_pdu = decode_ble(pdu_8ch)
    d_ad = decode_ble(pdu_8ch[8:])
    d_12 = decode_ble(pdu_8ch[19:])
    d_10 = decode_ble(pdu_8ch[21:])
    for d in (d_pdu, d_ad, d_12, d_10):
        assert d["verdict"] == "PASS" and d["afe_channels"] == 8 and not d["safety_alerts"]

    d_16 = decode_ble(_build_pdu_for_test(0x03FF, 0x0000, NF_HFXO | NF_LINK, 198, 2, 0x92, 0xD2))
    assert d_16["verdict"] == "PASS" and d_16["afe_channels"] == 16

    d_2 = decode_ble(_build_pdu_for_test(0x03F5, 0x0000, NF_HFXO | NF_LINK, 190, 9, 0x53, 0xFF))
    assert d_2["verdict"] == "PASS" and d_2["afe_channels"] == 2

    # 3. BLE 反例：等待 L432 / B 片乱码不许假绿 / USB 互锁旁路告警
    d_wait = decode_ble(_build_pdu_for_test(0x0000, 0xFFFF, NF_HFXO | NF_VBUS | NF_OE_OFF, 205, 0, 0x00, 0x00))
    assert d_wait["verdict"] == "WAITING_L432" and not d_wait["safety_alerts"] and d_wait["notes"]

    d_garbled_b = decode_ble(_build_pdu_for_test(0x03F5, 0x0000, NF_HFXO | NF_LINK, 195, 4, 0x92, 0x80))
    assert d_garbled_b["afe_channels"] == 0 and d_garbled_b["verdict"] == "FAIL"

    d_interlock_bad = decode_ble(_build_pdu_for_test(0x03F5, 0x0000, NF_HFXO | NF_LINK | NF_VBUS, 200, 5, 0x92, 0x00))
    assert any("CRITICAL_USB_INTERLOCK_BYPASSED" in a for a in d_interlock_bad["safety_alerts"])

    # 4. 97 字节 c08b_report_t 三档解码与损坏拦截反例
    for ch, ida, idb, dm in ((16, 0x92, 0x92, 0x03FF), (8, 0x92, 0x00, 0x03F5), (2, 0x73, 0xFF, 0x03F5)):
        rep = _pack_report_for_test(dm, 0x0000, ida, idb)
        dr = decode_report(rep)
        assert dr["verdict"] == "PASS" and dr["afe_channels"] == ch and len(dr["channels"]) == ch
        assert "PASS" in format_human(dr)

    bad_crc = bytearray(_pack_report_for_test(0x03F5, 0x0000, 0x92, 0x00))
    bad_crc[20] ^= 0x01
    try:
        decode_report(bytes(bad_crc))
        raise AssertionError("CRC 翻转未抛异常")
    except ValueError as e:
        assert "CRC16-CCITT" in str(e)

    bad_len = _pack_report_for_test(0x03F5, 0x0000, 0x92, 0x00)[:-1]
    try:
        decode_report(bad_len)
        raise AssertionError("截断报告未抛异常")
    except ValueError:
        pass

    print("   decode_bringup.py 自检通过：BLE 4种格式、97B报告、16CH/8CH/2CH识别、B片乱码拦截、CRC反例、USB互锁告警")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="解码 C08B 上电自检 BLE 广播或 97 字节 L432 报告")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--ble-hex", help="手机 nRF Connect 厂商数据或完整 BLE 广播包十六进制串")
    g.add_argument("--report-hex", help="97 字节 c08b_report_t 十六进制内存导出串")
    g.add_argument("--self-test", action="store_true", help="运行内置正反例自检")
    ap.add_argument("--json", action="store_true", help="输出结构化 JSON")
    args = ap.parse_args()

    if args.self_test:
        return run_self_test()
    res = decode_ble(clean_hex(args.ble_hex)) if args.ble_hex else decode_report(clean_hex(args.report_hex))
    if args.json:
        print(json.dumps(res, ensure_ascii=False, indent=2))
    else:
        print(format_human(res))
    return 0 if res["verdict"] == "PASS" and not res.get("safety_alerts") else 2


if __name__ == "__main__":
    raise SystemExit(main())

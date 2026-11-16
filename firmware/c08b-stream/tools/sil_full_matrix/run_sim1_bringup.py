#!/usr/bin/env python3
"""Sim-1: OpenEMG v0.01 c08b-bringup 双核全硅在环测试（正例 + 6 组必挂反例）。"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

from sim_ctypes import (
    HAZ_ADS1292_VCAP1_UNDERTIME,
    HAZ_GPIO_OUTPUT_SHORT_GND,
    HAZ_NONE,
    HAZ_PIN62_AVDD_RLD_MEAS,
    HAZ_RLDREF_INT_SHORT_AGND,
    HAZ_VREF_4V_ON_2V5_RAIL,
    REPO_DIR,
    SIM_DIR,
    SIM_MAINBOARD_MCU_U9_V001,
    SIM_SUBBOARD_ADS1292_2CH,
    SIM_SUBBOARD_AFE30P_16CH,
    SIM_SUBBOARD_D20_8CH,
    SIM_SUBBOARD_GARBLED_B,
    SimConfig,
    get_tel,
    load_twin,
)

sys.path.insert(0, str(REPO_DIR / "firmware" / "c08b-bringup" / "tools"))
import decode_bringup  # noqa: E402


def run_case(lib, **overrides):
    cfg = SimConfig()
    lib.sim_default_config(ctypes.byref(cfg))
    for k, v in overrides.items():
        setattr(cfg, k, v)
    t0 = time.perf_counter()
    lib.sim_init(ctypes.byref(cfg))
    # 推进 8.4 秒虚拟时间（覆盖 1050ms POR + 150ms VREF + 4.2s 方波 + 2.2s 短接底噪 + IMU + SPI3 同步 + BLE 37/38/39 广播）
    lib.sim_step_us(8_400_000)
    tel = get_tel(lib)
    wall_ms = (time.perf_counter() - t0) * 1000.0

    rep_dec = None
    if tel.has_report_97b:
        rep_bytes = bytes(tel.last_report_97b)
        try:
            rep_dec = decode_bringup.decode_report(rep_bytes)
        except ValueError as exc:
            rep_dec = {"crc_error": str(exc)}

    ble_dec = None
    if tel.last_adv_len > 0:
        pdu_bytes = bytes(tel.last_adv_pdu[: tel.last_adv_len])
        ble_dec = decode_bringup.decode_ble(pdu_bytes)

    return tel, rep_dec, ble_dec, wall_ms


import ctypes  # noqa: E402


def main() -> int:
    lib = load_twin("libsim1_bringup.dylib")
    cases_out = []

    # 1. P1-16CH: OpenEMG v0.01 AFE-30P 双片 ADS1298 标准自检正例
    tel, rep, ble, wall_ms = run_case(lib, subboard_kind=SIM_SUBBOARD_AFE30P_16CH)
    assert rep is not None and ble is not None
    assert rep["verdict"] == "PASS" and ble["verdict"] == "PASS", (rep, ble)
    assert rep["done_mask_hex"] == "0x03FF" and rep["fail_mask_hex"] == "0x0000"
    assert ble["done_mask_hex"] == "0x03FF" and ble["fail_mask_hex"] == "0x0000"
    assert tel.hazard_mask == HAZ_NONE, f"unexpected hazard: 0x{tel.hazard_mask:X}"
    assert tel.spi1_sclk_hz == 4_000_000, f"expected 4 MHz SPI1 on ADS1298, got {tel.spi1_sclk_hz}"
    assert tel.nrf_reset_count == 1 and tel.approtect_disable_reg == 0x5A
    assert 498.0 <= rep["drdy_rate_hz"] <= 502.0
    sig16 = [c["sig_pp_uv"] for c in rep["channels"]]
    noi16 = [c["noise_rms_nv"] for c in rep["channels"]]
    assert len(sig16) == 16
    assert all(1850 <= v <= 2150 for v in sig16), sig16
    assert all(700 <= v <= 1400 for v in noi16), noi16
    assert ble["local_name"] == "C08B"
    assert ble["safety_alerts"] == []
    cases_out.append({
        "id": "P1-16CH",
        "title": "OpenEMG v0.01 AFE-30P 16CH 双片 ADS1298 全链路自检正例",
        "pass": True,
        "wall_ms": round(wall_ms, 1),
        "done_mask": rep["done_mask_hex"],
        "fail_mask": rep["fail_mask_hex"],
        "drdy_rate_hz": rep["drdy_rate_hz"],
        "ch1_pp_uv": sig16[0],
        "ch9_pp_uv": sig16[8],
        "ch1_noise_nv": noi16[0],
        "imu_norm_g": rep["imu"]["norm_g"],
        "nrf_reset_count": tel.nrf_reset_count,
        "approtect_reg": f"0x{tel.approtect_disable_reg:02X}",
        "hazard_mask": f"0x{tel.hazard_mask:04X}",
        "ble_led": ble["led_pattern"],
    })

    # 2. P1-8CH: D20-8CH 单片 ADS1298 正例
    tel, rep, ble, wall_ms = run_case(lib, subboard_kind=SIM_SUBBOARD_D20_8CH)
    assert rep["verdict"] == "PASS" and ble["verdict"] == "PASS"
    assert rep["done_mask_hex"] == "0x03F5" and rep["fail_mask_hex"] == "0x0000"
    assert tel.hazard_mask == HAZ_NONE
    sig8 = [c["sig_pp_uv"] for c in rep["channels"]]
    assert len(sig8) == 8 and all(1850 <= v <= 2150 for v in sig8)
    cases_out.append({
        "id": "P1-8CH",
        "title": "D20-8CH 单面 ADS1298 自检正例",
        "pass": True,
        "wall_ms": round(wall_ms, 1),
        "done_mask": rep["done_mask_hex"],
        "fail_mask": rep["fail_mask_hex"],
        "ch1_pp_uv": sig8[0],
        "hazard_mask": f"0x{tel.hazard_mask:04X}",
        "ble_led": ble["led_pattern"],
    })

    # 3. P1-2CH (Finding #3 已闭环修复): ADS1292-2ch-R9 六触点板在严格 tPOR=512ms + 1s VCAP1 门禁下零隐患全绿！
    tel, rep, ble, wall_ms = run_case(
        lib, subboard_kind=SIM_SUBBOARD_ADS1292_2CH, strict_ads1292_por=True
    )
    assert rep["verdict"] == "PASS" and ble["verdict"] == "PASS", (rep, ble)
    assert rep["done_mask_hex"] == "0x03F5" and rep["fail_mask_hex"] == "0x0000"
    assert tel.hazard_mask == HAZ_NONE, f"unexpected 2CH hazard: 0x{tel.hazard_mask:X}"
    assert tel.spi1_sclk_hz == 1_000_000, f"expected 1 MHz SPI1 on ADS1292, got {tel.spi1_sclk_hz}"
    sig2 = [c["sig_pp_uv"] for c in rep["channels"]]
    assert len(sig2) == 2 and 1900 <= sig2[0] <= 2150 and 1900 <= sig2[1] <= 2150
    cases_out.append({
        "id": "P1-2CH-COLD",
        "title": "ADS1292-2ch-R9 六触点板冷启动正例（Finding #3 已修复：1050ms POR + 1MHz SPI1 + 20µs PA1 复位，hazard=0x0000）",
        "pass": True,
        "wall_ms": round(wall_ms, 1),
        "done_mask": rep["done_mask_hex"],
        "fail_mask": rep["fail_mask_hex"],
        "spi1_sclk_hz": tel.spi1_sclk_hz,
        "ch1_pp_uv": sig2[0],
        "ch2_pp_uv": sig2[1],
        "hazard_mask": f"0x{tel.hazard_mask:04X}",
    })

    # 4. P1-BTN-OFF: SW300 长按 3.1 秒释放 PWR_HOLD 关机正例
    assert tel.pwr_hold_level is True
    lib.sim_set_button(True)
    lib.sim_step_us(3_200_000)
    tel_btn = get_tel(lib)
    assert tel_btn.pwr_hold_level is False, "SW300 长按 3.2s 后未拉低 PWR_HOLD"
    cases_out.append({
        "id": "P1-BTN-OFF",
        "title": "SW300 松手解锁后长按 >3.0s 释放 PWR_HOLD 软关机",
        "pass": True,
        "pwr_hold_before": True,
        "pwr_hold_after_3p2s": tel_btn.pwr_hold_level,
    })

    # 5. NC-1a (必挂反例): 旧版 yuanli-band U2 CONFIG2=0x00 回归缺陷 -> v0.01 独立 17/18 脚 CH9..16 无方波报红！
    tel, rep, ble, wall_ms = run_case(
        lib, subboard_kind=SIM_SUBBOARD_AFE30P_16CH, old_u2_cfg2_zero_bug=True
    )
    assert rep["verdict"] == "FAIL" and ble["verdict"] == "FAIL"
    assert rep["fail_mask_hex"] == "0x0040", f"expected TEST_SIG(0x0040), got {rep['fail_mask_hex']}"
    sig_nc1a = [c["sig_pp_uv"] for c in rep["channels"]]
    assert all(1850 <= v <= 2150 for v in sig_nc1a[:8])
    assert all(v < 20 for v in sig_nc1a[8:16]), sig_nc1a[8:16]
    assert "闪 7 下" in ble["led_pattern"]
    cases_out.append({
        "id": "NC-1a",
        "title": "反例：复现旧版固件 U2 CONFIG2=0x00 在 v0.01 AFE-30P 上 CH9..16=0 方波（Finding #1）",
        "pass": True,
        "expected_red_caught": True,
        "fail_mask": rep["fail_mask_hex"],
        "ch1_pp_uv": sig_nc1a[0],
        "ch9_pp_uv": sig_nc1a[8],
        "ble_led": ble["led_pattern"],
    })

    # 6. NC-1b (必挂反例): v0.01 AFE-30P 四大电气安全红线故障注入（RLDREF_INT / Pin62 RLD_MEAS / VREF_4V / GPIO 对地短路）
    tel_haz, _, _, _ = run_case(
        lib,
        subboard_kind=SIM_SUBBOARD_AFE30P_16CH,
        inject_hazard_cfg3=0x38,  # VREF_4V(0x20) | RLD_MEAS(0x10) | RLDREF_INT(0x08)
        inject_hazard_gpio=0xF0,  # GPIOC=0000(全推挽输出) + GPIOD=1111(驱动高电平) -> GPIO1/2/4 对地硬短路!
    )
    expected_haz = (
        HAZ_RLDREF_INT_SHORT_AGND
        | HAZ_PIN62_AVDD_RLD_MEAS
        | HAZ_VREF_4V_ON_2V5_RAIL
        | HAZ_GPIO_OUTPUT_SHORT_GND
    )
    assert (tel_haz.hazard_mask & expected_haz) == expected_haz, f"0x{tel_haz.hazard_mask:X}"
    cases_out.append({
        "id": "NC-1b",
        "title": "反例：注入 RLDREF_INT/Pin62_RLD_MEAS/VREF_4V/GPIO输出 电气短路位，安全监控器全数拦截",
        "pass": True,
        "expected_red_caught": True,
        "hazard_mask": f"0x{tel_haz.hazard_mask:04X}",
    })

    # 7. NC-1c (必挂反例): USB VBUS=1 硬件互锁生效 vs VBUS=1 + JP701 短接旁路告警
    tel_ilk, rep_ilk, ble_ilk, _ = run_case(
        lib,
        mainboard_rev=SIM_MAINBOARD_MCU_U9_V001,
        subboard_kind=SIM_SUBBOARD_AFE30P_16CH,
        vbus_present=True,
        jp701_shorted=False,
    )
    assert tel_ilk.oe_n_level is True
    assert rep_ilk["verdict"] == "FAIL" and rep_ilk["afe_channels"] == 0
    assert ble_ilk["nrf_flags"]["vbus_present"] is True and ble_ilk["nrf_flags"]["afe_oe_off"] is True
    assert ble_ilk["safety_alerts"] == []

    tel_byp, rep_byp, ble_byp, _ = run_case(
        lib,
        mainboard_rev=SIM_MAINBOARD_MCU_U9_V001,
        subboard_kind=SIM_SUBBOARD_AFE30P_16CH,
        vbus_present=True,
        jp701_shorted=True,
    )
    assert tel_byp.oe_n_level is False
    assert any("CRITICAL_USB_INTERLOCK_BYPASSED" in s for s in ble_byp["safety_alerts"]), ble_byp
    cases_out.append({
        "id": "NC-1c",
        "title": "反例：VBUS=1 互锁切断 OE_N=1 读全零 vs JP701 短接触发 CRITICAL_USB_INTERLOCK_BYPASSED",
        "pass": True,
        "expected_red_caught": True,
        "ilk_oe_n": tel_ilk.oe_n_level,
        "ilk_id_ab": [rep_ilk["id_a_hex"], rep_ilk["id_b_hex"]],
        "jp701_alert": ble_byp["safety_alerts"][0],
    })

    # 8. NC-1d (必挂反例): 2CH U3 3.0V LDO 掉电开路 + PA4 3.3V 寄生残荷 -> 10µs P_DOWN 泄放检出 T_STATUS 失败
    tel_2d, rep_2d, ble_2d, _ = run_case(
        lib, subboard_kind=SIM_SUBBOARD_ADS1292_2CH, avdd_3v0_ok=False
    )
    assert rep_2d["verdict"] == "FAIL" and ble_2d["verdict"] == "FAIL"
    assert (int(rep_2d["fail_mask_hex"], 16) & (1 << 5)) != 0, rep_2d  # bit5 = STATUS
    assert rep_2d["bad_status_frames"] > 0
    cases_out.append({
        "id": "NC-1d",
        "title": "反例：2CH U3 3.0V LDO 开路（带 3.3V 寄生残荷），10µs P_DOWN 泄放准确检出 T_STATUS 失败",
        "pass": True,
        "expected_red_caught": True,
        "fail_mask": rep_2d["fail_mask_hex"],
        "bad_status_frames": rep_2d["bad_status_frames"],
    })

    # 9. NC-1e (必挂反例): DRDY_B 粘连、U2 半死乱码 0x80、SPI3 CRC 翻转三重总线故障注入
    _, rep_drdy, _, _ = run_case(
        lib, subboard_kind=SIM_SUBBOARD_AFE30P_16CH, drdy_b_stuck_low=True
    )
    assert rep_drdy["verdict"] == "FAIL" and rep_drdy["drdy_desync_frames"] > 0
    assert (int(rep_drdy["fail_mask_hex"], 16) & (1 << 4)) != 0  # bit4 = DRDY

    _, rep_garb, _, _ = run_case(lib, subboard_kind=SIM_SUBBOARD_GARBLED_B)
    assert rep_garb["verdict"] == "FAIL" and rep_garb["afe_channels"] == 0

    tel_crc, _, ble_crc, _ = run_case(
        lib, subboard_kind=SIM_SUBBOARD_AFE30P_16CH, corrupt_spi3_crc=True
    )
    assert ble_crc["verdict"] == "WAITING_L432"
    assert "5 Hz 快闪" in ble_crc["led_pattern"]
    assert "校验不过" in tel_crc.nrf_rtt.decode("utf-8", errors="replace")
    cases_out.append({
        "id": "NC-1e",
        "title": "反例：DRDY_B 粘连 / U2 0x80 乱码 / SPI3 CRC 翻转全部被精确拒收",
        "pass": True,
        "expected_red_caught": True,
        "drdy_desync_frames": rep_drdy["drdy_desync_frames"],
        "garbled_b_mode": rep_garb["afe_channels"],
        "crc_corrupt_ble_verdict": ble_crc["verdict"],
    })

    # 10. NC-1f (必挂反例): 注入旧版 280ms 缩短冷启动延时 + TI SBAS502C tPOR=512ms 锁死 -> 读 ID=0x00 且拦截 VCAP1 未充饱！
    tel_por, rep_por, ble_por, _ = run_case(
        lib,
        subboard_kind=SIM_SUBBOARD_ADS1292_2CH,
        strict_ads1292_por=True,
        force_short_bringup_por=True,
    )
    assert rep_por["verdict"] == "FAIL" and rep_por["afe_channels"] == 0
    assert rep_por["id_a_hex"] == "0x00"
    assert (tel_por.hazard_mask & HAZ_ADS1292_VCAP1_UNDERTIME) != 0
    cases_out.append({
        "id": "NC-1f",
        "title": "反例：强制缩短冷启动至旧版 280ms 时，TI SBAS502C tPOR=512ms 门禁准确拦截 ID=0x00 与 VCAP1 隐患",
        "pass": True,
        "expected_red_caught": True,
        "id_a_at_280ms": rep_por["id_a_hex"],
        "hazard_mask": f"0x{tel_por.hazard_mask:04X}",
        "verdict": rep_por["verdict"],
    })

    summary = {
        "suite": "Sim-1 (c08b-bringup Dual-MCU Silicon-in-the-Loop)",
        "total_cases": len(cases_out),
        "passed_cases": sum(1 for c in cases_out if c["pass"]),
        "cases": cases_out,
    }
    out_path = SIM_DIR / "reports" / "results_sim1_bringup.json"
    out_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"SIM1_ALL_PASS ({summary['passed_cases']}/{summary['total_cases']}) -> {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

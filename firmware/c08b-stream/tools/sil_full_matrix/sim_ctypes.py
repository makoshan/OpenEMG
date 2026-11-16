#!/usr/bin/env python3
"""OpenEMG v0.01 双核硅级硬件孪生 Python ctypes 绑定与 Bleak 协议栈适配器。"""
from __future__ import annotations

import asyncio
import ctypes
from pathlib import Path

import os

SIM_DIR = Path(__file__).resolve().parent
BUILD_DIR = Path(os.environ.get("SIM_BUILD_DIR", str(SIM_DIR / "build")))


def _detect_repo_dir() -> Path:
    env = os.environ.get("REPO_DIR")
    if env:
        return Path(env).resolve()
    for p in SIM_DIR.parents:
        if (p / "firmware/c08b-bringup").is_dir() or (p / "v12/c08b-bringup-fw-20261109").is_dir():
            return p
    return SIM_DIR.parents[1]


REPO_DIR = _detect_repo_dir()
BRINGUP_DIR = (REPO_DIR / "firmware/c08b-bringup") if (REPO_DIR / "firmware/c08b-bringup").is_dir() else (REPO_DIR / "v12/c08b-bringup-fw-20261109")
STREAM_DIR = (REPO_DIR / "firmware/c08b-stream") if (REPO_DIR / "firmware/c08b-stream").is_dir() else (REPO_DIR / "v12/c08b-stream-fw-20261112")
DONGLE_DIR = (REPO_DIR / "firmware/ble-dongle") if (REPO_DIR / "firmware/ble-dongle").is_dir() else (REPO_DIR / "v12/ble-dongle-20261021")
X2_DIR = (REPO_DIR / "firmware/xiao-ads1292-2ch") if (REPO_DIR / "firmware/xiao-ads1292-2ch").is_dir() else (REPO_DIR / "v12/ads1292-p44e-xiao-fw-20261112")
DSP_DIR = (REPO_DIR / "firmware/dsp-f03") if (REPO_DIR / "firmware/dsp-f03").is_dir() else (REPO_DIR / "v12/dsp-f03")

SIM_MAINBOARD_MCU_U9_V001 = 0
SIM_MAINBOARD_R4U6 = 1

SIM_SUBBOARD_NONE = 0
SIM_SUBBOARD_AFE30P_16CH = 16
SIM_SUBBOARD_D20_8CH = 8
SIM_SUBBOARD_ADS1292_2CH = 2
SIM_SUBBOARD_GARBLED_B = 99

SIM_WAVE_SEMG_PHYSIOL = 0
SIM_WAVE_TONE_SWEEP = 1
SIM_WAVE_SINGLE_CH = 2

HAZ_NONE = 0
HAZ_RLDREF_INT_SHORT_AGND = 1 << 0
HAZ_PIN62_AVDD_RLD_MEAS = 1 << 1
HAZ_VREF_4V_ON_2V5_RAIL = 1 << 2
HAZ_GPIO_OUTPUT_SHORT_GND = 1 << 3
HAZ_RLD_NO_WARMUP_OR_U2_RLD = 1 << 4
HAZ_ADS1292_SPI_TSDECODE = 1 << 5
HAZ_ADS1292_VCAP1_UNDERTIME = 1 << 6
HAZ_NRF_LFCLK_XTAL_ON_XL1 = 1 << 7
HAZ_NRF_OE_N_DRIVEN_OUTPUT = 1 << 8
HAZ_SPI3_OVER_8MHZ = 1 << 9
HAZ_L432_PLL_FLASH_WS = 1 << 10
HAZ_ADS1298_CLK_EN_PIN37 = 1 << 11


class SimConfig(ctypes.Structure):
    _fields_ = [
        ("mainboard_rev", ctypes.c_int),
        ("subboard_kind", ctypes.c_int),
        ("id_a_override", ctypes.c_uint8),
        ("id_b_override", ctypes.c_uint8),
        ("vbus_present", ctypes.c_bool),
        ("jp701_shorted", ctypes.c_bool),
        ("force_oe_n_high", ctypes.c_bool),
        ("avdd_3v0_ok", ctypes.c_bool),
        ("strict_ads1292_por", ctypes.c_bool),
        ("force_short_bringup_por", ctypes.c_bool),
        ("imu_present", ctypes.c_bool),
        ("imu_bus_stuck_low", ctypes.c_bool),
        ("drdy_a_timeout", ctypes.c_bool),
        ("drdy_b_stuck_low", ctypes.c_bool),
        ("reg_readback_fault", ctypes.c_bool),
        ("corrupt_spi3_crc", ctypes.c_bool),
        ("old_u2_cfg2_zero_bug", ctypes.c_bool),
        ("inject_hazard_cfg3", ctypes.c_uint32),
        ("inject_hazard_gpio", ctypes.c_uint32),
        ("inject_periodic_stall_us", ctypes.c_uint32),
        ("wave_mode", ctypes.c_int),
        ("active_single_ch", ctypes.c_int),
        ("tone_amp_uv", ctypes.c_double),
        ("mains_50hz_cm_uv", ctypes.c_double),
        ("crosstalk_ratio", ctypes.c_double),
        ("vbat_mv", ctypes.c_uint32),
        ("chrg_active", ctypes.c_bool),
        ("button_pressed", ctypes.c_bool),
    ]


class SimTelemetry(ctypes.Structure):
    _fields_ = [
        ("sim_time_us", ctypes.c_uint64),
        ("hazard_mask", ctypes.c_uint32),
        ("l432_hclk_hz", ctypes.c_uint32),
        ("nrf_reset_count", ctypes.c_uint32),
        ("approtect_disable_reg", ctypes.c_uint32),
        ("spi1_sclk_hz", ctypes.c_uint32),
        ("spi3_sclk_hz", ctypes.c_uint32),
        ("spi3_frames_sent", ctypes.c_uint32),
        ("spi3_crc_ok_count", ctypes.c_uint32),
        ("spi3_crc_fail_count", ctypes.c_uint32),
        ("radio_adv_count", ctypes.c_uint32),
        ("last_adv_pdu", ctypes.c_uint8 * 39),
        ("last_adv_len", ctypes.c_uint8),
        ("last_report_97b", ctypes.c_uint8 * 97),
        ("has_report_97b", ctypes.c_bool),
        ("ads_regs", (ctypes.c_uint8 * 0x1A) * 2),
        ("ana_en_level", ctypes.c_bool),
        ("oe_n_level", ctypes.c_bool),
        ("ads_pwdn_level", ctypes.c_bool),
        ("ads_reset_level", ctypes.c_bool),
        ("ads_start_level", ctypes.c_bool),
        ("pwr_hold_level", ctypes.c_bool),
        ("led_pin_level", ctypes.c_bool),
        ("vbus_inject_us", ctypes.c_uint64),
        ("ana_en_off_us", ctypes.c_uint64),
        ("nrf_stop_us", ctypes.c_uint64),
        ("zero_frames_leaked", ctypes.c_uint32),
        ("l432_rtt", ctypes.c_char * 2048),
        ("nrf_rtt", ctypes.c_char * 2048),
    ]


def load_twin(dylib_name: str) -> ctypes.CDLL:
    lib = ctypes.CDLL(str(BUILD_DIR / dylib_name), mode=ctypes.RTLD_LOCAL)
    lib.sim_default_config.argtypes = [ctypes.POINTER(SimConfig)]
    lib.sim_default_config.restype = None
    lib.sim_init.argtypes = [ctypes.POINTER(SimConfig)]
    lib.sim_init.restype = None
    lib.sim_step_us.argtypes = [ctypes.c_uint64]
    lib.sim_step_us.restype = None
    lib.sim_set_vbus.argtypes = [ctypes.c_bool]
    lib.sim_set_vbus.restype = None
    lib.sim_set_force_oe_n_high.argtypes = [ctypes.c_bool]
    lib.sim_set_force_oe_n_high.restype = None
    lib.sim_set_avdd_3v0.argtypes = [ctypes.c_bool]
    lib.sim_set_avdd_3v0.restype = None
    lib.sim_set_button.argtypes = [ctypes.c_bool]
    lib.sim_set_button.restype = None
    lib.sim_set_readback_fault.argtypes = [ctypes.c_bool]
    lib.sim_set_readback_fault.restype = None
    lib.sim_get_telemetry.argtypes = [ctypes.POINTER(SimTelemetry)]
    lib.sim_get_telemetry.restype = None

    lib.sim_ble_connect.argtypes = [ctypes.c_uint16]
    lib.sim_ble_connect.restype = None
    lib.sim_ble_disconnect.argtypes = []
    lib.sim_ble_disconnect.restype = None
    lib.sim_ble_subscribe.argtypes = [ctypes.c_uint8, ctypes.c_bool]
    lib.sim_ble_subscribe.restype = ctypes.c_int
    lib.sim_ble_write_ctrl.argtypes = [ctypes.POINTER(ctypes.c_uint8), ctypes.c_uint16]
    lib.sim_ble_write_ctrl.restype = ctypes.c_int
    lib.sim_ble_read_char.argtypes = [ctypes.c_uint8, ctypes.POINTER(ctypes.c_uint8), ctypes.c_int]
    lib.sim_ble_read_char.restype = ctypes.c_int
    lib.sim_ble_pop_notify.argtypes = [
        ctypes.POINTER(ctypes.c_uint8),
        ctypes.POINTER(ctypes.c_uint8),
        ctypes.c_int,
        ctypes.POINTER(ctypes.c_uint64),
    ]
    lib.sim_ble_pop_notify.restype = ctypes.c_int
    lib.sim_ble_get_adv_name.argtypes = [ctypes.c_char_p, ctypes.c_int]
    lib.sim_ble_get_adv_name.restype = ctypes.c_int
    return lib


def get_tel(lib: ctypes.CDLL) -> SimTelemetry:
    tel = SimTelemetry()
    lib.sim_get_telemetry(ctypes.byref(tel))
    return tel

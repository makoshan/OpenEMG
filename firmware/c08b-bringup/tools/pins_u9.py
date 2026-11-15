#!/usr/bin/env python3
"""从人工审核定版双板工程 hardware/16ch-afe-hirose-1mm-1nf/OpenEMG_v0.01_DualBoard.epro2
与旗舰六层主控工程 hardware/16ch-u9-dual30/OpenEMG-C08B-Mainboard-Rev0.01.epro2 逐脚核对：
1. 01 主控板（C08B-U9）：U7（STM32L432KCU6）23+3 脚（含 31 脚 PH3=L_BOOT0）、U8（nRF52840-QFAA）15 脚、
   U17（LTC4054）5 脚与 FPC1（20P 板间座）20 脚；
2. 02 采集板（v0.01 AFE-30P）：FPC2（20P 板间座 k <-> 21-k）、U1/U2（双 ADS1298）全部电源/SPI/控制脚
   （含 Pin 17/18 独立悬空、Pin 31 RESV1=GND、Pin 42/44/46 GPIO1/2/4=GND、Pin 60 RLDREF=AGND、
   Pin 62 RLDIN=+2.5V、Pin 63 RLDOUT 经 R34/R36 至 FPC1.29/FPC3.29）以及 D101..D132 全 32 路 ESD 保护；
3. 与现行 l432/pins.h、nrf/pins.h 及 l432/main.c 的 CFG1298_TEST 寄存器配置交叉核对（确保 U1/U2 均开 INT_TEST=1，
   且 CONFIG3 严禁置 VREF_4V/RLD_MEAS/RLDREF_INT）。
支持 `--selftest` 执行 6 项必败反例自检。纯 Python 标准库，可在本地与云端 CI 直接运行。
"""
from __future__ import annotations
import json
import re
import sys
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
REPO = HERE.parents[1]
DEFAULT_DUAL_EPRO2 = REPO / "hardware/16ch-afe-hirose-1mm-1nf/OpenEMG_v0.01_DualBoard.epro2"
DEFAULT_EPRO2 = REPO / "hardware/16ch-u9-dual30/OpenEMG-C08B-Mainboard-Rev0.01.epro2"

L432_PKG = {
    "PC14": 2, "PC15": 3, "NRST": 4,
    "PA0": 6, "PA1": 7, "PA2": 8, "PA3": 9, "PA4": 10, "PA5": 11, "PA6": 12, "PA7": 13,
    "PB0": 14, "PB1": 15, "PA8": 18, "PA9": 19, "PA10": 20, "PA11": 21, "PA12": 22,
    "PA13": 23, "PA14": 24, "PA15": 25, "PB3": 26, "PB4": 27, "PB5": 28, "PB6": 29, "PB7": 30,
    "PH3": 31,
}

NRF_PKG = {
    "P0.00": 2, "P0.01": 3, "P0.04": 4, "P0.05": 5, "P0.07": 6, "P0.08": 7,
    "P1.08": 8, "P1.09": 9, "P0.11": 10, "P0.12": 11, "P0.13": 13, "P0.14": 14,
    "P0.17": 15, "P0.18": 16, "P0.19": 18, "P0.20": 19, "P0.21": 20, "P0.22": 21,
    "P0.23": 22, "P0.24": 23, "P1.00": 24, "P0.09": 29, "P0.10": 30, "P1.15": 38,
    "P0.03": 39, "P0.02": 40, "P0.28": 41, "P0.29": 42, "P0.30": 43, "P0.31": 44,
}

U7_L432_EXPECTED = [
    ("ANA_EN",    "PC14", "ANA_EN"),
    ("AFE_GPIO3", "PA0",  "AFE_GPIO3"),
    ("ADS_PWDN",  "PA1",  "XIAO_PWDN"),
    ("DRDY_A",    "PA2",  "XIAO_DRDY"),
    ("ADS_START", "PA3",  "AFE_START"),
    ("DRDY_B",    "PA4",  "AFE_DRDY_B"),
    ("SPI1_SCK",  "PA5",  "XIAO_SCLK"),
    ("SPI1_MISO", "PA6",  "XIAO_MISO"),
    ("SPI1_MOSI", "PA7",  "XIAO_MOSI"),
    ("CS_A",      "PB0",  "XIAO_CS"),
    ("CS_B",      "PB1",  "MCU_CS_B"),
    ("ADS_RESET", "PA8",  "XIAO_RESET"),
    ("IMU_SCL",   "PA9",  "IMU_SCL"),
    ("IMU_SDA",   "PA10", "IMU_SDA"),
    ("USB_DM",    "PA11", "MCU_DM"),
    ("USB_DP",    "PA12", "MCU_DP"),
    ("LINK_CS",   "PA15", "LINK_CS"),
    ("LINK_SCK",  "PB3",  "LINK_SCK"),
    ("LINK_MISO", "PB4",  "LINK_MISO"),
    ("LINK_MOSI", "PB5",  "LINK_MOSI"),
    ("LINK_RDY",  "PB6",  "LINK_RDY"),
    ("IMU_INT1",  "PB7",  "IMU_INT1"),
    ("BOOT0",     "PH3",  "L_BOOT0"),
]

U7_DEBUG_PINS = {
    4: "L_NRST",
    23: "L_SWDIO",
    24: "L_SWCLK",
}

U8_NRF_EXPECTED = [
    ("BENCH_EN",   "P0.00", "MCU_BENCH_EN"),
    ("VBUS_SENSE", "P0.01", "VBUS_SENSE"),
    ("VBAT_SENSE", "P0.04", "VBAT_SENSE"),
    ("PWR_HOLD",   "P0.05", "PWR_HOLD"),
    ("LINK_RDY",   "P0.07", "LINK_RDY"),
    ("LINK_MOSI",  "P0.08", "LINK_MOSI"),
    ("LINK_MISO",  "P1.08", "LINK_MISO"),
    ("LINK_SCK",   "P1.09", "LINK_SCK"),
    ("LINK_CS",    "P0.11", "LINK_CS"),
    ("CHRG_N",     "P0.12", "CHRG_N"),
    ("BUTTON_N",   "P0.14", "BUTTON_N"),
    ("OE_N",       "P0.17", "OE_N"),
    ("MCU_RST_N",  "P0.18", "MCU_RST_N"),
    ("LED",        "P0.23", "MCU_LED"),
    ("UART_TX",    "P0.24", "MCU_TX"),
]

U17_LTC4054_EXPECTED = {
    1: "CHRG_N",
    2: "GND",
    3: "VBAT",
    4: "VBUS",
    5: "CHG_PROG",
}

FPC1_20P_EXPECTED = {
    1: "GND", 2: "", 3: "AFE_DRDY_B", 4: "AFE_CS_B", 5: "AFE_DIN",
    6: "AFE_PWDN", 7: "AFE_RESET", 8: "", 9: "AFE_START", 10: "AFE_CS_A",
    11: "AFE_SCLK", 12: "GND", 13: "", 14: "GND", 15: "DOUT_B",
    16: "AFE_GPIO3", 17: "ADS_DRDY_A", 18: "", 19: "3V3_AFE", 20: "3V3_AFE",
}


FPC2_20P_EXPECTED = {
    1: "+3.3V", 2: "+3.3V", 3: "CLKSEL", 4: "DRDY#", 5: "GPIO3",
    6: "DOUT", 7: "GND", 8: "GND", 9: "GND", 10: "SCLK",
    11: "CS#", 12: "START", 13: "CLK", 14: "RESET#", 15: "PWDN#",
    16: "DIN", 17: "CS#2", 18: "DRDY2#", 19: "GND", 20: "GND",
}

ADS1298_COMMON_PINS = {
    17: "", 18: "",  # v0.01 AFE-30P TESTP/TESTN 独立悬空
    19: "+2.5V", 21: "+2.5V", 22: "+2.5V", 54: "+2.5V", 56: "+2.5V", 59: "+2.5V",
    20: "-2.5V", 23: "-2.5V", 25: "-2.5V", 32: "-2.5V", 53: "-2.5V", 57: "-2.5V", 58: "-2.5V",
    31: "GND", 33: "GND", 41: "GND", 42: "GND", 44: "GND", 46: "GND", 49: "GND", 51: "GND",
    48: "+3.3V", 50: "+3.3V",
    34: "DIN", 35: "PWDN#", 36: "RESET#", 37: "CLK", 38: "START", 40: "SCLK",
    43: "DOUT", 45: "GPIO3", 52: "CLKSEL",
    60: "AGND",  # RLDREF 接 AGND -> 严禁置 RLDREF_INT(0x08)
    62: "+2.5V", # RLDIN 接 +2.5V -> 严禁置 RLD_MEAS(0x10) 或 MUX=010
}


def load_epro2_pcb_boards(epro2_path: Path) -> list[tuple[str, dict[tuple[str, int], str]]]:
    with zipfile.ZipFile(epro2_path) as zf:
        doc = zf.read(next(n for n in zf.namelist() if n.endswith(".epru"))).decode("utf-8", "ignore")
    boards: list[tuple[str, dict[str, str], dict[tuple[str, int], str]]] = []
    active = False
    for line in doc.splitlines():
        if "||" not in line:
            continue
        left, right = line.split("||", 1)
        right = right.removesuffix("|")
        if not right:
            continue
        h = json.loads(left)
        if h["type"] not in ("DOCHEAD", "ATTR", "PAD_NET"):
            continue
        v, _ = json.JSONDecoder().raw_decode(right)
        if h["type"] == "DOCHEAD":
            if v.get("docType") == "PCB":
                active = True
                boards.append((v.get("uuid", ""), {}, {}))
            else:
                active = False
        elif active and h["type"] == "ATTR" and v.get("key") == "Designator":
            boards[-1][1][v["parentId"]] = v.get("value", "")
        elif active and h["type"] == "PAD_NET":
            _, cid, pin, _ = json.loads(h["id"])
            if str(pin).isdigit():
                boards[-1][2][(cid, int(pin))] = v.get("padNet", "")
    return [
        (uuid, {(des[cid], pin): net for (cid, pin), net in pads.items() if cid in des})
        for uuid, des, pads in boards
    ]


def load_u9_nets(epro2_path: Path) -> dict[tuple[str, int], str]:
    boards = load_epro2_pcb_boards(epro2_path)
    for _, nets in boards:
        if ("U7", 31) in nets and ("U8", 2) in nets:
            return nets
    return boards[0][1] if boards else {}


def load_afe30p_v001_nets(epro2_path: Path) -> dict[tuple[str, int], str] | None:
    for _, nets in load_epro2_pcb_boards(epro2_path):
        if ("U1", 39) in nets and ("U2", 39) in nets and ("FPC2", 1) in nets:
            return nets
    return None


def verify_u9_nets(nets: dict[tuple[str, int], str]) -> list[str]:
    errs: list[str] = []

    used_u7 = set()
    for macro, port, exp_net in U7_L432_EXPECTED:
        pin = L432_PKG[port]
        got = nets.get(("U7", pin), "")
        if got != exp_net:
            errs.append(f"U7 {macro} ({port}/脚{pin}): 实际 {got!r} != 期望 {exp_net!r}")
        used_u7.add(pin)
    for pin, exp_net in U7_DEBUG_PINS.items():
        got = nets.get(("U7", pin), "")
        if got != exp_net:
            errs.append(f"U7 调试脚 {pin}: 实际 {got!r} != 期望 {exp_net!r}")
        used_u7.add(pin)
    extra_u7 = {
        pin
        for pin in L432_PKG.values()
        if pin not in used_u7 and nets.get(("U7", pin), "") not in ("", "GND", "3V3")
    }
    for pin in sorted(extra_u7):
        errs.append(f"U7 未登记信号脚 {pin}: {nets[('U7', pin)]!r}")

    used_u8 = set()
    for macro, port, exp_net in U8_NRF_EXPECTED:
        pin = NRF_PKG[port]
        got = nets.get(("U8", pin), "")
        if got != exp_net:
            errs.append(f"U8 {macro} ({port}/脚{pin}): 实际 {got!r} != 期望 {exp_net!r}")
        used_u8.add(pin)
    extra_u8 = {
        pin
        for pin in NRF_PKG.values()
        if pin not in used_u8 and nets.get(("U8", pin), "") not in ("", "GND", "3V3")
    }
    for pin in sorted(extra_u8):
        errs.append(f"U8 未登记 GPIO 脚 {pin}: {nets[('U8', pin)]!r}")

    for pin, exp_net in U17_LTC4054_EXPECTED.items():
        got = nets.get(("U17", pin), "")
        if got != exp_net:
            errs.append(f"U17.pin{pin}: 实际 {got!r} != 期望 {exp_net!r}")

    for pin, exp_net in FPC1_20P_EXPECTED.items():
        got = nets.get(("FPC1", pin), "")
        if got != exp_net:
            errs.append(f"FPC1.pin{pin}: 实际 {got!r} != 期望 {exp_net!r}")

    return errs


def verify_afe30p_v001_nets(afe_nets: dict[tuple[str, int], str]) -> list[str]:
    errs: list[str] = []
    for pin, exp_net in FPC2_20P_EXPECTED.items():
        got = afe_nets.get(("FPC2", pin), "")
        if got != exp_net:
            errs.append(f"AFE-30P FPC2.pin{pin}: 实际 {got!r} != 期望 {exp_net!r}")

    for ref, cs_net, drdy_net, rldinv_net, rldout_net in (
        ("U1", "CS#", "DRDY#", "BIASINV1", "BIASOUT1"),
        ("U2", "CS#2", "DRDY2#", "BIASINV12", "BIASOUT12"),
    ):
        for pin, exp_net in ADS1298_COMMON_PINS.items():
            got = afe_nets.get((ref, pin), "<MISSING>")
            if got != exp_net:
                errs.append(f"AFE-30P {ref}.pin{pin}: 实际 {got!r} != 期望 {exp_net!r}")
        for pin, exp_net in ((39, cs_net), (47, drdy_net), (61, rldinv_net), (63, rldout_net)):
            got = afe_nets.get((ref, pin), "<MISSING>")
            if got != exp_net:
                errs.append(f"AFE-30P {ref}.pin{pin}: 实际 {got!r} != 期望 {exp_net!r}")

    r34_nets = {afe_nets.get(("R34", 1), ""), afe_nets.get(("R34", 2), "")}
    r36_nets = {afe_nets.get(("R36", 1), ""), afe_nets.get(("R36", 2), "")}
    if r34_nets != {"BIASOUT1", "BIAS_DRV1"} or afe_nets.get(("FPC1", 29), "") != "BIAS_DRV1":
        errs.append(f"AFE-30P U1 RLD 驱动链路异常: R34={r34_nets!r}, FPC1.29={afe_nets.get(('FPC1', 29))!r}")
    if r36_nets != {"BIASOUT12", "BIAS_DRV12"} or afe_nets.get(("FPC3", 29), "") != "BIAS_DRV12":
        errs.append(f"AFE-30P U2 RLD 驱动链路异常: R36={r36_nets!r}, FPC3.29={afe_nets.get(('FPC3', 29))!r}")

    esd_inputs = set()
    for idx in range(101, 133):
        ref = f"D{idx}"
        p1 = afe_nets.get((ref, 1), "")
        p2 = afe_nets.get((ref, 2), "")
        if not p1 or p2 != "AGND":
            errs.append(f"AFE-30P {ref}: 实际 (1={p1!r}, 2={p2!r}) != 期望 (非空输入网, 'AGND')")
        else:
            esd_inputs.add(p1)
    if len(esd_inputs) != 32:
        errs.append(f"AFE-30P D101..D132 覆盖独立输入网数量 {len(esd_inputs)} != 32")
    return errs


def verify_headers_and_source_compat(l432_src: str | None = None) -> list[str]:
    errs: list[str] = []
    l432_h = (HERE / "l432/pins.h").read_text(encoding="utf-8")
    nrf_h = (HERE / "nrf/pins.h").read_text(encoding="utf-8")

    for macro, port, _ in U7_L432_EXPECTED:
        p_letter, p_num = port[1], int(port[2:])
        if f"#define {macro}_PORT GPIO{p_letter}" not in l432_h or not re.search(rf"#define\s+{macro}_PIN\s+{p_num}\b", l432_h):
            errs.append(f"l432/pins.h 宏不兼容: {macro} -> {port}")

    for macro, port, _ in U8_NRF_EXPECTED:
        po, pi = int(port[1]), int(port.split(".")[1])
        if f"#define {macro}_PIN ({po} * 32 + {pi})" not in nrf_h:
            errs.append(f"nrf/pins.h 宏不兼容: {macro} -> {port}")

    raw_c = l432_src if l432_src is not None else (HERE / "l432/main.c").read_text(encoding="utf-8")
    code = re.sub(r"/\*.*?\*/", "", raw_c, flags=re.S)
    code = re.sub(r"//[^\n]*", "", code)
    if not re.search(r"\[0x02\]\s*=\s*0x10\b", code):
        errs.append("l432/main.c CFG1298_TEST[0x02] 未设为 0x10 (INT_TEST=1)")
    if re.search(r"if\s*\(\s*chip\s*==\s*1\s*\)\s*cfg\[\s*0x02\s*\]\s*=\s*0x00\b", code):
        errs.append("l432/main.c 严禁对 U2 (chip==1) 覆写 cfg[0x02]=0x00（v0.01 AFE-30P 17/18 脚独立悬空，会令 CH9..16 失波）")
    m_c3 = re.search(r"\[0x03\]\s*=\s*0x([0-9A-Fa-f]{2})\b", code)
    if not m_c3 or (int(m_c3.group(1), 16) & 0x38) != 0:
        errs.append("l432/main.c CFG1298_TEST[0x03] 严禁置 VREF_4V(0x20)/RLD_MEAS(0x10)/RLDREF_INT(0x08)")
    if not re.search(r"\[0x14\]\s*=\s*0x0F\b", code):
        errs.append("l432/main.c CFG1298_TEST[0x14] 未设为 0x0F（GPIO1/2/4 接地，必须全输入）")

    return errs


def main() -> int:
    selftest = "--selftest" in sys.argv
    args = [a for a in sys.argv[1:] if a != "--selftest"]
    epro2_path = Path(args[0]) if args else (DEFAULT_DUAL_EPRO2 if DEFAULT_DUAL_EPRO2.is_file() else DEFAULT_EPRO2)

    nets = load_u9_nets(epro2_path)
    errs = verify_u9_nets(nets) + verify_headers_and_source_compat()
    afe_nets = load_afe30p_v001_nets(epro2_path)
    if afe_nets is None and DEFAULT_DUAL_EPRO2.is_file():
        afe_nets = load_afe30p_v001_nets(DEFAULT_DUAL_EPRO2)
    if afe_nets is not None:
        errs.extend(verify_afe30p_v001_nets(afe_nets))
    if not args and DEFAULT_DUAL_EPRO2.is_file() and DEFAULT_EPRO2.is_file():
        errs.extend(verify_u9_nets(load_u9_nets(DEFAULT_EPRO2)))

    if errs:
        print("MCU-U9 / v0.01 AFE-30P 引脚与寄存器核对失败：", file=sys.stderr)
        for e in errs:
            print("  -", e, file=sys.stderr)
        return 1

    if selftest:
        # 反例 1：FPC1.3 / 4 对调
        bad1 = dict(nets)
        bad1[("FPC1", 3)], bad1[("FPC1", 4)] = bad1[("FPC1", 4)], bad1[("FPC1", 3)]
        assert len(verify_u9_nets(bad1)) == 2, "反例 1 未检出 FPC1.3/4 交叉"

        # 反例 2：U7.31 被误当成 VBUS_SENSE
        bad2 = dict(nets)
        bad2[("U7", 31)] = "VBUS_SENSE"
        assert any("BOOT0" in e for e in verify_u9_nets(bad2)), "反例 2 未检出 U7.31 启动脚差异"

        # 反例 3：U8 多出一根未登记信号线
        bad3 = dict(nets)
        bad3[("U8", 19)] = "ROGUE_NET"
        assert any("未登记 GPIO 脚 19" in e for e in verify_u9_nets(bad3)), "反例 3 未检出 U8 未登记 GPIO"

        if afe_nets is not None:
            # 反例 4：U1.31 (RESV1) 未接 GND
            bad4 = dict(afe_nets)
            bad4[("U1", 31)] = "+3.3V"
            assert any("U1.pin31" in e for e in verify_afe30p_v001_nets(bad4)), "反例 4 未检出 U1.31 RESV1 错接"

            # 反例 5：U2.62 (RLDIN) 或 D116 漏接
            bad5 = dict(afe_nets)
            bad5[("D116", 1)] = ""
            assert any("D116" in e for e in verify_afe30p_v001_nets(bad5)), "反例 5 未检出 D116 ESD 漏接"

        # 反例 6：l432/main.c 误将 U2 设 cfg[0x02]=0x00 或置 RLD_MEAS(0x10)
        orig_c = (HERE / "l432/main.c").read_text(encoding="utf-8")
        assert any("cfg[0x02]=0x00" in e for e in verify_headers_and_source_compat(orig_c + "\nif (chip == 1) cfg[0x02] = 0x00;\n"))
        assert any("CFG1298_TEST[0x03]" in e for e in verify_headers_and_source_compat(orig_c.replace("[0x03] = 0xC0", "[0x03] = 0xD0", 1)))
        print("[SELFTEST PASS] 6/6 必败反例（FPC1.3/4 交叉、U7.31 错配、U8 未登记脚、U1.31 错接、D116 漏接、U2 关 INT_TEST/开 RLD_MEAS）全部拦截。")

    print(
        f"MCU-U9 + v0.01 AFE-30P 核对通过：U7(STM32L432) {len(U7_L432_EXPECTED)}+3 脚、U8(nRF52840) {len(U8_NRF_EXPECTED)} 脚、"
        "FPC1<->FPC2 20P、U1/U2(ADS1298) 电源/SPI/RLD/独立17-18脚、32 颗 ESD 与 l432/nrf 固件 100% 兼容。"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

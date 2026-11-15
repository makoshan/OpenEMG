#!/usr/bin/env python3
"""ADS1292-2ch + P44e + XIAO nRF52840 Sense 跨板引脚、硬件锁与 I2C 禁令自动核对器（含 6 项必败反例）。"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def locate_hw_files(design_arg: str | None, table_arg: str | None) -> tuple[Path, Path]:
    if design_arg and table_arg:
        return Path(design_arg), Path(table_arg)
    candidates = [
        (
            HERE.parent.parent / "hardware" / "2ch-ads1292" / "schematics" / "design.json",
            HERE.parent.parent / "hardware" / "common-mainboard" / "adapter-p44e-xiao" / "pin-table.csv",
        ),
        (
            HERE.parent.parent / "v12" / "ads1292-2ch-20261104" / "design.json",
            HERE.parent.parent / "v12" / "ads1292-p44e-xiao-adapter-20261106" / "pin-table.csv",
        ),
        (
            HERE.parent / "ads1292-2ch-20261104" / "design.json",
            HERE.parent / "ads1292-p44e-xiao-adapter-20261106" / "pin-table.csv",
        ),
    ]
    for d_path, t_path in candidates:
        if d_path.is_file() and t_path.is_file():
            return d_path, t_path
    raise FileNotFoundError("未找到 ads1292-2ch/design.json 与 P44e pin-table.csv")


def parse_pins_header(text: str) -> dict[str, int]:
    out: dict[str, int] = {}
    for m in re.finditer(r"static\s+constexpr\s+unsigned\s+([A-Z0-9_]+)\s*=\s*(\d+)u\s*;", text):
        out[m.group(1)] = int(m.group(2))
    return out


def parse_j2_pins(design_data: dict) -> dict[int, str]:
    raw_pins = design_data["parts"]["J2"]["pins"]
    out: dict[int, str] = {}
    for k, net in raw_pins.items():
        num = int(k.split(":", 1)[0])
        if 1 <= num <= 20:
            out[num] = net
    if len(out) != 20:
        raise ValueError(f"J2 信号脚数量异常：{len(out)}")
    return out


def parse_p44e_table(csv_text: str) -> dict[int, dict[str, str]]:
    out: dict[int, dict[str, str]] = {}
    for row in csv.DictReader(csv_text.splitlines()):
        p = int(row["adapter_pin"])
        out[p] = {
            "net": row["adapter_net"].strip(),
            "xiao": row["xiao"].strip(),
        }
    if len(out) != 20:
        raise ValueError(f"P44e pin-table 行数异常：{len(out)}")
    return out


def verify_all(
    pins_h_text: str,
    bench_h_text: str,
    pio_ini_text: str,
    src_texts: dict[str, str],
    design_data: dict,
    p44e_csv_text: str,
) -> list[str]:
    errors: list[str] = []
    consts = parse_pins_header(pins_h_text)
    j2 = parse_j2_pins(design_data)
    j1 = parse_p44e_table(p44e_csv_text)

    # 1. 核对 20P 反向排线 J1.k <-> J2.(21-k) 的电源、地、空脚与信号一致性
    expected_signals = [
        # (后缀, P44e net, XIAO pin, J2 net, Const_PIN, Const_J1, Const_J2)
        ("START", "START", "D3", "ADS_START", "PIN_ADS_START", "J1_PIN_START", "J2_PIN_START"),
        ("PWDN", "PWDN_N", "D4", "MCU_PWDN", "PIN_ADS_PWDN", "J1_PIN_PWDN", "J2_PIN_PWDN"),
        ("AVDD", "DRDY_B", "D5", "AVDD_SENSE", "PIN_AVDD_ADC", "J1_PIN_AVDD", "J2_PIN_AVDD"),
        ("DRDY", "DRDY_A", "D6", "ADS_DRDY_N", "PIN_ADS_DRDY", "J1_PIN_DRDY", "J2_PIN_DRDY"),
        ("CS", "CS_A", "D7", "ADS_CS_N", "PIN_ADS_CS", "J1_PIN_CS", "J2_PIN_CS"),
        ("SCLK", "SCLK", "D8", "MCU_SCLK", "XIAO_PIN_SCLK", "J1_PIN_SCLK", "J2_PIN_SCLK"),
        ("MISO", "MISO", "D9", "ADS_DOUT", "XIAO_PIN_MISO", "J1_PIN_MISO", "J2_PIN_MISO"),
        ("MOSI", "MOSI", "D10", "ADS_DIN", "XIAO_PIN_MOSI", "J1_PIN_MOSI", "J2_PIN_MOSI"),
    ]
    for label, p44e_net, xiao_name, j2_net, c_pin, c_j1, c_j2 in expected_signals:
        for req in (c_pin, c_j1, c_j2):
            if req not in consts:
                errors.append(f"ads1292_pins.h 缺少常量 {req}")
                return errors
        j1_pin = consts[c_j1]
        j2_pin = consts[c_j2]
        xiao_num = consts[c_pin]
        if j1_pin + j2_pin != 21:
            errors.append(f"{label} 违反 20P 反向排线关系：J1.{j1_pin} + J2.{j2_pin} != 21")
        if f"D{xiao_num}" != xiao_name:
            errors.append(f"{label} XIAO 引脚号错：头文件 D{xiao_num} != {xiao_name}")
        if j1.get(j1_pin, {}).get("net") != p44e_net or j1.get(j1_pin, {}).get("xiao") != xiao_name:
            errors.append(f"{label} 与 P44e pin-table J1.{j1_pin} 不符：{j1.get(j1_pin)}")
        if j2.get(j2_pin) != j2_net:
            errors.append(f"{label} 与 ADS1292-2ch J2.{j2_pin} 不符：实际 {j2.get(j2_pin)} != {j2_net}")

    # 核对 VBUS 硬件互锁脚 J1.19 <-> J2.2
    if consts.get("J1_PIN_VBUS") != 19 or consts.get("J2_PIN_VBUS") != 2:
        errors.append("VBUS 互锁脚常量错误（应为 J1.19 <-> J2.2）")
    elif j1[19]["net"] != "5V" or j1[19]["xiao"] != "5V" or j2[2] != "XIAO_5V":
        errors.append(f"VBUS 互锁网名不匹配：J1.19={j1[19]}, J2.2={j2[2]}")

    # 核对 3V3 与 GND 配对（防电源对地反插）
    for k in range(1, 21):
        m = 21 - k
        n1, n2 = j1[k]["net"], j2[m]
        if n1 == "3V3" and n2 != "3V3":
            errors.append(f"电源错配：J1.{k}(3V3) 对 J2.{m}({n2})")
        if n1 == "GND" and n2 != "GND":
            errors.append(f"地线错配：J1.{k}(GND) 对 J2.{m}({n2})")
        if n1 == "" and n2 not in ("NC",):
            errors.append(f"P44e 空脚 J1.{k} 意外连到载板有效网 J2.{m}({n2})")

    # 核对 D0、D1、D2 未使用常量
    if (consts.get("PIN_UNUSED_D0"), consts.get("PIN_UNUSED_D1"), consts.get("PIN_UNUSED_D2")) != (0, 1, 2):
        errors.append("未使用引脚常量 PIN_UNUSED_D0..D2 必须为 0, 1, 2")

    # 2. 静态检查源码禁止使用 Wire / TwoWire / TWIM（D5 复用为 SCL，初始化会破坏 AVDD_SENSE）
    forbidden_i2c = re.compile(r"\b(Wire|Wire1|TwoWire|NRF_TWIM0|NRF_TWIM1|NRF_TWI0|NRF_TWI1)\b")
    for fname, body in src_texts.items():
        stripped = re.sub(r"//[^\n]*", "", body)
        stripped = re.sub(r"/\*.*?\*/", "", stripped, flags=re.S)
        m = forbidden_i2c.search(stripped)
        if m:
            errors.append(f"{fname} 出现禁用 I2C 标识符 {m.group(1)}（会冲突占用 D5 AVDD_SENSE）")

    # 3. 检查默认双硬件锁与 1 MHz SPI 时钟约束未被放宽
    if not re.search(r"^\s*#define\s+MAKO_BENCH_MEASURED\s+0\s*$", bench_h_text, re.M):
        errors.append("bench_release.h 默认硬件锁 MAKO_BENCH_MEASURED 必须保持为 0")
    if not re.search(r"^\s*#define\s+MAKO_BENCH_POR_US\s+1000000u\s*$", bench_h_text, re.M):
        errors.append("bench_release.h 默认 MAKO_BENCH_POR_US 必须为 1000000u (>=1s)")
    if "-DMAKO_V12_AFE_ENABLED=0" not in pio_ini_text:
        errors.append("platformio.ini 缺少 -DMAKO_V12_AFE_ENABLED=0 默认锁")
    for m in re.finditer(r"-DMAKO_V12_SPI_HZ=(\d+)", pio_ini_text):
        if int(m.group(1)) != 1000000:
            errors.append(f"platformio.ini 存在超速 SPI 配置：{m.group(0)}（ADS1292 限 <=1.024 MHz）")
    if "-DMAKO_V12_SPI_HZ=1000000" not in pio_ini_text:
        errors.append("platformio.ini 必须显式固定 -DMAKO_V12_SPI_HZ=1000000")

    # 4. 检查 D5(AVDD_SENSE, 串 R26=100k) 是否显式设置 SAADC 采集时间 >=20 µs（防默认 3 µs <=10k 欠充误报欠压）
    main_stripped = re.sub(r"//[^\n]*", "", src_texts.get("main.cpp", ""))
    main_stripped = re.sub(r"/\*.*?\*/", "", main_stripped, flags=re.S)
    if not re.search(r"\banalogSampleTime\s*\(\s*(20|40)\s*\)", main_stripped):
        errors.append("main.cpp 必须调用 analogSampleTime(20) 或 analogSampleTime(40) 适配 R26=100 kΩ 源阻抗")

    return errors


def run_selftest(
    pins_h_text: str,
    bench_h_text: str,
    pio_ini_text: str,
    src_texts: dict[str, str],
    design_data: dict,
    p44e_csv_text: str,
) -> None:
    mutations = [
        (
            "反例1：排线脚号错1位(J2_PIN_DRDY=16)",
            pins_h_text.replace("J2_PIN_DRDY   = 17u;", "J2_PIN_DRDY   = 16u;"),
            bench_h_text,
            pio_ini_text,
            src_texts,
        ),
        (
            "反例2：交换D5/D6引脚号",
            pins_h_text.replace("PIN_ADS_DRDY  = 6u;", "PIN_ADS_DRDY  = 5u;"),
            bench_h_text,
            pio_ini_text,
            src_texts,
        ),
        (
            "反例3：源码误调Wire.begin()抢占D5",
            pins_h_text,
            bench_h_text,
            pio_ini_text,
            {**src_texts, "main.cpp": src_texts["main.cpp"] + "\nvoid bad(){ Wire.begin(); }\n"},
        ),
        (
            "反例4：私自放宽默认硬件锁MAKO_BENCH_MEASURED=1",
            pins_h_text,
            bench_h_text.replace("#define MAKO_BENCH_MEASURED 0", "#define MAKO_BENCH_MEASURED 1"),
            pio_ini_text,
            src_texts,
        ),
        (
            "反例5：SPI超速至2MHz违反SBAS502C",
            pins_h_text,
            bench_h_text,
            pio_ini_text.replace("-DMAKO_V12_SPI_HZ=1000000", "-DMAKO_V12_SPI_HZ=2000000"),
            src_texts,
        ),
        (
            "反例6：漏设analogSampleTime(20)导致100k源阻抗采样欠充",
            pins_h_text,
            bench_h_text,
            pio_ini_text,
            {**src_texts, "main.cpp": src_texts["main.cpp"].replace("analogSampleTime(20);", "")},
        ),
    ]
    for name, ph, bh, pi, st in mutations:
        errs = verify_all(ph, bh, pi, st, design_data, p44e_csv_text)
        if not errs:
            raise AssertionError(f"必败反例未报红：{name}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--design-json", default=None, help="ads1292-2ch design.json 路径")
    ap.add_argument("--pin-table", default=None, help="P44e pin-table.csv 路径")
    ap.add_argument("--self-test", action="store_true", help="运行 6 项必败反例自检")
    args = ap.parse_args()

    design_path, table_path = locate_hw_files(args.design_json, args.pin_table)
    design_data = json.loads(design_path.read_text(encoding="utf-8"))
    p44e_csv_text = table_path.read_text(encoding="utf-8")
    pins_h_text = (HERE / "src" / "ads1292_pins.h").read_text(encoding="utf-8")
    bench_h_text = (HERE / "src" / "bench_release.h").read_text(encoding="utf-8")
    pio_ini_text = (HERE / "platformio.ini").read_text(encoding="utf-8")
    src_texts = {
        p.name: p.read_text(encoding="utf-8")
        for p in sorted((HERE / "src").iterdir())
        if p.is_file() and p.suffix in {".h", ".c", ".cpp"}
    }

    errors = verify_all(pins_h_text, bench_h_text, pio_ini_text, src_texts, design_data, p44e_csv_text)
    if errors:
        for e in errors:
            print(f"[FAIL] {e}", file=sys.stderr)
        return 1

    if args.self_test:
        run_selftest(pins_h_text, bench_h_text, pio_ini_text, src_texts, design_data, p44e_csv_text)

    print(
        f"引脚与安全门核对通过：J1.k<->J2.(21-k) 20/20 脚 0 差，0 处 Wire/I2C 冲突，"
        f"默认双锁、1 MHz SPI 与 20us SAADC 生效" + ("，6/6 反例全红" if args.self_test else "")
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
